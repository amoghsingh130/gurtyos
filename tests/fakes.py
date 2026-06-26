"""A fake Slack WebClient for integration tests — records every call and returns
canned responses, so handler flows can be driven end-to-end without a real workspace.

Only the methods the handlers actually use are implemented. Responses are plain dicts
(slack_sdk's SlackResponse supports both `.get()` and `[...]`, and so do dicts)."""
from __future__ import annotations

from slack_sdk.errors import SlackApiError


class FakeSlackClient:
    def __init__(self, *, history=None, replies=None, channel_name=None,
                 info_raises=False):
        self.calls: list[tuple[str, dict]] = []
        self._history = list(history or [])
        self._replies = dict(replies or {})       # parent_ts -> [reply messages]
        self._channel_name = channel_name
        self._info_raises = info_raises
        self._canvas_seq = 0

    # --- helpers for assertions ------------------------------------------
    def _rec(self, method: str, **kw) -> None:
        self.calls.append((method, kw))

    def calls_to(self, method: str) -> list[dict]:
        return [kw for (m, kw) in self.calls if m == method]

    def called(self, method: str) -> bool:
        return any(m == method for (m, _) in self.calls)

    # --- Slack API surface used by the handlers --------------------------
    def conversations_history(self, channel, limit=100, **kw):
        self._rec("conversations_history", channel=channel, limit=limit, **kw)
        # fetch_message() uses latest/oldest to pin a single message; honor it loosely.
        if kw.get("latest") and kw.get("limit", limit) == 1:
            msgs = [m for m in self._history if m.get("ts") == kw["latest"]] or self._history[:1]
            return {"ok": True, "messages": msgs}
        return {"ok": True, "messages": list(self._history), "response_metadata": {}}

    def conversations_replies(self, channel, ts, limit=50, **kw):
        self._rec("conversations_replies", channel=channel, ts=ts)
        return {"ok": True, "messages": self._replies.get(ts, [])}

    def conversations_info(self, channel):
        self._rec("conversations_info", channel=channel)
        if self._info_raises:
            raise SlackApiError("missing_scope", {"ok": False, "error": "missing_scope"})
        return {"ok": True, "channel": {"name": self._channel_name or "general"}}

    def chat_postMessage(self, **kw):
        self._rec("chat_postMessage", **kw)
        return {"ok": True, "ts": "1700000000.000100", "channel": kw.get("channel")}

    def chat_postEphemeral(self, **kw):
        self._rec("chat_postEphemeral", **kw)
        return {"ok": True}

    def chat_update(self, **kw):
        self._rec("chat_update", **kw)
        return {"ok": True}

    def canvases_create(self, **kw):
        self._rec("canvases_create", **kw)
        self._canvas_seq += 1
        return {"ok": True, "canvas_id": f"F{self._canvas_seq:06d}"}

    def views_publish(self, **kw):
        self._rec("views_publish", **kw)
        return {"ok": True}


class Recorder:
    """Captures positional string args from say()/set_status() callbacks."""
    def __init__(self):
        self.messages: list[str] = []

    def __call__(self, text=None, *a, **k):
        if text is not None:
            self.messages.append(str(text))

    @property
    def last(self) -> str:
        return self.messages[-1] if self.messages else ""

    @property
    def joined(self) -> str:
        return "\n".join(self.messages)
