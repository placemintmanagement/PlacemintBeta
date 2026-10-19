-- Hiretric: Supabase migration, part 2 -- orders table + oa_attempts race fix.
-- Paste into Supabase: SQL Editor -> New query -> Run. Run AFTER schema.sql.
-- ALREADY RUN against the live Supabase project (confirmed by the product owner
-- 2026-10-19) -- kept here as the source of truth / for replaying on a fresh
-- project, not as a pending action.
--
-- Covers two of the inventory's findings:
--  1. `orders` (Razorpay order lifecycle) was never in the original brief's
--     mapping table -- this adds it, keyed on the Razorpay order id itself,
--     with a UNIQUE constraint on the payment id so a payment can only ever
--     be attached to one order row (the DB-level half of idempotent crediting;
--     the app-level half -- checking `status = 'paid'` before granting credits
--     again on a retried /payments/verify call -- lives in the repository-layer
--     code, not here).
--  2. `oa_attempts`'s "already in progress" check was a check-then-insert race
--     in Mongo (read at server.py:1987-1990, insert ~75 lines later at :2072,
--     with awaits in between -- confirmed against the live code, both the
--     status string "in_progress" and the race itself). A partial unique
--     index closes this for real at the DB level.

-- ============================================================ ORDERS
create table if not exists public.orders (
  order_id            text primary key,                 -- the Razorpay order id itself
  user_id             uuid not null references public.profiles(id) on delete cascade,
  kind                text not null,                     -- 'plan' | 'credits'
  status              text not null default 'created',   -- 'created' -> 'paid'
  razorpay_payment_id text unique,                        -- set once, on /payments/verify; UNIQUE = can never be credited via two different orders
  created_at          timestamptz not null default now(),
  paid_at             timestamptz,
  data                jsonb not null default '{}'         -- amount, currency, plan/credits detail, raw signature -- anything not filtered/joined on
);
create index if not exists orders_user_idx on public.orders (user_id, created_at desc);

alter table public.orders enable row level security;

drop policy if exists "own orders read" on public.orders;
create policy "own orders read" on public.orders
  for select to authenticated using (user_id = (select auth.uid()));

-- No insert/update/delete policy for any role -- only the backend (service
-- credentials, which bypass RLS) can ever write an order row.

-- ============================================================ OA_ATTEMPTS: race fix
-- Only one IN-PROGRESS attempt per (user, company) can exist at a time.
-- Completed/abandoned attempts for the same user+company are unaffected --
-- this only constrains rows where status = 'in_progress'.
create unique index if not exists oa_attempts_one_in_progress_idx
  on public.oa_attempts (user_id, company_id)
  where status = 'in_progress';
