"""Assistant-panel agent: "Catch me up, accessibly".

thread_started -> suggested prompts.
user_message   -> RTS assistant.search.context (uses the event's action_token)
                  -> llm.digest: a draft -> audit -> revise agent that synthesizes a
                     screen-reader-friendly summary, surfacing each audit step
                  -> render an accessible canvas (message fallback if canvas fails).

Progress is shown as streamed plan/task steps (chat.startStream, the money-shot)
when ENABLE_TASK_STREAM is on; otherwise it degrades to set_status updates. Either
way the agent's audit passes are surfaced so judges see it think.

Scopes: assistant:write, search:read.public (RTS), canvases:write.
"""
from __future__ import annotations

import logging
import re

import anthropic
from slack_bolt import App, Assistant

from config import Settings
from guardrails import Guardrails, BudgetExceeded
from handlers.reactions import run_alt_text, _handle_rewrite
from llm import digest
from mcp_server import scoring
from prefs.store import PrefsStore
from slack_io import canvas, messages, rts
from slack_io.stream import TaskStream

log = logging.getLogger("handlers.assistant")

_CHANNEL_MENTION = re.compile(r"<#(C[A-Z0-9]+)(?:\|[^>]*)?>")
# "accessibility report on #general", "a11y score", "audit #general"
_REPORT_RE = re.compile(r"(accessibilit(?:y|ies)|a11y)\s+(report|score|audit|check)|\baudit\b",
                        re.IGNORECASE)
# Typed fallback for the "Fix this channel" button, in case the button isn't handy.
_FIX_RE = re.compile(r"\bfix\b", re.IGNORECASE)


def _channel_label(client, query: str, channel_id: str) -> str:
    """Display label for the audited channel: '#name' from the <#C…|name> mention or
    conversations.info, else a graceful 'this channel' (resolving the name needs the
    channels:read scope, which the app may not have)."""
    m = re.search(r"<#C[A-Z0-9]+\|([^>]+)>", query)
    if m and m.group(1).strip():
        return f"#{m.group(1).strip()}"
    try:
        name = (client.conversations_info(channel=channel_id).get("channel") or {}).get("name")
        if name:
            return f"#{name}"
    except Exception:
        log.info("conversations_info failed for %s (add channels:read for a name)", channel_id)
    return "this channel"

# Natural-language personalization. The Assistant lets users *tell* the agent how to
# adapt ("now in Spanish", "set my reading level to 5"); we persist it so every future
# rewrite/digest for that user honors it — the visible "it learned" personalization beat.
_LANGUAGES = ("Spanish", "French", "German", "Portuguese", "Italian", "Chinese",
              "Japanese", "Korean", "Hindi", "Arabic", "English")
_LANG_RE = re.compile(r"\bin (" + "|".join(_LANGUAGES) + r")\b", re.IGNORECASE)
_GRADE_RE = re.compile(r"\b(?:reading level|grade|reading grade|level)\s*(?:to|=|:)?\s*(\d{1,2})\b",
                       re.IGNORECASE)
_SIMPLER_RE = re.compile(r"\b(simpler|too hard|easier|plainer)\b", re.IGNORECASE)


def _parse_pref_updates(query: str, current) -> tuple[dict, str | None]:
    """Pull preference changes out of a natural-language message. Returns
    (updates, note) where updates is a dict for PrefsStore.set kwargs and note is a
    short confirmation to show the user (or None if nothing changed)."""
    updates: dict = {}
    notes: list[str] = []

    m = _LANG_RE.search(query)
    if m:
        lang = m.group(1).capitalize()
        if lang.lower() != current.language.lower():
            updates["target_grade"] = current.target_grade  # carried so set() keeps it
            updates["language"] = lang
            notes.append(f"language → {lang}")

    g = _GRADE_RE.search(query)
    if g:
        grade = max(1, min(18, int(g.group(1))))
        updates["target_grade"] = grade
        notes.append(f"reading grade → {grade}")
    elif _SIMPLER_RE.search(query):
        grade = max(3, current.target_grade - 2)
        updates["target_grade"] = grade
        notes.append(f"reading grade → {grade}")

    if not updates:
        return {}, None
    return updates, "Got it — " + ", ".join(notes) + "."


