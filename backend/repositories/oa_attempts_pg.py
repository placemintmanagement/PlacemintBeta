"""Postgres access for `oa_attempts` + `oa_attempt_keys` -- mirrors the
`db.oa_attempts` call sites in backend/server.py: the double-start guard and
attempt-creation sequence (~1987-2072), the many ownership-scoped
`find_one({"attempt_id": ..., "user_id": ...})` reads (~3058-3774 and
others), the per-user listing (~3679, ~6836), and the various
`update_one({"attempt_id": ...}, {"$set": ...})` progress writes scattered
through the OA section-submit flow (~1422, ~1777-1936, ~3318, ~3361).

Answer-key separation: `_store_hidden_answer_key`/`_get_hidden_answer_key`
(server.py:1021-1033) keep puzzle-type answer keys on the SAME oa_attempts
document under `_hidden_answer_keys`, excluded only from the one GET
/oa/{attempt_id} projection (line ~2314) -- every other find_one in the
file reads the attempt WITHOUT excluding that field, so the exclusion was
one query's responsibility, not the schema's. schema.sql moves answer keys
to their own table (`oa_attempt_keys`) specifically so that can never
happen again: nothing in this module ever selects `oa_attempt_keys` through
`get_attempt`/`list_attempts_for_user`/etc -- only `set_hidden_answer_key`/
`get_hidden_answer_key` below touch that table at all, and those two are
the explicitly-scoped internal grading functions the migration brief calls
for. A caller that wants an answer key has to call one of those two by
name; it can never fall out of a general attempt fetch.

Fix #2 (the "already in progress" race): server.py's double-start guard
(~1987-1996) was check-then-insert with real awaits (background work,
other updates) in between -- a genuine race window. `supabase/
002_orders_and_oa_attempts_race_fix.sql`'s partial unique index
(`oa_attempts_one_in_progress_idx` on (user_id, company_id) WHERE status =
'in_progress', already applied) is the actual guarantee; create_attempt
below still does the same pre-check-for-a-nice-error-message the app wants
(see get_existing_in_progress), but ALSO catches psycopg.errors.
UniqueViolation on the INSERT itself and turns that into the same clean
"already in progress" result instead of letting the raw constraint
violation become a 500 -- that's what actually closes the race; the
pre-check alone cannot.
"""
from __future__ import annotations

from typing import Any, List, Optional, Sequence

import psycopg
from psycopg.types.json import Jsonb

from db_postgres import fetch_all, fetch_one, transaction

_COLUMNS = (
    "attempt_id, user_id, company_id, company_name, cluster, status, "
    "generation_status, scoring_mode, charged_source, current_section_index, "
    "resume_id, created_at, completed_at, sections, answers, section_results"
)


async def get_existing_in_progress(user_id: str, company_id: str) -> Optional[dict]:
    """Mirrors server.py:1987-1989's pre-check: `db.oa_attempts.find_one(
    {"user_id": ..., "company_id": ..., "status": "in_progress"},
    {"_id": 0})`. Used both as create_attempt's nice-error-message pre-check
    and, standalone, by anything else that wants to know "does this user
    already have one of these open" without trying to create one."""
    return await fetch_one(
        f"SELECT {_COLUMNS} FROM oa_attempts WHERE user_id = %s AND company_id = %s "
        "AND status = 'in_progress'",
        (user_id, company_id),
    )


async def create_attempt(
    attempt_id: str,
    user_id: str,
    company_id: str,
    company_name: str,
    cluster: Optional[str],
    scoring_mode: Optional[str],
    sections: list,
    charged_source: Optional[str] = None,
    resume_id: Optional[str] = None,
    status: str = "in_progress",
    generation_status: str = "generating",
) -> dict:
    """Mirrors server.py:1987-2072's full create-attempt sequence: the
    double-start pre-check, then the attempt insert. Also inserts this
    attempt's (initially empty) `oa_attempt_keys` row in the SAME
    transaction as the `oa_attempts` insert -- they're logically one unit
    (every attempt has exactly one keys row from the moment it exists) even
    though schema.sql keeps them in two tables precisely so answer keys can
    never leak through a plain attempt read.

    Returns {"created": True, "attempt": <row>} on success, or
    {"created": False, "attempt": <existing in-progress row>} if one
    already existed -- found either by the pre-check or (the actual race-
    closing path) by catching the partial unique index's UniqueViolation on
    the INSERT itself and re-fetching. Callers map "created": False to the
    same 409 "oa_already_in_progress" response server.py returns today.
    """
    pre_existing = await get_existing_in_progress(user_id, company_id)
    if pre_existing is not None:
        return {"created": False, "attempt": pre_existing}

    try:
        async with transaction() as cur:
            await cur.execute(
                "INSERT INTO oa_attempts (attempt_id, user_id, company_id, "
                "company_name, cluster, status, generation_status, scoring_mode, "
                "charged_source, resume_id, sections) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                f"RETURNING {_COLUMNS}",
                (
                    attempt_id, user_id, company_id, company_name, cluster,
                    status, generation_status, scoring_mode, charged_source,
                    resume_id, Jsonb(sections),
                ),
            )
            row = await cur.fetchone()
            await cur.execute(
                "INSERT INTO oa_attempt_keys (attempt_id, answer_keys) VALUES (%s, %s)",
                (attempt_id, Jsonb({})),
            )
    except psycopg.errors.UniqueViolation:
        # The race the pre-check couldn't close: another request's INSERT
        # won between our pre-check and ours. Re-fetch and report it the
        # same clean way as the pre-check branch above, never the raw
        # constraint-violation error.
        existing = await get_existing_in_progress(user_id, company_id)
        return {"created": False, "attempt": existing}

    return {"created": True, "attempt": row}


