"""Postgres access for `ai_assisted_sessions` -- mirrors the
`db.ai_assisted_sessions` call sites in backend/server.py: the session-start
insert (~6120-6158, dev_ai_assisted_start -- the live-wiring start route
follows the identical doc shape), the attempt+section_key scored lookup
(~6091-6105), and the many ownership-scoped `find_one({"session_id": ...,
"user_id": ...})` / `update_one({"session_id": ...}, {"$set": update})`
pairs through the conversation-turn flow (~6163-6590).

Every session doc the Mongo code builds is one flat dict (session_id,
user_id, problem_id, problem, current_stage, transcript, stage_attempts,
consent_given, self_review_result, bug_explanation_text/score,
revealed_code, final_outcome, status, created_at, completed_at -- see
dev_ai_assisted_start's `session = {...}` literal). schema.sql promotes
only the fields other code filters/joins on (session_id, attempt_id,
user_id, company_name, section_key, problem_id, status, current_stage,
consent_given, created_at, completed_at) to real columns; everything else
(problem, transcript, stage_attempts, final_outcome, self_review_result,
bug_explanation_text, bug_explanation_score, revealed_code) stays in the
jsonb `data` column. insert_session/update_session below accept the SAME
flat-dict shape the Mongo code already builds and split it automatically,
so a caller doesn't have to know which fields are promoted."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from psycopg.types.json import Jsonb

from db_postgres import fetch_all, fetch_one

_TOP_LEVEL = (
    "session_id", "user_id", "attempt_id", "company_name", "section_key",
    "problem_id", "status", "current_stage", "consent_given", "created_at",
    "completed_at",
)
_COLUMNS = (
    "session_id, attempt_id, user_id, company_name, section_key, problem_id, "
    "status, current_stage, consent_given, created_at, completed_at, data"
)


def _split(doc: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    cols = {k: doc[k] for k in _TOP_LEVEL if k in doc}
    data = {k: v for k, v in doc.items() if k not in _TOP_LEVEL}
    return cols, data


async def insert_session(session: Dict[str, Any]) -> dict:
    """Mirrors `db.ai_assisted_sessions.insert_one(session)` (server.py
    ~6156) -- `session` is the same flat dict shape the real call site
    builds; split automatically into promoted columns + jsonb `data`."""
    cols, data = _split(session)
    col_names = list(cols.keys()) + ["data"]
    placeholders = ", ".join(["%s"] * len(col_names))
    params = list(cols.values()) + [Jsonb(data)]
    row = await fetch_one(
        f"INSERT INTO ai_assisted_sessions ({', '.join(col_names)}) VALUES ({placeholders}) "
        f"RETURNING {_COLUMNS}",
        params,
    )
    assert row is not None
    return row


async def get_session(session_id: str, user_id: Optional[str] = None) -> Optional[dict]:
    """Mirrors the many `db.ai_assisted_sessions.find_one({"session_id":
    ..., "user_id": ...}, {"_id": 0})` reads (~6163, 6178, 6298, 6336,
    6402). `user_id` is optional for the rare internal unscoped lookup."""
    if user_id is not None:
        return await fetch_one(
            f"SELECT {_COLUMNS} FROM ai_assisted_sessions WHERE session_id = %s AND user_id = %s",
            (session_id, user_id),
        )
    return await fetch_one(f"SELECT {_COLUMNS} FROM ai_assisted_sessions WHERE session_id = %s", (session_id,))


async def get_session_by_attempt_section(attempt_id: str, section_key: str, user_id: str) -> Optional[dict]:
    """Mirrors server.py:6091-6093's scoring lookup: `find_one({
    "attempt_id": ..., "section_key": ..., "user_id": ...}, {"_id": 0})`."""
    return await fetch_one(
        f"SELECT {_COLUMNS} FROM ai_assisted_sessions "
        "WHERE attempt_id = %s AND section_key = %s AND user_id = %s",
        (attempt_id, section_key, user_id),
    )


async def update_session(session_id: str, changes: Dict[str, Any]) -> Optional[dict]:
    """Mirrors the repeated `db.ai_assisted_sessions.update_one(
    {"session_id": session_id}, {"$set": update})` calls (~6102, 6258,
    6324, 6371, 6511, 6545, 6590) -- `changes` is the same flat `update`
    dict those call sites build; promoted-column keys become real `SET`
    assignments, everything else is merged into the jsonb `data` column
    via `||` (so an update that only touches e.g. `transcript` doesn't
    clobber `stage_attempts` sitting alongside it in `data`)."""
    if not changes:
        return await get_session(session_id)
    cols, data_patch = _split(changes)
    set_parts: List[str] = []
    params: List[Any] = []
    for col, value in cols.items():
        set_parts.append(f"{col} = %s")
        params.append(value)
    if data_patch:
        set_parts.append("data = data || %s::jsonb")
        params.append(Jsonb(data_patch))
    params.append(session_id)
    return await fetch_one(
        f"UPDATE ai_assisted_sessions SET {', '.join(set_parts)} WHERE session_id = %s "
        f"RETURNING {_COLUMNS}",
        params,
    )


async def list_sessions_for_user(user_id: str) -> List[dict]:
    """No direct Mongo call site lists all of a user's ai_assisted_sessions
    today, but every other *_pg.py session module exposes this primitive
    for symmetry and for whatever future listing UI needs it."""
    return await fetch_all(
        f"SELECT {_COLUMNS} FROM ai_assisted_sessions WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,),
    )