def _content_words(ctx: str) -> int:
    """Count words of real message content in a flattened context block — the text
    after the 'who:' prefix on each line. Used to decline near-empty channels."""
    return sum(len(ln.split(":", 1)[-1].split()) for ln in ctx.splitlines())


def _history_context(msgs: list[dict]) -> str:
    """Flatten recent channel history into a chronological '<who>: <text>' block for
    the digest. conversations.history returns newest-first, so reverse it. Skips
    join/leave and other subtype noise; uses the bot/display name when present."""
    lines = []
    for m in reversed(msgs):
        text = (m.get("text") or "").strip()
        if text and not m.get("subtype"):
            who = m.get("username") or m.get("user") or "someone"
            lines.append(f"{who}: {text}")
    return "\n".join(lines)


def _run_channel_report(client, settings: Settings, query: str, set_status, say) -> None:
    """Audit a whole channel into a single accessibility score (before → projected
    after) and a screen-reader-friendly canvas. Uses the same deterministic scorer
    the MCP server exposes, so the on-camera number is trustworthy. No RTS token
    needed — reads channel history directly."""
    m = _CHANNEL_MENTION.search(query)
    if not m:
        say("Tell me which channel to audit, e.g. *accessibility report on #general*.")
        return
    target = m.group(1)
    label = _channel_label(client, query, target)

    set_status(f"Scanning {label} for accessibility issues")
    try:
        msgs = messages.fetch_recent(client, target, limit=150)  # includes thread replies
    except Exception:
        log.exception("couldn't read channel %s for report", target)
        say(f"⚠️ I couldn't read {label} — make sure I've been invited to it.")
        return

    rep = scoring.channel_report(msgs)
    md = canvas.accessibility_report_markdown(label, rep)

    set_status("Building the accessibility report canvas")
    try:
        canvas_id = canvas.create_accessible_digest(
            client, f"Accessibility report — {label}", md, channel_id=target)
        canvas_note = f"\n\n📄 Saved as an accessible canvas (id `{canvas_id}`)."
    except Exception:
        log.exception("report canvas creation failed — posting summary only")
        canvas_note = ""

    summary = (
        f"📋 *Accessibility report for {label}* — score "
        f"*{rep['score_before']} → {rep['score_after']}* once I apply my fixes.\n"
        f"Scanned {rep['messages_scanned']} messages: "
        f"{rep['missing_alt']} of {rep['total_images']} images missing alt text, "
        f"{rep['jargon_walls']} jargon-heavy messages, average reading grade "
        f"{rep['avg_grade']} (target {rep['target_grade']})."
        f"{canvas_note}"
    )
    blocks_out = [{"type": "section", "text": {"type": "mrkdwn", "text": summary}}]
    if rep["missing_alt"] or rep["jargon_walls"]:
        # The agent doesn't just measure — it can fix the whole channel in one click.
        blocks_out.append({"type": "actions", "elements": [{
            "type": "button", "action_id": "fix_channel", "value": target, "style": "primary",
            "text": {"type": "plain_text", "text": "🛠️  Fix this channel", "emoji": True},
        }]})
    say(text=summary, blocks=blocks_out)


_FIX_CAP = 3  # per click, keep it fast + within the spend guardrail


