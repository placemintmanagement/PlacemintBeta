"""Static-only Capgemini draw: no LLM call, least-recently-seen reuse, shortfall warning.
Uses an in-memory fake db (no Mongo, no network).

Every test below is parametrized over DB_BACKEND ("mongo"/"supabase") --
see supabase_dispatch_fake_support.py's module docstring for why: without
this, a GLOBAL DB_BACKEND=supabase (set when running the full suite against
real Postgres) would silently redirect sb.sample_static_with_reuse's calls
into repositories/mcq_static_bank_pg.py with no real Postgres underneath,
erroring instead of exercising the reuse/recycling behavior this file
actually checks. The "supabase" param installs a fake that reads from the
SAME fake Mongo db these tests already build, so the real assertions below
run for real under both backends."""
import asyncio
import logging
import re

import pytest

import server
from banks import mcq_static_bank as sb
from supabase_dispatch_fake_support import use_backend


class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def limit(self, n):
        # Mirrors real pymongo/motor cursor chaining: limit() truncates and
        # returns the (same) cursor for further chaining/await.
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        return list(self._docs if length is None else self._docs[:length])


def _matches(doc, query):
    for key, cond in query.items():
        value = doc.get(key)
        if isinstance(cond, dict) and "$nin" in cond:
            if value in cond["$nin"]:
                return False
        elif isinstance(cond, dict) and "$in" in cond:
            # Added for sample_static's 2026-10 randomization rewrite: it
            # now fetches its final `count` documents by a $in-on-id query.
            if value not in cond["$in"]:
                return False
        elif value != cond:
            return False
    return True


class _Coll:
    def __init__(self, docs=None):
        self.docs = docs if docs is not None else []

    def find(self, query=None, projection=None):
        # `projection` accepted (and ignored -- this fake always returns
        # whole docs) for sample_static's new id-only projection query.
        return _Cursor([d for d in self.docs if _matches(d, query or {})])

    async def find_one(self, query=None):
        for d in self.docs:
            if _matches(d, query or {}):
                return dict(d)
        return None

    async def update_one(self, query, update, upsert=False):
        target = next((d for d in self.docs if _matches(d, query)), None)
        if target is None:
            if not upsert:
                return
            target = dict(query)
            self.docs.append(target)
        for field, values in update.get("$addToSet", {}).items():
            target.setdefault(field, [])
            for v in values.get("$each", []):
                if v not in target[field]:
                    target[field].append(v)
        for field, value in update.get("$set", {}).items():
            if "." in field:
                head, sub = field.split(".", 1)
                target.setdefault(head, {})[sub] = value
            else:
                target[field] = value


class _FakeDb:
    def __init__(self, bank_docs, seen_docs=None):
        self.mcq_static_bank = _Coll(bank_docs)
        self.mcq_static_bank_seen = _Coll(seen_docs or [])


def _bank(topic, n):
    return [{
        "topic": topic, "question_id": f"{topic}-{i:03d}", "prompt": f"{topic} q{i}",
        "options": ["a", "b", "c", "d"], "correct_index": 0, "explanation": "",
    } for i in range(n)]


def _use(monkeypatch, db, backend="mongo"):
    monkeypatch.setattr(sb, "_db", db)
    use_backend(monkeypatch, backend)


@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_fresh_user_gets_unseen_questions_without_reuse(monkeypatch, backend):
    _use(monkeypatch, _FakeDb(_bank("dsa", 5)), backend)
    items, reused, unfilled = asyncio.run(sb.sample_static_with_reuse("u1", "dsa", 3))
    assert len(items) == 3 and reused == 0 and unfilled == 0


