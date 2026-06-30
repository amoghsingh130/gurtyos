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
import logging
from dataclasses import dataclass

from pydantic import BaseModel

from config import Settings
from llm import mcp_agent, sanitize

log = logging.getLogger("llm.digest")

DIGEST_SYSTEM = (
    "You summarize Slack activity for blind/low-vision, neurodivergent, and ESL "
    "readers, as markdown for a Slack canvas. Use short sentences and clear section "
    "headings. Define jargon inline or in a short glossary. Never rely on color or "
    "emoji to carry meaning. Write at the reader's target reading grade and language.\n\n"
    "Work like an editor with a checker: draft the summary, then call the "
    "`audit_accessibility` tool on your draft. If the reading grade is above target, "
    "or it has overly long sentences, undefined jargon, or color-only references, "
    "revise and check again — but **audit at most twice**, then return your best "
    "version even if a metric is still slightly off.\n\n"
    "Always finish your turn by returning the final summary markdown — never end on a "
    "tool call without it, and never return an empty summary. No preamble or commentary "
    "about your process. The summary must contain only reader-facing content with "
    "section headings — never your audit notes, status updates, or words like 'revising'."
) + sanitize.INJECTION_GUARD

# Appended on a retry when the agent ended its turn on narration instead of the summary.
_RETRY_NUDGE = (
    "\n\nIMPORTANT: Return ONLY the finished summary markdown with clear section "
    "headings. Do not include audit notes, status updates, or words like 'revising'."
)

MAX_ITERATIONS = 8  # the agent must audit (up to ~twice) AND still emit its final summary;
# too low cuts it off mid-audit → empty digest. The wall-clock timeout in
# mcp_agent.run_loop is the real guard against a wedged MCP scorer.


def _looks_like_summary(md: str) -> bool:
    """A real digest has section headings or substantial length. The agent occasionally
    ends its turn on audit narration ("…revising now") instead of the summary; catch
    that so we retry/bail rather than publish a one-line non-summary as a canvas."""
    md = (md or "").strip()
    if not md:
        return False
    has_heading = any(ln.lstrip().startswith("#") for ln in md.splitlines())
    return has_heading or len(md.split()) >= 50


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
            f"check and improve your draft before you finish.\n\n{sanitize.fence(rts_context)}"
        )

        async def _attempt(extra: str = ""):
            return await mcp_agent.run_loop(
                settings, model=settings.model_digest, system=DIGEST_SYSTEM,
                user=user + extra, tools=tools, output_model=_Digest, field="markdown",
                max_tokens=4000, max_iterations=MAX_ITERATIONS, guard=guard, on_step=on_step,
            )

        md, tool_calls = await _attempt()
        if not _looks_like_summary(md):
            # The agent ended on audit narration instead of the summary — retry once
            # with a firmer instruction (this is intermittent; the retry usually fixes it).
            log.warning("digest returned a non-summary (%d chars) — retrying once",
                        len(md.strip()))
            md2, tc2 = await _attempt(_RETRY_NUDGE)
            tool_calls += tc2
            md = md2 if _looks_like_summary(md2) else max((md, md2), key=lambda s: len(s.strip()))

        if not _looks_like_summary(md):
            # Both attempts degenerate: return empty so the handler declines cleanly
            # rather than publishing a one-line non-summary canvas.
            log.warning("digest still a non-summary after retry — declining")
            return DigestResult(markdown="", grade=0.0, tool_calls=tool_calls)

        grade = await mcp_agent.score_grade(mcp, md)
    return DigestResult(markdown=md, grade=grade, tool_calls=tool_calls)
