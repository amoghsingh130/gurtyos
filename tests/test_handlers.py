"""Integration tests for the handler flows, driven through a fake Slack client.

These exercise the real code paths (history fetch, scoring, canvas, block building,
the 👎 learning loop) with the LLM calls mocked at the function boundary, so they're
fast, deterministic, and offline. Live LLM/MCP behavior is covered separately in
test_llm_integration.py.
"""
from __future__ import annotations

import pytest

from config import Settings
from prefs.store import PrefsStore
from fakes import FakeSlackClient, Recorder

import handlers.reactions as reactions
import handlers.assistant as assistant
import handlers.home as home
from llm.rewrite import RewriteResult


def _settings() -> Settings:
    return Settings(slack_bot_token="x", slack_app_token="x", anthropic_api_key="x",
                    demo_channels=("C0DEMO",))


def _prefs(tmp_path) -> PrefsStore:
    return PrefsStore(str(tmp_path / "prefs.db"))


def _img(alt=""):
    return {"mimetype": "image/png", "alt_txt": alt, "url_private_download": "https://x/y.png"}


# --- reactions: alt text (👁️) ------------------------------------------------

def test_run_alt_text_posts_description(monkeypatch):
    client = FakeSlackClient(history=[{"ts": "1.1", "files": [_img()]}])
    monkeypatch.setattr(reactions.files_io, "download", lambda s, f: (b"bytes", "image/png"))
    monkeypatch.setattr(reactions.alt_text, "describe", lambda *a, **k: "A bar chart trending up.")

    reactions.run_alt_text(client, _settings(), None, "C1", "1.1")

    posts = client.calls_to("chat_postMessage")
    assert len(posts) == 1
    assert "Alt text" in posts[0]["text"] and "bar chart" in posts[0]["text"]
    assert posts[0]["thread_ts"] == "1.1"


def test_run_alt_text_noop_without_image(monkeypatch):
    client = FakeSlackClient(history=[{"ts": "1.1", "text": "no image here"}])
    monkeypatch.setattr(reactions.alt_text, "describe", lambda *a, **k: pytest.fail("should not be called"))
    reactions.run_alt_text(client, _settings(), None, "C1", "1.1")
    assert not client.called("chat_postMessage")


# --- reactions: rewrite (🧩) + the 👎 learning loop --------------------------

def test_handle_rewrite_posts_grade_and_buttons(monkeypatch, tmp_path):
    client = FakeSlackClient()
    monkeypatch.setattr(reactions.messages, "fetch_thread", lambda c, ch, ts: [{"text": "jargon"}])
    monkeypatch.setattr(reactions.messages, "thread_text", lambda thread: "Per the SLA the KPIs...")
    monkeypatch.setattr(reactions.rewrite, "plain_language",
                        lambda *a, **k: RewriteResult(text="Plain version.", grade_before=22,
                                                      grade_after=6, language="English", tool_calls=2))
    reactions._handle_rewrite(client, _settings(), None, _prefs(tmp_path), "C1", "9.9", user="U1")

    post = client.calls_to("chat_postMessage")[0]
    assert "grade 22 → 6" in post["text"]
    assert any(b.get("type") == "actions" for b in post["blocks"])  # feedback buttons present


def test_feedback_down_lowers_grade_persists_and_updates_in_place(monkeypatch, tmp_path):
    client = FakeSlackClient()
    prefs = _prefs(tmp_path)
    prefs.set("U1", target_grade=8, language="English")
    monkeypatch.setattr(reactions.messages, "fetch_thread", lambda c, ch, ts: [{"text": "jargon"}])
    monkeypatch.setattr(reactions.messages, "thread_text", lambda thread: "jargon wall text")

    captured = {}

    def fake_rewrite(settings, text, target_grade=6, language="English", guard=None, on_step=None):
        captured["grade"] = target_grade
        return RewriteResult(text="Simpler.", grade_before=18, grade_after=target_grade,
                             language=language, tool_calls=1)

    monkeypatch.setattr(reactions.rewrite, "plain_language", fake_rewrite)

    reactions._rerender_simpler(client, _settings(), None, prefs,
                                value="C1:9.9", user="U1", msg_channel="C1", msg_ts="m1")

    assert prefs.get("U1").target_grade == 6          # 8 - 2, persisted
    assert captured["grade"] == 6                      # re-ran at the lowered grade
    upd = client.calls_to("chat_update")[0]
    assert upd["channel"] == "C1" and upd["ts"] == "m1"   # updated the SAME message in place
    assert "simplified" in upd["text"].lower()
    assert not client.called("chat_postMessage")       # not a new message