@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_exhausted_topic_reuses_least_recently_seen(monkeypatch, backend):
    seen = [{
        "user_id": "u1", "topic": "dsa",
        "question_ids": [f"dsa-{i:03d}" for i in range(5)],
        "seen_at": {
            "dsa-000": "2026-01-01T00:00:00+00:00",  # oldest
            "dsa-001": "2026-01-02T00:00:00+00:00",
            "dsa-002": "2026-01-03T00:00:00+00:00",
            "dsa-003": "2026-01-04T00:00:00+00:00",
            "dsa-004": "2026-01-05T00:00:00+00:00",  # newest
        },
    }]
    _use(monkeypatch, _FakeDb(_bank("dsa", 5), seen), backend)
    items, reused, unfilled = asyncio.run(sb.sample_static_with_reuse("u1", "dsa", 3))
    assert len(items) == 3 and reused == 3 and unfilled == 0
    assert [it["id"] for it in items] == ["dsa-000", "dsa-001", "dsa-002"]


@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_bank_smaller_than_request_reports_unfilled(monkeypatch, backend):
    seen = [{"user_id": "u1", "topic": "dsa", "question_ids": ["dsa-000", "dsa-001"]}]
    _use(monkeypatch, _FakeDb(_bank("dsa", 2), seen), backend)
    items, reused, unfilled = asyncio.run(sb.sample_static_with_reuse("u1", "dsa", 3))
    assert len(items) == 2 and reused == 2 and unfilled == 1


@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_static_only_draw_never_calls_llm_and_logs_shortfall(monkeypatch, caplog, backend):
    seen = [{"user_id": "u1", "topic": "dsa", "question_ids": [f"dsa-{i:03d}" for i in range(5)]}]
    _use(monkeypatch, _FakeDb(_bank("dsa", 5), seen), backend)

    def _boom(*args, **kwargs):
        raise AssertionError("LLM called on the static-only path")

    monkeypatch.setattr(server, "call_json", _boom)
    monkeypatch.setattr(server.mcq_pool, "fallback_live_verify_topic", _boom)
    monkeypatch.setattr(server.mcq_pool, "pop_from_pool", _boom)
    caplog.set_level(logging.WARNING, logger="server")
    got = asyncio.run(server._generate_extra_topics(
        "Capgemini", [{"key": "dsa", "name": "DSA", "count": 3}], None, "u1", static_only=True,
    ))
    assert len(got) == 3 and all(q["topic"] == "DSA" for q in got)
    shortfall = [r for r in caplog.records if "static bank shortfall" in r.getMessage()]
    assert shortfall and "dsa" in shortfall[0].getMessage() and "reused 3" in shortfall[0].getMessage()


def test_pool_worker_flag_defaults_on_and_accepts_off_values():
    assert server.mcq_pool_worker_enabled(None) is True
    assert server.mcq_pool_worker_enabled("") is True
    assert server.mcq_pool_worker_enabled("1") is True
    assert server.mcq_pool_worker_enabled("true") is True
    for off in ("0", "false", "no", "off", " OFF ", "False"):
        assert server.mcq_pool_worker_enabled(off) is False, off


@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_legacy_seen_entries_without_seen_at_sort_as_oldest(monkeypatch, backend):
    # dsa-000 and dsa-001 were served before seen_at existed; dsa-002 has a timestamp.
    seen = [{
        "user_id": "u1", "topic": "dsa", "question_ids": ["dsa-000", "dsa-001", "dsa-002"],
        "seen_at": {"dsa-002": "2026-02-01T00:00:00+00:00"},
    }]
    _use(monkeypatch, _FakeDb(_bank("dsa", 3), seen), backend)
    items, reused, unfilled = asyncio.run(sb.sample_static_with_reuse("u1", "dsa", 2))
    assert reused == 2 and unfilled == 0
    assert {it["id"] for it in items} == {"dsa-000", "dsa-001"}


@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_reuse_never_returns_a_question_twice_in_one_draw(monkeypatch, backend):
    seen = [{"user_id": "u1", "topic": "dsa", "question_ids": [f"dsa-{i:03d}" for i in range(4)]}]
    _use(monkeypatch, _FakeDb(_bank("dsa", 4), seen), backend)
    items, _, _ = asyncio.run(sb.sample_static_with_reuse("u1", "dsa", 4))
    ids = [it["id"] for it in items]
    assert len(ids) == len(set(ids)) == 4
