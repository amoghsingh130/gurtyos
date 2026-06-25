"""Unit tests for the pure accessibility-scoring functions (no MCP / network)."""
from mcp_server import scoring


def test_contrast_extremes():
    assert scoring.wcag_contrast("#000000", "#ffffff") == 21.0   # max contrast
    assert scoring.wcag_contrast("#777777", "#777777") == 1.0    # identical colors


def test_grade_orders_simple_below_jargon():
    simple = "The cat sat on the mat. The dog ran."
    jargon = ("The aforementioned stakeholders must operationalize deliverables "
              "expeditiously per the SLA.")
    assert scoring.flesch_kincaid_grade(simple) < scoring.flesch_kincaid_grade(jargon)


def test_long_sentences_flags_only_long():
    text = "Short one. " + " ".join(["word"] * 25) + "."
    longs = scoring.long_sentences(text)
    assert len(longs) == 1
    assert all("Short one." != s for s in longs)


def test_jargon_candidates_finds_acronyms_and_long_words():
    out = scoring.jargon_candidates(
        "The API documentation necessitates expeditious operationalization.")
    assert "API" in out
    assert "operationalization" in out


def test_color_only_refs():
    assert scoring.color_only_refs("Click the items shown in red to proceed.")
    assert scoring.color_only_refs("This text has no color cues.") == []


def test_audit_has_all_keys():
    a = scoring.audit("Per the SLA, click the parts in green.")
    assert set(a) >= {"grade", "reading_seconds", "long_sentences",
                      "undefined_jargon", "color_only_refs", "contrast_fails"}
    assert isinstance(a["grade"], float)
    assert a["color_only_refs"]  # "in green" flagged
