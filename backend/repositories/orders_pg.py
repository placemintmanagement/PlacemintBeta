"""Postgres access for `orders` -- mirrors the `db.orders` call sites in
backend/server.py: POST /payments/order's insert (~6887-6938) and
POST /payments/verify's find + paid-status update (~6948-7004). NOT wired
into those routes in this phase (payments cutover is phase 5, per the
migration brief's suggested order of work) -- this module is built and
tested in isolation only.

Surprise worth flagging (see phase report): the real Mongo order document
has TWO different order ids -- the app-minted `order_id` (`new_id(
"order")`, server.py ~6898) used as the row's own key everywhere
(`/payments/verify`'s lookup, the one the frontend is given back), and a
SEPARATE `razorpay_order_id` (Razorpay's own id for the order, returned by
`_razorpay_client.order.create(...)` or mocked as `order_mock_<hex>`).
schema.sql's `orders` table comment claims `order_id` IS "the Razorpay
order id itself", which doesn't match the app's actual behavior -- the app
never uses Razorpay's order id as its primary key. create_order below
takes the app-minted order_id as the primary key (matching real behavior,
not the column comment's assumption) and keeps `razorpay_order_id` inside
the jsonb `data` column alongside amount/currency/plan_id/credit_pack_id/
mock -- schema-compatible either way since `data` absorbs the extra field,
but the column's own comment is stale against the real call site.

Fix (the idempotent-crediting requirement): mark_paid uses a single
`UPDATE ... WHERE order_id = %s AND status != 'paid' RETURNING *` --
zero rows back means this order was already paid, and the caller must
treat that as a no-op (same success response, no second credit/plan
grant) rather than relying on an app-level `if order["status"] ==
"paid": return` check alone (which is what server.py:6970's "Signature
verification failed" gate and a naive retry-guard would otherwise be
tempted to do, non-atomically, with a read-then-write race between the
check and the grant)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from psycopg.types.json import Jsonb

from db_postgres import fetch_one

_COLUMNS = (
    "order_id, user_id, kind, status, razorpay_payment_id, created_at, "
    "paid_at, data"
)


async def create_order(order_id: str, user_id: str, kind: str, data: Dict[str, Any]) -> dict:
    """Mirrors `db.orders.insert_one(doc)` (server.py ~6919-6932). `kind`
    is `"plan"` or `"credits"` (schema.sql's own `kind` column comment);
    `data` carries everything else the Mongo doc had (razorpay_order_id,
    plan_id/credit_pack_id, amount, currency, mock) -- see this module's
    docstring for why razorpay_order_id lives in `data` rather than being
    the primary key."""
    row = await fetch_one(
        "INSERT INTO orders (order_id, user_id, kind, data) VALUES (%s, %s, %s, %s) "
        f"RETURNING {_COLUMNS}",
        (order_id, user_id, kind, Jsonb(data)),
    )
    assert row is not None
    return row


async def get_order(order_id: str, user_id: str) -> Optional[dict]:
    """Mirrors `db.orders.find_one({"order_id": ..., "user_id": ...},
    {"_id": 0})` (server.py ~6950) -- ownership-scoped."""
    return await fetch_one(
        f"SELECT {_COLUMNS} FROM orders WHERE order_id = %s AND user_id = %s",
        (order_id, user_id),
    )


async def mark_paid(order_id: str, razorpay_payment_id: str) -> Optional[dict]:
    """Idempotent-crediting fix: mirrors server.py:7001-7004's `db.orders.
    update_one({"order_id": ...}, {"$set": {"status": "paid",
    "razorpay_payment_id": ..., "paid_at": ...}})`, but as one atomic,
    status-checked statement. Returns the updated row, or None if this
    order was already `status = 'paid'` -- callers MUST treat None as "this
    was already credited, return the same success response without
    granting credits/plan again", not call this and separately check
    status. The `razorpay_payment_id` column's UNIQUE constraint
    (schema.sql) is the DB-level half of the guarantee (a payment can never
    attach to two different orders); this WHERE clause is the app-level
    half (a retried verify call on the SAME already-paid order is a
    genuine no-op)."""
    return await fetch_one(
        "UPDATE orders SET status = 'paid', razorpay_payment_id = %s, paid_at = now() "
        f"WHERE order_id = %s AND status != 'paid' RETURNING {_COLUMNS}",
        (razorpay_payment_id, order_id),
    )
