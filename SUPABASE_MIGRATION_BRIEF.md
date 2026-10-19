# Hiretric: MongoDB + Auth0 -> Supabase (Postgres + Auth)

Brief for Claude Code, plus the product owner's decisions on the inventory. This is
the source of truth for the migration — read it before touching any migration code.

## Context

- Product: company-specific placement OA and interview simulator (placeholder repo
  name PLACEMINT-BETA). Stack: React frontend, FastAPI backend (Cloud Run target),
  MongoDB Atlas (db `placemint`), Auth0, Razorpay payments.
- Decision: move the database to Supabase Postgres and replace Auth0 with Supabase
  Auth.
- There are **no real users**. Existing user records are test data and are NOT
  being migrated. Start clean on Supabase Auth — no backfill.
- The Supabase project exists (Mumbai, ap-south-1). `supabase/schema.sql` has
  already been run there. Content has already been copied and verified by count
  (confirmed against the live Mongo DB during inventory, all exact matches):
  `mcq_static_bank` 8795, `mcq_pool` 326, `mcq_pool_stats` 48, `puzzle_bank` 1280,
  `capgemini_round1_bank` 350, `capgemini_round2_bank` 19, `gamified_round_config` 4.
- `supabase/002_orders_and_oa_attempts_race_fix.sql` has also already been run
  (2026-10-19) — adds the `orders` table and the `oa_attempts` race-fix index
  (see "Decisions on the inventory" below).
- MongoDB stays the live database until the Supabase branch passes every check in
  "Done means" below.

## Ground rules

1. Work on this branch (`supabase-migration`). Do not touch `design-rollout`/`main`
   or the live Mongo config.
2. Never print, log or commit secrets. Connection strings and keys go in `.env`
   (already in `.gitignore`). The product owner puts secrets in `.env` themselves —
   never ask for them in chat, never print or commit them.
3. Read the code first. An inventory of every place the code touches MongoDB,
   Auth0, and user ids was already produced (2026-10-19, by a dedicated read-only
   task) and reviewed by the product owner — see "Inventory findings" below.
   Don't re-derive it; extend it if something new turns up.
4. Introduce one repository / data-access layer so the database swap is isolated,
   instead of scattering SQL through route handlers. Keep the existing pytest
   suite green.
5. Make small, reviewable commits.
6. Any SQL that needs to run against the live Supabase project goes in a numbered
   file under `supabase/` and gets shown to the product owner first — they run it
   themselves in the Supabase SQL Editor. Nothing in this migration ever executes
   DDL against Supabase directly from the agent.

## Target schema (already created, see `supabase/schema.sql`)

Content tables (backend-only, no browser access): `mcq_static_bank`, `mcq_pool`,
`mcq_pool_stats`, `puzzle_bank`, `capgemini_round1_bank`, `capgemini_round2_bank`,
`gamified_round_config`.
User tables: `profiles`, `resumes`, `oa_attempts`, `oa_attempt_keys`,
`game_sessions`, `ai_assisted_sessions`, `interviews`, `reports`, `question_seen`,
`review_deck`, `orders`.

### Collection -> table mapping and field changes

