"""Block Kit builders: plan blocks, task-update steps, feedback buttons.

Plan/task-step shapes come from docs.slack.dev/ai/developing-agents — pin the
exact block types during build; the helpers below are placeholders.
"""
from __future__ import annotations


def feedback_buttons(value: str) -> list[dict]:
    """👍/👎 feedback actions carrying an opaque `value` (e.g. channel:ts)."""
    return [
        {
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "👍 Helpful"},
                 "action_id": "feedback_up", "value": value},
                {"type": "button", "text": {"type": "plain_text", "text": "👎 Not helpful"},
                 "action_id": "feedback_down", "value": value},
            ],
        }
    ]


def alt_text_offer(value: str) -> list[dict]:
    """Ephemeral proactive offer to describe an image."""
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "This image has no alt text. Describe it? 👁️"},
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "Describe image"},
                "action_id": "offer_alt_text",
                "value": value,
            },
        }
    ]
