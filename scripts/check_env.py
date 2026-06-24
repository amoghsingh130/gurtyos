"""Pre-flight credential + dependency check. Run from the project root:

    .venv/bin/python scripts/check_env.py

Prints only token prefixes / pass-fail — never full secrets. Safe to re-run.
The Anthropic check makes one tiny Haiku call (a few tokens, ~$0).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import dotenv_values

PLACEHOLDERS = {
    "SLACK_BOT_TOKEN": "xoxb-...",
    "SLACK_APP_TOKEN": "xapp-...",
    "ANTHROPIC_API_KEY": "sk-ant-...",
}

# 0. Catch un-replaced placeholders before wasting an API round-trip.
vals = dotenv_values(".env")
stale = [k for k, ph in PLACEHOLDERS.items() if vals.get(k, "") == ph]
if stale:
    print("✗ .env still has placeholder values for:", ", ".join(stale))
    print("  Open .env and paste the real tokens, then re-run.")
    sys.exit(1)

from config import load_settings
s = load_settings()
print(f"[1] config OK   bot={s.slack_bot_token[:9]}… app={s.slack_app_token[:8]}… "
      f"anthropic={s.anthropic_api_key[:11]}…")

from mcp_server import scoring
print(f"[2] MCP scorer OK   contrast(#000,#fff)={scoring.wcag_contrast('#000000', '#FFFFFF')}")

import anthropic
try:
    c = anthropic.Anthropic(api_key=s.anthropic_api_key)
    m = c.messages.create(model="claude-haiku-4-5", max_tokens=5,
                          messages=[{"role": "user", "content": "Reply with: ok"}])
    from guardrails import estimate_cost
    cost = estimate_cost("claude-haiku-4-5", m.usage.input_tokens, m.usage.output_tokens)
    print(f"[3] Anthropic OK   in/out={m.usage.input_tokens}/{m.usage.output_tokens} tok "
          f"cost=${cost:.6f}")
except Exception as e:
    print("[3] FAIL Anthropic:", type(e).__name__, getattr(e, "message", e))

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
try:
    r = WebClient(token=s.slack_bot_token).auth_test()
    print(f"[4] Slack bot OK   team={r['team']} user=@{r['user']} bot_id={r.get('bot_id')}")
except SlackApiError as e:
    print("[4] FAIL Slack bot:", e.response.get("error"))

try:
    # app-level token: validates connections:write by issuing a Socket Mode URL
    r = WebClient().apps_connections_open(app_token=s.slack_app_token)
    print(f"[5] Slack app-token OK   socket url issued={str(r.get('url','')).startswith('wss')}")
except SlackApiError as e:
    print("[5] FAIL Slack app-token:", e.response.get("error"))
