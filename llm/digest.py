"""RTS results -> accessible "catch me up" digest, built by the same draft → audit
→ revise agent as the rewrite.

The agent synthesizes a screen-reader-friendly summary (short sentences, headed
sections, jargon glossary, no color-only meaning), then calls the accessibility
MCP tools to check its own draft and revises until it meets the reader's target
grade. `on_step(tool_name)` fires per tool call so the Assistant panel can stream
live task steps — the "watch the agent think" money-shot.

Output is markdown destined for a Slack canvas. A deterministic final grade is
scored directly so any on-screen number is trustworthy.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from pydantic import BaseModel

from config import Settings
from llm import mcp_agent

DIGEST_SYSTEM = (
    "You summarize Slack activity for blind/low-vision, neurodivergent, and ESL "
    "readers, as markdown for a Slack canvas. Use short sentences and clear section "
    "headings. Define jargon inline or in a short glossary. Never rely on color or "
    "emoji to carry meaning. Write at the reader's target reading grade and language.\n\n"
    "Work like an editor with a checker: draft the summary, then call the "
    "`audit_accessibility` tool on your draft. If the reading grade is above target, "
    "or it has overly long sentences, undefined jargon, or color-only references, "
    "revise and check again. Keep iterating until it meets the target.\n\n"
    "When you are done, return ONLY the final summary markdown — no preamble or "
    "commentary about your process."
)

MAX_ITERATIONS = 6


class _Digest(BaseModel):
    """API-enforced shape so the final summary markdown lands clean on the canvas."""

    markdown: str


@dataclass
class DigestResult:
    markdown: str
    grade: float
    tool_calls: int = 0  # how many times the agent audited its own draft


def synthesize(
    settings: Settings,
    rts_context: str,
    target_grade: int = 6,
    language: str = "English",
    on_step=None,
    guard=None,
) -> DigestResult:
    """Sync entry point for the Assistant handler. `on_step(tool_name)` fires per
    tool the agent calls, to drive live task-step streaming."""
    if guard is not None:
        guard.check()
    return asyncio.run(_run(settings, rts_context, target_grade, language, on_step, guard))


async def _run(settings, rts_context, target_grade, language, on_step, guard) -> DigestResult:
    async with mcp_agent.mcp_session() as mcp:
        tools = await mcp_agent.agent_tools(mcp)
        user = (
            f"Reading grade: {target_grade}. Language: {language}.\n\n"
            f"Summarize this Slack activity accessibly. Use the accessibility tools to "
            f"check and improve your draft before you finish.\n\n{rts_context}"
        )
        md, tool_calls = await mcp_agent.run_loop(
            settings, model=settings.model_digest, system=DIGEST_SYSTEM, user=user,
            tools=tools, output_model=_Digest, field="markdown",
            max_tokens=4000, max_iterations=MAX_ITERATIONS, guard=guard, on_step=on_step,
        )
        grade = await mcp_agent.score_grade(mcp, md)
    return DigestResult(markdown=md, grade=grade, tool_calls=tool_calls)
