"""Client-facing views of a Capgemini tier result. Uses an in-memory fake db
(no Mongo, no network): checks what get_oa and submit_section actually return."""
import asyncio
import json

import server
from services import capgemini_tiers as ct


class _FakeOAAttempts:
    def __init__(self, doc):
        self.doc = doc
        self.written = None

    async def find_one(self, query, projection=None):
        return json.loads(json.dumps(self.doc))

    async def update_one(self, query, update):
        self.written = update["$set"]


class _FakeDb:
    def __init__(self, doc):
        self.oa_attempts = _FakeOAAttempts(doc)


def _section_results():
    return {
        "ai_literacy": {"score": 0.0, "correct": 16, "total": 20, "passed": True},
        "technical_assessment": {"score": 0.0, "correct": 15, "total": 20, "passed": True},
        "round3_debugging": {"score": 0.7, "passed": True},
        "round4_ai_assisted": {
            "score": 0.6, "passed": True,
            "components": {"self_review_correct": 1.0, "bug_explanation_quality": 0.9, "stage_efficiency": 0.2},
        },
    }


def _attempt_with_tier(tier_doc):
    return {
        "attempt_id": "att_1", "user_id": "u1", "company_id": "capgemini", "company_name": "Capgemini",
        "status": "completed", "sections": [{"key": "round5_cognitive", "type": "mcq", "questions": []}],
        "section_results": _section_results(), "answers": {}, "current_section_index": 1,
        "capgemini_tier": tier_doc,
    }


def _stored_tier():
    tier = ct.evaluate({**_section_results(), "round5_cognitive": {"score": 0.7, "passed": True}})
    tier["computed_at"] = "2026-10-05T00:00:00+00:00"
    return tier


def test_get_oa_returns_only_tier_and_lpa(monkeypatch):
    stored = _stored_tier()
    assert stored["tier"] == "dave" and "criteria" in stored  # breakdown exists on the stored doc
    monkeypatch.setattr(server, "db", _FakeDb(_attempt_with_tier(stored)))
    doc = asyncio.run(server.get_oa("att_1", user={"user_id": "u1"}))
    assert doc["capgemini_tier"] == {"tier": "dave", "lpa": 5.75}
    # Section results are the candidate's own scores and are shown as before; only the
    # tier's breakdown keys must be absent.
    serialized = json.dumps(doc["capgemini_tier"])
    for banned in ("criteria", "technical_module_score", "computed_at"):
        assert banned not in serialized, banned


def test_submit_section_response_has_no_breakdown(monkeypatch):
    fake = _FakeDb(_attempt_with_tier(None))
    monkeypatch.setattr(server, "db", fake)
    monkeypatch.setattr(server, "_grade_mcq_like", lambda section, answers: {"score": 0.7, "passed": True})
    body = server.SubmitSectionIn(section_key="round5_cognitive", answers={})
    response = asyncio.run(server.submit_section("att_1", body, user={"user_id": "u1"}))
    assert response["capgemini_tier"] == {"tier": "dave", "lpa": 5.75}
    serialized = json.dumps(response)
    for banned in ("criteria", "technical_module_score", "computed_at"):
        assert banned not in serialized, banned
    # The breakdown is still stored on the attempt for admin use.
    assert "criteria" in fake.oa_attempts.written["capgemini_tier"]


def test_submit_section_cognitive_055_gives_no_tier(monkeypatch):
    fake = _FakeDb(_attempt_with_tier(None))
    monkeypatch.setattr(server, "db", fake)
    monkeypatch.setattr(server, "_grade_mcq_like", lambda section, answers: {"score": 0.55, "passed": False})
    body = server.SubmitSectionIn(section_key="round5_cognitive", answers={})
    response = asyncio.run(server.submit_section("att_1", body, user={"user_id": "u1"}))
    assert response["capgemini_tier"] == {"tier": None, "lpa": None}


def test_client_section_results_drop_round4_components():
    raw = {"round4_ai_assisted": {"score": 0.6, "passed": True, "components": {"stage_efficiency": 0.2}}}
    client = server._client_section_results(raw)
    assert client == {"round4_ai_assisted": {"score": 0.6, "passed": True}}
    assert "components" in raw["round4_ai_assisted"]  # stored data is not mutated
