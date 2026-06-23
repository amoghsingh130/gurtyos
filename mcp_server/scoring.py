"""Pure scoring functions (no MCP / Slack deps) so they're unit-testable."""
from __future__ import annotations

WORDS_PER_MINUTE = 200


def flesch_kincaid_grade(text: str) -> float:
    """US reading grade level. Uses textstat if available, else a rough fallback."""
    try:
        import textstat
        return float(textstat.flesch_kincaid_grade(text))
    except Exception:
        # Fallback so the server still runs without textstat installed.
        words = max(len(text.split()), 1)
        sentences = max(text.count(".") + text.count("!") + text.count("?"), 1)
        return round(0.39 * (words / sentences), 1)


def reading_seconds(text: str) -> int:
    words = len(text.split())
    return int(round(words / WORDS_PER_MINUTE * 60))


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def wcag_contrast(fg_hex: str, bg_hex: str) -> float:
    """WCAG 2.x contrast ratio (1..21)."""
    l1, l2 = sorted((_luminance(fg_hex), _luminance(bg_hex)), reverse=True)
    return round((l1 + 0.05) / (l2 + 0.05), 2)
