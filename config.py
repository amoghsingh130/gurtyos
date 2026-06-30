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


def _bool_env(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _list_env(key: str) -> tuple[str, ...]:
    """Comma-separated env var → tuple of trimmed, non-empty values."""
    raw = os.environ.get(key, "")
    return tuple(v.strip() for v in raw.split(",") if v.strip())


def _str_env(key: str, default: str) -> str:
    val = os.environ.get(key)
    return val.strip() if val and val.strip() else default


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

    # Models. Haiku (cheap/fast) on the high-frequency reacji paths; the digest uses
    # Sonnet 4.6 — fast enough that its multi-iteration agent loop doesn't drag, and on
    # a separate capacity pool from Opus (fewer 529 "overloaded" errors). Set
    # MODEL_DIGEST=claude-opus-4-8 for the final recorded demo if you want max polish.
    model_alt_text: str = "claude-haiku-4-5"     # vision (single call)
    model_rewrite: str = "claude-haiku-4-5"      # plain-language rewrite (tool_runner)
    model_digest: str = "claude-sonnet-4-6"      # RTS digest synthesis (agent loop)

    # Anthropic 529s ("overloaded") are transient; the SDK retries with backoff. The
    # digest loop makes many calls, so any one exhausting retries fails the whole flow —
    # give it generous headroom so a brief overload self-heals instead of erroring.
    anthropic_max_retries: int = 5

    # Wall-clock ceiling on a single draft→audit→revise agent loop. The MCP scorer's
    # stdio transport can deadlock mid-call (subprocess blocks at 0% CPU); this bounds
    # the loop so it falls back to the best draft produced so far instead of hanging a
    # whole Slack interaction forever. See llm/mcp_agent.run_loop.
    agent_loop_timeout_s: int = 30

    prefs_db_path: str = "prefs.db"

    # Spend guardrails (app-side; the console spend limit is the real hard stop).
    max_spend_usd: float = 8.0          # refuse LLM calls once cumulative est. spend hits this
    max_calls_per_day: int = 300        # per-day call cap across all flows (loop backstop)
    cost_db_path: str = "cost.db"

    # Assistant money-shot: stream plan/task steps via chat.startStream so judges watch
    # the agent audit its draft live. On by default; every streaming call is defensive
    # and degrades to set_status progress + a posted digest if the API is unavailable.
    enable_task_stream: bool = True

    # Proactive plain-language offer (the autonomy beat). Scoped to an allow-list of
    # channels so the agent never spams a real workspace; empty = the feature is off.
    # A message is "hard" (worth offering on) if it's at least N words AND scores at or
    # above the grade ceiling / has a long sentence / stacks ≥3 jargon tokens.
    demo_channels: tuple[str, ...] = ()
    rewrite_offer_min_words: int = 40
    rewrite_offer_grade: float = 12.0


def load_settings() -> Settings:
    return Settings(
        slack_bot_token=_require("SLACK_BOT_TOKEN"),
        slack_app_token=_require("SLACK_APP_TOKEN"),
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        model_alt_text=_str_env("MODEL_ALT_TEXT", "claude-haiku-4-5"),
        model_rewrite=_str_env("MODEL_REWRITE", "claude-haiku-4-5"),
        model_digest=_str_env("MODEL_DIGEST", "claude-sonnet-4-6"),
        anthropic_max_retries=_int_env("ANTHROPIC_MAX_RETRIES", 5),
        agent_loop_timeout_s=_int_env("AGENT_LOOP_TIMEOUT_S", 30),
        max_spend_usd=_float_env("MAX_SPEND_USD", 8.0),
        max_calls_per_day=_int_env("MAX_CALLS_PER_DAY", 300),
        enable_task_stream=_bool_env("ENABLE_TASK_STREAM", True),
        demo_channels=_list_env("DEMO_CHANNELS"),
        rewrite_offer_grade=_float_env("REWRITE_OFFER_GRADE", 12.0),
    )
