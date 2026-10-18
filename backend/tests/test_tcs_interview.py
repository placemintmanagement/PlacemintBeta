"""TCS NQT interview: end-to-end coverage through the real route-handler-
equivalent call path (server.start_interview / submit_interview_answer /
get_interview / interview_report), with TCS_INTERVIEW_ENABLED turned on via
the tcs_world fixture (tests/tcs_support.py) and the AI boundary faked
(call_json_gpt stubbed; call_json stubbed per-test for the report step).
No real Mongo, no network, no live AI call anywhere in this file.

Covers: a full deterministic run for each of the three tiers (ninja/
digital/prime) reaching a final report; flag-OFF behaviour byte-identical
to the pre-existing blocked response (also covered, pre-existing, by
test_interview_oa_independence.py's test_tcs_company_id_start_has_no_
interview_phase/test_tcs_attempt_id_start_is_also_blocked -- neither of
those sets TCS_INTERVIEW_ENABLED, so they already pin this contract);
resume-required before a TCS interview can start; tier_source for both
use_designated=true and an explicit tier choice (not gated by the OA
result); the 409 double-start guard; and the report route building on the
report-cache-gate fix (test_report_cache_gate_tcs_mode.py, commit 1).
"""
import asyncio

import pytest
from fastapi import HTTPException

import server
from tcs_support import (  # noqa: F401
    TCS_PROJECTS, TCS_PROJECTS_SINGLE_LANGUAGE, _answer, _get, _run_to_end, _start, _stored, _tcs_attempt, tcs_world,
)

TCS_DURATION_SECONDS = 45 * 60  # 25 (TR) + 10 (MR) + 10 (HR) minutes


def _fake_final_report_call_json(monkeypatch, captured=None):
    async def fake_call_json(system, prompt, **kwargs):
        return {"overall_verdict": "borderline", "overall_score": 55, "narrative": "n",
                "weakest_dimension": "", "strongest_dimension": "", "next_steps": []}
    monkeypatch.setattr(server, "call_json", fake_call_json)

    if captured is not None:
        real = server.final_report_prompt

        def spy(company, resume_analysis, oa_summary, interview_summary):
            captured.append({"company": company, "oa_summary": oa_summary, "interview_summary": interview_summary})
            return real(company, resume_analysis, oa_summary, interview_summary)

        monkeypatch.setattr(server, "final_report_prompt", spy)


def _report_by_interview_id(w, iid, monkeypatch, captured=None):
    _fake_final_report_call_json(monkeypatch, captured)
    return asyncio.run(server.interview_report(iid, w.user))


# ---- full deterministic end-to-end run, one per tier -----------------------

@pytest.mark.parametrize("tier", ["ninja", "digital", "prime"])
def test_full_tcs_interview_reaches_a_final_report(tcs_world, monkeypatch, tier):
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    assert started["mode"] == "tcs"
    assert started["stage"] == "technical"
    assert started["status"] == "in_progress"

    steps = _run_to_end(tcs_world, iid)
    assert steps[-1]["status"] == "completed"
    assert steps[-1]["stage"] == "done"
    assert steps[-1]["closing_message"]

    stored = _stored(tcs_world, iid)
    assert stored["tier"] == tier
    assert stored["status"] == "completed"
    assert stored["tcs_score"]["interview"] >= 0.0
    assert len(stored["answers"]) == len(stored["turns"])
    # Never leaks grading internals to the client view at any step.
    for step in steps:
        assert "flags" not in step and "key_points" not in step and "tcs_score" not in step

    captured = []
    report = _report_by_interview_id(tcs_world, iid, monkeypatch, captured)
    assert report["interview_summary"]["completed"] is True
    assert report["interview_summary"]["skipped"] is False
    assert report["interview_summary"]["avg_score"] > 0
    assert captured[0]["oa_summary"] == {"skipped": True}  # no OA attempt behind this interview
    assert report["tier"] == tier
    assert report["tier_source"] == "chosen"


def test_tr_stage_covers_every_tr_topic_at_prime_tier(tcs_world):
    """Sanity check on question selection: Prime's Technical stage visits
    every one of the six TR dimensions (resume_language + the five bank
    topics), confirming the stage/weight table and the bank draws line up."""
    started = _start(tcs_world, company_id="tcs-nqt", tier="prime")
    iid = started["interview_id"]
    stored_before = _stored(tcs_world, iid)
    topics = {q["topic"] for q in stored_before["technical_questions"]}
    assert topics == {"resume_language", "oop", "dbms_sql", "os", "networking", "coding_discussion"}


# ---- flag OFF: byte-identical to the pre-existing blocked response --------

def test_flag_off_tcs_interview_start_is_blocked_exactly_as_before(monkeypatch):
    """TCS_INTERVIEW_ENABLED unset (the default) -- same exact
    {"code": "interview_not_available", "message": "This company does not
    have an interview phase yet."} / 400 contract that
    test_interview_oa_independence.py's test_tcs_company_id_start_has_no_
    interview_phase already pins (that test never sets the flag either),
    confirmed again here directly against the exact response shape."""
    monkeypatch.delenv("TCS_INTERVIEW_ENABLED", raising=False)
    from types import SimpleNamespace
    from spark_support import _Coll
    fake = SimpleNamespace(interviews=_Coll(), oa_attempts=_Coll(), reports=_Coll(), resumes=_Coll())
    monkeypatch.setattr(server, "db", fake)
    monkeypatch.setattr(server.entitlements, "free_is_oa_only", lambda user: False)
    body = server.StartInterviewIn(company_id="tcs-nqt", tier="ninja")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, {"user_id": "u1", "name": "Priya"}))
    assert exc.value.status_code == 400
    assert exc.value.detail == {
        "code": "interview_not_available",
        "message": "This company does not have an interview phase yet.",
    }


