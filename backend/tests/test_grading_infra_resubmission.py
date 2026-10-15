"""Confirms the actual guarantee the canary rework exists for: a student
is never left unable to submit a coding section because of an
infrastructure problem. A 503 from _grade_coding_section must leave the
attempt's state -- status, current_section_index (which the section-
order check and any timer logic both read), section_results, answers --
completely untouched, so the exact same submission can be sent again
afterward and this time succeed normally, with no partial score or track
evaluation ever having been written from the failed attempt.

Uses a fake Mongo-shaped db (same minimal pattern as
test_oa_section_order_enforcement.py) and monkeypatches
_grade_coding_section itself (not code_runner) -- this file is about
submit_section's own behavior around a 503, not about re-proving the
canary mechanics again (covered separately in
test_grading_infra_classification.py).

No model is used anywhere in this file.
"""
import asyncio
import json

import pytest

import server


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


def _attempt_with_one_coding_section():
    return {
        "attempt_id": "att", "user_id": "u1", "company_id": "tcs-nqt",
        "status": "in_progress",
        "sections": [{"key": "coding", "type": "coding", "questions": []}],
        "section_results": {}, "answers": {}, "current_section_index": 0,
        # Stands in for whatever timer/deadline field a real attempt
        # carries -- asserting the WHOLE doc is byte-identical after a
        # 503 covers this (and any other field) without needing to know
        # its exact name.
        "section_deadline_ts": 1234567890.0,
    }


def test_503_leaves_attempt_untouched_and_allows_resubmission(monkeypatch):
    calls = {"n": 0}

    async def flaky_then_ok_grade(section, answers, use_ai_note=True):
        calls["n"] += 1
        if calls["n"] == 1:
            raise server.HTTPException(503, {
                "code": "grading_infra_error",
                "message": "We hit an infrastructure problem while grading your code. "
                            "Nothing was scored for this section -- please resubmit.",
            })
        return {"score": 1.0, "problems": [], "passed": True}

    monkeypatch.setattr(server, "_grade_coding_section", flaky_then_ok_grade)
    fake = _FakeDb(_attempt_with_one_coding_section())
    monkeypatch.setattr(server, "db", fake)

    body = server.SubmitSectionIn(section_key="coding", answers={})
    snapshot_before = json.loads(json.dumps(fake.oa_attempts.doc))

    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(server.submit_section("att", body, user={"user_id": "u1"}))
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "grading_infra_error"

    # Nothing was written at all: the attempt doc is byte-for-byte
    # unchanged -- same status, same current_section_index (what the
    # section-order check and any timer logic both read), same
    # section_results (no partial/empty score stored), same answers,
    # same deadline/timer field.
    assert fake.oa_attempts.doc == snapshot_before

    # The exact same submission can be sent again -- the student isn't
    # locked out by the earlier 503 -- and this time it succeeds.
    second = asyncio.run(server.submit_section("att", body, user={"user_id": "u1"}))
    assert calls["n"] == 2
    assert fake.oa_attempts.doc["section_results"]["coding"]["passed"] is True
    assert fake.oa_attempts.doc["current_section_index"] == 1
    assert second["status"] == "completed"


def test_503_does_not_advance_even_if_it_was_the_attempts_last_section(monkeypatch):
    # Specifically guards against a 503 somehow still marking the attempt
    # "completed" (which would also trigger track computation) -- the
    # attempt has exactly one section, so completing it would otherwise
    # flip status to "completed" and compute a tier.
    async def always_infra_error(section, answers, use_ai_note=True):
        raise server.HTTPException(503, {"code": "grading_infra_error", "message": "x"})

    monkeypatch.setattr(server, "_grade_coding_section", always_infra_error)
    fake = _FakeDb(_attempt_with_one_coding_section())
    monkeypatch.setattr(server, "db", fake)

    body = server.SubmitSectionIn(section_key="coding", answers={})
    with pytest.raises(server.HTTPException):
        asyncio.run(server.submit_section("att", body, user={"user_id": "u1"}))

    assert fake.oa_attempts.doc["status"] == "in_progress"
    assert fake.oa_attempts.doc["current_section_index"] == 0
    assert fake.oa_attempts.doc["section_results"] == {}
    assert "tcs_tier" not in fake.oa_attempts.doc
    assert "capgemini_tier" not in fake.oa_attempts.doc
