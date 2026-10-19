"""Postgres read access for `puzzle_bank` and `gamified_round_config` --
mirrors the query shapes in backend/games/gamified_round.py (get_config,
sample_puzzles, and the various `_db.puzzle_bank.find_one`/`find` calls used
by check_answer/get_grid_challenge_phase/grade_session/
grade_motion_challenge_session, all of which key off `puzzle_id` the same
way).

Both tables need a merge-back: `supabase/schema.sql` promoted the fields
callers filter/join on into real columns (puzzle_id, game_type,
company_tags, content_hash, explanation for puzzle_bank; company,
draw_count, game_types, per_type, draw_note for gamified_round_config) and
renamed a few of them from the old Mongo field names in the process
(gameType -> game_type, companyTags -> company_tags, perType -> per_type,
drawCount -> draw_count, _drawNote -> draw_note). Every type-specific
puzzle_bank field that ISN'T one of those (grid, blocks, walls, candidates,
circleLayout, correctAnswer, ...) still lives in the jsonb `data` column.

gamified_round.py's real callers (confirmed in backend/server.py, e.g.
`config.get("gameTypes")`, `config.get("drawCount")`, `config.get("perType")`,
and backend/games/gamified_round.py's own `doc.get("gameType")` /
`doc.get("blocks")` / `doc["circleLayout"]`) still expect the OLD camelCase
Mongo keys -- so the merge-back functions below rebuild that exact shape
rather than exposing the new snake_case column names, letting a future
cutover swap the data source under an unchanged call site.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from db_postgres import fetch_all, fetch_one


def _merge_puzzle_row(row: Optional[dict]) -> Optional[dict]:
    """jsonb `data` (grid/blocks/walls/candidates/circleLayout/
    correctAnswer/... -- every type-specific field) merged back with the
    promoted top-level columns, restoring the old Mongo document shape:
    `gameType`/`companyTags` (renamed columns, restored to their old
    camelCase names) plus `puzzle_id`/`content_hash`/`explanation`
    (unchanged names) layered on top so a same-named column always wins
    over anything of the same key that happened to also be in `data`."""
    if row is None:
        return None
    data = row.get("data") or {}
    merged: Dict[str, Any] = dict(data)
    merged["puzzle_id"] = row["puzzle_id"]
    merged["gameType"] = row["game_type"]
    merged["companyTags"] = row["company_tags"]
    merged["content_hash"] = row.get("content_hash")
    merged["explanation"] = row.get("explanation")
    return merged


async def get_by_id(puzzle_id: str) -> Optional[dict]:
    """Mirrors the many `_db.puzzle_bank.find_one({"puzzle_id": puzzle_id},
    {"_id": 0})` call sites in gamified_round.py (check_answer,
    get_grid_challenge_phase, check_grid_challenge_answer,
    grade_grid_challenge_session). Those queries filter on puzzle_id alone
    (not the (game_type, puzzle_id) composite PK) -- same behavior here:
    if puzzle_id collides across game types this returns whichever row
    Postgres happens to pick first, matching Mongo find_one's own
    unspecified-tiebreak semantics for a non-unique filter."""
    row = await fetch_one(
        "SELECT * FROM puzzle_bank WHERE puzzle_id = %s LIMIT 1", (puzzle_id,)
    )
    return _merge_puzzle_row(row)


async def get_by_ids(puzzle_ids: Sequence[str]) -> List[dict]:
    """Mirrors `_db.puzzle_bank.find({"puzzle_id": {"$in": puzzle_ids}},
    {"_id": 0})` (grade_session, grade_motion_challenge_session)."""
    if not puzzle_ids:
        return []
    rows = await fetch_all(
        "SELECT * FROM puzzle_bank WHERE puzzle_id = ANY(%s)", (list(puzzle_ids),)
    )
    return [m for r in rows if (m := _merge_puzzle_row(r)) is not None]


async def sample_puzzles(
    company: str, game_type: str, exclude_ids: Optional[Sequence[str]], count: int
) -> List[dict]:
    """Up to `count` genuinely-random puzzles for (game_type, company),
    excluding `exclude_ids`. Direct replacement for sample_puzzles' Mongo
    query (`_db.puzzle_bank.find({"gameType": game_type, "companyTags":
    company, "puzzle_id": {"$nin": list(seen)}}, {"_id": 0}).to_list(
    length=count)`) -- that Mongo call was never actually random (plain
    cursor order, first `count` docs), one of the two cases
    SUPABASE_MIGRATION_BRIEF.md explicitly calls out to fix for real here
    via `ORDER BY random() LIMIT n`, not replicate.

    Answer-stripping (removing `correctAnswer`/`explanation` before a
    client-facing response -- gamified_round.strip_answer) is NOT done
    here; that stays the caller's job, same as it is for the Mongo path
    today, so this module never has to guess which caller is server-only
    vs. client-facing."""
    if count <= 0:
        return []
    params: list = [game_type, company]
    sql = (
        "SELECT * FROM puzzle_bank WHERE game_type = %s AND %s = ANY(company_tags)"
    )
    if exclude_ids:
        sql += " AND NOT (puzzle_id = ANY(%s))"
        params.append(list(exclude_ids))
    sql += " ORDER BY random() LIMIT %s"
    params.append(count)
    rows = await fetch_all(sql, params)
    return [m for r in rows if (m := _merge_puzzle_row(r)) is not None]


async def get_config(company: str) -> Optional[dict]:
    """Mirrors gamified_round.get_config:
    `_db.gamified_round_config.find_one({"company": company}, {"_id": 0})`.
    Restores the old Mongo camelCase keys server.py's callers already read
    (`gameTypes`, `drawCount`, `perType`, `_drawNote`) from the renamed
    Postgres columns (game_types, draw_count, per_type, draw_note)."""
    row = await fetch_one(
        "SELECT company, draw_count, game_types, per_type, draw_note "
        "FROM gamified_round_config WHERE company = %s",
        (company,),
    )
    if row is None:
        return None
    return {
        "company": row["company"],
        "drawCount": row["draw_count"],
        "gameTypes": row["game_types"],
        "perType": row["per_type"],
        "_drawNote": row["draw_note"],
    }
