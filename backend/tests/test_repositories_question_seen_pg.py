"""Unit tests for repositories/question_seen_pg.py -- mocks fetch_one
directly. Covers the single table replacing the five Mongo *_bank_seen
collections, keyed on (user_id, bank, scope)."""
from __future__ import annotations

import asyncio

from repositories import question_seen_pg as pg


def test_get_seen_ids_returns_set_from_row(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"question_ids": ["q1", "q2"]}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    seen = asyncio.run(pg.get_seen_ids("u1", "mcq_static", "aptitude"))
    assert seen == {"q1", "q2"}
    assert captured["params"] == ("u1", "mcq_static", "aptitude")


def test_get_seen_ids_empty_set_when_no_row(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    assert asyncio.run(pg.get_seen_ids("u1", "debugging")) == set()


def test_get_seen_ids_default_scope_is_empty_string(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["params"] = params
        return None

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.get_seen_ids("u1", "ai_assisted"))
    assert captured["params"] == ("u1", "ai_assisted", "")


def test_mark_seen_noop_on_empty_list(monkeypatch):
    called = {"n": 0}

    async def fake_fetch_one(sql, params=()):
        called["n"] += 1
        return None

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.mark_seen("u1", "mcq_static", "aptitude", []))
    assert called["n"] == 0


def test_mark_seen_atomic_union_and_seen_at_merge(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"user_id": "u1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.mark_seen("u1", "mcq_static", "aptitude", ["q1", "q2"]))
    assert "ON CONFLICT (user_id, bank, scope) DO UPDATE" in captured["sql"]
    assert "array(SELECT DISTINCT unnest(" in captured["sql"]
    assert "seen_at = question_seen.seen_at || EXCLUDED.seen_at" in captured["sql"]
    params = captured["params"]
    assert params[0] == "u1"
    assert params[1] == "mcq_static"
    assert params[2] == "aptitude"
    assert params[3] == ["q1", "q2"]
    assert set(params[4].obj.keys()) == {"q1", "q2"}
