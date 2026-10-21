"""Postgres read access for `mcq_pool` and `mcq_pool_stats` -- mirrors the
query shapes in backend/banks/mcq_pool.py (pop_from_pool, pool_stats's
admin readout). Columns match the old Mongo document fields 1:1 for both
tables (no renames -- see SUPABASE_MIGRATION_BRIEF.md's mapping table), so
every row here already has mcq_pool.py's expected shape.

NOT ported here: the generation/verification pipeline (_process_one_stem,
the background worker, `_record_outcome`'s upsert-with-$inc write side).
That is write/generation logic, not a content-bank read, and `mcq_pool_stats`
specifically is called out in the migration task as "read-only version
here; the actual upsert-write logic is a LATER phase" -- noted below so
that later phase isn't surprised by anything this phase already decided.
"""
from __future__ import annotations

from typing import List, Optional

from db_postgres import fetch_all, fetch_one

_POOL_COLUMNS = (
    "pool_id, company_name, section_key, verified, difficulty, prompt, "
    "options, correct_index, explanation, ground_truth_source, created_at"
)


async def pop_one(company_name: str, section_key: str) -> Optional[dict]:
    """Atomically removes and returns ONE verified row for
    (company_name, section_key), or None if the pool is empty for that key.

    This is the direct Postgres equivalent of mcq_pool.py's
    `_db.mcq_pool.find_one_and_delete({...})` -- a single `DELETE ... WHERE
    pool_id = (SELECT ... LIMIT 1) RETURNING *` statement. The row to
    delete is chosen by a sub-select evaluated once per statement; under
    Postgres's normal read-committed row locking, two concurrent callers
    racing on the same (company_name, section_key) can never both get the
    same row back -- whichever DELETE's row lock loses the race re-checks
    the WHERE clause against the post-delete table state and finds nothing,
    so it legitimately returns zero rows (None here) rather than the
    first caller's row. This is the "atomic-consume" guarantee the pool
    draw depends on (see pop_from_pool's own docstring: "Atomically remove
    up to `count` verified questions")."""
    return await fetch_one(
        """
        DELETE FROM mcq_pool
        WHERE pool_id = (
            SELECT pool_id FROM mcq_pool
            WHERE company_name = %s AND section_key = %s AND verified = true
            LIMIT 1
        )
        RETURNING {cols}
        """.format(cols=_POOL_COLUMNS),
        (company_name, section_key),
    )


async def pop_up_to(company_name: str, section_key: str, count: int) -> List[dict]:
    """Up to `count` atomically-popped rows for (company_name, section_key)
    -- mirrors pop_from_pool's `for _ in range(count): find_one_and_delete`
    loop, stopping early once the pool is empty. Each individual pop is
    still its own atomic statement (see pop_one); this just repeats it,
    same as the Mongo version's own loop."""
    if count <= 0:
        return []
    out: List[dict] = []
    for _ in range(count):
        row = await pop_one(company_name, section_key)
        if row is None:
            break
        out.append(row)
    return out


async def count_by_company_and_section() -> List[dict]:
    """Mirrors mcq_pool.py's `pool_stats()`'s `pool_counts` half: `_db.mcq_pool
    .aggregate([{"$group": {"_id": {"c": "$company_name", "k": "$section_key"},
    "count": {"$sum": 1}}}, {"$project": ...}, {"$sort": {"company_name": 1,
    "section_key": 1}}])`. This is the Step-1 gap flagged in
    SUPABASE_CUTOVER_PLAN.md's punch list item #1: `get_all_stats()` below
    only ever covered the `mcq_pool_stats` half of `pool_stats()`'s return
    value -- this is the missing `pool_counts` half, a single `GROUP BY`
    query replacing Mongo's 3-stage `$group`/`$project`/`$sort` pipeline.
    Returns rows shaped `{"company_name": ..., "section_key": ...,
    "count": ...}`, matching the Mongo pipeline's own `$project`ed shape
    exactly so callers don't need to reshape the result."""
    return await fetch_all(
        "SELECT company_name, section_key, count(*) AS count "
        "FROM mcq_pool GROUP BY company_name, section_key "
        "ORDER BY company_name, section_key"
    )


async def get_all_stats() -> List[dict]:
    """Read-only admin readout -- mirrors mcq_pool.py's `pool_stats()`:
    `_db.mcq_pool_stats.find({}, {"_id": 0})`. Sorted by
    (company_name, section_key) for determinism (pool_stats() sorts the
    same way in Python after reading).

    The write side (mcq_pool.py's `_record_outcome`, an upsert that
    increments total_generated/outcome_*/source_* counters per
    (company_name, section_key) via Mongo's `$inc` + `$setOnInsert`) is
    NOT built here -- that is generation-pipeline write logic, explicitly
    deferred to the user-data/write-path migration phase. Whoever picks
    that up next: the Postgres equivalent is a single `INSERT ... ON
    CONFLICT (company_name, section_key) DO UPDATE SET total_generated =
    mcq_pool_stats.total_generated + 1, outcome_<x> = mcq_pool_stats.
    outcome_<x> + 1, updated_at = now() RETURNING *` -- atomic in one
    statement, same spirit as pop_one above, no read-then-write race."""
    return await fetch_all(
        "SELECT * FROM mcq_pool_stats ORDER BY company_name, section_key"
    )
