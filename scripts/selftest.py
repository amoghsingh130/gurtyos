"""Headless self-test: drive gurtYos features as function calls against a real
workspace, so behavior can be verified without clicking through Slack.

It posts REAL (temporary) messages/canvases into the target channel, then purges the
bot's own messages as cleanup. Canvas tabs are not auto-removed. Point it at a
**scratch** channel, never your demo channel.

    python -m scripts.selftest <SCRATCH_CHANNEL_ID>
    python -m scripts.selftest            # defaults to the first DEMO_CHANNELS entry

Needs the real bot token in env (same as `python app.py`). Run from the repo root.

Not covered (needs a real user action + Assistant thread): Socket Mode user_message /
reaction_added events and the live chat.startStream round-trip — verify those manually.
"""
from __future__ import annotations

import dataclasses
import sys

from slack_sdk import WebClient

from config import load_settings
from handlers import assistant
from prefs.store import PrefsStore
from slack_io.purge import purge_bot_messages


class _Rec:
    """Minimal say()/set_status() capture."""
    def __init__(self):
        self.msgs: list[str] = []

    def __call__(self, text=None, **k):
        if text is not None:
            self.msgs.append(str(text))

    @property
    def last(self) -> str:
        return self.msgs[-1] if self.msgs else ""


def _row(ok: bool, name: str, detail: str) -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name:<22} -> {detail[:120]!r}")


def main() -> None:
    settings = dataclasses.replace(load_settings(), enable_task_stream=False)  # headless
    channel = sys.argv[1] if len(sys.argv) > 1 else (
        settings.demo_channels[0] if settings.demo_channels else None)
    if not channel:
        print("usage: python -m scripts.selftest <CHANNEL_ID>  (or set DEMO_CHANNELS)")
        return

    client = WebClient(token=settings.slack_bot_token)
    prefs = PrefsStore(settings.prefs_db_path)
    mention = f"<#{channel}>"
    print(f"== gurtYos self-test against {channel} ==\n")

    # 1. Catch-up via an explicit mention (history path — the core flow).
    say = _Rec()
    assistant._run_catch_up(
        client, settings,
        {"text": f"catch me up on {mention}", "channel": channel, "user": "selftest"},
        None, prefs, _Rec(), say)
    _row("grade" in say.last.lower() or "📄" in say.last, "catch-up (mention)", say.last)

    # 2. Catch-up via plain #name — exercises name resolution (needs channels:read).
    name = None
    try:
        name = (client.conversations_info(channel=channel).get("channel") or {}).get("name")
    except Exception:
        pass
    if name:
        say = _Rec()
        assistant._run_catch_up(
            client, settings,
            {"text": f"catch me up on #{name}", "channel": channel, "user": "selftest"},
            None, prefs, _Rec(), say)
        _row("couldn't find" not in say.last.lower(), f"catch-up (plain #{name})", say.last)
    else:
        print("[SKIP] catch-up (plain #name)  -> channels:read missing; can't get the name")

    # 3. Accessibility report (deterministic scorer + canvas).
    say = _Rec()
    assistant._run_channel_report(
        client, settings, f"accessibility report on {mention}", _Rec(), say)
    _row("score" in say.last.lower(), "report", say.last)

    # 4. Fix this channel (alt text + rewrites — real LLM calls).
    say = _Rec()
    assistant._fix_channel(client, settings, None, prefs, channel, mention, say)
    _row("done" in say.last.lower() or "already looks accessible" in say.last.lower(),
         "fix-channel", say.last)

    # 5. Purge the bot's own messages we just posted (cleanup + exercises purge).
    n = purge_bot_messages(client, channel)
    _row(True, "purge cleanup", f"deleted {n} bot message(s)")

    print("\nNot covered here: live streaming round-trip + Socket Mode events "
          "(need a real user action + Assistant thread) — verify those manually.")


if __name__ == "__main__":
    main()
