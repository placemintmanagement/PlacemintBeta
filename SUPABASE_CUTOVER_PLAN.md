# Supabase Cutover Plan

Planning-only document. Nothing in this file changes `server.py`, any route,
any repository module, or any frontend file. It is the reviewable plan the
product owner asked for before Phases 2-3's Postgres repository layer
(`backend/repositories/*_pg.py`, `backend/db_postgres.py`) is actually wired
into `server.py`. Read `SUPABASE_MIGRATION_BRIEF.md` first — this document
assumes its decisions (Razorpay-only, legacy-auth-deletion, the three
race-fixes, etc.) and does not repeat them except where a specific route
needs them spelled out.

Order of work, per the product owner's instruction: **Step 1 (content-bank
reads) → Step 2 (auth) → Step 3 (everything else, including payments)**.

### Methodology note on the "136 calls" figure

A fresh regex pass over `backend/server.py` (`\bdb\.[a-zA-Z_]+\.`) found
**141** occurrences, not 136. The 5-call difference is almost certainly
counting convention, not a real discrepancy: 11 of the 141 are one-time
`db.<collection>.create_index(...)` calls inside the `@app.on_event("startup")`
handler (lines 7196–7206) — infrastructure setup, not a route touching live
request data, and arguably excludable depending on how the original audit
counted. The route-by-route tables below account for all 141 (the 11
startup-index calls are called out separately, not assigned to any route).
Six content-bank collections (`mcq_static_bank`, `mcq_pool`,
`mcq_pool_stats`, `puzzle_bank`, `capgemini_round1_bank`,
`gamified_round_config`) are read through helper modules
(`backend/banks/*.py`, `backend/games/gamified_round.py`) that hold their own
`_db` handle set via an `init(db)` call at startup — their
`_db.<collection>.*` calls live in those files, not in `server.py`, so they
are **not** part of the 141 and are tracked separately in the Step 1 section.
`capgemini_round1_bank`/`capgemini_round2_bank` are the one exception: those
reads happen directly inline in `server.py` (inside `_generate_section_questions`),
so they *are* part of the 141.

---

## Overview: the `DB_BACKEND` switch

### Convention (matches `TCS_INTERVIEW_ENABLED`/`DISABLE_AUTH` exactly)

```python
# backend/server.py, next to _auth_disabled()/tcs_interview_enabled()
def db_backend() -> str:
    """DB_BACKEND: "mongo" (default) or "supabase". Read fresh on every
    call, never cached at import time -- same convention as _auth_disabled()
    and tcs_interview_enabled() above. A plain restart with no config change
    behaves exactly as today; flipping to "supabase" is one env var, and
    flipping back is instant and requires no code change on either side."""
    return os.environ.get("DB_BACKEND", "mongo").strip().lower()
```

