"""Reacji handlers:
  👁️  (:eyes:)         -> alt-text on images via Claude vision
  🧩  (:jigsaw:)       -> plain-language rewrite + MCP readability before/after

Scopes: reactions:read, files:read, chat:write, channels:history/im:history.
"""
from __future__ import annotations

import logging

from slack_bolt import App

from config import Settings
from guardrails import Guardrails, BudgetExceeded
from llm import alt_text, rewrite
from mcp_server import scoring
from prefs.store import PrefsStore
from slack_io import blocks
from slack_io import files as files_io
from slack_io import messages

log = logging.getLogger("handlers.reactions")

ALT_TEXT_EMOJI = "eyes"      # 👁️ — pick the final emoji during demo prep
REWRITE_EMOJI = "jigsaw"     # 🧩


def register(app: App, settings: Settings) -> None:
    guard = Guardrails(settings)
    prefs = PrefsStore(settings.prefs_db_path)

    @app.event("reaction_added")
    def on_reaction_added(event, client, logger):
        emoji = event.get("reaction")
        item = event.get("item", {})
        log.info("reaction_added: :%s: on %s", emoji, item.get("type"))
        if item.get("type") != "message":
            return

        channel = item["channel"]
        ts = item["ts"]

        if emoji == ALT_TEXT_EMOJI:
            run_alt_text(client, settings, guard, channel, ts)
        elif emoji == REWRITE_EMOJI:
            _handle_rewrite(client, settings, guard, prefs, channel, ts, user=event.get("user"))

    # 👍 is a positive signal — log it (a small grade nudge up could go here later).
    @app.action("feedback_up")
    def _fb_up(ack, body, logger):
        ack()
        log.info("feedback 👍 on %s", body["actions"][0].get("value"))

    # 👎 closes the loop: lower this user's reading grade and re-render the SAME
    # message simpler, in place — a visibly learning agent, not a logged shrug.
    @app.action("feedback_down")
    def _fb_down(ack, body, client, logger):
        ack()
        value = body["actions"][0].get("value")          # "channel:ts" of the source thread
        user = (body.get("user") or {}).get("id")
        msg_channel = (body.get("channel") or {}).get("id")
        msg_ts = (body.get("container") or {}).get("message_ts")
        if not (value and msg_channel and msg_ts):
            log.info("feedback 👎 missing context, can't re-render (%s)", value)
            return
        _rerender_simpler(client, settings, guard, prefs, value, user, msg_channel, msg_ts)


def run_alt_text(client, settings: Settings, guard: Guardrails, channel: str, ts: str) -> None:
    """Describe every image on the message at channel/ts and reply in-thread.
    Shared by the 👁️ reacji and the proactive offer button."""
    try:
        msg = messages.fetch_message(client, channel, ts)
    except LookupError:
        log.info("no message at %s/%s (maybe not in channel)", channel, ts)
        return

    images = [f for f in (msg.get("files") or [])
              if (f.get("mimetype") or "").startswith("image/")]
    if not images:
        return  # reacted message had no image — nothing to describe

    for f in images:
        try:
            data, media_type = files_io.download(settings, f)
            alt = alt_text.describe(settings, data, media_type, guard=guard)
        except BudgetExceeded as e:
            client.chat_postMessage(
                channel=channel, thread_ts=ts,
                text=f"⚠️ Alt-text paused — spend guardrail tripped ({e}).")
            return
        except Exception:
            log.exception("alt-text failed for file in %s/%s", channel, ts)
            client.chat_postMessage(
                channel=channel, thread_ts=ts,
                text="⚠️ Couldn't generate alt text for that image.")
            continue
        client.chat_postMessage(channel=channel, thread_ts=ts, text=f"👁️ *Alt text:* {alt}")


def _handle_rewrite(client, settings: Settings, guard: Guardrails, prefs: PrefsStore,
                    channel: str, ts: str, user: str | None) -> None:
    """Rewrite the reacted thread in plain language with an MCP grade before/after."""
    try:
        thread = messages.fetch_thread(client, channel, ts)
    except Exception:
        log.exception("couldn't fetch thread %s/%s", channel, ts)
        return
    text = messages.thread_text(thread)
    if not text.strip():
        return  # nothing to rewrite

    p = prefs.get(user) if user else prefs.get("")
    try:
        result = rewrite.plain_language(
            settings, text, target_grade=p.target_grade, language=p.language, guard=guard)
    except BudgetExceeded as e:
        client.chat_postMessage(
            channel=channel, thread_ts=ts,
            text=f"⚠️ Rewrite paused — spend guardrail tripped ({e}).")
        return
    except Exception:
        log.exception("rewrite failed for %s/%s", channel, ts)
        client.chat_postMessage(
            channel=channel, thread_ts=ts, text="⚠️ Couldn't rewrite that thread.")
        return

    if not (result.text or "").strip():
        # The agent loop hit its cap/timeout before emitting a final rewrite. Post a
        # plain fallback rather than a 0-length Slack section block (invalid_blocks).
        log.warning("empty rewrite for %s/%s — posting fallback", channel, ts)
        client.chat_postMessage(
            channel=channel, thread_ts=ts,
            text="⚠️ Couldn't produce a plain-language version — try again.")
        return

    text_out, blocks_out = _rewrite_message(result, f"{channel}:{ts}")
    client.chat_postMessage(channel=channel, thread_ts=ts, text=text_out, blocks=blocks_out)


