"""Proactive alt-text offer: when an image is posted with no alt text, send an
ephemeral "Describe this image? 👁️" offer whose button reuses the alt-text path.
This is what turns the tool into an *agent*.

Scopes: channels:history (+ message events), chat:write.
"""
from __future__ import annotations

import logging

from slack_bolt import App

from config import Settings

log = logging.getLogger("handlers.proactive")


def register(app: App, settings: Settings) -> None:
    @app.event("message")
    def on_message(event, client, logger):
        # Ignore bot echoes / edits / non-file messages.
        if event.get("subtype") in {"bot_message", "message_changed", "message_deleted"}:
            return
        files = event.get("files") or []
        images = [f for f in files if (f.get("mimetype") or "").startswith("image/")]
        if not images:
            return

        # An image already carrying alt text doesn't need the offer.
        if all(f.get("alt_txt") for f in images):
            return

        # TODO: post ephemeral offer with a button (action_id="offer_alt_text")
        #       carrying channel+ts in the block value; on click, run the
        #       handlers.reactions alt-text path.
        log.info("image w/o alt text in %s; would offer", event.get("channel"))

    @app.action("offer_alt_text")
    def on_offer_clicked(ack, body, client, logger):
        ack()
        # TODO: parse channel+ts from action value -> run alt-text path.
        raise NotImplementedError
