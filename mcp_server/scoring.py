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


# --- Accessibility audit (text-level) ------------------------------------
# Pure heuristics so the audit is deterministic and unit-testable. These feed
# the agent's draft -> audit -> revise loop as concrete, actionable findings.

import re as _re

LONG_SENTENCE_WORDS = 20  # plain-language guidance: keep sentences short
_COLOR_WORDS = ("red", "green", "blue", "yellow", "orange", "purple", "pink")
# "see the items in red", "the green button", "highlighted in blue" — color used
# to convey meaning, which excludes screen-reader / colorblind users.
_COLOR_ONLY = _re.compile(
    r"\b(?:in|the|marked|highlighted|shown|colou?red)\s+(?:%s)\b" % "|".join(_COLOR_WORDS),
    _re.IGNORECASE,
)
_ACRONYM = _re.compile(r"\b[A-Z]{2,6}s?\b")  # API, SLA, KPIs, etc.


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def long_sentences(text: str, max_words: int = LONG_SENTENCE_WORDS) -> list[str]:
    """Sentences longer than max_words — candidates to split."""
    return [s for s in _sentences(text) if len(s.split()) > max_words]


def jargon_candidates(text: str) -> list[str]:
    """Acronyms / very long words a reader may not know (deduped, capped)."""
    found: list[str] = []
    seen: set[str] = set()
    for tok in _ACRONYM.findall(text) + [w for w in text.split() if len(w.strip(".,;:()")) >= 13]:
        key = tok.strip(".,;:()").lower()
        if key and key not in seen:
            seen.add(key)
            found.append(tok.strip(".,;:()"))
    return found[:25]


def color_only_refs(text: str) -> list[str]:
    """Phrases that lean on color to carry meaning (a11y anti-pattern)."""
    return [m.group(0) for m in _COLOR_ONLY.finditer(text)]


def audit(text: str) -> dict:
    """Structured accessibility findings for `text` — the agent acts on these."""
    return {
        "grade": flesch_kincaid_grade(text),
        "reading_seconds": reading_seconds(text),
        "long_sentences": long_sentences(text),
        "undefined_jargon": jargon_candidates(text),
        "color_only_refs": color_only_refs(text),
        "contrast_fails": [],  # populated by the channel/image path when colors are known
    }


# --- Channel-level accessibility report -----------------------------------
# Aggregates the per-text heuristics above across a whole channel into one
# 0–100 accessibility score, plus a projected score if the agent's fixes were
# applied. Deterministic and pure so the on-camera before/after number is
# trustworthy and unit-testable — the same scorer the MCP server exposes.

REPORT_TARGET_GRADE = 8       # plain-language target for the channel as a whole
_JARGON_WALL_TOKENS = 3       # ≥ this many jargon tokens makes a message a "wall"
_JARGON_WALL_GRADE = 14.0     # …or a reading grade this high


def _a11y_score(*, total_images, missing_alt, has_text, avg_grade,
                jargon_walls, color_refs, target_grade=REPORT_TARGET_GRADE) -> int:
    """Weighted 0–100 accessibility score. Missing alt text is the heaviest
    penalty (a hard barrier for screen-reader users); reading grade, jargon
    walls, and color-only meaning follow."""
    s = 100.0
    if total_images:
        s -= 45.0 * (missing_alt / total_images)          # screen-reader barrier
    if has_text:
        s -= min(30.0, max(0.0, avg_grade - target_grade) * 3.0)  # readability
    s -= min(20.0, jargon_walls * 4.0)                    # undefined jargon
    s -= min(5.0, color_refs * 2.0)                       # color-only meaning
    return max(0, round(s))


def channel_report(messages: list[dict], target_grade: int = REPORT_TARGET_GRADE) -> dict:
    """Aggregate accessibility report for a channel's recent messages.

    `messages` are raw Slack message dicts (each may have `text` and `files`).
    Returns counts, a current `score_before`, and a `score_after` projecting the
    score once the agent's auto-fixes (alt text, plain-language rewrites) land —
    color-only/contrast issues are flagged but not assumed auto-fixed, so `after`
    stays honest rather than a perfect 100."""
    texts = [
        m.get("text", "") for m in messages
        if (m.get("text") or "").strip() and not m.get("subtype")
    ]
    images = [
        f for m in messages for f in (m.get("files") or [])
        if (f.get("mimetype") or "").startswith("image/")
    ]
    total_images = len(images)
    missing_alt = sum(1 for f in images if not (f.get("alt_txt") or "").strip())

    graded = [flesch_kincaid_grade(t) for t in texts if len(t.split()) >= 12]
    avg_grade = round(sum(graded) / len(graded), 1) if graded else 0.0
    jargon_walls = sum(
        1 for t in texts
        if len(jargon_candidates(t)) >= _JARGON_WALL_TOKENS
        or flesch_kincaid_grade(t) >= _JARGON_WALL_GRADE
    )
    color_refs = sum(len(color_only_refs(t)) for t in texts)

    before = _a11y_score(
        total_images=total_images, missing_alt=missing_alt, has_text=bool(graded),
        avg_grade=avg_grade, jargon_walls=jargon_walls, color_refs=color_refs,
        target_grade=target_grade)
    # Projected: the agent describes every image and rewrites every wall to target;
    # color-only refs remain flagged-but-unfixed. Cap at 97 (never below the current
    # score) — auto-generated alt text still warrants a human pass, so a literal 100
    # would overclaim.
    after = _a11y_score(
        total_images=total_images, missing_alt=0, has_text=bool(graded),
        avg_grade=float(target_grade), jargon_walls=0, color_refs=color_refs,
        target_grade=target_grade)
    after = max(before, min(97, after))

    return {
        "messages_scanned": len(messages),
        "total_images": total_images,
        "missing_alt": missing_alt,
        "avg_grade": avg_grade,
        "jargon_walls": jargon_walls,
        "color_only_refs": color_refs,
        "score_before": before,
        "score_after": after,
        "target_grade": target_grade,
    }