# --- assistant: channel accessibility report --------------------------------

def test_channel_report_scans_history_and_posts_canvas():
    history = [
        {"ts": "1", "text": "thanks team"},
        {"ts": "2", "files": [_img(), _img()]},  # 2 images, no alt text
        {"ts": "3", "text": ("Per the SLA the API KPIs must be reconciled against the EOD "
                             "ETL pipeline before the QBR notwithstanding the aforementioned "
                             "dependencies that materially impact downstream deliverables.")},
    ]
    client = FakeSlackClient(history=history, channel_name="acct-omega")
    say = Recorder()
    assistant._run_channel_report(client, _settings(), "report on <#C1|acct-omega>",
                                  set_status=Recorder(), say=say)

    assert client.called("canvases_create")
    md = client.calls_to("canvases_create")[0]["document_content"]["markdown"]
    assert "Accessibility report — #acct-omega" in md
    assert "→" in say.last and "acct-omega" in say.last  # before → after score in the summary


def test_channel_report_requires_a_channel():
    client = FakeSlackClient()
    say = Recorder()
    assistant._run_channel_report(client, _settings(), "give me a report", Recorder(), say)
    assert not client.called("canvases_create")
    assert "channel" in say.last.lower()


def test_channel_report_offers_fix_button_when_issues_exist():
    history = [{"ts": "2", "files": [_img()]},  # missing alt → there's something to fix
               {"ts": "3", "text": "thanks all"}]
    client = FakeSlackClient(history=history, channel_name="general")
    say = Recorder()
    assistant._run_channel_report(client, _settings(), "report on <#C1|general>", Recorder(), say)
    assert say.any_block_action("fix_channel")   # the "Fix this channel" button is offered


# --- assistant: "Fix this channel" applies fixes channel-wide ----------------

def test_fix_channel_describes_images_and_rewrites_walls(monkeypatch):
    history = [
        {"ts": "10", "files": [_img()]},                       # image, no alt
        {"ts": "11", "files": [_img(alt="already described")]},  # skip (has alt)
        {"ts": "12", "text": ("Per the SLA the API KPIs must be reconciled against the EOD "
                              "ETL pipeline before the QBR notwithstanding the aforementioned "
                              "dependencies materially impacting downstream deliverables.")},
        {"ts": "13", "text": "lgtm thanks"},                   # not a wall
    ]
    client = FakeSlackClient(history=history)
    alt_called, rewrite_called = [], []
    monkeypatch.setattr(assistant, "run_alt_text",
                        lambda c, s, g, ch, ts: alt_called.append(ts))
    monkeypatch.setattr(assistant, "_handle_rewrite",
                        lambda c, s, g, p, ch, ts, user=None: rewrite_called.append(ts))
    say = Recorder()
    assistant._fix_channel(client, _settings(), None, None, "C1", "<#C1>", say)

    assert alt_called == ["10"]          # only the un-alt-texted image
    assert rewrite_called == ["12"]      # only the jargon wall
    assert "Done" in say.last and "1" in say.last


def test_fix_channel_noop_when_already_accessible(monkeypatch):
    client = FakeSlackClient(history=[{"ts": "1", "text": "see you tomorrow"}])
    monkeypatch.setattr(assistant, "run_alt_text", lambda *a, **k: pytest.fail("nothing to fix"))
    monkeypatch.setattr(assistant, "_handle_rewrite", lambda *a, **k: pytest.fail("nothing to fix"))
    say = Recorder()
    assistant._fix_channel(client, _settings(), None, None, "C1", "<#C1>", say)
    assert "already looks accessible" in say.last


