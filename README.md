# gurtYos — an accessibility co-pilot for Slack

Slack, made readable for the teammates it leaves behind. **gurtYos** describes images,
rewrites jargon into plain language with a measurable readability before/after, and
catches you up accessibly — and it *measures* every fix, so the difference is a number,
not a claim. Built for the Slack Agent Builder Challenge, **Agent for Good** track.

## What it does
| Capability | Trigger | Notes |
|---|---|---|
| **Alt text on images** | react 👁️ `:eyes:` on an image | Claude vision → screen-reader-quality alt text in-thread |
| **Proactive alt-text offer** | post an image with no alt text | ephemeral "Describe this image?" — the agent acts unprompted |
| **Plain-language rewrite** | react 🧩 `:jigsaw:` on a thread | reading grade *before → after* + impact line (acronyms defined, sentences split). 👎 makes it simpler **and remembers** your level |
| **Proactive rewrite offer** | a hard/jargon thread in a `DEMO_CHANNELS` channel | the agent notices and offers to fix it, unprompted |
| **Catch me up, accessibly** | Assistant: *"catch me up on #channel"* | reads recent history → screen-reader-friendly **canvas** digest, in your language; streams the agent's audit passes live |
| **Channel accessibility report** | Assistant: *"accessibility report on #channel"* | whole-channel score *current → projected-after-fixes* (ADA/508 framing) + a **"Fix this channel"** button that applies fixes channel-wide |
| **Natural-language prefs** | *"now in Spanish"*, *"set my reading level to 5"* | parsed, persisted, applied to future output |
| **App Home** | click the app | a formatted, fully alt-texted intro + guide |

## The three required techs are load-bearing
Remove any one and a flow breaks:
- **Slack Assistant** (`handlers/assistant.py`) — the co-pilot surface + live plan/task streaming.
- **Custom MCP server** (`mcp_server/`) — a FastMCP accessibility scorer (Flesch-Kincaid grade,
  WCAG contrast, jargon/long-sentence audit). The rewrite and digest run a real `tool_runner`
  **draft → audit → revise** loop against it over a live stdio session.
- **Real-Time Search** (`slack_io/rts.py`, `assistant.search.context`) — powers the topical /
  cross-channel catch-up path (named-channel catch-up reads history directly for reliability).

## Setup
Requires **Python 3.10+** (MCP needs it).
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # paste real tokens into .env (NOT .env.example)
python scripts/check_env.py # pre-flight: verifies creds + deps
python app.py               # Socket Mode — no public URL needed
```
Run the MCP scorer standalone: `python -m mcp_server.server`

### Slack app config (api.slack.com/apps → your app)
- **Bot scopes:** `reactions:read`, `files:read`, `chat:write`, `assistant:write`,
  `search:read.public`, `canvases:write`, `channels:history`, `im:history`.
  *Recommended extras:* `channels:read` (real channel names in the report),
  `chat:write.customize` (multi-persona demo seeding).
- **App-level token** with `connections:write` (Socket Mode).
- **Event Subscriptions → bot events:** `reaction_added`, `message.channels`, `message.im`,
  `app_home_opened`.
- **Socket Mode:** On · **Interactivity & Shortcuts:** On (buttons) · **Agents & AI Apps:** On.
- **App Home:** Messages tab On (+ allow messages); **Home tab On**.
- Invite the bot to your channels (`/invite @gurtYos`). Reinstall after scope changes.

## Configuration (`config.py` / `.env`)
| Knob | Default | Purpose |
|---|---|---|
| `MODEL_DIGEST` | `claude-sonnet-4-6` | digest model (set `claude-opus-4-8` for the final recording) |
| `MODEL_REWRITE` / `MODEL_ALT_TEXT` | `claude-haiku-4-5` | reacji-path models |
| `ANTHROPIC_MAX_RETRIES` | 5 | transient 529 ("overloaded") self-heal |
| `ENABLE_TASK_STREAM` | true | stream the agent's audit passes live (degrades to status text) |
| `DEMO_CHANNELS` | — | allow-list for the proactive rewrite offer (empty = off) |
| `MAX_SPEND_USD` / `MAX_CALLS_PER_DAY` | 8 / 300 | spend ledger guardrails (`guardrails.py`) |

## Run / operate
Run **exactly one** `app.py` instance — multiple connected sockets make Slack round-robin
events (flaky). The process shows the resolved interpreter path, so kill it with a
case-insensitive match: `pkill -if "python app.py"`.

## Layout
| Path | Purpose |
|---|---|
| `app.py` | Bolt app + Socket Mode (websocket-client backend) |
| `config.py` / `guardrails.py` | env + models + pricing; spend ledger + budget check |
| `handlers/` | `reactions` (👁️/🧩 + 👎 loop), `proactive` (offers), `assistant` (digest, report, fix), `home` (App Home) |
| `llm/` | `alt_text`, `rewrite`, `digest`, `mcp_agent` (shared draft→audit→revise loop) |
| `slack_io/` | `files`, `messages`, `rts`, `canvas`, `blocks`, `stream` (live task steps) |
| `mcp_server/` | FastMCP scorer (`server.py`) + pure, tested scoring (`scoring.py`) |
| `prefs/` | SQLite — user settings ONLY (grade/language, no Slack content) |
| `seed/` | `seed_channel.py` — seed a believable demo channel (`--clean` to re-seed) |
| `assets/` | `home-banner.png` + `make_banner.py` |
| `tests/` | pure + integration (`fakes.py` fake Slack client) + gated live LLM/MCP |
| `DEMO.md` | demo video script, Devpost copy, pitch + soundbites |

## Tests
```bash
python -m pytest -q                                   # 43 fast offline tests
RUN_LLM_TESTS=1 python -m pytest tests/test_llm_integration.py -q   # live LLM/MCP
```

## Demo & submission
See **`DEMO.md`** for the <3-min video script, Devpost copy, and pitch. Repo:
https://github.com/amoghsingh130/gurtyos · runtime gotchas in `handoff.md`.
