"""Unit tests for banks/mcq_pool.py's DB_BACKEND dispatch (SUPABASE_CUTOVER_
PLAN.md Step 1) -- confirms pop_from_pool()/pool_stats() call the right
repositories/mcq_pool_pg.py function and shape the result correctly under
DB_BACKEND=supabase, AND that the DEFAULT (DB_BACKEND unset) still runs the
exact original Mongo-fake path untouched -- the single most important
correctness property of this task (see SUPABASE_CUTOVER_PLAN.md condition 2).
"""
from __future__ import annotations

import asyncio

import pytest

from banks import mcq_pool
from repositories import mcq_pool_pg


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, length=None):
        return self._docs[:length] if length is not None else list(self._docs)

    def __aiter__(self):
        self._i = 0
        return self

    async def __anext__(self):
        if self._i >= len(self._docs):
            raise StopAsyncIteration
        item = self._docs[self._i]
        self._i += 1
        return item


class _FakeCollection:
    def __init__(self, docs):
        self.docs = docs
        self.aggregate_calls = 0

    def find(self, query=None, projection=None):
        return _FakeCursor(list(self.docs))

    async def find_one_and_delete(self, query):
        if not self.docs:
            return None
        return self.docs.pop(0)

    def aggregate(self, pipeline):
        self.aggregate_calls += 1
        return _AsyncIter(list(self.docs))


class _AsyncIter:
    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        self._i = 0
        return self

    async def __anext__(self):
        if self._i >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._i]
        self._i += 1
        return item


class _FakeDb:
    def __init__(self, pool_docs=None, stats_docs=None):
        self.mcq_pool = _FakeCollection(pool_docs or [])
        self.mcq_pool_stats = _FakeCollection(stats_docs or [])


@pytest.fixture(autouse=True)
def _reset_mcq_pool_db():
    yield
    mcq_pool._db = None


def test_pop_from_pool_mongo_default_unchanged(monkeypatch):
    """DB_BACKEND unset -- must run the exact original Mongo fake path."""
    monkeypatch.delenv("DB_BACKEND", raising=False)
    docs = [
        {"prompt": "2+2?", "options": ["3", "4"], "correct_index": 1, "explanation": "basic math", "difficulty": "Easy"},
    ]
    mcq_pool._db = _FakeDb(pool_docs=docs)
    out = asyncio.run(mcq_pool.pop_from_pool("TCS", "aptitude", "Aptitude", 5))
    assert out == [{
        "id": "q1", "prompt": "2+2?", "options": ["3", "4"],
        "correct_index": 1, "explanation": "basic math", "difficulty": "Easy",
    }]


def test_pop_from_pool_supabase_dispatches_to_repo(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "supabase")
    mcq_pool._db = _FakeDb()  # mongo handle present but must NOT be touched

    captured = {}

    async def fake_pop_up_to(company_name, section_key, count):
        captured["args"] = (company_name, section_key, count)
        return [
            {"pool_id": "p1", "prompt": "q1?", "options": ["a", "b"], "correct_index": 0, "explanation": None, "difficulty": "Medium"},
            {"pool_id": "p2", "prompt": "q2?", "options": ["c", "d"], "correct_index": 1, "explanation": "exp2", "difficulty": "Hard"},
        ]

    monkeypatch.setattr(mcq_pool_pg, "pop_up_to", fake_pop_up_to)
    out = asyncio.run(mcq_pool.pop_from_pool("TCS", "aptitude", "Aptitude", 5))
    assert captured["args"] == ("TCS", "aptitude", 5)
    assert out == [
        {"id": "q1", "prompt": "q1?", "options": ["a", "b"], "correct_index": 0, "explanation": "", "difficulty": "Medium"},
        {"id": "q2", "prompt": "q2?", "options": ["c", "d"], "correct_index": 1, "explanation": "exp2", "difficulty": "Hard"},
    ]


def test_pool_stats_mongo_default_unchanged(monkeypatch):
    monkeypatch.delenv("DB_BACKEND", raising=False)
    pool_docs = [{"company_name": "TCS", "section_key": "aptitude", "count": 2}]
    stats_docs = [{"company_name": "TCS", "section_key": "aptitude", "total_generated": 10, "outcome_accepted": 5}]
    mcq_pool._db = _FakeDb(pool_docs=pool_docs, stats_docs=stats_docs)
    result = asyncio.run(mcq_pool.pool_stats())
    assert result["pool_counts"] == pool_docs
    assert result["stats"][0]["acceptance_rate_pct"] == 50.0


def test_pool_stats_supabase_dispatches_to_repo_and_merges_pool_counts_gap_fix(monkeypatch):
    """Gap fix proof (SUPABASE_CUTOVER_PLAN.md punch-list #1): under
    DB_BACKEND=supabase, pool_stats() must return a non-empty pool_counts
    (previously the illustration in the plan showed this as `[]` -- a known
    gap -- now fixed via mcq_pool_pg.count_by_company_and_section())."""
    monkeypatch.setenv("DB_BACKEND", "supabase")
    mcq_pool._db = _FakeDb()

    async def fake_count_by_company_and_section():
        return [{"company_name": "TCS", "section_key": "aptitude", "count": 7}]

    async def fake_get_all_stats():
        return [{"company_name": "TCS", "section_key": "aptitude", "total_generated": 4, "outcome_accepted": 2}]

    monkeypatch.setattr(mcq_pool_pg, "count_by_company_and_section", fake_count_by_company_and_section)
    monkeypatch.setattr(mcq_pool_pg, "get_all_stats", fake_get_all_stats)

    result = asyncio.run(mcq_pool.pool_stats())
    assert result["pool_counts"] == [{"company_name": "TCS", "section_key": "aptitude", "count": 7}]
    assert result["stats"][0]["acceptance_rate_pct"] == 50.0
    assert result["stats"][0]["from_execution"] == 0
    assert "buffer_target" in result and "pipeline" in result
