"""Assistant-panel agent: "Catch me up, accessibly".

thread_started -> suggested prompts.
user_message   -> RTS assistant.search.context (uses the event's action_token)
                  -> llm.digest synthesizes a screen-reader-friendly summary
                  -> render an accessible canvas; stream plan blocks + task steps.

Scopes: assistant:write, search:read.public (RTS), canvases:write.
"""
from __future__ import annotations

import logging

from slack_bolt import App, Assistant

from config import Settings

log = logging.getLogger("handlers.assistant")


def register(app: App, settings: Settings) -> None:
    assistant = Assistant()

    @assistant.thread_started
    def on_thread_started(say, set_suggested_prompts):
        say("Hi — I can catch you up accessibly. Pick a channel or paste a thread.")
        set_suggested_prompts(
            prompts=[
                {"title": "Catch me up accessibly", "message": "Catch me up accessibly on #general"},
                {"title": "Explain this thread simply", "message": "Explain this thread simply"},
            ]
        )

    @assistant.user_message
    def on_user_message(payload, client, set_status, say, context):
        # action_token for RTS bot-token path comes from the triggering event.
        # TODO: action_token = payload/context -> slack_io.rts.search_context(...)
        #       set_status("Reading the channel...")  # plan/task-step streaming
        #       llm.digest.synthesize(rts_results, prefs) (streamed)
        #       slack_io.canvas.create_accessible_digest(...) -> link
        #       say(canvas link)
        set_status("is thinking...")
        raise NotImplementedError

    app.use(assistant)
