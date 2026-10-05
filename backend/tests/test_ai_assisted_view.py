"""GET /oa/{id}/ai-assisted/{section_key} must not expose Round 4 components.
Uses an in-memory fake db (no Mongo, no network)."""
import asyncio
import json

import server


class _Col:
    def __init__(self, doc):
        self.doc = doc

    async def find_one(self, query, projection=None):
        return json.loads(json.dumps(self.doc)) if self.doc else None


class _FakeDb:
    def __init__(self, attempt, session):
        self.oa_attempts = _Col(attempt)
        self.ai_assisted_sessions = _Col(session)


def _attempt():
    return {"attempt_id": "att_1", "user_id": "u1", "sections": [{"key": "round4_ai_assisted", "type": "ai_assisted"}]}


def _session():
    return {
        "session_id": "aas_1", "status": "completed", "current_stage": "complete",
        "final_outcome": {
            "score": 0.62, "passed": True, "reason": "candidate correctly caught the flawed code",
            "components": {"self_review_correct": 1.0, "bug_explanation_quality": 0.7, "stage_efficiency": 0.4},
        },
    }


def test_get_ai_assisted_session_drops_components(monkeypatch):
    monkeypatch.setattr(server, "db", _FakeDb(_attempt(), _session()))
    view = asyncio.run(server.oa_ai_assisted_get("att_1", "round4_ai_assisted", user={"user_id": "u1"}))
    assert view["final_outcome"] == {"score": 0.62, "passed": True, "reason": "candidate correctly caught the flawed code"}
    assert "components" not in json.dumps(view)
    assert view["status"] == "completed"


def test_stored_session_keeps_components(monkeypatch):
    stored = _session()
    server_db = _FakeDb(_attempt(), stored)
    monkeypatch.setattr(server, "db", server_db)
    asyncio.run(server.oa_ai_assisted_get("att_1", "round4_ai_assisted", user={"user_id": "u1"}))
    raw = asyncio.run(server._load_ai_assisted_session_for_attempt("att_1", "round4_ai_assisted", "u1"))
    assert raw["final_outcome"]["components"]["stage_efficiency"] == 0.4
