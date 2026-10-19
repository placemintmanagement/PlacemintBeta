-- Hiretric: Supabase (Postgres) schema, designed from the MongoDB "placemint" database.
-- Paste into Supabase: SQL Editor -> New query -> Run.
--
-- Design rules
--  * Fields you filter or join on are real columns. Deeply nested, type-specific
--    data (puzzles, sections, transcripts) stays in jsonb, so nothing is lost.
--  * Row Level Security is ON for every table. The FastAPI backend connects with
--    the database/service credentials, which bypass RLS. The browser can only
--    read its own profile, reports and resumes. Question banks and attempts hold
--    answer keys, so the browser gets NO direct access to them.
--  * Users come from Supabase Auth (auth.users). Auth0 fields, password hashes
--    and the old user_sessions collection are dropped.

-- ============================================================ USERS
create table if not exists public.profiles (
  id                 uuid primary key references auth.users(id) on delete cascade,
  name               text,
  picture_url        text,
  college            text,
  branch             text,
  graduation_year    text,
  target_role        text,
  company_selections text[] not null default '{}',
  plan               text not null default 'free',
  plan_started_at    timestamptz,
  plan_expires_at    timestamptz,
  credits            integer not null default 0,
  runs_quota         integer not null default 0,
  runs_used          integer not null default 0,
  runs_period_start  timestamptz,
  is_internal_tester boolean not null default false,
  created_at         timestamptz not null default now()
);

-- Create a profile automatically whenever someone signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, name, picture_url)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'name', new.raw_user_meta_data->>'full_name'),
    new.raw_user_meta_data->>'avatar_url'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============================================================ CONTENT (copied from Mongo)
create table if not exists public.mcq_static_bank (
  question_id     text primary key,
  topic           text,
  subtopic        text,
  subtype         text,
  question_style  text,
  difficulty      text,
  prompt          text not null,
  options         jsonb not null default '[]',
  correct_index   integer,
  explanation     text,
  chart           jsonb,
  svg_diagram     text,
  ground_truth_source text,
  verified_by     text,
  source_batch    text,
  date_added      text
);
create index if not exists mcq_static_bank_topic_idx on public.mcq_static_bank (topic, question_id);

create table if not exists public.mcq_pool (
  pool_id         text primary key,
  company_name    text not null,
  section_key     text not null,
  verified        boolean not null default false,
  difficulty      text,
  prompt          text not null,
  options         jsonb not null default '[]',
  correct_index   integer,
  explanation     text,
  ground_truth_source text,
  created_at      timestamptz
);
create index if not exists mcq_pool_lookup_idx on public.mcq_pool (company_name, section_key, verified);

create table if not exists public.mcq_pool_stats (
  company_name    text not null,
  section_key     text not null,
  total_generated integer not null default 0,
  outcome_accepted integer not null default 0,
  outcome_dropped_explanation_conflict integer not null default 0,
  outcome_dropped_explanation_failure  integer not null default 0,
  outcome_dropped_no_ground_truth      integer not null default 0,
  source_execution integer not null default 0,
  source_solver_agreement integer not null default 0,
  source_transpile_execution integer not null default 0,
  created_at      timestamptz,
  updated_at      timestamptz,
  primary key (company_name, section_key)
);

create table if not exists public.puzzle_bank (
  puzzle_id       text not null,
  game_type       text not null,
  company_tags    text[] not null default '{}',
  content_hash    text,
  explanation     text,
  data            jsonb not null default '{}',   -- every type-specific field (grid, blocks, walls, ...)
  primary key (game_type, puzzle_id)
);
create index if not exists puzzle_bank_tags_idx on public.puzzle_bank using gin (company_tags);

create table if not exists public.capgemini_round1_bank (
  id              bigint generated always as identity primary key,
  section         text,
  item_type       text,
  difficulty      text,
  question_id     text,
  data            jsonb not null                  -- the complete original document
);
create index if not exists capgemini_r1_section_idx on public.capgemini_round1_bank (section, item_type);
create index if not exists capgemini_r1_qid_idx on public.capgemini_round1_bank (question_id);

create table if not exists public.capgemini_round2_bank (
  scenario_id     text primary key,
  section         text,
  domain          text,
  batch_number    integer,
  scenario_title  text,
  scenario_text   text,
  questions       jsonb not null default '[]'
);

create table if not exists public.gamified_round_config (
  company         text primary key,
  draw_count      integer,
  game_types      text[] not null default '{}',
  per_type        jsonb not null default '{}',
  draw_note       text
);

-- ============================================================ USER DATA (empty at first)
create table if not exists public.resumes (
  resume_id        text primary key,
  user_id          uuid not null references public.profiles(id) on delete cascade,
  company_id       text,
  role             text,
  resume_text_sample text,
  analysis         jsonb,
  created_at       timestamptz not null default now()
);
create index if not exists resumes_user_idx on public.resumes (user_id);

