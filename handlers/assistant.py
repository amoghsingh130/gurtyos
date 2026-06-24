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

    # Verified handler args (docs.slack.dev, Bolt-Python Assistant class):
    #   client, context, get_thread_context, logger, payload, say, set_status
    @assistant.user_message
    def on_user_message(payload, client, set_status, say, context, logger):
        # Bot-token RTS calls REQUIRE action_token; it arrives top-level in the
        # triggering event payload (format "xact-1-..."). Confirm the key against
        # a live event the first time — docs say "in the payload" but don't print it.
        action_token = payload.get("action_token")

        set_status("is thinking...")  # assistant.threads.setStatus

        # TODO wire-up:
        #   resp = slack_io.rts.search_context(client, payload["text"], action_token, ...)
        #   ctx  = slack_io.rts.flatten_results(resp)
        #   For the streamed "watch it work" UX, open a stream and emit task_update
        #   chunks while synthesizing, then attach the canvas link + feedback blocks
        #   on stop:
        #     start = client.api_call("chat.startStream",
        #               params={"channel": ch, "thread_ts": thread, "task_display_mode": "plan"})
        #     ts = start["ts"]
        #     client.api_call("chat.appendStream", params={"channel": ch, "message_ts": ts,
        #               "thread_ts": thread, "chunks": [blocks.task_update_chunk("Reading channel", "in_progress")]})
        #     digest_md = llm.digest.synthesize(settings, ctx, prefs.target_grade, prefs.language)
        #     canvas_id = slack_io.canvas.create_accessible_digest(client, title, digest_md, channel_id=ch)
        #     client.api_call("chat.stopStream", params={"channel": ch, "message_ts": ts,
        #               "thread_ts": thread, "blocks": blocks.feedback_buttons(f"{ch}:{ts}")})
        raise NotImplementedError

    app.use(assistant)
