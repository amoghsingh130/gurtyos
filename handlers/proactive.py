"""Proactive alt-text offer: when an image is posted with no alt text, send an
ephemeral "Describe this image? 👁️" offer whose button reuses the alt-text path.
This is what turns the tool into an *agent*.

Scopes: channels:history (+ message events), chat:write.
"""
from __future__ import annotations

import logging

from slack_bolt import App

from config import Settings
from guardrails import Guardrails
from handlers.reactions import run_alt_text
from slack_io import blocks

log = logging.getLogger("handlers.proactive")

_IGNORED_SUBTYPES = {"bot_message", "message_changed", "message_deleted"}


def register(app: App, settings: Settings) -> None:
    guard = Guardrails(settings)

    @app.event("message")
    def on_message(event, client, logger):
        # Ignore bot echoes / edits / non-file messages.
        if event.get("subtype") in _IGNORED_SUBTYPES:
            return
        images = [f for f in (event.get("files") or [])
                  if (f.get("mimetype") or "").startswith("image/")]
        if not images:
            return
        # An image already carrying alt text doesn't need the offer.
        if all(f.get("alt_txt") for f in images):
            return

        channel = event.get("channel")
        ts = event.get("ts")
        user = event.get("user")
        if not (channel and ts and user):
            return

        # Ephemeral so only the poster sees it; button carries channel:ts.
        client.chat_postEphemeral(
            channel=channel,
            user=user,
            blocks=blocks.alt_text_offer(f"{channel}:{ts}"),
            text="This image has no alt text. Describe it? 👁️",  # fallback for a11y/notifs
        )
        log.info("offered alt text for image in %s", channel)

    @app.action("offer_alt_text")
    def on_offer_clicked(ack, body, client, respond, logger):
        ack()
        value = body["actions"][0]["value"]
        channel, ts = value.split(":", 1)
        respond(text="On it — describing the image… 👁️", replace_original=True)
        run_alt_text(client, settings, guard, channel, ts)