create table if not exists public.oa_attempts (
  attempt_id       text primary key,
  user_id          uuid not null references public.profiles(id) on delete cascade,
  company_id       text,
  company_name     text,
  cluster          text,
  status           text,
  generation_status text,
  scoring_mode     text,
  charged_source   text,
  current_section_index integer not null default 0,
  resume_id        text,
  created_at       timestamptz not null default now(),
  completed_at     timestamptz,
  sections         jsonb not null default '[]',   -- questions served (server only: contains answers)
  answers          jsonb not null default '{}',
  section_results  jsonb not null default '{}'
);
create index if not exists oa_attempts_user_idx on public.oa_attempts (user_id, created_at desc);

-- Answer keys live apart so they can never leak through the attempt row.
create table if not exists public.oa_attempt_keys (
  attempt_id       text primary key references public.oa_attempts(attempt_id) on delete cascade,
  answer_keys      jsonb not null default '{}'
);

create table if not exists public.game_sessions (
  session_id       text primary key,
  attempt_id       text,
  user_id          uuid not null references public.profiles(id) on delete cascade,
  company          text,
  game_type        text,
  section_key      text,
  raw_score        integer,
  running_score    integer,
  correct          integer,
  incorrect        integer,
  total            integer,
  created_at       timestamptz not null default now(),
  graded_at        timestamptz,
  data             jsonb not null default '{}'    -- live_checks, gradingByType, puzzle ids, moves
);
create index if not exists game_sessions_user_idx on public.game_sessions (user_id, game_type);

create table if not exists public.ai_assisted_sessions (
  session_id       text primary key,
  attempt_id       text,
  user_id          uuid not null references public.profiles(id) on delete cascade,
  company_name     text,
  section_key      text,
  problem_id       text,
  status           text,
  current_stage    text,
  consent_given    boolean,
  created_at       timestamptz not null default now(),
  completed_at     timestamptz,
  data             jsonb not null default '{}'    -- problem, transcript, stage_attempts, final_outcome, ...
);
create index if not exists ai_sessions_user_idx on public.ai_assisted_sessions (user_id, created_at desc);

create table if not exists public.interviews (
  interview_id     text primary key,
  attempt_id       text,
  user_id          uuid not null references public.profiles(id) on delete cascade,
  resume_id        text,
  company_name     text,
  status           text,
  current_index    integer not null default 0,
  created_at       timestamptz not null default now(),
  completed_at     timestamptz,
  questions        jsonb not null default '[]',
  answers          jsonb not null default '[]'
);
create index if not exists interviews_user_idx on public.interviews (user_id, created_at desc);

create table if not exists public.reports (
  report_id        text primary key,
  attempt_id       text,
  user_id          uuid not null references public.profiles(id) on delete cascade,
  company_name     text,
  created_at       timestamptz not null default now(),
  oa_summary       jsonb,
  interview_summary jsonb,
  resume_analysis  jsonb,
  report           jsonb
);
create index if not exists reports_user_idx on public.reports (user_id, created_at desc);

-- One table replaces the five "*_seen" collections.
-- bank: ai_assisted | capgemini | debugging | mcq_static | problem_bank
-- scope: the section or topic ('' when the bank has no sub-division)
create table if not exists public.question_seen (
  user_id          uuid not null references public.profiles(id) on delete cascade,
  bank             text not null,
  scope            text not null default '',
  question_ids     text[] not null default '{}',
  seen_at          jsonb not null default '{}',
  updated_at       timestamptz not null default now(),
  primary key (user_id, bank, scope)
);

create table if not exists public.review_deck (
  id               bigint generated always as identity primary key,
  user_id          uuid not null references public.profiles(id) on delete cascade,
  source_attempt_id text,
  section_key      text,
  question_id      text,
  added_at         timestamptz not null default now(),
  data             jsonb not null default '{}',
  unique (user_id, source_attempt_id, section_key, question_id)
);
create index if not exists review_deck_user_idx on public.review_deck (user_id, added_at desc);

-- ============================================================ SECURITY (RLS)
alter table public.profiles              enable row level security;
alter table public.mcq_static_bank       enable row level security;
alter table public.mcq_pool              enable row level security;
alter table public.mcq_pool_stats        enable row level security;
alter table public.puzzle_bank           enable row level security;
alter table public.capgemini_round1_bank enable row level security;
alter table public.capgemini_round2_bank enable row level security;
alter table public.gamified_round_config enable row level security;
alter table public.resumes               enable row level security;
alter table public.oa_attempts           enable row level security;
alter table public.oa_attempt_keys       enable row level security;
alter table public.game_sessions         enable row level security;
alter table public.ai_assisted_sessions  enable row level security;
alter table public.interviews            enable row level security;
alter table public.reports               enable row level security;
alter table public.question_seen         enable row level security;
alter table public.review_deck           enable row level security;

-- The browser may read only its own profile, reports and resumes. Everything else
-- has no policy, so only the backend can touch it.
drop policy if exists "own profile read" on public.profiles;
create policy "own profile read" on public.profiles
  for select to authenticated using (id = (select auth.uid()));

drop policy if exists "own reports read" on public.reports;
create policy "own reports read" on public.reports
  for select to authenticated using (user_id = (select auth.uid()));

drop policy if exists "own resumes read" on public.resumes;
create policy "own resumes read" on public.resumes
  for select to authenticated using (user_id = (select auth.uid()));
