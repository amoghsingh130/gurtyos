"""Shared agentic-loop plumbing for the accessibility co-pilot.

Both load-bearing LLM flows — the plain-language rewrite and the "catch me up"
digest — are the *same* shape: open the custom accessibility MCP scorer over
stdio, expose its tools to Claude via `tool_runner`, and run a draft → audit →
revise loop until the output meets the reader's target. Keeping that logic (and
the deterministic scoring used for the on-camera before/after number) in one
place makes MCP genuinely load-bearing in one audited spot instead of two copies.
"""
from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager

import anthropic
from anthropic.lib.tools.mcp import async_mcp_tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Our FastMCP accessibility scorer, launched as a subprocess and spoken to over stdio.
_SERVER = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])


@asynccontextmanager
async def mcp_session():
    """Open a live client→server stdio session with the accessibility scorer."""
    async with stdio_client(_SERVER) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            yield mcp


async def agent_tools(mcp: ClientSession):
    """Wrap every MCP tool so `tool_runner` can call it inside the live session."""
    listed = await mcp.list_tools()
    return [async_mcp_tool(t, mcp) for t in listed.tools]


async def score_grade(mcp: ClientSession, text: str) -> float:
    """Deterministic Flesch-Kincaid grade via the MCP `score_readability` tool.
    Handles both the structuredContent and JSON content-block return shapes."""
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


async def run_loop(
    settings,
    *,
    model: str,
    system: str,
    user: str,
    tools,
    output_model,
    field: str,
    max_tokens: int,
    max_iterations: int,
    guard=None,
    on_step=None,
):
    """Run a draft → audit → revise `tool_runner` loop and return (text, tool_calls).

    The runner yields each assistant message (the final answer message included),
    so we record token usage + tool-call steps as we go and read the answer off the
    last message. `output_model` is a pydantic model with a single `field` string —
    API-enforced so no 'here is my rewrite…' preamble leaks onto screen.
    """
    async with anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key, max_retries=settings.anthropic_max_retries
    ) as client:
        runner = client.beta.messages.tool_runner(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=tools,
            max_iterations=max_iterations,
            output_format=output_model,
        )
        final = None
        tool_calls = 0
        async for message in runner:
            for blk in message.content:
                if getattr(blk, "type", None) == "tool_use":
                    tool_calls += 1
                    if on_step:
                        on_step(blk.name)
            if guard is not None and getattr(message, "usage", None) is not None:
                guard.record(model, message.usage)
            final = message
    return _extract(final, field), tool_calls


def _extract(message, field: str) -> str:
    """Pull the answer field out of the agent's final (structured) message."""
    parsed = getattr(message, "parsed", None)
    if parsed is not None:
        return getattr(parsed, field)
    raw = "".join(
        b.text for b in (message.content if message else [])
        if getattr(b, "type", None) == "text"
    ).strip()
    try:
        return json.loads(raw)[field]
    except (ValueError, KeyError, TypeError):
        return raw
