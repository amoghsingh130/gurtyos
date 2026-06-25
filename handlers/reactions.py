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

    # Acknowledge feedback buttons so clicks don't dangle (record can come later).
    @app.action("feedback_up")
    def _fb_up(ack, body, logger):
        ack()
        log.info("feedback 👍 on %s", body["actions"][0].get("value"))

    @app.action("feedback_down")
    def _fb_down(ack, body, logger):
        ack()
        log.info("feedback 👎 on %s", body["actions"][0].get("value"))


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

    lang = "" if result.language.lower() == "english" else f", {result.language}"
    header = (f"🧩 *Plain-language rewrite*  ·  reading grade "
              f"{result.grade_before:.0f} → {result.grade_after:.0f}{lang}")
    client.chat_postMessage(
        channel=channel, thread_ts=ts,
        text=f"{header}\n\n{result.text}",
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": header}},
            {"type": "section", "text": {"type": "mrkdwn", "text": result.text}},
            *blocks.feedback_buttons(f"{channel}:{ts}"),
        ])
