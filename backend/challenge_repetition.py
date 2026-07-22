"""Per-candidate, category-level non-repetition tracking for procedurally
generated challenge sections (Capgemini's capgemini_challenges, Cognizant's
cognizant_games).

This only works because those sections are fully procedural, not LLM-based:
each generator can always produce a fresh variant on request, so instead of
just hoping a model doesn't repeat itself (the "Do NOT repeat questions"
prompt instruction used elsewhere in this app), we can guarantee it — hash
the generated content, check it against what this candidate has already
been served for that category, and regenerate on a collision.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Set

_db = None


def init(db) -> None:
    global _db
    _db = db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_seen_hashes(user_id: str, section_key: str) -> Dict[str, Set[str]]:
    """Return {category: {content_hash, ...}} of everything this candidate
    has already been served for this section, across all their past
    attempts (not just the current one)."""
    if _db is None:
        return {}
    out: Dict[str, Set[str]] = {}
    async for doc in _db.seen_challenges.find({"user_id": user_id, "section_key": section_key}):
        out.setdefault(doc["category"], set()).add(doc["content_hash"])
    return out


async def mark_seen(user_id: str, section_key: str, category: str, content_hash: str) -> None:
    if _db is None:
        return
    await _db.seen_challenges.update_one(
        {"user_id": user_id, "section_key": section_key, "category": category, "content_hash": content_hash},
        {"$setOnInsert": {"created_at": _now_iso()}},
        upsert=True,
    )
