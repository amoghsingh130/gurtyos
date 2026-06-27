"""Vision -> alt text. Single Claude call with a base64 image block."""
from __future__ import annotations

import base64

import anthropic

from config import Settings
from llm import sanitize

ALT_TEXT_PROMPT = (
    "Write concise, accurate alt text for this image for a blind or low-vision Slack "
    "user. Lead with the most important content. Describe meaningful text in the image "
    "verbatim. No 'image of'/'picture of' preamble. One to two sentences."
) + sanitize.IMAGE_INJECTION_GUARD


def describe(settings: Settings, image_bytes: bytes, media_type: str, guard=None) -> str:
    if guard is not None:
        guard.check()  # raises BudgetExceeded if over the spend ceiling / daily cap
    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key, max_retries=settings.anthropic_max_retries
    )
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    msg = client.messages.create(
        model=settings.model_alt_text,
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    },
                    {"type": "text", "text": ALT_TEXT_PROMPT},
                ],
            }
        ],
    )
    if guard is not None:
        guard.record(settings.model_alt_text, msg.usage)
    return "".join(block.text for block in msg.content if block.type == "text").strip()