async def get_attempt(attempt_id: str, user_id: Optional[str] = None) -> Optional[dict]:
    """Mirrors the many ownership-scoped `db.oa_attempts.find_one(
    {"attempt_id": ..., "user_id": ...}, {"_id": 0})` reads. `user_id` is
    optional only because a few internal call sites (e.g. _spark_finish's
    stale-turn re-fetch) look an attempt up by id alone -- pass it whenever
    the caller is serving a user-facing request."""
    if user_id is not None:
        return await fetch_one(
            f"SELECT {_COLUMNS} FROM oa_attempts WHERE attempt_id = %s AND user_id = %s",
            (attempt_id, user_id),
        )
    return await fetch_one(f"SELECT {_COLUMNS} FROM oa_attempts WHERE attempt_id = %s", (attempt_id,))


async def list_attempts_for_user(user_id: str, limit: int = 20) -> List[dict]:
    """Mirrors `db.oa_attempts.find({"user_id": ...}, {"_id": 0}).sort(
    "created_at", -1).to_list(20)` (server.py ~3679, ~6836)."""
    return await fetch_all(
        f"SELECT {_COLUMNS} FROM oa_attempts WHERE user_id = %s "
        "ORDER BY created_at DESC LIMIT %s",
        (user_id, limit),
    )


async def update_attempt_progress(attempt_id: str, **fields: Any) -> Optional[dict]:
    """Mirrors the repeated `db.oa_attempts.update_one({"attempt_id": ...},
    {"$set": {...}})` progress writes scattered through the OA
    section-submit flow (current_section_index, status, generation_status,
    completed_at, sections, answers, section_results, ...). jsonb columns
    (sections/answers/section_results) are wrapped in Jsonb automatically
    when the caller passes a dict/list for them; scalar columns pass
    straight through."""
    _JSONB_FIELDS = {"sections", "answers", "section_results"}
    if not fields:
        return await get_attempt(attempt_id)
    set_parts = []
    params: List[Any] = []
    for col, value in fields.items():
        set_parts.append(f"{col} = %s")
        params.append(Jsonb(value) if col in _JSONB_FIELDS and value is not None else value)
    params.append(attempt_id)
    return await fetch_one(
        f"UPDATE oa_attempts SET {', '.join(set_parts)} WHERE attempt_id = %s "
        f"RETURNING {_COLUMNS}",
        params,
    )


# ---------------------------------------------------------------------------
# Answer keys -- explicitly scoped, never exposed via the functions above.
# ---------------------------------------------------------------------------

async def set_hidden_answer_key(attempt_id: str, section_key: str, question_id: str, key_data: Any) -> None:
    """Mirrors `_store_hidden_answer_key` (server.py:1021-1029): sets
    `answer_keys[section_key][question_id] = key_data`, creating the
    intermediate `section_key` object if it doesn't exist yet. This is the
    ONLY way anything writes to oa_attempt_keys outside of create_attempt's
    initial empty row -- an internal, grading-side call, never reachable
    from a client-facing response.

    Live-verification correction: a single `jsonb_set(answer_keys,
    ARRAY[section_key, question_id], key_data, true)` (the original form of
    this statement) does NOT create a missing intermediate path element --
    Postgres's `create_missing` flag only ever creates the LAST element of
    `path` if absent; if a non-last element (here, `section_key`) is
    missing, jsonb_set is a silent no-op and returns `answer_keys`
    unchanged (confirmed directly against live Postgres, not from docs
    alone -- every brand-new attempt starts with `answer_keys = '{}'`, so
    the very first call for any `section_key` was silently swallowed,
    and every subsequent call for that same never-created `section_key`
    silently swallowed too; mocked tests only ever asserted this
    statement's SQL text, never executed it, so this never surfaced until
    a real Postgres run). Fixed by nesting two single-level jsonb_sets: the
    inner one builds `{question_id: key_data}` merged onto whatever that
    section already holds (`COALESCE(answer_keys -> section_key, '{}')`,
    so sibling question_ids under the same section are preserved), and the
    outer one sets that whole object as `answer_keys[section_key]` -- a
    single-level jsonb_set on an existing top-level object, which Postgres
    creates correctly."""
    await fetch_one(
        "UPDATE oa_attempt_keys SET answer_keys = "
        "jsonb_set(answer_keys, ARRAY[%s]::text[], "
        "jsonb_set(COALESCE(answer_keys -> %s, '{}'::jsonb), ARRAY[%s]::text[], %s::jsonb, true), "
        "true) WHERE attempt_id = %s "
        "RETURNING attempt_id",
        (section_key, section_key, question_id, Jsonb(key_data), attempt_id),
    )


async def get_hidden_answer_key(attempt_id: str, section_key: str, question_id: str) -> Any:
    """Mirrors `_get_hidden_answer_key` (server.py:1032-1033): reads back
    one answer key for server-side grading only. Deliberately the only
    read path into oa_attempt_keys -- there is no "get all keys for this
    attempt" or "list oa_attempt_keys" function here on purpose."""
    row = await fetch_one(
        "SELECT answer_keys #> %s::text[] AS key_data FROM oa_attempt_keys WHERE attempt_id = %s",
        ([section_key, question_id], attempt_id),
    )
    return row["key_data"] if row else None
