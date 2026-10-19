"""Unit tests for repositories/capgemini_bank_pg.py -- mocks fetch_all
directly. Mirrors backend/server.py's capgemini_round1/capgemini_round2
OA-section branches (db.capgemini_round1_bank.find / db.capgemini_round2_bank.find)."""
from __future__ import annotations

import asyncio

from repositories import capgemini_bank_pg as pg


def test_list_round1_by_section_returns_data_column_only(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [
            {"data": {"question_id": "g1", "prompt": "fix this sentence"}},
            {"data": {"question_id": "g2", "prompt": "fix that sentence"}},
        ]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(pg.list_round1_by_section("grammar_correction"))
    assert captured["sql"] == "SELECT data FROM capgemini_round1_bank WHERE section = %s"
    assert captured["params"] == ["grammar_correction"]
    # The whole original document lives in `data` -- returned as-is, not
    # re-wrapped, so draw_section1_questions etc. see question_id/prompt
    # directly at the top level exactly like the Mongo doc did.
    assert rows == [
        {"question_id": "g1", "prompt": "fix this sentence"},
        {"question_id": "g2", "prompt": "fix that sentence"},
    ]


def test_list_round1_by_section_with_tts_status_filters_inside_jsonb(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"data": {"clip_id": "c1", "tts_status": "generated"}}]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(
        pg.list_round1_by_section("listening_comprehension", tts_status="generated")
    )
    assert "data->>'tts_status' = %s" in captured["sql"]
    assert captured["params"] == ["listening_comprehension", "generated"]
    assert rows == [{"clip_id": "c1", "tts_status": "generated"}]


def test_list_round2_all_returns_rows_directly(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        return [
            {
                "scenario_id": "s1",
                "section": "ai_literacy",
                "domain": "ethics",
                "batch_number": 1,
                "scenario_title": "Bias in hiring",
                "scenario_text": "...",
                "questions": [{"q": "What is bias?"}],
            }
        ]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(pg.list_round2_all())
    assert "capgemini_round2_bank" in captured["sql"]
    assert "WHERE" not in captured["sql"]
    assert rows[0]["scenario_id"] == "s1"
    assert rows[0]["questions"] == [{"q": "What is bias?"}]
