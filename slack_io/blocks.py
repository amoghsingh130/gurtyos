"""Block Kit + streaming builders.

Streaming the agent's work (verified against docs.slack.dev/ai/developing-agents,
2026-06-24): use chat.startStream(task_display_mode="plan"|"timeline") -> ts, then
chat.appendStream(channel, message_ts=ts, thread_ts, chunks=[...]) to push text and
"task_update" chunks, then chat.stopStream(...) to finalize. Block Kit blocks
(including the "plan block") may ONLY be attached on chat.stopStream, not on
start/append. For a simple "is thinking..." state use assistant.threads.setStatus
(Bolt's set_status).

Task update states: in_progress | completed | error.
Plan block task states:  pending | in_progress | completed | error.
"""
from __future__ import annotations


def task_update_chunk(text: str, state: str) -> dict:
    """A 'task_update' chunk for chat.appendStream. state in
    {in_progress, completed, error}."""
    return {"type": "task_update", "state": state, "text": text}


def text_chunk(text: str) -> dict:
    """A plain text chunk for chat.appendStream."""
    return {"type": "text", "text": text}


def feedback_buttons(value: str) -> list[dict]:
    """👍/👎 feedback actions carrying an opaque `value` (e.g. channel:ts).
    Attach via chat.stopStream(blocks=...) or a normal chat_postMessage."""
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
