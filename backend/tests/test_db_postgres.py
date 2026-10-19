"""Unit tests for backend/db_postgres.py -- the Postgres connection layer.

No real Postgres connection is made anywhere in this file (SUPABASE_DB_URL is
not set in this dev environment yet -- see SUPABASE_MIGRATION_BRIEF.md's
"Database access" section). Pool construction is mocked out entirely so
these tests exercise db_postgres.py's own logic (pooler-mode detection,
lazy pool creation, the fetch_all/fetch_one query helpers) without touching
psycopg_pool's real networking.
"""
from __future__ import annotations

import asyncio

import pytest

import db_postgres


@pytest.fixture(autouse=True)
def _reset_pool_state():
    """Every test starts with no cached pool and no SUPABASE_DB_URL, and
    leaves none behind for the next test."""
    db_postgres.reset_pool_for_tests()
    yield
    db_postgres.reset_pool_for_tests()


# ---- port detection / pooler-mode handling ----------------------------------

@pytest.mark.parametrize(
    "conninfo,expected_port",
    [
        ("postgresql://user:pass@aws-0-ap-south-1.pooler.supabase.com:6543/postgres", 6543),
        ("postgresql://user:pass@aws-0-ap-south-1.pooler.supabase.com:5432/postgres", 5432),
        ("postgres://user:pass@db.example.com:6543/postgres?sslmode=require", 6543),
        ("host=db.example.com port=6543 dbname=postgres user=u password=p", 6543),
        ("host=db.example.com port=5432 dbname=postgres user=u password=p", 5432),
        ("host=db.example.com dbname=postgres user=u password=p", None),
    ],
)
def test_detect_port(conninfo, expected_port):
    assert db_postgres._detect_port(conninfo) == expected_port


def test_connect_kwargs_disables_prepared_statements_on_transaction_pooler():
    kwargs = db_postgres._connect_kwargs(
        "postgresql://u:p@host:6543/postgres"
    )
    assert kwargs["prepare_threshold"] is None
    assert kwargs["autocommit"] is True
    assert kwargs["row_factory"] is not None


def test_connect_kwargs_leaves_prepared_statements_on_for_session_pooler():
    kwargs = db_postgres._connect_kwargs(
        "postgresql://u:p@host:5432/postgres"
    )
    assert "prepare_threshold" not in kwargs
    assert kwargs["autocommit"] is True


# ---- get_pool() ---------------------------------------------------------------

def test_get_pool_raises_clear_error_when_env_var_missing(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="SUPABASE_DB_URL"):
        db_postgres.get_pool()


def test_get_pool_constructs_pool_with_detected_kwargs(monkeypatch):
    captured = {}

    class _FakePool:
        def __init__(self, conninfo, **kwargs):
            captured["conninfo"] = conninfo
            captured["kwargs"] = kwargs
            self.closed = True

    monkeypatch.setattr(db_postgres, "AsyncConnectionPool", _FakePool)
    monkeypatch.setenv(
        "SUPABASE_DB_URL", "postgresql://u:p@host:6543/postgres"
    )
    pool = db_postgres.get_pool()
    assert isinstance(pool, _FakePool)
    assert captured["conninfo"] == "postgresql://u:p@host:6543/postgres"
    # AsyncConnectionPool(conninfo, kwargs={...per-connection connect
    # kwargs...}, min_size=..., ...) -- "kwargs" here is the pool
    # constructor's own `kwargs=` parameter, forwarded to each
    # connection's connect() call.
    assert captured["kwargs"]["kwargs"]["prepare_threshold"] is None


def test_get_pool_is_a_singleton(monkeypatch):
    class _FakePool:
        def __init__(self, conninfo, **kwargs):
            self.closed = True

    monkeypatch.setattr(db_postgres, "AsyncConnectionPool", _FakePool)
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://u:p@host:5432/postgres")
    first = db_postgres.get_pool()
    second = db_postgres.get_pool()
    assert first is second


# ---- fetch_all / fetch_one ----------------------------------------------------

class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed = []

    async def execute(self, sql, params):
        self.executed.append((sql, tuple(params)))

    async def fetchall(self):
        return self._rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows
        self.cursors = []

    def cursor(self):
        cur = _FakeCursor(self._rows)
        self.cursors.append(cur)
        return cur

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakePool:
    def __init__(self, rows):
        self._rows = rows
        self.conns = []

    def connection(self):
        conn = _FakeConn(self._rows)
        self.conns.append(conn)
        return conn


def test_fetch_all_returns_rows_and_passes_through_params(monkeypatch):
    fake_pool = _FakePool(rows=[{"a": 1}, {"a": 2}])
    monkeypatch.setattr(db_postgres, "get_pool", lambda: fake_pool)
    rows = asyncio.run(db_postgres.fetch_all("SELECT a FROM t WHERE b = %s", (5,)))
    assert rows == [{"a": 1}, {"a": 2}]
    executed_sql, executed_params = fake_pool.conns[0].cursors[0].executed[0]
    assert executed_sql == "SELECT a FROM t WHERE b = %s"
    assert executed_params == (5,)


def test_fetch_one_returns_first_row_or_none(monkeypatch):
    fake_pool = _FakePool(rows=[{"a": 1}, {"a": 2}])
    monkeypatch.setattr(db_postgres, "get_pool", lambda: fake_pool)
    row = asyncio.run(db_postgres.fetch_one("SELECT a FROM t"))
    assert row == {"a": 1}

    empty_pool = _FakePool(rows=[])
    monkeypatch.setattr(db_postgres, "get_pool", lambda: empty_pool)
    row = asyncio.run(db_postgres.fetch_one("SELECT a FROM t WHERE false"))
    assert row is None
