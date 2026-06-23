<!-- Working title only — you name the project and write the submission copy. -->
# Slack Accessibility Co-pilot (working title)

Accessibility co-pilot for Slack: alt-text on images (Claude vision), plain-language
rewrites with a measurable readability before/after (custom MCP scorer), and a
"Catch me up, accessibly" Assistant agent that uses Real-Time Search to build a
screen-reader-friendly canvas digest.

## Required tech used
- **MCP** — `mcp_server/` exposes accessibility-scoring tools Claude calls via tool_runner.
- **Real-Time Search** — `slack_io/rts.py` (`assistant.search.context`) feeds the digest.
- **Slack AI / Assistant** — `handlers/assistant.py`.

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in tokens
python app.py               # Socket Mode — no public URL needed
```

Run the MCP scorer standalone (used by the rewrite flow):
```bash
python -m mcp_server.server
```

## Layout
| Path | Purpose |
|------|---------|
| `app.py` | Bolt app + Socket Mode entry point |
| `config.py` | env + model IDs |
| `handlers/` | reacji, proactive offer, Assistant panel |
| `llm/` | alt-text, rewrite (tool_runner), digest (streamed) |
| `slack_io/` | files, messages, RTS, canvas, Block Kit |
| `prefs/` | SQLite — user settings ONLY (no Slack content) |
| `mcp_server/` | FastMCP accessibility scorer + pure scoring fns |
| `seed/` | scripts to seed the demo sandbox |

## Build order (see handoff.md / plan for the day-by-day)
1. Sandbox + paid AI features + **verify RTS availability** + pin API signatures.
2. Bolt skeleton responds in Socket Mode.
3. Alt-text vertical slice (no RTS/MCP dependency).
4. Plain-language rewrite + MCP before/after.
5. Assistant + RTS + canvas digest.
6. Proactive offer, prefs, feedback, seed, polish, video, submit.

> Items marked `TODO` / `raise NotImplementedError` are intentional stubs. Several
> Slack API signatures (`assistant.search.context`, `canvases.*`, plan/task-step
> blocks) must be pinned against docs.slack.dev on Day 1 — they're flagged inline.
