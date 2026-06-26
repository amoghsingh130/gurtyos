"""Live LLM + MCP integration tests — the real proof the agent loops work end to end.

These make real Anthropic calls and spawn the MCP scorer, so they cost a little and
are slow/occasionally rate-limited. They're skipped by default; run explicitly with:

    RUN_LLM_TESTS=1 python -m pytest tests/test_llm_integration.py -q
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_LLM_TESTS"),
    reason="set RUN_LLM_TESTS=1 to run live LLM/MCP tests",
)


def _settings():
    from config import load_settings
    return load_settings()


_NORMAL = (
    "marcus: Shipped the auth refactor, tests are green; picking up search indexing.\n"
    "sam: The OKR rollup is blocked because the CRM SSO handshake failed.\n"
    "lena: We're sunsetting the legacy auth shim for the OIDC broker; audit your tokens."
)
_THIN = ("alice: thanks everyone\nbob: lgtm, merging the hotfix now\ncarol: see you tomorrow")


def test_digest_normal_produces_summary_at_grade():
    from llm import digest
    r = digest.synthesize(_settings(), _NORMAL, target_grade=8, language="English")
    assert r.markdown.strip(), "digest must not be empty"
    assert r.grade > 0
    assert r.grade <= 13  # roughly near the grade-8 target, not jargon-level


def test_digest_thin_content_still_summarizes():
    # The #general regression: thin-but-real content must still yield a summary,
    # never an empty canvas.
    from llm import digest
    r = digest.synthesize(_settings(), _THIN, target_grade=6, language="English")
    assert r.markdown.strip(), "thin content should still produce a summary"
    assert r.grade > 0


def test_digest_in_spanish():
    from llm import digest
    r = digest.synthesize(_settings(), _NORMAL, target_grade=8, language="Spanish")
    assert r.markdown.strip()


def test_rewrite_reduces_reading_grade():
    from llm import rewrite
    jargon = ("Per the SLA the API KPIs must be reconciled against the EOD ETL pipeline "
              "before the QBR notwithstanding the aforementioned dependencies which "
              "materially impact the downstream deliverables across the organization.")
    r = rewrite.plain_language(_settings(), jargon, target_grade=6, language="English")
    assert r.text.strip(), "rewrite must not be empty"
    assert r.grade_after < r.grade_before  # it actually simplified


def test_mcp_scorer_roundtrip():
    # The custom MCP server is reachable over stdio and scores text.
    import asyncio
    from llm import mcp_agent

    async def _run():
        async with mcp_agent.mcp_session() as mcp:
            simple = await mcp_agent.score_grade(mcp, "The cat sat on the mat.")
            jargon = await mcp_agent.score_grade(
                mcp, "Aforementioned stakeholders must operationalize the deliverables.")
            return simple, jargon

    simple, jargon = asyncio.run(_run())
    assert simple < jargon  # the scorer orders simple below jargon
