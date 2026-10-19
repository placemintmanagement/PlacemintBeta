"""Unit tests for repositories/resumes_pg.py -- mocks fetch_all/fetch_one
directly. Covers get_latest_resume_for_company's "most recent by
created_at" selection, matching _latest_resume_for_company (server.py)."""
from __future__ import annotations

import asyncio

from repositories import resumes_pg as pg


def test_insert_resume_wraps_analysis_as_jsonb(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"resume_id": "r1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.insert_resume("r1", "u1", "tcs", "SDE", "text sample", {"skills": ["py"]}))
    assert row == {"resume_id": "r1"}
    assert "INSERT INTO resumes" in captured["sql"]
    assert captured["params"][0] == "r1"
    # analysis (last-but-one positional param) is wrapped for jsonb adaptation
    assert captured["params"][-1].obj == {"skills": ["py"]}


def test_insert_resume_allows_none_analysis(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["params"] = params
        return {"resume_id": "r1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.insert_resume("r1", "u1", None, None, None, None))
    assert captured["params"][-1] is None


def test_get_resume_is_ownership_scoped(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"resume_id": "r1", "user_id": "u1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.get_resume("r1", "u1"))
    assert row["resume_id"] == "r1"
    assert "resume_id = %s AND user_id = %s" in captured["sql"]
    assert captured["params"] == ("r1", "u1")


def test_get_resumes_for_user_orders_newest_first_with_limit(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"resume_id": "r2"}, {"resume_id": "r1"}]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(pg.get_resumes_for_user("u1", limit=20))
    assert len(rows) == 2
    assert "ORDER BY created_at DESC LIMIT %s" in captured["sql"]
    assert captured["params"] == ("u1", 20)


def test_get_latest_resume_for_company_orders_desc_limit_one(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"resume_id": "r_newest", "created_at": "2026-02-01T00:00:00+00:00"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.get_latest_resume_for_company("u1", "tcs"))
    assert row["resume_id"] == "r_newest"
    assert "ORDER BY created_at DESC LIMIT 1" in captured["sql"]
    assert "WHERE user_id = %s AND company_id = %s" in captured["sql"]
    assert captured["params"] == ("u1", "tcs")


def test_get_resume_by_id_unscoped(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"resume_id": "r1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.get_resume_by_id("r1"))
    # _COLUMNS still SELECTs user_id (it's a real column); only the WHERE
    # clause should have no ownership filter for this unscoped lookup.
    assert "AND user_id" not in captured["sql"]
    assert captured["params"] == ("r1",)