def _impact_line(result) -> str:
    """Concrete, deterministic 'what this bought you' line for the rewrite. Plain
    language is often *longer* (it defines terms), so only show reading time when it
    genuinely dropped — the comprehension wins below carry the rest."""
    parts = []
    if result.seconds_before > result.seconds_after > 0:
        saved = result.seconds_before - result.seconds_after
        parts.append(
            f"⏱️ reading time {scoring.format_reading_time(result.seconds_before)} → "
            f"{scoring.format_reading_time(result.seconds_after)} "
            f"(saved {scoring.format_reading_time(saved)})")
    if result.acronyms_defined:
        parts.append(f"defined {result.acronyms_defined} "
                     f"acronym{'s' if result.acronyms_defined != 1 else ''}")
    if result.sentences_split:
        parts.append(f"split {result.sentences_split} long "
                     f"sentence{'s' if result.sentences_split != 1 else ''}")
    return "   ·   ".join(parts)


def _rewrite_message(result, feedback_value: str, *, note: str = "") -> tuple[str, list[dict]]:
    """Build the (fallback text, blocks) for a rewrite result. Shared by the first
    post and the 👎 re-render so both render identically. `note` appends an italic
    aside to the header (e.g. 'simplified after your feedback')."""
    lang = "" if result.language.lower() == "english" else f", {result.language}"
    # Surface the agentic beat: the rewrite came from a draft→audit→revise loop, not
    # a single shot. (Text carries the meaning — emoji stays decorative, dogfooding a11y.)
    revised = (f"  ·  _the agent audited & revised its draft {result.tool_calls}×_"
               if result.tool_calls else "")
    aside = f"  ·  _{note}_" if note else ""
    header = (f"🧩 *Plain-language rewrite*  ·  reading grade "
              f"{result.grade_before:.0f} → {result.grade_after:.0f}{lang}{revised}{aside}")
    blocks_out = [
        {"type": "section", "text": {"type": "mrkdwn", "text": header}},
        {"type": "section", "text": {"type": "mrkdwn", "text": result.text}},
    ]
    impact = _impact_line(result)
    if impact:
        blocks_out.append({"type": "context", "elements": [{"type": "mrkdwn", "text": impact}]})
    blocks_out += blocks.feedback_buttons(feedback_value)
    body = f"{header}\n\n{result.text}" + (f"\n\n{impact}" if impact else "")
    return body, blocks_out


def _rerender_simpler(client, settings: Settings, guard: Guardrails, prefs: PrefsStore,
                      value: str, user: str | None, msg_channel: str, msg_ts: str) -> None:
    """👎 handler: lower the user's reading grade, persist it, re-rewrite the source
    thread at the lower grade, and chat_update the SAME message in place."""
    try:
        channel, ts = value.split(":", 1)
    except ValueError:
        log.info("feedback 👎 unparseable value %r", value)
        return

    p = prefs.get(user) if user else prefs.get("")
    new_grade = max(3, p.target_grade - 2)   # step toward simpler; floor at grade 3
    if user:
        prefs.set(user, target_grade=new_grade)  # remembered for this user's future rewrites
    log.info("feedback 👎 → grade %s→%s for %s", p.target_grade, new_grade, user)

    try:
        thread = messages.fetch_thread(client, channel, ts)
    except Exception:
        log.exception("couldn't refetch thread %s/%s for re-render", channel, ts)
        return
    text = messages.thread_text(thread)
    if not text.strip():
        return

    try:
        result = rewrite.plain_language(
            settings, text, target_grade=new_grade, language=p.language, guard=guard)
    except BudgetExceeded as e:
        client.chat_update(channel=msg_channel, ts=msg_ts,
                           text=f"⚠️ Couldn't simplify further — spend guardrail tripped ({e}).")
        return
    except Exception:
        log.exception("re-render rewrite failed for %s/%s", channel, ts)
        return

    text_out, blocks_out = _rewrite_message(
        result, value, note=f"simplified to grade {new_grade} after your feedback")
    client.chat_update(channel=msg_channel, ts=msg_ts, text=text_out, blocks=blocks_out)
