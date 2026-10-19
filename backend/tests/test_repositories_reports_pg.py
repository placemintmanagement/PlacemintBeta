"""Unit tests for repositories/reports_pg.py -- mocks fetch_all/fetch_one/
transaction directly. Covers fix #3: finish_interview wraps the turn-count
-guarded interview update + report invalidation (by interview_id, and by
attempt_id when present) in ONE transaction, and replace_cached_report is
a literal delete-then-insert single-transaction primitive."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from repositories import reports_pg as pg


class _FakeTxnCursor:
    def __init__(self, plan):
        self._plan = list(plan)
        self.executed = []
        self._last = None

    async def execute(self, sql, params=()):
        self.executed.append((sql, params))
        self._last = self._plan.pop(0)

    async def fetchone(self):
        return self._last


def _patch_transaction(monkeypatch, plan):
    cur_holder = {}

    @asynccontextmanager
    async def fake_transaction():
        cur = _FakeTxnCursor(plan)
        cur_holder["cur"] = cur
        yield cur

    monkeypatch.setattr(pg, "transaction", fake_transaction)
    return cur_holder


def test_get_cached_report_by_attempt_id(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"report_id": "rep1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.get_cached_report("u1", attempt_id="oa1"))
    assert row == {"report_id": "rep1"}
    assert "attempt_id = %s AND user_id = %s" in captured["sql"]


def test_get_cached_report_by_interview_id_joins_through_interviews(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"report_id": "rep1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.get_cached_report("u1", interview_id="intv1"))
    assert row == {"report_id": "rep1"}
    assert "JOIN interviews" in captured["sql"]
    assert "i.interview_id = %s" in captured["sql"]


def test_insert_report(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"report_id": "rep1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    doc = {
        "report_id": "rep1", "user_id": "u1", "company_name": "TCS", "attempt_id": "oa1",
        "created_at": "2026-01-01T00:00:00+00:00", "oa_summary": {"verdict": "ready"},
        "interview_summary": {}, "resume_analysis": {}, "report": {"narrative": "..."},
    }
    row = asyncio.run(pg.insert_report(doc))
    assert row == {"report_id": "rep1"}
    assert "INSERT INTO reports" in captured["sql"]


def test_invalidate_reports_deletes_by_interview_and_attempt(monkeypatch):
    calls = []

    async def fake_fetch_all(sql, params=()):
        calls.append((sql, params))
        return []

    monkeypatch.setattr(pg, "fetch_all", fake_fetch_all)
    asyncio.run(pg.invalidate_reports("u1", interview_id="intv1", attempt_id="oa1"))
    assert len(calls) == 2
    assert "interview_id = %s" in calls[0][0]
    assert "attempt_id = %s AND user_id = %s" in calls[1][0]


def test_finish_interview_commits_update_and_both_deletes_in_one_transaction(monkeypatch):
    updated_interview_row = {"interview_id": "intv1", "attempt_id": "oa1", "status": "completed"}
    cur_holder = _patch_transaction(monkeypatch, plan=[updated_interview_row, None, None])

    result = asyncio.run(
        pg.finish_interview(
            "intv1", expected_turn_count=5,
            changes={"status": "completed", "turn_count": 6},
            user_id="u1", attempt_id="oa1",
        )
    )
    assert result == {"interview": updated_interview_row, "stale_turn": False}
    cur = cur_holder["cur"]
    assert len(cur.executed) == 3  # interview update + 2 deletes (by interview_id, by attempt_id)
    assert "UPDATE interviews" in cur.executed[0][0]
    assert "(data->>'turn_count') = %s" in cur.executed[0][0]
    assert "DELETE FROM reports" in cur.executed[1][0]
    assert "interview_id" in cur.executed[1][0]
    assert "attempt_id = %s AND user_id = %s" in cur.executed[2][0]


def test_finish_interview_skips_attempt_delete_when_no_attempt_id(monkeypatch):
    updated_interview_row = {"interview_id": "intv2", "attempt_id": None, "status": "completed"}
    cur_holder = _patch_transaction(monkeypatch, plan=[updated_interview_row, None])

    result = asyncio.run(
        pg.finish_interview(
            "intv2", expected_turn_count=0, changes={"status": "completed"}, user_id="u1", attempt_id=None,
        )
    )
    assert result["stale_turn"] is False
    cur = cur_holder["cur"]
    assert len(cur.executed) == 2  # interview update + 1 delete (no attempt_id delete)


def test_finish_interview_stale_turn_returns_none_and_skips_deletes(monkeypatch):
    cur_holder = _patch_transaction(monkeypatch, plan=[None])  # UPDATE matched nothing

    result = asyncio.run(
        pg.finish_interview(
            "intv1", expected_turn_count=99, changes={"status": "completed"}, user_id="u1", attempt_id="oa1",
        )
    )
    assert result == {"interview": None, "stale_turn": True}
    cur = cur_holder["cur"]
    assert len(cur.executed) == 1  # only the UPDATE ran -- no deletes on a stale/failed guard


def test_replace_cached_report_deletes_then_inserts_in_one_transaction(monkeypatch):
    inserted_row = {"report_id": "rep_new"}
    cur_holder = _patch_transaction(monkeypatch, plan=[None, inserted_row])

    doc = {
        "report_id": "rep_new", "user_id": "u1", "company_name": "TCS", "attempt_id": "oa1",
        "created_at": "2026-02-01T00:00:00+00:00", "oa_summary": {}, "interview_summary": {},
        "resume_analysis": {}, "report": {},
    }
    row = asyncio.run(pg.replace_cached_report({"attempt_id": "oa1", "user_id": "u1"}, doc))
    assert row == inserted_row
    cur = cur_holder["cur"]
    assert len(cur.executed) == 2
    assert cur.executed[0][0].startswith("DELETE FROM reports")
    assert cur.executed[1][0].startswith("INSERT INTO reports")
