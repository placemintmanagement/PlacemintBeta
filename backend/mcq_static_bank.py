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

# The 8 canonical topics (matches ai_service.TOPIC_INSTRUCTIONS /
# mcq_pool.TOPIC_KEY_MAP's topic_key values exactly).
CANONICAL_TOPICS = {"aptitude", "verbal", "reasoning", "oops", "dbms", "os", "cn", "architecture"}

# Company section keys (mcq_pool.POOLED_SECTION_KEYS) that map cleanly to one
# canonical topic, and therefore get the 90/10 static/live split on their
# plain "mcq" sections. Anything NOT listed here (cs-fundamentals, technical,
# puzzles, advanced) stays live-only — those keys mean different things to
# different companies and don't have a clean 1:1 topic match.
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
    await _db.mcq_static_bank_seen.update_one(
        {"user_id": user_id, "topic": topic},
        {"$addToSet": {"question_ids": {"$each": question_ids}}, "$set": {"updated_at": _now_iso()}},
        upsert=True,
    )


async def sample_static(user_id: str, topic: str, count: int) -> List[dict]:
    """Return up to `count` static-bank questions for `topic`, excluding
    ones this user has already been served, and mark them seen immediately.
    Returns FEWER than `count` (down to zero) if the bank is exhausted for
    this user — callers are expected to backfill the shortfall from the
    live pool, never treat this as a hard failure."""
    if _db is None or count <= 0:
        return []
    seen = await get_seen_ids(user_id, topic)
    cursor = _db.mcq_static_bank.find({"topic": topic, "question_id": {"$nin": list(seen)}})
    docs = await cursor.to_list(length=count)
    if not docs:
        return []
    items = [{
        "id": d["question_id"],
        "prompt": d["prompt"],
        "options": d["options"],
        "correct_index": d["correct_index"],
        "explanation": d.get("explanation", ""),
        "difficulty": d.get("difficulty", "Medium"),
        "chart": d.get("chart"),
    } for d in docs]
    await mark_seen(user_id, topic, [it["id"] for it in items])
    return items


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
