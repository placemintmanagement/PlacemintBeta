# -*- coding: utf-8 -*-
"""Integration tests for the DSA-hints detection + wiring (STAGE 2), through
the real Spark/Dave/Commit answer flow in server.py, behind HINTS_ENABLED.
Everything here is mocked (spark_world/dave_world/commit_world's own model
stubs, same pattern as test_pushback_integration.py) -- zero real OpenAI
calls, and several tests explicitly assert the model-call COUNT to prove a
hint/answer-request/confirmation turn makes none."""
import asyncio

import pytest

import server
from spark_support import world, _start as spark_start, _answer as spark_answer, _get as spark_get, _stored as spark_stored
from dave_support import dave_world, _start as dave_start, _answer as dave_answer, _get as dave_get, _stored as dave_stored
from commit_support import commit_world, _start as commit_start, _answer as commit_answer, _get as commit_get, _stored as commit_stored

dsa_hints = server.capgemini_dsa_hints

GENERIC_ANSWER = "A clear answer about my own part and the trade-off I handled."


@pytest.fixture(autouse=True)
def _hints_on(monkeypatch):
    monkeypatch.setenv("HINTS_ENABLED", "1")


def _advance_to_dsa(get_fn, answer_fn, w, iid, max_steps=40):
    view = get_fn(w, iid)
    for _ in range(max_steps):
        if view["current_question"]["stage"] == "dsa":
            return view
        q = view["current_question"]
        view = answer_fn(w, iid, q["id"], GENERIC_ANSWER)
    raise AssertionError("never reached dsa stage")


# =============================================================================
# Spark
# =============================================================================
def test_spark_hint_request_makes_zero_model_calls_and_does_not_advance_stage(world):
    doc = spark_start(world)
    iid = doc["interview_id"]
    view = _advance_to_dsa(spark_get, spark_answer, world, iid)
    q = view["current_question"]
    calls_before = len(world.model.calls)

    view2 = spark_answer(world, iid, q["id"], "can I get a hint")

    assert len(world.model.calls) == calls_before
    assert view2["stage"] == "dsa"
    assert view2["current_question"]["id"] == q["id"]  # same question still open, not advanced
    assert view2["current_question"]["prompt"] == q["prompt"]  # the problem statement is NEVER overwritten
    assert len(view2["hints"]["shown"]) == 1  # the hint is surfaced separately instead


def test_spark_hint_ladder_progresses_l1_l2_l3_then_exhausts(world):
    doc = spark_start(world)
    iid = doc["interview_id"]
    view = _advance_to_dsa(spark_get, spark_answer, world, iid)
    q = view["current_question"]
    original_prompt = q["prompt"]
    stored = spark_stored(world, iid)
    ladder = dsa_hints.get_ladder("spark", stored["dsa_problem_id"])

    for i in range(3):
        view = spark_answer(world, iid, q["id"], "give me a hint")
        assert view["hints"]["used"] == i + 1
        assert view["current_question"]["prompt"] == original_prompt  # statement never overwritten
        assert len(view["hints"]["shown"]) == i + 1
        assert view["hints"]["shown"][i]["level"] == i + 1
        assert view["hints"]["shown"][i]["text"] == ladder[i]
        assert view["hints"]["shown"][i]["lead_in"]  # non-empty lead-in recorded too
    # earlier levels are never re-sent or mutated once shown
    assert [h["text"] for h in view["hints"]["shown"]] == ladder

    exhausted = spark_answer(world, iid, q["id"], "give me a hint")
    assert exhausted["current_question"]["prompt"] == original_prompt  # still unchanged
    assert exhausted["notice"] == {"kind": "hint_exhausted", "text": dsa_hints.HINTS_EXHAUSTED_REPLY}
    assert exhausted["hints"]["used"] == 3
    assert exhausted["hints"]["available"] is False
    assert len(exhausted["hints"]["shown"]) == 3  # the exhausted reply itself is never added to "shown"


