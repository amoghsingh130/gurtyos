"""Accessibility-scoring MCP server (FastMCP, stdio).

This is the second load-bearing required tech (MCP). Claude calls these tools via
tool_runner during the plain-language rewrite to produce a credible reading-grade
before/after. Run standalone:  python -m mcp_server.server
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server import scoring

mcp = FastMCP("accessibility-scorer")


@mcp.tool()
def score_readability(text: str) -> dict:
    """Reading grade (Flesch-Kincaid) and estimated reading time for `text`."""
    return {
        "grade": scoring.flesch_kincaid_grade(text),
        "reading_seconds": scoring.reading_seconds(text),
    }


@mcp.tool()
def wcag_contrast(fg_hex: str, bg_hex: str) -> dict:
    """WCAG contrast ratio between two hex colors, with AA/AAA pass flags."""
    ratio = scoring.wcag_contrast(fg_hex, bg_hex)
    return {"ratio": ratio, "passes_aa": ratio >= 4.5, "passes_aaa": ratio >= 7.0}


@mcp.tool()
def reading_time(text: str) -> dict:
    """Estimated reading time in seconds for `text`."""
    return {"reading_seconds": scoring.reading_seconds(text)}


@mcp.tool()
def audit_accessibility(text: str) -> dict:
    """Full accessibility audit of `text`: reading grade, reading time, overly long
    sentences, undefined jargon/acronyms, and color-only references. The agent uses
    these concrete findings to revise its draft until it is accessible."""
    return scoring.audit(text)


if __name__ == "__main__":
    mcp.run()
