"""OA and Interview as independent rounds, for Capgemini and TCS (2026-10).

Covers: POST /interview/start's new company_id body shape (use_designated
or an explicit tier), the resume-required gate for that new path, unknown-
tier and cross-company-tier rejection, a spoofed tier_source having zero
effect, the double-start guard on both /oa/start and /interview/start,
TCS's interview_not_available (for both start paths), GET /interview/list
(own-interviews-only + per-company designated tier), the new interview_id-
keyed report path (including a legacy interview doc with no tier field at
all), and a full Spark/Dave/Commit interview started from company_id+tier
with NO OA attempt at all, through to a report fetched by interview_id.

In-memory fake db (spark_support's _Coll, extended here with find()), no
real Mongo, no network. Every model call in this file is stubbed -- zero
live AI calls anywhere, including in the full-flow tests' report step.
"""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import server
from spark_support import PROJECTS, _Coll
from spark_support import world as spark_world  # noqa: F401
from spark_support import _run_to_end as _spark_run_to_end
from dave_support import dave_world  # noqa: F401
from dave_support import _run_to_end as _dave_run_to_end
from commit_support import commit_world  # noqa: F401
from commit_support import _run_to_end as _commit_run_to_end

USER_A = {"user_id": "userA", "name": "Alice"}
USER_B = {"user_id": "userB", "name": "Bob"}


def _fake_db(**colls):
    base = dict(oa_attempts=_Coll([]), interviews=_Coll([]), resumes=_Coll([]), reports=_Coll([]))
    base.update(colls)
    return SimpleNamespace(**base)


def _wire(monkeypatch, db, free_oa_only=False):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server.entitlements, "free_is_oa_only", lambda user: free_oa_only)


def _resume(user_id="userA", company_id="capgemini", created_at="2026-01-01T00:00:00"):
    return {"resume_id": f"res-{user_id}-{company_id}", "user_id": user_id, "company_id": company_id,
            "created_at": created_at, "analysis": {"extracted_projects": PROJECTS}}


async def _fake_call_json(system, prompt, **kwargs):
    return {"overall_verdict": "borderline", "overall_score": 50, "narrative": "n",
            "weakest_dimension": "", "strongest_dimension": "", "next_steps": []}


# ---- best_cleared_tier: per-company dispatch, ties, no attempts, other users

def test_best_cleared_tier_capgemini_picks_the_highest_across_attempts(monkeypatch):
    db = _fake_db(oa_attempts=_Coll([
        {"attempt_id": "a1", "user_id": "userA", "company_id": "capgemini", "capgemini_tier": {"tier": "spark"}},
        {"attempt_id": "a2", "user_id": "userA", "company_id": "capgemini", "capgemini_tier": {"tier": "commit"}},
        {"attempt_id": "a3", "user_id": "userB", "company_id": "capgemini", "capgemini_tier": {"tier": "commit"}},
    ]))
    monkeypatch.setattr(server, "db", db)
    assert asyncio.run(server.best_cleared_tier("userA", "capgemini")) == "commit"


def test_best_cleared_tier_ignores_other_users_attempts(monkeypatch):
    db = _fake_db(oa_attempts=_Coll([
        {"attempt_id": "a1", "user_id": "userB", "company_id": "capgemini", "capgemini_tier": {"tier": "commit"}},
    ]))
    monkeypatch.setattr(server, "db", db)
    assert asyncio.run(server.best_cleared_tier("userA", "capgemini")) is None


def test_best_cleared_tier_no_attempts_at_all(monkeypatch):
    db = _fake_db()
    monkeypatch.setattr(server, "db", db)
    assert asyncio.run(server.best_cleared_tier("userA", "capgemini")) is None
    assert asyncio.run(server.best_cleared_tier("userA", "tcs-nqt")) is None


def test_best_cleared_tier_tie_resolves_to_the_shared_tier(monkeypatch):
    db = _fake_db(oa_attempts=_Coll([
        {"attempt_id": "a1", "user_id": "userA", "company_id": "capgemini", "capgemini_tier": {"tier": "dave"}},
        {"attempt_id": "a2", "user_id": "userA", "company_id": "capgemini", "capgemini_tier": {"tier": "dave"}},
    ]))
    monkeypatch.setattr(server, "db", db)
    assert asyncio.run(server.best_cleared_tier("userA", "capgemini")) == "dave"


