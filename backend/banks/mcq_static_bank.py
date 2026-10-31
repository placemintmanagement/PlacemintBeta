"""Static, once-verified MCQ bank — a 90/10 split (static/live, changed
2026-07-21, permanent) with the live mcq_pool worker, for the 8 canonical
topics (fundamentals/aptitude/verbal/reasoning: aptitude, verbal, reasoning,
oops, dbms, os, cn, architecture).

Same reliability model as problem_bank.py's DSA bank: every question is
verified ONCE (same Stage B/C ground-truth pipeline mcq_pool.py already
uses — see scripts/mcq_bank_add.py) and then served many times, instead of
mcq_pool's model of re-generating and re-verifying continuously in the
background. At 90/10 this cuts live generation traffic far more than the
original 50/50 design did for the topics it covers — see split_counts().

Non-repetition is ID-based (not the hash-collision approach
challenge_repetition.py uses) — the bank is a FINITE, stable set, so
"has this candidate already seen question_id X" is the right question,
simpler than hashing regeneratable procedural content.
"""
from __future__ import annotations
import math
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# The 10 canonical topics (matches ai_service.TOPIC_INSTRUCTIONS /
# mcq_pool.TOPIC_KEY_MAP's topic_key values exactly, plus "puzzles" and
# "pseudocode" which are static-bank-only — no live mcq_pool worker
# generates puzzles or pseudocode content). "pseudocode" added 2026-09
# (Phase 0 live-generation migration): 130 questions were already seeded
# here but unwired -- server.py's "pseudocode" branch now draws from this
# bank first via sample_mixed_static_part, same 90/10 split as every other
# canonical topic, falling back to mcq_pool.fallback_live_verify's 3-stage
# ground-truth pipeline for the remaining 10% + any shortfall.
#
# "programming_logic"/"dsa"/"swe_fundamentals"/"modern_engineering" added
# 2026-09/10 (Capgemini Round 2 Technical Assessment wiring): all four are
# static-bank-only, same as "puzzles"/"pseudocode" -- no live mcq_pool
# worker or TOPIC_INSTRUCTIONS entry exists for any of them, so a static
# shortfall would fall through to _generate_extra_topics's live-fallback
# path with only a generic topic hint (see ai_service.topic_mcq_prompt's
# graceful default) rather than a topic-specific one. Registering them
# here is what lets _generate_extra_topics (already used for Capgemini's
# OOPS/DBMS/OS/CN) route to these banks automatically -- see server.py's
# new "capgemini_round2_technical" branch.
CANONICAL_TOPICS = {
    "aptitude", "verbal", "reasoning", "oops", "dbms", "os", "cn", "architecture", "puzzles", "pseudocode",
    "programming_logic", "dsa", "swe_fundamentals", "modern_engineering",
}

# Company section keys (mcq_pool.POOLED_SECTION_KEYS) that map cleanly to one
# canonical topic, and therefore get the 90/10 static/live split on their
# plain "mcq" sections. Anything NOT listed here (cs-fundamentals, technical,
# advanced) stays live-only — those keys mean different things to
# different companies and don't have a clean 1:1 topic match. "puzzles" is
# routed via extra_topics instead (see companies.py, Infosys) rather than
# this dict, since it's a dedicated per-company section, not a pooled key.
SECTION_KEY_TO_TOPIC = {
    "verbal": "verbal",
    "english": "verbal",
    "reasoning": "reasoning",
    "logical": "reasoning",
    "analytical": "reasoning",
    "numerical": "aptitude",
    "aptitude": "aptitude",
    "quant": "aptitude",
}

_db = None  # set by init(db)


def init(db) -> None:
    global _db
    _db = db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_seen_ids(user_id: str, topic: str) -> set:
    if _db is None:
        return set()
    doc = await _db.mcq_static_bank_seen.find_one({"user_id": user_id, "topic": topic})
    return set(doc.get("question_ids", [])) if doc else set()


async def mark_seen(user_id: str, topic: str, question_ids: List[str]) -> None:
    if _db is None or not question_ids:
        return
    now = _now_iso()
    # seen_at records when each question was last served. Only used to pick the
    # least-recently-seen questions when a topic's unseen set runs out (see
    # sample_static_with_reuse). Dotted ids can't be stored as field names.
    seen_at = {f"seen_at.{qid}": now for qid in question_ids if "." not in qid and "$" not in qid}
    await _db.mcq_static_bank_seen.update_one(
        {"user_id": user_id, "topic": topic},
        {"$addToSet": {"question_ids": {"$each": question_ids}}, "$set": {"updated_at": now, **seen_at}},
        upsert=True,
    )


