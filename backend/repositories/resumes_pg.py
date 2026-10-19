"""Postgres access for `resumes` -- mirrors the `db.resumes` call sites in
backend/server.py (search `db.resumes.` there): the resume-upload insert
(~line 923), ownership-scoped fetch by id (~930, 1970), the per-user list
sorted newest-first (~938, 6837), the per-(user, company) list that backs
`_latest_resume_for_company` (~3750), and the bare by-id lookup used only
for its `analysis` field when building a final report (~6705).
"""
from __future__ import annotations

from typing import List, Optional

from psycopg.types.json import Jsonb

from db_postgres import fetch_all, fetch_one

_COLUMNS = (
    "resume_id, user_id, company_id, role, resume_text_sample, analysis, created_at"
)


async def insert_resume(
    resume_id: str,
    user_id: str,
    company_id: Optional[str],
    role: Optional[str],
    resume_text_sample: Optional[str],
    analysis: Optional[dict],
) -> dict:
    """Mirrors `db.resumes.insert_one(doc)` (server.py ~line 923) -- resume
    analysis is generated up front and stored whole, never updated in
    place afterwards (every later read is a plain fetch), so a single
    INSERT is the complete port, no upsert/merge needed."""
    row = await fetch_one(
        "INSERT INTO resumes (resume_id, user_id, company_id, role, "
        "resume_text_sample, analysis) VALUES (%s, %s, %s, %s, %s, %s) "
        f"RETURNING {_COLUMNS}",
        (resume_id, user_id, company_id, role, resume_text_sample, Jsonb(analysis) if analysis is not None else None),
    )
    assert row is not None
    return row


async def get_resume(resume_id: str, user_id: str) -> Optional[dict]:
    """Mirrors `db.resumes.find_one({"resume_id": ..., "user_id": ...},
    {"_id": 0})` (server.py ~930, ~1970) -- ownership-scoped; a resume_id
    that exists but belongs to another user returns None, same as Mongo's
    filtered find_one."""
    return await fetch_one(
        f"SELECT {_COLUMNS} FROM resumes WHERE resume_id = %s AND user_id = %s",
        (resume_id, user_id),
    )


async def get_resume_by_id(resume_id: str) -> Optional[dict]:
    """Mirrors the unscoped `db.resumes.find_one({"resume_id": resume_id},
    {"_id": 0})` used only internally when building a final report
    (server.py ~6705) to read back `analysis` for whichever resume an
    attempt/interview already recorded as its own `resume_id` -- ownership
    was already established when that resume_id was attached to the
    attempt/interview, so no extra user_id filter is applied here, matching
    the real call site."""
    return await fetch_one(f"SELECT {_COLUMNS} FROM resumes WHERE resume_id = %s", (resume_id,))


async def get_resumes_for_user(user_id: str, limit: int = 50) -> List[dict]:
    """Mirrors `db.resumes.find({"user_id": ...}, {"_id": 0}).sort(
    "created_at", -1).to_list(50)` (server.py ~938) -- the resume-picker
    list. A second call site (~6837) uses `.to_list(20)`, hence the
    `limit` parameter rather than a hardcoded 50."""
    return await fetch_all(
        f"SELECT {_COLUMNS} FROM resumes WHERE user_id = %s "
        "ORDER BY created_at DESC LIMIT %s",
        (user_id, limit),
    )


async def get_latest_resume_for_company(user_id: str, company_id: str) -> Optional[dict]:
    """Mirrors `_latest_resume_for_company` (server.py ~3744-3753): the
    OA/interview auto-fallback helper used when a caller doesn't supply an
    explicit resume_id. The Mongo version fetches up to 100 matching docs
    and picks `max(docs, key=lambda d: d.get("created_at") or "")` in
    Python; the Postgres equivalent is the same selection expressed as a
    single query -- most recent by created_at, `ORDER BY created_at DESC
    LIMIT 1` -- not a re-implementation of a different rule."""
    return await fetch_one(
        f"SELECT {_COLUMNS} FROM resumes WHERE user_id = %s AND company_id = %s "
        "ORDER BY created_at DESC LIMIT 1",
        (user_id, company_id),
    )
