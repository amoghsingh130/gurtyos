"""Render the accessible digest as a Slack canvas.

Verified against docs.slack.dev (2026-06-24):
- canvases.create(title, document_content={"type":"markdown","markdown": ...},
  channel_id=...) -> {"ok", "canvas_id"}. FREE teams (incl. some sandboxes)
  REQUIRE channel_id, so always pass it.
- canvases.edit(canvas_id, changes=[{operation, section_id?, document_content}]) ->
  {"ok"}. One operation per call; use operation="insert_at_end" to append.
- Scope: canvases:write.

The canvas holds *synthesized* output (allowed under the RTS no-storage rule).
"""
from __future__ import annotations


def create_accessible_digest(client, title: str, markdown: str, channel_id: str) -> str:
    """Create a canvas from markdown; return its canvas_id."""
    resp = client.canvases_create(
        title=title,
        document_content={"type": "markdown", "markdown": markdown},
        channel_id=channel_id,  # required on free teams / sandboxes
    )
    return resp["canvas_id"]


def append_markdown(client, canvas_id: str, markdown: str) -> None:
    """Append a markdown section to an existing canvas (one op per call)."""
    client.canvases_edit(
        canvas_id=canvas_id,
        changes=[
            {
                "operation": "insert_at_end",
                "document_content": {"type": "markdown", "markdown": markdown},
            }
        ],
    )
