"""Plain-language rewrite via tool_runner: Claude calls the MCP readability scorer
on the original, rewrites at the user's target grade/language, then scores the
rewrite -> returns rewrite + (grade_before, grade_after).

Wires the local stdio MCP server (mcp_server/server.py) to Claude via
anthropic.lib.tools.mcp. Pin exact tool_runner API against the SDK during build.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import Settings


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
) -> RewriteResult:
    # TODO (Days 8-9): build the local stdio MCP session, register score_readability
    # as a Claude tool, and run client.beta.messages.tool_runner(...) so Claude:
    #   1. calls score_readability(original)         -> grade_before
    #   2. rewrites at target_grade in `language`
    #   3. calls score_readability(rewrite)          -> grade_after
    # Return RewriteResult. See mcp_server/server.py for the tool contract.
    raise NotImplementedError
