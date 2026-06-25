<!-- Working title only — you name the project and write the submission copy. -->
# Slack Accessibility Co-pilot (working title)

Accessibility co-pilot for Slack: alt-text on images (Claude vision), plain-language
rewrites with a measurable readability before/after (custom MCP scorer), and a
"Catch me up, accessibly" Assistant agent that uses Real-Time Search to build a
screen-reader-friendly canvas digest.

## Status — all three core flows work live (2026-06-25)
| Flow | Trigger | Status |
|------|---------|--------|
| Alt-text on images | react 👁️ `:eyes:` on an image message | ✅ working |
| Proactive alt-text offer | post an image without alt text → ephemeral offer | ✅ working |
| Plain-language rewrite + grade before/after | react 🧩 `:jigsaw:` on a thread | ✅ working (e.g. grade 24.7 → 7.7) |
| "Catch me up, accessibly" → canvas | Assistant pane → "Catch me up accessibly on #channel" | ✅ working |

**Both required techs are load-bearing:** MCP (custom scorer over a real stdio
client→server session) and RTS (`assistant.search.context`).

## Required tech used
- **MCP** — `mcp_server/` is a FastMCP accessibility scorer; `llm/rewrite.py` calls it
  over a real stdio client→server session for the readability before/after.
- **Real-Time Search** — `slack_io/rts.py` (`assistant.search.context`) feeds the digest;
  the bot-token `action_token` comes from `payload["assistant_thread"]["action_token"]`.
- **Slack AI / Assistant** — `handlers/assistant.py`.

## Setup
Requires **Python 3.10+** (MCP needs it; system 3.9 is too old — use `python3.12`).
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # paste real tokens into .env (NOT .env.example)
python scripts/check_env.py # pre-flight: verifies creds + deps (one tiny Haiku call)
python app.py               # Socket Mode — no public URL needed
```
Run the MCP scorer standalone: `python -m mcp_server.server`

### Slack app config (api.slack.com/apps → your app)
- **OAuth scopes (bot):** `reactions:read`, `files:read`, `chat:write`, `assistant:write`,
  `search:read.public`, `canvases:write`, `channels:history`, `im:history`.
- **App-level token** with `connections:write` (Socket Mode).
- **Event Subscriptions → bot events:** `reaction_added`, `message.channels`, `message.im`.
- **Socket Mode:** On. **Interactivity & Shortcuts:** On (for buttons).
- **Agents & AI Apps:** On. **App Home → Messages tab:** On + "allow users to send messages."
- Invite the bot to a test channel (`/invite @your-app`). Reinstall after scope changes.

## Run / operate
- Run **exactly one** `app.py` instance — multiple instances make Slack round-robin
  events across sockets (flaky). To stop it, kill by PID (`pkill -f "python app.py"`
  does NOT match — the process shows the resolved interpreter path).
- Cost guardrails live in `guardrails.py`: SQLite `cost.db` ledger, `MAX_SPEND_USD`
  ceiling (default $8), `MAX_CALLS_PER_DAY` cap. Dev defaults to Haiku on the reacji
  paths; swap `model_alt_text`/`model_rewrite` to Opus in `config.py` for the final demo.

## Layout
| Path | Purpose |
|------|---------|
| `app.py` | Bolt app + Socket Mode (websocket-client backend) |
| `config.py` | env + model IDs + pricing + budget knobs |
| `guardrails.py` | spend ledger + pre-call budget check |
| `handlers/` | `reactions` (👁️/🧩), `proactive` (offer), `assistant` (RTS panel) |
| `llm/` | `alt_text` (vision), `rewrite` (MCP before/after), `digest` (streamed) |
| `slack_io/` | `files`, `messages`, `rts`, `canvas`, `blocks` |
| `prefs/` | SQLite — user settings ONLY (grade/language, no Slack content) |
| `mcp_server/` | FastMCP scorer (`server.py`) + pure scoring fns (`scoring.py`) |
| `scripts/` | `check_env.py` pre-flight |
| `seed/` | scripts to seed the demo sandbox |

## Remaining before submission
- Streamed plan/task steps (`chat.startStream`) for the Assistant — visual money-shot.
- Personalization beat: prefs language switch (re-run digest in Spanish on camera).
- Seed a text-rich demo channel; quiet debug logs; finalize architecture diagram.
- Record <3-min video; write submission copy (your voice); submit early (deadline Jul 13).

> Known runtime gotchas are documented in `handoff.md` → Progress.
