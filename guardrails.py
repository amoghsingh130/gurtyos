"""Cost guardrails: a persistent spend ledger + pre-call budget check.

Two layers protect the $10 budget:
  1. The Anthropic *console* spend limit — the real hard stop, enforced server-side.
  2. This module — app-side belt-and-suspenders so a runaway loop can't burn the
     budget within a single session before the console limit trips.

Usage in an LLM call site:
    guard = Guardrails(settings)
    guard.check()                      # raises BudgetExceeded if over ceiling/daily cap
    resp = client.messages.create(...)
    guard.record(settings.model_alt_text, resp.usage)   # log real token spend
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
import threading

from config import PRICING, Settings


class BudgetExceeded(RuntimeError):
    """Raised before an LLM call when a spend ceiling or daily cap is hit."""


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost for a single call. Unknown models fall back to Opus rates (safe high)."""
    in_rate, out_rate = PRICING.get(model, PRICING["claude-opus-4-8"])
    return input_tokens / 1_000_000 * in_rate + output_tokens / 1_000_000 * out_rate


class Guardrails:
    def __init__(self, settings: Settings):
        self._s = settings
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(settings.cost_db_path, check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS calls (
                   ts     TEXT NOT NULL,
                   day    TEXT NOT NULL,
                   model  TEXT NOT NULL,
                   in_tok INTEGER NOT NULL,
                   out_tok INTEGER NOT NULL,
                   cost_usd REAL NOT NULL
               )"""
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_day ON calls(day)")
        self._conn.commit()

    def total_spend(self) -> float:
        row = self._conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM calls").fetchone()
        return float(row[0])

    def calls_today(self) -> int:
        today = _dt.date.today().isoformat()
        row = self._conn.execute("SELECT COUNT(*) FROM calls WHERE day = ?", (today,)).fetchone()
        return int(row[0])

    def check(self) -> None:
        """Raise BudgetExceeded if the next call would be over a limit. Call BEFORE
        every LLM request."""
        spend = self.total_spend()
        if spend >= self._s.max_spend_usd:
            raise BudgetExceeded(
                f"cumulative est. spend ${spend:.2f} ≥ ceiling ${self._s.max_spend_usd:.2f}"
            )
        if self.calls_today() >= self._s.max_calls_per_day:
            raise BudgetExceeded(
                f"daily call cap reached ({self._s.max_calls_per_day}) — loop guard"
            )

    def record(self, model: str, usage) -> float:
        """Record real token usage from a response's `usage` object. Returns the
        call's estimated cost. Accepts the SDK usage object or a plain dict."""
        in_tok = int(getattr(usage, "input_tokens", None) or usage["input_tokens"])
        out_tok = int(getattr(usage, "output_tokens", None) or usage["output_tokens"])
        cost = estimate_cost(model, in_tok, out_tok)
        now = _dt.datetime.now(_dt.timezone.utc)
        with self._lock:
            self._conn.execute(
                "INSERT INTO calls (ts, day, model, in_tok, out_tok, cost_usd) VALUES (?,?,?,?,?,?)",
                (now.isoformat(), now.date().isoformat(), model, in_tok, out_tok, cost),
            )
            self._conn.commit()
        return cost
