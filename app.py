"""Entry point: Bolt(App) + Socket Mode. Registers all handlers, then connects.

Run:  python app.py   (no public URL / ngrok needed — Socket Mode)
"""
from __future__ import annotations

import logging

from slack_bolt import App
# websocket-client backend — the built-in Socket Mode client is prone to a
# BrokenPipe reconnect loop on macOS; this adapter is stable.
from slack_bolt.adapter.socket_mode.websocket_client import SocketModeHandler

from config import load_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")


def build_app() -> tuple[App, str]:
    settings = load_settings()
    app = App(token=settings.slack_bot_token)

    # Register feature handlers (each module attaches its own listeners).
    from handlers import reactions, proactive, assistant, home

    reactions.register(app, settings)
    proactive.register(app, settings)
    assistant.register(app, settings)
    home.register(app, settings)

    return app, settings.slack_app_token


def main() -> None:
    app, app_token = build_app()
    log.info("Starting Socket Mode handler...")
    SocketModeHandler(app, app_token).start()


if __name__ == "__main__":
    main()
