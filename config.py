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


def _float_env(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


# Per-1M-token USD rates (input, output), verified 2026-06-24. Vision images are
# billed as input tokens — no separate line — so the input rate covers them.
PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


@dataclass(frozen=True)
class Settings:
    slack_bot_token: str
    slack_app_token: str
    anthropic_api_key: str

    # Models. DEV DEFAULT = Haiku (cheap) on the high-frequency reacji paths; the
    # streamed digest stays on Opus for the demo money-shot. Override per-env.
    model_alt_text: str = "claude-haiku-4-5"     # vision — swap to opus for final demo
    model_rewrite: str = "claude-haiku-4-5"      # plain-language rewrite (tool_runner)
    model_digest: str = "claude-opus-4-8"        # RTS digest synthesis (streamed)

    prefs_db_path: str = "prefs.db"

    # Spend guardrails (app-side; the console spend limit is the real hard stop).
    max_spend_usd: float = 8.0          # refuse LLM calls once cumulative est. spend hits this
    max_calls_per_day: int = 300        # per-day call cap across all flows (loop backstop)
    cost_db_path: str = "cost.db"


def load_settings() -> Settings:
    return Settings(
        slack_bot_token=_require("SLACK_BOT_TOKEN"),
        slack_app_token=_require("SLACK_APP_TOKEN"),
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        max_spend_usd=_float_env("MAX_SPEND_USD", 8.0),
        max_calls_per_day=_int_env("MAX_CALLS_PER_DAY", 300),
    )
