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
from llm import digest
from prefs.store import PrefsStore
from slack_io import canvas, rts
from slack_io.stream import TaskStream

log = logging.getLogger("handlers.assistant")

_CHANNEL_MENTION = re.compile(r"<#(C[A-Z0-9]+)(?:\|[^>]*)?>")

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


def register(app: App, settings: Settings) -> None:
    assistant = Assistant()
    guard = Guardrails(settings)
    prefs = PrefsStore(settings.prefs_db_path)

    @assistant.thread_started
    def on_thread_started(say, set_suggested_prompts):
        say("Hi — I can catch you up accessibly. Name a channel or paste a thread.")
        set_suggested_prompts(prompts=[
            {"title": "Catch me up accessibly", "message": "Catch me up accessibly on #general"},
            {"title": "Explain this simply", "message": "Explain the latest discussion simply"},
        ])

    # Verified handler args: client, context, get_thread_context, logger, payload,
    # say, set_status.
    @assistant.user_message
    def on_user_message(payload, client, context, set_status, say, logger):
        query = (payload.get("text") or "").strip()

        # Bot-token RTS calls REQUIRE action_token. Confirmed location (2026-06-25):
        # the message event's assistant_thread carries it.
        action_token = ((payload.get("assistant_thread") or {}).get("action_token")
                        or payload.get("action_token"))
        if not action_token:
            say("⚠️ I couldn't get a search token for this thread — RTS may not be "
                "enabled for this app yet. (Check the logs for the payload keys.)")
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
            progress("Searching the channel for recent activity", tid="search")
            resp = rts.search_context(
                client, query=query, action_token=action_token,
                context_channel_id=context_channel_id)
            if not resp.get("ok"):
                finish_error(f"Search failed: `{resp.get('error', 'unknown')}`.")
                return
            ctx = rts.flatten_results(resp)
            if not ctx.strip():
                finish_error("I didn't find recent messages to summarize for that.")
                return
            progress("Searching the channel for recent activity", status="completed", tid="search")

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

            footer = (f"\n\n_Reading grade {result.grade:.0f}. The agent audited & revised "
                      f"its draft {result.tool_calls}× to get there._")
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

    app.use(assistant)
