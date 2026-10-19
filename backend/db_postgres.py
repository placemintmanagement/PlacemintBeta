"""Postgres (Supabase) connection layer -- additive, isolated from the live
Mongo path. Nothing in server.py imports this yet; this module exists so the
repository layer (backend/repositories/) has one place to get a pooled
connection, instead of each repository module opening its own.

Why psycopg 3 + psycopg_pool (not asyncpg): the migration brief calls out
psycopg 3's async pool as the first-listed option, and it gives us dict-row
results and automatic jsonb<->dict (de)serialization for free, both of which
the content-bank repositories below lean on heavily (several banks store
their type-specific fields in a jsonb `data` column that has to come back
out as a plain dict).

Supabase pooler modes: the Session pooler (port 5432) behaves like a normal
Postgres connection and supports server-side prepared statements. The
Transaction pooler (port 6543) multiplexes transactions across physical
connections, so a prepared statement from one logical "session" can land on
a different backend next time -- psycopg must be told not to prepare
statements at all (`prepare_threshold=None`) when talking to that pooler, or
queries will intermittently fail against it. We detect the port from
SUPABASE_DB_URL and flip that setting automatically so callers don't have to
know which pooler they're pointed at.
"""
from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, List, Optional, Sequence
from urllib.parse import urlsplit

from psycopg import AsyncCursor
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

TRANSACTION_POOLER_PORT = 6543

_pool: Optional[AsyncConnectionPool] = None


def _detect_port(conninfo: str) -> Optional[int]:
    """Best-effort port extraction from a Postgres connection string. Supports
    both URI form (postgresql://user:pass@host:6543/db) and keyword=value
    form (host=... port=6543 ...) -- Supabase's own "connection string" copy
    buttons can hand out either, depending on which one the product owner
    copies from the dashboard."""
    try:
        parsed = urlsplit(conninfo)
        if parsed.scheme in ("postgres", "postgresql") and parsed.port:
            return parsed.port
    except ValueError:
        pass
    m = re.search(r"\bport\s*=\s*'?(\d+)'?", conninfo)
    if m:
        return int(m.group(1))
    return None


def _connect_kwargs(conninfo: str) -> dict:
    kwargs: dict = {"autocommit": True, "row_factory": dict_row}
    if _detect_port(conninfo) == TRANSACTION_POOLER_PORT:
        # Transaction pooler: server-side prepared statements are not safe
        # (see module docstring) -- disable them for every connection this
        # pool opens.
        kwargs["prepare_threshold"] = None
    return kwargs


def get_pool() -> AsyncConnectionPool:
    """Returns the process-wide pool, creating it (opened lazily, not at
    construction time -- avoids psycopg_pool's "pool opened in constructor"
    deprecation warning and lets this module be imported even in a process
    that never ends up using Postgres) on first call.

    Raises RuntimeError with a clear message if SUPABASE_DB_URL isn't set --
    callers should let that surface rather than silently falling back to
    anything Mongo-shaped; this layer is purely additive and must never be
    reached unless the product owner has actually wired up Postgres."""
    global _pool
    if _pool is not None:
        return _pool
    conninfo = os.environ.get("SUPABASE_DB_URL")
    if not conninfo:
        raise RuntimeError(
            "SUPABASE_DB_URL is not set. The Postgres repository layer is "
            "additive and only used once that variable is configured in "
            "backend/.env -- see SUPABASE_MIGRATION_BRIEF.md."
        )
    _pool = AsyncConnectionPool(
        conninfo,
        kwargs=_connect_kwargs(conninfo),
        min_size=1,
        max_size=10,
        open=False,
    )
    return _pool


async def open_pool() -> None:
    """Explicitly opens the pool (call once at app startup, once this layer
    is actually wired into server.py's lifespan -- not done yet in this
    phase). Safe to call more than once."""
    pool = get_pool()
    if pool.closed:
        await pool.open()


async def close_pool() -> None:
    """Closes and drops the process-wide pool. Mainly for tests/shutdown
    hooks -- lets a fresh get_pool() rebuild from a possibly-changed env."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def reset_pool_for_tests() -> None:
    """Drops the cached pool reference WITHOUT closing it -- for tests that
    inject their own fake pool and want get_pool() to forget any real pool
    created by an earlier test. Prefer close_pool() for real shutdown."""
    global _pool
    _pool = None


# ---- Thin query helpers used by every repositories/*_pg.py module ----------
# Every connection the pool hands out already has row_factory=dict_row (set
# in _connect_kwargs), so a plain cur.fetchall()/fetchone() already returns
# plain dicts -- these two helpers just hide the connection/cursor
# boilerplate so repository functions can read as a single SQL statement.

async def fetch_all(sql: str, params: Sequence[Any] = ()) -> List[dict]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()


async def fetch_one(sql: str, params: Sequence[Any] = ()) -> Optional[dict]:
    rows = await fetch_all(sql, params)
    return rows[0] if rows else None


@asynccontextmanager
async def transaction() -> AsyncIterator[AsyncCursor]:
    """Yields a dict_row cursor that runs inside a single Postgres
    transaction on one pooled connection -- for repository functions that
    need more than one statement to commit (or roll back) together as one
    unit, e.g. inserting an `oa_attempts` row and its paired
    `oa_attempt_keys` row, or a report/interview "finish" sequence that
    deletes a stale cached report and writes the fresh state in its place
    (see SUPABASE_MIGRATION_BRIEF.md's transaction-wrapper requirement).

    Every pool connection already runs with autocommit=True (see
    _connect_kwargs) so plain fetch_all/fetch_one calls each commit
    immediately as their own implicit transaction -- that's correct for a
    single statement, including an atomic single-statement
    UPDATE ... RETURNING, but wrong when two or more statements must
    succeed or fail as one unit. `conn.transaction()` (psycopg 3) opens an
    explicit transaction block even on an autocommit connection: it BEGINs
    on entry and COMMITs on a clean exit, or ROLLBACKs if the block raises
    -- exactly the semantics callers need here. Nothing in this module
    auto-retries; a caller that needs to react to a specific failure (e.g.
    psycopg.errors.UniqueViolation from the oa_attempts race-fix index)
    catches it around the `async with transaction() as cur:` block itself.
    """
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                yield cur
