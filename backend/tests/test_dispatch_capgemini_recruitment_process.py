"""Unit tests for capgemini_recruitment_process's new fetch_round1_pool()/
fetch_round2_pool() (SUPABASE_CUTOVER_PLAN.md Step 1, gap #4) -- these
replace what used to be 6+1 inline `db.capgemini_round1_bank.find(...)` /
`db.capgemini_round2_bank.find(...)` call sites directly in server.py.
Confirms DB_BACKEND=supabase dispatches to repositories/capgemini_bank_pg.py,
and that DB_BACKEND unset still runs the exact original Mongo-fake query
shape (query dict + {"_id": 0} projection) unchanged."""
from __future__ import annotations

import asyncio

import pytest

from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini import (
    capgemini_recruitment_process as crp,
)
from repositories import capgemini_bank_pg


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, length=None):
        return list(self._docs)


class _FakeCollection:
    def __init__(self, docs):
        self.docs = docs
        self.last_query = None

    def find(self, query, projection=None):
        self.last_query = query
        out = [d for d in self.docs if all(d.get(k) == v for k, v in query.items())]
        return _FakeCursor(out)


class _FakeDb:
    def __init__(self, r1_docs=None, r2_docs=None):
        self.capgemini_round1_bank = _FakeCollection(r1_docs or [])
        self.capgemini_round2_bank = _FakeCollection(r2_docs or [])


@pytest.fixture(autouse=True)
def _reset_db():
    yield
    crp._db = None


def test_fetch_round1_pool_mongo_default_unchanged(monkeypatch):
    monkeypatch.delenv("DB_BACKEND", raising=False)
    crp._db = _FakeDb(r1_docs=[{"section": "grammar_correction", "question_id": "g1"}])
    pool = asyncio.run(crp.fetch_round1_pool("grammar_correction"))
    assert pool == [{"section": "grammar_correction", "question_id": "g1"}]
    assert crp._db.capgemini_round1_bank.last_query == {"section": "grammar_correction"}


def test_fetch_round1_pool_with_tts_status_mongo_default_unchanged(monkeypatch):
    monkeypatch.delenv("DB_BACKEND", raising=False)
    crp._db = _FakeDb(r1_docs=[{"section": "listening_comprehension", "tts_status": "generated", "clip_id": "c1"}])
    pool = asyncio.run(crp.fetch_round1_pool("listening_comprehension", tts_status="generated"))
    assert pool == [{"section": "listening_comprehension", "tts_status": "generated", "clip_id": "c1"}]
    assert crp._db.capgemini_round1_bank.last_query == {"section": "listening_comprehension", "tts_status": "generated"}


def test_fetch_round1_pool_supabase_dispatches_to_repo(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "supabase")
    crp._db = _FakeDb()  # Mongo must NOT be read

    captured = {}

    async def fake_list_round1_by_section(section, tts_status=None):
        captured["args"] = (section, tts_status)
        return [{"question_id": "g1"}]

    monkeypatch.setattr(capgemini_bank_pg, "list_round1_by_section", fake_list_round1_by_section)
    pool = asyncio.run(crp.fetch_round1_pool("grammar_correction"))
    assert captured["args"] == ("grammar_correction", None)
    assert pool == [{"question_id": "g1"}]


def test_fetch_round2_pool_mongo_default_unchanged(monkeypatch):
    monkeypatch.delenv("DB_BACKEND", raising=False)
    crp._db = _FakeDb(r2_docs=[{"scenario_id": "s1"}])
    pool = asyncio.run(crp.fetch_round2_pool())
    assert pool == [{"scenario_id": "s1"}]


def test_fetch_round2_pool_supabase_dispatches_to_repo(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "supabase")
    crp._db = _FakeDb()

    async def fake_list_round2_all():
        return [{"scenario_id": "s1"}]

    monkeypatch.setattr(capgemini_bank_pg, "list_round2_all", fake_list_round2_all)
    pool = asyncio.run(crp.fetch_round2_pool())
    assert pool == [{"scenario_id": "s1"}]
