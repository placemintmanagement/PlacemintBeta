"""Tests for POST /oa/{attempt_id}/finish-part-a (server.finish_oa_part_a),
the generic "finish early when every remaining section is optional" endpoint
added for TCS's Part B. Calls the handler directly (same style as
test_capgemini_views.py) with an in-memory fake db -- no Mongo, no network,
no model calls.

Covers: ownership scoping (401 at the shared require_user dependency, 404 for
a missing/not-mine attempt), refusal while a mandatory section remains,
refusal for a company whose remaining sections aren't all optional, that
calling it twice is safe (second call 409s cleanly, doesn't corrupt the
already-stored result), and that nothing the client sends can set or
influence the computed track.
"""
import asyncio
import inspect
import json

import pytest
from fastapi import HTTPException

import server
from services import tcs_tiers


class _FakeOAAttempts:
    """Faithful enough to enforce the SAME ownership scoping the real
    db.oa_attempts.find_one({"attempt_id":..., "user_id":...}) query does --
    unlike test_capgemini_views.py's fake (which ignores the query entirely),
    this one actually filters by it, so wrong-user lookups correctly miss."""

    def __init__(self, docs):
        self.docs = {d["attempt_id"]: d for d in docs}
        self.update_calls = []

    async def find_one(self, query, projection=None):
        doc = self.docs.get(query.get("attempt_id"))
        if doc is None:
            return None
        if "user_id" in query and doc.get("user_id") != query["user_id"]:
            return None
        return json.loads(json.dumps(doc))

    async def update_one(self, query, update):
        aid = query["attempt_id"]
        self.update_calls.append(update["$set"])
        self.docs[aid] = {**self.docs[aid], **update["$set"]}


class _FakeDb:
    def __init__(self, docs):
        self.oa_attempts = _FakeOAAttempts(docs)


def _section_results(foundation=65, advanced=0, coding=0.0):
    return {
        "numerical": {"correct": foundation // 3, "score": 1.0},
        "verbal": {"correct": foundation // 3, "score": 1.0},
        "reasoning": {"correct": foundation - 2 * (foundation // 3), "score": 1.0},
        "advanced": {"correct": advanced, "score": advanced / 15 if advanced else 0.0},
        "coding": {"score": coding},
    }


def _tcs_sections():
    return [
        {"key": "numerical", "type": "mcq"},
        {"key": "verbal", "type": "mcq"},
        {"key": "reasoning", "type": "mcq"},
        {"key": "advanced", "type": "mcq", "optional": True},
        {"key": "coding", "type": "coding", "optional": True},
    ]


def _attempt(
    attempt_id="att_1", user_id="u1", company_id="tcs-nqt", current_section_index=3,
    status="in_progress", section_results=None, sections=None, extra=None,
):
    doc = {
        "attempt_id": attempt_id, "user_id": user_id, "company_id": company_id,
        "status": status, "sections": sections if sections is not None else _tcs_sections(),
        "section_results": section_results if section_results is not None else _section_results(),
        "answers": {}, "current_section_index": current_section_index,
    }
    if extra:
        doc.update(extra)
    return doc


# ---- auth / ownership -------------------------------------------------------

def test_no_authorization_header_is_401_at_the_shared_require_user_dependency():
    # finish_oa_part_a uses the exact same require_user Depends() as every
    # other authenticated oa endpoint -- this proves that shared gate itself
    # rejects an unauthenticated caller before the handler ever runs.
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.require_user(authorization=None))
    assert exc.value.status_code == 401


def test_nonexistent_attempt_id_is_404():
    fake = _FakeDb([_attempt()])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.finish_oa_part_a("does-not-exist", user={"user_id": "u1"}))
    assert exc.value.status_code == 404


def test_another_users_attempt_is_404_not_leaked_as_403():
    # Ownership is enforced by scoping the lookup query itself (attempt_id +
    # user_id together) -- a caller who isn't the owner gets the same 404 as
    # a caller asking about an attempt_id that doesn't exist at all, so no
    # response ever confirms "this attempt_id exists, you're just not allowed
    # to touch it".
    fake = _FakeDb([_attempt(user_id="u1")])
    server.db = fake
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.finish_oa_part_a("att_1", user={"user_id": "someone-else"}))
    assert exc.value.status_code == 404


# ---- mandatory-section gating -----------------------------------------------

def test_refused_while_a_mandatory_tcs_section_is_unfinished():
    # current_section_index=0 -> numerical/verbal/reasoning (none optional)
    # are still in "remaining".
    fake = _FakeDb([_attempt(current_section_index=0)])
    server.db = fake
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.finish_oa_part_a("att_1", user={"user_id": "u1"}))
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "mandatory_section_remains"