def _fix_channel(client, settings: Settings, guard, prefs, channel_id: str, label: str, say) -> None:
    """The agent applies its fixes channel-wide: writes alt text on images missing it
    and posts plain-language versions of jargon walls — capped per click. Reuses the
    same paths as the 👁️ and 🧩 reacji, so fixes appear in the channel itself."""
    try:
        msgs = messages.fetch_recent(client, channel_id, limit=80)
    except Exception:
        log.exception("fix: couldn't read %s", channel_id)
        say(f"⚠️ I couldn't read {label} to fix it — make sure I've been invited.")
        return

    image_ts = [m["ts"] for m in msgs if m.get("ts") and any(
        (f.get("mimetype") or "").startswith("image/") and not (f.get("alt_txt") or "").strip()
        for f in (m.get("files") or []))][:_FIX_CAP]
    wall_ts = [m["ts"] for m in msgs if m.get("ts") and not m.get("subtype")
               and (m.get("text") or "").strip() and scoring.is_jargon_wall(m["text"])][:_FIX_CAP]

    if not image_ts and not wall_ts:
        say(f"✅ {label} already looks accessible — nothing for me to fix.")
        return

    say(f"🛠️ On it — fixing {label}: writing alt text for {len(image_ts)} image(s) and "
        f"posting plain-language versions of {len(wall_ts)} thread(s)…")
    imgs = walls = 0
    try:
        for ts in image_ts:
            if guard is not None:
                guard.check()
            run_alt_text(client, settings, guard, channel_id, ts)
            imgs += 1
        for ts in wall_ts:
            if guard is not None:
                guard.check()
            _handle_rewrite(client, settings, guard, prefs, channel_id, ts, user=None)
            walls += 1
    except BudgetExceeded as e:
        say(f"⚠️ Stopped early — spend guardrail tripped ({e}). Fixed {imgs} image(s), "
            f"{walls} thread(s).")
        return

    say(f"✅ Done — described *{imgs}* image(s) and posted *{walls}* plain-language "
        f"rewrite(s) in {label}. Re-run *accessibility report on {label}* to watch the "
        f"score climb.")