# --- catch-up routing: channel resolution -----------------------------------

from llm.digest import DigestResult


def _settings_no_stream() -> Settings:
    # Disable streaming so finish_error/say() are observable (no stream.stop swallow).
    return Settings(slack_bot_token="x", slack_app_token="x", anthropic_api_key="x",
                    demo_channels=("C0DEMO",), enable_task_stream=False)


def _patch_digest(monkeypatch) -> dict:
    """Stub digest.synthesize so routing tests stay offline; capture the context it got."""
    seen: dict = {}

    def fake(settings, ctx, target_grade=6, language="English", on_step=None, guard=None):
        seen["ctx"] = ctx
        return DigestResult(markdown="A simple summary.", grade=6.0, tool_calls=1)

    monkeypatch.setattr(assistant.digest, "synthesize", fake)
    return seen


_RICH = ("We shipped the auth refactor today and every test is green across the whole "
         "payments suite now.")


def test_catch_up_mention_uses_history_not_search(tmp_path, monkeypatch):
    seen = _patch_digest(monkeypatch)
    client = FakeSlackClient(history=[{"ts": "1", "user": "alice", "text": _RICH}])
    assistant.channels.reset_cache()
    say = Recorder()
    payload = {"text": "catch me up on <#C1|acct-omega>", "channel": "D1", "user": "U1"}
    assistant._run_catch_up(client, _settings_no_stream(), payload, None, _prefs(tmp_path),
                            Recorder(), say)
    assert client.calls_to("conversations_history")[0]["channel"] == "C1"
    assert "auth refactor" in seen["ctx"]            # read history, not RTS
    assert "simple summary" in say.last.lower()


def test_catch_up_plain_name_resolves_via_list(tmp_path, monkeypatch):
    seen = _patch_digest(monkeypatch)
    client = FakeSlackClient(history=[{"ts": "1", "user": "alice", "text": _RICH}],
                             channels=[{"id": "C7", "name": "acct-omega"}])
    assistant.channels.reset_cache()
    say = Recorder()
    payload = {"text": "catch me up on #acct-omega", "channel": "D1", "user": "U1"}
    assistant._run_catch_up(client, _settings_no_stream(), payload, None, _prefs(tmp_path),
                            Recorder(), say)
    assert client.called("conversations_list")
    assert client.calls_to("conversations_history")[0]["channel"] == "C7"
    assert "simple summary" in say.last.lower()


def test_catch_up_unresolved_name_is_clear_not_empty_channel(tmp_path, monkeypatch):
    # The regression guard for this session's bug: a typed #name we can't resolve must
    # say "couldn't find", NOT "not enough recent activity", and must not read history.
    _patch_digest(monkeypatch)
    client = FakeSlackClient(channels=[{"id": "C1", "name": "general"}])  # no acct-omega
    assistant.channels.reset_cache()
    say = Recorder()
    payload = {"text": "catch me up on #acct-omega", "channel": "D1", "user": "U1"}
    assistant._run_catch_up(client, _settings_no_stream(), payload, None, _prefs(tmp_path),
                            Recorder(), say)
    assert "couldn't find" in say.last.lower()
    assert "not enough recent activity" not in say.last.lower()
    assert not client.called("conversations_history")


def test_catch_up_no_channel_no_token_asks_for_channel(tmp_path, monkeypatch):
    _patch_digest(monkeypatch)
    client = FakeSlackClient()
    assistant.channels.reset_cache()
    say = Recorder()
    payload = {"text": "catch me up please", "channel": "D1", "user": "U1"}
    assistant._run_catch_up(client, _settings_no_stream(), payload, None, _prefs(tmp_path),
                            Recorder(), say)
    assert "name a channel" in say.last.lower()


