"""Postgres access for `review_deck` -- mirrors the `db.review_deck` call
sites in backend/server.py: the add-card dup-check + insert (~3556-3585),
the listing sorted by added_at (~3589-3599), the attempt (mastery-update)
route (~3606-3627), and the delete route (~3630-3635).

Surprise worth flagging (see phase report): the real Mongo review_deck
document's own id field is `card_id` (an app-minted string, `new_id(
"card")`), but schema.sql's review_deck table has no `card_id` column --
its primary key is an auto-increment `id bigint identity`, with
`card_id` nowhere in the schema at all. Rather than changing the already-
applied schema (out of scope for this phase -- no DDL against the live
project), `card_id` is kept inside the jsonb `data` column and looked up
via `data->>'card_id'` -- functionally correct (no index on it yet, but
review_deck is empty and low-volume) and keeps the externally-visible
card id format the frontend already expects unchanged. The existing
`unique (user_id, source_attempt_id, section_key, question_id)` constraint
(schema.sql) is reused as the real atomic dup-check instead of the Mongo
code's own find-then-insert (not one of the brief's three required fixes,
but the same spirit: a constraint schema.sql already provides, used
properly instead of pre-checked only in application code).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from psycopg.types.json import Jsonb

from db_postgres import fetch_all, fetch_one

_DATA_FIELDS = (
    "card_id", "company_name", "section_name", "prompt", "options",
    "correct_index", "explanation", "difficulty", "attempts", "mastered",
)


def _row_to_card(row: Optional[dict]) -> Optional[dict]:
    """Merges the jsonb `data` column back with the promoted top-level
    columns, restoring the flat Mongo document shape server.py's callers
    already expect (card_id, user_id, source_attempt_id, section_key,
    question_id, added_at, plus every field in `data`)."""
    if row is None:
        return None
    data = row.get("data") or {}
    merged: Dict[str, Any] = dict(data)
    merged["id"] = row["id"]
    merged["user_id"] = row["user_id"]
    merged["source_attempt_id"] = row.get("source_attempt_id")
    merged["section_key"] = row.get("section_key")
    merged["question_id"] = row.get("question_id")
    merged["added_at"] = row.get("added_at")
    return merged


async def add_card(
    user_id: str,
    source_attempt_id: str,
    section_key: str,
    question_id: str,
    card_id: str,
    company_name: Optional[str],
    section_name: Optional[str],
    prompt: str,
    options: list,
    correct_index: Optional[int],
    explanation: str,
    difficulty: Optional[str],
) -> Optional[dict]:
    """Mirrors the add-card loop's find-then-insert (server.py ~3559-3584),
    but as one atomic `INSERT ... ON CONFLICT (user_id, source_attempt_id,
    section_key, question_id) DO NOTHING` -- the existing unique
    constraint is the real dup-guard; zero rows back (None here) means a
    card for this (attempt, section, question) already existed, which
    callers count as `skipped_duplicates` exactly like the Mongo code's own
    `if existing: skipped += 1; continue`."""
    data = {
        "card_id": card_id,
        "company_name": company_name,
        "section_name": section_name,
        "prompt": prompt,
        "options": options,
        "correct_index": correct_index,
        "explanation": explanation,
        "difficulty": difficulty,
        "attempts": [],
        "mastered": False,
    }
    row = await fetch_one(
        "INSERT INTO review_deck (user_id, source_attempt_id, section_key, question_id, data) "
        "VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (user_id, source_attempt_id, section_key, question_id) DO NOTHING "
        "RETURNING id, user_id, source_attempt_id, section_key, question_id, added_at, data",
        (user_id, source_attempt_id, section_key, question_id, Jsonb(data)),
    )
    return _row_to_card(row)


async def list_cards(user_id: str, unmastered_only: bool = False) -> List[dict]:
    """Mirrors GET /deck (server.py ~3589-3599): `find(q, {"_id":
    0}).sort("added_at", -1)`, optionally filtered to `mastered: False`."""
    sql = (
        "SELECT id, user_id, source_attempt_id, section_key, question_id, added_at, data "
        "FROM review_deck WHERE user_id = %s"
    )
    params: list = [user_id]
    if unmastered_only:
        sql += " AND (data->>'mastered')::boolean IS NOT TRUE"
    sql += " ORDER BY added_at DESC"
    rows = await fetch_all(sql, params)
    return [c for r in rows if (c := _row_to_card(r)) is not None]


async def get_card(card_id: str, user_id: str) -> Optional[dict]:
    """Mirrors `db.review_deck.find_one({"card_id": ..., "user_id": ...},
    {"_id": 0})` (server.py ~3608) -- looked up via `data->>'card_id'`
    since no dedicated column exists for it (see this module's docstring)."""
    row = await fetch_one(
        "SELECT id, user_id, source_attempt_id, section_key, question_id, added_at, data "
        "FROM review_deck WHERE user_id = %s AND data->>'card_id' = %s",
        (user_id, card_id),
    )
    return _row_to_card(row)


async def record_attempt(card_id: str, user_id: str, attempts: list, mastered: bool) -> Optional[dict]:
    """Mirrors POST /deck/{card_id}/attempt's mastery update (server.py
    ~3623-3626): `update_one({"card_id": ..., "user_id": ...}, {"$set": {
    "attempts": attempts, "mastered": mastered}})` -- merged into `data`
    via `||` so no other field in `data` is disturbed."""
    row = await fetch_one(
        "UPDATE review_deck SET data = data || %s::jsonb "
        "WHERE user_id = %s AND data->>'card_id' = %s "
        "RETURNING id, user_id, source_attempt_id, section_key, question_id, added_at, data",
        (Jsonb({"attempts": attempts, "mastered": mastered}), user_id, card_id),
    )
    return _row_to_card(row)


async def delete_card(card_id: str, user_id: str) -> bool:
    """Mirrors DELETE /deck/{card_id} (server.py ~3632-3635): `delete_one(
    {"card_id": ..., "user_id": ...})`, returning whether a row was
    actually deleted (`r.deleted_count` truthy)."""
    row = await fetch_one(
        "DELETE FROM review_deck WHERE user_id = %s AND data->>'card_id' = %s RETURNING id",
        (user_id, card_id),
    )
    return row is not None