def test_best_cleared_tier_tcs_not_qualified_counts_as_none(monkeypatch):
    db = _fake_db(oa_attempts=_Coll([
        {"attempt_id": "a1", "user_id": "userA", "company_id": "tcs-nqt",
         "tcs_tier": {"tier": "not_qualified"}},
    ]))
    monkeypatch.setattr(server, "db", db)
    assert asyncio.run(server.best_cleared_tier("userA", "tcs-nqt")) is None


def test_best_cleared_tier_tcs_picks_the_best_real_track(monkeypatch):
    db = _fake_db(oa_attempts=_Coll([
        {"attempt_id": "a1", "user_id": "userA", "company_id": "tcs-nqt", "tcs_tier": {"tier": "ninja"}},
        {"attempt_id": "a2", "user_id": "userA", "company_id": "tcs-nqt", "tcs_tier": {"tier": "not_qualified"}},
        {"attempt_id": "a3", "user_id": "userA", "company_id": "tcs-nqt", "tcs_tier": {"tier": "digital"}},
    ]))
    monkeypatch.setattr(server, "db", db)
    assert asyncio.run(server.best_cleared_tier("userA", "tcs-nqt")) == "digital"


def test_best_cleared_tier_non_tiered_company_returns_none(monkeypatch):
    db = _fake_db(oa_attempts=_Coll([{"attempt_id": "a1", "user_id": "userA", "company_id": "infosys"}]))
    monkeypatch.setattr(server, "db", db)
    assert asyncio.run(server.best_cleared_tier("userA", "infosys")) is None


# ---- company_id start: resume / tier validation ----------------------------

def test_company_id_start_requires_a_resume(monkeypatch):
    db = _fake_db()
    _wire(monkeypatch, db)
    body = server.StartInterviewIn(company_id="capgemini", tier="spark")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, USER_A))
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "resume_required"


def test_unknown_tier_rejected(monkeypatch):
    db = _fake_db(resumes=_Coll([_resume()]))
    _wire(monkeypatch, db)
    body = server.StartInterviewIn(company_id="capgemini", tier="not-a-real-tier")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, USER_A))
    assert exc.value.detail["code"] == "unknown_tier"


def test_tier_from_another_company_rejected(monkeypatch):
    """"prime" is a real TCS track name, but Capgemini has no such tier."""
    db = _fake_db(resumes=_Coll([_resume()]))
    _wire(monkeypatch, db)
    body = server.StartInterviewIn(company_id="capgemini", tier="prime")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, USER_A))
    assert exc.value.detail["code"] == "unknown_tier"


def test_invalid_start_body_rejected_when_selector_is_ambiguous(monkeypatch):
    db = _fake_db(resumes=_Coll([_resume()]))
    _wire(monkeypatch, db)
    for body in (
        server.StartInterviewIn(company_id="capgemini"),                                    # neither selector
        server.StartInterviewIn(company_id="capgemini", use_designated=True, tier="spark"),  # both selectors
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.start_interview(body, USER_A))
        assert exc.value.detail["code"] == "invalid_start_body"


def test_no_designated_tier_when_oa_never_cleared_one(monkeypatch):
    db = _fake_db(
        resumes=_Coll([_resume()]),
        oa_attempts=_Coll([{"attempt_id": "a1", "user_id": "userA", "company_id": "capgemini",
                            "status": "completed", "capgemini_tier": {"tier": None}}]),
    )
    _wire(monkeypatch, db)
    body = server.StartInterviewIn(company_id="capgemini", use_designated=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, USER_A))
    assert exc.value.detail["code"] == "no_designated_tier"


