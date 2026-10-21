"""Unit tests for repositories/mcq_pool_pg.py -- mocks fetch_all/fetch_one
directly. Mirrors backend/banks/mcq_pool.py's pop_from_pool (atomic
find_one_and_delete loop) and pool_stats's admin readout.

The genuine concurrent-pop-can-never-double-serve guarantee is a property
of the real SQL statement (DELETE ... WHERE pool_id = (SELECT ... LIMIT 1)
RETURNING *) running against a real Postgres row-locking engine -- it
cannot be verified with a mocked fetch_one, only against live Supabase.
That real-concurrency proof now lives in
tests/test_live_supabase_integration.py's
test_mcq_pool_pop_one_atomic_under_real_concurrency (skipped unless
SUPABASE_DB_URL is set), run against a scratch row inserted and deleted by
the test itself -- never against the real 326 seeded mcq_pool rows."""
from __future__ import annotations

import asyncio

from repositories import mcq_pool_pg as pg


def test_pop_one_issues_single_delete_returning_statement(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"pool_id": "p1", "prompt": "2+2?", "verified": True}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.pop_one("TCS", "aptitude"))
    assert row == {"pool_id": "p1", "prompt": "2+2?", "verified": True}
    sql = captured["sql"]
    assert "DELETE FROM mcq_pool" in sql
    assert "SELECT pool_id FROM mcq_pool" in sql
    assert "LIMIT 1" in sql
    assert "RETURNING" in sql
    assert captured["params"] == ("TCS", "aptitude")


def test_pop_one_returns_none_when_pool_empty(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    assert asyncio.run(pg.pop_one("TCS", "aptitude")) is None


def test_pop_up_to_loops_and_stops_when_exhausted(monkeypatch):
    pool = [{"pool_id": "p1"}, {"pool_id": "p2"}]
    calls = {"n": 0}

    async def fake_pop_one(company_name, section_key):
        calls["n"] += 1
        return pool.pop(0) if pool else None

    monkeypatch.setattr(pg, "pop_one", fake_pop_one)
    rows = asyncio.run(pg.pop_up_to("TCS", "aptitude", 5))
    assert rows == [{"pool_id": "p1"}, {"pool_id": "p2"}]
    # Stopped as soon as pop_one returned None (3rd call), not looping the
    # full 5 requested -- same "fewer than count is fine, callers backfill"
    # convention as the Mongo version's own for-loop-with-break.
    assert calls["n"] == 3


def test_pop_up_to_zero_count_short_circuits(monkeypatch):
    calls = {"n": 0}

    async def fake_pop_one(company_name, section_key):
        calls["n"] += 1
        return {"pool_id": "shouldnt be called"}

    monkeypatch.setattr(pg, "pop_one", fake_pop_one)
    assert asyncio.run(pg.pop_up_to("TCS", "aptitude", 0)) == []
    assert calls["n"] == 0


def test_count_by_company_and_section_groups_and_sorts(monkeypatch):
    """Gap fix (SUPABASE_CUTOVER_PLAN.md punch-list #1): mcq_pool_pg used to
    have no equivalent of pool_stats()'s `pool_counts` aggregation -- this is
    the new GROUP BY replacement for Mongo's $group/$project/$sort pipeline."""
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        return [
            {"company_name": "TCS", "section_key": "aptitude", "count": 3},
            {"company_name": "TCS", "section_key": "reasoning", "count": 1},
        ]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(pg.count_by_company_and_section())
    assert "GROUP BY company_name, section_key" in captured["sql"]
    assert "ORDER BY company_name, section_key" in captured["sql"]
    assert "FROM mcq_pool" in captured["sql"]
    assert rows == [
        {"company_name": "TCS", "section_key": "aptitude", "count": 3},
        {"company_name": "TCS", "section_key": "reasoning", "count": 1},
    ]


def test_get_all_stats_sorted_readout(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        return [{"company_name": "TCS", "section_key": "aptitude", "total_generated": 10}]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(pg.get_all_stats())
    assert "mcq_pool_stats" in captured["sql"]
    assert "ORDER BY company_name, section_key" in captured["sql"]
    assert rows == [{"company_name": "TCS", "section_key": "aptitude", "total_generated": 10}]
