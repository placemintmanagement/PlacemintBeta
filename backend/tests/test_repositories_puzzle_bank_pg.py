"""Unit tests for repositories/puzzle_bank_pg.py -- mocks fetch_all/fetch_one
directly. Mirrors backend/games/gamified_round.py's puzzle_bank/
gamified_round_config reads, with particular attention to the jsonb `data`
merge-back producing the OLD Mongo document shape (camelCase gameType/
companyTags/drawCount/gameTypes/perType/_drawNote) that server.py's and
gamified_round.py's real callers already read -- see that module's own
docstring for exactly which call sites were checked.
"""
from __future__ import annotations

import asyncio

from repositories import puzzle_bank_pg as pg


def _row(puzzle_id="pz1", game_type="deductive_grid", company_tags=None, **data):
    return {
        "puzzle_id": puzzle_id,
        "game_type": game_type,
        "company_tags": company_tags or ["Capgemini"],
        "content_hash": "abc123",
        "explanation": "because logic",
        "data": data,
    }


def test_get_by_id_merges_data_and_renames_columns(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        assert "puzzle_id = %s" in sql
        assert params == ("pz1",)
        return _row(grid=[[1, 2]], correctAnswer=2)

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    doc = asyncio.run(pg.get_by_id("pz1"))
    # Old Mongo shape: gameType/companyTags (renamed columns, restored to
    # camelCase), plus every jsonb data field flattened to the top level.
    assert doc["gameType"] == "deductive_grid"
    assert doc["companyTags"] == ["Capgemini"]
    assert doc["puzzle_id"] == "pz1"
    assert doc["content_hash"] == "abc123"
    assert doc["explanation"] == "because logic"
    assert doc["grid"] == [[1, 2]]
    assert doc["correctAnswer"] == 2
    # No leftover "data" key -- it was merged, not nested.
    assert "data" not in doc


def test_get_by_id_returns_none_when_missing(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    assert asyncio.run(pg.get_by_id("nope")) is None


def test_get_by_ids_empty_short_circuits(monkeypatch):
    called = {"n": 0}

    async def fake_fetch_all(sql, params=()):
        called["n"] += 1
        return []

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    assert asyncio.run(pg.get_by_ids([])) == []
    assert called["n"] == 0


def test_get_by_ids_merges_every_row(monkeypatch):
    async def fake_fetch_all(sql, params=()):
        assert "puzzle_id = ANY(%s)" in sql
        assert params == (["pz1", "pz2"],)
        return [_row("pz1", grid="g1"), _row("pz2", grid="g2")]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    docs = asyncio.run(pg.get_by_ids(["pz1", "pz2"]))
    assert [d["puzzle_id"] for d in docs] == ["pz1", "pz2"]
    assert [d["grid"] for d in docs] == ["g1", "g2"]


def test_sample_puzzles_orders_by_random_and_excludes(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [_row("pz3", game_type="deductive_grid", company_tags=["Capgemini"])]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    docs = asyncio.run(
        pg.sample_puzzles("Capgemini", "deductive_grid", exclude_ids=["pz1", "pz2"], count=4)
    )
    sql = captured["sql"]
    assert "game_type = %s" in sql
    assert "%s = ANY(company_tags)" in sql
    assert "NOT (puzzle_id = ANY(%s))" in sql
    assert "ORDER BY random()" in sql
    assert "LIMIT %s" in sql
    assert captured["params"] == ["deductive_grid", "Capgemini", ["pz1", "pz2"], 4]
    assert docs[0]["gameType"] == "deductive_grid"


def test_sample_puzzles_no_exclusion_clause_when_none_given(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        return []

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    asyncio.run(pg.sample_puzzles("Capgemini", "deductive_grid", exclude_ids=None, count=4))
    assert "puzzle_id = ANY" not in captured["sql"]


def test_sample_puzzles_zero_count_short_circuits(monkeypatch):
    called = {"n": 0}

    async def fake_fetch_all(sql, params=()):
        called["n"] += 1
        return []

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    assert asyncio.run(pg.sample_puzzles("Capgemini", "deductive_grid", None, 0)) == []
    assert called["n"] == 0


def test_get_config_renames_to_old_mongo_camelcase(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        assert params == ("Capgemini",)
        return {
            "company": "Capgemini",
            "draw_count": 4,
            "game_types": ["deductive_grid", "switch_challenge"],
            "per_type": {"deductive_grid": {"timerPerPuzzle": 15}},
            "draw_note": "provisional timers",
        }

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    config = asyncio.run(pg.get_config("Capgemini"))
    assert config == {
        "company": "Capgemini",
        "drawCount": 4,
        "gameTypes": ["deductive_grid", "switch_challenge"],
        "perType": {"deductive_grid": {"timerPerPuzzle": 15}},
        "_drawNote": "provisional timers",
    }


def test_get_config_returns_none_when_missing(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    assert asyncio.run(pg.get_config("Nope Inc")) is None