async def sample_static(user_id: str, topic: str, count: int, rng: Optional[random.Random] = None) -> List[dict]:
    """Return up to `count` static-bank questions for `topic`, excluding
    ones this user has already been served, and mark them seen immediately.
    Returns FEWER than `count` (down to zero) if the bank is exhausted for
    this user — callers are expected to backfill the shortfall from the
    live pool, never treat this as a hard failure.

    The unseen pool is drawn RANDOMLY (2026-10 fix for every non-TCS
    caller, e.g. Capgemini -- before this, the query had no sort/shuffle
    at all, so every fresh user got the identical first `count` questions
    in Mongo's own cursor/insertion order; confirmed by direct experiment
    against the live bank). Only `question_id`s are fetched for the
    shuffle -- never the full documents for the whole topic -- then
    exactly the picked `count` full documents are fetched by id, and
    re-ordered to match the shuffled pick (an `$in` query doesn't promise
    to preserve that order).

    `rng`: optional seeded random.Random for a reproducible draw (e.g.
    keyed on an attempt_id, same convention as sample_static_with_reuse's
    own `rng`). Omitted, a FRESH random.Random() is used -- genuinely
    random every call, deliberately never the shared global `random`
    module, so no caller's state can leak in or out."""
    if _db is None or count <= 0:
        return []
    seen = await get_seen_ids(user_id, topic)
    id_docs = await _db.mcq_static_bank.find(
        {"topic": topic, "question_id": {"$nin": list(seen)}},
        {"question_id": 1, "_id": 0},
    ).to_list(length=None)
    candidate_ids = [d["question_id"] for d in id_docs]
    if not candidate_ids:
        return []
    (rng or random.Random()).shuffle(candidate_ids)
    picked_ids = candidate_ids[:count]
    docs_by_id = {
        d["question_id"]: d
        for d in await _db.mcq_static_bank.find({"question_id": {"$in": picked_ids}}).to_list(length=len(picked_ids))
    }
    items = [{
        "id": d["question_id"],
        "prompt": d["prompt"],
        "options": d["options"],
        "correct_index": d["correct_index"],
        "explanation": d.get("explanation", ""),
        "difficulty": d.get("difficulty", "Medium"),
        "chart": d.get("chart"),
        "svg_diagram": d.get("svg_diagram"),
    } for qid in picked_ids if (d := docs_by_id.get(qid)) is not None]
    await mark_seen(user_id, topic, [it["id"] for it in items])
    return items


def _item_from_doc(d: dict) -> dict:
    return {
        "id": d["question_id"],
        "prompt": d["prompt"],
        "options": d["options"],
        "correct_index": d["correct_index"],
        "explanation": d.get("explanation", ""),
        "difficulty": d.get("difficulty", "Medium"),
        "chart": d.get("chart"),
        "svg_diagram": d.get("svg_diagram"),
    }


async def sample_static_with_reuse(
    user_id: str, topic: str, count: int, rng: Optional[random.Random] = None,
) -> Tuple[List[dict], int, int]:
    """Static-only draw with no LLM call. Serves up to `count` unseen questions
    for `topic` (sample_static), then fills any shortfall with this user's
    least-recently-seen static questions. Returns (items, reused, unfilled):
    `reused` counts questions repeated from earlier draws, `unfilled` counts
    slots the bank could not fill at all (the bank is smaller than `count`).

    `rng`: optional seeded random.Random, used for BOTH this function's own
    unseen-first draw (passed straight through to sample_static -- 2026-10:
    now genuinely random there too, not Mongo cursor order, see its own
    docstring) AND to break ties among reuse candidates sharing the same
    seen_at (most commonly: several questions with no recorded seen_at at
    all, sorting as equally "oldest") -- shuffled BEFORE the stable least-
    recently-seen sort, so the sort key still dominates and only genuine
    ties get randomized. Omitting `rng` (the default, 2026-10 change) now
    means a FRESH, unseeded random.Random() is used for each of those two
    shuffles -- every caller (Capgemini and everyone else) gets a
    genuinely random draw; it is simply no longer reproducible across
    calls without passing an explicit rng. (The one caller that always
    passes a seeded rng -- TCS's own draw -- is unaffected in spirit: it
    was already deterministic and stays deterministic.)"""
    if _db is None or count <= 0:
        return [], 0, max(count, 0)
    items = await sample_static(user_id, topic, count, rng=rng)
    short = count - len(items)
    if short <= 0:
        return items, 0, 0
    served = {it["id"] for it in items}
    doc = await _db.mcq_static_bank_seen.find_one({"user_id": user_id, "topic": topic}) or {}
    seen_at = doc.get("seen_at") or {}
    candidates = await _db.mcq_static_bank.find(
        {"topic": topic, "question_id": {"$nin": list(served)}}
    ).to_list(length=None)
    (rng or random.Random()).shuffle(candidates)
    # Oldest last-served first. A question with no recorded time was served
    # before seen_at existed, so it sorts as oldest. Python's sort is
    # stable, so the shuffle above only affects the order WITHIN ties.
    candidates.sort(key=lambda d: seen_at.get(d["question_id"], ""))
    reused_docs = candidates[:short]
    reused = [_item_from_doc(d) for d in reused_docs]
    await mark_seen(user_id, topic, [it["id"] for it in reused])
    return items + reused, len(reused), short - len(reused)