def test_use_designated_picks_the_best_tier_across_every_oa_attempt(monkeypatch):
    """OA can be retaken any number of times -- the best tier EVER cleared
    wins, not just the most recent attempt's."""
    db = _fake_db(
        resumes=_Coll([_resume()]),
        oa_attempts=_Coll([
            {"attempt_id": "a1", "user_id": "userA", "company_id": "capgemini",
             "status": "completed", "capgemini_tier": {"tier": "spark"}},
            {"attempt_id": "a2", "user_id": "userA", "company_id": "capgemini",
             "status": "completed", "capgemini_tier": {"tier": "commit"}},  # a later, better retake
        ]),
    )
    _wire(monkeypatch, db)
    body = server.StartInterviewIn(company_id="capgemini", use_designated=True)
    doc = asyncio.run(server.start_interview(body, USER_A))
    stored = next(d for d in db.interviews.docs if d["interview_id"] == doc["interview_id"])
    assert stored["tier"] == "commit" and stored["tier_source"] == "oa_designated"


def test_spoofed_tier_source_is_ignored(monkeypatch):
    """There is no tier_source body field at all -- pydantic silently drops
    it, and the server always computes tier_source itself from HOW the
    tier was resolved, never from client input."""
    db = _fake_db(
        resumes=_Coll([_resume()]),
        oa_attempts=_Coll([{"attempt_id": "a1", "user_id": "userA", "company_id": "capgemini",
                            "status": "completed", "capgemini_tier": {"tier": "spark"}}]),
    )
    _wire(monkeypatch, db)
    body = server.StartInterviewIn.model_validate(
        {"company_id": "capgemini", "use_designated": True, "tier_source": "chosen"}
    )
    assert not hasattr(body, "tier_source")
    doc = asyncio.run(server.start_interview(body, USER_A))
    stored = next(d for d in db.interviews.docs if d["interview_id"] == doc["interview_id"])
    assert stored["tier_source"] == "oa_designated"  # never the spoofed "chosen"


# ---- TCS: no interview phase, either start path ----------------------------

def test_tcs_company_id_start_has_no_interview_phase(monkeypatch):
    db = _fake_db()
    _wire(monkeypatch, db)
    body = server.StartInterviewIn(company_id="tcs-nqt", use_designated=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, USER_A))
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "interview_not_available"


def test_tcs_attempt_id_start_is_also_blocked(monkeypatch):
    db = _fake_db(oa_attempts=_Coll([{"attempt_id": "a1", "user_id": "userA", "company_id": "tcs-nqt",
                                       "status": "completed"}]))
    _wire(monkeypatch, db)
    body = server.StartInterviewIn(attempt_id="a1")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, USER_A))
    assert exc.value.detail["code"] == "interview_not_available"


# ---- double-start guards ----------------------------------------------------

def test_oa_double_start_returns_409_with_existing_attempt_id(monkeypatch):
    db = _fake_db(oa_attempts=_Coll([{"attempt_id": "existing1", "user_id": "userA",
                                       "company_id": "capgemini", "status": "in_progress"}]))
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server.entitlements, "maybe_reset_period", lambda user: None)
    monkeypatch.setattr(server.entitlements, "assert_company_allowed", lambda user, company_id: (True, None))
    monkeypatch.setattr(server.entitlements, "can_start_run", lambda user: (True, None, "bypass"))
    monkeypatch.setattr(server.entitlements, "PLAN_LIMITS", {})
    body = server.StartOAIn(company_id="capgemini")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_oa(body, USER_A))
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "oa_already_in_progress"
    assert exc.value.detail["attempt_id"] == "existing1"


def test_oa_double_start_does_not_block_a_second_user_or_a_completed_one(monkeypatch):
    db = _fake_db(oa_attempts=_Coll([{"attempt_id": "done1", "user_id": "userA",
                                       "company_id": "capgemini", "status": "completed"}]))
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server.entitlements, "maybe_reset_period", lambda user: None)
    monkeypatch.setattr(server.entitlements, "assert_company_allowed", lambda user, company_id: (True, None))
    monkeypatch.setattr(server.entitlements, "can_start_run", lambda user: (True, None, "bypass"))
    monkeypatch.setattr(server.entitlements, "PLAN_LIMITS", {})

    async def _noop_bg(*a, **k):
        return None
    monkeypatch.setattr(server, "_generate_all_sections_bg", _noop_bg)

    attempt = asyncio.run(server.start_oa(server.StartOAIn(company_id="capgemini"), USER_A))
    assert attempt["status"] == "in_progress"  # a completed attempt never blocks a fresh one


