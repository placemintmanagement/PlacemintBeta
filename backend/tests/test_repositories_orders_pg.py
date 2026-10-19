"""Unit tests for repositories/orders_pg.py -- mocks fetch_one directly.
Covers the idempotent-crediting fix: mark_paid's single, status-checked
UPDATE, and the None-means-already-paid contract."""
from __future__ import annotations

import asyncio

from repositories import orders_pg as pg


def test_create_order_wraps_data_as_jsonb(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"order_id": "order_1", "status": "created"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(
        pg.create_order("order_1", "u1", "credits", {"razorpay_order_id": "rzp_1", "amount": 4900})
    )
    assert row["status"] == "created"
    assert captured["params"][:3] == ("order_1", "u1", "credits")
    assert captured["params"][-1].obj == {"razorpay_order_id": "rzp_1", "amount": 4900}


def test_get_order_is_ownership_scoped(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"order_id": "order_1", "user_id": "u1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.get_order("order_1", "u1"))
    assert row["order_id"] == "order_1"
    assert "order_id = %s AND user_id = %s" in captured["sql"]


def test_mark_paid_atomic_status_checked_sql(monkeypatch):
    captured = {}

    async def fake_fetch_one(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return {"order_id": "order_1", "status": "paid", "razorpay_payment_id": "pay_1"}

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    row = asyncio.run(pg.mark_paid("order_1", "pay_1"))
    assert row["status"] == "paid"
    assert "status = 'paid'" in captured["sql"]
    assert "status != 'paid'" in captured["sql"]
    assert "paid_at = now()" in captured["sql"]
    assert captured["params"] == ("pay_1", "order_1")


def test_mark_paid_returns_none_when_already_paid_idempotent_retry(monkeypatch):
    async def fake_fetch_one(sql, params=()):
        return None  # WHERE status != 'paid' matched zero rows -- already paid

    monkeypatch.setattr(pg, "fetch_one", fake_fetch_one)
    result = asyncio.run(pg.mark_paid("order_1", "pay_1_retry"))
    assert result is None
