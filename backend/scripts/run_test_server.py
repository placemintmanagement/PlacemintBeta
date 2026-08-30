# -*- coding: utf-8 -*-
"""TEST-ONLY launcher for Playwright E2E click-through tests.

Starts the real FastAPI app (server.py, completely unmodified) on a
dedicated test port, with the auth bypass documented in server.py's
_resolve_auth0_sub ACTIVE for this process only:

    ENVIRONMENT=test
    TEST_AUTH_TOKEN=<random, generated fresh every run unless passed in>

Both are set via os.environ BEFORE `server` is imported -- NEVER written to
backend/.env (the file server.py's own load_dotenv() reads on every start,
including any real deployment that reuses that file). python-dotenv's
load_dotenv() does not override a variable that's already present in
os.environ, so by the time server.py's `load_dotenv(ROOT_DIR / ".env")`
runs, ENVIRONMENT/TEST_AUTH_TOKEN are already set from THIS process's own
environment and the .env file's (nonexistent) values for them are ignored.
Closing this process ends the bypass entirely -- nothing persists to disk.

Usage:
    python scripts/run_test_server.py [--port 8899] [--token <fixed-token>]

Prints the port and the effective TEST_AUTH_TOKEN to stdout on startup so a
driving script (e.g. the Playwright E2E test) can capture and reuse them --
notably, the SAME token value must also be exported as
REACT_APP_TEST_AUTH_TOKEN when starting the frontend dev server (see
frontend/e2e/README or the Playwright test's own setup script), since the
frontend and backend bypass checks are two independent, symmetric gates
that both require the identical secret.

Writes real data to whatever MONGO_URL/DB_NAME backend/.env points at --
this is the same database `python server.py` would use normally, since
this script doesn't override those. It does NOT set up a separate test
database (none exists in this project's config). Test scripts using this
server are responsible for cleaning up their own test user/attempts
(filter by the fixed test sub, see server._TEST_BYPASS_USER_SUB) --
matching this repo's existing convention (test_capgemini_round1_e2e.py and
friends clean up in a `finally` block).
"""
from __future__ import annotations
import argparse
import asyncio
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Must match server.py's own _TEST_BYPASS_USER_SUB exactly -- duplicated as a
# literal (not imported) so this cleanup can run BEFORE `server` is
# imported, since importing it kicks off the mcq_pool background worker.
_TEST_BYPASS_USER_SUB = "test-bypass|e2e-runner"


async def _reset_test_user() -> None:
    """Deletes the fixed E2E test user (and any of its OA attempts) before
    each test-server run, so entitlements (run quota, company-selection cap)
    never carry over stale state from a previous run and false-fail a
    perfectly good click-through with a 402. Matches this repo's existing
    test-cleanup convention (test_capgemini_round1_e2e.py and friends
    delete their own test data in a `finally` block) -- this just does it
    proactively, up front, since a Playwright run can't easily hook a
    Python `finally` on the server process it starts."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=10000)
    db = client[os.environ["DB_NAME"]]
    try:
        user = await db.users.find_one({"auth0_sub": _TEST_BYPASS_USER_SUB}, {"_id": 0, "user_id": 1})
        if user:
            await db.oa_attempts.delete_many({"user_id": user["user_id"]})
            await db.users.delete_many({"auth0_sub": _TEST_BYPASS_USER_SUB})
            print(f"[run_test_server] reset test user {user['user_id']} (deleted user doc + its oa_attempts)")
        else:
            print("[run_test_server] no prior test user found -- clean slate")
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument("--token", default=None, help="Fixed TEST_AUTH_TOKEN (random if omitted)")
    parser.add_argument("--frontend-port", type=int, default=3899, help="Frontend test dev-server port, for CORS_ORIGINS")
    args = parser.parse_args()

    token = args.token or secrets.token_urlsafe(32)

    # MUST happen before `import server` (or anything that imports it) --
    # server.py's ENVIRONMENT/TEST_AUTH_TOKEN checks read os.environ live on
    # every request, but load_dotenv() itself only fills in vars NOT already
    # present, so these need to already be set by the time load_dotenv runs.
    os.environ["ENVIRONMENT"] = "test"
    os.environ["TEST_AUTH_TOKEN"] = token
    # backend/.env's CORS_ORIGINS is normally http://localhost:3000 (the
    # NORMAL dev frontend port) -- the throwaway test frontend runs on its
    # OWN dedicated port (3899 by default, see e2e/start-test-frontend.js)
    # specifically so it never collides with a real dev server, which means
    # it's also a genuinely different origin the real .env's CORS list was
    # never meant to cover. Overridden here, in this process's own env only
    # -- never written to backend/.env -- same "ephemeral, process-local
    # only" discipline as ENVIRONMENT/TEST_AUTH_TOKEN above.
    os.environ["CORS_ORIGINS"] = f"http://localhost:{args.frontend_port}"

    asyncio.run(_reset_test_user())

    import uvicorn

    print("=" * 70)
    print("STARTING TEST SERVER -- AUTH0 BYPASS ACTIVE FOR THIS PROCESS ONLY")
    print(f"  port:            {args.port}")
    print(f"  TEST_AUTH_TOKEN: {token}")
    print("  (export this SAME value as REACT_APP_TEST_AUTH_TOKEN for the")
    print("   frontend dev server -- both sides must match)")
    print("=" * 70)

    uvicorn.run("server:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
