# Slack Agent Builder Challenge — Handoff

**Platform:** Devpost — https://slackhack.devpost.com
**Sponsor:** Salesforce, Inc. · **Administrator:** Devpost, Inc.
**Status:** Direction chosen + full build plan ready. **Not started building.** (Greenfield repo — only this file.)

---

## TL;DR — what we're doing
- **Track:** **Slack Agent for Good** ($8k / $4k).
- **Concept (working label, you name the final):** an **accessibility co-pilot for Slack itself** — an agent
  that fixes Slack's own inaccessibility for blind/low-vision, neurodivergent, and ESL users.
- **Why this one:** highest *expected* win — it can take **For-Good 1st OR the Best UX achievement prize**
  (two shots), the demo is visceral and works on arbitrary content (robust to off-script judges), the impact
  story is unimpeachable (accessibility is an explicitly listed area), and it's a **less-crowded track** than
  the marquee "New Slack Agent." Hardened so **two of the three required techs (RTS + MCP) are load-bearing**,
  which erases its one weakness (tech ceiling) vs the runner-up idea.
- **Three load-bearing flows:** (1) **alt-text** on images via Claude vision (reacji + proactive), (2)
  **plain-language rewrite** of jargon threads with a **measurable readability before/after** from a custom
  **accessibility-scoring MCP server**, (3) **"Catch me up, accessibly"** — an Assistant-panel agent that uses
  the **RTS API** to build a screen-reader-friendly **canvas** digest, streamed with visible plan/task steps.
- **Your rules honored:** *you* name the project and *you* write the submission description. This doc uses
  working labels only.

---

## Key Dates (Pacific Time — Sponsor's clock is official)
- **Submission Period:** Wed May 20, 2026 (10:00 AM PT) → **Mon Jul 13, 2026 (5:00 PM PT)**
- **Judging Period:** Jul 14, 2026 (11:00 AM PT) → Aug 6, 2026 (11:00 AM PT)
- **Winners Announced:** ~Tue Aug 11, 2026 (2:00 PM PT)
- **Today:** 2026-06-23 → **~20 days left to submit.**

## Eligibility (relevant to me)
- Must be 18+ and legal resident of an eligible country. **US is eligible** (incl. DC). ✅
- I'm a Georgia Tech student (asingh3206@gatech.edu) — eligible as an individual.
- Teams up to 4 people. Solo entry allowed. → **Decision: solo.**
- **Not eligible:** Salesforce employees/contractors (past 2 yrs), gov employees, judges. Not me.

---

## What to Build
An app that uses **at least ONE** of these three technologies:
1. **Slack AI capabilities** (Slack Agent Builder, `slack create agent`)
2. **MCP server integration**
3. **Real-Time Search (RTS) API**

...AND fits **at least ONE track**.

## Tracks (pick one)
| Track | Requirement | Prize (1st / 2nd) |
|---|---|---|
| **New Slack Agent** | New agent, automate workflows / surface insights | $8,000 / $4,000 |
| **Slack Agent for Good** ← **CHOSEN** | New agent + real social-impact problem (accessibility, education, econ opportunity, environment, public health, nonprofit ops). **Must explain impact.** | $8,000 / $4,000 |
| **Slack Agent for Organizations** | New OR significantly-updated existing agent, **submitted to Slack Marketplace before deadline**. Needs Slack App ID. | $8,000 / $4,000 (+ exec chat, Stack Overflow podcast feature) |

**Achievement prizes ($2,000 each):** Best UX, Most Innovative Slack Agent, Best Technological Implementation.
(1st/2nd winners are NOT eligible for achievement prizes — one prize per submission. So build one project
polished enough to win *either* pool; let the judges sort it.)

**Why For Good over the marquee track:** avoids the Marketplace hurdle (Organizations), is less crowded than
"New Slack Agent," and the accessibility angle gives a clean impact narrative + a second shot at Best UX.

---

## Judging Criteria (equally weighted)
1. **Technological Implementation** — quality software; must leverage ≥1 of the 3 techs; code quality.
2. **Design** — UX thought-through; balanced frontend + backend.
3. **Potential Impact** — impact on Slack community and beyond.
4. **Quality of the Idea** — creativity, uniqueness, improvement over existing concepts.

Stage 1 = pass/fail viability check. Stage 2 = scored on the 4 criteria above.

---

