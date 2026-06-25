"""Real-Time Search (RTS): assistant.search.context.

Verified against docs.slack.dev (2026-06-24):
- Bot-token calls REQUIRE `action_token`, taken from the triggering event payload
  (message / app_mention). User-token calls don't need it.
- Bot scope: search:read.public (search:read.files / search:read.users optional).
- channel_types values: public_channel, private_channel, mpim, im (default public_channel).
- content_types values: messages, files, channels, users (default messages).
- before/after are INTEGER unix timestamps. limit max 20. Cursor pagination via
  response_metadata.next_cursor.

No-storage rule: query at request time, persist nothing from results.
"""
from __future__ import annotations


def search_context(
    client,
    query: str,
    action_token: str,
    content_types: list[str] | None = None,
    channel_types: list[str] | None = None,
    context_channel_id: str | None = None,
    after: int | None = None,
    before: int | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> dict:
    """Raw assistant.search.context response (stores nothing)."""
    params: dict = {
        "query": query,
        "action_token": action_token,
        "content_types": content_types or ["messages", "files"],
        "limit": min(limit, 20),
    }
    if channel_types:
        params["channel_types"] = channel_types
    if context_channel_id:
        params["context_channel_id"] = context_channel_id
    if after is not None:
        params["after"] = after
    if before is not None:
        params["before"] = before
    if cursor:
        params["cursor"] = cursor

    return client.api_call("assistant.search.context", params=params)


def flatten_results(resp: dict) -> str:
    """Shape results.messages/files into a plain-text block for digest synthesis.
    Uses only the fields the API documents: content, author_name, channel_name,
    permalink (messages) and title/content (files)."""
    results = resp.get("results", {})
    lines: list[str] = []
    for m in results.get("messages", []):
        who = m.get("author_name", "someone")
        where = m.get("channel_name", "")
        lines.append(f"[#{where}] {who}: {m.get('content', '')}")
    for f in results.get("files", []):
        lines.append(f"[file] {f.get('title', '')}: {f.get('content', '')}")
    return "\n".join(lines)
