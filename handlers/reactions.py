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
from llm import alt_text
from slack_io import files as files_io
from slack_io import messages

log = logging.getLogger("handlers.reactions")

ALT_TEXT_EMOJI = "eyes"      # 👁️ — pick the final emoji during demo prep
REWRITE_EMOJI = "jigsaw"     # 🧩


def register(app: App, settings: Settings) -> None:
    guard = Guardrails(settings)

    @app.event("reaction_added")
    def on_reaction_added(event, client, logger):
        emoji = event.get("reaction")
        item = event.get("item", {})
        if item.get("type") != "message":
            return

        channel = item["channel"]
        ts = item["ts"]

        if emoji == ALT_TEXT_EMOJI:
            _handle_alt_text(client, settings, guard, channel, ts)
        elif emoji == REWRITE_EMOJI:
            _handle_rewrite(client, settings, guard, channel, ts, user=event.get("user"))


def _handle_alt_text(client, settings: Settings, guard: Guardrails, channel: str, ts: str) -> None:
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


def _handle_rewrite(client, settings: Settings, guard: Guardrails,
                    channel: str, ts: str, user: str | None) -> None:
    # TODO (Days 8-9): fetch_thread -> prefs -> llm.rewrite.plain_language (MCP
    # before/after via tool_runner) -> post in thread with feedback buttons.
    log.info("rewrite requested for %s/%s by %s", channel, ts, user)
    raise NotImplementedError
