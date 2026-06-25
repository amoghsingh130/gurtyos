# Testing Guide — Slack Accessibility Co-pilot

End-to-end manual test plan plus ready-to-paste seed messages. Covers every
user-facing flow, with emphasis on the three "competitive hardening" beats
(👎 closes the loop, natural-language prefs, the proactive autonomy offer).

---

## 0. Prerequisites (one-time)

- **`.env`** has `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `ANTHROPIC_API_KEY`, and
  `DEMO_CHANNELS` (the proactive-offer allow-list). Current test channel:
  `DEMO_CHANNELS=C0BD2PX1753`.
- In the Slack app config (api.slack.com/apps → your app):
  - **Socket Mode:** On · **Interactivity & Shortcuts:** On (required for buttons) ·
    **Agents & AI Apps / Assistant:** On.
  - **Bot scopes:** `reactions:read`, `files:read`, `chat:write`, `assistant:write`,
    `search:read.public`, `canvases:write`, `channels:history`, `im:history`.
  - **App-level token** with `connections:write`.
- **Invite the bot** to the demo channel: `/invite @your-app` in `C0BD2PX1753`.
- Reinstall the app after any scope change.

## 1. Fast offline check (no Slack needed)

Confirms the deterministic logic before you spend any tokens:

```bash
cd "/Users/amoghsingh/Documents/Projects/Slack Agent Builder Challenge"
source .venv/bin/activate
python -m pytest -q          # expect: 23 passed
python -m mcp_server.server  # the MCP scorer should start (Ctrl-C to stop)
```

## 2. Start the app

```bash
source .venv/bin/activate
python app.py                # Socket Mode — no public URL needed
```

Wait for `Starting Socket Mode handler...`. Run **exactly one** instance. Keep this
terminal visible — every test prints an `INFO` line here (e.g. `feedback 👎 → grade 8→6`,
`offered plain-language rewrite in C…`). Stop with `Ctrl-C` or `pkill -f "python app.py"`.

---

## 3. Test matrix

> Emoji reacji names: 👁️ = `:eyes:`, 🧩 = `:jigsaw:`.

### A. Alt-text on an image (👁️)
1. Post any image (photo/screenshot) in the demo channel.
2. React 👁️ on it.
3. **Expect:** a threaded reply `👁️ *Alt text:* …` describing the image.

### B. Proactive alt-text offer (autonomy — images)
1. Post an image **without** alt text.
2. **Expect:** an *ephemeral* (only-you-see-it) "This image has no alt text. Describe it? 👁️"
   with a **Describe image** button.
3. Click it → posts the alt text in-thread. Log: `offered alt text for image in C…`.

### C. Plain-language rewrite (🧩) + grade before/after
1. Post **SEED THREAD 1** (below) in any channel the bot is in.
2. React 🧩 on it.
3. **Expect:** a reply `🧩 *Plain-language rewrite* · reading grade X → Y …` with the
   simplified text and 👍 / 👎 buttons. The header notes how many times the agent
   audited & revised its own draft.

### D. 👎 closes the loop (re-render simpler, in place) ⭐ new
1. On the rewrite from test C, click **👎 Not helpful**.
2. **Expect:** the *same message updates in place* to a simpler version; the header now
   reads `… · simplified to grade N after your feedback`. Log: `feedback 👎 → grade …`.
3. **Persistence check:** post **SEED THREAD 2**, react 🧩 as the *same user* → the
   rewrite now targets the lowered grade by default (your preference was remembered).
4. 👍 just logs a positive signal (no visible change) — that's expected.

### E. Natural-language preferences in the Assistant ⭐ new
Open the app's **Assistant pane** (the AI panel for the app), then send these one at a time:
1. `Catch me up accessibly on #general in Spanish`
   → **Expect:** a "Got it — language → Spanish." note, then a Spanish digest.
2. `set my reading level to 5`
   → **Expect:** "Got it — reading grade → 5."
3. `Catch me up accessibly on #general` (no language said)
   → **Expect:** still Spanish at grade 5 (preferences persisted).
4. `make it simpler` → lowers grade by 2 (floored at 3).

### F. "Catch me up, accessibly" digest → canvas
1. Make sure the target channel (e.g. `#general`) has recent messages (seed it first).
2. In the Assistant, send `Catch me up accessibly on #general`.
3. **Expect:** progress updates ("Searching…", "Drafting…", "Audited the draft — pass N",
   "Building an accessible canvas"), then a screen-reader-friendly summary and a note that
   it was saved as a canvas, with a footer `Reading grade N. The agent audited & revised
   its draft N×…`.
4. If RTS isn't enabled yet you'll get a clear "couldn't get a search token" message —
   that's the graceful fallback, not a crash.

