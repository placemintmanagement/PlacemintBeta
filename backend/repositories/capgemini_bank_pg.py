"""Postgres read access for `capgemini_round1_bank` and
`capgemini_round2_bank` -- mirrors the query shapes in backend/server.py's
"capgemini_round1"/"capgemini_round2_ai_literacy" OA-section branches
(search `db.capgemini_round1_bank` / `db.capgemini_round2_bank` there).

capgemini_round1_bank: per schema.sql's own comment, "the complete original
document" is stored whole in the jsonb `data` column -- `section`,
`item_type`, `difficulty`, `question_id` are promoted to real columns only
for indexing/filtering, not because the old document shape dropped them
from `data`. So the merge-back here is simply "return `data` as-is" (no
field-by-field reconstruction needed, unlike puzzle_bank/gamified_round_
config where columns were renamed) -- each row's `data` already has
whatever id field that item type uses (question_id/scenario_id/passage_id/
clip_id/item_id), which is exactly what server.py's draw_sectionN_questions
helpers key off of.

capgemini_round2_bank: no field renames per the migration brief's mapping
table -- every column name already matches the old Mongo document's field
name 1:1 (scenario_id, section, domain, batch_number, scenario_title,
scenario_text, questions), so a plain row dict IS the old document shape;
no merge-back helper needed there either.
"""
from __future__ import annotations

from typing import List, Optional

from db_postgres import fetch_all


async def list_round1_by_section(section: str, tts_status: Optional[str] = None) -> List[dict]:
    """Mirrors `db.capgemini_round1_bank.find({"section": section[,
    "tts_status": tts_status]}, {"_id": 0}).to_list(None)` -- used for all
    six Round-1 sub-parts (grammar_correction, business_writing,
    situational_response, reading_comprehension, listening_comprehension,
    spoken_simulation). `tts_status` (Section 5's listening-clip readiness
    gate -- only clips with tts_status == "generated" may ever be served)
    is NOT a top-level column; it lives inside the jsonb `data` column
    (same place every other section-specific field for this bank lives),
    so filtering on it needs a `data->>'tts_status'` check rather than a
    plain column comparison."""
    params: list = [section]
    sql = "SELECT data FROM capgemini_round1_bank WHERE section = %s"
    if tts_status is not None:
        sql += " AND data->>'tts_status' = %s"
        params.append(tts_status)
    rows = await fetch_all(sql, params)
    return [r["data"] for r in rows]


async def list_round2_all() -> List[dict]:
    """Mirrors `db.capgemini_round2_bank.find({}, {"_id": 0}).to_list(None)`
    -- the whole pool (19 rows total per the inventory count), used for
    Round 2's AI Literacy section. No `data` merge needed -- every column
    already matches the old document's own field names."""
    rows = await fetch_all(
        "SELECT scenario_id, section, domain, batch_number, scenario_title, "
        "scenario_text, questions FROM capgemini_round2_bank"
    )
    return rows