def test_spark_answer_request_is_refused_and_confirmation_is_neutral(world):
    doc = spark_start(world)
    iid = doc["interview_id"]
    view = _advance_to_dsa(spark_get, spark_answer, world, iid)
    q = view["current_question"]
    original_prompt = q["prompt"]

    refused = spark_answer(world, iid, q["id"], "just tell me the answer")
    assert refused["current_question"]["prompt"] == original_prompt  # never overwritten
    assert refused["notice"] == {"kind": "answer_request", "text": dsa_hints.ANSWER_REFUSAL}
    assert refused["hints"]["used"] == 0  # consumes no hint
    assert refused["hints"]["shown"] == []  # a refusal is never added to the persisted ladder

    neutral = spark_answer(world, iid, q["id"], "is this right")
    assert neutral["current_question"]["prompt"] == original_prompt
    assert neutral["notice"] == {"kind": "confirmation", "text": dsa_hints.CONFIRMATION_REPLY}
    assert neutral["hints"]["used"] == 0


def test_spark_real_attempt_after_a_hint_is_graded_normally_and_flags_needed_hint(world):
    doc = spark_start(world)
    iid = doc["interview_id"]
    view = _advance_to_dsa(spark_get, spark_answer, world, iid)
    q = view["current_question"]

    spark_answer(world, iid, q["id"], "I'm stuck")
    calls_before = len(world.model.calls)
    spark_answer(world, iid, q["id"], GENERIC_ANSWER)
    assert len(world.model.calls) == calls_before + 1  # the real grading call happened, exactly once

    stored = spark_stored(world, iid)
    dsa_turn = next(t for t in stored["turns"] if t["stage"] == "dsa" and t.get("flags"))
    assert dsa_turn.get("needed_hint") is True


def test_spark_hint_turn_itself_is_never_graded_and_never_in_the_report(world):
    doc = spark_start(world)
    iid = doc["interview_id"]
    view = _advance_to_dsa(spark_get, spark_answer, world, iid)
    q = view["current_question"]
    spark_answer(world, iid, q["id"], "I'm stuck")
    stored = spark_stored(world, iid)
    hint_turn = next(t for t in stored["turns"] if t.get("is_hint_turn"))
    assert hint_turn["flags"] is None
    assert hint_turn["answer"] == "I'm stuck"
    report_answers = server._spark_report_answers(stored["turns"])
    assert all(a["answer"] != "I'm stuck" for a in report_answers)  # the hint request never reaches the report


def test_spark_problem_statement_is_unchanged_after_multiple_hints_and_notices(world):
    """Explicit, dedicated check (beyond the inline assertions already in
    the ladder/notice tests above): the DSA problem statement text is
    byte-identical before and after a full round of hints, an answer
    request, and a confirmation request."""
    doc = spark_start(world)
    iid = doc["interview_id"]
    view = _advance_to_dsa(spark_get, spark_answer, world, iid)
    q = view["current_question"]
    original_prompt = q["prompt"]

    for text in ("give me a hint", "give me a hint", "give me a hint", "give me a hint",
                "just tell me the answer", "is this right"):
        view = spark_answer(world, iid, q["id"], text)
        assert view["current_question"]["prompt"] == original_prompt
        assert view["current_question"]["id"] == q["id"]


def test_spark_hints_shown_survive_a_refresh(world):
    doc = spark_start(world)
    iid = doc["interview_id"]
    view = _advance_to_dsa(spark_get, spark_answer, world, iid)
    q = view["current_question"]
    original_prompt = q["prompt"]

    spark_answer(world, iid, q["id"], "give me a hint")
    spark_answer(world, iid, q["id"], "give me a hint")

    refreshed = spark_get(world, iid)
    assert refreshed["current_question"]["prompt"] == original_prompt  # statement intact
    assert refreshed["hints"]["used"] == 2
    assert len(refreshed["hints"]["shown"]) == 2
    stored = spark_stored(world, iid)
    ladder = dsa_hints.get_ladder("spark", stored["dsa_problem_id"])
    assert [h["text"] for h in refreshed["hints"]["shown"]] == ladder[:2]
    assert all(h["lead_in"] for h in refreshed["hints"]["shown"])

    # a THIRD refresh-like read (idle ping, which also goes through
    # _capgemini_tag_view) must show the identical shown list too.
    idle_view = asyncio.run(server.interview_idle(iid, world.user))
    assert idle_view["hints"]["shown"] == refreshed["hints"]["shown"]


def test_spark_notice_does_not_survive_a_refresh(world):
    """Unlike a hint, the one-off answer-request/confirmation notice is
    NOT persisted -- a refresh must not show it again."""
    doc = spark_start(world)
    iid = doc["interview_id"]
    view = _advance_to_dsa(spark_get, spark_answer, world, iid)
    q = view["current_question"]
    view2 = spark_answer(world, iid, q["id"], "just tell me the answer")
    assert "notice" in view2

    refreshed = spark_get(world, iid)
    assert "notice" not in refreshed


