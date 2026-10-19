"""Unit tests for repositories/game_sessions_pg.py -- mocks fetch_all/
fetch_one directly. Mirrors gamified_round.py's create_session (upsert),
check_answer (session find + partial update), and get_seen_puzzle_ids
(per-user session scan)."""
from __future__ import annotations

import asyncio

from repositories import game_sessions_pg as pg


def test_upsert_session_on_conflict_update(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"session_id": "oa1_sec1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(
        pg.upsert_session(
            "oa1_sec1", "u1", {"puzzleIdsByType": {"grid": ["p1"]}},
            attempt_id="oa1", company="tcs", game_type="grid", section_key="sec1",
        )
    )
    assert row == {"session_id": "oa1_sec1"}
    assert "ON CONFLICT (session_id) DO UPDATE" in captured["sql"]
    assert captured["params"][0] == "oa1_sec1"
    assert captured["params"][-1].obj == {"puzzleIdsByType": {"grid": ["p1"]}}


def test_get_session(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"session_id": "s1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.get_session("s1"))
    assert row == {"session_id": "s1"}
    assert captured["params"] == ("s1",)


def test_update_session_fields_merges_data_and_scores(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"session_id": "s1", "running_score": 3}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(
        pg.update_session_fields("s1", data={"live_checks": {"p1": {"correct": True}}}, running_score=3)
    )
    assert row["running_score"] == 3
    assert "data = %s" in captured["sql"]
    assert "running_score = %s" in captured["sql"]
    params = captured["params"]
    assert params[0].obj == {"live_checks": {"p1": {"correct": True}}}
    assert params[1] == 3
    assert params[-1] == "s1"


def test_update_session_fields_noop_returns_current(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return {"session_id": "s1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.update_session_fields("s1"))
    assert row == {"session_id": "s1"}


def test_list_sessions_for_user(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"session_id": "s1"}, {"session_id": "s2"}]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(pg.list_sessions_for_user("u1"))
    assert len(rows) == 2
    assert captured["params"] == ("u1",)
