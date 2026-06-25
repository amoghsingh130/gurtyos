# Plan to WIN First Place — Slack Accessibility Co-pilot · Agent for Good

## Context
Goal: **win the Agent-for-Good track outright ($8,000), no matter what.** Verified prize rules
reframe the strategy:
- **One prize per submission:** *"A winning Eligible Submission may only win one (1) Prize…
  First/Second Prize winners are not eligible to receive an Achievement prize."* → achievement
  prizes are **consolation, not strategy**; commit fully to best-in-track.
- **Tie-break = Technological Implementation** (first listed criterion) → in a close race, **tech
  decides**; over-invest there.
- **Bar:** if we don't win, it's because a judge actively preferred someone else's work — not
  because we left points on the table. Track confirmed: **stay Agent for Good**.

**North star: the demo is the product.** Design the <3-min video first; build backward to it.
SDK verified: `anthropic` 0.112.0 has `beta.messages.tool_runner` + `anthropic.lib.tools.mcp`;
`slack_sdk` 3.42.0 has `canvases_*`.

**Ceiling-raisers chosen** (fold in, but respect the cut line): Channel Accessibility Report
(signature artifact), adaptive feedback loop, standalone reusable MCP server, living jargon
glossary (RTS). Plus two **free demo techniques** (no build): real screen-reader playback on
camera, and opening on the scale-of-problem counter.

> **Scope warning (solo, ~18 days):** this is ambitious. The critical demo path ships at 100%
> *before* any add-on; the living glossary is first to cut. Impressiveness must not come at the
> cost of a flawless core demo.

---

## WS0 — Demo script & critical path (do FIRST, before code)
Write the shot-by-shot <3-min script and lock the wow beats. **Critical path (must be 100%):**
1. Open on **scale-of-problem** ("scanned #general: 47 images no alt text, 12 jargon walls").
2. 🧩 rewrite showing the agent's **draft → audit → revise** tool-calls + grade before/after.
3. "Catch me up, accessibly" **streaming plan/task steps → accessible canvas** (money-shot).
4. **Channel Accessibility Report** canvas (42→96) as the system-level payoff.
5. Personalization: "now in Spanish" → live re-render; 👎 "too hard" → re-render simpler.
**Free demo technique throughout:** play alt text + digest through **VoiceOver** so judges *hear*
the before/after. Supporting B-roll: alt-text reacji, proactive offer.

## WS1 — Signature wows (the un-copyable first-place edges)
- **(a) Self-auditing agent loop is THE story.** Agentic `tool_runner` over the MCP a11y toolset
  in `llm/rewrite.py` + `llm/digest.py`: draft → call `audit_accessibility`/`score_readability`
  → revise until target grade (cap ~3 iters). Keep one **deterministic** final `score_readability`
  in app code for the on-camera number. Surface each tool-call as a visible task step.
- **(b) Dogfood accessibility.** Every message/Block Kit/canvas the agent emits is itself
  screen-reader-perfect: plain language, real alt text, headed sections, no color/emoji-only
  meaning, logical order. "The accessibility agent models accessibility." (Audit every emit path.)
