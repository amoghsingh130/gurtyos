"""App Home tab: a friendly, well-formatted intro + guide shown when a user clicks
the app.

Published on `app_home_opened` via views.publish. The view is itself accessible —
every image carries real alt text — so the app dogfoods its own rules.

Slack app config (one-time): App Home → Home Tab = On; Event Subscriptions →
subscribe to the `app_home_opened` bot event. Scope: the bot token already covers
views.publish.
"""
from __future__ import annotations

import logging

from slack_bolt import App

from config import Settings

log = logging.getLogger("handlers.home")

# --- Pictures ---------------------------------------------------------------
# SWAP THESE for real screenshots before the final demo: replace each `url` with a
# public HTTPS image URL (GitHub raw is the most reliable — see the shot list in chat).
# Keep `alt` accurate: this app describes images for a living, so its own Home tab must
# too. The defaults are self-describing placeholders so the layout looks intentional
# until you swap them. `banner` renders full-width; the rest render as card thumbnails.
HOME_IMAGES = {
    "banner": {
        # Real banner generated at assets/home-banner.png — host it at a public URL
        # (GitHub raw / imgur) and paste the link here. Until then this placeholder
        # mirrors the same branding.
        "url": "https://placehold.co/1200x300/4A154B/FFFFFF/png?text=gurtYos",
        "alt": "gurtYos — accessibility co-pilot for Slack.",
    },
    "rewrite": {
        "url": "https://placehold.co/400x300/2EB67D/FFFFFF/png?text=grade%2024%20%E2%86%92%207",
        "alt": "A jargon-heavy thread rewritten in plain language, reading grade 24 to 7.",
    },
    "digest": {
        "url": "https://placehold.co/400x300/1264A3/FFFFFF/png?text=accessible%0Acanvas",
        "alt": "An accessible canvas summarizing a channel in short, headed sections.",
    },
    "report": {
        "url": "https://placehold.co/400x300/ECB22E/111111/png?text=score%2022%20%E2%86%92%2097",
        "alt": "A channel accessibility report scoring 22 out of 100, projected 97 after fixes.",
    },
}


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _card(text: str, image_key: str) -> dict:
    """A feature card: copy on the left, a thumbnail screenshot on the right."""
    img = HOME_IMAGES[image_key]
    return {
        "type": "section",
        "text": {"type": "mrkdwn", "text": text},
        "accessory": {"type": "image", "image_url": img["url"], "alt_text": img["alt"]},
    }


def _home_view() -> dict:
    return {
        "type": "home",
        "blocks": [
            # --- Hero ---------------------------------------------------------
            {"type": "header",
             "text": {"type": "plain_text", "text": "♿ gurtYos", "emoji": True}},
            {"type": "context", "elements": [{"type": "mrkdwn",
             "text": "Accessibility co-pilot for Slack"}]},
            _section(
                "*Slack, made readable for the teammates it leaves behind.*\n"
                "I describe images, rewrite jargon into plain language, and catch you up — "
                "accessibly. And I _measure_ every fix, so the difference is a number, "
                "not a claim."),
            {"type": "image", "image_url": HOME_IMAGES["banner"]["url"],
             "alt_text": HOME_IMAGES["banner"]["alt"]},

            # --- Who I help (2-column grid) ----------------------------------
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": "🦮  *Blind & low-vision*\nAlt text + screen-reader-ready digests"},
                {"type": "mrkdwn", "text": "🧠  *Neurodivergent*\nPlain language, shorter sentences"},
                {"type": "mrkdwn", "text": "🌍  *Non-native English*\nRewrites in your language"},
                {"type": "mrkdwn", "text": "📊  *Everyone*\nMeasurable, ADA / 508-aligned"},
            ]},
            {"type": "divider"},

            # --- What I can do (feature cards with thumbnails) ---------------
            {"type": "header", "text": {"type": "plain_text", "text": "✨ What I can do", "emoji": True}},

            _card(
                "*🧩  Plain-language rewrite*\n"
                "React :jigsaw: on a jargon-heavy thread. I rewrite it and show the reading "
                "grade *before → after*. Tap 👎 and I make it simpler — and remember your level.",
                "rewrite"),
            _card(
                "*💬  Catch me up, accessibly*\n"
                "Message me _“catch me up on #channel”_ → a screen-reader-friendly canvas "
                "summary, in your language (_“now in Spanish”_) and at your reading level.",
                "digest"),
            _card(
                "*📋  Accessibility report*\n"
                "Message me _“accessibility report on #channel”_ → a whole-channel score, "
                "current *→* projected-after-fixes, framed for ADA / Section 508.",
                "report"),
            _section(
                "*👁️  Describe an image*\n"
                "React :eyes: on any message with an image → screen-reader-quality alt text "
                "in the thread."),
            _section(
                "*⚡  I act on my own*\n"
                "In channels I watch, I notice hard-to-read threads and offer to fix them — "
                "no one has to ask."),

            {"type": "divider"},

            # --- Get started --------------------------------------------------
            {"type": "header", "text": {"type": "plain_text", "text": "🚀 Try it", "emoji": True}},
            _section(
                "•  React 🧩 on a jargon-heavy thread\n"
                "•  Message me  *catch me up on #general*\n"
                "•  Message me  *accessibility report on #general*"),

            # --- Footer -------------------------------------------------------
            {"type": "divider"},
            {"type": "context", "elements": [{"type": "mrkdwn",
             "text": "🔒 I store only your reading-level and language preferences — never "
                     "your messages.   ·   Built on Slack Assistant, a custom MCP "
                     "accessibility scorer, and Real-Time Search."}]},
            {"type": "context", "elements": [{"type": "mrkdwn",
             "text": "✅ Every image on this page has real alt text — I follow my own rules."}]},
        ],
    }


def register(app: App, settings: Settings) -> None:
    @app.event("app_home_opened")
    def on_home_opened(event, client, logger):
        user = event.get("user")
        if not user:
            return
        try:
            client.views_publish(user_id=user, view=_home_view())
            log.info("published App Home for %s", user)
        except Exception:
            log.exception("failed to publish App Home")
