"""Assistant-panel agent: "Catch me up, accessibly".

thread_started -> suggested prompts.
user_message   -> RTS assistant.search.context (uses the event's action_token)
                  -> llm.digest synthesizes a screen-reader-friendly summary
                  -> render an accessible canvas (message fallback if canvas fails).
Progress is shown via set_status; streamed plan/task steps are a later polish pass.

Scopes: assistant:write, search:read.public (RTS), canvases:write.
"""
from __future__ import annotations

import logging
import re

from slack_bolt import App, Assistant

from config import Settings
from guardrails import Guardrails, BudgetExceeded
from llm import digest
from prefs.store import PrefsStore
from slack_io import canvas, rts

log = logging.getLogger("handlers.assistant")

_CHANNEL_MENTION = re.compile(r"<#(C[A-Z0-9]+)(?:\|[^>]*)?>")


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

        # Bot-token RTS calls REQUIRE action_token from the triggering event. Its
        # exact key isn't documented; log the candidates on first run to confirm.
        action_token = (payload.get("action_token")
                        or context.get("action_token")
                        or (context.get("assistant_thread") or {}).get("action_token"))
        log.info("user_message keys=%s action_token_found=%s",
                 sorted(payload.keys()), bool(action_token))

        if not action_token:
            say("⚠️ I couldn't get a search token for this thread — RTS may not be "
                "enabled for this app yet. (Check the logs for the payload keys.)")
            return

        # Scope to a channel if the prompt mentions one (<#C…|name>).
        m = _CHANNEL_MENTION.search(query)
        context_channel_id = m.group(1) if m else None

        try:
            set_status("Searching the channel…")
            resp = rts.search_context(
                client, query=query, action_token=action_token,
                context_channel_id=context_channel_id)
            if not resp.get("ok"):
                say(f"⚠️ Search failed: `{resp.get('error', 'unknown')}`.")
                return
            ctx = rts.flatten_results(resp)
            if not ctx.strip():
                say("I didn't find recent messages to summarize for that.")
                return

            p = prefs.get(payload.get("user") or "")
            set_status("Writing an accessible summary…")
            md = digest.synthesize(
                settings, ctx, target_grade=p.target_grade, language=p.language, guard=guard)
        except BudgetExceeded as e:
            say(f"⚠️ Paused — spend guardrail tripped ({e}).")
            return
        except Exception:
            log.exception("digest flow failed")
            say("⚠️ Something went wrong building the summary.")
            return

        # Render to an accessible canvas; fall back to posting the markdown.
        set_status("Building an accessible canvas…")
        title = "Catch-up summary"
        try:
            canvas_id = canvas.create_accessible_digest(
                client, title, md, channel_id=payload.get("channel"))
            say(f"📄 *{title}* is ready as an accessible canvas (id `{canvas_id}`).\n\n{md}")
        except Exception:
            log.exception("canvas creation failed — posting markdown instead")
            say(f"📄 *{title}*\n\n{md}")

    app.use(assistant)
