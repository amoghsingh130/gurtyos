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


def accessibility_report_markdown(channel_name: str, rep: dict) -> str:
    """Screen-reader-friendly markdown for a Channel Accessibility Report canvas.
    `rep` is the dict from mcp_server.scoring.channel_report. Plain language, headed
    sections, no color/emoji-only meaning — the agent dogfoods its own a11y rules."""
    alt_pct = (round(100 * rep["missing_alt"] / rep["total_images"])
               if rep["total_images"] else 0)
    return (
        f"# Accessibility report — #{channel_name}\n\n"
        f"## Accessibility score: {rep['score_before']} out of 100\n"
        f"If the agent applies its fixes, this channel reaches "
        f"**{rep['score_after']} out of 100**.\n\n"
        f"## What we scanned\n"
        f"- Messages scanned: {rep['messages_scanned']}\n"
        f"- Images: {rep['total_images']}, of which {rep['missing_alt']} "
        f"have no alt text ({alt_pct}%)\n"
        f"- Average reading grade: {rep['avg_grade']} "
        f"(target is grade {rep['target_grade']})\n"
        f"- Jargon-heavy messages: {rep['jargon_walls']}\n"
        f"- Phrases that rely on color alone: {rep['color_only_refs']}\n\n"
        f"## Why this matters\n"
        f"Images without alt text and text above the reading target exclude blind, "
        f"low-vision, neurodivergent, and non-native-English teammates. Under the "
        f"Americans with Disabilities Act and Section 508, accessible workplace "
        f"communication is a legal requirement, not a nicety.\n\n"
        f"## Fixes the agent can apply\n"
        f"- Write alt text for the {rep['missing_alt']} images that need it.\n"
        f"- Rewrite the {rep['jargon_walls']} jargon-heavy messages to grade "
        f"{rep['target_grade']}.\n"
        f"- Flag the {rep['color_only_refs']} color-only phrases for a human to reword.\n"
    )


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
