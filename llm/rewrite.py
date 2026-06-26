"""Plain-language rewrite as an agentic self-audit loop.

The agent (Claude via `tool_runner`) drafts a rewrite, then calls the custom
accessibility MCP tools (`audit_accessibility` / `score_readability`) to check its
own draft, and revises until it meets the reader's target grade. This makes MCP
genuinely load-bearing: the tools *drive the agent's behavior*, they don't just
decorate the output.

Two numbers are reported deterministically (independent of model behavior) by
scoring the original and the final rewrite directly, so the on-screen "grade
X → Y" is always trustworthy — the reliability point of this concept.

Shared loop plumbing lives in `llm/mcp_agent.py`. The MCP SDK is async, so the
work runs in a private event loop via asyncio.run(); Slack handlers call the sync
`plain_language()` wrapper.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from pydantic import BaseModel

from config import Settings
from llm import mcp_agent
from mcp_server import scoring

REWRITE_SYSTEM = (
    "You rewrite jargon-heavy Slack threads into plain language for neurodivergent "
    "and ESL readers. Preserve every concrete fact, name, number, decision, and "
    "action item — simplify the wording, never the substance.\n\n"
    "Work like an editor with a checker: draft a rewrite, then call the "
    "`audit_accessibility` tool on your draft. If it reports a reading grade above "
    "the target, overly long sentences, undefined jargon, or color-only references, "
    "revise and check again — but **audit at most twice**, then return your best "
    "version even if a metric is still slightly off.\n\n"
    "Always finish your turn by replying with the final rewrite — never end on a tool "
    "call without it, and never return an empty rewrite. No preamble, no scores, no "
    "commentary about your process."
)

MAX_ITERATIONS = 8  # safety cap on the agent's draft / audit / revise turns


class _FinalRewrite(BaseModel):
    """API-enforced shape for the agent's final answer — guarantees we get the
    rewrite alone, with no 'here is my rewrite…' preamble leaking onto screen."""

    text: str


@dataclass
class RewriteResult:
    text: str
    grade_before: float
    grade_after: float
    language: str
    tool_calls: int = 0  # how many times the agent audited/scored its own draft
    # Concrete impact numbers (deterministic, for on-screen "what this bought you").
    seconds_before: int = 0
    seconds_after: int = 0
    acronyms_defined: int = 0   # jargon tokens removed/defined vs the original
    sentences_split: int = 0    # over-long sentences the rewrite broke up


def plain_language(
    settings: Settings,
    original: str,
    target_grade: int = 6,
    language: str = "English",
    guard=None,
    on_step=None,
) -> RewriteResult:
    """Sync entry point for Slack handlers. `on_step(tool_name)` is called for each
    tool the agent invokes (lets a caller surface live task steps)."""
    if guard is not None:
        guard.check()  # raises BudgetExceeded if over the spend ceiling / daily cap
    return asyncio.run(_run(settings, original, target_grade, language, guard, on_step))


async def _run(settings, original, target_grade, language, guard, on_step) -> RewriteResult:
    async with mcp_agent.mcp_session() as mcp:
        # Deterministic before-score — the trustworthy on-camera number.
        grade_before = await mcp_agent.score_grade(mcp, original)

        tools = await mcp_agent.agent_tools(mcp)
        user = (
            f"Rewrite the following Slack thread at roughly a US grade-{target_grade} "
            f"reading level, in {language}. Use the accessibility tools to check and "
            f"improve your draft before you finish.\n\n{original}"
        )
        text, tool_calls = await mcp_agent.run_loop(
            settings, model=settings.model_rewrite, system=REWRITE_SYSTEM, user=user,
            tools=tools, output_model=_FinalRewrite, field="text",
            max_tokens=1500, max_iterations=MAX_ITERATIONS, guard=guard, on_step=on_step,
        )

        # Deterministic after-score on the agent's final rewrite.
        grade_after = await mcp_agent.score_grade(mcp, text)

    # Deterministic impact deltas (pure scoring, original vs rewrite).
    jargon_b, jargon_a = len(scoring.jargon_candidates(original)), len(scoring.jargon_candidates(text))
    long_b, long_a = len(scoring.long_sentences(original)), len(scoring.long_sentences(text))
    return RewriteResult(
        text=text, grade_before=grade_before, grade_after=grade_after,
        language=language, tool_calls=tool_calls,
        seconds_before=scoring.reading_seconds(original),
        seconds_after=scoring.reading_seconds(text),
        acronyms_defined=max(0, jargon_b - jargon_a),
        sentences_split=max(0, long_b - long_a),
    )
