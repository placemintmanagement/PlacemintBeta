"""Regression tests for the TCS-driven banks/mcq_static_bank.py changes:

  1. sample_static() gained a trailing `.limit(count)` on its cursor (fixes
     mongomock_motor's to_list(length=...) silently ignoring its length
     argument -- a test-double bug, not a prod one, but the fix needed
     proving it changes nothing for real callers).
  2. sample_static_with_reuse() gained an optional `rng` kwarg, used ONLY
     to break ties among candidates sharing the same seen_at. Every
     existing caller omits it.
  3. topic_bank_size() is a brand-new function, not a modification -- no
     existing caller can be affected by it.

UPDATE (2026-10, "make the Capgemini/non-TCS draw genuinely random" pass):
sample_static() was rewritten to actually shuffle its unseen pool before
picking `count` (previously pure Mongo cursor/insertion order -- confirmed
dead code for randomness: every fresh user got the identical first `count`
questions). Tests 1 and 2 below used to assert the EXACT id sequence was
byte-identical between HEAD and the live module -- that assumption is now
WRONG BY DESIGN (the whole point of this change is that the draw differs
run to run without an explicit rng), so both were rewritten to assert the
new contract instead: same total count, same live_n, no duplicates, and
every drawn id actually belongs to the real candidate pool. The fake
collection's `_matches`/`find()` also gained `$in` and a `projection` param,
since sample_static's new id-then-fetch-by-id design needs both.

These tests prove the NEW contract holds for every OTHER company's actual
call shape (same technique test_problem_bank_tcs_regression.py established:
load HEAD's copy of mcq_static_bank.py into a throwaway module, run both
HEAD and the live module against byte-identical fake-Mongo state, and
compare).

Real call shapes exercised (grepped from server.py / companies.py at
write-time):
  - sample_mixed_static_part(user_id, topic, count) -- used by every
    plain-mcq company section that maps to a canonical topic (Infosys
    aptitude/reasoning, Wipro's per-group topic mix, the pseudocode
    section, etc.) and by _generate_topic_mix. Calls sample_static()
    internally -- this is what the .limit() fix must not change.
  - sample_static_with_reuse(user_id, topic, count) -- used by
    _generate_extra_topics's static_only=True branch (today: Capgemini
    Round 2 Technical). Called WITHOUT rng, same as every production call
    site except TCS's own tcs_recruitment_process.py.

Both call shapes are exercised with a non-empty pre-existing "seen" state
(the $nin exclude argument), not just a fresh user, since that's the
realistic shape for a returning candidate.
"""
import asyncio
import random
import subprocess
import types
from pathlib import Path

import pytest

from supabase_dispatch_fake_support import use_backend

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

# Pinned to the last commit BEFORE this diff landed, not a floating "HEAD"
# -- see test_problem_bank_tcs_regression.py's identical comment for why a
# bare "HEAD:" lookup breaks the moment this diff itself gets committed.
BASELINE_COMMIT = "2155881"


def _load_head_mcq_static_bank() -> types.ModuleType:
    """Load banks/mcq_static_bank.py as it existed at BASELINE_COMMIT
    (before this diff's .limit()/rng/topic_bank_size changes) into a
    standalone module, isolated from the live one under sys.modules."""
    src = subprocess.check_output(
        ["git", "show", f"{BASELINE_COMMIT}:backend/banks/mcq_static_bank.py"],
        cwd=REPO_ROOT, text=True,
    )
    mod = types.ModuleType("mcq_static_bank_at_head")
    mod.__file__ = str(BACKEND_DIR / "banks" / "mcq_static_bank.py")
    exec(compile(src, "<head:banks/mcq_static_bank.py>", "exec"), mod.__dict__)
    return mod


@pytest.fixture(scope="module")
def head_mcq_static_bank():
    return _load_head_mcq_static_bank()


@pytest.fixture(scope="module")
def live_mcq_static_bank():
    from banks import mcq_static_bank as live
    return live


# ---- Minimal fake Mongo double --------------------------------------------
# Supports .limit() (the live module's new call) in addition to to_list(),
# so the SAME fake collection class works for both HEAD's and the live
# module's code unchanged. A real pymongo/motor cursor's .limit() truncates
# and returns the cursor itself for chaining -- mirrored here.

class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def limit(self, n):
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
            # Added for sample_static's 2026-10 randomization rewrite: its
            # second query fetches the picked ids back via $in.
            if value not in cond["$in"]:
                return False
        elif isinstance(cond, dict) and "$exists" in cond:
            has = key in doc
            if has != cond["$exists"]:
                return False
        elif value != cond:
            return False
    return True


class _Coll:
    def __init__(self, docs=None):
        self.docs = docs if docs is not None else []

    def find(self, query=None, projection=None):
        # `projection` accepted (and ignored -- always returns whole docs)
        # for sample_static's new id-only projection query.
        return _Cursor([dict(d) for d in self.docs if _matches(d, query or {})])

    async def find_one(self, query=None):
        for d in self.docs:
            if _matches(d, query or {}):
                return dict(d)
        return None

    async def count_documents(self, query=None):
        return sum(1 for d in self.docs if _matches(d, query or {}))

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


