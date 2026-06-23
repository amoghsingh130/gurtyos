"""Fetch the reacted message (and its thread) by channel+ts."""
from __future__ import annotations


def fetch_message(client, channel: str, ts: str) -> dict:
    """Single message at `ts`. conversations_history with a tight window."""
    resp = client.conversations_history(
        channel=channel, latest=ts, oldest=ts, inclusive=True, limit=1
    )
    msgs = resp.get("messages", [])
    if not msgs:
        raise LookupError(f"no message at {channel}/{ts}")
    return msgs[0]


def fetch_thread(client, channel: str, ts: str) -> list[dict]:
    """Full thread rooted at `ts` (or the single message if not threaded)."""
    resp = client.conversations_replies(channel=channel, ts=ts, limit=200)
    return resp.get("messages", [])


def thread_text(messages: list[dict]) -> str:
    """Flatten thread messages into plain text for rewrite/scoring."""
    return "\n\n".join(m.get("text", "") for m in messages if m.get("text"))
