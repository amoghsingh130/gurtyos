"""Entry point: Bolt(App) + Socket Mode. Registers all handlers, then connects.

Run:  python app.py   (no public URL / ngrok needed — Socket Mode)
"""
from __future__ import annotations

import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import load_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")


def build_app() -> tuple[App, str]:
    settings = load_settings()
    app = App(token=settings.slack_bot_token)

    # Register feature handlers (each module attaches its own listeners).
    from handlers import reactions, proactive, assistant

    reactions.register(app, settings)
    proactive.register(app, settings)
    assistant.register(app, settings)

    return app, settings.slack_app_token


def main() -> None:
    app, app_token = build_app()
    log.info("Starting Socket Mode handler...")
    SocketModeHandler(app, app_token).start()


if __name__ == "__main__":
    main()
