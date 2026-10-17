"""TCS-only difficulty-weighted draw (2026-10, "make the TCS draw genuinely
random and difficulty-aware" pass).

Covers:
  1. The draw was never actually random before this change: sample_static()
     has no shuffle at all (pure Mongo cursor/insertion order), and
     sample_static_with_reuse() only randomizes TIES in its reuse-recycling
     path, never the main unseen-first draw. Documented here as a pinned
     regression (not a live-DB experiment -- that was done separately,
     read-only, against Atlas; see this task's own report for those
     numbers) so the "was it ever random" claim stays checkable from code
     alone.
  2. mcq_static_bank.sample_static_difficulty_weighted_with_reuse is new
     and additive: every other company's path (sample_static,
     sample_static_with_reuse, sample_mixed_static_part) is proved
     byte-identical to the commit before this diff landed, using the same
     git-show-a-frozen-copy technique test_mcq_static_bank_tcs_regression.py
     already established.
  3. The new function itself: no in-attempt duplicates, least-recently-seen
     recycling still works, bucket-to-nearest-difficulty fallback (+
     metadata), and many draws land at/near the target difficulty mix.
  4. draw_tcs_foundation_and_advanced actually uses the weighted draw now
     (Foundation + Advanced sections hit their target bucket composition
     when the bank has plenty of every difficulty), while the raw,
     non-weighted _draw_one_topic primitive (and every existing test that
     calls it directly) is untouched.

Uses mongomock_motor's AsyncMongoMockClient (real Mongo query semantics)
for the new function's own tests -- same convention as test_tcs_zero_ai.py.
"""
import asyncio
import random
import subprocess
import types
from pathlib import Path

import pytest
from mongomock_motor import AsyncMongoMockClient

