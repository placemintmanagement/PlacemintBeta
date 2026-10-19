-- Hiretric: Supabase migration, part 3 -- two columns schema.sql's
-- `interviews` table is missing, found while porting the real
-- `db.interviews` call sites in backend/server.py (phase 3 of the
-- migration, "port user-data features"). NOT YET RUN against the live
-- Supabase project -- paste into Supabase: SQL Editor -> New query -> Run,
-- after reviewing. Purely additive (ADD COLUMN IF NOT EXISTS on an
-- already-empty table), so safe to run at any time; nothing in
-- repositories/interviews_pg.py or reports_pg.py executes this -- the
-- product owner runs it themselves, same convention as 002_....sql.
--
-- What's missing and why:
--  1. `company_id` -- server.py queries interviews directly by company_id
--     in at least two places: `_existing_in_progress_interview` (~3761-3763:
--     `db.interviews.find_one({"user_id": ..., "company_id": ...,
--     "status": "in_progress"})`) and the plain-interview creation doc
--     itself (~3960: `"company_id": company_id`). schema.sql only has
--     `company_name`, not `company_id` -- these are different values
--     (id is the stable slug used for lookups/caps; name is display-only),
--     so company_name can't stand in for it.
--  2. `data` jsonb -- every OTHER user-data table in schema.sql (oa_attempts,
--     game_sessions, ai_assisted_sessions, reports, review_deck) has
--     somewhere to put nested/type-specific fields; `interviews` does not,
--     but the real interview documents carry plenty of fields with no
--     promoted column: the Capgemini-style interview modes (Spark/Dave/
--     Commit/TCS -- see _start_spark_interview, server.py ~4497-4532) store
--     tier, tier_source, candidate_name, mode, state, turn_count,
--     current_question, project, project_text, dsa_problem_id, dsa_flags,
--     turns, usage, flag_review, spark_score -- none of which fit the
--     existing columns. This is an oversight in the original schema.sql
--     (the migration brief's own mapping table says "interviews, reports,
--     resumes | same | Nested parts are jsonb", i.e. a `data` column was
--     always the intent), not a deliberate omission.

alter table public.interviews add column if not exists company_id text;
alter table public.interviews add column if not exists data jsonb not null default '{}';

create index if not exists interviews_company_idx on public.interviews (user_id, company_id, status);
