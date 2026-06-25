"""Tests for the deterministic, LLM-free pieces of the proactive autonomy beat and
the Assistant's natural-language preference parsing — the new 'closes the loop' /
'agent acts on its own' logic. No Slack or Anthropic calls."""
from config import Settings
from prefs.store import Prefs
from handlers.proactive import _looks_hard
from handlers.assistant import _parse_pref_updates

_SETTINGS = Settings(slack_bot_token="x", slack_app_token="x", anthropic_api_key="x")

_JARGON_WALL = (
    "Per the SLA the API KPIs must be reconciled against the EOD ETL pipeline before "
    "the QBR, and the stakeholders expect the RCA documentation finalized notwithstanding "
    "the aforementioned dependencies which materially impact the downstream deliverables "
    "across the entire organization and its many partner teams."
)
# Plain chatter that runs long with NO terminal punctuation — the false-positive the
# grade-only screen produced (FK grade balloons to ~13 without sentence breaks).
_CASUAL_RUNON = (
    "hey everyone just a quick heads up that the lunch order is going out in ten minutes "
    "so let me know what you want and i will add it to the list thanks so much you all "
    "are the best and have a great rest of your day"
)


def test_jargon_wall_is_hard():
    assert _looks_hard(_SETTINGS, _JARGON_WALL) is True


def test_plain_runon_is_not_hard():
    # The whole point of the precision-first screen: don't nudge on plain chatter.
    assert _looks_hard(_SETTINGS, _CASUAL_RUNON) is False


def test_short_message_is_never_hard():
    assert _looks_hard(_SETTINGS, "lgtm thanks team") is False


def test_parse_language_change():
    updates, note = _parse_pref_updates("now in Spanish", Prefs(target_grade=8))
    assert updates.get("language") == "Spanish"
    assert updates.get("target_grade") == 8  # grade carried so set() keeps it
    assert note and "Spanish" in note


def test_parse_explicit_reading_level():
    updates, note = _parse_pref_updates("set my reading level to 5", Prefs(target_grade=8))
    assert updates == {"target_grade": 5}
    assert note and "5" in note


def test_parse_simpler_lowers_grade():
    updates, _ = _parse_pref_updates("can you make it simpler", Prefs(target_grade=8))
    assert updates["target_grade"] == 6  # -2, floored at 3


def test_parse_no_command_returns_nothing():
    updates, note = _parse_pref_updates("Catch me up accessibly on #general", Prefs())
    assert updates == {}
    assert note is None