from banks import mcq_static_bank
from departments.computer_science_and_it.group1_it_services_mass_recruiters.tcs import (
    tcs_recruitment_process as tcs,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

# Pinned to the commit BEFORE this diff landed (not a floating "HEAD") --
# same reasoning as test_mcq_static_bank_tcs_regression.py's own comment:
# a bare "HEAD:" lookup breaks the moment this diff itself gets committed.
BASELINE_COMMIT = "a60c25e"


def _mcq_doc(topic, qid, difficulty="Medium"):
    return {
        "topic": topic, "question_id": qid, "prompt": f"{topic} question {qid}",
        "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "because",
        "difficulty": difficulty,
    }


def _seed(db, topic, n, difficulty="Medium", prefix=""):
    docs = [_mcq_doc(topic, f"{prefix}{difficulty.lower()}-{i}", difficulty) for i in range(n)]
    asyncio.run(db.mcq_static_bank.insert_many(docs))
    return [d["question_id"] for d in docs]


def _fresh_db():
    client = AsyncMongoMockClient()
    db = client["test"]
    mcq_static_bank.init(db)
    return db


# ---- 1. Before this change, the draw was cursor/insertion order -----------

def test_sample_static_has_no_shuffle_anywhere_in_its_source():
    """Pinned regression for the "is it actually random" question: confirms
    sample_static's only query is topic + $nin-seen + .limit(count), with
    no .sort()/shuffle call in the function at all -- i.e. whatever order
    Mongo's cursor returns (insertion order in practice) is exactly what
    gets served. If this ever gains a shuffle, this test should be updated
    deliberately, not silently pass through unnoticed."""
    import inspect
    src = inspect.getsource(mcq_static_bank.sample_static)
    assert "shuffle" not in src
    assert "sort(" not in src
    assert ".limit(count)" in src


def test_sample_static_with_reuse_only_shuffles_the_reuse_tiebreak_not_the_main_draw():
    """The OLD flat draw (still used by every non-TCS caller, and by TCS's
    own _draw_one_topic primitive) randomizes ties in the recycle/backfill
    path only -- the primary "serve unseen" call (sample_static) it makes
    internally is never shuffled. This is exactly why every fresh user
    used to get the identical first N questions (confirmed by direct
    experiment against the live bank, read-only, separately from this
    suite)."""
    import inspect
    src = inspect.getsource(mcq_static_bank.sample_static_with_reuse)
    # The one shuffle CALL that exists is gated on `rng is not None` and
    # only touches `candidates` (the reuse pool), never the sample_static()
    # call that serves the unseen-first items. (Counting ".shuffle(" rather
    # than the bare word "shuffle" since the docstring's own prose mentions
    # "shuffle" twice without calling it.)
    assert src.count(".shuffle(") == 1
    assert "rng.shuffle(candidates)" in src


# ---- 2. Every other company's path is untouched, byte-identical -----------

def _load_baseline_mcq_static_bank() -> types.ModuleType:
    src = subprocess.check_output(
        ["git", "show", f"{BASELINE_COMMIT}:backend/banks/mcq_static_bank.py"],
        cwd=REPO_ROOT, text=True,
    )
    mod = types.ModuleType("mcq_static_bank_at_baseline")
    mod.__file__ = str(BACKEND_DIR / "banks" / "mcq_static_bank.py")
    exec(compile(src, "<baseline:backend/banks/mcq_static_bank.py>", "exec"), mod.__dict__)
    return mod


@pytest.fixture(scope="module")
def baseline_mcq_static_bank():
    return _load_baseline_mcq_static_bank()


@pytest.fixture(scope="module")
def live_mcq_static_bank():
    from banks import mcq_static_bank as live
    return live


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
        else:
            if value != cond:
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


def _bank_docs(topic, n, prefix=""):
    return [
        {
            "topic": topic, "question_id": f"{prefix}{topic}-{i}",
            "prompt": f"{topic} q{i}", "options": ["A", "B", "C", "D"],
            "correct_index": 0, "explanation": "because", "difficulty": "Medium",
        }
        for i in range(n)
    ]


def _seen_doc(user_id, topic, seen_ids):
    return {"user_id": user_id, "topic": topic, "question_ids": list(seen_ids)}


@pytest.mark.parametrize("seed", [0, 1, 42])
@pytest.mark.parametrize("topic,count,seen_n", [
    ("aptitude", 8, 0),
    ("reasoning", 6, 3),
    ("verbal", 25, 10),  # TCS-shaped count, but via Capgemini/everyone's GENERIC path
])
def test_capgemini_path_sample_mixed_static_part_byte_identical_to_baseline(
    seed, topic, count, seen_n, baseline_mcq_static_bank, live_mcq_static_bank,
):
    bank_docs = _bank_docs(topic, 40)
    seen_ids = [f"{topic}-{i}" for i in range(seen_n)]
    user_id = "u-regress"

    baseline_mcq_static_bank.init(_FakeDb([dict(d) for d in bank_docs], [_seen_doc(user_id, topic, seen_ids)]))
    random.seed(seed)
    before_items, before_live_n = asyncio.run(
        baseline_mcq_static_bank.sample_mixed_static_part(user_id, topic, count)
    )

    live_mcq_static_bank.init(_FakeDb([dict(d) for d in bank_docs], [_seen_doc(user_id, topic, seen_ids)]))
    random.seed(seed)
    after_items, after_live_n = asyncio.run(
        live_mcq_static_bank.sample_mixed_static_part(user_id, topic, count)
    )

    assert [it["id"] for it in before_items] == [it["id"] for it in after_items]
    assert before_live_n == after_live_n


@pytest.mark.parametrize("seed", [0, 7, 2026])
@pytest.mark.parametrize("topic,bank_n,count,seen_n", [
    ("oops", 10, 6, 0),   # Capgemini R2 Technical's real shape -- fresh
    ("dbms", 5, 8, 2),    # returning candidate + shortfall -- exercises reuse
])
def test_capgemini_path_sample_static_with_reuse_byte_identical_to_baseline(
    seed, topic, bank_n, count, seen_n, baseline_mcq_static_bank, live_mcq_static_bank,
):
    bank_docs = _bank_docs(topic, bank_n)
    seen_ids = [f"{topic}-{i}" for i in range(seen_n)]
    user_id = "u-regress"

    baseline_mcq_static_bank.init(_FakeDb([dict(d) for d in bank_docs], [_seen_doc(user_id, topic, seen_ids)]))
    random.seed(seed)
    b_items, b_reused, b_unfilled = asyncio.run(
        baseline_mcq_static_bank.sample_static_with_reuse(user_id, topic, count)
    )

    live_mcq_static_bank.init(_FakeDb([dict(d) for d in bank_docs], [_seen_doc(user_id, topic, seen_ids)]))
    random.seed(seed)
    a_items, a_reused, a_unfilled = asyncio.run(
        live_mcq_static_bank.sample_static_with_reuse(user_id, topic, count)
    )

    assert [it["id"] for it in b_items] == [it["id"] for it in a_items]
    assert (b_reused, b_unfilled) == (a_reused, a_unfilled)


def test_new_function_is_additive_not_a_modification(baseline_mcq_static_bank, live_mcq_static_bank):
    assert not hasattr(baseline_mcq_static_bank, "sample_static_difficulty_weighted_with_reuse"), (
        "sample_static_difficulty_weighted_with_reuse already existed at the baseline commit -- "
        "this is supposed to be a brand-new function; re-audit what actually changed."
    )
    assert hasattr(live_mcq_static_bank, "sample_static_difficulty_weighted_with_reuse")


def test_weighted_draw_never_wired_into_the_generic_server_dispatch():
    """Structural guard: the new TCS-only function must never be reachable
    from server.py's generic company dispatch (which is what every company
    other than TCS -- Capgemini included -- actually goes through)."""
    server_src = (BACKEND_DIR / "server.py").read_text(encoding="utf-8")
    assert "sample_static_difficulty_weighted_with_reuse" not in server_src
    assert "TCS_FOUNDATION_DIFFICULTY_MIX" not in server_src
    assert "TCS_ADVANCED_DIFFICULTY_MIX" not in server_src


# ---- 3. _bucket_targets: largest-remainder rounding ------------------------

@pytest.mark.parametrize("count,mix,expected", [
    (25, tcs.TCS_FOUNDATION_DIFFICULTY_MIX, {"Easy": 10, "Medium": 11, "Hard": 4}),
    (20, tcs.TCS_FOUNDATION_DIFFICULTY_MIX, {"Easy": 8, "Medium": 9, "Hard": 3}),
    (10, tcs.TCS_ADVANCED_DIFFICULTY_MIX, {"Easy": 2, "Medium": 4, "Hard": 4}),
    (5, tcs.TCS_ADVANCED_DIFFICULTY_MIX, {"Easy": 1, "Medium": 2, "Hard": 2}),
    (0, tcs.TCS_FOUNDATION_DIFFICULTY_MIX, {"Easy": 0, "Medium": 0, "Hard": 0}),
])
def test_bucket_targets_rounds_to_exactly_count(count, mix, expected):
    targets = mcq_static_bank._bucket_targets(count, mix)
    assert targets == expected
    assert sum(targets.values()) == count


# ---- 4. sample_static_difficulty_weighted_with_reuse: core behavior -------

def test_weighted_draw_no_duplicates_within_one_call():
    db = _fresh_db()
    _seed(db, "aptitude", 30, "Easy")
    _seed(db, "aptitude", 30, "Medium")
    _seed(db, "aptitude", 30, "Hard")
    items, reused, unfilled, metadata = asyncio.run(
        mcq_static_bank.sample_static_difficulty_weighted_with_reuse(
            "u1", "aptitude", 20, tcs.TCS_FOUNDATION_DIFFICULTY_MIX, rng=random.Random(1),
        )
    )
    assert unfilled == 0
    assert len(items) == 20
    assert len({it["id"] for it in items}) == 20


def test_weighted_draw_hits_exact_bucket_targets_when_bank_has_plenty():
    db = _fresh_db()
    _seed(db, "aptitude", 50, "Easy")
    _seed(db, "aptitude", 50, "Medium")
    _seed(db, "aptitude", 50, "Hard")
    items, reused, unfilled, metadata = asyncio.run(
        mcq_static_bank.sample_static_difficulty_weighted_with_reuse(
            "u1", "aptitude", 20, tcs.TCS_FOUNDATION_DIFFICULTY_MIX, rng=random.Random(2),
        )
    )
    assert unfilled == 0
    counts = {"Easy": 0, "Medium": 0, "Hard": 0}
    for it in items:
        counts[it["difficulty"]] += 1
    assert counts == {"Easy": 8, "Medium": 9, "Hard": 3}
    assert metadata["fallback"] == []  # plenty of each bucket -- no fallback needed


def test_weighted_draw_recycles_least_recently_seen_within_a_thin_bank():
    db = _fresh_db()
    # Only 3 Medium questions total -- count=3 with the Foundation mix
    # forces every bucket's shortfall to funnel into this one Medium pool,
    # then exhaust it; a second draw must recycle, least-recently-seen first.
    ids = _seed(db, "aptitude", 3, "Medium")

    items1, _reused1, unfilled1, _meta1 = asyncio.run(
        mcq_static_bank.sample_static_difficulty_weighted_with_reuse(
            "u1", "aptitude", 3, tcs.TCS_FOUNDATION_DIFFICULTY_MIX, rng=random.Random(3),
        )
    )
    assert unfilled1 == 0
    assert {it["id"] for it in items1} == set(ids)

    # Mark one id as seen MORE RECENTLY than the others, so it sorts last.
    asyncio.run(mcq_static_bank.mark_seen("u1", "aptitude", [ids[0]]))

    items2, _reused2, unfilled2, _meta2 = asyncio.run(
        mcq_static_bank.sample_static_difficulty_weighted_with_reuse(
            "u1", "aptitude", 3, tcs.TCS_FOUNDATION_DIFFICULTY_MIX, rng=random.Random(4),
        )
    )
    assert unfilled2 == 0
    assert [it["id"] for it in items2][-1] == ids[0]


def test_weighted_draw_falls_back_to_nearest_difficulty_and_records_it():
    db = _fresh_db()
    # Only Medium exists -- Easy and Hard buckets must fall back to Medium.
    _seed(db, "aptitude", 20, "Medium")
    items, _reused, unfilled, metadata = asyncio.run(
        mcq_static_bank.sample_static_difficulty_weighted_with_reuse(
            "u1", "aptitude", 20, tcs.TCS_FOUNDATION_DIFFICULTY_MIX, rng=random.Random(5),
        )
    )
    assert unfilled == 0  # bank (20) exactly covers the requested count (20)
    assert len(items) == 20
    assert len({it["id"] for it in items}) == 20
    assert all(it["difficulty"] == "Medium" for it in items)
    froms = {entry["from"] for entry in metadata["fallback"]}
    assert "Easy" in froms
    assert "Hard" in froms
    for entry in metadata["fallback"]:
        assert entry["to"] == "Medium"


def test_weighted_draw_never_returns_fewer_than_the_flat_draw_would():
    """The ultimate "no regression" guarantee: however lopsided the
    difficulty mix of a bank is, the weighted draw's total served must
    equal min(count, topic_bank_size) -- exactly what the OLD flat draw
    would achieve, via the global safety net."""
    db = _fresh_db()
    _seed(db, "aptitude", 7, "Hard")  # single difficulty, smaller than count
    items, _reused, unfilled, _metadata = asyncio.run(
        mcq_static_bank.sample_static_difficulty_weighted_with_reuse(
            "u1", "aptitude", 20, tcs.TCS_ADVANCED_DIFFICULTY_MIX, rng=random.Random(6),
        )
    )
    assert len(items) == 7
    assert unfilled == 13
    assert len({it["id"] for it in items}) == 7


def test_weighted_draw_distribution_lands_at_target_mix_across_many_fresh_users():
    """"Many draws land near the target mix" -- aggregate the difficulty
    composition across 25 independent fresh users' draws (a generous bank,
    no recycling/fallback in play) and confirm the aggregate proportions
    are within a few points of the Advanced mix's 15/45/40."""
    db = _fresh_db()
    _seed(db, "reasoning", 400, "Easy")
    _seed(db, "reasoning", 400, "Medium")
    _seed(db, "reasoning", 400, "Hard")

    totals = {"Easy": 0, "Medium": 0, "Hard": 0}
    n_users = 25
    for i in range(n_users):
        items, _reused, unfilled, metadata = asyncio.run(
            mcq_static_bank.sample_static_difficulty_weighted_with_reuse(
                f"user-{i}", "reasoning", 20, tcs.TCS_ADVANCED_DIFFICULTY_MIX, rng=random.Random(1000 + i),
            )
        )
        assert unfilled == 0
        assert metadata["fallback"] == []
        for it in items:
            totals[it["difficulty"]] += 1

    grand_total = n_users * 20
    fractions = {d: totals[d] / grand_total for d in totals}
    assert abs(fractions["Easy"] - 0.15) < 0.03
    assert abs(fractions["Medium"] - 0.45) < 0.03
    assert abs(fractions["Hard"] - 0.40) < 0.03


def test_weighted_draw_unseen_pool_is_actually_shuffled_not_insertion_order():
    """The real fix for the "every fresh user gets the identical first N
    questions" bug: two DIFFERENT seeded rngs drawing from the same ample,
    single-difficulty bank must (with overwhelming probability) choose a
    different first item -- unlike sample_static's bare cursor order,
    which is always the same regardless of who's asking."""
    db = _fresh_db()
    _seed(db, "verbal", 200, "Medium")
    items_a, *_ = asyncio.run(
        mcq_static_bank.sample_static_difficulty_weighted_with_reuse(
            "u1", "verbal", 20, {"Easy": 0, "Medium": 1.0, "Hard": 0}, rng=random.Random(11),
        )
    )
    items_b, *_ = asyncio.run(
        mcq_static_bank.sample_static_difficulty_weighted_with_reuse(
            "u2", "verbal", 20, {"Easy": 0, "Medium": 1.0, "Hard": 0}, rng=random.Random(99),
        )
    )
    assert [it["id"] for it in items_a] != [it["id"] for it in items_b]


# ---- 5. draw_tcs_foundation_and_advanced actually uses the weighted draw ---

def _tcs_sections():
    cfg = tcs.get_config()
    return [{**s, "questions": []} for s in cfg["sections"]]


def test_foundation_and_advanced_hit_their_target_bucket_mix():
    db = _fresh_db()
    for topic in ("aptitude", "verbal", "reasoning"):
        _seed(db, topic, 200, "Easy")
        _seed(db, topic, 200, "Medium")
        _seed(db, topic, 200, "Hard")

    sections = _tcs_sections()
    by_key = {s["key"]: s for s in sections}
    by_key["advanced"]["count"] = 0  # isolate Foundation's own mix first

    result = asyncio.run(tcs.draw_tcs_foundation_and_advanced("att-mix", "u1", sections))
    for key, expected_count in (("numerical", 20), ("verbal", 25), ("reasoning", 20)):
        items = result[key]
        assert len(items) == expected_count
        counts = {"Easy": 0, "Medium": 0, "Hard": 0}
        for it in items:
            counts[it["difficulty"]] += 1
        targets = mcq_static_bank._bucket_targets(expected_count, tcs.TCS_FOUNDATION_DIFFICULTY_MIX)
        assert counts == targets, f"{key}: expected {targets}, got {counts}"


def test_advanced_sub_topics_hit_the_advanced_mix():
    db = _fresh_db()
    for topic in ("aptitude", "verbal", "reasoning"):
        _seed(db, topic, 200, "Easy")
        _seed(db, topic, 200, "Medium")
        _seed(db, topic, 200, "Hard")

    sections = _tcs_sections()
    by_key = {s["key"]: s for s in sections}
    by_key["numerical"]["count"] = 0
    by_key["verbal"]["count"] = 0
    by_key["reasoning"]["count"] = 0

    result = asyncio.run(tcs.draw_tcs_foundation_and_advanced("att-mix-adv", "u1", sections))
    advanced_items = result["advanced"]
    assert len(advanced_items) == 15  # 10 quant + 5 reasoning
    # No _borrowed_from_topic tags -- both sub-topics had plenty, no sibling-borrow needed.
    assert not any(q.get("_borrowed_from_topic") for q in advanced_items)
    assert len({q["id"] for q in advanced_items}) == 15


def test_raw_draw_one_topic_primitive_is_unchanged():
    """The non-weighted _draw_one_topic primitive -- what every existing
    direct-call test in test_tcs_zero_ai.py exercises -- keeps its exact
    old 2-tuple signature and flat (non-difficulty-aware) behavior; it is
    simply no longer called from draw_tcs_foundation_and_advanced."""
    import inspect
    sig = inspect.signature(tcs._draw_one_topic)
    assert [p.name for p in sig.parameters.values()] == ["attempt_id", "user_id", "topic", "count"]

    db = _fresh_db()
    ids = _seed(db, "aptitude", 5, "Medium")
    items, unfilled = asyncio.run(tcs._draw_one_topic("att-1", "u1", "aptitude", 5))
    assert unfilled == 0
    assert {q["id"] for q in items} == set(ids)