- **(c) Channel Accessibility Report (signature artifact).** Audit a whole channel (RTS /
  `conversations.history` → run `audit_accessibility` at scale) → an **A11y-score canvas**:
  score (e.g. 42→96), % images missing alt text, avg reading grade, contrast/color-only flags,
  with an **ADA / Section 508 compliance** framing (the rubric's "impact *beyond* the community").
  Offer one-click fixes. Reuses the MCP tool, RTS, and canvas you're already building.

## WS2 — Tech-Implementation ceiling (the tie-breaker — over-invest)
- **Name & prove "all three required techs, each load-bearing"** (Assistant + MCP loop + RTS);
  most entrants use one. Make it an explicit argument in diagram + copy + video.
- **Standalone reusable MCP server:** package `mcp_server/` with a README + public tool schema so
  it's "an accessibility-scoring MCP server anyone can mount," not just an internal detail.
- **Eval harness** (`evals/` + pytest): alt-text accuracy on a fixed image set; **rewrite
  faithfulness** (no dropped facts/names/numbers); readability-delta distribution → a one-screen
  "report card" to flash on camera and cite in copy.
- **Visible reliability:** retry/backoff on Slack + Anthropic calls, graceful per-flow
  degradation, `guardrails.py` ledger surfaced as observability.
- **Enrich the MCP server** (`mcp_server/server.py`, `scoring.py`): add `audit_accessibility(text)
  -> {grade, reading_seconds, long_sentences[], undefined_jargon[], color_only_refs[],
  contrast_fails[]}`; keep `score_readability` + `wcag_contrast`.

## WS3 — Money-shot + personalization + adaptive feedback
- **Plan-blocks / task-update steps** on the Assistant flow (`handlers/assistant.py`,
  `slack_io/blocks.py`); `chat.startStream` if available, else iterative `set_status`; wire
  `digest.py`'s `on_token`. **Pin shapes vs docs.slack.dev/ai/developing-agents.**
- **Prefs write-path** (dead `PrefsStore.set`, `prefs/store.py:41`): parse the Assistant
  `user_message` for "now in Spanish" / "set my reading level to N" → `prefs.set(...)` → re-run.
- **Adaptive feedback loop:** wire the currently-dead 👍/👎 (`reactions.py:48-56`) so 👎 lowers the
  user's grade and **re-renders simpler on screen** — a visibly learning agent.

## WS4 — Truth-up + robustness (eliminate self-inflicted losses)
- `llm/digest.py`: implement adaptive thinking + `effort=high` (resolve `:41` TODO, verify arg
  names) or drop the claim. Remove stale `tool_runner` comments (`config.py:51`).
- Reconcile `README.md` + `handoff.md` with the real (now agentic) architecture; fix date drift.
- Unit tests (`scoring.py`, MCP stdio round-trip, guardrails ledger) fold into WS2 evals.
- Demo on **Opus** (`config.py`), Haiku via env for dev; scope proactive offer to `DEMO_CHANNEL` + de-dupe.

## WS5 — Scored artifacts, designed early
- **Impact statement** (required for For Good, judged): prevalence receipts + measurable
  before/after + ADA/508 "Slack should ship this" framing. Draft early, **in your voice**.
- **Architecture diagram** (PNG): agentic loop + all 3 techs + canvas.
- **Seed** a text-rich demo channel (`seed/`): chatter, un-alt-texted images, ≥1 dense jargon thread.
- **Living jargon glossary (RTS)** — *second-tier:* agent learns the org's acronyms from real usage
  → glossary canvas. Build only if the critical path is already at 100%.
- **Record/edit** the <3-min video to the WS0 script (with VoiceOver playback). **Submission copy**
  in your voice. Grant test access to slackhack@salesforce.com + testing@devpost.com. **Submit early.**

---

## Cut line (protect the critical path; cut from the bottom if time slips)
WS0 script → WS3 money-shot + personalization + feedback → WS1(a)(b) loop & dogfood →
WS1(c) Channel Report → WS2 evals/all-3-techs/standalone-MCP → WS4 truth-up → proactive polish →
**living jargon glossary** → extra MCP tools → test breadth.
**Never let the WS5 video or impact statement slip** — they outweigh any extra feature.

## Verification (to a first-place bar)
1. 🧩 rewrite shows visible **draft→audit→revise** steps + a trustworthy grade before/after (Opus).
2. "Catch me up" **streams plan/task steps** → accessible **canvas**.
3. **Channel Report** produces an A11y-score canvas with a real before/after number.
4. "Now in Spanish" re-renders; 👎 "too hard" re-renders simpler.
5. Every agent-emitted message/block/canvas passes its **own** accessibility audit (dogfood check).
6. `pytest` + **eval report** pass; faithfulness shows no dropped facts; ledger records.
7. All three techs demonstrably load-bearing (remove one → a flow breaks).
8. VoiceOver audibly reads the agent's alt text/digest; the two test-access emails reach the agent.

## Pin vs docs (execution Day 1)
- plan-block / task-update shapes + `chat.startStream` (docs.slack.dev/ai/developing-agents).
- `beta.messages.tool_runner` + `mcp_tool` signature (anthropic 0.112.0); adaptive-thinking/effort args.
- `assistant.search.context` + `canvases.*` fields on the sandbox.
