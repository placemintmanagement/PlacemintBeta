"""Unit tests for repositories/review_deck_pg.py -- mocks fetch_all/
fetch_one directly. Covers the atomic ON CONFLICT DO NOTHING dup-check
(using the existing unique constraint) and the card_id-lives-in-`data`
lookup pattern (see module docstring for why)."""
from __future__ import annotations

import asyncio

from repositories import review_deck_pg as pg


def test_add_card_inserts_with_on_conflict_do_nothing(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {
            "id": 1, "user_id": "u1", "source_attempt_id": "oa1", "section_key": "sec1",
            "question_id": "q1", "added_at": "2026-01-01T00:00:00+00:00",
            "data": {"card_id": "card1", "mastered": False, "attempts": []},
        }

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    card = asyncio.run(
        pg.add_card("u1", "oa1", "sec1", "q1", "card1", "TCS", "Aptitude", "2+2?", ["3", "4"], 1, "basic math", "Easy")
    )
    assert card["card_id"] == "card1"
    assert card["id"] == 1  # the real bigint identity PK, distinct from card_id (see module docstring)
    assert card["mastered"] is False
    assert "ON CONFLICT (user_id, source_attempt_id, section_key, question_id) DO NOTHING" in captured["sql"]


def test_add_card_returns_none_on_duplicate(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None  # ON CONFLICT DO NOTHING matched zero rows

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    card = asyncio.run(
        pg.add_card("u1", "oa1", "sec1", "q1", "card1", "TCS", "Aptitude", "2+2?", ["3", "4"], 1, "basic math", "Easy")
    )
    assert card is None


def test_list_cards_filters_unmastered(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{
            "id": 1, "user_id": "u1", "source_attempt_id": "oa1", "section_key": "sec1",
            "question_id": "q1", "added_at": "t", "data": {"card_id": "card1", "mastered": False},
        }]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    cards = asyncio.run(pg.list_cards("u1", unmastered_only=True))
    assert len(cards) == 1
    assert "mastered')::boolean IS NOT TRUE" in captured["sql"]
    assert "ORDER BY added_at DESC" in captured["sql"]


def test_get_card_looks_up_by_data_card_id(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {
            "id": 1, "user_id": "u1", "source_attempt_id": "oa1", "section_key": "sec1",
            "question_id": "q1", "added_at": "t", "data": {"card_id": "card1"},
        }

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    card = asyncio.run(pg.get_card("card1", "u1"))
    assert card["card_id"] == "card1"
    assert "data->>'card_id' = %s" in captured["sql"]
    assert captured["params"] == ("u1", "card1")


def test_record_attempt_merges_into_data(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {
            "id": 1, "user_id": "u1", "source_attempt_id": "oa1", "section_key": "sec1",
            "question_id": "q1", "added_at": "t",
            "data": {"card_id": "card1", "mastered": True, "attempts": [{"correct": True}, {"correct": True}]},
        }

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    card = asyncio.run(pg.record_attempt("card1", "u1", [{"correct": True}, {"correct": True}], True))
    assert card["mastered"] is True
    assert "data = data || %s::jsonb" in captured["sql"]
    patch = captured["params"][0]
    assert patch.obj == {"attempts": [{"correct": True}, {"correct": True}], "mastered": True}


def test_delete_card_returns_true_when_row_deleted(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return {"id": 1}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    assert asyncio.run(pg.delete_card("card1", "u1")) is True


def test_delete_card_returns_false_when_not_found(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    assert asyncio.run(pg.delete_card("ghost", "u1")) is False