def test_catch_up_no_channel_with_token_uses_rts(tmp_path, monkeypatch):
    seen = _patch_digest(monkeypatch)
    called = {}

    def fake_search(client, query, action_token):
        called["q"] = query
        return {"ok": True}

    monkeypatch.setattr(assistant.rts, "search_context", fake_search)
    monkeypatch.setattr(assistant.rts, "flatten_results", lambda resp: f"alice: {_RICH}")
    client = FakeSlackClient()
    assistant.channels.reset_cache()
    say = Recorder()
    payload = {"text": "catch me up on the migration", "channel": "D1", "user": "U1",
               "assistant_thread": {"action_token": "tok"}}
    assistant._run_catch_up(client, _settings_no_stream(), payload, None, _prefs(tmp_path),
                            Recorder(), say)
    assert called["q"] == "catch me up on the migration"
    assert not client.called("conversations_history")   # RTS path, no channel read
    assert "simple summary" in say.last.lower()


def test_catch_up_resolved_but_thin_channel_declines(tmp_path, monkeypatch):
    _patch_digest(monkeypatch)
    client = FakeSlackClient(history=[{"ts": "1", "user": "a", "text": "hi"}])
    assistant.channels.reset_cache()
    say = Recorder()
    payload = {"text": "catch me up on <#C1|quiet>", "channel": "D1", "user": "U1"}
    assistant._run_catch_up(client, _settings_no_stream(), payload, None, _prefs(tmp_path),
                            Recorder(), say)
    assert "not enough recent activity" in say.last.lower()


def test_resolve_target_mention_plain_hit_miss_and_none():
    from slack_io import channels as ch
    client = FakeSlackClient(channels=[{"id": "C9", "name": "acct-omega"}])
    ch.reset_cache()
    assert ch.resolve_target(client, "report on <#C1|general>") == ("C1", "#general", True)
    ch.reset_cache()
    assert ch.resolve_target(client, "catch me up on #acct-omega") == ("C9", "#acct-omega", True)
    ch.reset_cache()
    assert ch.resolve_target(client, "catch me up on #nope") == (None, "#nope", True)
    ch.reset_cache()
    assert ch.resolve_target(client, "explain the latest simply") == (None, None, False)


# --- impact numbers on the rewrite reply ------------------------------------

def test_rewrite_message_shows_impact_numbers():
    r = RewriteResult(text="Plain.", grade_before=22, grade_after=6, language="English",
                      tool_calls=2, seconds_before=130, seconds_after=50,
                      acronyms_defined=3, sentences_split=2)
    body, blocks = reactions._rewrite_message(r, "C1:9.9")
    ctx = [b for b in blocks if b["type"] == "context"]
    assert ctx, "impact context block present"
    txt = ctx[0]["elements"][0]["text"]
    assert "2m 10s → 50s" in txt and "saved 1m 20s" in txt
    assert "defined 3 acronyms" in txt and "split 2 long sentences" in txt


def test_rewrite_message_impact_omitted_when_zero():
    r = RewriteResult(text="x", grade_before=8, grade_after=7, language="English")
    _body, blocks = reactions._rewrite_message(r, "C1:1")
    assert not [b for b in blocks if b["type"] == "context"]


# --- assistant: helpers -----------------------------------------------------

def test_channel_label_from_mention_then_info_then_fallback():
    c_ok = FakeSlackClient(channel_name="general")
    assert assistant._channel_label(c_ok, "report on <#C1|general>", "C1") == "#general"
    assert assistant._channel_label(c_ok, "report on <#C1>", "C1") == "#general"     # via info
    c_bad = FakeSlackClient(info_raises=True)
    assert assistant._channel_label(c_bad, "report on <#C1>", "C1") == "this channel"


def test_history_context_is_chronological_and_skips_noise():
    msgs = [
        {"ts": "3", "text": "merging now", "username": "marcus"},
        {"ts": "2", "subtype": "channel_join", "text": "joined"},
        {"ts": "1", "text": "kickoff", "user": "U1"},
    ]
    ctx = assistant._history_context(msgs)
    assert ctx == "U1: kickoff\nmarcus: merging now"   # reversed, join skipped


def test_content_words_counts_after_prefix():
    assert assistant._content_words("alice: ") == 0
    assert assistant._content_words("bob: sounds good to me") == 4
    assert assistant._content_words("a: one two\nb: three four five") == 5