No on/off boolean — two explicit string values, because this is a
three-way fork (not a feature flag that's simply on or off): every call site
that branches on it needs exactly one of two concrete code paths, never a
"half-on" state. Any value other than exactly `"supabase"` is treated as
`"mongo"` (fails closed to the existing, proven behavior), matching
`_auth_disabled()`'s "omission is what keeps it off" philosophy.

### Where the dispatch lives: per-collection, not per-route

**Recommendation: a thin dispatch function at each existing data-access
choke point, not inline `if db_backend() == "supabase":` branches scattered
through route handlers.** Reason: `server.py`'s 7220 lines already have most
collections funneled through a small number of named functions/modules
(`require_user`, `_create_user_record`, the `banks/*.py` + `games/
gamified_round.py` modules' `_db.<collection>` calls, and the many
`db.oa_attempts.find_one({"attempt_id":..., "user_id":...})`-shaped call
sites that *could* funnel through one `oa_attempts` accessor but currently
don't). The repository layer built in Phases 2-3 already assumes "one
function per operation" — `oa_attempts_pg.get_attempt(attempt_id, user_id)`,
`profiles_pg.deduct_credit(user_id)`, etc. The cleanest cutover is: **collapse
each repeated raw-Mongo-call shape into one small accessor function first (or
reuse the helper functions that already exist — `_generate_section_questions`,
`mcq_pool.pop_from_pool`, etc.), then add the backend fork inside that one
function**, so every route handler keeps calling the exact same name
regardless of backend. Scattering `if db_backend() == "supabase"` into ~50
`Depends(require_user)` route bodies would mean every route carries its own
copy of the fork, doubling the chance of a route that silently keeps reading
Mongo after the flag flips, and making a future Mongo-removal pass (deleting
the `mongo` branch once the cutover is final) a 50-site hunt instead of a
~15-function one.

Two different shapes of "choke point" exist in this codebase today, and the
dispatch sits at whichever one already owns the call:

1. **Bank modules with their own `_db` handle** (`banks/mcq_static_bank.py`,
   `banks/mcq_pool.py`, `games/gamified_round.py`) — the fork goes *inside*
   each public function in that module, right where its `_db.<collection>`
   call already is. These modules never need to touch `server.py` at all.
2. **Calls made directly in `server.py`** (every `db.oa_attempts.*`,
   `db.users.*`, etc., plus — the one content-bank exception —
   `db.capgemini_round1_bank`/`db.capgemini_round2_bank`, which are read
   inline inside `_generate_section_questions`, not behind a module
   boundary like the other five banks). Here the plan is to extract each
   repeated shape into a named function (many already exist as private
   helpers — `_store_hidden_answer_key`, `_latest_resume_for_company`,
   `_existing_in_progress_interview`, etc. — those just need the fork added
   in place; a few shapes that are currently *inlined* at each of several
   call sites, like the plain `db.oa_attempts.find_one({"attempt_id":...,
   "user_id":...})` ownership-scoped read repeated at ~8 call sites, should
   be collapsed into one function first so the fork is written once).

### Illustration ONLY — not applied in this task

`GET /admin/mcq-stats` is a good representative example: a simple route
whose entire body is one content-bank read, already behind a module
boundary (`mcq_pool.pool_stats()`), with a Postgres repository function
already built and tested (`mcq_pool_pg.get_all_stats()`). This is a sketch
of what Step 1's dispatch would look like for it — real code shape, but
illustrating the pattern only, not a change made in this task:

```python
# backend/banks/mcq_pool.py -- ILLUSTRATION ONLY

import os
from repositories import mcq_pool_pg

def _db_backend() -> str:
    # Same convention as server.py's db_backend() -- read fresh, no cache.
    return os.environ.get("DB_BACKEND", "mongo").strip().lower()


async def pool_stats() -> Dict[str, Any]:
    """Founder-only readout -- new-pipeline metrics tell you WHERE questions
    are being dropped and WHICH ground-truth source is producing them."""
    if _db_backend() == "supabase":
        # NOTE (real gap, see punch list): mcq_pool_pg.get_all_stats() only
        # covers the mcq_pool_stats half of this readout today. The
        # pool_counts half (a $group aggregation over mcq_pool rows by
        # company_name/section_key) has no Postgres repository function yet
        # -- it would need a new mcq_pool_pg.count_by_company_and_section()
        # before this branch could return full parity.
        stats_rows = await mcq_pool_pg.get_all_stats()
        stats = [_shape_stats_row(r) for r in stats_rows]  # same shaping the Mongo branch below does
        pool_counts = []  # GAP -- see above
        return {"pool_counts": pool_counts, "stats": stats}

    # ---- existing Mongo path, unchanged ----
    if _db is None:
        return {"pool_counts": [], "stats": []}
    pool = []
    async for doc in _db.mcq_pool.aggregate([...]):
        pool.append(doc)
    stats = []
    async for doc in _db.mcq_pool_stats.find({}, {"_id": 0}):
        ...
    return {"pool_counts": pool, "stats": stats}
```

This example also demonstrates why the fork belongs inside `mcq_pool.py`
and not inside `server.py`'s `admin_mcq_stats` route handler: the route
handler already just calls `await mcq_pool.pool_stats()` and returns it
verbatim — it has no Mongo-shaped code of its own to fork.

---

## Step 1 — content-bank reads only

Scope: `mcq_static_bank`, `mcq_pool`/`mcq_pool_stats`, `puzzle_bank`,
`capgemini_round1_bank`, `capgemini_round2_bank`, `gamified_round_config`.
Gated behind `DB_BACKEND`. Default `mongo` — a plain restart changes nothing.

### Access paths (not all in `server.py` — see methodology note above)

| Collection | Where the `_db.<collection>` call actually lives | Repo module |
|---|---|---|
| `mcq_static_bank` | `backend/banks/mcq_static_bank.py` (`sample_static`, `_draw_bucket`, `sample_static_with_reuse`, `sample_static_difficulty_weighted_with_reuse`, `sample_mixed_static_part`, `topic_bank_size`) | `mcq_static_bank_pg.py` |
| `mcq_pool` | `backend/banks/mcq_pool.py` (`pop_from_pool`, `pool_stats`'s aggregation half) | `mcq_pool_pg.py` |
| `mcq_pool_stats` | `backend/banks/mcq_pool.py` (`pool_stats`'s stats half; write side `_record_outcome` explicitly NOT in scope) | `mcq_pool_pg.py` |
| `puzzle_bank` | `backend/games/gamified_round.py` (`sample_puzzles`, `check_answer`, `get_grid_challenge_phase`, `check_grid_challenge_answer`, `grade_grid_challenge_session`, motion-challenge functions, `grade_session`) | `puzzle_bank_pg.py` |
| `gamified_round_config` | `backend/games/gamified_round.py` (`get_config`) | `puzzle_bank_pg.py` (same module as puzzle_bank) |
| `capgemini_round1_bank` | **`backend/server.py` directly**, inside `_generate_section_questions` (grammar/business/situational/reading/listening/spoken pools, 6 `.find()` calls) | `capgemini_bank_pg.py` |
| `capgemini_round2_bank` | **`backend/server.py` directly**, inside `_generate_section_questions` (AI-literacy pool, 1 `.find()` call) | `capgemini_bank_pg.py` |

The `capgemini_round1_bank`/`capgemini_round2_bank` asymmetry (inline in
`server.py`, not behind a module boundary like the other five banks) is
itself a punch-list item — see "Gaps" below.

### Route-by-route (every route whose execution path reaches one of these banks, directly or via a background task)

| Route | Collections touched (this step) | Repo function status | Notes |
|---|---|---|---|
| `POST /oa/start` | `mcq_static_bank`, `mcq_pool`, `capgemini_round1_bank`, `capgemini_round2_bank`, `puzzle_bank`, `gamified_round_config` | All six have a matching repo function **except** the `mcq_pool_stats` write-upsert (out of scope, generation pipeline) and the reuse-sort combination below | The actual content reads happen inside `_generate_extra_topics` → `_generate_topic_mix` → `_generate_section_questions` → `_gen_and_persist_section`, invoked as `asyncio.create_task(_generate_tcs_sections_bg(...))` / `_generate_all_sections_bg(...)` from inside `start_oa`'s body (~line 2099–2101) — i.e. this is background-task work kicked off by the route, not inline in the request/response cycle. The dispatch for `capgemini_round1_bank`/`capgemini_round2_bank` must be added directly at those 7 call sites (or, better, after extracting them into `capgemini_recruitment_process.fetch_round1_pool()`/`fetch_round2_pool()` first — see Gaps). |
| `POST /oa/{attempt_id}/section` | `puzzle_bank` (via `_grade_gamified_round_section` → `gamified_round.grade_session`/`grade_grid_challenge_session`/`grade_motion_challenge_session`, which read puzzle answer keys for grading) | `puzzle_bank_pg.get_by_id`/`get_by_ids` cover the read shape | Grading-time read, not client-facing — still must never leak `correctAnswer`/`explanation` (unchanged responsibility, stays in `gamified_round.py`, not this bank's job). |
| `POST /oa/{attempt_id}/section/check` | `puzzle_bank` (via `gamified_round.check_answer`) | Covered (`get_by_id`) | |
| `POST /oa/{attempt_id}/section/grid-challenge/phase` | `puzzle_bank` (via `get_grid_challenge_phase`) | Covered | |
| `POST /oa/{attempt_id}/section/grid-challenge/answer` | `puzzle_bank` (via `check_grid_challenge_answer`) | Covered | |
| `POST /oa/{attempt_id}/section/motion-challenge/move` | `puzzle_bank` (via `motion_challenge_move`) | Covered | |
| `POST /oa/{attempt_id}/section/motion-challenge/undo` | `puzzle_bank` (via `motion_challenge_undo`) | Covered | |
| `POST /oa/{attempt_id}/section/motion-challenge/state` | `puzzle_bank` (via `motion_challenge_state`) | Covered | |
| `GET /admin/mcq-stats` | `mcq_pool`, `mcq_pool_stats` (via `mcq_pool.pool_stats()`) | **Partial gap** — `mcq_pool_pg.get_all_stats()` covers only the `mcq_pool_stats` half; the `pool_counts` aggregation (group mcq_pool rows by company_name/section_key) has no repo function | See Overview's illustration for this exact route. |
| app startup (`@app.on_event("startup")`, not a route) | `mcq_pool`, `mcq_pool_stats`, `mcq_static_bank`, `mcq_static_bank_seen`, `gamified_round_config`, `puzzle_bank`, `review_deck`, `game_session` index creation | N/A — Postgres indexes are already declared in `supabase/schema.sql`; under `DB_BACKEND=supabase` this whole block should simply be skipped (a `if db_backend() == "mongo":` guard around the existing `_startup` body), not ported | Not a route; listed for completeness since it's 11 of the 141 raw matches. |

### Risk notes — Step 1

- **`mcq_pool.pop_from_pool`'s atomic pop-one is proven correct only
  standalone, not under real route traffic yet.** `mcq_pool_pg.pop_one` has
  a dedicated live concurrency test
  (`test_mcq_pool_pop_one_atomic_under_real_concurrency` in
  `test_live_supabase_integration.py`) that fires concurrent simulated
  callers directly at the repository function. It has never been exercised
  through the real request path — `POST /oa/start`'s background section
  generation, triggered by real concurrent OA starts for the same
  company+section — which adds request-level concurrency (multiple users
  starting OAs for the same company at the same moment) on top of what the
  test simulates. The atomicity guarantee itself (`DELETE ... WHERE pool_id
  = (SELECT ... LIMIT 1) RETURNING ...`) is sound regardless of caller count,
  but pool *exhaustion* behavior under real traffic (what happens when
  `pop_up_to` returns fewer than requested because real concurrent demand
  drained the pool faster than the background worker refills it) has not
  been observed outside a test.
- **The MCQ pool worker still writes to Mongo only.** `mcq_pool_worker_enabled()`
  gates a background worker (`backend/banks/mcq_pool.py`'s `_worker_loop`)
  that continuously generates and inserts fresh questions into Mongo's
  `mcq_pool`/`mcq_pool_stats`. Nothing in Phases 2-3 built a Postgres write
  path for it (deliberately — `mcq_pool_pg.py`'s own docstring calls this
  out as deferred). If `DB_BACKEND=supabase` is flipped on while the worker
  keeps running, Postgres's `mcq_pool` table is a strictly *draining*
  resource (consumed by `pop_from_pool`'s Postgres path, never
  replenished) — it will eventually run dry and every live-pool serve falls
  through to `fallback_live_verify` (a live-AI generation path, slower and
  more expensive per question) for every company/section, silently, with no
  alert. This needs either a decision to pause/retire the worker once
  `DB_BACKEND=supabase` is the live mode, or a Postgres write path for it
  before cutover — the product owner should decide which, it's explicitly
  not resolved here.
- **`sample_static_with_reuse`'s least-recently-seen fallback is not fully
  coverable by Step 1 alone.** `mcq_static_bank_pg.py`'s own docstring flags
  this: the reuse sort needs per-user `seen_at` data, which lives in
  `question_seen` — a Step 3 (user-data) table. A Step 1 cutover either (a)
  ships only the non-reuse sampling paths under `supabase` first and defers
  `sample_static_with_reuse`/`sample_static_difficulty_weighted_with_reuse`
  until `question_seen_pg` is wired, or (b) pulls `question_seen_pg` forward
  as a Step 1 prerequisite exception. Not resolved here — flagged for the
  product owner.
- **Random draws are a genuine behavior change, not a port.** Per the
  migration brief, `puzzle_bank`/`mcq_pool` draws under Mongo were never
  actually randomized (plain cursor order). Under Postgres they become
  `ORDER BY random() LIMIT n` — a real behavior improvement, but it does
  mean a difficulty/distribution assumption baked into any test that
  expects a specific (non-random) draw order will need updating for the
  `supabase` path specifically (the `mongo` path is untouched and keeps its
  old non-random order).

### Test coverage — Step 1

- Every one of the four content-bank repo modules has a dedicated mocked
  test file (`test_repositories_mcq_static_bank_pg.py` — 9 tests,
  `test_repositories_mcq_pool_pg.py` — 5, `test_repositories_puzzle_bank_pg.py`
  — 9, `test_repositories_capgemini_bank_pg.py` — 3) plus live-Supabase
  coverage in `test_live_supabase_integration.py`
  (`test_content_bank_row_counts_match_expected`,
  `test_mcq_static_bank_pg_shape_and_exclusion`,
  `test_puzzle_bank_pg_merge_back_shape_and_exclusion`,
  `test_gamified_round_config_pg_shape`, `test_capgemini_bank_pg_shapes`,
  `test_mcq_pool_pop_one_atomic_under_real_concurrency`).
- **Gap: no test exercises any of these routes end-to-end with
  `DB_BACKEND=supabase`.** The Mongo-path behavior of `POST /oa/start`'s
  section generation is covered today only by `backend_test.py`'s
  `test_oa_submit_all_sections_and_review` (a live-HTTP test against a
  running server with real Mongo) and various unit tests
  (`test_tcs_puzzle_wiring.py`, `test_interview_puzzle_bank.py`,
  `test_capgemini_tiers.py`, `test_capgemini_views.py`) that monkeypatch a
  fake db object. None of these parametrize over `DB_BACKEND`, so the
  Postgres path through the actual route (as opposed to the repository
  function in isolation) has zero coverage today. This needs new
  route-level tests (reuse the existing fake-db-style fixtures, parametrized
  to also run with `DB_BACKEND=supabase` against a real or test Postgres
  instance) before/alongside wiring each bank in.
- **Gap: `GET /admin/mcq-stats` has no dedicated test at all today** (Mongo
  or Postgres) — grep of the test suite found no reference to
  `/admin/mcq-stats` or `pool_stats`. Both the Mongo baseline and the new
  Postgres path should get one.

---

## Step 2 — auth (Auth0 → Supabase Auth)

Per the brief: delete, don't port, `/auth/signup`, `/auth/login`,
`/auth/google/session`, `/auth/logout`, `/auth/email/send-verification`,
`/auth/email/verify`, `/auth/password/forgot`, `/auth/password/reset`, and
the `auth_tokens` collection — Supabase Auth replaces all of it natively.

### Routes to delete outright (not ported)

| Route | Collections touched today | Disposition |
|---|---|---|
| `POST /auth/signup` | `users` (via `_create_user_record`) | Delete |
| `POST /auth/login` | `users` | Delete |
| `POST /auth/google/session` | `users`, `user_sessions` | Delete |
| `POST /auth/logout` | `user_sessions` | Delete |
| `POST /auth/email/send-verification` | `auth_tokens` (via `_create_token`) | Delete |
| `POST /auth/email/verify` | `users`, `auth_tokens` (via `_consume_token`) | Delete |
| `POST /auth/password/forgot` | `users`, `auth_tokens` (via `_create_token`) | Delete |
| `POST /auth/password/reset` | `users`, `auth_tokens` (via `_consume_token`) | Delete |

Also delete at this time: `_create_token`, `_consume_token`, `_new_token`,
`_dev_link` (only callers are the routes above), `hash_password`/
`verify_password`/`make_jwt` (only used by the deleted password flow), and
the `user_sessions` collection's only two call sites (`google_session`,
`logout`). `_create_user_record` is **not** deleted outright — see below.

### Routes that stay, reimplemented against Supabase Auth

| Route | Collections touched | Repo function status | Notes |
|---|---|---|---|
| `GET /auth/me` | `users` → `profiles` | `profiles_pg.get_profile` + `profiles_pg.maybe_reset_period` cover this exactly | Response shape changes: no more `password_hash`/`auth0_sub`/`user_sessions` fields to strip — `profiles_pg._COLUMNS` already excludes them. |
| `POST /user/company-selection` | `users` → `profiles` (`company_selections`) | `profiles_pg.add_company_selection`/`remove_company_selection` — **behavior upgrade**: the Mongo route does a read-then-write `$addToSet`/removal today; the repo functions are already atomic (the brief's required fix) | Route logic (cap-check, which company to add/remove) stays the same; only the persistence call changes. |
| `PATCH /auth/profile` | `users` → `profiles` | `profiles_pg.upsert_onboarding_fields` covers it | |
| `require_user` (shared `Depends`, ~50 call sites) | `users` → `profiles` | **Needs a new function, no direct repo equivalent** — see Gaps | This is the highest-leverage single change in the whole migration: one dependency function, reused everywhere. |

### `require_user`'s replacement — what has to change

Today `require_user` (server.py:433-475): (1) verifies the Auth0 JWT via
`_resolve_auth0_sub` → `auth0_middleware.get_current_user`, (2) looks up
`db.users.find_one({"auth0_sub": auth0_sub})`, (3) on first sight, calls
Auth0's `/userinfo` for an email, then `_create_user_record(...)` to
auto-provision a brand-new `users` document with starting plan/quota/credits.

The Supabase-Auth replacement: (1) verify the bearer token against the
Supabase project's JWKS (`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`),
exactly analogous to `auth0_middleware.py`'s own `_verify_token`/`_get_jwks`
shape (same TTL-cached-JWKS pattern can be reused almost as-is — the brief
explicitly allows PyJWT + JWKS or the legacy JWT secret); (2) the token
`sub` claim IS the Supabase auth user uuid — no separate "look up by
auth0_sub, mint our own user_id" step, because `profiles.id` *is* that uuid
(no more two-id indirection); (3) `profiles_pg.get_profile(sub)` — **and
tolerate a brief moment where the row doesn't exist yet**, since
`handle_new_user()` (the database trigger in `schema.sql`) runs
asynchronously on `auth.users` insert, not synchronously with the same
request that creates the Supabase Auth account; a short retry-or-425
("try again shortly") is the idiomatic answer here, not a 404, since it
isn't user error.

### Gaps (Step 2)

- **`_create_user_record`'s plan/quota-defaulting logic has no home in the
  Postgres path.** It isn't just "create the row" — it sets `plan: "founder"`
  + `runs_quota: 999999` for `is_bypass_email(email)` addresses, and
  `runs_quota: entitlements.FREE_RUN_LIMIT_DURING_CONTEST` (currently 3) for
  everyone else, plus the `company_selections: []`/`plan_started_at`/
  `email_verified` initial values. `handle_new_user()`'s trigger creates a
  *bare* row (per the brief: "Make sure the backend tolerates the brief
  moment before it exists, and does upserts of onboarding fields... on
  profiles" — it does not mention plan defaults at all). Nothing in
  `profiles_pg.py` sets a founder plan or a starting quota. **This needs
  either**: a new `profiles_pg.ensure_default_plan(user_id, email)` called
  once from the new `require_user`'s first-seen path (same "first time we
  see this sub" moment the old code used), **or** extending
  `handle_new_user()` itself to read a bypass-email list and set plan
  defaults at insert time (a schema/trigger change, which per Ground Rule 6
  must go in a numbered `supabase/*.sql` file shown to the product owner,
  never executed directly). Not resolved here — flagged as required
  follow-up work before Step 2 ships, not optional polish.
- **Auth0's `get_userinfo_email` has no Supabase-Auth analogue needed** —
  Supabase Auth's JWT already carries `email` as a standard claim (no
  separate network call required), which is actually a simplification, not
  a gap — noted so it isn't mistaken for missing work.

### Risk notes — Step 2 (the highest-risk step overall)

- **Session invalidation for anyone mid-session.** Every existing Auth0
  access token becomes instantly unverifiable the moment the backend's JWKS
  URL changes — any user with a live session must re-authenticate. The
  brief notes there are no real users and `DISABLE_AUTH` is presently on in
  this environment (Auth0 itself is not even reachable today — the tenant's
  client ID is misconfigured, see `server.py`'s own `DISABLE_AUTH` comment),
  which makes this close to zero-impact *right now*, but the risk is real
  the moment `DISABLE_AUTH` is ever unset before this cutover ships.
- **Legacy-route deletion must not break anything still reachable.** Before
  deleting, confirm nothing else in `server.py` calls `_create_token`,
  `_consume_token`, `hash_password`, `verify_password`, or `make_jwt`
  outside the 8 routes being deleted (a plain grep, not a guess — done
  above; all four are single-purpose to the deleted routes). Also: deleting
  routes changes the live FastAPI route table, which
  `test_route_table_integrity.py`'s committed `route_table_snapshot.json`
  will (correctly) flag as drift — the snapshot must be regenerated in the
  **same diff** as the route deletions, or that test fails by design (a
  guard working as intended, not a bug, but easy to forget).
- **JWT claims shape.** `require_user`'s replacement must map Supabase's
  claims (`sub`, `email`, `role`, etc.) onto whatever the rest of the app
  expects from "the current user" — today that's a full `profiles` row
  keyed by `sub`-as-uuid, not the raw claims themselves, so this is lower
  risk than it sounds (the claims are only ever used to look up the real
  row), but the JWKS verification step itself (audience/issuer checks) needs
  the same care `auth0_middleware.py`'s `_verify_token` already takes —
  copy that shape, don't freehand a new one.
- **The founder/bypass-email plan grant (`is_bypass_email`) must keep
  working identically**, since it's how the product owner's own test
  accounts get unlimited access — this is exactly the gap flagged above,
  called out twice because it is easy to silently lose in a trigger-based
  provisioning model where "create the row" and "set the plan" are no
  longer the same code path.

### Test coverage — Step 2

- **`backend_test.py` (live-HTTP regression suite, `requests` against a
  running server) is the only test that exercises
  signup/login/me/logout/companies/pricing/payments/dashboard/OA-start/
  interview-flow/final-report/quota-exhaustion end-to-end, and its `auth`
  fixture (and several standalone tests:
  `test_me_unauth`, `test_signup_login_me`, `test_login_invalid`,
  `test_signup_duplicate`, `test_quota_exhaustion`) authenticates by calling
  `POST /auth/signup` directly.** The moment Step 2 deletes that route, this
  entire file's fixture — and therefore every test in it, including the
  ones covering Step 3 routes (`test_dashboard`, `test_mock_payment_flow`,
  `test_oa_start_and_get`, `test_oa_run_python`,
  `test_oa_submit_all_sections_and_review`, `test_interview_and_report`) —
  breaks at collection/setup time, not just the auth-specific tests. **This
  is the single biggest test-coverage gap found in this audit**: a large
  fraction of this codebase's only end-to-end HTTP coverage is keyed to the
  very routes Step 2 deletes. Required companion work, not optional: rewrite
  `backend_test.py`'s `auth`/`oa_attempt` fixtures to provision a real (or
  sandboxed) Supabase Auth user and mint a token the same way the frontend
  will, before or in the same change as Step 2's route deletions — otherwise
  Step 2 ships with a silent, large coverage regression across three steps'
  worth of routes, not just its own.
- `test_route_table_integrity.py` passes today and will (correctly) fail
  the moment the 8 routes are deleted, until `route_table_snapshot.json` is
  regenerated — tracked above as a required same-diff companion change, not
  a separate gap.
- No existing test covers Supabase JWT verification itself (no
  `auth0_middleware.py`-equivalent test file exists for Auth0 either, so
  this isn't a regression, but it does mean the new verification code starts
  from zero coverage, not "replacing a tested thing").

---

## Step 3 — user-data routes and payments

Scope: profiles/entitlements (the parts not already covered in Step 2),
resumes, `oa_attempts`+`oa_attempt_keys`, `game_sessions`,
`ai_assisted_sessions`, interviews, reports, `question_seen`, `review_deck`,
and the Razorpay order/verify flow — all behind the same `DB_BACKEND` switch.

### Route-by-route

| Route | Collection(s) | Repo function status | Notes |
|---|---|---|---|
| `POST /resume/analyze` | `resumes` | `resumes_pg.insert_resume` | Direct match. |
| `GET /resume/{resume_id}` | `resumes` | `resumes_pg.get_resume` | Direct match (ownership-scoped). |
| `GET /resume` | `resumes` | `resumes_pg.get_resumes_for_user` | Direct match. |
| `POST /oa/start` | `oa_attempts`, `resumes`, `users`→`profiles` | `oa_attempts_pg.create_attempt` (+ `get_existing_in_progress`), `resumes_pg.get_resume`, `profiles_pg.maybe_reset_period`/`deduct_credit`/`add_company_selection` | Also the Step 1 content-bank reads (see that section) run inside this same route's background tasks. `create_attempt` already folds in the race-fix (partial unique index + `UniqueViolation` catch) and the paired `oa_attempt_keys` insert in one transaction — both already live-verified. |
| `GET /oa/{attempt_id}` | `oa_attempts` | `oa_attempts_pg.get_attempt` | Direct match; the route's own answer-key-exclusion projection logic (`_strip_answer_fields_for_response`) stays unchanged — it operates on the row after fetch either way. |
| `POST /oa/run` | `oa_attempts` | `oa_attempts_pg.get_attempt` | Direct match. |
| `POST /dev/debugging/run` | — (no direct db call in this route) | N/A | |
| `POST /oa/{attempt_id}/transcribe` | `oa_attempts` | `oa_attempts_pg.get_attempt` | |
| `POST /oa/{attempt_id}/section/check` | `oa_attempts` (+ `puzzle_bank`, Step 1) | `oa_attempts_pg.get_attempt` | |
| `POST /oa/{attempt_id}/section/grid-challenge/phase` | `oa_attempts` (+ `puzzle_bank`) | `oa_attempts_pg.get_attempt` | |
| `POST /oa/{attempt_id}/section/grid-challenge/answer` | `oa_attempts` (+ `puzzle_bank`) | `oa_attempts_pg.get_attempt` | |
| `POST /oa/{attempt_id}/section/motion-challenge/move` | `oa_attempts` (+ `puzzle_bank`, `game_sessions`) | `oa_attempts_pg.get_attempt` | |
| `POST /oa/{attempt_id}/section/motion-challenge/undo` | `oa_attempts` | `oa_attempts_pg.get_attempt` | |
| `POST /oa/{attempt_id}/section/motion-challenge/state` | `oa_attempts` | `oa_attempts_pg.get_attempt` | |
| `POST /oa/{attempt_id}/section` | `oa_attempts` (x2: read + progress update), `ai_assisted_sessions` (via `_finalize_ai_assisted_section`), `game_sessions`/`puzzle_bank` (via `_grade_gamified_round_section`) | `oa_attempts_pg.get_attempt`/`update_attempt_progress`, `ai_assisted_sessions_pg.*`, `game_sessions_pg.*` | Busiest single route by collection count; the `update_attempt_progress(**fields)` kwargs shape matches the route's existing "whatever changed" `$set` pattern directly. |
| `POST /oa/{attempt_id}/finish-part-a` | `oa_attempts` (x2) | `oa_attempts_pg.get_attempt`/`update_attempt_progress` | |
| `GET /oa/{attempt_id}/review` | `oa_attempts` | `oa_attempts_pg.get_attempt` | |
| `POST /deck/add` | `oa_attempts` (read source), `review_deck` (x2: dup-check + insert) | `oa_attempts_pg.get_attempt`, `review_deck_pg.add_card` | `add_card` is already atomic (`ON CONFLICT ... DO NOTHING` against the real unique constraint) vs. the Mongo route's find-then-insert loop — a behavior upgrade, same `skipped_duplicates` semantics. |
| `GET /deck` | `review_deck` | `review_deck_pg.list_cards` | |
| `POST /deck/{card_id}/attempt` | `review_deck` (x2) | `review_deck_pg.get_card`/`record_attempt` | |
| `DELETE /deck/{card_id}` | `review_deck` | `review_deck_pg.delete_card` | |
| `POST /interview/start` | `oa_attempts` (via `best_cleared_tier`), `resumes` (via `_latest_resume_for_company`), `interviews` (via `_existing_in_progress_interview`, then the create itself) | `oa_attempts_pg.list_attempts_for_user` (for best_cleared_tier's scan), `resumes_pg.get_latest_resume_for_company`, `interviews_pg.get_existing_in_progress`/`insert_interview` | `best_cleared_tier` is a derived/computed helper (scans the user's attempts in Python) — no single repo function is "best_cleared_tier", it's built from `list_attempts_for_user` same as today. |
| `GET /interview/list` | `interviews` | `interviews_pg.list_interviews_for_user` | |
| `GET /interview/{interview_id}` | `interviews` | `interviews_pg.get_interview` | |
| `POST /interview/{interview_id}/idle` | `interviews` | `interviews_pg.get_interview` | |
| `POST /interview/{interview_id}/answer` | `interviews` (13+ sites across the Spark/Dave/Commit/TCS persona sub-handlers: `_claim_turn_or_409`, `_release_turn_claim`, `_spark_persist`/`_dave_persist`/`_commit_persist`, `_spark_finalize_if_expired`/`_dave_finalize_if_expired`/`_commit_finalize_if_expired`), `reports` (via `_invalidate_cached_report`, called from all three persist helpers) | `interviews_pg.get_interview`/`update_interview`/`update_interview_if_turn_matches`, `reports_pg.finish_interview` (already wraps the turn-guarded update + both report-invalidation deletes in one transaction — the brief's Fix #3) | **Highest-complexity route in Step 3.** The three `_X_persist`→`_invalidate_cached_report` pairs are exactly the "near-duplicate finish sequence" the brief calls out; `reports_pg.finish_interview` is the already-built, already-tested single-transaction replacement for all three — this is a 3-callers-to-1-function consolidation, not 3 separate ports. `_claim_turn_or_409`'s optimistic-concurrency check reads `interviews` directly too (no dedicated repo function beyond `get_interview`/`update_interview_if_turn_matches` — the claim logic itself is Python, operates on the fetched row). |
| `POST /dev/ai-assisted/start` | `ai_assisted_sessions` | `ai_assisted_sessions_pg.insert_session` | |
| `GET /dev/ai-assisted/{session_id}` | `ai_assisted_sessions` | `ai_assisted_sessions_pg.get_session` | |
| `POST /dev/ai-assisted/{session_id}/message` | `ai_assisted_sessions` (x2) | `ai_assisted_sessions_pg.get_session`/`update_session` | |
| `POST /dev/ai-assisted/{session_id}/consent` | `ai_assisted_sessions` (x2) | same | |
| `POST /dev/ai-assisted/{session_id}/self_review` | `ai_assisted_sessions` (x3) | same | |
| `GET /oa/{attempt_id}/ai-assisted/{section_key}` | `oa_attempts`, `ai_assisted_sessions` (via `_load_ai_assisted_session_for_attempt`) | `oa_attempts_pg.get_attempt`, `ai_assisted_sessions_pg.get_session_by_attempt_section` | `get_session_by_attempt_section` is an exact-match repo function for this shared helper's lookup. |
| `POST /oa/{attempt_id}/ai-assisted/{section_key}/message` | same + `ai_assisted_sessions` update | same + `update_session` | |
| `POST /oa/{attempt_id}/ai-assisted/{section_key}/consent` | same | same | |
| `POST /oa/{attempt_id}/ai-assisted/{section_key}/self_review` | same | same | |
| `GET /report/{attempt_id}` | `oa_attempts`, `interviews`, `resumes`+`reports` (via `_build_final_report_doc`) | `oa_attempts_pg.get_attempt`, `interviews_pg.get_interview_by_attempt`, `resumes_pg.get_resume_by_id`, `reports_pg.get_cached_report`/`insert_report` | |
| `GET /interview/{interview_id}/report` | `interviews`, `oa_attempts` (+ same `_build_final_report_doc` chain as above) | `interviews_pg.get_interview`, `oa_attempts_pg.get_attempt`, same reports/resumes functions | |
| `GET /dashboard` | `oa_attempts`, `resumes` | `oa_attempts_pg.list_attempts_for_user`, `resumes_pg.get_resumes_for_user` | |
| `POST /payments/order` | `orders` | `orders_pg.create_order` | Not wired in Phases 2-3 by design (payments is explicitly this step, not earlier). |
| `POST /payments/verify` | `orders` (x2), `users`→`profiles` (x2) | `orders_pg.get_order`/`mark_paid`, `profiles_pg.set_plan`/`increment_credits` | **Financially sensitive — see risk notes.** `mark_paid`'s `WHERE status != 'paid'` is the idempotency fix the brief requires; `razorpay_payment_id`'s UNIQUE constraint is the DB-level half. |

Routes with **zero** `server.py`-level db calls (static/in-process data,
nothing to migrate): `GET /companies`, `GET /companies/{company_id}`,
`GET /departments`, `GET /departments/{department_id}/companies`,
`GET /pricing`, `GET /`.

### Risk notes — Step 3

- **Credit-deduction race, now under real concurrent load for the first
  time.** `profiles_pg.deduct_credit`'s atomic `WHERE credits > 0 RETURNING`
  fix has a dedicated live concurrency test
  (`test_profiles_pg_live_flow_and_deduct_credit_concurrency`), but that
  test drives the repository function directly with simulated concurrent
  callers — it has never been exercised through `POST /oa/start`'s actual
  request path, where the deduction is one step inside a larger
  entitlement-check-then-attempt-create sequence (`maybe_reset_period` →
  entitlement check → `deduct_credit` → `add_company_selection` →
  `create_attempt`), each currently a separate await. A real user hitting
  "start OA" twice in quick succession (double-click, retry-on-timeout) is
  the realistic trigger for this, not synthetic concurrency — worth an
  explicit route-level concurrency test, not just trusting the repository
  function's own test.
- **`oa_attempts`'s "already in progress" race, same caveat.** `create_attempt`'s
  partial-unique-index + `UniqueViolation`-catch fix has a dedicated live
  test (`test_oa_attempts_pg_create_attempt_real_race_and_hidden_answer_keys`),
  same standalone-vs-route-traffic gap as above.
- **The orders/payments flow is financially sensitive — correctness here
  literally means money.** `orders_pg.mark_paid`'s idempotency fix is
  correct in isolation (`test_orders_pg_live_flow_and_idempotent_mark_paid`
  covers double-verify), but `POST /payments/verify`'s real sequence is
  (1) re-verify the Razorpay HMAC signature, (2) call `mark_paid`, (3) if
  non-None, grant plan/credits via `profiles_pg.set_plan`/`increment_credits`.
  Step (3) is NOT inside the same transaction as step (2) in the current
  repo-module design (`mark_paid` and `set_plan`/`increment_credits` are
  separate `fetch_one` calls on separate implicit transactions) — a crash
  between them would leave an order marked `paid` with no credit/plan
  granted. This is the same shape of gap the brief's Fix #3 already solved
  for interview-finish (`reports_pg.finish_interview`'s single transaction)
  but has **not** been solved here: wiring Step 3's payments route should
  either wrap `mark_paid` + the profile grant in one transaction (mirroring
  `finish_interview`'s pattern) or explicitly accept the gap with a documented
  reconciliation plan — currently neither has been decided. Flagged as a
  concrete design question for whoever wires this route, not an oversight to
  silently paper over.
- **Order-of-work matters for Step 3 itself**: payments should be wired
  *after* profiles (since `set_plan`/`increment_credits` are profile writes)
  and after `oa_attempts`/interviews/reports (since a broken attempt-credit
  flow is easier to debug once the simpler collections are already proven
  live under real traffic) — the brief's own suggested order already reflects
  this (step 3 before step 5 in the brief's numbering), this plan doesn't
  change it, just confirms it.

### Test coverage — Step 3

Every collection's repository module has mocked unit tests + one live
Supabase-flow test:

| Collection | Mocked repo tests | Live test |
|---|---|---|
| `oa_attempts`+`oa_attempt_keys` | `test_repositories_oa_attempts_pg.py` (10) | `test_oa_attempts_pg_create_attempt_real_race_and_hidden_answer_keys` |
| `profiles` | `test_repositories_profiles_pg.py` (15) | `test_profiles_pg_live_flow_and_deduct_credit_concurrency` |
| `resumes` | `test_repositories_resumes_pg.py` (6) | `test_resumes_pg_live_flow` |
| `game_sessions` | `test_repositories_game_sessions_pg.py` (5) | `test_game_sessions_pg_live_flow` |
| `ai_assisted_sessions` | `test_repositories_ai_assisted_sessions_pg.py` (5) | `test_ai_assisted_sessions_pg_live_flow` |
| `interviews` | `test_repositories_interviews_pg.py` (8) | `test_interviews_pg_live_roundtrip_with_capgemini_shaped_data` |
| `reports` | `test_repositories_reports_pg.py` (8) | `test_reports_pg_finish_interview_atomicity_live` |
| `question_seen` | `test_repositories_question_seen_pg.py` (5) | `test_question_seen_pg_live_flow` |
| `review_deck` | `test_repositories_review_deck_pg.py` (7) | `test_review_deck_pg_live_flow` |
| `orders` | `test_repositories_orders_pg.py` (4) | `test_orders_pg_live_flow_and_idempotent_mark_paid` |

**Gaps, same shape as Step 1's:**

- **No route-level test exists for any Step 3 route under
  `DB_BACKEND=supabase`.** The Mongo-path behavior of every route in the
  table above is covered today by some combination of `backend_test.py`
  (live HTTP — and remember, broken by Step 2's deletions unless fixed
  first), and targeted unit tests (`test_oa_draw_persistence.py`,
  `test_oa_section_order_enforcement.py`, `test_interview_oa_independence.py`,
  `test_real_mongo_turn_claim.py`, `test_dsa_hints_real_mongo_race.py`,
  `test_resume_ownership.py`, `test_commit_interview.py`/`test_dave_interview.py`/
  `test_spark_interview.py`/`test_tcs_interview.py`, `test_commit_report_route.py`/
  `test_dave_report_route.py`/`test_spark_report_route.py`). None of these
  parametrize over `DB_BACKEND`, and several (`test_real_mongo_turn_claim.py`,
  `test_dsa_hints_real_mongo_race.py`) are explicitly named "real mongo" —
  they exercise the turn-claim/race behavior against a **real Mongo
  instance**, which has no Postgres-path sibling test today. The
  interview-answer route's optimistic-concurrency behavior
  (`_claim_turn_or_409`) specifically needs a "real Postgres" equivalent of
  `test_real_mongo_turn_claim.py` before Step 3 ships that route, not just
  the generic `interviews_pg` mocked tests.
- **`POST /payments/order` and `POST /payments/verify` have no live-HTTP
  test today beyond `backend_test.py`'s `test_mock_payment_flow`/
  `test_free_plan_order_invalid`** (both Razorpay-mocked, Mongo-backed, and
  both inside the file that breaks under Step 2 — see above). Given this
  route's financial sensitivity (see risk notes), it should not ship on
  `DB_BACKEND=supabase` with only the generic `orders_pg`/`profiles_pg`
  mocked+live-repo tests as coverage; a dedicated route-level test
  (mock Razorpay + real/test Postgres, double-verify-is-idempotent,
  asserting the transaction gap noted above either doesn't matter or is
  fixed) should exist before cutover, not be inferred as "probably fine"
  from the repository-level tests alone.

---

## Gaps — consolidated punch list

Missing repository functions / behavior:

1. `mcq_pool_pg.py` has no equivalent of `pool_stats()`'s `pool_counts`
   aggregation (group `mcq_pool` rows by company_name/section_key) — needed
   for full parity on `GET /admin/mcq-stats`.
2. `mcq_pool_pg.py`'s write side (`_record_outcome`'s upsert-with-counters)
   is explicitly out of scope — fine for Step 1 reads, but the background
   pool-generation **worker** still writes only to Mongo; flipping
   `DB_BACKEND=supabase` while the worker runs drains the Postgres pool with
   no replenishment (see Step 1 risk notes) — needs a product-owner decision
   (pause the worker, or build its Postgres write path) before Step 1 goes
   live in production.
3. `mcq_static_bank_pg.py`'s content-read functions don't cover
   `sample_static_with_reuse`'s least-recently-seen sort, since that needs
   `question_seen` (a Step 3 table) — a sequencing decision is needed:
   either defer those two sampling functions until `question_seen_pg` is
   wired, or pull `question_seen_pg` forward as a Step 1 prerequisite.
4. `capgemini_round1_bank`/`capgemini_round2_bank` reads are inline in
   `server.py` (not behind a module boundary like the other five banks) —
   recommend extracting `capgemini_recruitment_process.fetch_round1_pool()`/
   `fetch_round2_pool()` first, so the `DB_BACKEND` fork can live there
   instead of being added ad hoc at 7 inline call sites in `server.py`.
5. `profiles_pg.py` has no equivalent of `_create_user_record`'s
   bypass-email founder-plan grant + default free-plan-quota initialization
   — new Supabase-Auth-provisioned users get a bare row from
   `handle_new_user()` with no plan defaults set anywhere. Needs a new
   function (e.g. `ensure_default_plan`) or a trigger extension (schema
   change, must go through the product owner per Ground Rule 6). Flagged as
   required work before Step 2 ships, not optional.
6. The payments-grant sequence (`orders_pg.mark_paid` →
   `profiles_pg.set_plan`/`increment_credits`) is not wrapped in one
   transaction the way `reports_pg.finish_interview` wraps its own
   multi-statement finish sequence — a crash between the two leaves an order
   `paid` with nothing granted. Needs either a transaction-wrapped
   combined function (mirroring `finish_interview`'s pattern) or an explicit,
   documented decision to accept the gap.
7. `review_deck`'s `card_id` lookup goes through `data->>'card_id'` with no
   dedicated index (schema constraint, not agent-created) — functionally
   correct at current (empty/low) volume, worth a follow-up index if
   `review_deck` usage grows; not a blocker.

Missing test coverage (flagged as follow-up work needed before/alongside
the relevant step, not an assumed given):

8. No route-level test (as opposed to repository-level) exists for any
   route in Step 1 or Step 3 with `DB_BACKEND=supabase` — every route's
   Postgres-path coverage today is the generic mocked repo test +
   `test_live_supabase_integration.py`'s live-flow check, neither of which
   goes through the actual FastAPI route handler, entitlement checks, or
   response shaping.
9. `backend_test.py` (the main live-HTTP regression suite covering
   signup/login/me, companies, pricing, payments, dashboard, OA
   start/section-submit, interview flow, final report, quota exhaustion)
   authenticates via `POST /auth/signup`, a route Step 2 deletes — its
   fixtures must be rewritten to mint a Supabase Auth token before or
   alongside Step 2, or this file's entire coverage (spanning routes in all
   three steps) silently breaks at collection time.
10. `test_route_table_integrity.py`'s committed `route_table_snapshot.json`
    must be regenerated in the same diff as Step 2's route deletions.
11. No Postgres-path equivalent exists for `test_real_mongo_turn_claim.py`/
    `test_dsa_hints_real_mongo_race.py` (real-Mongo-backed concurrency tests
    for the interview turn-claim mechanism) — needed before
    `POST /interview/{interview_id}/answer` ships on `DB_BACKEND=supabase`.
12. `POST /payments/order`/`POST /payments/verify` have no dedicated
    route-level test today beyond the two Mongo-backed, mocked-Razorpay
    tests inside `backend_test.py` (itself broken by Step 2, see #9) — given
    this route's financial sensitivity, a dedicated Postgres-backed
    route-level test (double-verify idempotency, the transaction-gap in #6)
    should exist before this route ships on `DB_BACKEND=supabase`.
13. `GET /admin/mcq-stats` has no test at all today, Mongo or Postgres —
    both should exist before/alongside Step 1's full-parity fix for gap #1.
