"""Unit tests for banks/mcq_static_bank.py's DB_BACKEND dispatch
(SUPABASE_CUTOVER_PLAN.md Step 1) -- confirms sample_static()/_draw_bucket()/
topic_bank_size() call the right repositories/mcq_static_bank_pg.py function
under DB_BACKEND=supabase, that per-user seen-tracking (mcq_static_bank_seen)
keeps going through the SAME Mongo fake regardless of backend (this is the
design that resolves SUPABASE_CUTOVER_PLAN.md's gap #3 without touching
question_seen/Step 3 -- see mcq_static_bank._db_backend()'s docstring), and
that the DEFAULT (DB_BACKEND unset) still runs the exact original Mongo-fake
path untouched."""
from __future__ import annotations

import asyncio

import pytest

from banks import mcq_static_bank
from repositories import mcq_static_bank_pg


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, length=None):
        return self._docs[:length] if length is not None else list(self._docs)


class _FakeBankCollection:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query, projection=None):
        out = list(self.docs)
        qid_filter = query.get("question_id")
        if isinstance(qid_filter, dict):
            if "$nin" in qid_filter:
                excl = set(qid_filter["$nin"])
                out = [d for d in out if d["question_id"] not in excl]
            if "$in" in qid_filter:
                allowed = set(qid_filter["$in"])
                out = [d for d in out if d["question_id"] in allowed]
        if "topic" in query:
            out = [d for d in out if d["topic"] == query["topic"]]
        return _FakeCursor(out)

    async def count_documents(self, query):
        return len([d for d in self.docs if d.get("topic") == query.get("topic")])


class _FakeSeenCollection:
    def __init__(self):
        self.docs = {}
        self.update_calls = []

    async def find_one(self, query):
        return self.docs.get((query["user_id"], query["topic"]))

    async def update_one(self, filter_, update, upsert=False):
        self.update_calls.append((filter_, update))


class _FakeDb:
    def __init__(self, docs):
        self.mcq_static_bank = _FakeBankCollection(docs)
        self.mcq_static_bank_seen = _FakeSeenCollection()


SAMPLE_DOCS = [
    {"question_id": "q1", "topic": "verbal", "prompt": "p1", "options": ["a"], "correct_index": 0, "explanation": "e1", "difficulty": "Easy"},
    {"question_id": "q2", "topic": "verbal", "prompt": "p2", "options": ["b"], "correct_index": 0, "explanation": "e2", "difficulty": "Easy"},
]


@pytest.fixture(autouse=True)
def _reset_db():
    yield
    mcq_static_bank._db = None


def test_sample_static_mongo_default_unchanged(monkeypatch):
    monkeypatch.delenv("DB_BACKEND", raising=False)
    mcq_static_bank._db = _FakeDb(list(SAMPLE_DOCS))
    items = asyncio.run(mcq_static_bank.sample_static("u1", "verbal", 2))
    assert {it["id"] for it in items} == {"q1", "q2"}
    assert mcq_static_bank._db.mcq_static_bank_seen.update_calls, "mark_seen must still run against Mongo"


def test_sample_static_supabase_dispatches_to_repo_and_still_marks_seen_on_mongo(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "supabase")
    mcq_static_bank._db = _FakeDb([])  # Mongo bank content must NOT be read

    captured = {}

    async def fake_sample_random_by_topic(topic, count, difficulty=None, exclude_ids=None):
        captured["args"] = (topic, count, difficulty, exclude_ids)
        return list(SAMPLE_DOCS)

    monkeypatch.setattr(mcq_static_bank_pg, "sample_random_by_topic", fake_sample_random_by_topic)
    items = asyncio.run(mcq_static_bank.sample_static("u1", "verbal", 2))

    assert captured["args"][0] == "verbal"
    assert captured["args"][1] == 2
    assert {it["id"] for it in items} == {"q1", "q2"}
    # Seen-tracking must still be the SAME Mongo fake, untouched by the
    # backend switch -- this is the gap-#3 resolution: question_seen/Step 3
    # is never touched, mcq_static_bank_seen keeps doing this job.
    assert mcq_static_bank._db.mcq_static_bank_seen.update_calls
    marked_ids = mcq_static_bank._db.mcq_static_bank_seen.update_calls[0][1]["$addToSet"]["question_ids"]["$each"]
    assert set(marked_ids) == {"q1", "q2"}


def test_topic_bank_size_mongo_default_unchanged(monkeypatch):
    monkeypatch.delenv("DB_BACKEND", raising=False)
    mcq_static_bank._db = _FakeDb(list(SAMPLE_DOCS))
    n = asyncio.run(mcq_static_bank.topic_bank_size("verbal"))
    assert n == 2


def test_topic_bank_size_supabase_dispatches_to_repo(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "supabase")
    mcq_static_bank._db = _FakeDb([])

    async def fake_count_by_topic(topic):
        assert topic == "verbal"
        return 42

    monkeypatch.setattr(mcq_static_bank_pg, "count_by_topic", fake_count_by_topic)
    n = asyncio.run(mcq_static_bank.topic_bank_size("verbal"))
    assert n == 42


def test_draw_bucket_supabase_dispatches_unseen_and_reuse_fetches(monkeypatch):
    """_draw_bucket is the core of sample_static_with_reuse /
    sample_static_difficulty_weighted_with_reuse (TCS's draw) -- confirms
    BOTH the primary unseen draw and the least-recently-seen reuse fallback
    go through mcq_static_bank_pg under supabase, while seen_at (needed for
    the reuse sort) still comes from the untouched Mongo seen collection."""
    monkeypatch.setenv("DB_BACKEND", "supabase")
    mcq_static_bank._db = _FakeDb([])
    mcq_static_bank._db.mcq_static_bank_seen.docs[("u1", "verbal")] = {
        "seen_at": {"q_old": "2020-01-01T00:00:00+00:00"},
    }

    async def fake_sample_random_by_topic(topic, count, difficulty=None, exclude_ids=None):
        # Simulate only 1 unseen row available -- forces the reuse fallback.
        return [{"question_id": "q_new", "topic": topic, "prompt": "p", "options": [], "correct_index": 0, "explanation": "", "difficulty": difficulty or "Medium"}]

    async def fake_list_by_topic(topic, difficulty=None, exclude_ids=None):
        return [{"question_id": "q_old", "topic": topic, "prompt": "p_old", "options": [], "correct_index": 0, "explanation": "", "difficulty": difficulty or "Medium"}]

    monkeypatch.setattr(mcq_static_bank_pg, "sample_random_by_topic", fake_sample_random_by_topic)
    monkeypatch.setattr(mcq_static_bank_pg, "list_by_topic", fake_list_by_topic)

    items, reused = asyncio.run(
        mcq_static_bank._draw_bucket("u1", "verbal", "Medium", 2, set(), None)
    )
    assert {it["id"] for it in items} == {"q_new", "q_old"}
    assert reused == 1
