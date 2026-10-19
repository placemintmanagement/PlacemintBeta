"""Postgres access for `profiles` -- mirrors the `db.users` call sites in
backend/server.py that survive the Auth0 -> Supabase Auth cutover (see
SUPABASE_MIGRATION_BRIEF.md's collection->table mapping: `users` ->
`profiles`, `id` is the Supabase auth user uuid, auth0_sub/auth_provider/
password_hash/email_verified/user_id are dropped). The legacy auth routes
(/auth/signup, /auth/login, /auth/google/session, /auth/logout, the email
verify/reset flow) are NOT ported here -- the brief marks them for deletion,
not porting, since Supabase Auth replaces them natively. Nothing below
touches `auth.users` itself; a profile row is created automatically by the
`handle_new_user()` trigger in schema.sql the moment someone signs up.

Three functions here are the migration's required correctness fixes, not
faithful 1:1 ports of the Mongo call sites they mirror:

  * deduct_credit -- server.py:2083's `db.users.update_one({"user_id":...},
    {"$inc": {"credits": -1}})` has no floor check at the DB level, a real
    double-spend race under concurrent requests. Ported as a single atomic
    `UPDATE ... WHERE credits > 0 RETURNING credits` -- zero rows back means
    "no credits available", never decrement-then-check.
  * add_company_selection -- server.py:2088's `{"$addToSet": {
    "company_selections": company["id"]}}` becomes one atomic statement
    (array(select distinct unnest(...))), not a read-modify-write.
  * maybe_reset_period -- the exact rollover rule is
    backend/core/entitlements.py's own maybe_reset_period/_in_current_window
    (confirmed by reading that module, not guessed): only plans with a
    truthy `resets_every_days` in PLAN_LIMITS (today: basic, pro, both 30)
    ever roll over; the window is considered elapsed, and due for a reset,
    when `runs_period_start` is unset OR `now - runs_period_start >= `
    resets_every_days` days. On rollover: `runs_used = 0`,
    `runs_period_start = now()`. This module reuses entitlements.py's own
    PLAN_LIMITS/_in_current_window directly (pure Python, no Mongo
    dependency) rather than re-deriving the rule, so the two can never
    drift apart.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core import entitlements
from db_postgres import fetch_all, fetch_one

_COLUMNS = (
    "id, name, picture_url, college, branch, graduation_year, target_role, "
    "company_selections, plan, plan_started_at, plan_expires_at, credits, "
    "runs_quota, runs_used, runs_period_start, is_internal_tester, created_at"
)

# Onboarding fields update_profile (server.py's PATCH /auth/profile) is
# allowed to touch. `name` is included because ProfileIn carries it too;
# company_selections is deliberately NOT in this whitelist -- it has its
# own atomic add_company_selection/remove path (server.py's
# POST /user/company-selection does a full read-modify-write replace
# today, which is fine for cap+swap logic since it's gated by the same
# request's own cap check, but the brief calls out `$addToSet` specifically
# as needing an atomic port -- see add_company_selection below).
_ONBOARDING_FIELDS = ("college", "branch", "graduation_year", "target_role", "name")


async def get_profile(user_id: str) -> Optional[dict]:
    """Mirrors `db.users.find_one({"user_id": user_id}, {"_id": 0, ...})`
    (server.py's /auth/me and every `require_user`-style lookup). `user_id`
    here is the Supabase auth uuid (profiles.id), not the old Mongo
    `user_id` string field -- that field is dropped per the migration
    brief."""
    return await fetch_one(f"SELECT {_COLUMNS} FROM profiles WHERE id = %s", (user_id,))


async def upsert_onboarding_fields(user_id: str, **fields: Any) -> Optional[dict]:
    """Mirrors PATCH /auth/profile (server.py:717-723): `db.users.update_one(
    {"user_id": ...}, {"$set": updates})` where `updates` is whichever of
    college/branch/graduation_year/target_role/name was actually provided.
    Only known onboarding fields are accepted (unknown kwargs are dropped,
    not silently written) -- a profile row always already exists by the
    time a caller reaches here (created by the on-signup trigger), so this
    is a plain UPDATE, never an upsert against a missing row. Returns the
    fresh row, or None if no recognized field was given (no-op, matching
    the Mongo code's own `if updates:` guard)."""
    updates = {k: v for k, v in fields.items() if k in _ONBOARDING_FIELDS and v is not None}
    if not updates:
        return await get_profile(user_id)
    set_clause = ", ".join(f"{col} = %s" for col in updates)
    params: List[Any] = list(updates.values()) + [user_id]
    return await fetch_one(
        f"UPDATE profiles SET {set_clause} WHERE id = %s RETURNING {_COLUMNS}",
        params,
    )


async def deduct_credit(user_id: str) -> Optional[int]:
    """Fix #1 (race): mirrors server.py:2083's credit-deduction `$inc`, but
    as one atomic, floor-checked statement instead of Mongo's unconditional
    decrement. Returns the new credit balance, or None if the user had zero
    (or fewer -- defensive) credits -- callers MUST treat None as "no
    credits available", not call this and then separately check the
    balance."""
    row = await fetch_one(
        "UPDATE profiles SET credits = credits - 1 WHERE id = %s AND credits > 0 "
        "RETURNING credits",
        (user_id,),
    )
    return row["credits"] if row else None


async def increment_credits(user_id: str, amount: int) -> Optional[int]:
    """Mirrors server.py:6996-6999's credit-pack grant (`$inc` with a
    positive amount) -- no floor concern in this direction, straightforward
    atomic increment. Returns the new balance."""
    row = await fetch_one(
        "UPDATE profiles SET credits = credits + %s WHERE id = %s RETURNING credits",
        (amount, user_id),
    )
    return row["credits"] if row else None


async def set_plan(
    user_id: str,
    plan: str,
    runs_quota: Optional[int] = None,
    plan_started_at: Optional[str] = None,
    plan_expires_at: Optional[str] = None,
) -> Optional[dict]:
    """Mirrors server.py:6982-6992's plan-purchase grant: `plan`,
    `runs_used = 0`, `plan_started_at`, `runs_period_start` (reset to now,
    same moment as plan_started_at -- a fresh plan always starts a fresh
    30-day window), and `plan_expires_at` (explicitly set to NULL for
    non-expiring plans, matching the Mongo code's own
    `else: update_set["plan_expires_at"] = None` branch, not just omitted).
    `runs_quota` is persisted too (schema.sql column; the Mongo code kept
    the per-plan limit in PLAN_LIMITS rather than a per-user column, but
    the new schema has the column so a caller that wants to stamp it can)."""
    return await fetch_one(
        "UPDATE profiles SET plan = %s, runs_used = 0, runs_period_start = %s, "
        "plan_started_at = %s, plan_expires_at = %s, "
        "runs_quota = COALESCE(%s, runs_quota) "
        f"WHERE id = %s RETURNING {_COLUMNS}",
        (plan, plan_started_at, plan_started_at, plan_expires_at, runs_quota, user_id),
    )


async def maybe_reset_period(user_id: str) -> Optional[dict]:
    """Mirrors server.py's repeated `reset_op = entitlements.
    maybe_reset_period(user); if reset_op: await db.users.update_one(...)`
    dance (GET /auth/me and /oa/start, at least) -- rolls the Basic/Pro
    30-day window forward exactly when entitlements.maybe_reset_period's own
    rule says to (see this module's docstring for the rule itself, copied
    verbatim from backend/core/entitlements.py, not re-derived). Fetches
    the profile itself (so callers don't have to pass plan/runs_period_start
    in by hand), reuses entitlements.maybe_reset_period/_in_current_window
    against that row, and -- only if a reset is actually due -- applies it
    as one atomic UPDATE. Returns the fresh profile row if a reset happened,
    or None if no reset was due (caller keeps using whatever profile row it
    already has)."""
    profile = await get_profile(user_id)
    if profile is None:
        return None
    reset_op = entitlements.maybe_reset_period(profile)
    if not reset_op:
        return None
    new_period_start = reset_op["$set"]["runs_period_start"]
    return await fetch_one(
        "UPDATE profiles SET runs_used = 0, runs_period_start = %s "
        f"WHERE id = %s RETURNING {_COLUMNS}",
        (new_period_start, user_id),
    )


async def add_company_selection(user_id: str, company_id: str) -> List[str]:
    """Fix (the `$addToSet` -> atomic-array pattern the brief calls out):
    mirrors server.py:2088's `{"$addToSet": {"company_selections":
    company["id"]}}` -- one atomic statement rather than a read-then-write
    (fetch selections, append in Python, write back), so two concurrent
    "first run on company X" requests for the same user can't race each
    other into writing an array missing one of the two companies. Uses a
    `CASE` so a company already present is a true no-op (array unchanged,
    not re-appended) -- Postgres `array_append` has no built-in dedup.
    Returns the resulting company_selections array."""
    row = await fetch_one(
        "UPDATE profiles SET company_selections = "
        "CASE WHEN %s = ANY(company_selections) THEN company_selections "
        "ELSE array_append(company_selections, %s) END "
        "WHERE id = %s RETURNING company_selections",
        (company_id, company_id, user_id),
    )
    return row["company_selections"] if row else []


async def remove_company_selection(user_id: str, company_id: str) -> List[str]:
    """Mirrors server.py's POST /user/company-selection `remove` branch
    (the swap-out half of the same endpoint add_company_selection's
    docstring describes) -- one atomic statement, same spirit as
    add_company_selection. Returns the resulting company_selections array."""
    row = await fetch_one(
        "UPDATE profiles SET company_selections = "
        "array_remove(company_selections, %s) WHERE id = %s "
        "RETURNING company_selections",
        (company_id, user_id),
    )
    return row["company_selections"] if row else []
