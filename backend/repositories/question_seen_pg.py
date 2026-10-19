"""Postgres access for `question_seen` -- replaces the five Mongo
`*_bank_seen` collections (ai_assisted_bank_seen, capgemini_bank_seen,
debugging_bank_seen, mcq_static_bank_seen, problem_bank_seen), each of
which follows the identical `get_seen_ids(user_id[, scope])`/
`mark_seen(user_id[, scope], question_ids)` shape (confirmed by reading
all five real call sites: backend/banks/mcq_static_bank.py:79-98,
backend/banks/ai_assisted_bank.py:1119-1133, backend/banks/debugging_bank.py
(~578-585), backend/banks/problem_bank.py (~3049-3071), and
backend/departments/.../capgemini/capgemini_recruitment_process.py:
177-191) -- only the key shape differs: mcq_static/problem_bank key on
(user_id, topic), capgemini keys on (user_id, section), ai_assisted/
debugging key on user_id alone. schema.sql's `question_seen` table unifies
all five under one composite key `(user_id, bank, scope)` -- `bank` names
which of the five pools (`ai_assisted` | `capgemini` | `debugging` |
`mcq_static` | `problem_bank`), `scope` is the topic/section for the two
that have one, or `''` for the two that don't (ai_assisted, debugging).

mcq_static_bank.mark_seen additionally records a per-question `seen_at`
timestamp (used by sample_static_with_reuse's least-recently-seen
fallback) -- the other four banks don't read that back today, but
schema.sql gives every (user_id, bank, scope) row the same `seen_at` jsonb
column regardless of bank, so mark_seen always updates it; banks that
never read it simply never notice.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Set

from psycopg.types.json import Jsonb

from db_postgres import fetch_one


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_seen_ids(user_id: str, bank: str, scope: str = "") -> Set[str]:
    """Mirrors every bank's own `get_seen_ids`: `find_one({"user_id": ...
    [, "topic"/"section": scope]})`, returning `set(doc.get("question_ids",
    []))` or empty set if no row exists yet."""
    row = await fetch_one(
        "SELECT question_ids FROM question_seen WHERE user_id = %s AND bank = %s AND scope = %s",
        (user_id, bank, scope),
    )
    return set(row["question_ids"]) if row else set()


async def mark_seen(user_id: str, bank: str, scope: str, question_ids: List[str]) -> None:
    """Mirrors every bank's own `mark_seen`: an upserting `$addToSet` +
    `updated_at` (and, for mcq_static, a per-question `seen_at` set) in one
    statement -- `array(select distinct unnest(question_ids || %s))` is the
    atomic equivalent of `$addToSet: {"$each": question_ids}`, and the
    jsonb `seen_at` merge (`seen_at || %s::jsonb`) is the equivalent of
    mcq_static_bank.mark_seen's per-id `seen_at.{qid}` dotted-field `$set`.
    A no-op (matching every real call site's own `if not question_ids:
    return` guard) when `question_ids` is empty."""
    if not question_ids:
        return
    now = _now_iso()
    seen_at_patch = {qid: now for qid in question_ids}
    await fetch_one(
        "INSERT INTO question_seen (user_id, bank, scope, question_ids, seen_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (user_id, bank, scope) DO UPDATE SET "
        "question_ids = array(SELECT DISTINCT unnest(question_seen.question_ids || EXCLUDED.question_ids)), "
        "seen_at = question_seen.seen_at || EXCLUDED.seen_at, "
        "updated_at = EXCLUDED.updated_at "
        "RETURNING user_id",
        (user_id, bank, scope, question_ids, Jsonb(seen_at_patch), now),
    )