def test_spark_hint_penalizes_only_the_dsa_score_component(world):
    doc = spark_start(world)
    iid = doc["interview_id"]
    view = _advance_to_dsa(spark_get, spark_answer, world, iid)
    q = view["current_question"]
    spark_answer(world, iid, q["id"], "give me a hint")  # 1 hint used
    view = spark_answer(world, iid, q["id"], GENERIC_ANSWER)
    while view["status"] == "in_progress":
        q = view["current_question"]
        view = spark_answer(world, iid, q["id"], GENERIC_ANSWER)

    stored = spark_stored(world, iid)
    score = stored["spark_score"]
    raw_dsa = server.capgemini_interview.dsa_score(stored["dsa_flags"])
    assert score["dsa"] == pytest.approx(raw_dsa * 0.9)  # 1 - 0.1*1


def test_spark_flag_off_hint_phrasing_is_graded_as_a_normal_weak_answer(world, monkeypatch):
    monkeypatch.delenv("HINTS_ENABLED", raising=False)
    doc = spark_start(world)
    iid = doc["interview_id"]
    view = _advance_to_dsa(spark_get, spark_answer, world, iid)
    q = view["current_question"]
    calls_before = len(world.model.calls)

    view2 = spark_answer(world, iid, q["id"], "can I get a hint")

    assert len(world.model.calls) == calls_before + 1  # treated as a normal (graded) answer
    assert "hints" not in view2


# NOTE: there is deliberately no in-memory-fake version of the concurrent
# double-hint-request race here. test_openai_spend_controls.py's own
# in-memory double-submit race tests only manage to interleave two
# asyncio.gather()'d coroutines because their slow model stub has a real
# `await asyncio.sleep(...)` between the claim and the grading call -- a
# hint turn makes NO model call at all (the entire point of this feature),
# so there is no await point for the fake in-memory _Coll (whose update_one
# never actually awaits network I/O) to interleave on; both coroutines run
# to completion back-to-back and both "win". That is a limitation of the
# fake harness, not a bug in _claim_turn_or_409 -- the race is proven for
# real in test_dsa_hints_real_mongo_race.py, against an actual mongod where
# the network round-trip IS a real await point.


# =============================================================================
# Dave
# =============================================================================
def test_dave_hint_request_makes_zero_model_calls_and_ladder_progresses(dave_world):
    w = dave_world
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dsa(dave_get, dave_answer, w, iid)
    q = view["current_question"]
    assert q["id"] == "dave-dsa"
    calls_before = len(w.model.calls)

    view2 = dave_answer(w, iid, q["id"], "any hint")
    assert len(w.model.calls) == calls_before
    assert view2["hints"]["used"] == 1

    dave_answer(w, iid, q["id"], "any hint")
    view4 = dave_answer(w, iid, q["id"], "any hint")
    assert view4["hints"]["used"] == 3
    assert view4["hints"]["available"] is False

    exhausted = dave_answer(w, iid, q["id"], "any hint")
    assert exhausted["current_question"]["prompt"] == q["prompt"]  # never overwritten
    assert exhausted["notice"] == {"kind": "hint_exhausted", "text": dsa_hints.HINTS_EXHAUSTED_REPLY}


def test_dave_hint_penalizes_dsa_complexity_score(dave_world):
    w = dave_world
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dsa(dave_get, dave_answer, w, iid)
    q = view["current_question"]
    dave_answer(w, iid, q["id"], "any hint")
    dave_answer(w, iid, q["id"], "any hint")  # 2 hints used
    view = dave_answer(w, iid, q["id"], GENERIC_ANSWER)
    while view["status"] == "in_progress":
        q = view["current_question"]
        view = dave_answer(w, iid, q["id"], GENERIC_ANSWER)

    stored = dave_stored(w, iid)
    score = stored["dave_score"]
    raw = server.capgemini_interview.dave_dsa_complexity_score(
        stored["dave_dsa_flags"], stored["dave_time_flags"], stored["dave_space_flags"])
    assert score["dsa_complexity"] == pytest.approx(raw * 0.8)  # 1 - 0.1*2


