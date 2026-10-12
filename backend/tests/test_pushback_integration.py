# -*- coding: utf-8 -*-
"""Integration tests for FEATURE B (pushback.py) wired through the real
Dave/Commit answer flow in server.py, behind PUSHBACK_ENABLED (and
HUMANIZE_ENABLED, since pass/clarification short-circuits are shared
infrastructure pushback's call sites reuse)."""
import asyncio

import pytest

import server
from dave_support import dave_world, _start as dave_start, _answer as dave_answer, _get as dave_get, _stored as dave_stored
from commit_support import commit_world, _start as commit_start, _answer as commit_answer, _get as commit_get, _stored as commit_stored


@pytest.fixture(autouse=True)
def _flags_on(monkeypatch):
    monkeypatch.setenv("HUMANIZE_ENABLED", "1")
    monkeypatch.setenv("PUSHBACK_ENABLED", "1")


WRONG_LONG_ANSWER = ("I think the way to approach this would be to consider several different angles and "
                    "walk through my reasoning carefully before settling on a final answer here.")  # 15+ words, deliberately vague
CORRECT_ANSWER = "A clear, correct, specific answer naming the exact key points the grader is looking for."


def _advance_to_dave_cs_main(w, iid):
    view = dave_get(w, iid)
    for _ in range(60):
        q = view["current_question"]
        if q["stage"] == "cs_fundamentals" and not q["id"].endswith("-nudge") and not q["id"].endswith("-pushback"):
            return view
        view = dave_answer(w, iid, q["id"], "A clear answer about my own part and the trade-off I handled.")
    raise AssertionError("never reached dave cs_fundamentals main question")


def test_dave_wrong_answer_triggers_exactly_one_pushback_then_wrong_again_moves_on(dave_world):
    w = dave_world
    w.model.cs_value = False  # zero key points present
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dave_cs_main(w, iid)
    q = view["current_question"]
    view2 = dave_answer(w, iid, q["id"], WRONG_LONG_ANSWER)
    assert view2["current_question"]["id"].endswith("-pushback")
    # second attempt, still wrong -- moves on, no second pushback
    view3 = dave_answer(w, iid, view2["current_question"]["id"], WRONG_LONG_ANSWER)
    assert not view3["current_question"]["id"].endswith("-pushback")
    stored = dave_stored(w, iid)
    pushback_turn = next(t for t in stored["turns"] if t.get("needed_hint"))
    assert pushback_turn.get("needed_hint") is True
    assert not any(pushback_turn["flags"].values())  # still zero credit either way


def test_dave_wrong_then_correct_credits_hint_and_marks_needed_hint(dave_world):
    w = dave_world
    w.model.cs_value = False
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dave_cs_main(w, iid)
    q = view["current_question"]
    view2 = dave_answer(w, iid, q["id"], WRONG_LONG_ANSWER)
    assert view2["current_question"]["id"].endswith("-pushback")
    w.model.cs_value = True  # second attempt now earns every key point
    dave_answer(w, iid, view2["current_question"]["id"], CORRECT_ANSWER)
    stored = dave_stored(w, iid)
    pushback_turn = next(t for t in stored["turns"] if t.get("needed_hint"))
    assert pushback_turn["needed_hint"] is True
    assert all(v == server.capgemini_pushback.HINT_CREDIT for v in pushback_turn["flags"].values())


def test_dave_partial_answer_never_triggers_pushback(dave_world, monkeypatch):
    """A mixed grader result (some key points present) must never trigger
    pushback -- simulated here by monkeypatching normalize_cs_flags for one
    call to return a partial result, since the model stub only supports an
    all-or-nothing cs_value."""
    w = dave_world
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dave_cs_main(w, iid)
    q = view["current_question"]

    real_normalize = server.capgemini_interview.normalize_cs_flags

    def partial_once(raw, n, answer):
        flags, rejections = real_normalize(raw, n, answer)
        keys = list(flags.keys())
        if keys:
            flags[keys[0]] = True  # force exactly one key point present
        return flags, rejections

    monkeypatch.setattr(server.capgemini_interview, "normalize_cs_flags", partial_once)
    w.model.cs_value = False
    view2 = dave_answer(w, iid, q["id"], WRONG_LONG_ANSWER)
    assert not view2["current_question"]["id"].endswith("-pushback")


