"""Tests for the spend ledger + budget guard (uses a temp SQLite db, no network)."""
import pytest

from config import Settings
from guardrails import BudgetExceeded, Guardrails, estimate_cost


def _settings(tmp_path, **kw):
    base = dict(slack_bot_token="x", slack_app_token="x", anthropic_api_key="x",
                cost_db_path=str(tmp_path / "cost.db"))
    base.update(kw)
    return Settings(**base)


def test_estimate_cost_opus_rates():
    # opus = (5, 25) per 1M tokens → 5 + 25
    assert estimate_cost("claude-opus-4-8", 1_000_000, 1_000_000) == 30.0


def test_estimate_cost_unknown_model_falls_back_to_opus():
    assert estimate_cost("mystery-model", 1_000_000, 0) == 5.0


def test_record_accumulates_spend_and_calls(tmp_path):
    g = Guardrails(_settings(tmp_path))
    assert g.total_spend() == 0.0
    g.record("claude-haiku-4-5", {"input_tokens": 1_000_000, "output_tokens": 0})  # $1
    assert round(g.total_spend(), 4) == 1.0
    assert g.calls_today() == 1


def test_check_raises_over_spend_ceiling(tmp_path):
    g = Guardrails(_settings(tmp_path, max_spend_usd=0.5))
    g.record("claude-opus-4-8", {"input_tokens": 1_000_000, "output_tokens": 1_000_000})  # $30
    with pytest.raises(BudgetExceeded):
        g.check()


def test_check_raises_over_daily_cap(tmp_path):
    g = Guardrails(_settings(tmp_path, max_calls_per_day=1))
    g.record("claude-haiku-4-5", {"input_tokens": 10, "output_tokens": 10})
    with pytest.raises(BudgetExceeded):
        g.check()