def _bank_docs(topic: str, n: int, prefix: str = "") -> list:
    return [
        {
            "topic": topic, "question_id": f"{prefix}{topic}-{i}",
            "prompt": f"{topic} q{i}", "options": ["A", "B", "C", "D"],
            "correct_index": 0, "explanation": "because", "difficulty": "Medium",
        }
        for i in range(n)
    ]


def _seen_doc(user_id: str, topic: str, seen_ids: list) -> dict:
    # seen_at intentionally omitted for some ids -- mirrors real "legacy"
    # entries from before seen_at existed, same edge case test_static_reuse.py
    # already covers for the un-diffed sort behavior.
    return {"user_id": user_id, "topic": topic, "question_ids": list(seen_ids)}


# ---- 1. sample_mixed_static_part -- every plain-mcq company's real call ---

@pytest.mark.parametrize("seed", [0, 1, 42, 1234, 999999])
@pytest.mark.parametrize("topic,count,seen_n", [
    ("aptitude", 8, 0),    # fresh candidate, no seen history
    ("reasoning", 6, 3),   # returning candidate, partial seen history
    ("verbal", 25, 10),    # TCS-shaped count, but via the GENERIC path
])
@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_sample_mixed_static_part_same_contract_as_head(
    seed, topic, count, seen_n, head_mcq_static_bank, live_mcq_static_bank, monkeypatch, backend,
):
    """HEAD and the live module no longer draw the identical SEQUENCE (the
    live module's sample_static is now genuinely randomized -- that's the
    deliberate point of this change), but the CONTRACT must match: same
    total served, same live_n backfill need, no duplicates, and every
    served id genuinely belongs to this topic's bank.

    Parametrized over `backend` -- head_mcq_static_bank is a frozen copy
    from BASELINE_COMMIT (predates DB_BACKEND entirely, so it's unaffected
    either way); live_mcq_static_bank IS banks.mcq_static_bank, which forks
    on DB_BACKEND, so "supabase" here proves this same contract holds when
    its draw is dispatched through repositories/mcq_static_bank_pg.py
    (faked below to read the SAME live_db fixture) instead of Mongo."""
    bank_docs = _bank_docs(topic, 40)
    bank_ids = {d["question_id"] for d in bank_docs}
    seen_ids = [f"{topic}-{i}" for i in range(seen_n)]
    user_id = "u-regress"

    head_db = _FakeDb([dict(d) for d in bank_docs], [_seen_doc(user_id, topic, seen_ids)])
    head_mcq_static_bank.init(head_db)
    random.seed(seed)  # inert for the live module now (fresh random.Random() per call), kept for head's own sake
    before_items, before_live_n = asyncio.run(
        head_mcq_static_bank.sample_mixed_static_part(user_id, topic, count)
    )

    live_db = _FakeDb([dict(d) for d in bank_docs], [_seen_doc(user_id, topic, seen_ids)])
    live_mcq_static_bank.init(live_db)
    use_backend(monkeypatch, backend)
    random.seed(seed)
    after_items, after_live_n = asyncio.run(
        live_mcq_static_bank.sample_mixed_static_part(user_id, topic, count)
    )

    after_ids = [it["id"] for it in after_items]
    assert len(after_items) == len(before_items), (
        f"topic={topic} count={count} seed={seed}: HEAD served {len(before_items)}, live served {len(after_items)}"
    )
    assert len(set(after_ids)) == len(after_ids), "duplicate ids within one draw"
    assert set(after_ids).issubset(bank_ids), "drew an id that doesn't belong to this topic's bank"
    assert after_live_n == before_live_n


# ---- 2. sample_static_with_reuse -- Capgemini R2 Technical's real shape ---

@pytest.mark.parametrize("seed", [0, 7, 2026])
@pytest.mark.parametrize("topic,bank_n,count,seen_n", [
    ("oops", 10, 6, 0),    # fresh -- no shortfall, no reuse needed
    ("dbms", 5, 8, 2),     # returning candidate + shortfall -- exercises reuse
    ("cn", 3, 6, 0),       # bank smaller than count even unseen -- unfilled path
])
@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_sample_static_with_reuse_same_contract_as_head_when_rng_omitted(
    seed, topic, bank_n, count, seen_n, head_mcq_static_bank, live_mcq_static_bank, monkeypatch, backend,
):
    """Same deliberate relaxation as test_sample_mixed_static_part_same_
    contract_as_head above: the live module's draw is no longer the exact
    same SEQUENCE as HEAD's (genuinely randomized now), but reused/unfilled
    counts, total served, and no-duplicates must still match exactly.
    Parametrized over `backend` -- same reasoning as that test."""
    # Every real production call site (the static_only branch of
    # _generate_extra_topics) omits `rng` -- exactly like this test.
    bank_docs = _bank_docs(topic, bank_n)
    bank_ids = {d["question_id"] for d in bank_docs}
    seen_ids = [f"{topic}-{i}" for i in range(seen_n)]
    user_id = "u-regress"

    head_db = _FakeDb([dict(d) for d in bank_docs], [_seen_doc(user_id, topic, seen_ids)])
    head_mcq_static_bank.init(head_db)
    random.seed(seed)
    b_items, b_reused, b_unfilled = asyncio.run(
        head_mcq_static_bank.sample_static_with_reuse(user_id, topic, count)
    )

    live_db = _FakeDb([dict(d) for d in bank_docs], [_seen_doc(user_id, topic, seen_ids)])
    live_mcq_static_bank.init(live_db)
    use_backend(monkeypatch, backend)
    random.seed(seed)
    a_items, a_reused, a_unfilled = asyncio.run(
        live_mcq_static_bank.sample_static_with_reuse(user_id, topic, count)
    )

    a_ids = [it["id"] for it in a_items]
    assert len(a_items) == len(b_items), (
        f"topic={topic} bank_n={bank_n} count={count} seed={seed}: "
        f"HEAD served {len(b_items)}, live served {len(a_items)}"
    )
    assert len(set(a_ids)) == len(a_ids), "duplicate ids within one draw"
    assert set(a_ids).issubset(bank_ids), "drew an id that doesn't belong to this topic's bank"
    assert (a_reused, a_unfilled) == (b_reused, b_unfilled)


