"""Plan/task-step streaming for the Assistant "watch the agent think" money-shot.

Wraps chat.startStream / chat.appendStream / chat.stopStream with
`task_display_mode="plan"` so judges watch the agent's steps stream in as a plan
with task updates (in_progress → completed). Method names are verified present in
slack_sdk 3.42; the live round-trip needs a real Assistant thread, so every call
is defensive — if streaming is unavailable the caller falls back to set_status.

Chunk shapes (pinned against docs.slack.dev/ai/developing-agents):
- start:  chat.startStream(task_display_mode="plan", chunks=[{type:"markdown_text", ...}])
- step:   chat.appendStream(message_ts=…, chunks=[{type:"task_update", task:{…}}])
- finish: chat.stopStream(message_ts=…, chunks=[{type:"markdown_text", ...}])  (may carry blocks)
"""
from __future__ import annotations

import logging

log = logging.getLogger("slack_io.stream")


class TaskStream:
    """Thin, defensive wrapper around the Assistant streaming API."""

    def __init__(self, client, channel: str, thread_ts: str):
        self._client = client
        self._channel = channel
        self._thread_ts = thread_ts
        self._ts: str | None = None
        self.active = False

    def start(self, intro: str) -> bool:
        """Begin a plan-mode stream. Returns True only if streaming is live."""
        try:
            resp = self._client.chat_startStream(
                channel=self._channel,
                thread_ts=self._thread_ts,
                task_display_mode="plan",
                chunks=[{"type": "markdown_text", "markdown_text": intro}],
            )
            self._ts = resp.get("ts") or resp.get("message_ts")
            self.active = bool(self._ts)
        except Exception:
            log.warning("chat.startStream unavailable; using set_status fallback", exc_info=True)
            self.active = False
        return self.active

    def task(self, task_id: str, title: str, status: str = "in_progress") -> None:
        """Add or update a task step. Status: in_progress | completed | error."""
        if not self.active:
            return
        try:
            self._client.chat_appendStream(
                channel=self._channel,
                message_ts=self._ts,
                thread_ts=self._thread_ts,
                chunks=[{
                    "type": "task_update",
                    "task": {"task_id": task_id, "title": title, "status": status},
                }],
            )
        except Exception:
            log.warning("chat.appendStream task update failed", exc_info=True)

    def stop(self, final_markdown: str) -> str | None:
        """Finish the stream with the final message. Returns the message ts."""
        if not self.active:
            return None
        try:
            self._client.chat_stopStream(
                channel=self._channel,
                message_ts=self._ts,
                thread_ts=self._thread_ts,
                chunks=[{"type": "markdown_text", "markdown_text": final_markdown}],
            )
        except Exception:
            log.warning("chat.stopStream failed", exc_info=True)
        return self._ts
