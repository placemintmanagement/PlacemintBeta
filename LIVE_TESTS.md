# Live Supabase tests

`backend/tests/test_live_supabase_integration.py` runs real round-trips against
the actual Supabase Postgres database -- real inserts, real concurrency races,
real cleanup. It's the only thing in this migration that can catch a bug a
mocked test can't (see `7543e38`'s jsonb_set fix: a real, silent production
bug that every mocked test missed because mocks only assert the SQL *string
shape*, never execute it against a real server).

## Prerequisite: a network that allows outbound Postgres

Supabase's pooler is reachable on ports 5432 (session pooler) and 6543
(transaction pooler). Plenty of networks -- corporate wifi, some ISPs, some
VPNs -- block non-standard outbound ports and only allow 80/443. If a
connection hangs for ~10-20s and then times out, that's almost always this,
not a credentials problem or Supabase being down (a bad password fails fast;
a blocked port times out). **A phone hotspot or a home network has worked
reliably in this session when an office/other network didn't.** If in doubt,
a quick isolating check:

```bash
python -c "import socket; socket.create_connection(('aws-0-ap-south-1.pooler.supabase.com', 5432), timeout=8); print('open')"
```

If that hangs/times out but `https://` to the same host works fine, it's the
network blocking the port, not anything on the Supabase or app side.

## Running it

1. In `backend/.env`, uncomment and fill in `SUPABASE_URL` and
   `SUPABASE_DB_URL` (placeholders are already there, commented out). No
   other setup needed -- the file loads automatically via the backend's
   existing `load_dotenv()` call, same as every other env var.
2. From `backend/`:
   ```bash
   python -m pytest tests/test_live_supabase_integration.py -v
   ```
   Or just run the normal full suite (`python -m pytest`) -- these tests are
   regular pytest tests, not a separate runner. They skip themselves
   automatically (not an error, not a failure) if `SUPABASE_DB_URL` isn't set.

### PowerShell (Windows)

The commands above are bash syntax. On a Windows machine running PowerShell
(the product owner's own setup), use this instead -- PowerShell has no
inline `VAR=value command` prefix form, so `DB_BACKEND=supabase python -m
pytest` (bash syntax) silently does NOT set the env var in PowerShell; it
must be set as its own statement first.

Run just the live integration file (from `backend/`):
```powershell
python -m pytest tests/test_live_supabase_integration.py -v
```

Run the FULL suite for real against Postgres (not self-skipped), now that
`SUPABASE_DB_URL` is set in `backend/.env`:
```powershell
$env:DB_BACKEND = "supabase"
python -m pytest -v
```

**Important**: `$env:DB_BACKEND` persists for the rest of this PowerShell
session (and any other process you launch from it), not just this one
command. Once you're done running the Postgres-backed suite, unset it
before doing anything else in this shell -- otherwise every later `pytest`
run (and anything else that reads `DB_BACKEND`) in this same window keeps
reading "supabase" instead of the default:
```powershell
Remove-Item Env:DB_BACKEND
```
Closing the PowerShell window entirely also clears it, if that's easier.

## What it covers

Schema sanity (the `interviews` migration's columns/index actually exist),
every content-bank repository's shape and exclusion-filter behavior against
the real 8795/326/48/1280/350/19/4-row banks, `mcq_pool`'s atomic
pop-one under real concurrency, and the three correctness fixes
(`profiles.deduct_credit`'s floor check, `oa_attempts.create_attempt`'s
unique-violation race, `reports.finish_interview`'s transactional rollback)
proven with real concurrent calls and literal before/after values -- not just
"it passed."

A module-scoped autouse fixture asserts every user-data table is at 0 rows
both before and after this file's tests run, so a test that doesn't clean up
after itself (even on failure, via try/finally) fails loudly rather than
leaving scratch data in the real database.

## Known flakiness

This specific Supabase host has shown intermittent connection timeouts in
this session, independent of any test/code (confirmed with a bare TCP socket
connect, no psycopg involved) -- it comes and goes with no code change. The
test file has a small retry/backoff around its connection setup for this
reason, but a long enough outage will still make these tests fail/error
rather than pass. If they fail, re-run the isolating check above before
assuming it's a real regression.
