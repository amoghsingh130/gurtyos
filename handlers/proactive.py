"""Proactive offers — what turns the tool into an *agent* that acts unprompted:

  • image with no alt text  -> posted "Describe this image? 👁️" (reuses alt-text path)
  • hard-to-read text thread -> posted "Post a plain-language version? 🧩"
    (DEMO_CHANNELS-scoped, reuses the rewrite path) — the autonomy beat.

The offers are posted as ordinary channel messages (not ephemeral) so they're visible to
everyone, persist through reloads, and film cleanly for the demo. Accepting the offer
swaps the message in place (replace_original) and posts the result in the thread.

The text screen is a cheap, deterministic, LLM-free heuristic (reuses the pure
`mcp_server.scoring` functions), so watching a channel costs nothing until the user
actually accepts an offer.

Scopes: channels:history (+ message events), chat:write.
"""
from __future__ import annotations

import logging

from slack_bolt import App

from config import Settings
from guardrails import Guardrails
from handlers.reactions import run_alt_text, _handle_rewrite
from mcp_server import scoring
from prefs.store import PrefsStore
from slack_io import blocks

log = logging.getLogger("handlers.proactive")

_IGNORED_SUBTYPES = {"bot_message", "message_changed", "message_deleted"}

# Per-process de-dupe so a single message is only ever offered on once.
_offered: set[str] = set()


def _looks_hard(settings: Settings, text: str) -> bool:
    """Cheap, deterministic screen: is this text worth a plain-language offer?
    Tuned for *precision* over recall — a proactive nudge should only fire on
    genuinely hard text, never on plain chatter, so the agent doesn't become noise.

    Jargon/vocabulary density is the primary signal: it's robust to Slack's missing
    punctuation, whereas the Flesch-Kincaid grade is dominated by sentence length and
    balloons on punctuation-free run-ons (plain chatter scores ~13 with no periods,
    ~3 with them). So we only trust the grade when the text actually has sentence
    breaks AND carries at least some jargon."""
    if len(text.split()) < settings.rewrite_offer_min_words:
        return False
    jargon = len(scoring.jargon_candidates(text))
    if jargon >= 3:
        return True
    has_sentences = any(p in text for p in ".!?")
    return (has_sentences and jargon >= 1
            and scoring.flesch_kincaid_grade(text) >= settings.rewrite_offer_grade)


def register(app: App, settings: Settings) -> None:
    guard = Guardrails(settings)
    prefs = PrefsStore(settings.prefs_db_path)

    @app.event("message")
    def on_message(event, client, logger):
        # Ignore bot echoes / edits / non-file messages. The bot_id guard is what keeps
        # our own now-visible offer posts (and the seed personas) from re-triggering the
        # handler — ephemeral offers never generated message events, posted ones do.
        if event.get("subtype") in _IGNORED_SUBTYPES or event.get("bot_id"):
            return

        channel = event.get("channel")
        ts = event.get("ts")
        user = event.get("user")
        if not (channel and ts and user):
            return

        images = [f for f in (event.get("files") or [])
                  if (f.get("mimetype") or "").startswith("image/")]
        # Image missing alt text → offer to describe it (takes precedence).
        if images and not all(f.get("alt_txt") for f in images):
            client.chat_postMessage(
                channel=channel,
                blocks=blocks.alt_text_offer(f"{channel}:{ts}"),
                text="This image has no alt text. Describe it? 👁️",  # fallback for a11y/notifs
            )
            log.info("offered alt text for image in %s", channel)
            return

        # Proactive plain-language offer — allow-listed channels only, de-duped, and
        # only when the text actually screens as hard to read.
        if channel not in settings.demo_channels:
            return
        key = f"{channel}:{ts}"
        if key in _offered:
            return
        if not _looks_hard(settings, event.get("text") or ""):
            return
        _offered.add(key)
        client.chat_postMessage(
            channel=channel,
            blocks=blocks.rewrite_offer(key),
            text="This thread may be hard to read for some teammates — "
                 "post a plain-language version? 🧩",  # fallback for a11y/notifs
        )
        log.info("offered plain-language rewrite in %s", channel)

    @app.action("offer_alt_text")
    def on_offer_clicked(ack, body, client, respond, logger):
        ack()
        value = body["actions"][0]["value"]
        channel, ts = value.split(":", 1)
        respond(text="On it — describing the image… 👁️", replace_original=True)
        run_alt_text(client, settings, guard, channel, ts)

    @app.action("offer_rewrite")
    def on_rewrite_offer_clicked(ack, body, client, respond, logger):
        ack()
        value = body["actions"][0]["value"]
        channel, ts = value.split(":", 1)
        user = (body.get("user") or {}).get("id")
        respond(text="On it — posting a plain-language version… 🧩", replace_original=True)
        _handle_rewrite(client, settings, guard, prefs, channel, ts, user=user)
