"""Plain-language rewrite with a measurable readability before/after.

Pipeline (all three steps run per request):
  1. score the original via the custom MCP scorer  -> grade_before
  2. Claude rewrites at the user's target grade / language
  3. score the rewrite via the MCP scorer          -> grade_after

The MCP scorer (mcp_server/server.py) is reached over a real stdio client→server
session, so MCP is genuinely load-bearing — not a library import. Scoring both
ends deterministically guarantees the before/after numbers on ANY content (the
reliability point of this concept), independent of model behavior.

The MCP SDK is async, so the work runs in a private event loop via asyncio.run();
the Slack handler calls the sync `plain_language()` wrapper.
"""
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config import Settings

REWRITE_SYSTEM = (
    "You rewrite jargon-heavy Slack threads into plain language for neurodivergent "
    "and ESL readers. Preserve every concrete fact, name, number, decision, and "
    "action item — simplify the wording, never the substance. Short sentences. "
    "Define unavoidable terms inline. Output only the rewrite, no preamble."
)


@dataclass
class RewriteResult:
    text: str
    grade_before: float
    grade_after: float
    language: str


def plain_language(
    settings: Settings,
    original: str,
    target_grade: int = 6,
    language: str = "English",
    guard=None,
) -> RewriteResult:
    if guard is not None:
        guard.check()  # raises BudgetExceeded if over the spend ceiling / daily cap
    return asyncio.run(_run(settings, original, target_grade, language, guard))


async def _run(settings, original, target_grade, language, guard) -> RewriteResult:
    # Launch our FastMCP scorer as a subprocess and talk to it over stdio.
    server = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            grade_before = await _score(mcp, original)
            rewrite = _rewrite(settings, original, target_grade, language, guard)
            grade_after = await _score(mcp, rewrite)
    return RewriteResult(
        text=rewrite, grade_before=grade_before, grade_after=grade_after, language=language
    )


async def _score(mcp: ClientSession, text: str) -> float:
    """Call the MCP score_readability tool and pull out the Flesch-Kincaid grade."""
    res = await mcp.call_tool("score_readability", {"text": text})
    sc = getattr(res, "structuredContent", None)
    if isinstance(sc, dict):
        if "grade" in sc:
            return float(sc["grade"])
        inner = sc.get("result")
        if isinstance(inner, dict) and "grade" in inner:
            return float(inner["grade"])
    for block in getattr(res, "content", []) or []:
        txt = getattr(block, "text", None)
        if txt:
            return float(json.loads(txt)["grade"])
    raise RuntimeError("MCP scorer returned no grade")


def _rewrite(settings: Settings, original: str, target_grade: int, language: str, guard) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.model_rewrite,
        max_tokens=1500,
        system=REWRITE_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Rewrite the following at roughly a US grade-{target_grade} reading level, "
                f"in {language}.\n\n{original}"
            ),
        }],
    )
    if guard is not None:
        guard.record(settings.model_rewrite, msg.usage)
    return "".join(b.text for b in msg.content if b.type == "text").strip()
