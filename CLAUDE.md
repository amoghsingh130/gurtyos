# CLAUDE.md — orientation for a new session

**Project:** **gurtYos** — an accessibility co-pilot for Slack (Slack Agent Builder Challenge,
*Agent for Good* track). It describes images, rewrites jargon into plain language with a
measurable readability before/after, catches you up accessibly, and reports + fixes a whole
channel's accessibility. Public repo: https://github.com/amoghsingh130/gurtyos

**State:** Feature-complete and tested. Remaining work is demo + submission (video,
screenshots, Slack config), **not code**. Source of truth: `README.md` (setup/config),
`handoff.md` (build log + gotchas + remaining), `DEMO.md` (video script + Devpost copy).

## Run / test
```bash
source .venv/bin/activate            # Python 3.12 venv
python app.py                        # Socket Mode; run EXACTLY ONE instance
python -m pytest -q                  # 55 fast offline tests
RUN_LLM_TESTS=1 python -m pytest tests/test_llm_integration.py -q   # live LLM/MCP
python -m scripts.selftest <SCRATCH_CHANNEL_ID>   # headless live drive (posts then purges)
```
Stop the app: `pkill -if "python app.py"` (case-insensitive — the process shows the resolved
`…/Python app.py` path, so plain `-f "python app.py"` misses it).

## Architecture (where things live)
- `handlers/` — `reactions` (👁️ alt text, 🧩 rewrite, 👎 learning loop), `proactive` (offers),
  `assistant` (catch-up digest, channel report, "fix this channel"), `home` (App Home).
- `llm/` — `alt_text`, `rewrite`, `digest`, `mcp_agent` (shared draft→audit→revise tool_runner loop).
- `mcp_server/` — FastMCP accessibility scorer + pure, tested `scoring.py`.
- `slack_io/` — `messages`, `rts`, `canvas`, `blocks`, `stream` (live task steps), `files`,
  `channels` (mention/`#name`→id resolver), `purge` (delete the bot's own messages).
- `tests/fakes.py` — fake Slack client for integration tests.

## Key facts & gotchas (don't relearn)
- **Models:** digest = `claude-sonnet-4-6` (set `MODEL_DIGEST=claude-opus-4-8` for the final
  recording); rewrite/alt-text = Haiku. All env-overridable. `ANTHROPIC_MAX_RETRIES=5` (529s).
- **Catch-up retrieval:** named-channel catch-up reads `conversations.history` (reliable); RTS
  (`assistant.search.context`) powers the topical/no-channel path. RTS is a *search* and
  starves a generic "catch me up" query — don't route channel catch-up through it.
- **Channel resolution (`slack_io/channels.py`):** catch-up/report/fix resolve a channel from
  either a `<#C…|name>` mention **or a plain typed `#name`** (needs `channels:read` for the
  `conversations.list` lookup). A named-but-unresolved channel gives a clear "couldn't find it"
  error — distinct from the empty-channel "not enough activity" message. Without `channels:read`,
  only the blue autocompleted mention works.
- **Catch-up logic is in module-level `_run_catch_up`** (not the `on_user_message` closure) so it's
  unit-testable; `on_user_message` just dispatches purge → report → fix → catch-up.
- **Three required techs are load-bearing** (Assistant + custom MCP + RTS) — the tie-breaker claim.
- **`ENABLE_TASK_STREAM` on by default** (live audit-pass streaming; degrades to status text).
- **Demo channel:** `C0BD2PX1753` (in `DEMO_CHANNELS`), workspace **gurtYo**. Seed it with
  `python -m seed.seed_channel C0BD2PX1753 --clean`.
- Socket Mode uses the `websocket-client` backend (built-in client loops on macOS).
- `guardrails.calls_today()` uses UTC to match `record()`.

## Working preferences
- **Commits: NO `Co-Authored-By: Claude` trailer** (standing user instruction).
- The user names the project and writes the final submission copy — don't AI-write the Devpost
  description.

## Remaining before submission
Capture 3 Home-tab feature screenshots → wire raw URLs in `handlers/home.py:HOME_IMAGES`;
in Slack config add `chat:write.customize` + `channels:read` (the latter also enables plain
`#name` catch-up/report, not just real channel names) and enable the Home tab; record the
<3-min video (`DEMO.md`); finalize Devpost copy + impact statement; grant test access; submit early.
