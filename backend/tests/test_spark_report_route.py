"""Report-route behaviour for Capgemini Spark attempts: an abandoned (deadline-
passed) interview is finalized by the report route, and the report is not
cached while the interview is open. Shares fixtures with test_spark_interview.py
via spark_support.py. Mocked clock, stubbed model, in-memory fake db."""
import asyncio
import json

import server
from spark_support import CLOSE_PRIYA, _answer, _get, _run_to_end, _start, _stored, world  # noqa: F401
from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini import (
    capgemini_interview as ci,  # noqa: F401
)


def _fake_review(attempt_id, user):
    async def review(a, u):
        return {"verdict": "borderline", "composite_score": 0.5, "weakest_section": "",
                "section_results": {}}
    return review(attempt_id, user)


def _report(w, monkeypatch, captured=None):
    monkeypatch.setattr(server, "oa_review", _fake_review)

    async def fake_call_json(system, prompt, **kwargs):
        return {"overall_verdict": "borderline", "overall_score": 50, "narrative": "n",
                "weakest_dimension": "", "strongest_dimension": "", "next_steps": []}

    monkeypatch.setattr(server, "call_json", fake_call_json)
    if captured is not None:
        real = server.final_report_prompt

        def spy(company, resume_analysis, oa_summary, interview_summary):
            captured.append({"company": company, "interview_summary": interview_summary})
            return real(company, resume_analysis, oa_summary, interview_summary)

        monkeypatch.setattr(server, "final_report_prompt", spy)
    return asyncio.run(server.final_report("att1", w.user))


# ---- abandoned interviews: the report route closes an expired one ----------
def test_report_route_closes_an_expired_abandoned_interview(world, monkeypatch):
    iid = _start(world)["interview_id"]
    _answer(world, iid, "spark-intro", "Hello there.")  # then the candidate walks away
    world.clock.t += 35 * 60 + 1                          # deadline passes; nobody reopens it
    assert _stored(world, iid)["status"] == "in_progress"  # nothing has closed it yet

    report = _report(world, monkeypatch)

    stored = _stored(world, iid)
    assert stored["status"] == "timed_out" and stored["state"]["timed_out"] is True
    assert stored["current_question"] is None
    assert report["interview_summary"]["completed"] is False
    assert _get(world, iid)["closing_message"] == CLOSE_PRIYA


def test_finalization_is_idempotent_and_does_not_rewrite_a_closed_interview(world, monkeypatch):
    iid = _start(world)["interview_id"]
    _answer(world, iid, "spark-intro", "Hello there.")
    world.clock.t += 35 * 60 + 1
    _report(world, monkeypatch)
    first = _stored(world, iid)

    world.clock.t += 60
    _report(world, monkeypatch)  # cached report, but finalization still runs first
    again = _stored(world, iid)
    assert again["completed_at"] == first["completed_at"]
    assert again["turn_count"] == first["turn_count"]
    assert again["status"] == "timed_out"


def test_report_input_for_a_finished_spark_interview(world, monkeypatch):
    iid = _start(world)["interview_id"]
    steps = _run_to_end(world, iid)
    captured = []
    _report(world, monkeypatch, captured)
    summary = captured[0]["interview_summary"]
    stored = _stored(world, iid)
    graded = [t for t in stored["turns"] if t.get("flags")]
    expected_avg = round(sum(round(100 * ci.flags_score(t["flags"])) for t in graded) / len(graded), 1)
    assert summary["skipped"] is False and summary["completed"] is True
    assert summary["avg_score"] == expected_avg and summary["avg_score"] > 0
    assert len(summary["verdicts"]) == len(graded)  # the intro is not scored
    rendered = json.dumps(captured[0], default=str)
    assert "Priya" not in rendered and "flags" not in rendered and "spark_score" not in rendered
    assert "flag_review" not in rendered  # rejected-flag records never reach the report input
    assert steps[-1]["status"] == "completed"


# ---- report caching for Spark attempts ---------------------------------------
def test_report_is_not_cached_while_the_spark_interview_is_open(world, monkeypatch):
    world.db.reports.docs.append({"attempt_id": "att1", "user_id": "u1", "report": {"stale": True},
                                  "interview_summary": {"skipped": True}})  # cached before the interview
    iid = _start(world)["interview_id"]
    captured = []
    report = _report(world, monkeypatch, captured)
    assert captured[0]["interview_summary"]["skipped"] is False  # not served from the stale cache
    assert report.get("report", {}).get("stale") is None
    new_docs = [d for d in world.db.reports.docs if d.get("report") != {"stale": True}]
    assert new_docs == []  # nothing new was cached while the interview is open
    assert _stored(world, iid)["status"] == "in_progress"


def test_report_opened_before_the_end_is_regenerated_with_the_interview_after_it(world, monkeypatch):
    iid = _start(world)["interview_id"]
    _answer(world, iid, "spark-intro", "Hello there.")
    _report(world, monkeypatch)  # opened before the interview ends
    assert world.db.reports.docs == []  # nothing cached while open

    _run_to_end(world, iid)  # the interview ends
    captured = []
    _report(world, monkeypatch, captured)
    summary = captured[0]["interview_summary"]
    assert summary["completed"] is True and summary["skipped"] is False and summary["avg_score"] > 0
    assert len(world.db.reports.docs) == 1  # now cached, with the interview in it


def test_cached_report_from_before_the_interview_is_dropped_when_the_interview_ends(world, monkeypatch):
    world.db.reports.docs.append({"attempt_id": "att1", "user_id": "u1", "report": {"stale": True},
                                  "interview_summary": {"skipped": True}})
    iid = _start(world)["interview_id"]
    world.clock.t += 35 * 60 + 1  # the interview is abandoned and times out
    captured = []
    report = _report(world, monkeypatch, captured)
    assert _stored(world, iid)["status"] == "timed_out"
    assert captured[0]["interview_summary"]["skipped"] is False  # regenerated, interview included
    assert report.get("report", {}).get("stale") is None
