"""Postgres access for `interviews` -- mirrors the `db.interviews` call
sites in backend/server.py: the plain-interview create (~3955-3971), the
Capgemini-style (Spark/Dave/Commit/TCS) interview create
(_start_spark_interview, ~4497-4532), the per-user listing (~3977-3984),
the in-progress lookup by (user_id, company_id) (_existing_in_progress_
interview, ~3761-3763), the many ownership-scoped `find_one({
"interview_id": ..., "user_id": ...})` reads, and the optimistic-
concurrency `update_one({"interview_id": ..., "turn_count": expected},
{"$set": changes})` writes the Capgemini interview modes use (_spark_
persist and its Dave/Commit/TCS near-duplicates, ~4446-4455, ~4808-4815,
~5377-5384).

IMPORTANT -- depends on a column schema.sql doesn't have yet: real
`db.interviews` documents carry a `company_id` field queried directly
(not derivable from `company_name`) and, for the Capgemini interview
modes, a long tail of fields (tier, tier_source, candidate_name, mode,
state, turn_count, current_question, project, project_text,
dsa_problem_id, dsa_flags, turns, usage, flag_review, spark_score) with
no promoted column and no catch-all jsonb column to fall back to --
every other user-data table in schema.sql has a `data` jsonb column for
exactly this, `interviews` does not. See
`supabase/003_interviews_missing_columns.sql` (NOT yet run against the
live project -- additive, for the product owner to review and run
themselves per this repo's ground rules) for the proposed
`company_id text` + `data jsonb` columns this module is written against.
Until that migration runs, insert_interview/update_interview's `data`
writes will fail against the live table with "column data does not
exist" -- this module is complete and unit-tested against mocks, but not
live-verified (SUPABASE_DB_URL was absent for this phase regardless, so
no live run happened either way -- see the phase report).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from psycopg.types.json import Jsonb

from db_postgres import fetch_all, fetch_one

_TOP_LEVEL = (
    "interview_id", "attempt_id", "user_id", "company_id", "resume_id",
    "company_name", "status", "current_index", "created_at", "completed_at",
    "questions", "answers",
)
_JSONB_COLUMNS = {"questions", "answers"}
_COLUMNS = (
    "interview_id, attempt_id, user_id, company_id, resume_id, company_name, "
    "status, current_index, created_at, completed_at, questions, answers, data"
)


def _split(doc: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    cols = {k: doc[k] for k in _TOP_LEVEL if k in doc}
    data = {k: v for k, v in doc.items() if k not in _TOP_LEVEL}
    return cols, data


async def insert_interview(interview: Dict[str, Any]) -> dict:
    """Mirrors `db.interviews.insert_one(interview)` -- both the plain-
    interview shape (~3969) and the Capgemini-style shape (~4530, ~4892,
    ~5466) use this; `interview` is the same flat dict those call sites
    build, split automatically into promoted columns + jsonb `data`."""
    cols, data = _split(interview)
    col_names = list(cols.keys()) + ["data"]
    placeholders = ", ".join(["%s"] * len(col_names))
    params = [Jsonb(v) if k in _JSONB_COLUMNS else v for k, v in cols.items()] + [Jsonb(data)]
    row = await fetch_one(
        f"INSERT INTO interviews ({', '.join(col_names)}) VALUES ({placeholders}) "
        f"RETURNING {_COLUMNS}",
        params,
    )
    assert row is not None
    return row


async def get_interview(interview_id: str, user_id: Optional[str] = None) -> Optional[dict]:
    """Mirrors the many ownership-scoped `db.interviews.find_one({
    "interview_id": ..., "user_id": ...}, {"_id": 0})` reads. `user_id`
    optional for the rare internal unscoped re-fetch (e.g. _spark_finalize_
    if_expired's stale-turn re-fetch, server.py ~4487)."""
    if user_id is not None:
        return await fetch_one(
            f"SELECT {_COLUMNS} FROM interviews WHERE interview_id = %s AND user_id = %s",
            (interview_id, user_id),
        )
    return await fetch_one(f"SELECT {_COLUMNS} FROM interviews WHERE interview_id = %s", (interview_id,))


async def get_interview_by_attempt(attempt_id: str, user_id: str) -> Optional[dict]:
    """Mirrors `db.interviews.find_one({"attempt_id": ..., "user_id": ...},
    {"_id": 0})` (server.py ~6788, used when building a final report)."""
    return await fetch_one(
        f"SELECT {_COLUMNS} FROM interviews WHERE attempt_id = %s AND user_id = %s",
        (attempt_id, user_id),
    )


async def get_existing_in_progress(user_id: str, company_id: str) -> Optional[dict]:
    """Mirrors `_existing_in_progress_interview` (server.py ~3761-3763):
    `db.interviews.find_one({"user_id": ..., "company_id": ..., "status":
    "in_progress"}, {"_id": 0})`."""
    return await fetch_one(
        f"SELECT {_COLUMNS} FROM interviews WHERE user_id = %s AND company_id = %s "
        "AND status = 'in_progress'",
        (user_id, company_id),
    )


async def list_interviews_for_user(user_id: str, limit: int = 200) -> List[dict]:
    """Mirrors `db.interviews.find({"user_id": ...}, {"_id": 0}).to_list(
    200)` (server.py ~3979), sorted newest first -- the Mongo code sorts in
    Python after fetching (`sorted(docs, key=lambda d: d.get("created_at")
    or "", reverse=True)`); doing the sort in SQL is equivalent and avoids
    pulling all 200 rows into Python just to re-order them."""
    return await fetch_all(
        f"SELECT {_COLUMNS} FROM interviews WHERE user_id = %s "
        "ORDER BY created_at DESC LIMIT %s",
        (user_id, limit),
    )


async def update_interview(interview_id: str, changes: Dict[str, Any]) -> Optional[dict]:
    """Mirrors plain `db.interviews.update_one({"interview_id": ...},
    {"$set": changes})` calls that have no optimistic-concurrency guard
    (e.g. the regular interview flow's per-answer grade write, ~4114).
    Unconditional -- use update_interview_if_turn_matches for the
    Capgemini-mode optimistic-concurrency writes instead."""
    if not changes:
        return await get_interview(interview_id)
    cols, data_patch = _split(changes)
    set_parts: List[str] = []
    params: List[Any] = []
    for col, value in cols.items():
        set_parts.append(f"{col} = %s")
        params.append(Jsonb(value) if col in _JSONB_COLUMNS else value)
    if data_patch:
        set_parts.append("data = data || %s::jsonb")
        params.append(Jsonb(data_patch))
    params.append(interview_id)
    return await fetch_one(
        f"UPDATE interviews SET {', '.join(set_parts)} WHERE interview_id = %s "
        f"RETURNING {_COLUMNS}",
        params,
    )


async def update_interview_if_turn_matches(
    interview_id: str, expected_turn_count: int, changes: Dict[str, Any]
) -> Optional[dict]:
    """Mirrors the Capgemini interview modes' optimistic-concurrency guard
    (_spark_persist and its Dave/Commit/TCS near-duplicates, server.py
    ~4448-4453, ~4808, ~5377): `update_one({"interview_id": ...,
    "turn_count": expected_turn_count}, {"$set": changes})`, raising
    HTTPException(409, "stale_turn") when `matched_count == 0`. Returns
    None (rather than raising) on that same zero-rows case -- the caller
    (reports_pg.finish_interview, which wraps this together with the
    report-cache invalidation in one transaction) is responsible for
    turning a None here into the 409 the app returns today, same as the
    Mongo code's own `res.matched_count == 0` check. `turn_count` lives
    inside the jsonb `data` column (see this module's docstring -- no
    dedicated column was added for it, `data->>'turn_count'` is compared
    instead), matching every Capgemini-mode interview's real field."""
    if not changes:
        return None
    cols, data_patch = _split(changes)
    set_parts: List[str] = []
    params: List[Any] = []
    for col, value in cols.items():
        set_parts.append(f"{col} = %s")
        params.append(Jsonb(value) if col in _JSONB_COLUMNS else value)
    if data_patch:
        set_parts.append("data = data || %s::jsonb")
        params.append(Jsonb(data_patch))
    params.extend([interview_id, str(expected_turn_count)])
    return await fetch_one(
        f"UPDATE interviews SET {', '.join(set_parts)} "
        "WHERE interview_id = %s AND (data->>'turn_count') = %s "
        f"RETURNING {_COLUMNS}",
        params,
    )
