"""Delete every message THIS bot posted in a conversation — channel or DM.

Generalizes the seeder's ``--clean`` so the Assistant "clear our chat" command and a
CLI (``python -m seed.purge_dm``) reuse one rate-limit-aware, thread-aware purge.

A bot token can only delete the bot's *own* messages, so a user's typed prompts in a
DM remain — this clears the digests/reports/canvas links that actually clog the tab.
"""
from __future__ import annotations

import time

from slack_sdk.errors import SlackApiError


def purge_bot_messages(client, channel: str, *, sleep: float = 0.3) -> int:
    """Delete every message this bot posted in ``channel`` (parents + thread replies),
    looping until a full scan finds none. ``chat.delete`` is rate-limited, so 429s are
    honored with the server's Retry-After rather than dropped. Returns the count
    deleted. Works for channels (C…), DMs (D…), and group DMs (G…)."""
    me = client.auth_test()["user_id"]

    def _mine(m: dict) -> bool:
        return bool(m.get("bot_id")) or m.get("user") == me

    def _delete(ts: str) -> bool:
        for _ in range(5):
            try:
                client.chat_delete(channel=channel, ts=ts)
                time.sleep(sleep)
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
    return total
