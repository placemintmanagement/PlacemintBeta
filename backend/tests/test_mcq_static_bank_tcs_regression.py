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

These tests prove (1) and (2) are behavior-preserving for every OTHER
company's actual call shape, the same way test_problem_bank_tcs_regression.py
already proved problem_bank.py's "easy" branch is additive: load HEAD's copy
of mcq_static_bank.py into a throwaway module, run both HEAD and the live
module against byte-identical fake-Mongo state, and diff the output.

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

    def find(self, query=None):
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
def test_sample_mixed_static_part_byte_identical_to_head(
    seed, topic, count, seen_n, head_mcq_static_bank, live_mcq_static_bank,
):
    bank_docs = _bank_docs(topic, 40)
    seen_ids = [f"{topic}-{i}" for i in range(seen_n)]
    user_id = "u-regress"

    head_db = _FakeDb([dict(d) for d in bank_docs], [_seen_doc(user_id, topic, seen_ids)])
    head_mcq_static_bank.init(head_db)
    random.seed(seed)
    before_items, before_live_n = asyncio.run(
        head_mcq_static_bank.sample_mixed_static_part(user_id, topic, count)
    )

    live_db = _FakeDb([dict(d) for d in bank_docs], [_seen_doc(user_id, topic, seen_ids)])
    live_mcq_static_bank.init(live_db)
    random.seed(seed)
    after_items, after_live_n = asyncio.run(
        live_mcq_static_bank.sample_mixed_static_part(user_id, topic, count)
    )

    before_ids = [it["id"] for it in before_items]
    after_ids = [it["id"] for it in after_items]
    assert before_ids == after_ids, (
        f"topic={topic} count={count} seed={seed}: HEAD gave {before_ids}, current gives {after_ids}"
    )
    assert before_live_n == after_live_n


# ---- 2. sample_static_with_reuse -- Capgemini R2 Technical's real shape ---

@pytest.mark.parametrize("seed", [0, 7, 2026])
@pytest.mark.parametrize("topic,bank_n,count,seen_n", [
    ("oops", 10, 6, 0),    # fresh -- no shortfall, no reuse needed
    ("dbms", 5, 8, 2),     # returning candidate + shortfall -- exercises reuse
    ("cn", 3, 6, 0),       # bank smaller than count even unseen -- unfilled path
])
def test_sample_static_with_reuse_byte_identical_to_head_when_rng_omitted(
    seed, topic, bank_n, count, seen_n, head_mcq_static_bank, live_mcq_static_bank,
):
    # Every real production call site (the static_only branch of
    # _generate_extra_topics) omits `rng` -- exactly like this test.
    bank_docs = _bank_docs(topic, bank_n)
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
    random.seed(seed)
    a_items, a_reused, a_unfilled = asyncio.run(
        live_mcq_static_bank.sample_static_with_reuse(user_id, topic, count)
    )

    b_ids = [it["id"] for it in b_items]
    a_ids = [it["id"] for it in a_items]
    assert b_ids == a_ids, (
        f"topic={topic} bank_n={bank_n} count={count} seed={seed}: "
        f"HEAD gave {b_ids}, current gives {a_ids}"
    )
    assert (b_reused, b_unfilled) == (a_reused, a_unfilled)


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

def test_limit_bug_this_diff_fixes_is_real_and_fixed(live_mcq_static_bank):
    """Documents WHY sample_static() needed .limit() at all: without it,
    mongomock_motor's to_list(length=count) silently ignores `length` and
    returns the WHOLE matching set, over-filling the section. This is a
    test-double bug (real motor/pymongo honors to_list(length=...)
    correctly), but since this repo's new TCS test suite uses
    mongomock_motor, the fix had to land in production code. Guard against
    ever regressing it by asserting the live code path actually caps the
    result at `count` even when the fake cursor WOULD over-return."""
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

        def find(self, query=None):
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
    items = asyncio.run(live_mcq_static_bank.sample_static("u1", "aptitude", 3))
    assert len(items) == 3, (
        f"expected exactly 3 items (the requested count) even with an "
        f"over-returning cursor, got {len(items)} -- the .limit(count) fix regressed"
    )
