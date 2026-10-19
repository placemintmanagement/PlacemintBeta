"""Unit tests for repositories/profiles_pg.py -- mocks fetch_all/fetch_one
directly (no real Postgres connection). Covers fix #1 (atomic, floor-
checked credit deduction) and the maybe_reset_period rollover rule ported
from backend/core/entitlements.py."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from repositories import profiles_pg as pg


def test_get_profile_queries_by_id(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"id": "u1", "credits": 3}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.get_profile("u1"))
    assert row == {"id": "u1", "credits": 3}
    assert "WHERE id = %s" in captured["sql"]
    assert captured["params"] == ("u1",)


def test_upsert_onboarding_fields_only_known_fields(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"id": "u1", "college": "X"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.upsert_onboarding_fields("u1", college="X", bogus_field="nope", target_role=None))
    assert "college = %s" in captured["sql"]
    assert "bogus_field = %s" not in captured["sql"]
    assert "target_role = %s" not in captured["sql"]  # None is dropped, not written
    # _COLUMNS still SELECTs target_role in the RETURNING clause (it's a
    # real column), so only the SET-clause assignment is checked above, not
    # a blanket substring search for the column name.
    assert captured["params"] == ["X", "u1"]


def test_upsert_onboarding_fields_noop_returns_profile(monkeypatch):
    calls = {"get_profile": 0}

    async def fake_get_profile(user_id):
        calls["get_profile"] += 1
        return {"id": user_id}

    monkeypatch.setattr(pg, "get_profile", fake_get_profile)
    row = asyncio.run(pg.upsert_onboarding_fields("u1"))
    assert row == {"id": "u1"}
    assert calls["get_profile"] == 1


def test_deduct_credit_atomic_floor_checked_sql(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"credits": 2}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    new_balance = asyncio.run(pg.deduct_credit("u1"))
    assert new_balance == 2
    assert "credits = credits - 1" in captured["sql"]
    assert "credits > 0" in captured["sql"]
    assert "RETURNING credits" in captured["sql"]
    assert captured["params"] == ("u1",)


def test_deduct_credit_returns_none_when_zero_rows(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None  # zero credits -- UPDATE matched nothing

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    assert asyncio.run(pg.deduct_credit("u1")) is None


def test_increment_credits_adds_amount(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"credits": 8}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    assert asyncio.run(pg.increment_credits("u1", 5)) == 8
    assert "credits = credits + %s" in captured["sql"]
    assert captured["params"] == (5, "u1")


def test_set_plan_sets_null_expiry_for_non_expiring_plan(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"id": "u1", "plan": "max"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.set_plan("u1", "max", plan_started_at="2026-01-01T00:00:00+00:00", plan_expires_at=None))
    assert captured["params"][0] == "max"
    assert captured["params"][-2] is None  # runs_quota not given
    assert captured["params"][-1] == "u1"


def test_add_company_selection_case_when_already_present_is_noop_sql(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"company_selections": ["tcs", "infosys"]}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    result = asyncio.run(pg.add_company_selection("u1", "infosys"))
    assert result == ["tcs", "infosys"]
    assert "CASE WHEN %s = ANY(company_selections)" in captured["sql"]
    assert "array_append(company_selections, %s)" in captured["sql"]
    assert captured["params"] == ("infosys", "infosys", "u1")


def test_add_company_selection_returns_empty_when_no_row(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    assert asyncio.run(pg.add_company_selection("ghost", "tcs")) == []


def test_remove_company_selection_uses_array_remove(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"company_selections": []}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    result = asyncio.run(pg.remove_company_selection("u1", "tcs"))
    assert result == []
    assert "array_remove(company_selections, %s)" in captured["sql"]
    assert captured["params"] == ("tcs", "u1")


# ---- maybe_reset_period: the rollover rule, exactly as found in
# backend/core/entitlements.py (maybe_reset_period/_in_current_window) ----

def test_maybe_reset_period_noop_for_free_plan(monkeypatch):
    async def fake_get_profile(user_id):
        return {"plan": "free", "runs_used": 5, "runs_period_start": None}

    monkeypatch.setattr(pg, "get_profile", fake_get_profile)
    assert asyncio.run(pg.maybe_reset_period("u1")) is None


def test_maybe_reset_period_noop_when_still_inside_30_day_window(monkeypatch):
    recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

    async def fake_get_profile(user_id):
        return {"plan": "basic", "runs_used": 3, "runs_period_start": recent}

    monkeypatch.setattr(pg, "get_profile", fake_get_profile)
    assert asyncio.run(pg.maybe_reset_period("u1")) is None


def test_maybe_reset_period_resets_when_window_has_elapsed(monkeypatch):
    stale = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    captured = {}

    async def fake_get_profile(user_id):
        return {"plan": "pro", "runs_used": 20, "runs_period_start": stale}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"plan": "pro", "runs_used": 0, "runs_period_start": params[0]}

    monkeypatch.setattr(pg, "get_profile", fake_get_profile)
    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.maybe_reset_period("u1"))
    assert row["runs_used"] == 0
    assert "runs_used = 0" in captured["sql"]
    assert "runs_period_start = %s" in captured["sql"]


def test_maybe_reset_period_resets_when_runs_period_start_never_set(monkeypatch):
    """_in_current_window returns False (not True) when runs_period_start
    is unset on a resetting plan -- confirmed against entitlements.py's own
    `if not start: return False` -- so a Basic/Pro user who has never had
    the field set is due for a reset too, not treated as "in window"."""
    captured = {}

    async def fake_get_profile(user_id):
        return {"plan": "basic", "runs_used": 0, "runs_period_start": None}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        return {"plan": "basic", "runs_used": 0}

    monkeypatch.setattr(pg, "get_profile", fake_get_profile)
    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.maybe_reset_period("u1"))
    assert row is not None
    assert "runs_used = 0" in captured["sql"]


def test_maybe_reset_period_none_when_profile_missing(monkeypatch):
    async def fake_get_profile(user_id):
        return None

    monkeypatch.setattr(pg, "get_profile", fake_get_profile)
    assert asyncio.run(pg.maybe_reset_period("ghost")) is None