| Mongo collection | Postgres table | Notes |
|---|---|---|
| users | profiles | `id` is the Supabase auth user uuid. Email lives in `auth.users`. Dropped: `auth0_sub`, `auth_provider`, `password_hash`, `email_verified`, `picture` (now `picture_url`), `user_id`. Kept: name, college, branch, graduation_year, target_role, company_selections (text[]), plan, plan_started_at, plan_expires_at, credits, runs_quota, runs_used, runs_period_start, is_internal_tester, created_at |
| user_sessions | (dropped) | Supabase Auth issues sessions |
| mcq_static_bank | mcq_static_bank | `options` and `chart` are jsonb |
| mcq_pool, mcq_pool_stats | same names | `created_at` / `updated_at` are timestamptz |
| puzzle_bank | puzzle_bank | PK (game_type, puzzle_id). `gameType` -> `game_type`, `companyTags` -> `company_tags`. All other type-specific fields (grid, blocks, walls, candidates, ...) are inside the jsonb column `data`. Write a helper that merges `data` back with the top-level columns so callers still see the old document shape |
| capgemini_round1_bank | same | Whole original document is in jsonb `data`; helper returns `data` |
| capgemini_round2_bank | same | `questions` is jsonb |
| gamified_round_config | same | `perType` -> `per_type`, `drawCount` -> `draw_count`, `gameTypes` -> `game_types`, `_drawNote` -> `draw_note` |
| oa_attempts | oa_attempts + oa_attempt_keys | `_hidden_answer_keys` moves to `oa_attempt_keys.answer_keys`. **Never return it, nor `sections[].questions[].correct_*` fields, to the browser**. One in-progress attempt per (user_id, company_id) enforced by a partial unique index (already applied, see `supabase/002_...sql`) |
| game_session (singular in Mongo) | game_sessions | Common fields are columns; the rest (live_checks, gradingByType, puzzle ids, moves) is jsonb `data` |
| ai_assisted_sessions | same | problem, transcript, stage_attempts, final_outcome, etc. in jsonb `data` |
| interviews, reports, resumes | same | Nested parts are jsonb |
| ai_assisted_bank_seen, capgemini_bank_seen, debugging_bank_seen, mcq_static_bank_seen, problem_bank_seen | question_seen | Key is (user_id, bank, scope). bank = `ai_assisted` (scope ''), `capgemini` (scope = section), `debugging` (scope ''), `mcq_static` (scope = topic), `problem_bank` (scope = topic) |
| review_deck | review_deck | Currently empty |
| orders *(not in original brief — added after inventory)* | orders | Keyed on the Razorpay order id itself. UNIQUE on `razorpay_payment_id` so a payment can never be credited via two different orders (DB-level half of idempotent crediting — app code still must no-op a retried verify call on the *same* order by checking `status='paid'` first) |

All `user_id` values become the Supabase user uuid. No backfill needed (no real
users). Timestamps that were ISO strings become timestamptz; keep API responses
returning ISO strings so the frontend does not break.

### Mongo -> Postgres translation notes

- `$sample` / random draws: `order by random() limit n`. **Apply this fix for
  real, don't just replicate Mongo's non-randomness** — the inventory found
  `game_session`/`puzzle_bank` draws were never actually using `$sample` in Mongo
  (plain `find` + `$nin`, no shuffle), so this is a genuine behavior improvement,
  not a faithfulness risk. Keep the existing "not already seen" filter behaving
  exactly as it does now otherwise.
- Upserts: `insert ... on conflict (...) do update`.
- `$addToSet` / `$push` on `question_ids`: use
  `array(select distinct unnest(question_ids || new_ids))` or `array_append` with
  a not-exists check, inside one statement.
- `$inc` (for example `runs_used`, `credits`): `update ... set runs_used =
  runs_used + 1 ... returning ...`. Keep it atomic. **Fix the credit-deduction
  race found in the inventory**: use
  `update ... set credits = credits - 1 where credits > 0 returning credits`
  and treat zero rows returned as "no credits" — don't just port the old
  check-then-`$inc` pattern.
- Replace any use of `_id` / ObjectId with the primary keys above. The inventory
  found exactly one spot that relied on Mongo's native `_id` (the legacy
  `auth_tokens` email-verify/reset-token update) — moot, since that whole flow is
  being deleted, not ported (see "Decisions on the inventory" below).
- **Each report/interview "finish" sequence (delete-then-insert, found at three
  near-duplicate call sites in the inventory) must run inside a single Postgres
  transaction** — not three independent statements like the Mongo version.

## Database access

- Use `psycopg` 3 (async pool) or `asyncpg`. Connect to Postgres directly with the
  connection string from `SUPABASE_DB_URL` (Supabase pooler, IPv4 friendly).
  Session pooler is port 5432. If using the Transaction pooler (port 6543),
  disable prepared statements (`prepare_threshold=None` in psycopg).
