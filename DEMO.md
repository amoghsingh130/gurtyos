# Demo & Submission Framing — gurtYos (Slack accessibility co-pilot)

Everything here flows from one positioning. Lead with a person, prove with the number,
escalate to org-scale, close on inevitability — and say the tech depth and the stakes out
loud so a judge never has to infer them.

> **North Star:** *An accessibility co-pilot that makes Slack usable for the 1-in-4 teammates
> it leaves behind — built on Slack's own agent platform, and proving every fix with a
> reading score the model can't fake.*

**Hero tagline (lead with this):**
> *Slack, made readable for the teammates it leaves behind — and it proves every fix.*

Alternates: *"The accessibility agent that grades its own work."* · *"Most agents do work.
This one does the work nobody else will — and shows the receipts."*

### Why it wins — the five pillars (map each to a judging lever)

1. **On-platform by construction → the tech tie-breaker.** All three required Slack techs,
   each *load-bearing*: Assistant API (the co-pilot), a custom **MCP** accessibility scorer,
   and Real-Time Search (the digest). Remove any one and a flow breaks. Most entries use one.
2. **An un-fakeable technical signature.** The self-auditing **draft → audit → revise** loop —
   the agent grades its own homework live (reading grade 24 → 7), scored *deterministically
   by a custom MCP server*, not claimed by the model.
3. **It's an agent, not a tool.** It *watches* a channel and offers to fix a jargon wall
   unprompted; 👎 → it re-renders simpler **and remembers**; "now in Spanish" → live re-render.
4. **Impact at the right altitude.** 1-in-4 adults has a disability; inaccessible workplace
   tools are an **ADA / Section 508** liability and a reason people are **excluded from
   employment**. The Channel Accessibility Report (22 → 97) shows the fix at workspace scale.
5. **A human spine.** Open and close on a person hearing alt text through VoiceOver / getting
   the standup in Spanish. Feeling wins the room; the number seals it.

---

## 1 · The <3-minute video script (shot-by-shot)

The video *is* the product — build it to this arc. Two free ceiling-raisers: **VoiceOver
playback** (judges *hear* the before/after) and the **scale-of-problem opener**.

| Time | Beat | On screen | Narration (lift verbatim) |
|---|---|---|---|
| 0:00–0:15 | **Human cold open** | A screen reader lands on an image post → *"image, no description"* → silence | "For Maya, who's blind, half of Slack is a closed door. Every screenshot her team posts is just… silence." |
| 0:15–0:30 | **Scale of the problem** | The agent posts a count | "So I asked our agent to look. It scanned one channel: 47 images, zero alt text, 12 walls of jargon. This isn't rare — it's every channel, every team." |
| 0:30–1:05 | **Tech money-shot** | React 🧩 on a jargon thread → the agent's **draft → audit → revise** tool calls run → header flips to **reading grade 24 → 7**, "defined 4 acronyms, split 3 sentences" | "Watch it work. It drafts a plain-language version, then calls its *own accessibility scorer* — a custom MCP server — to grade itself, and revises until it passes. It doesn't *claim* it's simpler. It proves it: grade 24 to 7." |
| 1:05–1:35 | **Catch me up, accessibly** | Assistant: *"catch me up on #general"* → **the audit passes stream in live as plan steps** → an accessible **canvas**, then play it through **VoiceOver** | "And it catches you up — accessibly. You watch it audit its own draft, step by step, then it writes a screen-reader-perfect summary — and Maya hears the standup for the first time." *(let VoiceOver speak)* |
| 1:35–2:00 | **It's an agent** | Unprompted offer on a fresh jargon wall → 👎 → re-renders **simpler and remembers** → *"now in Spanish"* → live re-render | "No one asked it to. It *noticed* the jargon and offered to fix it. Thumbs-down — too hard? It simplifies, and remembers your level. 'Now in Spanish?' Done." |
| 2:00–2:35 | **Org scale + one-click fix** | **Channel Accessibility Report** canvas: **22 → 97**, framed **ADA / Section 508** → click **🛠️ Fix this channel** → alt text + plain-language rewrites cascade into the channel, live | "And it scales. It scores a whole channel against the ADA standard — 22 to 97 — then, one click, it *fixes it*: describing images and rewriting jargon across the channel. It doesn't just measure. It does the work." |
| 2:35–2:55 | **The close** | Cut back to Maya, now following along | "Three required Slack technologies, each load-bearing. An agent that measures — and fixes — its own accessibility. This is the agent Slack should ship." |

