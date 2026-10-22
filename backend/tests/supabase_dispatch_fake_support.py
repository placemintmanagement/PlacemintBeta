"""Shared helper for exercising banks/mcq_static_bank.py's DB_BACKEND=supabase
dispatch branch (SUPABASE_CUTOVER_PLAN.md Step 1) inside pre-existing
behavioral test files, without a real Postgres connection.

Why this exists: several test files written before the DB_BACKEND cutover
(test_tcs_difficulty_weighted_draw.py, test_mcq_static_bank_tcs_regression.py,
test_tcs_zero_ai.py, test_static_reuse.py, test_oa_draw_persistence.py) call
banks/mcq_static_bank.py's public functions directly against a hand-built
Mongo fake or a real mongomock_motor db, without themselves ever setting
DB_BACKEND. That's fine in isolation -- mcq_static_bank._db_backend() reads
`os.environ.get("DB_BACKEND", "mongo")` fresh on every call, defaulting to
"mongo" when unset. But it means that when the product owner runs the FULL
suite with DB_BACKEND=supabase set globally (to prove the Postgres path),
these same calls get silently redirected into the real repositories/
mcq_static_bank_pg.py functions, which have no live Postgres underneath in
a unit-test run -- every one of these tests then errors instead of
exercising the Mongo-fake behavior it was actually written to check (see
SUPABASE_CUTOVER_PLAN.md's Step 1 test-coverage gap: "no test exercises any
of these routes end-to-end with DB_BACKEND=supabase").

The fix applied in each of those 5 files: parametrize every affected test
over backend in ("mongo", "supabase"). "mongo" changes nothing (DB_BACKEND
stays unset, exactly today's behavior). "supabase" sets DB_BACKEND=supabase
AND installs the fake below, which monkeypatches
repositories/mcq_static_bank_pg.py's functions to read from the SAME
Mongo-shaped collection the test already built -- reached indirectly
through banks.mcq_static_bank's own `_db` module global, exactly as the
test already set it (mcq_static_bank.init(db) or
monkeypatch.setattr(mcq_static_bank, "_db", db)) -- instead of a real
Postgres connection. This re-implements each pg function's query shape
(topic/difficulty/exclude_ids filtering, "random" sampling) against that
same fixture data, so every test's real assertions (shuffle correctness,
least-recently-seen recycling, no in-attempt duplicates, zero-AI
invariants, draw-once persistence, ...) execute for real under BOTH
backends -- proving mcq_static_bank.py's dispatch branches themselves,
rather than merely re-running the untouched Mongo path twice. The
repositories/mcq_static_bank_pg.py functions THEMSELVES already have their
own dedicated mocked tests (test_repositories_mcq_static_bank_pg.py) and
live-Supabase coverage (test_live_supabase_integration.py) -- this helper
is not trying to re-prove those, only that mcq_static_bank.py calls them
correctly and the bank-level CONTRACT survives the switch.

install_mcq_static_bank_pg_fake() is lazy: it takes no db/collection
argument. It reads banks.mcq_static_bank._db at CALL TIME (not at
monkeypatch-install time), so it works regardless of whether the test sets
`_db` before or after calling this installer, and regardless of which
Mongo fake class backs it (AsyncMongoMockClient's real collections, or any
of this suite's several hand-rolled `_Coll`/`_FakeDb` doubles) -- every one
of those already implements `.find(query).to_list(length=None)`, which is
all this helper needs.
"""
from __future__ import annotations

import random


async def _all_docs(collection) -> list:
    """`collection.find({}).to_list(length=None)` -- supported by both
    mongomock_motor's real collections and every hand-rolled Mongo-fake
    collection class in this test suite (they all implement at least this
    much of the Motor cursor protocol already, for the plain unfiltered
    case)."""
    return await collection.find({}).to_list(length=None)


def install_mcq_static_bank_pg_fake(monkeypatch) -> None:
    """Monkeypatches repositories/mcq_static_bank_pg.py's content-read
    functions (count_by_topic/list_by_topic/sample_random_by_topic/
    get_by_ids) to query banks.mcq_static_bank._db.mcq_static_bank --
    whatever Mongo fake the calling test has set there -- instead of a real
    Postgres connection. Filtering (topic/difficulty/exclude_ids) mirrors
    the real pg module's WHERE clauses exactly; `sample_random_by_topic`
    does a genuine `random.shuffle` before slicing, mirroring Postgres's
    `ORDER BY random()` (a real reshuffle, not insertion order) the same
    way the real function does.

    Call this AFTER DB_BACKEND is set to "supabase" for the test (order
    relative to setting banks.mcq_static_bank._db doesn't matter -- see
    module docstring)."""
    from banks import mcq_static_bank as bank_mod
    from repositories import mcq_static_bank_pg as pg

    async def _bank_docs():
        if bank_mod._db is None:
            return []
        return await _all_docs(bank_mod._db.mcq_static_bank)

    async def fake_count_by_topic(topic):
        docs = await _bank_docs()
        return sum(1 for d in docs if d.get("topic") == topic)

    async def fake_list_by_topic(topic, difficulty=None, exclude_ids=None):
        docs = await _bank_docs()
        excl = set(exclude_ids or [])
        return [
            dict(d) for d in docs
            if d.get("topic") == topic
            and (difficulty is None or d.get("difficulty") == difficulty)
            and d.get("question_id") not in excl
        ]

    async def fake_sample_random_by_topic(topic, count, difficulty=None, exclude_ids=None):
        if count <= 0:
            return []
        candidates = await fake_list_by_topic(topic, difficulty=difficulty, exclude_ids=exclude_ids)
        random.shuffle(candidates)
        return candidates[:count]

    async def fake_get_by_ids(question_ids):
        if not question_ids:
            return []
        ids = set(question_ids)
        docs = await _bank_docs()
        return [dict(d) for d in docs if d.get("question_id") in ids]

    monkeypatch.setattr(pg, "count_by_topic", fake_count_by_topic)
    monkeypatch.setattr(pg, "list_by_topic", fake_list_by_topic)
    monkeypatch.setattr(pg, "sample_random_by_topic", fake_sample_random_by_topic)
    monkeypatch.setattr(pg, "get_by_ids", fake_get_by_ids)


def use_backend(monkeypatch, backend: str) -> None:
    """Sets (or unsets) DB_BACKEND for one test and, for "supabase",
    installs the fake above. Call this AFTER the test's own db/_db setup
    (init(db) / monkeypatch.setattr(mcq_static_bank, "_db", db)) has run,
    so the fake's lazy lookups see the right object regardless -- order
    doesn't actually matter (see module docstring) but keeping it after is
    the house convention used in each caller below."""
    if backend == "supabase":
        monkeypatch.setenv("DB_BACKEND", "supabase")
        install_mcq_static_bank_pg_fake(monkeypatch)
    else:
        monkeypatch.delenv("DB_BACKEND", raising=False)