# --- home tab ---------------------------------------------------------------

# --- digest: reject agent narration masquerading as a summary ----------------

def test_digest_looks_like_summary_rejects_narration():
    from llm.digest import _looks_like_summary
    assert _looks_like_summary("## Standup\nThe team shipped the auth refactor today.")
    assert _looks_like_summary("word " * 60)            # long enough even without a heading
    assert not _looks_like_summary("")
    # The real Run-2 failure: short audit narration, no heading -> not a summary.
    assert not _looks_like_summary(
        "The audit flagged a grade-18 score caused by the long bullet lists being read "
        "as run-on sentences. Revising now.")


# --- "clear our chat" DM purge ----------------------------------------------

def test_purge_dm_deletes_only_bot_messages_and_reports_count():
    history = [
        {"ts": "1", "bot_id": "B1", "text": "old digest"},     # bot -> delete
        {"ts": "2", "user": "U_HUMAN", "text": "catch me up"},  # user prompt -> keep
        {"ts": "3", "user": "U_BOT", "text": "report link"},    # bot (by user_id) -> delete
    ]
    client = FakeSlackClient(history=history)
    say = Recorder()
    assistant._purge_dm(client, "D1", set_status=Recorder(), say=say)

    deleted = {kw["ts"] for kw in client.calls_to("chat_delete")}
    assert deleted == {"1", "3"}                 # human prompt untouched
    assert "2" in [m.get("ts") for m in client._history]
    assert "Cleared" in say.last and "2" in say.last


def test_purge_dm_clears_bot_replies_under_a_thread():
    history = [{"ts": "10", "user": "U_HUMAN", "text": "q?", "reply_count": 1}]
    replies = {"10": [
        {"ts": "10", "user": "U_HUMAN", "text": "q?"},
        {"ts": "11", "bot_id": "B1", "text": "bot reply"},
    ]}
    client = FakeSlackClient(history=history, replies=replies)
    assistant._purge_dm(client, "D1", set_status=Recorder(), say=Recorder())
    assert {kw["ts"] for kw in client.calls_to("chat_delete")} == {"11"}


def test_purge_regex_matches_phrasings_but_not_catchup():
    for q in ("clear our chat", "delete history", "forget our conversation",
              "wipe my messages", "clean up our chat history"):
        assert assistant._PURGE_RE.search(q), q
    for q in ("catch me up on #general", "accessibility report on #general",
              "fix #general", "explain this simply"):
        assert not assistant._PURGE_RE.search(q), q


# --- live task streaming: chunk schema --------------------------------------

def test_task_stream_normalizes_status_to_slack_enum():
    from slack_io.stream import TaskStream
    client = FakeSlackClient()
    s = TaskStream(client, "C1", "100.1")
    s._ts, s.active = "100.2", True          # pretend start() succeeded

    s.task("step", "Reading activity", "completed")
    chunk = client.calls_to("chat_appendStream")[-1]["chunks"][0]
    assert chunk["status"] == "complete"     # not the invalid "completed"
    assert chunk["type"] == "task_update" and chunk["id"] == "step"


def test_task_stream_start_and_stop_use_text_chunk_field():
    from slack_io.stream import TaskStream
    client = FakeSlackClient()
    s = TaskStream(client, "C1", "100.1")
    assert s.start("intro") is True
    assert client.calls_to("chat_startStream")[-1]["chunks"][0] == {
        "type": "markdown_text", "text": "intro"}
    s.stop("final")
    assert client.calls_to("chat_stopStream")[-1]["chunks"][0] == {
        "type": "markdown_text", "text": "final"}


def test_home_view_is_valid_and_fully_alt_texted():
    v = home._home_view()
    assert v["type"] == "home" and v["blocks"]
    imgs = [b for b in v["blocks"] if b["type"] == "image"]
    accs = [b["accessory"] for b in v["blocks"]
            if b.get("accessory", {}).get("type") == "image"]
    assert imgs and accs
    for im in imgs + accs:
        assert im.get("image_url") and im.get("alt_text"), "every image needs url + alt"
