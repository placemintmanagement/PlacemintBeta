"""Postgres access for `game_sessions` -- mirrors the `_db.game_session`
(singular, in Mongo) call sites in backend/games/gamified_round.py:
create_session's upsert-by-session_id (~108-137), check_answer's
find-then-$set of live_checks/running_score (~140-183), and the various
other `find_one({"session_id": ...})` / `update_one({"session_id": ...},
{"$set": ...})` pairs used by grade_session/grade_grid_challenge_session/
grade_motion_challenge_session, plus get_seen_puzzle_ids's per-user scan of
every past session's puzzleIdsByType (~73-86).

schema.sql promotes the common fields used for filtering/joining to real
columns (session_id, attempt_id, user_id, company, game_type, section_key,
raw_score, running_score, correct, incorrect, total, created_at,
graded_at); everything else the Mongo document carried (live_checks,
gradingByType, puzzleIdsByType, moves, gameTypes, ...) stays in the jsonb
`data` column, same pattern as puzzle_bank/capgemini_round1_bank. A session
row's `data` is returned as-is (merged with nothing) since callers already
expect a flat dict of whatever fields that game type's grading code reads
out of it -- this module doesn't try to guess a fixed schema for `data`,
just like capgemini_round1_bank_pg's "whole document in `data`" helper.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from psycopg.types.json import Jsonb

from db_postgres import fetch_all, fetch_one

_COLUMNS = (
    "session_id, attempt_id, user_id, company, game_type, section_key, "
    "raw_score, running_score, correct, incorrect, total, created_at, "
    "graded_at, data"
)


async def upsert_session(
    session_id: str,
    user_id: str,
    data: dict,
    attempt_id: Optional[str] = None,
    company: Optional[str] = None,
    game_type: Optional[str] = None,
    section_key: Optional[str] = None,
) -> dict:
    """Mirrors create_session's `update_one({"session_id": ...}, {"$set":
    {...}}, upsert=True)` (gamified_round.py:123-137) -- one statement,
    insert-or-replace by session_id (the table's primary key), same
    "create if missing, overwrite if present" semantics as the Mongo
    upsert."""
    row = await fetch_one(
        "INSERT INTO game_sessions (session_id, attempt_id, user_id, company, "
        "game_type, section_key, data) VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (session_id) DO UPDATE SET "
        "attempt_id = EXCLUDED.attempt_id, user_id = EXCLUDED.user_id, "
        "company = EXCLUDED.company, game_type = EXCLUDED.game_type, "
        "section_key = EXCLUDED.section_key, data = EXCLUDED.data "
        f"RETURNING {_COLUMNS}",
        (session_id, attempt_id, user_id, company, game_type, section_key, Jsonb(data)),
    )
    assert row is not None
    return row


async def get_session(session_id: str) -> Optional[dict]:
    """Mirrors `_db.game_session.find_one({"session_id": session_id})`
    (used throughout gamified_round.py -- check_answer, grade_session,
    grade_grid_challenge_session, grade_motion_challenge_session)."""
    return await fetch_one(f"SELECT {_COLUMNS} FROM game_sessions WHERE session_id = %s", (session_id,))


async def update_session_fields(
    session_id: str,
    data: Optional[dict] = None,
    **score_fields: Any,
) -> Optional[dict]:
    """Mirrors the repeated `update_one({"session_id": ...}, {"$set": {...}})`
    calls (e.g. check_answer's `{"live_checks": ..., "running_score": ...}`,
    grade_session's score/correct/incorrect/total/graded_at write). `data`
    REPLACES the jsonb column wholesale (callers already read the current
    `data`, mutate the Python dict, and pass the whole thing back -- see
    check_answer's `live_checks = session.get("live_checks") or {}; ...;
    live_checks[puzzle_id] = ...` dance), matching the Mongo `$set`'s own
    whole-field replacement semantics; `score_fields` sets the promoted
    scalar columns (raw_score, running_score, correct, incorrect, total,
    graded_at)."""
    set_parts: List[str] = []
    params: List[Any] = []
    if data is not None:
        set_parts.append("data = %s")
        params.append(Jsonb(data))
    for col, value in score_fields.items():
        set_parts.append(f"{col} = %s")
        params.append(value)
    if not set_parts:
        return await get_session(session_id)
    params.append(session_id)
    return await fetch_one(
        f"UPDATE game_sessions SET {', '.join(set_parts)} WHERE session_id = %s "
        f"RETURNING {_COLUMNS}",
        params,
    )


async def list_sessions_for_user(user_id: str) -> List[dict]:
    """Mirrors get_seen_puzzle_ids's `_db.game_session.find({"user_id":
    user_id}, {"puzzleIdsByType": 1, "_id": 0})` scan (gamified_round.py:
    84-85) -- returns every past session for this user so the caller can
    union whichever `data` sub-key it wants (puzzleIdsByType today);
    unlike the Mongo projection this returns full rows, not just `data`,
    since Postgres has no equivalent cheap partial-jsonb projection worth
    the extra SQL surface for what's a small per-user row count."""
    return await fetch_all(f"SELECT {_COLUMNS} FROM game_sessions WHERE user_id = %s", (user_id,))