_DIFFICULTIES = ("Easy", "Medium", "Hard")
# Single-hop fallback target for a bucket that can't fill its own target
# even with full reuse. Medium falls back to Hard (arbitrary but fixed,
# for determinism); Easy/Hard both fall back to Medium, their one shared
# neighbor.
_NEAREST_DIFFICULTY = {"Easy": "Medium", "Hard": "Medium", "Medium": "Hard"}


def _bucket_targets(count: int, difficulty_mix: Dict[str, float]) -> Dict[str, int]:
    """Largest-remainder rounding of `count` into Easy/Medium/Hard integer
    targets from `difficulty_mix`'s fractional weights -- always sums to
    exactly `count` (e.g. count=25, mix 0.40/0.45/0.15 -> Easy 10, Medium
    11, Hard 4). Ties in the fractional remainder are broken by
    `_DIFFICULTIES`'s own order (Easy, then Medium, then Hard), so the
    same (count, mix) always rounds the same way."""
    if count <= 0:
        return {d: 0 for d in _DIFFICULTIES}
    raw = {d: count * difficulty_mix.get(d, 0.0) for d in _DIFFICULTIES}
    targets = {d: int(raw[d]) for d in _DIFFICULTIES}
    remainder = count - sum(targets.values())
    order = sorted(_DIFFICULTIES, key=lambda d: raw[d] - targets[d], reverse=True)
    for d in order[:remainder]:
        targets[d] += 1
    return targets


async def _draw_bucket(
    user_id: str, topic: str, difficulty: Optional[str], want: int, excluded: set,
    rng: Optional[random.Random],
) -> Tuple[List[dict], int]:
    """Up to `want` distinct (topic[, difficulty]) docs not already in
    `excluded`. `difficulty=None` means "any difficulty" -- used only by
    this module's own topic-wide safety net below, never by a bucket
    itself. Unseen docs are drawn RANDOMLY (the actual fix for
    sample_static's cursor/insertion-order bug -- every fresh user
    otherwise gets the identical first N questions, confirmed by direct
    experiment); any shortfall is then filled by this user's least-
    recently-seen docs of the same query, unchanged from
    sample_static_with_reuse's own recycling logic. Does not call
    mark_seen -- the caller marks everything actually served, once, at
    the end, so a document that's fetched here but then discarded (e.g.
    superseded by a later, more successful bucket) is never wrongly
    marked seen."""
    if want <= 0 or _db is None:
        return [], 0
    base_query: Dict[str, Any] = {"topic": topic}
    if difficulty is not None:
        base_query["difficulty"] = difficulty
    seen = await get_seen_ids(user_id, topic)
    unseen_docs = await _db.mcq_static_bank.find(
        {**base_query, "question_id": {"$nin": list(seen | excluded)}}
    ).to_list(length=None)
    (rng.shuffle if rng is not None else random.shuffle)(unseen_docs)
    picked_docs = unseen_docs[:want]
    items = [_item_from_doc(d) for d in picked_docs]
    short = want - len(items)
    if short <= 0:
        return items, 0
    got_ids = {it["id"] for it in items}
    doc = await _db.mcq_static_bank_seen.find_one({"user_id": user_id, "topic": topic}) or {}
    seen_at = doc.get("seen_at") or {}
    candidates = await _db.mcq_static_bank.find(
        {**base_query, "question_id": {"$nin": list(got_ids | excluded)}}
    ).to_list(length=None)
    if rng is not None:
        rng.shuffle(candidates)
    candidates.sort(key=lambda d: seen_at.get(d["question_id"], ""))
    reuse_docs = candidates[:short]
    reused_items = [_item_from_doc(d) for d in reuse_docs]
    return items + reused_items, len(reused_items)


