"""Unit tests for repositories/interviews_pg.py -- mocks fetch_all/
fetch_one directly. Covers the plain-interview and Capgemini-style
(Spark/Dave/Commit/TCS) flat-dict split, the in-progress lookup, and the
optimistic-concurrency (turn_count-guarded) update used by the Capgemini
interview modes. These are mocked unit tests only -- the live check that
`supabase/003_interviews_missing_columns.sql` (company_id + data columns)
has actually been applied, and that this module's Capgemini/TCS-shaped
`data` round-trips correctly against the real table, lives in
tests/test_live_supabase_integration.py instead (skipped unless
SUPABASE_DB_URL is set)."""
from __future__ import annotations

import asyncio

from repositories import interviews_pg as pg

PLAIN_INTERVIEW = {
    "interview_id": "intv1",
    "user_id": "u1",
    "attempt_id": "oa1",
    "company_id": "tcs-nqt",
    "company_name": "TCS",
    "resume_id": "r1",
    "questions": [{"id": "q1", "prompt": "Tell me about yourself"}],
    "answers": [],
    "current_index": 0,
    "status": "in_progress",
    "created_at": "2026-01-01T00:00:00+00:00",
}

SPARK_INTERVIEW = {
    "interview_id": "intv2",
    "user_id": "u1",
    "attempt_id": None,
    "company_id": "capgemini",
    "company_name": "Capgemini",
    "tier": "spark",
    "mode": "spark",
    "state": {"status": "in_progress"},
    "turn_count": 0,
    "current_question": {"id": "spark-intro"},
    "status": "in_progress",
    "created_at": "2026-01-01T00:00:00+00:00",
}


def test_insert_interview_splits_plain_shape(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"interview_id": "intv1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.insert_interview(PLAIN_INTERVIEW))
    assert row == {"interview_id": "intv1"}
    assert "questions" in captured["sql"]
    data_param = captured["params"][-1]
    assert data_param.obj == {}  # every field in PLAIN_INTERVIEW is a promoted column


def test_insert_interview_splits_capgemini_shape_into_data(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"interview_id": "intv2"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.insert_interview(SPARK_INTERVIEW))
    data_param = captured["params"][-1]
    assert data_param.obj["mode"] == "spark"
    assert data_param.obj["turn_count"] == 0
    assert data_param.obj["state"] == {"status": "in_progress"}
    assert "interview_id" not in data_param.obj


def test_get_existing_in_progress(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return None

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.get_existing_in_progress("u1", "tcs-nqt"))
    assert "status = 'in_progress'" in captured["sql"]
    assert captured["params"] == ("u1", "tcs-nqt")


def test_get_interview_by_attempt(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"interview_id": "intv1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.get_interview_by_attempt("oa1", "u1"))
    assert "attempt_id = %s AND user_id = %s" in captured["sql"]


def test_list_interviews_for_user_orders_desc(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"interview_id": "intv2"}, {"interview_id": "intv1"}]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(pg.list_interviews_for_user("u1"))
    assert len(rows) == 2
    assert "ORDER BY created_at DESC LIMIT %s" in captured["sql"]
    assert captured["params"] == ("u1", 200)


def test_update_interview_unconditional(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"interview_id": "intv1", "status": "completed"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.update_interview("intv1", {"status": "completed"}))
    assert row["status"] == "completed"
    assert "turn_count" not in captured["sql"]


def test_update_interview_if_turn_matches_checks_data_turn_count(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"interview_id": "intv2", "status": "completed"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(
        pg.update_interview_if_turn_matches("intv2", 3, {"status": "completed", "turn_count": 4})
    )
    assert row["status"] == "completed"
    assert "(data->>'turn_count') = %s" in captured["sql"]
    assert captured["params"][-1] == "3"  # expected_turn_count, stringified for the ->> comparison


def test_update_interview_if_turn_matches_returns_none_on_stale_turn(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None  # WHERE matched nothing -- turn_count had already moved

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.update_interview_if_turn_matches("intv2", 3, {"status": "completed"}))
    assert row is None