def test_interview_double_start_returns_409_with_existing_interview_id(monkeypatch):
    db = _fake_db(interviews=_Coll([{"interview_id": "existingI", "user_id": "userA",
                                      "company_id": "capgemini", "status": "in_progress"}]))
    _wire(monkeypatch, db)
    body = server.StartInterviewIn(company_id="capgemini", tier="spark")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, USER_A))
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "interview_already_in_progress"
    assert exc.value.detail["interview_id"] == "existingI"


# ---- ownership --------------------------------------------------------------

def test_user_b_cannot_read_user_as_interview_report(monkeypatch):
    db = _fake_db(interviews=_Coll([{"interview_id": "iA", "user_id": "userA", "attempt_id": None,
                                      "company_id": "capgemini", "company_name": "Capgemini",
                                      "mode": "spark", "status": "completed", "answers": [],
                                      "tier": "spark", "tier_source": "chosen"}]))
    monkeypatch.setattr(server, "db", db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.interview_report("iA", USER_B))
    assert exc.value.status_code == 404


def test_user_b_cannot_start_an_interview_from_user_as_attempt(monkeypatch):
    db = _fake_db(oa_attempts=_Coll([{"attempt_id": "a1", "user_id": "userA", "company_id": "infosys",
                                       "company_name": "Infosys", "status": "completed"}]))
    _wire(monkeypatch, db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(server.StartInterviewIn(attempt_id="a1"), USER_B))
    assert exc.value.status_code == 404


# ---- GET /interview/list ----------------------------------------------------

def test_interview_list_shows_only_own_interviews_and_per_company_availability(monkeypatch):
    db = _fake_db(interviews=_Coll([
        {"interview_id": "iA", "user_id": "userA", "company_id": "capgemini", "tier": "spark",
         "tier_source": "chosen", "status": "completed", "created_at": "2026-01-01T00:00:00"},
        {"interview_id": "iB", "user_id": "userB", "company_id": "capgemini", "tier": "dave",
         "tier_source": "oa_designated", "status": "in_progress", "created_at": "2026-01-02T00:00:00"},
    ]))
    monkeypatch.setattr(server, "db", db)
    result = asyncio.run(server.list_my_interviews(USER_A))
    assert [i["interview_id"] for i in result["interviews"]] == ["iA"]
    companies = {c["company_id"]: c for c in result["companies"]}
    assert companies["tcs-nqt"]["interview_available"] is False
    assert companies["capgemini"]["interview_available"] is True
    assert companies["capgemini"]["designated_tier"] is None  # no OA attempt in this fixture


# ---- report: legacy interview doc with no tier field -----------------------

def test_legacy_interview_doc_without_tier_field_still_works(monkeypatch):
    db = _fake_db(
        oa_attempts=_Coll([{"attempt_id": "a1", "user_id": "userA", "company_id": "capgemini",
                            "company_name": "Capgemini", "status": "completed",
                            "capgemini_tier": {"tier": "dave", "lpa": 5.75}}]),
        interviews=_Coll([{"interview_id": "iLegacy", "user_id": "userA", "attempt_id": "a1",
                           "company_name": "Capgemini", "mode": "dave", "status": "completed",
                           "answers": [], "state": {"status": "completed"}}]),  # no tier/tier_source at all
    )
    monkeypatch.setattr(server, "db", db)

    async def _fake_review(attempt_id, user):
        return {"verdict": "clear", "composite_score": 0.8, "weakest_section": "", "section_results": {}}
    monkeypatch.setattr(server, "oa_review", _fake_review)
    monkeypatch.setattr(server, "call_json", _fake_call_json)

    report = asyncio.run(server.interview_report("iLegacy", USER_A))
    assert report["tier"] == "dave"      # fell back to the attempt's own capgemini_tier
    assert report["tier_source"] is None  # a genuinely new concept -- never fabricated for old data
    assert report["interview_id"] == "iLegacy"
    assert report["attempt_id"] == "a1"