- The backend connects with the database owner credentials, which bypass Row
  Level Security. RLS is on for every table; the only browser-readable data is
  the user's own `profiles`, `reports` and `resumes` rows (and now `orders`, added
  after the inventory — same pattern). Keep it that way. Do not add public
  policies on banks, attempts or answer keys.

## Auth: Auth0 -> Supabase Auth

- Frontend: replace the Auth0 SDK with `@supabase/supabase-js`. Provide email
  login and Google sign-in (the product owner enables the Google provider and
  adds redirect URLs in Supabase Auth settings — tell them exactly what to click
  when this phase starts). Send `Authorization: Bearer <access_token>` to
  FastAPI.
- Backend: verify the Supabase JWT on every protected route (use the project's
  JWKS endpoint at `<SUPABASE_URL>/auth/v1/.well-known/jwks.json` with PyJWT, or
  the legacy JWT secret if that is what the project exposes). The user id is the
  token `sub` (uuid). Remove all Auth0 verification code and env vars.
- A profile row is created automatically by `public.handle_new_user()` (database
  trigger on `auth.users` insert, already in `schema.sql`). Make sure the backend
  tolerates the brief moment before it exists, and does upserts of onboarding
  fields (college, branch, graduation_year, target_role, company_selections) on
  `profiles`.
- Env vars the frontend needs: `SUPABASE_URL`, `SUPABASE_ANON_KEY` (public).
  Backend: `SUPABASE_DB_URL`, `SUPABASE_URL`. Never expose the service role key or
  DB URL to the frontend.
- **Decision: delete the legacy routes, don't port them.** The inventory found
  BOTH a parallel Auth0 path (the only one actually reachable — everything is
  Auth0-gated via `require_user` today) AND a dead-end legacy Google-session +
  email/password flow that still writes to Mongo on every call but can never
  reach a `Depends(require_user)` route. Delete `/auth/signup`, `/auth/login`,
  `/auth/google/session`, `/auth/logout`, `/auth/email/send-verification`,
  `/auth/email/verify`, `/auth/password/forgot`, `/auth/password/reset`, and the
  `auth_tokens` collection/table entirely. Supabase Auth handles email
  verification and password reset natively — no replacement code needed for
  those flows.

## Payments

