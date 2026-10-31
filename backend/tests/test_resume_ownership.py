"""Resume ownership/scope checks (2026-10): two pre-existing gaps, fixed
together.

(1) start_interview's resume lookup only matched resume_id -- so an OA
attempt whose resume_id happened to point at someone else's resume (e.g.
from a future bug, or a reused id) would leak that stranger's
extracted_projects into the interview plan. Fixed by also requiring
user_id to match; a mismatch is now treated exactly like "no resume at
all" (the pre-existing graceful path), so it never reveals that a resume
with that id exists for someone else.

(2) /oa/start trusted a client-supplied resume_id outright: no check that
it belonged to the caller, nor that it was analyzed for the same
company_id being started. Fixed with an explicit
(resume_id, user_id, company_id) lookup; a mismatch is now a 404
"Resume not found" -- the same convention get_resume already uses for its
own user_id-scoped lookup, chosen over silently ignoring the bad id so a
caller never thinks a bad resume_id was accepted.

In-memory fake db (spark_support's _Coll), no real Mongo, no network, no
live AI calls. start_oa's entitlements/payment plumbing and background
section-generation task are monkeypatched out since they're unrelated to
resume ownership (same rationale test_tcs_zero_ai.py uses for bypassing
them)."""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import server
from spark_support import _Coll

USER_A = {"user_id": "userA", "name": "Alice"}
USER_B = {"user_id": "userB", "name": "Bob"}


def _fake_db(resumes=None, oa_attempts=None):
    return SimpleNamespace(
        oa_attempts=_Coll(oa_attempts or []),
        resumes=_Coll(resumes or []),
        interviews=_Coll([]),
    )


def _wire_start_oa(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server.entitlements, "maybe_reset_period", lambda user: None)
    monkeypatch.setattr(server.entitlements, "assert_company_allowed", lambda user, company_id: (True, None))
    monkeypatch.setattr(server.entitlements, "can_start_run", lambda user: (True, None, "bypass"))
    monkeypatch.setattr(server.entitlements, "PLAN_LIMITS", {})

    async def _noop_bg(*a, **k):
        return None

    monkeypatch.setattr(server, "_generate_all_sections_bg", _noop_bg)


def _wire_start_interview(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server.entitlements, "free_is_oa_only", lambda user: False)


# ---- 1. /oa/start --------------------------------------------------------

def test_oa_start_rejects_another_users_resume(monkeypatch):
    """User B tries to start an OA for Capgemini using a resume_id that
    actually belongs to user A -- must 404, never silently accept it."""
    db = _fake_db(resumes=[{"resume_id": "resA", "user_id": "userA", "company_id": "capgemini"}])
    _wire_start_oa(monkeypatch, db)
    body = server.StartOAIn(company_id="capgemini", resume_id="resA")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_oa(body, USER_B))
    assert exc.value.status_code == 404


def test_oa_start_rejects_resume_from_a_different_company(monkeypatch):
    """The resume belongs to the right user, but was analyzed for a
    different company -- must also 404."""
    db = _fake_db(resumes=[{"resume_id": "resA", "user_id": "userA", "company_id": "tcs-nqt"}])
    _wire_start_oa(monkeypatch, db)
    body = server.StartOAIn(company_id="capgemini", resume_id="resA")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_oa(body, USER_A))
    assert exc.value.status_code == 404


def test_oa_start_normal_path_is_unchanged(monkeypatch):
    """Own resume_id, matching company -- starts exactly as before."""
    db = _fake_db(resumes=[{"resume_id": "resA", "user_id": "userA", "company_id": "capgemini"}])
    _wire_start_oa(monkeypatch, db)
    body = server.StartOAIn(company_id="capgemini", resume_id="resA")
    attempt = asyncio.run(server.start_oa(body, USER_A))
    assert attempt["resume_id"] == "resA"
    assert attempt["company_id"] == "capgemini"
    assert attempt["status"] == "in_progress"


def test_oa_start_with_no_resume_id_is_unaffected(monkeypatch):
    """No resume_id at all, and no resume on file for this company either
    -- stays resume_id=None, exactly as before."""
    db = _fake_db()
    _wire_start_oa(monkeypatch, db)
    body = server.StartOAIn(company_id="capgemini", resume_id=None)
    attempt = asyncio.run(server.start_oa(body, USER_A))
    assert attempt["resume_id"] is None
    assert attempt["status"] == "in_progress"


