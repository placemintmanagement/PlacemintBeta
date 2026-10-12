# -*- coding: utf-8 -*-
"""Integration tests for FEATURE A (humanize.py) wired through the real
Spark/Dave/Commit answer flow in server.py, behind HUMANIZE_ENABLED. Reuses
the existing spark_support/dave_support/commit_support fixtures and model
stubs so these exercise the actual server code path, not just the pure
humanize.py functions (already covered by test_humanize.py)."""
import asyncio

import pytest

import server
from dave_support import dave_world, _start as dave_start, _answer as dave_answer, _get as dave_get, _stored as dave_stored
from commit_support import commit_world, _start as commit_start, _answer as commit_answer, _get as commit_get


@pytest.fixture(autouse=True)
def _flags_on(monkeypatch):
    monkeypatch.setenv("HUMANIZE_ENABLED", "1")
    monkeypatch.setenv("PUSHBACK_ENABLED", "0")


def _advance_to_stage(w, iid, target_stage, answer_text="A clear answer about my own part and the trade-off I handled."):
    """Drives real answers until current_question reaches target_stage.
    "dsa" is used for the no-model-call assertions below because, unlike
    project1/project2, it has no LLM-written follow-up step -- its next
    question is always a fixed transition, so a pass/clarification there
    can be asserted to add literally zero model calls, not just zero
    GRADER calls."""
    view = dave_get(w, iid)
    for _ in range(40):
        q = view["current_question"]
        if q["stage"] == target_stage:
            return view
        view = dave_answer(w, iid, q["id"], answer_text)
    raise AssertionError(f"never reached stage {target_stage}")


def test_clarification_request_returns_rephrase_once_and_calls_no_grader(dave_world):
    w = dave_world
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = _advance_to_stage(w, iid, "dsa")
    q = view["current_question"]
    calls_before = len(w.model.calls)
    turn_count_before = dave_stored(w, iid)["turn_count"]
    view2 = dave_answer(w, iid, q["id"], "can you repeat that please?")
    assert len(w.model.calls) == calls_before  # no model call at all
    assert view2["current_question"]["id"] == q["id"]  # same question, not advanced
    stored = dave_stored(w, iid)
    assert stored["turn_count"] == turn_count_before  # consumed no quota
    # a SECOND clarification request on the SAME question falls through to
    # real grading instead of granting a second free rephrase
    view3 = dave_answer(w, iid, q["id"], "sorry can you repeat that again?")
    assert len(w.model.calls) == calls_before + 1
    assert view3["current_question"]["id"] != q["id"]  # advanced for real this time


def test_pass_phrase_scores_zero_and_advances_with_no_grader_call(dave_world):
    w = dave_world
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = _advance_to_stage(w, iid, "dsa")
    q = view["current_question"]
    calls_before = len(w.model.calls)
    view2 = dave_answer(w, iid, q["id"], "I don't know")
    assert len(w.model.calls) == calls_before  # no model call at all
    assert view2["current_question"]["id"] != q["id"]  # advanced
    stored = dave_stored(w, iid)
    last_turn = stored["turns"][-1]
    assert last_turn["verdict"] == "No problem, let's move on."
    assert last_turn["flags"] == {} or not any(last_turn["flags"].values())


def test_pass_phrase_does_not_trigger_the_short_answer_nudge(dave_world):
    """A pass is short by construction, but must bypass the existing nudge
    path entirely (per spec: a pass scores 0 and advances, with no nudge)."""
    w = dave_world
    doc = dave_start(w)
    iid = doc["interview_id"]
    for _ in range(40):
        view = dave_get(w, iid)
        if view["status"] != "in_progress":
            break
        q = view["current_question"]
        if q["stage"] == "cs_fundamentals" and not q["id"].endswith("-nudge"):
            calls_before = len(w.model.calls)
            view2 = dave_answer(w, iid, q["id"], "skip")
            assert len(w.model.calls) == calls_before
            assert "nudge" not in (view2["current_question"] or {}).get("id", "")
            return
        dave_answer(w, iid, q["id"], "A clear answer about my own part and the trade-off I handled.")
    pytest.skip("did not reach cs_fundamentals in this run")


def test_acknowledgement_never_repeats_back_to_back_across_a_full_run(dave_world):
    w = dave_world
    doc = dave_start(w)
    iid = doc["interview_id"]
    prompts = []
    view = dave_get(w, iid)
    steps = 0
    while view["status"] == "in_progress" and steps < 60:
        q = view["current_question"]
        view = dave_answer(w, iid, q["id"], "A clear answer about my own part and the trade-off I handled.")
        if view.get("current_question"):
            prompts.append(view["current_question"]["prompt"])
        steps += 1
    # extract whichever acknowledgement (if any) opens each prompt
    import departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview.humanize as h
    acks_seen = [next((a for a in h.NEUTRAL_ACKNOWLEDGEMENTS if p.startswith(a)), None) for p in prompts]
    non_none = [a for a in acks_seen if a is not None]
    assert len(non_none) > 0  # humanizer is actually firing
    for a, b in zip(non_none, non_none[1:]):
        assert a != b