def test_dave_short_answer_gets_existing_nudge_not_pushback(dave_world):
    w = dave_world
    w.model.cs_value = False
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dave_cs_main(w, iid)
    q = view["current_question"]
    view2 = dave_answer(w, iid, q["id"], "too short")  # under MIN_ATTEMPT_WORDS
    assert view2["current_question"]["id"].endswith("-nudge")
    assert not view2["current_question"]["id"].endswith("-pushback")


def test_dave_pushback_cap_per_interview_is_respected(dave_world, monkeypatch):
    w = dave_world
    w.model.cs_value = False
    w.model.time_value = False
    w.model.space_value = False
    monkeypatch.setattr(server.capgemini_pushback, "MAX_PUSHBACKS_PER_INTERVIEW", 1)
    doc = dave_start(w)
    iid = doc["interview_id"]
    pushbacks_seen = 0
    view = dave_get(w, iid)
    for _ in range(80):
        if view["status"] != "in_progress":
            break
        q = view["current_question"]
        view = dave_answer(w, iid, q["id"], WRONG_LONG_ANSWER)
        if (view.get("current_question") or {}).get("id", "").endswith("-pushback"):
            pushbacks_seen += 1
    assert pushbacks_seen <= 1


def test_dave_double_submit_on_a_pushback_triggering_answer_one_succeeds_one_gets_409(dave_world):
    w = dave_world
    w.model.cs_value = False
    doc = dave_start(w)
    iid = doc["interview_id"]
    view = _advance_to_dave_cs_main(w, iid)
    q = view["current_question"]

    async def submit():
        return await server.submit_interview_answer(iid, server.AnswerIn(question_id=q["id"], answer=WRONG_LONG_ANSWER), w.user)

    async def both():
        return await asyncio.gather(submit(), submit(), return_exceptions=True)

    results = asyncio.run(both())
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]
    assert len(successes) == 1
    assert len(failures) == 1


def _advance_to_commit_cs_main(w, iid):
    view = commit_get(w, iid)
    for _ in range(80):
        q = view["current_question"]
        if q["stage"] == "cs_grilling" and q["id"].endswith("-main"):
            return view
        view = commit_answer(w, iid, q["id"], "A clear answer about my own part and the trade-off I handled.")
    raise AssertionError("never reached commit cs_grilling main question")


def test_commit_wrong_answer_triggers_pushback_on_main_question_only(commit_world):
    w = commit_world
    w.model.cs_value = False
    doc = commit_start(w)
    iid = doc["interview_id"]
    view = _advance_to_commit_cs_main(w, iid)
    q = view["current_question"]
    view2 = commit_answer(w, iid, q["id"], WRONG_LONG_ANSWER)
    assert view2["current_question"]["id"].endswith("-pushback")
    # second attempt (still wrong) moves on to fu1, not a second pushback
    view3 = commit_answer(w, iid, view2["current_question"]["id"], WRONG_LONG_ANSWER)
    assert view3["current_question"]["id"].endswith("-fu1")


def test_commit_complexity_pushback_credits_hint_on_second_attempt(commit_world):
    w = commit_world
    w.model.time_value = False
    doc = commit_start(w)
    iid = doc["interview_id"]
    view = commit_get(w, iid)
    for _ in range(80):
        q = view["current_question"]
        if q["id"] == "commit-time-complexity":
            break
        view = commit_answer(w, iid, q["id"], "A clear answer about my own part and the trade-off I handled.")
    q = view["current_question"]
    view2 = commit_answer(w, iid, q["id"], WRONG_LONG_ANSWER)
    assert view2["current_question"]["id"] == "commit-time-complexity-pushback"
    w.model.time_value = True
    commit_answer(w, iid, view2["current_question"]["id"], CORRECT_ANSWER)
    stored = commit_stored(w, iid)
    pushback_turn = next(t for t in stored["turns"] if t.get("needed_hint"))
    assert all(v == server.capgemini_pushback.HINT_CREDIT for v in pushback_turn["flags"].values())