def test_dave_flag_off_equals_current_behaviour(dave_world, monkeypatch):
    w = dave_world
    monkeypatch.delenv("HINTS_ENABLED", raising=False)
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dsa(dave_get, dave_answer, w, iid)
    q = view["current_question"]
    calls_before = len(w.model.calls)
    view2 = dave_answer(w, iid, q["id"], "any hint")
    assert len(w.model.calls) == calls_before + 1
    assert "hints" not in view2


# =============================================================================
# Commit
# =============================================================================
def test_commit_hint_request_makes_zero_model_calls(commit_world):
    w = commit_world
    doc = commit_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dsa(commit_get, commit_answer, w, iid)
    q = view["current_question"]
    assert q["id"] == "commit-dsa"
    calls_before = len(w.model.calls)

    view2 = commit_answer(w, iid, q["id"], "give me a hint")
    assert len(w.model.calls) == calls_before
    assert view2["hints"]["used"] == 1


def test_commit_hint_limit_is_two_and_shared_across_dsa_and_efficiency_subquestions(commit_world):
    w = commit_world
    w.model.dsa_value = False  # approach_1 absent -> triggers the efficiency nudge sub-question
    doc = commit_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dsa(commit_get, commit_answer, w, iid)
    q = view["current_question"]
    assert q["id"] == "commit-dsa"

    view = commit_answer(w, iid, q["id"], "give me a hint")
    assert view["hints"]["used"] == 1
    view = commit_answer(w, iid, q["id"], "give me a hint")
    assert view["hints"]["used"] == 2
    assert view["hints"]["available"] is False

    # move on with a real (weak) answer -> the efficiency nudge sub-question opens
    view = commit_answer(w, iid, q["id"], GENERIC_ANSWER)
    assert view["current_question"]["id"] == "commit-dsa-efficiency"
    efficiency_prompt = view["current_question"]["prompt"]

    # the per-INTERVIEW cap (2) was already spent on the first sub-question --
    # still exhausted here, not reset per sub-question.
    exhausted = commit_answer(w, iid, view["current_question"]["id"], "give me a hint")
    assert exhausted["current_question"]["prompt"] == efficiency_prompt  # never overwritten
    assert exhausted["notice"] == {"kind": "hint_exhausted", "text": dsa_hints.HINTS_EXHAUSTED_REPLY}
    assert exhausted["hints"]["used"] == 2
    assert len(exhausted["hints"]["shown"]) == 2  # both earlier hints still there, nothing added for this one


def test_commit_hint_penalizes_dsa_complexity_score(commit_world):
    w = commit_world
    doc = commit_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dsa(commit_get, commit_answer, w, iid)
    q = view["current_question"]
    commit_answer(w, iid, q["id"], "give me a hint")  # 1 hint
    view = commit_answer(w, iid, q["id"], GENERIC_ANSWER)
    while view["status"] == "in_progress":
        q = view["current_question"]
        view = commit_answer(w, iid, q["id"], GENERIC_ANSWER)

    stored = commit_stored(w, iid)
    score = stored["commit_score"]
    raw = server.capgemini_commit.commit_dsa_complexity_score(
        stored["commit_dsa_flags"], stored["commit_efficiency_flags"],
        stored["commit_time_flags"], stored["commit_space_flags"])
    assert score["dsa_complexity"] == pytest.approx(raw * 0.9)


def test_commit_flag_off_equals_current_behaviour(commit_world, monkeypatch):
    w = commit_world
    monkeypatch.delenv("HINTS_ENABLED", raising=False)
    doc = commit_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dsa(commit_get, commit_answer, w, iid)
    q = view["current_question"]
    calls_before = len(w.model.calls)
    view2 = commit_answer(w, iid, q["id"], "give me a hint")
    assert len(w.model.calls) == calls_before + 1
    assert "hints" not in view2


# =============================================================================
# Report field (needed_hint + count)
# =============================================================================
def test_report_interview_summary_includes_hints_used_count_when_flag_on(world, monkeypatch):
    doc = spark_start(world)
    iid = doc["interview_id"]
    view = _advance_to_dsa(spark_get, spark_answer, world, iid)
    q = view["current_question"]
    spark_answer(world, iid, q["id"], "give me a hint")
    spark_answer(world, iid, q["id"], GENERIC_ANSWER)
    stored = spark_stored(world, iid)
    assert stored.get("hints_used") == 1
