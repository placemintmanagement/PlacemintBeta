"""Postgres access for `reports` -- mirrors the `db.reports` call sites in
backend/server.py: the cache read in `_build_final_report_doc`
(~6734: `db.reports.find_one(dict(cache_query), {"_id": 0})`, where
cache_query is either `{"attempt_id": ..., "user_id": ...}` or
`{"interview_id": ..., "user_id": ...}`), the fresh-report insert right
after a cache miss (~6765-6777), and `_invalidate_cached_report`
(~4433-4443: `db.reports.delete_many(...)` by interview_id, and again by
attempt_id when one exists) -- called from exactly three near-duplicate
"interview finish" call sites (_spark_persist ~4455, and its Dave/Commit
near-duplicates at ~4815 and ~5384), each of which does an `interviews.
update_one` (the turn-count-guarded status change) immediately before
invalidating the cached report.

Fix #3 (the delete-then-insert transaction requirement): the migration
brief asks for report/interview "finish" sequences to commit as one
transaction instead of Mongo's independent statements. The real call
sites' actual shape is "update the interview's status (one statement) +
delete any now-stale cached report row(s) (one or two more statements)" --
the FRESH report is not inserted in that same request; it's generated
lazily, on demand, the next time anything calls GET /report (a separate
request, possibly much later; see `_build_final_report_doc` above).
finish_interview below wraps the three real statements (interview update,
report delete by interview_id, report delete by attempt_id) in one
transaction -- a crash mid-sequence can no longer leave the interview
marked finished with a stale report still cached, or leave the report
deleted while the interview update silently failed. replace_cached_report
is ALSO provided as a literal delete-then-INSERT single-transaction
primitive (matching the brief's wording most directly), for a future
report-regeneration call site that wants to replace an existing cached row
atomically rather than relying on "delete now, insert whenever the next
GET happens" -- not wired into the GET /report handler in this phase
(that handler isn't being cut over yet), but exercised by its own test.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import psycopg
from psycopg.types.json import Jsonb

from db_postgres import fetch_all, fetch_one, transaction

_COLUMNS = (
    "report_id, attempt_id, user_id, company_name, created_at, oa_summary, "
    "interview_summary, resume_analysis, report"
)
_JSONB_COLUMNS = {"oa_summary", "interview_summary", "resume_analysis", "report"}


async def get_cached_report(
    user_id: str, attempt_id: Optional[str] = None, interview_id: Optional[str] = None
) -> Optional[dict]:
    """Mirrors `_build_final_report_doc`'s cache read (~6734): `db.reports.
    find_one(dict(cache_query), {"_id": 0})` where cache_query is `{
    "attempt_id": ..., "user_id": ...}` (server.py ~6792) or `{
    "interview_id": ..., "user_id": ...}` (~6820). Exactly one of
    attempt_id/interview_id should be given, matching the real call
    sites -- schema.sql's `reports` table has no `interview_id` column
    (only `attempt_id`), so the interview_id lookup joins through
    `interviews` to recover the attempt it belongs to, same resolution the
    report cache_query already assumes (every report row is really keyed
    by attempt_id underneath; a caller with only an interview_id needs it
    translated first)."""
    if attempt_id is not None:
        return await fetch_one(
            f"SELECT {_COLUMNS} FROM reports WHERE attempt_id = %s AND user_id = %s "
            "ORDER BY created_at DESC LIMIT 1",
            (attempt_id, user_id),
        )
    if interview_id is not None:
        return await fetch_one(
            f"SELECT r.report_id, r.attempt_id, r.user_id, r.company_name, "
            f"r.created_at, r.oa_summary, r.interview_summary, r.resume_analysis, r.report "
            "FROM reports r JOIN interviews i ON i.attempt_id = r.attempt_id "
            "WHERE i.interview_id = %s AND r.user_id = %s "
            "ORDER BY r.created_at DESC LIMIT 1",
            (interview_id, user_id),
        )
    return None


async def insert_report(doc: Dict[str, Any]) -> dict:
    """Mirrors `db.reports.insert_one(doc)` (server.py ~6765-6777) -- `doc`
    is the same flat dict that call site builds (report_id, user_id,
    company_name, resume_analysis, oa_summary, interview_summary, report,
    created_at, plus `**extra_doc_fields` which supplies attempt_id and/or
    interview_id -- schema.sql has no interview_id column, so a caller
    passing one here should fold it elsewhere; the only field this
    function writes to a real column from extra_doc_fields is
    attempt_id)."""
    cols = {k: doc[k] for k in ("report_id", "user_id", "company_name", "attempt_id",
                                 "created_at", "oa_summary", "interview_summary",
                                 "resume_analysis", "report") if k in doc}
    col_names = list(cols.keys())
    placeholders = ", ".join(["%s"] * len(col_names))
    params = [Jsonb(v) if k in _JSONB_COLUMNS and v is not None else v for k, v in cols.items()]
    row = await fetch_one(
        f"INSERT INTO reports ({', '.join(col_names)}) VALUES ({placeholders}) "
        f"RETURNING {_COLUMNS}",
        params,
    )
    assert row is not None
    return row


async def invalidate_reports(user_id: str, interview_id: Optional[str] = None, attempt_id: Optional[str] = None) -> None:
    """Standalone mirror of `_invalidate_cached_report` (server.py
    ~4433-4443) for callers that just want the delete, without the
    interview-update transaction wrapper (finish_interview below is the
    fix-#3 version that wraps both together). `interview_id` is resolved to
    its attempt_id the same way get_cached_report does, since reports has
    no interview_id column."""
    if interview_id is not None:
        await fetch_all(
            "DELETE FROM reports WHERE user_id = %s AND attempt_id IN "
            "(SELECT attempt_id FROM interviews WHERE interview_id = %s)",
            (user_id, interview_id),
        )
    if attempt_id is not None:
        await fetch_all(
            "DELETE FROM reports WHERE attempt_id = %s AND user_id = %s",
            (attempt_id, user_id),
        )


async def finish_interview(
    interview_id: str,
    expected_turn_count: int,
    changes: Dict[str, Any],
    user_id: str,
    attempt_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Fix #3: the real "interview finish" sequence --
    (1) the turn-count-guarded interview status update, (2) invalidate any
    report cached by interview_id, (3) invalidate any report cached by
    attempt_id (only when one exists, matching `_invalidate_cached_report`'s
    own `if interview.get("attempt_id"):` guard) -- run inside ONE
    transaction instead of three independent statements, so a crash
    mid-sequence can never leave the interview marked finished with a
    stale report still cached.

    `changes` is split the same way interviews_pg.update_interview_if_turn_
    matches splits it (promoted columns vs. the jsonb `data` column --
    duplicated here, not imported, because the two statements must share
    ONE cursor/transaction; see db_postgres.transaction's docstring for why
    a plain call to another repository module's own fetch_one-based
    function can't be used mid-transaction). `turn_count` lives in `data`
    (see interviews_pg's module docstring on the pending company_id/data
    migration this also depends on).

    Returns {"interview": <row or None>, "stale_turn": bool}. stale_turn
    True (interview None) means the optimistic-concurrency guard found
    turn_count had already moved -- caller raises the same 409
    "stale_turn" HTTPException the Mongo code raises today. The report
    invalidation only runs when the update actually matched (an already-
    stale request must not go on to delete a report out from under a
    DIFFERENT, still-valid finish that raced ahead of it)."""
    _TOP_LEVEL_INTERVIEW_COLS = (
        "status", "current_index", "completed_at", "questions", "answers",
    )
    _JSONB_INTERVIEW_COLS = {"questions", "answers"}
    cols = {k: changes[k] for k in _TOP_LEVEL_INTERVIEW_COLS if k in changes}
    data_patch = {k: v for k, v in changes.items() if k not in _TOP_LEVEL_INTERVIEW_COLS}

    set_parts: List[str] = []
    params: List[Any] = []
    for col, value in cols.items():
        set_parts.append(f"{col} = %s")
        params.append(Jsonb(value) if col in _JSONB_INTERVIEW_COLS else value)
    if data_patch:
        set_parts.append("data = data || %s::jsonb")
        params.append(Jsonb(data_patch))
    params.extend([interview_id, str(expected_turn_count)])

    async with transaction() as cur:
        await cur.execute(
            f"UPDATE interviews SET {', '.join(set_parts)} "
            "WHERE interview_id = %s AND (data->>'turn_count') = %s "
            "RETURNING interview_id, attempt_id, user_id, company_id, resume_id, "
            "company_name, status, current_index, created_at, completed_at, "
            "questions, answers, data",
            params,
        )
        row = await cur.fetchone()
        if row is None:
            return {"interview": None, "stale_turn": True}

        await cur.execute(
            "DELETE FROM reports WHERE user_id = %s AND attempt_id IN "
            "(SELECT attempt_id FROM interviews WHERE interview_id = %s)",
            (user_id, interview_id),
        )
        effective_attempt_id = attempt_id or row.get("attempt_id")
        if effective_attempt_id:
            await cur.execute(
                "DELETE FROM reports WHERE attempt_id = %s AND user_id = %s",
                (effective_attempt_id, user_id),
            )

    return {"interview": row, "stale_turn": False}


async def replace_cached_report(
    delete_filters: Dict[str, Any], doc: Dict[str, Any]
) -> dict:
    """A literal delete-then-insert single-transaction primitive: deletes
    every `reports` row matching `delete_filters` (a plain column=value
    dict, e.g. {"attempt_id": ..., "user_id": ...}), then inserts `doc`,
    both inside one transaction -- for a future report-regeneration call
    site that wants to atomically replace a stale cached report instead of
    relying on "delete now, a later GET inserts the fresh one whenever it
    happens" (which is what the real call sites do today -- see this
    module's docstring). Not wired into GET /report in this phase."""
    where = " AND ".join(f"{col} = %s" for col in delete_filters)
    cols = {k: doc[k] for k in ("report_id", "user_id", "company_name", "attempt_id",
                                 "created_at", "oa_summary", "interview_summary",
                                 "resume_analysis", "report") if k in doc}
    col_names = list(cols.keys())
    placeholders = ", ".join(["%s"] * len(col_names))
    insert_params = [Jsonb(v) if k in _JSONB_COLUMNS and v is not None else v for k, v in cols.items()]

    async with transaction() as cur:
        if delete_filters:
            await cur.execute(f"DELETE FROM reports WHERE {where}", list(delete_filters.values()))
        await cur.execute(
            f"INSERT INTO reports ({', '.join(col_names)}) VALUES ({placeholders}) "
            f"RETURNING {_COLUMNS}",
            insert_params,
        )
        row = await cur.fetchone()
    assert row is not None
    return row
