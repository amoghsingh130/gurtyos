"""Render the accessible digest as a Slack canvas (canvases_create/edit).

The canvas holds *synthesized* output (allowed under the RTS no-storage rule).
Scope: canvases:write. Pin field names against docs.slack.dev during build.
"""
from __future__ import annotations


def create_accessible_digest(client, title: str, markdown: str, channel: str | None = None) -> str:
    """Create a canvas from markdown; return its link/id."""
    # TODO: confirm canvases_create signature (document_content shape:
    # {"type": "markdown", "markdown": markdown}) and whether a follow-up
    # canvases_edit is needed for large content.
    resp = client.canvases_create(
        title=title,
        document_content={"type": "markdown", "markdown": markdown},
    )
    return resp.get("canvas_id", "")