- **Correction from the inventory: there is no Paddle integration anywhere in
  this codebase.** Out of scope — Razorpay only. (If Paddle is wanted later,
  that's new scope, not part of this migration.)
- Razorpay is **not** a server-to-server webhook today — it's a client-driven
  flow: `/payments/order` creates a Razorpay order + an `orders` row server-side;
  the frontend completes checkout directly with Razorpay; `/payments/verify`
  re-verifies the HMAC signature server-side and grants the plan/credits. **Keep
  this flow exactly as it is** — don't build a new webhook handler as part of
  this migration.
- Fields updated on success, by `kind`: `plan` → `profiles.plan`,
  `profiles.runs_used=0`, `profiles.plan_started_at`, `profiles.runs_period_start`,
  `profiles.plan_expires_at`; `credits` → `profiles.credits` via an atomic
  increment. Either way: `orders.status → 'paid'`, `orders.razorpay_payment_id`,
  `orders.paid_at`.
- Re-key to the new Supabase uuid (`orders.user_id`) — this is a drop-in rename
  since the app's `user_id` was already an opaque, provider-independent string
  even on Mongo (confirmed by the inventory), not something coupled to Razorpay
  identity.
- Make crediting idempotent per payment id: the `orders.razorpay_payment_id`
  UNIQUE constraint is the DB-level guarantee (a payment can never attach to two
  different orders); the app code must also treat a retried `/payments/verify`
  call on the *same already-paid* order as a no-op (check `status = 'paid'`
  first, don't grant credits/plan twice).
- **Decision: leave unpaid-order reconciliation for later. Do not build it.**
  Orders that never get `/payments/verify` called stay `status: 'created'`
  forever — same as today, not a regression, not in scope for this migration.

## Suggested order of work

1. ~~Inventory (Mongo calls, Auth0 calls, user-id usage, payment hooks).~~ Done
   2026-10-19, reviewed, decisions folded into this doc.
2. Add the repository layer + Postgres connection, with read-only content
   queries first (banks, puzzles, configs). Test against the real Supabase
   content.
3. Port user-data features: profiles, attempts (+ keys), game sessions,
   AI-assisted sessions, interviews, reports, resumes, seen-tracking, review
   deck, orders.
4. Swap auth (backend JWT verify, then frontend) — delete the legacy routes in
   the same phase.
5. Port payment webhooks (really: the client-driven order/verify flow — no new
   webhook).
6. Update `.env.example`, README and Cloud Run deployment notes.

## Done means all of these pass on the Supabase branch

- Sign up, log in, log out (email and Google).
- Start and finish a full OA run for one company; score and report are produced.
- Interview flow and AI-assisted coding flow complete.
- Seen-question tracking does not repeat questions for the same user.
- A test purchase (Razorpay test mode) updates plan and credits exactly once,
  even if `/payments/verify` is called twice for the same payment.
- No browser response contains answer keys (`correct_index`, `correct_option`,
  `_hidden_answer_keys`, `answer_keys`) before the answer is submitted.
- Existing pytest suite passes; new tests cover the repository layer.
- A written summary of every change and every environment variable to set in
  Cloud Run.

Only after all of the above, the product owner decides when to switch production.
Keep the Mongo cluster for about a week afterwards as a fallback.

---

## Inventory findings (2026-10-19, read-only task)

Full detail lives in this session's history; the load-bearing findings are
folded into the sections above. Headline points not already covered elsewhere
in this doc:

- `user_id` is already an opaque, app-minted string (`user_<hex>`), decoupled
  from the auth provider on Mongo too — the migration's uuid switch is a value
  backfill of one field per collection, not a schema-wide redesign.
- `auth0_sub` is only used as a provisioning/lookup key inside `require_user` /
  `_create_user_record` — never propagated as a foreign key elsewhere. Swapping
  it for Supabase's uuid is localized.
- Live DB collection counts match the brief's claimed-copied numbers exactly
  (confirmed via a read-only ping + count check, no document values read).
- Two collections existed in code but not in the original brief's table:
  `orders` (now added to schema, see above) and `auth_tokens` (deleted, not
  ported — see "Auth" above).

## Decisions on the inventory (product owner, 2026-10-19)

1. **Paddle**: out of scope. Mistake in the original brief. Razorpay only.
2. **Legacy auth**: delete the dead Google-session and email/password routes and
   the `auth_tokens` collection. Do not port them. Supabase Auth handles email
   verification and password reset.
3. **orders**: added as a Postgres table (`supabase/002_orders_and_oa_attempts_race_fix.sql`,
   already run). PK = Razorpay order id; `user_id uuid references profiles(id)`;
   UNIQUE on the Razorpay payment id; RLS with an own-rows-read policy; jsonb
   column for leftover fields. Client-driven `/payments/verify` flow stays as is.
   Crediting made idempotent on the payment id.
4. **Races fixed while porting**:
   - Credit deduction: atomic `UPDATE ... WHERE credits > 0 RETURNING`, zero
     rows = no credits.
   - OA attempt "already in progress": partial unique index on `oa_attempts`
     (already applied) — only one in-progress attempt per (user, company).
   - Each report/interview finish sequence (delete then insert) runs in a single
     transaction.
5. **Random draws**: `ORDER BY random() LIMIT n`, keeping the existing
   "not already seen" filter behavior exactly as it is now.
6. **Unpaid-order reconciliation**: left for later. Not built as part of this
   migration.
7. **User ids**: no real users, no backfill. New accounts get Supabase uuids as
   `user_id` everywhere.