## Submission Checklist (all tracks)
- [ ] Register on Devpost ("Join Hackathon") + Devpost account.
- [ ] Join the **Slack Developer Program** → get Slack developer sandbox.
- [ ] Build the Project (must install & run consistently; function as shown in video).
- [ ] **Text description** — features & functionality. *(Write in my own voice — not AI.)*
- [ ] **Agent for Good only:** explain the impact in the submission form.
- [ ] **Demo video** — <3 min, shows the project working, public on YouTube/Vimeo/Facebook/Youku, link on form. No copyrighted music/3rd-party marks without permission. English (or English translation).
- [ ] **Architecture diagram.**
- [ ] **URL to Slack developer sandbox** + grant test access to **slackhack@salesforce.com** AND **testing@devpost.com**.
- [ ] **Organizations track only:** Slack App ID (+ describe updates if updating existing app). *(N/A — we're For Good.)*
- [ ] Original work, solely owned, no IP violations.

### Notes / gotchas
- Video judged only up to 3 min — front-load the working demo.
- Can submit multiple distinct projects; can be on multiple teams.
- After Submission Period: no edits except Sponsor-permitted IP/PII fixes.
- Report security issues to security@salesforce.com (do NOT disclose publicly).
- Support: support@devpost.com.

---

# Strategy — how we got here

## The winning formula (apply to whichever idea)
1. **Make RTS or MCP load-bearing** — the product is impossible without it (not a bolted-on chatbot).
2. **Show the agent think** — plan blocks + live task steps = the "wow" and the Best-UX edge.
3. **Produce an artifact** — a canvas the judge can see being created = tangible impact on screen.
4. **Pick a pain that's universal or undeniably good** — covers Impact + Quality-of-Idea.
5. **Avoid the obvious** — "summarize my channel / standup bot / Q&A over docs" is what most of the 2,600+
   entrants will build (Slack itself lists these as examples). Reframe past them.

## Platform capabilities (what's actually possible — grounds the ideas)
- **RTS API** (`assistant.search.context`): semantic + keyword search across messages, files, users, channels
  the user can see; returns surrounding **context messages**; permission-aware. **Hard constraint: may not
  store/copy/train on retrieved data** → query at request time, no persistent index. Bot-token path needs an
  `action_token` from the triggering event; "internal"/directory-published apps only (a sandbox internal app
  qualifies). Scopes: `search:read.public` (+ `.private`/`.im`/`.mpim` for user tokens).
- **Slack MCP server**: exposes Slack as tools (search, post, manage canvas/users). Separately, *your* agent can
  call **other MCP servers** for external data/actions (this is how we make MCP load-bearing).
- **Agent surfaces (the UX palette that wins Design):** Assistant panel, suggested prompts, **plan blocks**
  (show the multi-step plan), **task-update steps** (in_progress/completed/error), streaming markdown,
  interactive Block Kit, feedback buttons, and **canvas** as a tangible artifact.
- **Build stack:** Bolt for Python; Developer Program sandbox covers paid-plan AI features.

## Idea brainstorm (the full menu we considered)

### Track A — New Slack Agent ($8k)
- **A1 — Decision-provenance agent ("decision archaeology").** Ask "why did we deprecate v1?" → RTS reconstructs
  the *actual* decision (debate thread, who weighed in, final call, date, permalinks) → renders a **Decision
  Record canvas** with citations; stretch: flag contradicting decisions. RTS = the whole product; novel framing;
  universal pain; gorgeous canvas demo. **Highest tech/idea ceiling — the runner-up.**
- **A2 — Open-loops / commitment agent.** Finds promises made in Slack ("I'll send it Friday") never closed,
  drafts one-click follow-ups. Emotionally resonant; best "Most Innovative" wildcard.
- **A3 — Blocker / unanswered-question radar** for project channels. Solid but more dashboard-y and closer to
  Slack's own examples. Fallback.

### Track B — Slack Agent for Good ($8k)
- **B1 ★ Accessibility co-pilot for Slack itself — CHOSEN.** Alt-text + plain-language + accessible RTS digest.
  Double-threat (For-Good 1st OR Best UX); visceral demo; unimpeachable impact; fresh framing (accessibility
  *of the tool itself*).
- **B2 — Mutual-aid / crisis coordination.** RTS matches "need 20 meals Sat" to prior volunteer offers; live
  needs-board canvas. Powerful on video; more demo-workspace staging required.
- **B3 — Private burnout companion** (leans on MoodMap experience). Opt-in DM check-ins, aggregate-only, never
  scans others. Strong narrative/personal-fit, but RTS less load-bearing — a story play more than a tech play.

## Decision: A1 vs B1 pressure-test → **B1 (hardened)**
| | A1 — Decision provenance | B1 — Accessibility co-pilot ← chosen |
|---|---|---|
| Demo robustness | One beat (ask→document); magic depends on a seeded workspace | Multiple instant, visceral beats; **works on the judge's own arbitrary content** |
| Track crowding | Marquee, most entries; RTS-search is the *expected* mechanic | Few build accessibility; **two prize shots** (For-Good 1st OR Best UX) |
| Criteria ceiling | Highest **Tech** + Idea | Highest **Design/UX** + **Impact** |
| 20-day risk | Medium (contradiction-detection is hard) | Low — features independent + degrade gracefully |
| One-line judge memory | "an RTS search bot with a pretty output" (risk) | "Slack itself is inaccessible — I fixed it" (sticky) |

**Call:** go **B1**, but **harden its tech story** so we don't concede the Tech-Implementation criterion —
make it genuinely agentic (proactive alt-text), add an **external MCP server** that scores readability/contrast
(measurable "grade 14→6"), and lean on **plan-blocks + canvas** for the UX money-shot. Captures B1's safety
*and* A1's tech-flex, and makes **RTS + MCP both load-bearing**. A1 stays on file as the pivot if you'd rather
take the marquee track + max tech-flex.

---

# Build Plan (engineering)

## Tech stack (decided)
- **Bolt for Python** + **Socket Mode** (`SocketModeHandler`) → no public URL, no ngrok. App installed as an
  **internal** app in a **Slack Developer Program sandbox** (covers paid AI features; internal app qualifies for RTS).
- **Anthropic Python SDK** (`anthropic`, install `anthropic[mcp]`). Models (default Opus 4.8 per Anthropic
  guidance; Sonnet noted where reacji latency matters):
  - Alt-text (vision) → `claude-opus-4-8` (swap to `claude-sonnet-4-6` for snappier reacji latency).
  - Plain-language rewrite → `claude-opus-4-8` via **tool-runner** (Claude calls the MCP scorer).
  - Digest synthesis → `claude-opus-4-8`, `thinking={"type":"adaptive"}` + `output_config={"effort":"high"}`,
    **streamed** (`client.messages.stream(...)` → `get_final_message()`; large output ⇒ stream to avoid timeouts).
- **Custom MCP server** (Python `mcp` / FastMCP) for accessibility scoring. Wire to Claude via
  `anthropic.lib.tools.mcp` (`mcp_tool`) + `client.beta.messages.tool_runner(...)` over a **local stdio** session
  — self-contained, nothing exposed. (Alt: remote MCP connector — `mcp_servers=[{type:"url",...}]` +
  `tools=[{type:"mcp_toolset", mcp_server_name}]`, beta `mcp-client-2025-11-20` — only if you host it publicly.)
- **Prefs store**: SQLite. Stores **only user settings** (reading level / language), **never Slack content**
  (RTS no-storage rule). RTS queried at request time; the canvas holds your synthesized output (allowed).

## Module layout
```
app.py                    # Bolt(App) + Socket Mode; register Assistant; wire events
config.py                 # env: SLACK_BOT_TOKEN, SLACK_APP_TOKEN, ANTHROPIC_API_KEY; model IDs
handlers/
  reactions.py            # @app.event("reaction_added"): 👁️ alt-text, 🧩 plain-language
  proactive.py            # @app.event("message"): image posted w/o alt text → ephemeral offer
  assistant.py            # Assistant(): thread_started, suggested prompts, "catch me up" user_message
llm/
  alt_text.py             # vision → alt text (base64 image block)
  rewrite.py              # plain-language rewrite + MCP before/after via tool_runner
  digest.py               # RTS results → accessible digest (streaming, effort=high)
slack_io/
  files.py                # download url_private_download bytes w/ bot token; mimetype → media_type
  messages.py             # fetch reacted message/thread (conversations_history latest=ts / replies)
  rts.py                  # assistant.search.context (query, action_token, content_types, channel_types)
  canvas.py               # canvases_create / canvases_edit → accessible markdown canvas
  blocks.py               # Block Kit: plan blocks, task-update steps, feedback buttons
prefs/store.py            # SQLite user prefs only (reading level / language) — NO Slack content
mcp_server/
  server.py               # FastMCP: score_readability(text), wcag_contrast(fg,bg), reading_time(text)
  scoring.py              # textstat (Flesch-Kincaid grade) + WCAG contrast math
seed/                     # scripts to seed the demo sandbox (chatter, un-alt-texted images, dense thread)
architecture.(md|png)     # required submission diagram
```

## Flow wiring (the load-bearing details)
**1. Alt-text (reacji 👁️ + proactive)** — scopes `reactions:read`, `files:read`, `chat:write`.
- `reaction_added` → from `event.item.channel`+`ts`, fetch the message (`conversations_history` with
  `latest=ts, oldest=ts, inclusive=True, limit=1`); for each `file` GET `url_private_download` with header
  `Authorization: Bearer {bot_token}`; base64 the bytes; call Claude vision:
  `messages.create(model=..., messages=[{role:"user","content":[{type:"image","source":{type:"base64",
  "media_type":file["mimetype"],"data":b64}},{type:"text","text":ALT_TEXT_PROMPT}]}])`; post the alt text as a
  threaded reply.
- Proactive: subscribe to `message` events; if a posted image has no alt text, post an **ephemeral** offer
  ("Describe this image? 👁️") → button triggers the same path. Turns the tool into an *agent*.

**2. Plain-language rewrite (reacji 🧩)** — fetch full thread (`conversations_replies`), then a `tool_runner`
loop where Claude (a) calls MCP `score_readability` on the original, (b) rewrites at the user's target
grade/language, (c) calls `score_readability` on the rewrite → returns the rewrite **plus the grade
before/after** ("reading grade 14 → 6"). Post in-thread with feedback buttons.

**3. "Catch me up, accessibly" (Assistant panel)** — `from slack_bolt import Assistant`; `@assistant.thread_started`
sets suggested prompts ("Catch me up accessibly on #channel", "Explain this thread simply"); `@assistant.user_message`
runs: **RTS** `assistant.search.context` (pass the event's `action_token`; `content_types=["messages","files"]`,
timeframe via `after`) → `digest.py` synthesizes a structured, screen-reader-friendly summary (short sentences,
headed sections, jargon glossary, no color-only meaning) → render a **canvas** (`canvases_create` + `canvases_edit`,
scope `canvases:write`). Stream **plan blocks + task-update steps** (`set_status` + Block Kit) so judges watch it
work, then drop the canvas link. Personalization: read grade/language from `prefs/store.py`.

**MCP server** — `mcp_server/server.py` (FastMCP, stdio): `score_readability(text)→{grade, reading_seconds}`
(textstat Flesch-Kincaid), `wcag_contrast(fg_hex,bg_hex)→ratio`, `reading_time(text)`. Second load-bearing
required tech (MCP) + supplies the credible before/after numbers.

> **Pin these against docs.slack.dev on Day 1** (named correctly here, but verify exact arg names before
> building on them): `assistant.search.context` params + the bot-token `action_token` requirement; `canvases.*`
> field names; the Block Kit shapes for plan blocks / task-update steps (docs.slack.dev/ai/developing-agents).

## Architecture diagram (for the required submission field)
```
Slack sandbox workspace
   │  events / reacji / assistant_thread_started / message.im   (Socket Mode — no public URL)
   ▼
Bolt-for-Python app  ──►  Claude API  (vision + rewrite + digest synthesis, streamed)
   │  ├──► RTS API  (assistant.search.context)                  ← "catch me up"
   │  ├──► Accessibility-Scoring MCP server (local stdio)        ← readability/contrast before-after
   │  └──► Slack Web API (conversations.*, files.read, chat.postMessage, canvases.*)
   ▼
Prefs store (SQLite) — USER SETTINGS ONLY, never Slack content   ← compliance line (RTS no-storage)
```

## Demo video (<3 min, front-loaded — shot-by-shot)
- 0:00–0:15 problem one-liner (Slack is full of un-alt-texted images + jargon walls; millions locked out) → cut straight to product.
- 0:15–0:45 react 👁️ → instant alt text; post a new image → **proactive** offer (agentic).
- 0:45–1:20 react 🧩 on a dense jargon thread → plain-language rewrite + **MCP grade 14→6**.
- 1:20–2:15 "Catch me up, accessibly" → **plan blocks + task steps** stream → **accessible digest canvas** built live (money-shot).
- 2:15–2:40 personalization (switch language → Spanish, re-run) + feedback buttons.
- 2:40–3:00 impact close (disability/ESL prevalence) + architecture-diagram flash.

## Day-by-day to Jul 13 (submit early)
- **Day 1:** Developer Program sandbox + internal app; enable Agents & AI Apps; add scopes (`reactions:read`,
  `files:read`, `chat:write`, `assistant:write`, `search:read.public`, `canvases:write`, `im:history`/`channels:history`);
  Socket Mode + app token; Bolt skeleton; Anthropic client; **verify paid AI features + RTS availability**; pin
  exact `assistant.search.context`/`canvases.*`/plan-block signatures.
- **Days 2–4:** reacji alt-text (vision + file download) and plain-language rewrite end-to-end — solid demo core.
- **Days 5–7:** Assistant agent + RTS "catch me up" + canvas + plan/task-step streaming.
- **Days 8–9:** accessibility-scoring **MCP server** + tool-runner before/after wiring.
- **Days 10–11:** proactive image detection + prefs store + feedback buttons.
- **Day 12:** seed the sandbox (channels, un-alt-texted images, ≥1 genuinely dense thread).
- **Days 13–14:** UX polish + error/edge states (task-update error rendering).
- **Days 15–16:** record + edit the <3-min video; finalize architecture diagram.
- **Day 17:** write submission description (your voice); Devpost; grant test access to slackhack@salesforce.com +
  testing@devpost.com; **submit**. Days 18–20 buffer.

## Verification (end-to-end)
Run the Bolt app (Socket Mode) against the sandbox and confirm live: (1) 👁️ returns accurate alt text on an
image message; (2) posting a fresh image fires the proactive offer; (3) 🧩 returns a plain-language rewrite
**with an MCP readability before/after**; (4) "Catch me up, accessibly" streams plan blocks + task steps and
produces a canvas; (5) changing the language pref re-renders output in that language; (6) feedback buttons
record. Then confirm the granted test-access emails can open the sandbox and reach the agent.

## Risks / mitigations
- Vision alt-text quality → tight Claude prompt + MCP score as objective backstop.
- RTS no-storage → query at request time; prefs store holds settings only; canvas holds synthesized output.
- RTS bot-token path needs `action_token` from the triggering event → use the Assistant `user_message` event's token.
- Paid-plan AI features → covered by Developer Program sandbox; verify Day 1.
- Off-script judge → every feature works on arbitrary content (key reason this concept is low-risk).
- Naming + submission copy → **yours**, not AI-generated.

---

## Resources (from Slack Dev team)
- **Slack Dev Huddles Ep05 — Slack MCP & RTS API** — covers MCP server integration + Real-Time Search API.
  **(Priority — covers 2 of the 3 core techs, and both are load-bearing for us.)**
- **Slack Dev Huddles Ep06 — Slack Marketplace** — only relevant to the Organizations track (N/A for us).
- Docs: docs.slack.dev/ai/ (agents), docs.slack.dev/ai/slack-mcp-server/, docs.slack.dev/apis/web-api/real-time-search-api/.

## Judge Strategy (official "how to win" guidance)
**Build & pitch to all 4 criteria** (equally weighted — none optional).
- **Pick a sharp, specific problem** — name the workflow you're killing; specificity reads as competence.
- **Make the required tech load-bearing** — if the agent would work identically without RTS/MCP, that costs
  Technological-Implementation points. (Ours wouldn't — RTS powers "catch me up," MCP powers the readability score.)
- **Architecture diagram earns its place** — show data flow + where AI/MCP/RTS sit; upload it, don't bury it.
- **Demo video carries the project (<3 min, front-loaded)** — talk over a real working demo; say what it is /
  does / who it's for / why it's cool; sound excited; AI voice-over over clean screen capture is fine.
- **Keep AI OUT of two things:** (1) **Don't let AI name the project** — name it myself. (2) **Don't let AI
  write the description** — my voice; write it like telling a teammate why I'm proud of it.
- **Process:** submit early (Devpost flags eligibility issues pre-deadline); start the submission form NOW even
  half-finished — gathering links/description/video always takes longer than expected.

---

## Decisions — resolved
1. **Track** — ✅ Slack Agent for Good.
2. **Idea** — ✅ Accessibility co-pilot for Slack (B1 hardened). Pivot on file: A1 decision-provenance agent.
3. **Solo vs team** — ✅ Solo.
4. **Sandbox** — ⏳ set up Slack Developer Program sandbox on Day 1 (needed for build + test access).
5. **Name + submission copy** — ⏳ mine to write, not AI.

## Prize Highlights (1st place, premium tracks)
$8,000 cash + Slack Dev Cert voucher + Dreamforce 2026 pass + swag + community gathering + newsletter/social
features (per eligible team member, up to 4).
