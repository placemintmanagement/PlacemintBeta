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
        "svg_diagram": d.get("svg_diagram"),
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
