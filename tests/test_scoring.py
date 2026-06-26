"""Unit tests for the pure accessibility-scoring functions (no MCP / network)."""
from mcp_server import scoring


def _img(alt=""):
    return {"mimetype": "image/png", "alt_txt": alt}


def test_channel_report_messy_scores_low_and_improves():
    msgs = [
        {"text": "hey team lunch in 10"},
        {"text": "", "files": [_img(), _img()]},          # 2 images, no alt text
        {"text": ("Per the SLA the API KPIs must be reconciled against the EOD ETL "
                  "pipeline before the QBR notwithstanding the aforementioned "
                  "dependencies that materially impact downstream deliverables.")},  # jargon wall
        {"text": "see the items marked in red for the blockers"},  # color-only
    ]
    rep = scoring.channel_report(msgs)
    assert rep["messages_scanned"] == 4
    assert rep["total_images"] == 2 and rep["missing_alt"] == 2
    assert rep["jargon_walls"] >= 1
    assert rep["color_only_refs"] >= 1
    # A channel with no alt text + jargon should score poorly, and the projected
    # post-fix score must be meaningfully higher.
    assert rep["score_before"] < 70
    assert rep["score_after"] > rep["score_before"]


def test_channel_report_clean_scores_high():
    msgs = [
        {"text": "The team will meet at noon. Lunch is on the way."},
        {"text": "", "files": [_img(alt="A bar chart of weekly sign-ups trending up.")]},
        {"text": "Nice work shipping the fix. Tests pass."},
    ]
    rep = scoring.channel_report(msgs)
    assert rep["missing_alt"] == 0
    assert rep["score_before"] >= 90


def test_channel_report_empty_is_safe():
    rep = scoring.channel_report([])
    assert rep["messages_scanned"] == 0
    assert rep["total_images"] == 0
    assert 0 <= rep["score_before"] <= 100


def test_format_reading_time():
    assert scoring.format_reading_time(45) == "45s"
    assert scoring.format_reading_time(130) == "2m 10s"
    assert scoring.format_reading_time(60) == "1m 0s"


def test_is_jargon_wall():
    assert scoring.is_jargon_wall(
        "Per the SLA the API KPIs must be reconciled against the EOD ETL pipeline.") is True
    assert scoring.is_jargon_wall("see you tomorrow everyone") is False


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
