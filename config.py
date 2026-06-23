"""Central config: env vars + model IDs. Import `settings` everywhere."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key} (see .env.example)")
    return val


@dataclass(frozen=True)
class Settings:
    slack_bot_token: str
    slack_app_token: str
    anthropic_api_key: str

    # Models. Default Opus 4.8; swap alt-text to Sonnet if reacji latency matters.
    model_alt_text: str = "claude-opus-4-8"      # vision
    model_rewrite: str = "claude-opus-4-8"       # plain-language rewrite (tool_runner)
    model_digest: str = "claude-opus-4-8"        # RTS digest synthesis (streamed)

    prefs_db_path: str = "prefs.db"


def load_settings() -> Settings:
    return Settings(
        slack_bot_token=_require("SLACK_BOT_TOKEN"),
        slack_app_token=_require("SLACK_APP_TOKEN"),
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
    )
