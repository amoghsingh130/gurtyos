"""Real-Time Search (RTS): assistant.search.context.

No-storage rule: query at request time, persist nothing from results. The
action_token must come from the triggering Assistant user_message event.

Pin exact param names against docs.slack.dev on Day 1 — these are best-guess.
"""
from __future__ import annotations


def search_context(
    client,
    query: str,
    action_token: str,
    content_types: list[str] | None = None,
    channel_types: list[str] | None = None,
    after: str | None = None,
) -> str:
    """Return a flattened text context for digest synthesis. Stores nothing."""
    # TODO Day 1: confirm method name + params (action_token requirement,
    # content_types=["messages","files"], channel_types, timeframe `after`).
    resp = client.api_call(
        "assistant.search.context",
        params={
            "query": query,
            "action_token": action_token,
            "content_types": content_types or ["messages", "files"],
            **({"channel_types": channel_types} if channel_types else {}),
            **({"after": after} if after else {}),
        },
    )
    results = resp.get("results", {})
    # TODO: shape this into the text block digest.synthesize expects.
    return str(results)