def test_oa_start_with_no_resume_id_auto_associates_the_latest_one_on_file(monkeypatch):
    """2026-10 follow-up (hub is now the only caller of /oa/start, and it
    never collects a resume_id itself): omitting resume_id now falls back
    to this user's latest resume for this exact company, via the same
    _latest_resume_for_company helper /interview/start already uses --
    instead of silently discarding a resume analyzed earlier."""
    db = _fake_db(resumes=[
        {"resume_id": "resOld", "user_id": "userA", "company_id": "capgemini", "created_at": "2026-01-01T00:00:00+00:00"},
        {"resume_id": "resNew", "user_id": "userA", "company_id": "capgemini", "created_at": "2026-06-01T00:00:00+00:00"},
        {"resume_id": "resOtherCo", "user_id": "userA", "company_id": "tcs-nqt", "created_at": "2026-09-01T00:00:00+00:00"},
        {"resume_id": "resOtherUser", "user_id": "userB", "company_id": "capgemini", "created_at": "2026-09-01T00:00:00+00:00"},
    ])
    _wire_start_oa(monkeypatch, db)
    body = server.StartOAIn(company_id="capgemini", resume_id=None)
    attempt = asyncio.run(server.start_oa(body, USER_A))
    assert attempt["resume_id"] == "resNew"  # newest, this user, this company -- not the older one, not another company's, not another user's


def test_oa_start_explicit_resume_id_is_not_overridden_by_auto_fallback(monkeypatch):
    """An explicitly-passed resume_id still wins over whatever the
    auto-fallback would have picked -- the fallback only ever fires when
    resume_id is omitted entirely."""
    db = _fake_db(resumes=[
        {"resume_id": "resExplicit", "user_id": "userA", "company_id": "capgemini", "created_at": "2026-01-01T00:00:00+00:00"},
        {"resume_id": "resNewer", "user_id": "userA", "company_id": "capgemini", "created_at": "2026-06-01T00:00:00+00:00"},
    ])
    _wire_start_oa(monkeypatch, db)
    body = server.StartOAIn(company_id="capgemini", resume_id="resExplicit")
    attempt = asyncio.run(server.start_oa(body, USER_A))
    assert attempt["resume_id"] == "resExplicit"


# ---- 2. /interview/start --------------------------------------------------

def test_interview_start_cannot_read_another_users_resume(monkeypatch):
    """Attempt belongs to user B and carries resume_id 'resA' -- but that
    resume actually belongs to user A. start_interview must behave exactly
    as if there were no resume at all: no leaked project data reaches the
    interview plan, and the call still succeeds (the existing graceful
    no-resume path), never erroring in a way that would confirm the
    resume exists."""
    attempt = {"attempt_id": "att1", "user_id": "userB", "company_id": "capgemini",
               "company_name": "Capgemini", "resume_id": "resA"}
    db = _fake_db(
        oa_attempts=[attempt],
        resumes=[{"resume_id": "resA", "user_id": "userA",
                  "analysis": {"extracted_projects": [{"name": "Secret project"}]}}],
    )
    _wire_start_interview(monkeypatch, db)

    captured = {}

    async def _fake_call_json(system, prompt, model=None):
        captured["prompt"] = prompt
        return {"questions": []}

    monkeypatch.setattr(server, "call_json", _fake_call_json)

    doc = asyncio.run(server.start_interview(server.StartInterviewIn(attempt_id="att1"), USER_B))
    assert doc["interview_id"]
    assert "Secret project" not in captured["prompt"]


def test_interview_start_normal_path_is_unchanged(monkeypatch):
    """Own resume, matching user_id -- resume projects still reach the
    interview plan exactly as before the fix."""
    attempt = {"attempt_id": "att1", "user_id": "userA", "company_id": "capgemini",
               "company_name": "Capgemini", "resume_id": "resA"}
    db = _fake_db(
        oa_attempts=[attempt],
        resumes=[{"resume_id": "resA", "user_id": "userA",
                  "analysis": {"extracted_projects": [{"name": "Visible project"}]}}],
    )
    _wire_start_interview(monkeypatch, db)

    captured = {}

    async def _fake_call_json(system, prompt, model=None):
        captured["prompt"] = prompt
        return {"questions": []}

    monkeypatch.setattr(server, "call_json", _fake_call_json)

    asyncio.run(server.start_interview(server.StartInterviewIn(attempt_id="att1"), USER_A))
    assert "Visible project" in captured["prompt"]
