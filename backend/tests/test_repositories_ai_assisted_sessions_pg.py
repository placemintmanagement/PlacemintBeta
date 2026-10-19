"""Unit tests for repositories/ai_assisted_sessions_pg.py -- mocks
fetch_all/fetch_one directly. Covers the flat-dict split into promoted
columns + jsonb `data` (insert_session/update_session), matching
dev_ai_assisted_start's session literal and the scoring lookup."""
from __future__ import annotations

import asyncio

from repositories import ai_assisted_sessions_pg as pg


SESSION_DOC = {
    "session_id": "aas1",
    "user_id": "u1",
    "problem_id": "p1",
    "problem": {"title": "Fix the bug"},
    "current_stage": "understand",
    "transcript": [{"role": "ai", "text": "hi"}],
    "stage_attempts": {"understand": 0},
    "consent_given": None,
    "self_review_result": None,
    "status": "in_progress",
    "created_at": "2026-01-01T00:00:00+00:00",
    "completed_at": None,
}


def test_insert_session_splits_promoted_columns_from_data(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"session_id": "aas1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.insert_session(SESSION_DOC))
    assert row == {"session_id": "aas1"}
    assert "session_id" in captured["sql"]
    assert "problem_id" in captured["sql"]
    # the jsonb data param is last and holds the non-promoted fields
    data_param = captured["params"][-1]
    assert data_param.obj["problem"] == {"title": "Fix the bug"}
    assert data_param.obj["stage_attempts"] == {"understand": 0}
    assert "session_id" not in data_param.obj


def test_get_session_scoped_and_unscoped(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"session_id": "aas1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.get_session("aas1", "u1"))
    assert "user_id = %s" in captured["sql"]
    asyncio.run(pg.get_session("aas1"))
    assert captured["params"] == ("aas1",)


def test_get_session_by_attempt_section(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"session_id": "aas1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.get_session_by_attempt_section("oa1", "sec1", "u1"))
    assert "attempt_id = %s AND section_key = %s AND user_id = %s" in captured["sql"]
    assert captured["params"] == ("oa1", "sec1", "u1")


def test_update_session_merges_data_and_sets_promoted_columns(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"session_id": "aas1", "status": "completed"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(
        pg.update_session("aas1", {"status": "completed", "completed_at": "now", "final_outcome": {"score": 1.0}})
    )
    assert row["status"] == "completed"
    assert "status = %s" in captured["sql"]
    assert "completed_at = %s" in captured["sql"]
    assert "data = data || %s::jsonb" in captured["sql"]
    data_param = [p for p in captured["params"] if hasattr(p, "obj")][0]
    assert data_param.obj == {"final_outcome": {"score": 1.0}}


def test_update_session_noop(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return {"session_id": "aas1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.update_session("aas1", {}))
    assert row == {"session_id": "aas1"}
