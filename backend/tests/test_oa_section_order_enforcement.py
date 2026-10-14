"""Registry-wide coverage for submit_section's server-side ordering
enforcement (409 wrong_section_order / section_already_submitted /
attempt_not_in_progress). Loops over EVERY company in companies.COMPANIES,
not just TCS -- the fix lives in the one shared submit_section endpoint, so
every company must keep completing normally, and every company must reject
an out-of-order or repeated submit.

All real grading functions are monkeypatched to a fixed, instant result --
this test is about the ORDER/STATUS gating in submit_section, not about any
company's actual grading logic (which already has its own dedicated tests
elsewhere). No Mongo, no network, no model calls.
"""
import asyncio
import json

import pytest
from fastapi import HTTPException

import server
from companies import COMPANIES


class _FakeOAAttempts:
    def __init__(self, doc):
        self.doc = doc

    async def find_one(self, query, projection=None):
        if query.get("attempt_id") != self.doc["attempt_id"]:
            return None
        if "user_id" in query and query["user_id"] != self.doc["user_id"]:
            return None
        return json.loads(json.dumps(self.doc))

    async def update_one(self, query, update):
        self.doc = {**self.doc, **update["$set"]}


class _FakeDb:
    def __init__(self, doc):
        self.oa_attempts = _FakeOAAttempts(doc)


def _attempt_for(company):
    sections = [{**s, "questions": []} for s in company["sections"]]
    return {
        "attempt_id": "att", "user_id": "u1", "company_id": company["id"],
        "status": "in_progress", "sections": sections,
        "section_results": {}, "answers": {}, "current_section_index": 0,
    }


def _fake_result():
    # "correct": 100 (not 1) deliberately -- tcs_tiers._foundation_correct
    # sums "correct" across numerical/verbal/reasoning with no cap at each
    # section's real question count, so a small fake value (e.g. 1 per
    # section) would never clear TCS's ninja threshold (33) and the TCS
    # completion test's tier assertion would wrongly see tier=None. A big
    # fake "correct" sidesteps that without needing per-company-accurate
    # question counts, since this test is about ORDER enforcement, not
    # grading accuracy.
    return {"score": 1.0, "correct": 100, "total": 100, "passed": True}


async def _fake_async_grade(*args, **kwargs):
    return _fake_result()


def _fake_sync_grade(*args, **kwargs):
    return _fake_result()


def _patch_all_graders(monkeypatch):
    for name in (
        "_grade_coding_section", "_grade_debugging_section", "_finalize_ai_assisted_section",
        "_grade_essay_section", "_grade_speaking_section", "_grade_comm_mixed_section",
        "_grade_voice_mixed_section", "_grade_gamified_round_section",
        "_grade_capgemini_round1_section", "_grade_capgemini_round2_ai_literacy_section",
    ):
        monkeypatch.setattr(server, name, _fake_async_grade)
    for name in ("_grade_reading_listening_section", "_grade_mcq_like"):
        monkeypatch.setattr(server, name, _fake_sync_grade)


@pytest.mark.parametrize("company", COMPANIES, ids=[c["id"] for c in COMPANIES])
def test_every_company_completes_by_submitting_sections_in_order(monkeypatch, company):
    _patch_all_graders(monkeypatch)
    fake = _FakeDb(_attempt_for(company))
    monkeypatch.setattr(server, "db", fake)

    keys = [s["key"] for s in company["sections"]]
    last_response = None
    for i, key in enumerate(keys):
        # TCS: skip Part B via finish-part-a once Foundation (the first 3
        # non-optional sections) is done, instead of walking the rest.
        if company["id"] == "tcs-nqt" and i == 3:
            response = asyncio.run(server.finish_oa_part_a("att", user={"user_id": "u1"}))
            assert response["status"] == "completed"
            assert response["tcs_tier"]["tier"] == "ninja"
            assert fake.oa_attempts.doc["status"] == "completed"
            return
        body = server.SubmitSectionIn(section_key=key, answers={})
        last_response = asyncio.run(server.submit_section("att", body, user={"user_id": "u1"}))

    assert last_response["status"] == "completed"
    assert fake.oa_attempts.doc["status"] == "completed"
    assert fake.oa_attempts.doc["current_section_index"] == len(keys)
    assert set(fake.oa_attempts.doc["section_results"].keys()) == set(keys)


@pytest.mark.parametrize("company", COMPANIES, ids=[c["id"] for c in COMPANIES])
def test_every_company_rejects_out_of_order_submit(monkeypatch, company):
    keys = [s["key"] for s in company["sections"]]
    if len(keys) < 2:
        pytest.skip(f"{company['id']} has only one section -- no 'out of order' to test")
    _patch_all_graders(monkeypatch)
    fake = _FakeDb(_attempt_for(company))
    monkeypatch.setattr(server, "db", fake)

    # Try to submit the SECOND section while current_section_index is still 0.
    body = server.SubmitSectionIn(section_key=keys[1], answers={})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.submit_section("att", body, user={"user_id": "u1"}))
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "wrong_section_order"
    assert exc.value.detail["expected_section_key"] == keys[0]
    # Nothing graded, nothing advanced.
    assert fake.oa_attempts.doc["section_results"] == {}
    assert fake.oa_attempts.doc["current_section_index"] == 0


@pytest.mark.parametrize("company", COMPANIES, ids=[c["id"] for c in COMPANIES])
def test_every_company_rejects_a_repeated_submit(monkeypatch, company):
    _patch_all_graders(monkeypatch)
    fake = _FakeDb(_attempt_for(company))
    monkeypatch.setattr(server, "db", fake)

    key0 = company["sections"][0]["key"]
    body = server.SubmitSectionIn(section_key=key0, answers={})
    first = asyncio.run(server.submit_section("att", body, user={"user_id": "u1"}))
    assert key0 in fake.oa_attempts.doc["section_results"]

    # Resubmitting the SAME (now already-submitted) section must be rejected,
    # whether or not the attempt has since moved on to a new current section.
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.submit_section("att", body, user={"user_id": "u1"}))
    if first["status"] == "completed":
        assert exc.value.detail["code"] == "attempt_not_in_progress"
    else:
        assert exc.value.detail["code"] == "section_already_submitted"
    assert exc.value.status_code == 409


# ---- Capgemini, called out explicitly per the request ----------------------

def test_capgemini_flow_completes_in_order_and_computes_tier(monkeypatch):
    capgemini = next(c for c in COMPANIES if c["id"] == "capgemini")
    _patch_all_graders(monkeypatch)
    fake = _FakeDb(_attempt_for(capgemini))
    monkeypatch.setattr(server, "db", fake)

    keys = [s["key"] for s in capgemini["sections"]]
    last_response = None
    for key in keys:
        body = server.SubmitSectionIn(section_key=key, answers={})
        last_response = asyncio.run(server.submit_section("att", body, user={"user_id": "u1"}))

    assert last_response["status"] == "completed"
    assert "capgemini_tier" in last_response
    assert fake.oa_attempts.doc["status"] == "completed"
    assert set(fake.oa_attempts.doc["section_results"].keys()) == set(keys)


def test_capgemini_rejects_skipping_straight_to_round5(monkeypatch):
    capgemini = next(c for c in COMPANIES if c["id"] == "capgemini")
    _patch_all_graders(monkeypatch)
    fake = _FakeDb(_attempt_for(capgemini))
    monkeypatch.setattr(server, "db", fake)

    body = server.SubmitSectionIn(section_key="round5_cognitive", answers={})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.submit_section("att", body, user={"user_id": "u1"}))
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "wrong_section_order"
    assert exc.value.detail["expected_section_key"] == "round1_communication"
