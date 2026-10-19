"""Postgres read access for `mcq_static_bank` -- mirrors the query shapes in
backend/banks/mcq_static_bank.py (sample_static, _draw_bucket,
topic_bank_size). Columns match the old Mongo document's field names 1:1
(see SUPABASE_MIGRATION_BRIEF.md's collection->table mapping -- no renames
for this table), so every row this module returns already has the same
shape mcq_static_bank.py's `_item_from_doc`/callers expect
(question_id, topic, subtopic, subtype, question_style, difficulty, prompt,
options, correct_index, explanation, chart, svg_diagram,
ground_truth_source, verified_by, source_batch, date_added) -- `options`
and `chart` come back as plain Python list/dict already (psycopg 3 decodes
jsonb automatically), not JSON strings.

Deliberately NOT ported here: per-user seen-tracking (get_seen_ids/
mark_seen in the Mongo module) and the least-recently-seen reuse sort --
both read/write `question_seen`, a USER table, which is phase 3 (user-data
port) of the migration, not this phase (read-only content banks). Every
function below takes `exclude_ids` as a plain parameter instead, so a future
Postgres-backed caller can supply whatever exclusion set it wants (seen ids,
already-picked ids within the same draw, etc.) without this module needing
to know where that set came from.

Random draws here use `ORDER BY random() LIMIT n` -- a genuine, single-query
random draw. This is a deliberate improvement over the Mongo code's own
shuffle-dance (fetch id-only projection, `random.shuffle` in Python, re-fetch
the picked ids) -- see SUPABASE_MIGRATION_BRIEF.md's "Mongo -> Postgres
translation notes" -- not a faithfulness risk.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from db_postgres import fetch_all, fetch_one

_COLUMNS = (
    "question_id, topic, subtopic, subtype, question_style, difficulty, "
    "prompt, options, correct_index, explanation, chart, svg_diagram, "
    "ground_truth_source, verified_by, source_batch, date_added"
)


def _exclusion_clause(exclude_ids: Optional[Sequence[str]], params: list) -> str:
    """Appends an exclusion param and returns the SQL fragment for it, or ''
    if there's nothing to exclude. Keeping this conditional (rather than
    always binding `= ANY(%s)` with a possibly-empty list) sidesteps
    Postgres's "could not determine data type of parameter" error on an
    empty array literal with no type context."""
    if not exclude_ids:
        return ""
    params.append(list(exclude_ids))
    return " AND NOT (question_id = ANY(%s))"


async def count_by_topic(topic: str) -> int:
    """Mirrors mcq_static_bank.topic_bank_size: total rows for `topic`,
    seen or unseen, across every candidate."""
    row = await fetch_one(
        "SELECT count(*) AS n FROM mcq_static_bank WHERE topic = %s", (topic,)
    )
    return int(row["n"]) if row else 0


async def list_by_topic(
    topic: str,
    difficulty: Optional[str] = None,
    exclude_ids: Optional[Sequence[str]] = None,
) -> List[dict]:
    """Every row for `topic` (optionally narrowed to one `difficulty`),
    excluding `exclude_ids`. Mirrors the full-document `$nin` queries
    mcq_static_bank.py runs today (sample_static's reuse-candidate fetch,
    _draw_bucket's unseen_docs/candidates queries) -- unordered; any
    least-recently-seen sort stays the caller's job since that needs
    per-user `seen_at` data this module doesn't touch."""
    params: list = [topic]
    sql = f"SELECT {_COLUMNS} FROM mcq_static_bank WHERE topic = %s"
    if difficulty is not None:
        sql += " AND difficulty = %s"
        params.append(difficulty)
    sql += _exclusion_clause(exclude_ids, params)
    return await fetch_all(sql, params)


async def sample_random_by_topic(
    topic: str,
    count: int,
    difficulty: Optional[str] = None,
    exclude_ids: Optional[Sequence[str]] = None,
) -> List[dict]:
    """Up to `count` genuinely-random rows for `topic` (optionally one
    `difficulty`), excluding `exclude_ids` -- the direct, single-statement
    replacement for sample_static's shuffle-then-refetch dance and
    _draw_bucket's find()-then-`random.shuffle()` -- both existed only to
    work around Mongo's non-random cursor order; Postgres's `ORDER BY
    random()` does the whole thing in one query."""
    if count <= 0:
        return []
    params: list = [topic]
    sql = f"SELECT {_COLUMNS} FROM mcq_static_bank WHERE topic = %s"
    if difficulty is not None:
        sql += " AND difficulty = %s"
        params.append(difficulty)
    sql += _exclusion_clause(exclude_ids, params)
    sql += " ORDER BY random() LIMIT %s"
    params.append(count)
    return await fetch_all(sql, params)


async def get_by_ids(question_ids: Sequence[str]) -> List[dict]:
    """`$in`-style fetch by id list -- kept as a primitive for callers that
    still want to pick ids first and fetch full docs after (as
    sample_static's old two-step dance did); sample_random_by_topic makes
    that two-step unnecessary for a fresh random draw, but this is still
    the right call for "give me exactly these known ids" (e.g. re-fetching
    a previously-picked set)."""
    if not question_ids:
        return []
    return await fetch_all(
        f"SELECT {_COLUMNS} FROM mcq_static_bank WHERE question_id = ANY(%s)",
        (list(question_ids),),
    )
