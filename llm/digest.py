"""RTS results -> accessible digest. Streamed (effort=high) so large output
doesn't time out, and so the Assistant can surface plan/task steps as it works.

Accessible-by-construction: short sentences, headed sections, a jargon glossary,
no color-only meaning. Output is markdown destined for a Slack canvas.
"""
from __future__ import annotations

from typing import Iterable

import anthropic

from config import Settings

DIGEST_SYSTEM = (
    "You summarize Slack activity for blind/low-vision, neurodivergent, and ESL "
    "readers. Use short sentences and clear section headings. Define jargon inline "
    "or in a short glossary. Never rely on color or emoji to carry meaning. "
    "Write at the reader's target reading grade and language."
)


def synthesize(
    settings: Settings,
    rts_context: str,
    target_grade: int = 6,
    language: str = "English",
    on_token=None,
    guard=None,
) -> str:
    """Return the digest markdown. If on_token is given, stream partial text to it
    (e.g. to drive task-step status updates in the Assistant panel)."""
    if guard is not None:
        guard.check()  # raises BudgetExceeded if over the spend ceiling / daily cap
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    user = (
        f"Reading grade: {target_grade}. Language: {language}.\n\n"
        f"Slack context to summarize:\n{rts_context}"
    )
    out: list[str] = []
    # TODO: confirm thinking={"type":"adaptive"} + output_config={"effort":"high"}
    # arg names against the installed SDK before relying on them.
    with client.messages.stream(
        model=settings.model_digest,
        max_tokens=4000,
        system=DIGEST_SYSTEM,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        for text in stream.text_stream:
            out.append(text)
            if on_token:
                on_token(text)
        final = stream.get_final_message()
    if guard is not None:
        guard.record(settings.model_digest, final.usage)
    return "".join(out)