def test_old_attempt_id_keyed_report_route_is_actually_wired(monkeypatch):
    """Regression guard for a pre-existing decorator bug: @api.get("/report/
    {attempt_id}") used to sit on the WRONG function (_build_tcs_template_
    report, a plain helper, not a route), leaving final_report undecorated
    and effectively unreachable over HTTP. Confirms the real route table
    now maps this path to final_report."""
    matched = [r for r in server.app.routes if getattr(r, "path", None) == "/api/report/{attempt_id}"]
    assert matched, "/report/{attempt_id} is not registered as a route at all"
    assert all(r.endpoint is server.final_report for r in matched)


# ---- attempt_id path is unchanged ------------------------------------------

def test_attempt_id_start_path_is_unchanged_for_a_generic_company(monkeypatch):
    db = _fake_db(oa_attempts=_Coll([{"attempt_id": "a1", "user_id": "userA", "company_id": "infosys",
                                       "company_name": "Infosys", "status": "completed"}]))
    _wire(monkeypatch, db)

    async def _fake_plan(system, prompt, **kwargs):
        return {"questions": [{"id": "q1", "kind": "fundamentals", "prompt": "Tell me about yourself.",
                                "expected_signals": []}]}
    monkeypatch.setattr(server, "call_json", _fake_plan)

    doc = asyncio.run(server.start_interview(server.StartInterviewIn(attempt_id="a1"), USER_A))
    assert doc["attempt_id"] == "a1"
    assert doc["company_id"] == "infosys"  # new, additive field; nothing existing removed
    assert doc["status"] == "in_progress"
    assert doc["questions"][0]["id"] == "q1"


# ---- full Spark/Dave/Commit flow from company_id+tier, no OA attempt ------

def _start_via_company_id(w, tier):
    w.db.resumes.docs.append(_resume(user_id="u1"))
    return asyncio.run(server.start_interview(server.StartInterviewIn(company_id="capgemini", tier=tier), w.user))


def test_spark_full_flow_from_company_id_with_no_oa_attempt(spark_world, monkeypatch):
    w = spark_world
    doc = _start_via_company_id(w, "spark")
    iid = doc["interview_id"]
    stored = next(d for d in w.db.interviews.docs if d["interview_id"] == iid)
    assert stored["attempt_id"] is None and stored["tier"] == "spark" and stored["tier_source"] == "chosen"

    _spark_run_to_end(w, iid)

    monkeypatch.setattr(server, "call_json", _fake_call_json)
    report = asyncio.run(server.interview_report(iid, w.user))
    assert report["interview_id"] == iid
    assert report["oa_summary"] == {"skipped": True}
    assert report["interview_summary"]["skipped"] is False
    assert report["tier"] == "spark" and report["tier_source"] == "chosen"


def test_dave_full_flow_from_company_id_with_no_oa_attempt(dave_world, monkeypatch):
    w = dave_world
    doc = _start_via_company_id(w, "dave")
    iid = doc["interview_id"]
    stored = next(d for d in w.db.interviews.docs if d["interview_id"] == iid)
    assert stored["attempt_id"] is None and stored["tier"] == "dave"

    _dave_run_to_end(w, iid)

    monkeypatch.setattr(server, "call_json", _fake_call_json)
    report = asyncio.run(server.interview_report(iid, w.user))
    assert report["interview_id"] == iid
    assert report["oa_summary"] == {"skipped": True}
    assert report["interview_summary"]["skipped"] is False


def test_commit_full_flow_from_company_id_with_no_oa_attempt(commit_world, monkeypatch):
    w = commit_world
    doc = _start_via_company_id(w, "commit")
    iid = doc["interview_id"]
    stored = next(d for d in w.db.interviews.docs if d["interview_id"] == iid)
    assert stored["attempt_id"] is None and stored["tier"] == "commit"

    _commit_run_to_end(w, iid)

    monkeypatch.setattr(server, "call_json", _fake_call_json)
    report = asyncio.run(server.interview_report(iid, w.user))
    assert report["interview_id"] == iid
    assert report["oa_summary"] == {"skipped": True}
    assert report["interview_summary"]["skipped"] is False