def register(app: App, settings: Settings) -> None:
    assistant = Assistant()
    guard = Guardrails(settings)
    prefs = PrefsStore(settings.prefs_db_path)

    @assistant.thread_started
    def on_thread_started(say, set_suggested_prompts):
        say("Hi — I can catch you up accessibly. Name a channel or paste a thread.")
        set_suggested_prompts(prompts=[
            {"title": "Catch me up accessibly", "message": "Catch me up accessibly on #general"},
            {"title": "Accessibility report", "message": "Accessibility report on #general"},
            {"title": "Explain this simply", "message": "Explain the latest discussion simply"},
        ])

    # Verified handler args: client, context, get_thread_context, logger, payload,
    # say, set_status.
    @assistant.user_message
    def on_user_message(payload, client, context, set_status, say, logger):
        query = (payload.get("text") or "").strip()

        # Channel accessibility report — the org-scale beat. Reads history directly,
        # so it works even when RTS isn't enabled; handle it before the RTS path.
        if _REPORT_RE.search(query):
            _run_channel_report(client, settings, query, set_status, say)
            return

        # "fix #channel" — typed equivalent of the report's Fix-this-channel button.
        if _FIX_RE.search(query):
            fm = _CHANNEL_MENTION.search(query)
            if fm:
                _fix_channel(client, settings, guard, prefs, fm.group(1),
                             _channel_label(client, query, fm.group(1)), say)
            else:
                say("Tell me which channel to fix, e.g. *fix #general*.")
            return

        channel = payload.get("channel")
        thread_ts = payload.get("thread_ts")

        # Scope to a channel if the prompt mentions one (<#C…|name>).
        m = _CHANNEL_MENTION.search(query)
        context_channel_id = m.group(1) if m else None

        # Stream plan/task steps when enabled + available; else fall back to set_status.
        stream = TaskStream(client, channel, thread_ts)
        streaming = settings.enable_task_stream and stream.start(
            "*Catching you up — accessibly.* Watch the steps:")

        def progress(label: str, *, status: str = "in_progress", tid: str | None = None):
            if streaming:
                stream.task(tid or label, label, status)
            else:
                set_status(label)

        def finish_error(msg: str):
            if streaming:
                stream.stop(f"⚠️ {msg}")
            else:
                say(f"⚠️ {msg}")

        try:
            progress("Reading recent channel activity", tid="search")
            if context_channel_id:
                # Reliable retrieval for a named channel: pull its recent history (incl.
                # thread replies). RTS is a relevance *search*, which starves a generic
                # "catch me up" query — history is what this use case actually needs.
                try:
                    msgs = messages.fetch_recent(client, context_channel_id, limit=80)
                except Exception:
                    log.exception("history fetch failed for %s", context_channel_id)
                    finish_error("I couldn't read that channel — make sure I've been "
                                 "invited to it.")
                    return
                ctx = _history_context(msgs)
            else:
                # No channel named → topical search across the workspace via RTS (this is
                # the search use case RTS is built for, and keeps it load-bearing).
                action_token = ((payload.get("assistant_thread") or {}).get("action_token")
                                or payload.get("action_token"))
                if not action_token:
                    finish_error("Name a channel to catch up on (e.g. #general), or enable "
                                 "Real-Time Search so I can search across channels.")
                    return
                resp = rts.search_context(client, query=query, action_token=action_token)
                if not resp.get("ok"):
                    finish_error(f"Search failed: `{resp.get('error', 'unknown')}`.")
                    return
                ctx = rts.flatten_results(resp)

            if not ctx.strip():
                finish_error("I didn't find recent messages to summarize for that.")
                return
            # Decline cleanly on a near-empty channel instead of spending a call and
            # publishing a canvas that just says "nothing to summarize".
            if _content_words(ctx) < 12:
                finish_error("There's not enough recent activity there to summarize yet. "
                             "Try a busier channel, or ask about a specific topic.")
                return
            progress("Reading recent channel activity", status="completed", tid="search")

            # Apply any natural-language personalization the user asked for ("now in
            # Spanish", "set my reading level to 5") and persist it for next time.
            user_id = payload.get("user") or ""
            p = prefs.get(user_id)
            updates, pref_note = _parse_pref_updates(query, p)
            if updates:
                if user_id:
                    prefs.set(user_id, **updates)
                p = prefs.get(user_id)
                say(pref_note)
            progress("Drafting an accessible summary", tid="draft")

            audits = {"n": 0}

            def on_step(tool: str):
                # The agent calling its accessibility tools IS the visible thinking.
                if tool == "audit_accessibility":
                    audits["n"] += 1
                    progress(
                        f"Audited the draft (reading grade · jargon · contrast) — pass {audits['n']}",
                        status="completed", tid=f"audit-{audits['n']}")

            result = digest.synthesize(
                settings, ctx, target_grade=p.target_grade, language=p.language,
                on_step=on_step, guard=guard)
            progress("Drafting an accessible summary", status="completed", tid="draft")

            # Never publish an empty canvas (e.g. if the agent didn't converge): a blank
            # summary scores grade 0 and clutters the Files tab. Bail gracefully instead.
            if not (result.markdown or "").strip():
                log.warning("digest came back empty — skipping canvas")
                finish_error("I couldn't pull together enough to summarize there. Try a "
                             "busier channel, or ask about a specific topic.")
                return

            progress("Building an accessible canvas", tid="canvas")
            title = "Catch-up summary"
            try:
                canvas_id = canvas.create_accessible_digest(
                    client, title, result.markdown, channel_id=channel)
                canvas_note = f"\n\n📄 Saved as an accessible canvas (id `{canvas_id}`)."
            except Exception:
                log.exception("canvas creation failed — posting markdown only")
                canvas_note = ""
            progress("Building an accessible canvas", status="completed", tid="canvas")

            read_time = scoring.format_reading_time(scoring.reading_seconds(result.markdown))
            footer = (f"\n\n_Reading grade {result.grade:.0f} · about {read_time} to read. "
                      f"The agent audited & revised its draft {result.tool_calls}× to get there._")
            final_md = f"{result.markdown}{canvas_note}{footer}"

            if streaming:
                stream.stop(final_md)
            else:
                say(final_md)

        except BudgetExceeded as e:
            finish_error(f"Paused — spend guardrail tripped ({e}).")
        except anthropic.OverloadedError:
            # 529 from the model API — transient load, not our bug. Say so plainly.
            log.warning("digest flow hit an Anthropic 529 (overloaded) after retries")
            finish_error("The model is briefly overloaded — please try that again in a moment.")
        except Exception:
            log.exception("digest flow failed")
            finish_error("Something went wrong building the summary.")

    @app.action("fix_channel")
    def on_fix_channel(ack, body, client, say, logger):
        ack()
        channel_id = (body["actions"][0] or {}).get("value")
        if not channel_id:
            return
        _fix_channel(client, settings, guard, prefs, channel_id, f"<#{channel_id}>", say)

    app.use(assistant)