### G. Proactive plain-language offer (autonomy — text) ⭐ new
**This only fires in `DEMO_CHANNELS` (`C0BD2PX1753`), on new messages posted after the
app starts.** It never scans history.
1. Paste **WALL 1**, **WALL 2**, or **WALL 3** (below) into `C0BD2PX1753`.
2. **Expect:** an *ephemeral* "This thread may be hard to read… Post a plain-language
   version? 🧩" offer with a **Post plain version** button. Log: `offered plain-language
   rewrite in C…`.
3. Click **Post plain version** → a plain-language rewrite posts in-thread (everyone sees it).
4. **Negative checks (no offer should appear):**
   - Paste **CONTROL A** (long but plain) → no offer.
   - Paste **CONTROL B** (short) → no offer.
   - Post a wall in a channel **not** in `DEMO_CHANNELS` → no offer.
   - Re-post the *same* wall → no second offer (per-message de-dupe).

### H. Guardrails (optional)
- The app refuses LLM calls once estimated spend hits `MAX_SPEND_USD` ($8) or
  `MAX_CALLS_PER_DAY` (300). You'll see a "spend guardrail tripped" message rather than a
  crash. No need to actually hit it; just know the message is expected behavior.

---

## 4. Seed messages

### Rewrite threads (for tests C / D — paste, then react 🧩)

**SEED THREAD 1** (dense status update):
```
Heads up team: per the Q3 OKRs we deprioritized the CDP migration pending the
vendor's SOC2 attestation, so the downstream ETL backfill is parked. The PM is
reconciling the MAU deltas against the BI dashboards and we'll socialize the RCA
async; ping me if the SLA breach impacts your workstream.
```

**SEED THREAD 2** (jargon-heavy decision):
```
Decision: we're sunsetting the legacy auth shim in favor of the OIDC broker. This
unblocks the SSO rollout but introduces a hard dependency on the IdP's SCIM
provisioning, which is non-trivial. Owners should audit their service-to-service
tokens before the cutover or risk a cascading 401 storm in prod.
```

### Proactive-offer triggers (for test G — paste into `C0BD2PX1753`)

These are verified to **trigger** the offer (≥40 words, high grade and/or ≥3 jargon tokens):

**WALL 1** (acronym-dense):
```
Per the SLA the API KPIs must be reconciled against the EOD ETL pipeline before the
QBR, and stakeholders expect the RCA documentation finalized notwithstanding the
aforementioned dependencies which materially impact the downstream deliverables
across the organization and its partner teams.
```

**WALL 2** (formal long-word prose):
```
Following extensive deliberation, the cross-functional working group concluded that
the prevailing prioritization methodology insufficiently accommodates interdependencies
between concurrent initiatives. Consequently, stakeholders should collaboratively
reassess resourcing allocations to ensure organizational throughput remains commensurate
with the strategic objectives articulated during the preceding quarterly planning cycle.
```

**WALL 3** (mixed acronyms + jargon, realistic):
```
Quick sync: the OKR rollup is blocked because the upstream CRM integration failed its
SSO handshake, so the QA env cannot validate the SLA dashboards. We need infra to rotate
the OAuth creds, then re-run the regression suite before the EOD freeze, otherwise the
launch readiness review slips.
```

### Controls — these should NOT trigger an offer (test G negative checks)

**CONTROL A** (long but plain — note: this scores a high *grade* only because it lacks
periods; the screen correctly ignores it because it has no jargon):
```
hey everyone just a quick heads up that the lunch order is going out in ten minutes so
let me know what you want and i will add it to the list thanks so much you all are the
best and have a great rest of your day
```

**CONTROL B** (short):
```
lgtm thanks team, merging now
```

---

## 5. Re-validate the screen offline (optional)

To confirm any new seed message will/won't trigger before posting it live:

```bash
source .venv/bin/activate
python - <<'PY'
from config import Settings
from handlers.proactive import _looks_hard
from mcp_server import scoring
s = Settings(slack_bot_token="x", slack_app_token="x", anthropic_api_key="x")
msg = "PASTE YOUR MESSAGE HERE"
print("would offer:", _looks_hard(s, msg),
      "| words:", len(msg.split()),
      "| grade:", round(scoring.flesch_kincaid_grade(msg), 1),
      "| jargon:", len(scoring.jargon_candidates(msg)))
PY
```

## 6. Troubleshooting

- **No reacji / button response:** confirm only one `app.py` is running, the bot is in the
  channel, and Interactivity is On. Multiple instances make Slack round-robin events.
- **Proactive text offer never appears:** the channel must be in `DEMO_CHANNELS`, the
  message must be new (posted after start) and pass the screen (≥40 words + jargon/grade).
- **Assistant "couldn't get a search token":** RTS isn't enabled for the app yet — the
  other flows still work.
- **Startup error:** paste the traceback; usually a missing scope or env var.