def test_refused_for_a_company_whose_remaining_sections_are_not_all_optional():
    # Generic case, not TCS-specific: any company whose section list has no
    # "optional" flags at all must be refused the same way, since
    # all(s.get("optional") for s in remaining) is False whenever any
    # remaining section lacks the flag.
    sections = [
        {"key": "aptitude", "type": "mcq"},
        {"key": "coding", "type": "coding"},
    ]
    fake = _FakeDb([_attempt(company_id="wipro", current_section_index=1, sections=sections)])
    server.db = fake
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.finish_oa_part_a("att_1", user={"user_id": "u1"}))
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "mandatory_section_remains"


def test_no_sections_remain_is_400_not_mandatory_remains():
    fake = _FakeDb([_attempt(current_section_index=5)])  # past the end of 5 sections
    server.db = fake
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.finish_oa_part_a("att_1", user={"user_id": "u1"}))
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "no_sections_remain"


# ---- success path + idempotent-ish re-call ----------------------------------

def test_succeeds_when_only_optional_sections_remain_and_computes_ninja_tier():
    fake = _FakeDb([_attempt(current_section_index=3, section_results=_section_results(foundation=65))])
    server.db = fake
    response = asyncio.run(server.finish_oa_part_a("att_1", user={"user_id": "u1"}))
    assert response["status"] == "completed"
    assert response["tcs_tier"] == {
        "tier": "ninja", "lpa": tcs_tiers.TCS_LPA["ninja"], "lpa_note": tcs_tiers.TCS_LPA_NOTE,
    }
    stored = fake.oa_attempts.docs["att_1"]
    assert stored["status"] == "completed"
    assert stored["tcs_tier"]["part_b_attempted"] is False
    assert "criteria" in stored["tcs_tier"]  # full breakdown kept server-side


def test_calling_it_twice_is_safe_second_call_409s_without_corrupting_first_result():
    fake = _FakeDb([_attempt(current_section_index=3, section_results=_section_results(foundation=65))])
    server.db = fake
    first = asyncio.run(server.finish_oa_part_a("att_1", user={"user_id": "u1"}))
    assert first["status"] == "completed"
    stored_after_first = json.loads(json.dumps(fake.oa_attempts.docs["att_1"]))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.finish_oa_part_a("att_1", user={"user_id": "u1"}))
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "not_in_progress"

    # The second (refused) call must not have touched the stored result.
    assert fake.oa_attempts.docs["att_1"] == stored_after_first
    assert len(fake.oa_attempts.update_calls) == 1  # only the first call wrote anything


# ---- the client cannot set or influence the computed track -----------------

def test_handler_takes_no_body_a_client_cannot_pass_a_track_at_all():
    sig = inspect.signature(server.finish_oa_part_a)
    assert list(sig.parameters) == ["attempt_id", "user"], (
        "finish_oa_part_a must not accept a request body -- if a 'track' or "
        "similar parameter is ever added here, this test will catch it and "
        "the endpoint needs re-auditing for client-controlled tier input."
    )


def test_a_preexisting_stale_tcs_tier_on_the_doc_is_overwritten_not_trusted():
    # Simulates a doc that already carries a (hypothetically client-tampered
    # or stale) tcs_tier of "prime" sitting on it before finish-part-a runs.
    # The endpoint must always recompute from section_results alone and
    # overwrite it -- never read or defer to whatever's already stored.
    stale = {"tier": "prime", "lpa": tcs_tiers.TCS_LPA["prime"], "part_b_attempted": True}
    fake = _FakeDb([_attempt(
        current_section_index=3,
        section_results=_section_results(foundation=65, advanced=0, coding=0.0),  # ninja-only level
        extra={"tcs_tier": stale},
    )])
    server.db = fake
    response = asyncio.run(server.finish_oa_part_a("att_1", user={"user_id": "u1"}))
    assert response["tcs_tier"]["tier"] == "ninja"
    assert fake.oa_attempts.docs["att_1"]["tcs_tier"]["tier"] == "ninja"