def test_flag_off_valid_interview_tiers_and_tier_start_fn_are_also_unchanged():
    """Direct unit check on the two helpers hook 2/hook 3 extended --
    with the flag off, both behave exactly as they did before TCS had any
    interview branch at all."""
    import os
    assert os.environ.get("TCS_INTERVIEW_ENABLED") in (None, "", "0", "false")
    assert server._valid_interview_tiers("tcs-nqt") == []
    assert server._tier_start_fn("tcs-nqt", "ninja") is None


# ---- resume required before a TCS interview can start ----------------------

def test_resume_required_before_a_tcs_interview_can_start(tcs_world):
    tcs_world.db.resumes.docs.clear()  # no resume on file for this user+company
    body = server.StartInterviewIn(company_id="tcs-nqt", tier="ninja")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, tcs_world.user))
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "resume_required"


# ---- tier_source: oa_designated vs chosen, student's free choice ----------

def test_use_designated_true_produces_the_oa_designated_tier(tcs_world):
    tcs_world.db.oa_attempts.docs.append({
        "attempt_id": "att-oa-1", "user_id": "u1", "company_id": "tcs-nqt",
        "tcs_tier": {"tier": "digital"},
    })
    started = _start(tcs_world, company_id="tcs-nqt", use_designated=True)
    assert started["tier"] == "digital"
    assert started["tier_source"] == "oa_designated"


def test_explicit_tier_choice_is_not_gated_by_the_oa_result(tcs_world):
    """The OA designated 'ninja', but the student is free to choose any of
    the three tiers regardless -- same permissiveness Capgemini already has
    for an explicit tier= with use_designated=false."""
    tcs_world.db.oa_attempts.docs.append({
        "attempt_id": "att-oa-1", "user_id": "u1", "company_id": "tcs-nqt",
        "tcs_tier": {"tier": "ninja"},
    })
    started = _start(tcs_world, company_id="tcs-nqt", tier="prime")
    assert started["tier"] == "prime"
    assert started["tier_source"] == "chosen"


def test_unknown_tier_is_rejected(tcs_world):
    body = server.StartInterviewIn(company_id="tcs-nqt", tier="not-a-real-tier")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, tcs_world.user))
    assert exc.value.detail["code"] == "unknown_tier"


# ---- 409 in-progress guard --------------------------------------------------

def test_409_starting_a_second_tcs_interview_while_one_is_in_progress(tcs_world):
    _start(tcs_world, company_id="tcs-nqt", tier="ninja")
    body = server.StartInterviewIn(company_id="tcs-nqt", tier="digital")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, tcs_world.user))
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "interview_already_in_progress"


# ---- report route (builds on commit 1's report-cache gate fix) ------------

def test_report_is_not_cached_while_the_tcs_interview_is_open(tcs_world, monkeypatch):
    tcs_world.db.reports.docs.append({
        "interview_id": "will-not-match", "user_id": "u1",
        "report": {"stale": True}, "interview_summary": {"skipped": True},
    })
    started = _start(tcs_world, company_id="tcs-nqt", tier="ninja")
    iid = started["interview_id"]
    _answer(tcs_world, iid, started["current_question"]["id"], "A thoughtful, specific first answer.")

    captured = []
    report = _report_by_interview_id(tcs_world, iid, monkeypatch, captured)

    assert captured[0]["interview_summary"]["skipped"] is False
    assert captured[0]["interview_summary"]["completed"] is False
    assert report.get("report", {}).get("stale") is None
    assert _stored(tcs_world, iid)["status"] == "in_progress"
    matching_cache = [d for d in tcs_world.db.reports.docs if d.get("interview_id") == iid]
    assert matching_cache == []  # nothing cached for THIS interview while it's open


def test_report_route_closes_an_abandoned_tcs_interview_and_caches_the_result(tcs_world, monkeypatch):
    started = _start(tcs_world, company_id="tcs-nqt", tier="ninja")
    iid = started["interview_id"]
    _answer(tcs_world, iid, started["current_question"]["id"], "Hello there.")  # then abandoned
    tcs_world.clock.t += TCS_DURATION_SECONDS + 1  # deadline passes; nobody reopens it
    assert _stored(tcs_world, iid)["status"] == "in_progress"  # nothing has closed it yet

    report = _report_by_interview_id(tcs_world, iid, monkeypatch)

    stored = _stored(tcs_world, iid)
    assert stored["status"] == "timed_out" and stored["state"]["timed_out"] is True
    assert stored["current_question"] is None
    assert report["interview_summary"]["completed"] is False
    matching_cache = [d for d in tcs_world.db.reports.docs if d.get("interview_id") == iid]
    assert len(matching_cache) == 1  # now cached, with the interview included


# ---- opener question: fewer than 2 inferable languages ---------------------

def test_opener_asks_directly_when_fewer_than_two_languages_are_inferable(tcs_world):
    tcs_world.db.resumes.docs[0]["analysis"]["extracted_projects"] = TCS_PROJECTS_SINGLE_LANGUAGE
    started = _start(tcs_world, company_id="tcs-nqt", tier="ninja")
    assert started["current_question"]["prompt"] == (
        "Which two programming languages would you like to be evaluated in during this interview, and why?"
    )