# ---- 3. new functions are additive, not replacements ----------------------

def test_topic_bank_size_is_new_not_a_modification(head_mcq_static_bank, live_mcq_static_bank):
    assert not hasattr(head_mcq_static_bank, "topic_bank_size"), (
        "topic_bank_size already existed at HEAD -- this is supposed to be a "
        "brand-new function; if it already existed, re-audit what actually changed."
    )
    assert hasattr(live_mcq_static_bank, "topic_bank_size")


def test_sample_static_signature_gained_only_an_optional_trailing_rng_kwarg():
    import inspect
    from banks import mcq_static_bank as live
    sig = inspect.signature(live.sample_static_with_reuse)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["user_id", "topic", "count", "rng"]
    assert params[-1].name == "rng"
    assert params[-1].default is None, "rng must default to None so every existing caller is unaffected"


# ---- 4. the mongomock_motor .limit() bug this diff actually fixes ---------

@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_limit_bug_this_diff_fixes_is_real_and_fixed(live_mcq_static_bank, monkeypatch, backend):
    """Originally documented WHY sample_static() needed .limit() at all:
    without it, mongomock_motor's to_list(length=count) silently ignores
    `length` and returns the WHOLE matching set, over-filling the section.

    UPDATE (2026-10 randomization rewrite): sample_static() no longer
    calls .limit() anywhere -- it fetches ALL unseen ids (deliberately
    unbounded), shuffles them client-side, and takes `count` in Python,
    then fetches exactly those `count` ids back by `$in`. So it is now
    structurally immune to this exact mongomock_motor quirk regardless of
    whether the backing store honors `to_list(length=...)`: the final
    result size is bounded by Python's own slicing, not by what Mongo
    chooses to return. This test (with `_BuggyColl.find` updated to accept
    the new `projection` arg sample_static's id-only query passes) is kept
    as a regression guard for that structural guarantee, not for .limit()
    itself.

    Parametrized over `backend`: under "supabase", sample_static's dispatch
    never touches `_BuggyColl.find()` with `.limit()` at all -- it goes
    through the fake repositories/mcq_static_bank_pg.py install below
    instead, which is immune to this bug by construction. Kept parametrized
    (rather than skipped for "supabase") because the actual guarantee this
    test checks -- "sample_static always returns exactly `count` items
    regardless of backend quirks" -- is exactly as true, and exactly as
    worth proving, under supabase."""
    class _OverReturningCursor:
        """Simulates the exact mongomock_motor bug: to_list(length=N) returns
        more than N if .limit() was never called first."""
        def __init__(self, docs):
            self._docs = docs
            self._limited = None

        def limit(self, n):
            self._limited = n
            return self

        async def to_list(self, length=None):
            if self._limited is not None:
                return list(self._docs[: self._limited])
            return list(self._docs)  # bug: ignores `length` entirely

    class _BuggyColl:
        def __init__(self, docs):
            self.docs = docs

        def find(self, query=None, projection=None):
            # Deliberately ignores `query` too (same as before this
            # update) -- always over-returns every doc, unfiltered.
            return _OverReturningCursor([dict(d) for d in self.docs])

        async def find_one(self, query=None):
            return None

        async def update_one(self, *a, **k):
            return None

    class _BuggyDb:
        def __init__(self, docs):
            self.mcq_static_bank = _BuggyColl(docs)
            self.mcq_static_bank_seen = _BuggyColl([])

    docs = _bank_docs("aptitude", 10)
    live_mcq_static_bank.init(_BuggyDb(docs))
    use_backend(monkeypatch, backend)
    items = asyncio.run(live_mcq_static_bank.sample_static("u1", "aptitude", 3))
    assert len(items) == 3, (
        f"expected exactly 3 items (the requested count) even with an "
        f"over-returning, query-ignoring cursor, got {len(items)}"
    )
    assert len({it["id"] for it in items}) == 3
