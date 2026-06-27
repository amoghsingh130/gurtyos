"""De-clog the gurtYos Assistant tab: delete every message the bot posted in a DM.

A bot token can't delete the *user's* own prompts, so those remain — this clears the
piled-up digests, reports, and canvas links. Pass a DM id (D…) or a user id (U…),
in which case the bot opens the IM first.

Run from the repo root:
    python -m seed.purge_dm D0123ABCD      # a DM conversation id
    python -m seed.purge_dm U0123ABCD      # a user id -> opens the IM, then purges
"""
from __future__ import annotations

import sys

from slack_sdk import WebClient

from config import load_settings
from slack_io.purge import purge_bot_messages


def _resolve_dm(client: WebClient, ident: str) -> str:
    """A user id (U…/W…) -> the IM channel id; anything else is used as-is."""
    if ident[:1] in ("U", "W"):
        return client.conversations_open(users=ident)["channel"]["id"]
    return ident


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print("usage: python -m seed.purge_dm <DM_ID | USER_ID>")
        return
    client = WebClient(token=load_settings().slack_bot_token)
    channel = _resolve_dm(client, args[0])
    print(f"deleted {purge_bot_messages(client, channel)} bot messages from {channel}")


if __name__ == "__main__":
    main()
