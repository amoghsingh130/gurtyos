"""Tests for the shared agentic-loop plumbing.

`_extract` is pure and tested with fakes. The stdio round-trip spins up the real
FastMCP scorer as a subprocess (no network, no API key) to prove the live
client→server path the agent relies on.
"""
import asyncio
import json
from types import SimpleNamespace

from llm.mcp_agent import _extract, mcp_session, score_grade


def _msg(parsed=None, blocks=None):
    return SimpleNamespace(parsed=parsed, content=blocks or [])


def _text_block(t):
    return SimpleNamespace(type="text", text=t)


def test_extract_prefers_parsed_object():
    msg = _msg(parsed=SimpleNamespace(text="hi there"))
    assert _extract(msg, "text") == "hi there"


def test_extract_parses_json_content():
    msg = _msg(blocks=[_text_block('{"text": "hello"}')])
    assert _extract(msg, "text") == "hello"


def test_extract_raw_fallback_when_not_json():
    msg = _msg(blocks=[_text_block("plain answer")])
    assert _extract(msg, "text") == "plain answer"


def test_extract_handles_none_message():
    assert _extract(None, "text") == ""


def test_mcp_stdio_roundtrip():
    """The agent reaches the scorer over a real stdio session — exercise it directly."""
    async def go():
        async with mcp_session() as mcp:
            grade = await score_grade(mcp, "The cat sat on the mat.")
            res = await mcp.call_tool(
                "audit_accessibility", {"text": "Per the SLA, click the items in red."})
            data = json.loads(res.content[0].text)
            return grade, data

    grade, data = asyncio.run(go())
    assert isinstance(grade, float)
    assert "color_only_refs" in data
    assert data["color_only_refs"]  # "in red" flagged
