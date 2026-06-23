"""Download a Slack file's bytes via url_private_download (needs bot token header)."""
from __future__ import annotations

import httpx

from config import Settings


def download(settings: Settings, file_obj: dict) -> tuple[bytes, str]:
    """Return (bytes, media_type) for a Slack file object. media_type is the
    file's mimetype (e.g. 'image/png'), suitable for a Claude image block."""
    url = file_obj["url_private_download"]
    media_type = file_obj.get("mimetype", "application/octet-stream")
    resp = httpx.get(
        url,
        headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
        follow_redirects=True,
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.content, media_type