async def sample_static_difficulty_weighted_with_reuse(
    user_id: str, topic: str, count: int, difficulty_mix: Dict[str, float],
    rng: Optional[random.Random] = None,
) -> Tuple[List[dict], int, int, Dict[str, Any]]:
    """TCS-only opt-in draw (2026-10, "make the TCS draw genuinely random
    and difficulty-aware" pass) -- draws within Easy/Medium/Hard buckets
    per `difficulty_mix` (e.g. {"Easy": 0.40, "Medium": 0.45, "Hard":
    0.15}) instead of a flat pool. Completely new and additive:
    sample_static, sample_static_with_reuse and sample_mixed_static_part
    (every other company's path, Capgemini included) are untouched and
    stay byte-identical to before.

    Within each bucket: unseen docs are drawn randomly, then any shortfall
    is filled by this user's least-recently-seen docs of that SAME
    difficulty (recycling behavior unchanged from sample_static_with_reuse
    -- "keep the existing least-recently-seen recycling for students who
    have seen everything"). If a bucket's own total bank is still too
    small even with full reuse, the remaining shortfall falls back to the
    nearest difficulty bucket (see _NEAREST_DIFFICULTY) and is recorded in
    the returned metadata; if that ALSO can't cover it, a final safety net
    draws from the topic's entire pool regardless of difficulty (the same
    guarantee sample_static_with_reuse already gives) -- so this function
    never returns fewer questions than the flat draw would for the same
    bank size.

    Returns (items, reused, unfilled, metadata). `metadata` = {
      "bucket_targets": {"Easy": n, "Medium": n, "Hard": n},
      "fallback": [{"from": "Hard", "to": "Medium", "count": n}, ...],
    }."""
    if _db is None or count <= 0:
        return [], 0, max(count, 0), {"bucket_targets": {}, "fallback": []}

    targets = _bucket_targets(count, difficulty_mix)
    fallback_log: List[Dict[str, Any]] = []
    all_items: List[dict] = []
    picked_ids: set = set()
    reused_total = 0

    for d in _DIFFICULTIES:
        want = targets[d]
        if want <= 0:
            continue
        items, reused = await _draw_bucket(user_id, topic, d, want, picked_ids, rng)
        all_items.extend(items)
        picked_ids.update(it["id"] for it in items)
        reused_total += reused
        short = want - len(items)
        if short > 0:
            nxt = _NEAREST_DIFFICULTY[d]
            extra, extra_reused = await _draw_bucket(user_id, topic, nxt, short, picked_ids, rng)
            if extra:
                all_items.extend(extra)
                picked_ids.update(it["id"] for it in extra)
                reused_total += extra_reused
                fallback_log.append({"from": d, "to": nxt, "count": len(extra)})

    unfilled_so_far = count - len(all_items)
    if unfilled_so_far > 0:
        extra, extra_reused = await _draw_bucket(user_id, topic, None, unfilled_so_far, picked_ids, rng)
        if extra:
            all_items.extend(extra)
            picked_ids.update(it["id"] for it in extra)
            reused_total += extra_reused
            fallback_log.append({"from": "bucketed", "to": "any", "count": len(extra)})

    unfilled = max(count - len(all_items), 0)
    await mark_seen(user_id, topic, [it["id"] for it in all_items])
    return all_items, reused_total, unfilled, {"bucket_targets": targets, "fallback": fallback_log}


async def topic_bank_size(topic: str) -> int:
    """Total question count for `topic`, seen or unseen, across every
    candidate -- used for feasibility checks (e.g. TCS's static-only draw)
    and the bank-readiness report. No LLM call, no seen-state involved."""
    if _db is None:
        return 0
    return await _db.mcq_static_bank.count_documents({"topic": topic})


def split_counts(count: int) -> Tuple[int, int]:
    """(static_n, live_n) for a requested total. 90/10 split (changed
    2026-07-21, permanent — not a temporary experiment): static gets 90%
    (ceiling), live only backfills the remaining 10% plus any static
    shortfall. static_n's ceiling means a lone-question pull (topic_mcq's
    count=1) always prefers static-if-available."""
    static_n = math.ceil(count * 0.9)
    return static_n, count - static_n


async def sample_mixed_static_part(user_id: str, topic: str, count: int) -> Tuple[List[dict], int]:
    """Convenience wrapper for call sites: returns (static_items, live_n_needed)
    where live_n_needed already accounts for any static shortfall (graceful
    backfill — see split_counts). Caller runs its own existing live-fetch
    logic for live_n_needed and concatenates + shuffles with static_items."""
    static_n, live_n = split_counts(count)
    static_items = await sample_static(user_id, topic, static_n)
    live_n += (static_n - len(static_items))
    return static_items, live_n
