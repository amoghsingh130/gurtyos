"""Isolated reproduction for the MCP scorer stdio deadlock.

Symptom (seen live): during a 🧩 rewrite the draft→audit→revise loop completes ~3 LLM
passes, then the 4th MCP `call_tool` never returns — the app sits at 0% CPU, blocked on
the stdio pipe, and nothing posts.

This script takes the Anthropic SDK / tool_runner out of the picture entirely: it opens a
single `mcp_session()` and calls the scorer tools in a tight loop. If it wedges here, the
bug is in the `mcp` stdio transport (or the FastMCP server). If this runs clean to the end
but the live rewrite still wedges, the fault is in the `anthropic` tool_runner integration
(`async_mcp_tool`) instead.

    python -m scripts.repro_mcp            # default 8 iterations
    python -m scripts.repro_mcp 20         # stress it harder

Each line prints as soon as the call returns, so a hang is obvious: the counter stops and
the process idles. Ctrl-C to abort.
"""
from __future__ import annotations

import asyncio
import sys
import time

from llm.mcp_agent import mcp_session, score_grade

# A long run-on jargon sentence like the one that triggered the wedge in the demo channel.
SAMPLE = (
    "Per the SLA the API KPIs must be reconciled against the EOD ETL pipeline before the "
    "QBR, and stakeholders expect the RCA documentation finalized notwithstanding the "
    "aforementioned dependencies which materially impact the downstream deliverables "
    "across the organization and its partner teams."
)


async def main(iterations: int) -> None:
    async with mcp_session() as mcp:
        print(f"session open; calling score_readability {iterations}x …", flush=True)
        for i in range(1, iterations + 1):
            t0 = time.monotonic()
            grade = await score_grade(mcp, f"{SAMPLE} (pass {i})")
            dt = time.monotonic() - t0
            print(f"  call {i:>2}: grade={grade:.1f}  ({dt:.2f}s)", flush=True)
            if dt > 10:
                print("  ⚠️  that call was suspiciously slow — near the wedge threshold")
    print("done — no deadlock at the transport layer.", flush=True)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    asyncio.run(main(n))
