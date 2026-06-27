"""Resolve a channel reference in a user's text to a channel id.

Handles both the autocompleted mention ``<#C…|name>`` and a plain typed ``#name``
(which Slack sends as literal text when the user doesn't pick the autocomplete). Plain
``#name`` resolution needs the **channels:read** scope (``conversations.list``); without
it we return "named but unresolved" so callers can show a clear error instead of
silently degrading the catch-up to a workspace search that starves the query.
"""
from __future__ import annotations

import re

# `<#C0123|name>` — Slack's rendered mention. name group is optional.
_MENTION = re.compile(r"<#(C[A-Z0-9]+)(?:\|([^>]*))?>")
# A plain typed `#name`. Require a leading letter so "#1 priority" isn't read as a
# channel. Slack channel names are lowercase, but match loosely and normalize.
_PLAIN = re.compile(r"#([a-zA-Z][\w.-]*)")

_cache: dict[str, str] | None = None  # name(lower) -> id, resolved once per process


def _channel_index(client) -> dict[str, str]:
    """name(lower) -> channel id for every channel the bot can list. Cached. Queries
    public (channels:read) and private (groups:read) channel types *separately* so a
    missing private scope doesn't abort public resolution — `conversations.list` rejects
    the whole call if any requested type lacks its scope. On error per type, keeps what
    it gathered, so callers treat unknown names as unresolved rather than crashing."""
    global _cache
    if _cache is not None:
        return _cache
    idx: dict[str, str] = {}
    for types in ("public_channel", "private_channel"):
        cur = None
        try:
            while True:
                resp = client.conversations_list(
                    types=types, limit=1000, cursor=cur, exclude_archived=True)
                for ch in resp.get("channels", []):
                    if ch.get("name"):
                        idx.setdefault(ch["name"].lower(), ch["id"])
                cur = (resp.get("response_metadata") or {}).get("next_cursor")
                if not cur:
                    break
        except Exception:
            continue  # e.g. private_channel without groups:read — public still resolves
    _cache = idx
    return idx


def resolve_target(client, query: str) -> tuple[str | None, str | None, bool]:
    """Resolve a channel reference in ``query``.

    Returns ``(channel_id, label, was_named)``:
    - ``<#C…|name>`` mention -> ``(id, "#name", True)``
    - plain ``#name`` -> ``(id, "#name", True)`` if resolvable, else ``(None, "#name",
      True)`` (channels:read missing or no such channel)
    - no channel referenced -> ``(None, None, False)``
    """
    m = _MENTION.search(query)
    if m:
        name = (m.group(2) or "").strip()
        return m.group(1), (f"#{name}" if name else "this channel"), True
    p = _PLAIN.search(query)
    if p:
        name = p.group(1)
        return _channel_index(client).get(name.lower()), f"#{name}", True
    return None, None, False


def reset_cache() -> None:
    """Test hook: drop the per-process channel index."""
    global _cache
    _cache = None