def test_time_awareness_line_appears_exactly_once_entering_hr_with_correct_minutes(dave_world):
    w = dave_world
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = dave_get(w, iid)
    time_line_count = 0
    steps = 0
    while view["status"] == "in_progress" and steps < 60:
        q = view["current_question"]
        view = dave_answer(w, iid, q["id"], "A clear answer about my own part and the trade-off I handled.")
        prompt = (view.get("current_question") or {}).get("prompt", "")
        if "minutes left" in prompt:
            time_line_count += 1
            assert (view["current_question"]["stage"]) == "hr"
        steps += 1
    assert time_line_count == 1


def test_equivalence_same_fixture_two_interviews_flags_differ_only_in_prefix(dave_world, monkeypatch):
    """The exact test that catches prompt contamination: FEATURE A must only
    decorate the CLIENT-FACING text, never the text later reused as grading
    context. Runs the identical scripted answer sequence as two separate
    interviews on the same fixture (one per flag state -- _DaveModel's
    canned answers are a pure function of prompt text/call-count-within-
    category, not shared state across interviews) and asserts the model
    made the same number of grading calls and the final score is
    identical."""
    w = dave_world
    base = dict(w.db.oa_attempts.docs[0])
    w.db.oa_attempts.docs[0]["attempt_id"] = "att-off"
    w.db.oa_attempts.docs.append({**base, "attempt_id": "att-on"})
    monkeypatch.setenv("HUMANIZE_ENABLED", "0")
    doc_off = dave_start(w, attempt_id="att-off")
    iid_off = doc_off["interview_id"]
    view = dave_get(w, iid_off)
    steps = 0
    while view["status"] == "in_progress" and steps < 60:
        q = view["current_question"]
        view = dave_answer(w, iid_off, q["id"], "A clear answer about my own part and the trade-off I handled.")
        steps += 1
    calls_off = len(w.model.calls)
    score_off = dave_stored(w, iid_off)["dave_score"]

    monkeypatch.setenv("HUMANIZE_ENABLED", "1")
    doc_on = dave_start(w, attempt_id="att-on")
    iid_on = doc_on["interview_id"]
    view = dave_get(w, iid_on)
    steps = 0
    while view["status"] == "in_progress" and steps < 60:
        q = view["current_question"]
        view = dave_answer(w, iid_on, q["id"], "A clear answer about my own part and the trade-off I handled.")
        steps += 1
    score_on = dave_stored(w, iid_on)["dave_score"]

    # same number of grading calls were made (humanizer added zero model
    # calls), and the final score is identical -- the ONLY difference
    # flags-on introduces here (no pushback, no pass, no clarification) is
    # cosmetic text on the client view, which must not reach the grader or
    # change the outcome.
    assert len(w.model.calls) == calls_off * 2
    assert score_on == score_off


def test_idle_endpoint_fires_once_per_question_and_respects_two_minute_floor(dave_world):
    w = dave_world
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = dave_get(w, iid)
    q = view["current_question"]
    idle_view = asyncio.run(server.interview_idle(iid, w.user))
    assert idle_view["current_question"]["id"] == q["id"]
    assert idle_view["current_question"]["prompt"] == server.capgemini_humanize.IDLE_LINE
    # a second idle call on the SAME question does not re-fire the idle line
    idle_view2 = asyncio.run(server.interview_idle(iid, w.user))
    assert idle_view2["current_question"]["prompt"] != server.capgemini_humanize.IDLE_LINE
    # under the 2-minute floor, idle never fires at all
    w.clock.t = w.db.interviews.docs[0]["state"]["deadline_at"] - 60
    dave_answer(w, iid, q["id"], "A clear answer about my own part and the trade-off I handled.")
    view3 = dave_get(w, iid)
    q3 = view3["current_question"]
    idle_view3 = asyncio.run(server.interview_idle(iid, w.user))
    assert idle_view3["current_question"]["prompt"] != server.capgemini_humanize.IDLE_LINE


def test_commit_clarification_resolves_bank_native_id_not_positional_id(commit_world):
    """Regression for the rephrase-key resolution: a clarification on a
    Commit CS main question must resolve to the underlying Java/OOPs bank
    id (e.g. "java-7"), not the positional client id ("commit-cs-0-main"),
    and must NOT accidentally match a follow-up sub-id to the main
    question's rephrase."""
    w = commit_world
    doc = commit_start(w)
    iid = doc["interview_id"]
    view = commit_get(w, iid)
    steps = 0
    while view["status"] == "in_progress" and steps < 80:
        q = view["current_question"]
        if q["stage"] == "cs_grilling" and q["id"].endswith("-main"):
            rephrased = commit_answer(w, iid, q["id"], "could you rephrase that for me?")
            assert rephrased["current_question"]["id"] == q["id"]
            assert rephrased["current_question"]["prompt"] != q["prompt"]
            return
        view = commit_answer(w, iid, q["id"], "A clear answer about my own part and the trade-off I handled.")
        steps += 1
    pytest.skip("did not reach cs_grilling main question in this run")