---

## 2 · Devpost submission copy

**Title:** gurtYos — *Slack, made readable for the teammates it leaves behind.*

**Inspiration.**
One in four adults lives with a disability, yet the tools we work in every day weren't built
for them. A blind teammate's screen reader hits a screenshot and goes silent. A neurodivergent
or non-native-English teammate opens a thread and finds a wall of acronyms. Slack is where work
happens — and for these colleagues, half of it is a closed door. We wanted the fix to live
*inside* Slack, and to be impossible to argue with.

**What it does.**
An agent that makes Slack accessible to the people it currently excludes:
- **Alt text on demand** for blind / low-vision teammates — react 👁️ on any image and the
  agent writes screen-reader-quality alt text (Claude vision).
- **Plain-language rewrites** for neurodivergent and ESL readers — react 🧩 on a jargon
  thread and it rewrites it, with a measured reading-grade before/after.
- **"Catch me up, accessibly"** — ask the Assistant and it pulls recent activity via Real-Time
  Search and produces a screen-reader-friendly canvas digest, in your language.
- It also **acts on its own** (offers to fix hard threads unprompted), **learns** (👎 →
  simpler, and it remembers), and **scores a whole channel** against an ADA-style standard —
  then, **one click, fixes the whole channel** (alt text + plain-language rewrites across it).
  You watch every audit pass **stream live**, and each fix carries concrete numbers
  (acronyms defined, sentences split, reading time).

**How we built it.**
Three required Slack platform technologies, each *load-bearing* — remove any one and a feature
breaks: the **Assistant API** (the co-pilot surface), a **custom MCP server** (a deterministic
accessibility scorer — Flesch-Kincaid grade, WCAG contrast, jargon/long-sentence audit), and
**Real-Time Search** (the catch-up digest). The agent runs a real `tool_runner` **draft →
audit → revise** loop: it writes a draft, calls its MCP scorer to grade itself, and revises
until it hits the reader's target — so the on-screen numbers are computed, not claimed.
Cost/safety guardrails (spend ceiling + daily cap) keep it production-shaped. Built with the
latest Claude models (Sonnet 4.6 / Haiku 4.5).

**Impact.**
Inaccessible workplace tools aren't an inconvenience — they're an **ADA / Section 508**
liability and a documented reason people are excluded from employment. Our agent makes the
fix measurable (reading grade 24 → 7 per thread; a workspace accessibility score of 22 → 97)
and puts it where the work already is. Slack should ship this.

**What's next.** A living jargon glossary that learns each org's acronyms; more languages; an
org-wide accessibility compliance dashboard.

---

## 3 · Verbal pitch + soundbites

**30-second pitch.**
"Slack has a new agent platform. We used it to fix the one thing Slack can't fix about itself —
that it's unusable for blind, neurodivergent, and non-native-English teammates. Our agent
rewrites jargon into plain language, describes images, and catches you up accessibly — and
unlike any other accessibility tool, it *scores its own output* with a custom MCP server, so
every fix is measurable: reading grade 24 to 7. It watches channels and fixes problems
unprompted, learns from your feedback, scores a whole workspace against the ADA standard —
and then *fixes the whole channel in one click*. It's the agent Slack should ship."

**Drop-in soundbites.**
- "It grades its own homework, live — you watch every pass."
- "Remove any one of the three Slack techs and a flow breaks."
- "We didn't build a tool that waits — we built an agent that notices, and fixes."
- "Accessibility you can't argue with, because it's a number."
- "It doesn't just measure the problem. One click, it fixes the whole channel."

---

## Pre-demo checklist

- [ ] **Channel Accessibility Report** built and rendering a real 22 → 97 canvas (the org-scale beat).
- [ ] Seeded demo channel: real-looking chatter, ≥1 un-alt-texted image, ≥1 dense jargon thread.
- [ ] `MODEL_DIGEST=claude-opus-4-8` set for the final recording (max polish), or leave Sonnet for speed.
- [ ] VoiceOver rehearsed on the alt-text reply and the digest canvas.
- [ ] Load-bearing check: disabling Assistant / MCP / RTS each visibly breaks a demoed flow.
- [ ] Numbers (24→7, 22→97) shown computed on camera, never on a slide.
- [ ] Grant test access to the judges' accounts; submit early.
