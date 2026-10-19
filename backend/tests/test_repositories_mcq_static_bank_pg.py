"""Unit tests for repositories/mcq_static_bank_pg.py -- mocks fetch_all/
fetch_one directly (no real Postgres connection) so these exercise this
module's own SQL-shape and guard logic, mirroring the Mongo-based
behavior in backend/banks/mcq_static_bank.py (sample_static,
_draw_bucket, topic_bank_size)."""
from __future__ import annotations

import asyncio

from repositories import mcq_static_bank_pg as pg


def test_count_by_topic_returns_int(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        assert "count(*)" in sql
        assert params == ("aptitude",)
        return {"n": 42}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    assert asyncio.run(pg.count_by_topic("aptitude")) == 42


def test_count_by_topic_zero_when_no_row(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    assert asyncio.run(pg.count_by_topic("aptitude")) == 0


def test_list_by_topic_basic_query(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"question_id": "q1"}]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(pg.list_by_topic("dsa"))
    assert rows == [{"question_id": "q1"}]
    assert "WHERE topic = %s" in captured["sql"]
    assert "NOT (question_id = ANY" not in captured["sql"]
    assert captured["params"] == ["dsa"]


def test_list_by_topic_with_difficulty_and_exclusions(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    asyncio.run(pg.list_by_topic("dsa", difficulty="Hard", exclude_ids=["q1", "q2"]))
    assert "difficulty = %s" in captured["sql"]
    assert "NOT (question_id = ANY(%s))" in captured["sql"]
    assert captured["params"] == ["dsa", "Hard", ["q1", "q2"]]


def test_list_by_topic_no_exclusion_clause_when_empty_list(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        return []

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    asyncio.run(pg.list_by_topic("dsa", exclude_ids=[]))
    assert "ANY" not in captured["sql"]


def test_sample_random_by_topic_uses_order_by_random(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"question_id": "q1"}, {"question_id": "q2"}]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(pg.sample_random_by_topic("dsa", 5, exclude_ids=["seen1"]))
    assert "ORDER BY random()" in captured["sql"]
    assert "LIMIT %s" in captured["sql"]
    assert captured["params"][-1] == 5
    assert "NOT (question_id = ANY(%s))" in captured["sql"]
    assert rows == [{"question_id": "q1"}, {"question_id": "q2"}]


def test_sample_random_by_topic_zero_count_short_circuits(monkeypatch):
    called = {"n": 0}

    async def fake_fetch_all(sql, params=()):
        called["n"] += 1
        return []

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    assert asyncio.run(pg.sample_random_by_topic("dsa", 0)) == []
    assert asyncio.run(pg.sample_random_by_topic("dsa", -3)) == []
    assert called["n"] == 0


def test_get_by_ids_empty_short_circuits(monkeypatch):
    called = {"n": 0}

    async def fake_fetch_all(sql, params=()):
        called["n"] += 1
        return []

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    assert asyncio.run(pg.get_by_ids([])) == []
    assert called["n"] == 0


def test_get_by_ids_passes_list(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"question_id": "q1"}, {"question_id": "q2"}]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(pg.get_by_ids(["q1", "q2"]))
    assert "question_id = ANY(%s)" in captured["sql"]
    assert captured["params"] == (["q1", "q2"],)
    assert len(rows) == 2
