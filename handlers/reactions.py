"""Reacji handlers:
  👁️  (:eyes:)         -> alt-text on images via Claude vision
  🧩  (:jigsaw:)       -> plain-language rewrite + MCP readability before/after

Scopes: reactions:read, files:read, chat:write, channels:history/im:history.
"""
from __future__ import annotations

import logging

from slack_bolt import App

from config import Settings

log = logging.getLogger("handlers.reactions")

ALT_TEXT_EMOJI = "eyes"      # 👁️ — pick the final emoji during demo prep
REWRITE_EMOJI = "jigsaw"     # 🧩


def register(app: App, settings: Settings) -> None:
    @app.event("reaction_added")
    def on_reaction_added(event, client, logger):
        emoji = event.get("reaction")
        item = event.get("item", {})
        if item.get("type") != "message":
            return

        channel = item["channel"]
        ts = item["ts"]

        if emoji == ALT_TEXT_EMOJI:
            _handle_alt_text(client, settings, channel, ts)
        elif emoji == REWRITE_EMOJI:
            _handle_rewrite(client, settings, channel, ts, user=event.get("user"))


def _handle_alt_text(client, settings: Settings, channel: str, ts: str) -> None:
    # TODO: slack_io.messages.fetch_message(channel, ts) -> files
    #       slack_io.files.download(file) -> bytes + media_type
    #       llm.alt_text.describe(bytes, media_type) -> alt text
    #       reply in thread (thread_ts=ts)
    log.info("alt-text requested for %s/%s", channel, ts)
    raise NotImplementedError


def _handle_rewrite(client, settings: Settings, channel: str, ts: str, user: str | None) -> None:
    # TODO: slack_io.messages.fetch_thread(channel, ts) -> text
    #       prefs.store.get(user) -> target grade / language
    #       llm.rewrite.plain_language(text, prefs) -> rewrite + (grade_before, grade_after)
    #       post in thread with feedback buttons (slack_io.blocks)
    log.info("rewrite requested for %s/%s by %s", channel, ts, user)
    raise NotImplementedError
