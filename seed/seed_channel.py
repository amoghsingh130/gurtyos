"""Seed a demo channel with believable, threaded chatter for the accessibility demo.

One bot plays several teammates by overriding the display name + avatar per message
(needs the **chat:write.customize** bot scope; without it everything posts as the bot's
own name, which still works — just less convincing). It posts top-level messages, real
thread replies, a couple of dense jargon walls (so 🧩 rewrite and the channel report have
something to chew on), and a color-only-meaning message.

It does NOT post images — Slack won't let a bot drop an un-alt-texted image convincingly.
For the alt-text beat, drag 1–2 screenshots into the channel by hand (Slack adds no alt
text), or react 👁️ on an existing image.

Run from the repo root:
    python -m seed.seed_channel C0BD2PX1753
    python -m seed.seed_channel C0BD2PX1753 --clean   # delete what THIS bot posted first
"""
from __future__ import annotations

import sys
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import load_settings

# persona display name -> avatar emoji
PERSONAS = {
    "Priya · PM": ":raising_hand:",
    "Marcus · Eng": ":technologist:",
    "Dana · Design": ":art:",
    "Sam · Infra": ":gear:",
    "Lena · Eng": ":woman_technologist:",
}

# (persona, text, [ (reply_persona, reply_text), ... ])
SCRIPT: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("Priya · PM", "Morning all — standup in the thread 👇 drop blockers too.", [
        ("Marcus · Eng", "Shipped the auth refactor, tests are green. Picking up search indexing next."),
        ("Dana · Design", "Wrapping the empty-state illustrations, handoff by end of day."),
        ("Lena · Eng", "Chasing a flaky test in the payments suite — should have it pinned this morning."),
    ]),
    ("Sam · Infra",
     "Per the SLA the API KPIs must be reconciled against the EOD ETL pipeline before the "
     "QBR, and stakeholders expect the RCA documentation finalized notwithstanding the "
     "aforementioned dependencies which materially impact the downstream deliverables "
     "across the organization and its partner teams.", [
        ("Marcus · Eng",
         "Following extensive deliberation, the cross-functional working group concluded "
         "that the prevailing prioritization methodology insufficiently accommodates the "
         "interdependencies between concurrent initiatives, so resourcing must be reassessed."),
        ("Priya · PM", "Can someone translate that into what's actually blocked and by when?"),
    ]),
    ("Lena · Eng",
     "Decision: we're sunsetting the legacy auth shim in favor of the OIDC broker. This "
     "unblocks the SSO rollout but adds a hard dependency on the IdP's SCIM provisioning, "
     "which is non-trivial. Owners should audit their service-to-service tokens before the "
     "cutover or risk a cascading 401 storm in prod.", []),
    ("Dana · Design",
     "Quick poll on the dashboard: see the items marked in red — keep red for destructive "
     "actions, or switch to an icon + label?", []),
    ("Priya · PM",
     "Reminder: the OKR rollup is blocked because the upstream CRM integration failed its "
     "SSO handshake, so the QA env cannot validate the SLA dashboards. We need infra to "
     "rotate the OAuth creds before the EOD freeze, otherwise launch readiness slips.", []),
    ("Marcus · Eng", "lgtm — merging the hotfix now 🚀", []),
    ("Lena · Eng", "thanks team, have a good one ☀️", []),
]


def _post(client: WebClient, channel: str, persona: str, text: str, thread_ts: str | None = None):
    return client.chat_postMessage(
        channel=channel, text=text, thread_ts=thread_ts,
        username=persona, icon_emoji=PERSONAS.get(persona, ":speech_balloon:"),
    )


def _clean(client: WebClient, channel: str) -> None:
    """Delete every message this bot previously posted (parents + thread replies),
    looping until a full scan finds none. chat.delete is rate-limited, so 429s are
    honored with the server's Retry-After rather than silently dropped."""
    me = client.auth_test()["user_id"]

    def _mine(m: dict) -> bool:
        return bool(m.get("bot_id")) or m.get("user") == me

    def _delete(ts: str) -> bool:
        for _ in range(5):
            try:
                client.chat_delete(channel=channel, ts=ts)
                time.sleep(0.3)
                return True
            except SlackApiError as e:
                if e.response.get("error") == "ratelimited":
                    time.sleep(int(e.response.headers.get("Retry-After", 2)))
                    continue
                return False
            except Exception:
                return False
        return False

    total = 0
    for _round in range(10):  # converge; cap so undeletable messages can't loop forever
        found = 0
        cur = None
        while True:
            resp = client.conversations_history(channel=channel, limit=200, cursor=cur)
            for m in resp.get("messages", []):
                # Clear our replies under ANY thread — including a tombstoned parent we
                # can't delete; once its orphan replies are gone, the stub disappears.
                if m.get("reply_count"):
                    try:
                        for r in client.conversations_replies(
                                channel=channel, ts=m["ts"], limit=200).get("messages", []):
                            if r.get("ts") != m["ts"] and _mine(r) and _delete(r["ts"]):
                                total += 1
                                found += 1
                    except Exception:
                        pass
                if _mine(m) and _delete(m["ts"]):
                    total += 1
                    found += 1
            cur = (resp.get("response_metadata") or {}).get("next_cursor")
            if not cur:
                break
        if found == 0:
            break
    print(f"deleted {total} prior bot messages")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print("usage: python -m seed.seed_channel <CHANNEL_ID> [--clean]")
        return
    channel = args[0]
    client = WebClient(token=load_settings().slack_bot_token)

    if "--clean" in sys.argv:
        _clean(client, channel)

    posted = 0
    for persona, text, replies in SCRIPT:
        parent = _post(client, channel, persona, text)
        posted += 1
        time.sleep(0.7)
        for rp, rtext in replies:
            _post(client, channel, rp, rtext, thread_ts=parent["ts"])
            posted += 1
            time.sleep(0.5)
    print(f"seeded {posted} messages into {channel}")
    print("Tip: drag 1–2 screenshots in by hand for the alt-text beat (Slack adds no alt text).")


if __name__ == "__main__":
    main()
