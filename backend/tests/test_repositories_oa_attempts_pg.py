"""Unit tests for repositories/oa_attempts_pg.py -- mocks fetch_all/
fetch_one/transaction directly (no real Postgres connection). Covers fix
#2 (the "already in progress" race): the pre-check path AND the actual
race-closing path (psycopg.errors.UniqueViolation caught on the INSERT
itself, turned into the same clean result), plus the answer-key
separation (oa_attempt_keys is never reachable via get_attempt/
list_attempts_for_user -- only the two explicitly-scoped functions touch
it)."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import psycopg
import pytest

from repositories import oa_attempts_pg as pg


class _FakeTxnCursor:
    def __init__(self, plan):
        self._plan = list(plan)
        self.executed = []
        self._last = None

    async def execute(self, sql, params=()):
        self.executed.append((sql, params))
        action = self._plan.pop(0)
        if isinstance(action, BaseException):
            raise action
        self._last = action

    async def fetchone(self):
        return self._last


def _patch_transaction(monkeypatch, plan):
    @asynccontextmanager
    async def fake_transaction():
        yield _FakeTxnCursor(plan)

    monkeypatch.setattr(pg, "transaction", fake_transaction)


def test_get_existing_in_progress_query_shape(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return None

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.get_existing_in_progress("u1", "tcs-nqt"))
    assert "status = 'in_progress'" in captured["sql"]
    assert captured["params"] == ("u1", "tcs-nqt")


def test_create_attempt_pre_check_returns_existing_without_opening_transaction(monkeypatch):
    existing = {"attempt_id": "oa_old", "status": "in_progress"}

    async def fake_fetch_one(sql, params=()):
        return existing

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)

    def fail_transaction():
        raise AssertionError("should not open a transaction when the pre-check already found one")

    monkeypatch.setattr(pg, "transaction", fail_transaction)

    result = asyncio.run(
        pg.create_attempt("oa_new", "u1", "tcs-nqt", "TCS", None, "weighted", [])
    )
    assert result == {"created": False, "attempt": existing}


def test_create_attempt_success_inserts_attempt_and_keys_in_one_transaction(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None  # pre-check: nothing in progress yet

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    inserted_row = {"attempt_id": "oa_new", "status": "in_progress"}
    _patch_transaction(monkeypatch, plan=[inserted_row, None])

    result = asyncio.run(
        pg.create_attempt("oa_new", "u1", "tcs-nqt", "TCS", "cluster1", "weighted", [{"key": "s1"}])
    )
    assert result == {"created": True, "attempt": inserted_row}


def test_create_attempt_race_caught_as_unique_violation_and_resolved_cleanly(monkeypatch):
    """The actual race-closing path: pre-check sees nothing, but the INSERT
    itself hits the partial unique index because another request won the
    race in between -- create_attempt must catch psycopg.errors.
    UniqueViolation (never let it propagate as a raw 500) and re-fetch the
    now-existing in-progress attempt instead."""
    call_count = {"n": 0}
    existing_after_race = {"attempt_id": "oa_winner", "status": "in_progress"}

    async def fake_fetch_one(sql, params=()):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None  # pre-check: nothing yet
        return existing_after_race  # post-exception re-fetch

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    _patch_transaction(monkeypatch, plan=[psycopg.errors.UniqueViolation("duplicate key")])

    result = asyncio.run(
        pg.create_attempt("oa_loser", "u1", "tcs-nqt", "TCS", None, "weighted", [])
    )
    assert result == {"created": False, "attempt": existing_after_race}
    assert call_count["n"] == 2


def test_get_attempt_scoped_and_unscoped(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"attempt_id": "oa1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.get_attempt("oa1", "u1"))
    assert "AND user_id = %s" in captured["sql"]
    assert captured["params"] == ("oa1", "u1")

    asyncio.run(pg.get_attempt("oa1"))
    # _COLUMNS still SELECTs user_id (it's a real column); only the WHERE
    # clause's ownership filter should be absent for the unscoped call.
    assert "AND user_id" not in captured["sql"]
    assert captured["params"] == ("oa1",)


def test_get_attempt_never_selects_oa_attempt_keys_columns(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        return {"attempt_id": "oa1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.get_attempt("oa1", "u1"))
    assert "oa_attempt_keys" not in captured["sql"]
    assert "answer_keys" not in captured["sql"]


def test_list_attempts_for_user(monkeypatch):
    captured = {}

    async def fake_fetch_all(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"attempt_id": "oa2"}, {"attempt_id": "oa1"}]

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    rows = asyncio.run(pg.list_attempts_for_user("u1", limit=20))
    assert len(rows) == 2
    assert "ORDER BY created_at DESC LIMIT %s" in captured["sql"]
    assert captured["params"] == ("u1", 20)


def test_update_attempt_progress_wraps_jsonb_fields(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"attempt_id": "oa1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.update_attempt_progress("oa1", status="completed", sections=[{"key": "s1"}]))
    assert "status = %s" in captured["sql"]
    assert "sections = %s" in captured["sql"]
    # sections value wrapped for jsonb adaptation, status passed straight through
    params = captured["params"]
    assert "completed" in params
    jsonb_params = [p for p in params if hasattr(p, "obj")]
    assert jsonb_params and jsonb_params[0].obj == [{"key": "s1"}]


def test_update_attempt_progress_noop_returns_current_attempt(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return {"attempt_id": "oa1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.update_attempt_progress("oa1"))
    assert row == {"attempt_id": "oa1"}


def test_set_and_get_hidden_answer_key_use_jsonb_path_ops(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"attempt_id": "oa1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    asyncio.run(pg.set_hidden_answer_key("oa1", "grid", "q1", {"answer": 3}))
    assert "jsonb_set(answer_keys" in captured["sql"]
    assert captured["params"][0] == ["grid", "q1"]
    assert captured["params"][1].obj == {"answer": 3}

    async def fake_fetch_one_get(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"key_data": {"answer": 3}}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one_get)
    value = asyncio.run(pg.get_hidden_answer_key("oa1", "grid", "q1"))
    assert value == {"answer": 3}
    assert "answer_keys #>" in captured["sql"]
    assert captured["params"] == (["grid", "q1"], "oa1")
