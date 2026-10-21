"""Live integration tests against the real Supabase Postgres instance --
exercises repositories/*_pg.py against ACTUAL SQL, not mocks. Skipped
entirely unless SUPABASE_DB_URL is set (see backend/.env): every other
test_repositories_*_pg.py file only ever monkeypatches fetch_one/fetch_all,
which proves the Python plumbing calls the right function with the right
arguments but can never prove the SQL itself is valid against the real
schema, that real Postgres semantics (jsonb_set's create_missing quirk,
partial unique indexes, row-level locking, FK cascades) behave the way a
docstring assumes, or that two real concurrent callers actually race the
way a mock can only simulate. This file is that missing proof.

Safety: every test that writes touches ONLY scratch rows it inserts itself
(a fresh auth.users row per test via `_scratch_user`, which the live
`handle_new_user()` trigger turns into a `profiles` row -- profiles.id is
FK'd to auth.users(id), so a bare profiles insert with a random uuid is
NOT possible against the real schema) and cleans up via try/finally even
on assertion failure, so a failing test can never leave scratch data
behind. Content-bank tables are read-only here. The module-scoped
`_assert_user_data_tables_empty` fixture below asserts every user-data
table is at 0 rows both before and after this file's tests run, as an
automatic residue detector.

Windows note: psycopg's async mode cannot run on the default
ProactorEventLoop (`Psycopg cannot use the 'ProactorEventLoop' to run in
async mode` -- confirmed by a live connection attempt, not from docs
alone). Switched to the Selector policy below; safe process-wide because
nothing in this codebase uses asyncio subprocess (confirmed by a
full-repo grep), which is the one thing that would need Proactor back.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager

import psycopg_pool
import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from db_postgres import close_pool, fetch_all, fetch_one, open_pool, transaction
from repositories import (
    ai_assisted_sessions_pg,
    capgemini_bank_pg,
    game_sessions_pg,
    interviews_pg,
    mcq_pool_pg,
    mcq_static_bank_pg,
    oa_attempts_pg,
    orders_pg,
    profiles_pg,
    puzzle_bank_pg,
    question_seen_pg,
    resumes_pg,
    reports_pg,
    review_deck_pg,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_DB_URL"),
    reason="needs a live Supabase Postgres connection (SUPABASE_DB_URL in backend/.env)",
)

USER_DATA_TABLES = (
    "profiles", "resumes", "oa_attempts", "oa_attempt_keys", "game_sessions",
    "ai_assisted_sessions", "interviews", "reports", "question_seen",
    "review_deck", "orders",
)

CONTENT_BANK_EXPECTED_COUNTS = {
    "mcq_static_bank": 8795,
    "mcq_pool": 326,
    "mcq_pool_stats": 48,
    "puzzle_bank": 1280,
    "capgemini_round1_bank": 350,
    "capgemini_round2_bank": 19,
    "gamified_round_config": 4,
}


_CONNECT_RETRY_ATTEMPTS = 3
_CONNECT_RETRY_BACKOFF_SECONDS = 5


def run(coro_factory):
    """Runs one async test body inside its own open_pool()/close_pool()
    lifecycle, all under a single event loop (required on Windows -- a
    pool opened under one loop cannot be reused from another).

    Retries a few times on psycopg_pool.PoolTimeout: this Supabase host has
    shown transient connection flakiness independent of any code change
    here (reproduced by hitting it directly, with no test load at all, and
    also seen as a `PoolTimeout: couldn't get a connection after 30.00 sec`
    on EVERY one of this file's 17 tests' very first query -- their
    module-scoped `_assert_user_data_tables_empty` fixture -- during one
    full-suite run under pytest-xdist, immediately after a standalone run
    of the same 17 tests had passed cleanly seconds earlier with no code
    in between). A fresh pool (via close_pool()) on each retry, since a
    pool that already timed out acquiring a connection is not assumed
    healthy to just retry against directly."""

    async def _wrapped():
        for attempt in range(1, _CONNECT_RETRY_ATTEMPTS + 1):
            await open_pool()
            try:
                await coro_factory()
                return
            except psycopg_pool.PoolTimeout:
                if attempt >= _CONNECT_RETRY_ATTEMPTS:
                    raise
                await asyncio.sleep(_CONNECT_RETRY_BACKOFF_SECONDS * attempt)
            finally:
                await close_pool()

    asyncio.run(_wrapped())


async def _table_counts() -> dict:
    out = {}
    for t in USER_DATA_TABLES:
        row = await fetch_one(f"SELECT count(*) AS n FROM {t}")
        out[t] = int(row["n"])
    return out


@asynccontextmanager
async def scratch_user():
    """Inserts one scratch auth.users row (triggering a `profiles` row via
    the live handle_new_user() trigger) and guarantees its deletion --
    cascading to every user-data table FK'd to profiles(id) -- even if the
    caller's block raises."""
    user_id = str(uuid.uuid4())
    await fetch_one(
        "INSERT INTO auth.users (id, email) VALUES (%s, %s) RETURNING id",
        (user_id, f"live-verify-{user_id}@scratch.invalid"),
    )
    try:
        yield user_id
    finally:
        await fetch_all("DELETE FROM auth.users WHERE id = %s RETURNING 1", (user_id,))


@pytest.fixture(scope="module", autouse=True)
def _assert_user_data_tables_empty():
    """Automatic residue detector: every user-data table must be at 0 rows
    both before this file's tests run (no real users exist yet) and after
    (every test must have cleaned up its own scratch rows)."""
    run(lambda: _check_empty("before"))
    yield
    run(lambda: _check_empty("after"))


async def _check_empty(when: str):
    counts = await _table_counts()
    assert all(n == 0 for n in counts.values()), f"user-data tables not empty {when} live tests: {counts}"


# ---------------------------------------------------------------------------
# 1. Schema check
# ---------------------------------------------------------------------------

def test_interviews_schema_has_company_id_and_data_columns():
    async def body():
        cols = await fetch_all(
            "SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='interviews'"
        )
        by_name = {c["column_name"]: c for c in cols}
        assert "company_id" in by_name, "003_interviews_missing_columns.sql not applied: company_id missing"
        assert by_name["company_id"]["data_type"] == "text"
        assert "data" in by_name, "003_interviews_missing_columns.sql not applied: data missing"
        assert by_name["data"]["data_type"] == "jsonb"
        assert by_name["data"]["is_nullable"] == "NO"
        assert by_name["data"]["column_default"] == "'{}'::jsonb"

        idx = await fetch_all(
            "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename='interviews'"
        )
        assert "interviews_company_idx" in {i["indexname"] for i in idx}

    run(body)


# ---------------------------------------------------------------------------
# 2. Content-bank live verification (read-only)
# ---------------------------------------------------------------------------

def test_content_bank_row_counts_match_expected():
    async def body():
        for table, expected in CONTENT_BANK_EXPECTED_COUNTS.items():
            row = await fetch_one(f"SELECT count(*) AS n FROM {table}")
            assert int(row["n"]) == expected, f"{table}: expected {expected}, got {row['n']}"

    run(body)


def test_mcq_static_bank_pg_shape_and_exclusion():
    async def body():
        row = await fetch_one("SELECT topic FROM mcq_static_bank LIMIT 1")
        topic = row["topic"]
        n = await mcq_static_bank_pg.count_by_topic(topic)
        assert n > 0
        sample = await mcq_static_bank_pg.sample_random_by_topic(topic, 5)
        assert sample
        expected_keys = {
            "question_id", "topic", "subtopic", "subtype", "question_style",
            "difficulty", "prompt", "options", "correct_index", "explanation",
            "chart", "svg_diagram", "ground_truth_source", "verified_by",
            "source_batch", "date_added",
        }
        assert set(sample[0].keys()) == expected_keys
        for r in sample:
            assert r["topic"] == topic

        ids = [r["question_id"] for r in sample]
        excluded = await mcq_static_bank_pg.sample_random_by_topic(topic, 50, exclude_ids=ids)
        assert not (set(ids) & {r["question_id"] for r in excluded}), "exclude_ids filter did not exclude"

        got_by_ids = await mcq_static_bank_pg.get_by_ids(ids)
        assert {r["question_id"] for r in got_by_ids} == set(ids)

    run(body)


def test_puzzle_bank_pg_merge_back_shape_and_exclusion():
    async def body():
        prow = await fetch_one("SELECT puzzle_id, game_type, company_tags FROM puzzle_bank LIMIT 1")
        puzzle = await puzzle_bank_pg.get_by_id(prow["puzzle_id"])
        assert "gameType" in puzzle and "companyTags" in puzzle, "merge-back to camelCase keys failed"
        assert "data" not in puzzle, "raw jsonb data column leaked unmerged"
        assert "game_type" not in puzzle and "company_tags" not in puzzle
        assert puzzle["gameType"] == prow["game_type"]

        company = prow["company_tags"][0] if prow["company_tags"] else None
        if company:
            sampled = await puzzle_bank_pg.sample_puzzles(company, prow["game_type"], None, 3)
            if sampled:
                ex_ids = [p["puzzle_id"] for p in sampled]
                excluded = await puzzle_bank_pg.sample_puzzles(company, prow["game_type"], ex_ids, 20)
                assert not (set(ex_ids) & {p["puzzle_id"] for p in excluded})

    run(body)


def test_gamified_round_config_pg_shape():
    async def body():
        crow = await fetch_one("SELECT company FROM gamified_round_config LIMIT 1")
        cfg = await puzzle_bank_pg.get_config(crow["company"])
        for key in ("drawCount", "perType", "gameTypes", "company"):
            assert key in cfg
        assert "draw_count" not in cfg and "per_type" not in cfg and "game_types" not in cfg

    run(body)


def test_capgemini_bank_pg_shapes():
    async def body():
        srow = await fetch_one("SELECT DISTINCT section FROM capgemini_round1_bank LIMIT 1")
        r1 = await capgemini_bank_pg.list_round1_by_section(srow["section"])
        assert r1
        for item in r1:
            assert "data" not in item  # already unwrapped to the whole document

        r2 = await capgemini_bank_pg.list_round2_all()
        assert len(r2) == CONTENT_BANK_EXPECTED_COUNTS["capgemini_round2_bank"]
        assert set(r2[0].keys()) == {
            "scenario_id", "section", "domain", "batch_number", "scenario_title",
            "scenario_text", "questions",
        }

    run(body)


# ---------------------------------------------------------------------------
# 3. mcq_pool_pg.pop_one -- REAL concurrency, scratch row only
# ---------------------------------------------------------------------------

def test_mcq_pool_pop_one_atomic_under_real_concurrency():
    scratch_company = "__live_verify_scratch__"
    scratch_section = "__live_verify_scratch__"

    async def body():
        pre = await fetch_one(
            "SELECT count(*) AS n FROM mcq_pool WHERE company_name=%s AND section_key=%s",
            (scratch_company, scratch_section),
        )
        assert pre["n"] == 0, "scratch key collided with pre-existing data -- aborting"

        pool_id = f"scratch-pool-{uuid.uuid4()}"
        await fetch_one(
            "INSERT INTO mcq_pool (pool_id, company_name, section_key, verified, prompt, options, correct_index) "
            "VALUES (%s, %s, %s, true, %s, %s, %s) RETURNING pool_id",
            (pool_id, scratch_company, scratch_section, "scratch prompt: 2+2=?", '["3","4","5"]', 1),
        )
        try:
            results = await asyncio.gather(
                mcq_pool_pg.pop_one(scratch_company, scratch_section),
                mcq_pool_pg.pop_one(scratch_company, scratch_section),
            )
            winners = [r for r in results if r is not None]
            losers = [r for r in results if r is None]
            assert len(winners) == 1, f"expected exactly one winner, got {results}"
            assert len(losers) == 1, f"expected exactly one None, got {results}"
            assert winners[0]["pool_id"] == pool_id
        finally:
            await fetch_all(
                "DELETE FROM mcq_pool WHERE company_name=%s AND section_key=%s RETURNING pool_id",
                (scratch_company, scratch_section),
            )

        post = await fetch_one(
            "SELECT count(*) AS n FROM mcq_pool WHERE company_name=%s AND section_key=%s",
            (scratch_company, scratch_section),
        )
        assert post["n"] == 0
        real_count = await fetch_one("SELECT count(*) AS n FROM mcq_pool")
        assert real_count["n"] == CONTENT_BANK_EXPECTED_COUNTS["mcq_pool"]

    run(body)


# ---------------------------------------------------------------------------
# 4. Phase 3 user-data repositories -- scratch profile per test
# ---------------------------------------------------------------------------

def test_profiles_pg_live_flow_and_deduct_credit_concurrency():
    async def body():
        async with scratch_user() as user_id:
            p1 = await profiles_pg.upsert_onboarding_fields(
                user_id, college="Test College", branch="CSE",
                graduation_year="2027", target_role="SDE", name="Scratch User",
            )
            assert p1["college"] == "Test College"

            bal = await profiles_pg.increment_credits(user_id, 5)
            assert bal == 5

            sel = await profiles_pg.add_company_selection(user_id, "tcs-nqt")
            assert sel == ["tcs-nqt"]
            sel_dedup = await profiles_pg.add_company_selection(user_id, "tcs-nqt")
            assert sel_dedup == ["tcs-nqt"], "add_company_selection must dedup, not append a duplicate"
            sel3 = await profiles_pg.add_company_selection(user_id, "capgemini")
            assert set(sel3) == {"tcs-nqt", "capgemini"}
            sel4 = await profiles_pg.remove_company_selection(user_id, "tcs-nqt")
            assert sel4 == ["capgemini"]

            setp = await profiles_pg.set_plan(
                user_id, "basic", runs_quota=10,
                plan_started_at="2026-01-01T00:00:00+00:00", plan_expires_at=None,
            )
            assert setp["plan"] == "basic" and setp["runs_used"] == 0

            # Force a stale 30-day window (basic resets_every_days=30) and confirm rollover fires.
            await fetch_one(
                "UPDATE profiles SET runs_used = 5, runs_period_start = now() - interval '40 days' "
                "WHERE id = %s RETURNING id",
                (user_id,),
            )
            reset_row = await profiles_pg.maybe_reset_period(user_id)
            assert reset_row is not None and reset_row["runs_used"] == 0
            reset_row_again = await profiles_pg.maybe_reset_period(user_id)
            assert reset_row_again is None, "a fresh window must not roll over again"

            # REAL concurrency: credits=1, two concurrent deduct_credit calls --
            # exactly one must land at 0, the other must see the floor and get None.
            await fetch_one("UPDATE profiles SET credits = 1 WHERE id = %s RETURNING id", (user_id,))
            results = await asyncio.gather(
                profiles_pg.deduct_credit(user_id),
                profiles_pg.deduct_credit(user_id),
            )
            succ = [r for r in results if r is not None]
            fail = [r for r in results if r is None]
            assert len(succ) == 1 and succ[0] == 0, f"expected exactly one success landing at 0, got {results}"
            assert len(fail) == 1, f"expected exactly one None (floor check), got {results}"
            final_profile = await profiles_pg.get_profile(user_id)
            assert final_profile["credits"] == 0

    run(body)


def test_resumes_pg_live_flow():
    async def body():
        async with scratch_user() as user_id:
            resume_id = f"scratch-resume-{uuid.uuid4()}"
            await resumes_pg.insert_resume(
                resume_id, user_id, "tcs-nqt", "SDE", "sample resume text",
                {"score": 88, "notes": ["good"]},
            )
            got = await resumes_pg.get_resume(resume_id, user_id)
            assert got is not None and got["analysis"]["score"] == 88

            other_user_got = await resumes_pg.get_resume(resume_id, str(uuid.uuid4()))
            assert other_user_got is None, "ownership scoping failed"

            got_by_id = await resumes_pg.get_resume_by_id(resume_id)
            assert got_by_id is not None

            lst = await resumes_pg.get_resumes_for_user(user_id)
            assert len(lst) == 1

            latest = await resumes_pg.get_latest_resume_for_company(user_id, "tcs-nqt")
            assert latest is not None and latest["resume_id"] == resume_id

    run(body)


def test_oa_attempts_pg_create_attempt_real_race_and_hidden_answer_keys():
    async def body():
        async with scratch_user() as user_id:
            company_id = "tcs-nqt"
            attempt_a = f"scratch-attempt-a-{uuid.uuid4()}"
            attempt_b = f"scratch-attempt-b-{uuid.uuid4()}"

            # THE single most important live check in this task: two real
            # concurrent create_attempt calls for the SAME (user_id,
            # company_id) racing against the live partial unique index
            # (oa_attempts_one_in_progress_idx). Exactly one must insert;
            # the other must catch the real UniqueViolation and resolve to
            # the winner's row, never a raw 500.
            results = await asyncio.gather(
                oa_attempts_pg.create_attempt(attempt_a, user_id, company_id, "TCS", None, "oa", [{"section_key": "aptitude"}]),
                oa_attempts_pg.create_attempt(attempt_b, user_id, company_id, "TCS", None, "oa", [{"section_key": "aptitude"}]),
            )
            created_flags = [r["created"] for r in results]
            assert created_flags.count(True) == 1, f"expected exactly one created=True, got {results}"
            assert created_flags.count(False) == 1, f"expected exactly one created=False, got {results}"
            winning_attempt_id = next(r["attempt"]["attempt_id"] for r in results if r["created"])
            losing_result = next(r for r in results if not r["created"])
            assert losing_result["attempt"]["attempt_id"] == winning_attempt_id, (
                "the losing call must resolve to the SAME winning row, not raise or create a second row"
            )
            rows_for_pair = await fetch_all(
                "SELECT attempt_id FROM oa_attempts WHERE user_id=%s AND company_id=%s", (user_id, company_id)
            )
            assert len(rows_for_pair) == 1, f"UniqueViolation path failed to prevent a double-insert: {rows_for_pair}"

            attempt_id = winning_attempt_id
            fetched = await oa_attempts_pg.get_attempt(attempt_id, user_id)
            assert fetched is not None
            lst = await oa_attempts_pg.list_attempts_for_user(user_id)
            assert len(lst) == 1
            updated = await oa_attempts_pg.update_attempt_progress(attempt_id, current_section_index=1, status="in_progress")
            assert updated["current_section_index"] == 1

            # Hidden answer keys: never exposed via a plain attempt fetch,
            # and the jsonb_set nested-path write must actually persist
            # (see oa_attempts_pg.set_hidden_answer_key's docstring --
            # single-statement jsonb_set silently no-ops on a missing
            # intermediate path element; fixed to nest two single-level
            # jsonb_sets).
            await oa_attempts_pg.set_hidden_answer_key(attempt_id, "aptitude", "q1", {"correct_index": 2})
            key = await oa_attempts_pg.get_hidden_answer_key(attempt_id, "aptitude", "q1")
            assert key == {"correct_index": 2}
            # a second key under the SAME section must not clobber the first
            await oa_attempts_pg.set_hidden_answer_key(attempt_id, "aptitude", "q2", {"correct_index": 0})
            key1_again = await oa_attempts_pg.get_hidden_answer_key(attempt_id, "aptitude", "q1")
            key2 = await oa_attempts_pg.get_hidden_answer_key(attempt_id, "aptitude", "q2")
            assert key1_again == {"correct_index": 2}
            assert key2 == {"correct_index": 0}
            assert "_hidden_answer_keys" not in fetched and "answer_keys" not in fetched

    run(body)


def test_game_sessions_pg_live_flow():
    async def body():
        async with scratch_user() as user_id:
            session_id = f"scratch-session-{uuid.uuid4()}"
            await game_sessions_pg.upsert_session(
                session_id, user_id, {"grid": [[1, 2], [3, 4]], "live_checks": {}},
                company="TCS", game_type="deductive_grid", section_key="games",
            )
            got = await game_sessions_pg.get_session(session_id)
            assert got["data"]["grid"] == [[1, 2], [3, 4]]

            upd = await game_sessions_pg.update_session_fields(
                session_id, data={"grid": [[1, 2], [3, 4]], "live_checks": {"p1": True}},
                raw_score=10, correct=1, incorrect=0, total=1,
            )
            assert upd["raw_score"] == 10 and upd["data"]["live_checks"] == {"p1": True}

            lst = await game_sessions_pg.list_sessions_for_user(user_id)
            assert len(lst) == 1

    run(body)


def test_ai_assisted_sessions_pg_live_flow():
    async def body():
        async with scratch_user() as user_id:
            session_id = f"scratch-ai-session-{uuid.uuid4()}"
            attempt_id = f"scratch-attempt-{uuid.uuid4()}"  # ai_assisted_sessions.attempt_id has no FK, a bare string is fine
            doc = {
                "session_id": session_id, "user_id": user_id, "attempt_id": attempt_id,
                "company_name": "TCS", "section_key": "debugging", "problem_id": "p1",
                "status": "in_progress", "current_stage": "consent", "consent_given": True,
                "problem": {"title": "Fix the bug"}, "transcript": [], "stage_attempts": {},
            }
            row = await ai_assisted_sessions_pg.insert_session(doc)
            assert row["data"]["problem"] == {"title": "Fix the bug"}

            got = await ai_assisted_sessions_pg.get_session(session_id, user_id)
            assert got is not None

            got_by_attempt = await ai_assisted_sessions_pg.get_session_by_attempt_section(attempt_id, "debugging", user_id)
            assert got_by_attempt is not None and got_by_attempt["session_id"] == session_id

            upd = await ai_assisted_sessions_pg.update_session(
                session_id, {"current_stage": "solving", "transcript": [{"role": "user", "text": "hi"}]}
            )
            assert upd["current_stage"] == "solving"
            assert upd["data"]["transcript"] == [{"role": "user", "text": "hi"}]
            assert upd["data"]["problem"] == {"title": "Fix the bug"}, "jsonb merge must not clobber unrelated fields"

            lst = await ai_assisted_sessions_pg.list_sessions_for_user(user_id)
            assert len(lst) == 1

    run(body)


def test_interviews_pg_live_roundtrip_with_capgemini_shaped_data():
    async def body():
        async with scratch_user() as user_id:
            interview_id = f"scratch-interview-{uuid.uuid4()}"
            doc = {
                "interview_id": interview_id, "user_id": user_id,
                "company_id": "tcs-nqt", "company_name": "TCS",
                "status": "in_progress", "current_index": 0,
                "questions": [{"id": "q1"}], "answers": [],
                "tier": "spark", "tier_source": "plan", "candidate_name": "Scratch User",
                "mode": "tcs", "state": {"phase": "intro"}, "turn_count": 0,
                "current_question": {"id": "intro-1"},
                "turns": [{"q": "Tell me about yourself", "a": None}],
                "usage": {"tokens": 120}, "dsa_problem_id": "two-sum",
                "dsa_flags": {"hinted": False},
            }
            row = await interviews_pg.insert_interview(doc)
            assert row["company_id"] == "tcs-nqt"
            assert row["data"]["tier"] == "spark"
            assert row["data"]["turn_count"] == 0
            assert row["data"]["turns"] == [{"q": "Tell me about yourself", "a": None}]
            assert "interview_id" not in row["data"]

            got = await interviews_pg.get_interview(interview_id, user_id)
            assert got["data"] == row["data"]

            got_in_progress = await interviews_pg.get_existing_in_progress(user_id, "tcs-nqt")
            assert got_in_progress is not None and got_in_progress["interview_id"] == interview_id

            lst = await interviews_pg.list_interviews_for_user(user_id)
            assert len(lst) == 1

            plain_upd = await interviews_pg.update_interview(interview_id, {"current_index": 1})
            assert plain_upd["current_index"] == 1 and plain_upd["data"]["tier"] == "spark"

            turn_upd = await interviews_pg.update_interview_if_turn_matches(
                interview_id, 0, {"turn_count": 1, "state": {"phase": "q1"}}
            )
            assert turn_upd is not None and turn_upd["data"]["turn_count"] == 1

            stale_upd = await interviews_pg.update_interview_if_turn_matches(interview_id, 0, {"turn_count": 2})
            assert stale_upd is None, "stale optimistic-concurrency guard must return None"

    run(body)


def test_reports_pg_finish_interview_atomicity_live():
    async def body():
        async with scratch_user() as user_id:
            attempt_id = f"scratch-attempt-{uuid.uuid4()}"
            await fetch_one(
                "INSERT INTO oa_attempts (attempt_id, user_id, company_id, company_name, status) "
                "VALUES (%s, %s, %s, %s, 'in_progress') RETURNING attempt_id",
                (attempt_id, user_id, "tcs-nqt", "TCS"),
            )
            interview_id = f"scratch-interview-{uuid.uuid4()}"
            await interviews_pg.insert_interview({
                "interview_id": interview_id, "user_id": user_id, "attempt_id": attempt_id,
                "company_id": "tcs-nqt", "company_name": "TCS", "status": "in_progress",
                "turn_count": 1,
            })

            report_id_a = f"scratch-report-a-{uuid.uuid4()}"
            await reports_pg.insert_report({
                "report_id": report_id_a, "user_id": user_id, "company_name": "TCS",
                "attempt_id": attempt_id, "created_at": "2026-01-01T00:00:00+00:00",
                "report": {"final": "ok"},
            })
            cached = await reports_pg.get_cached_report(user_id, attempt_id=attempt_id)
            assert cached is not None
            cached_by_interview = await reports_pg.get_cached_report(user_id, interview_id=interview_id)
            assert cached_by_interview is not None and cached_by_interview["report_id"] == report_id_a

            # --- happy path: expected_turn_count matches -> commits + invalidates cache ---
            fin = await reports_pg.finish_interview(
                interview_id, 1, {"status": "completed", "turn_count": 2}, user_id, attempt_id=attempt_id,
            )
            assert fin["stale_turn"] is False
            assert fin["interview"]["status"] == "completed"
            assert fin["interview"]["data"]["turn_count"] == 2
            post_cache = await reports_pg.get_cached_report(user_id, attempt_id=attempt_id)
            assert post_cache is None, "finish_interview must invalidate the cached report on success"

            # --- stale-turn path: wrong expected_turn_count must be a clean no-op ---
            report_id_b = f"scratch-report-b-{uuid.uuid4()}"
            await reports_pg.insert_report({
                "report_id": report_id_b, "user_id": user_id, "company_name": "TCS",
                "attempt_id": attempt_id, "created_at": "2026-01-02T00:00:00+00:00",
                "report": {"final": "second"},
            })
            fin_stale = await reports_pg.finish_interview(interview_id, 999, {"status": "should_not_apply"}, user_id, attempt_id=attempt_id)
            assert fin_stale["stale_turn"] is True and fin_stale["interview"] is None
            intv_unchanged = await interviews_pg.get_interview(interview_id, user_id)
            assert intv_unchanged["status"] == "completed", "a stale call must not apply its changes"
            still_cached = await reports_pg.get_cached_report(user_id, attempt_id=attempt_id)
            assert still_cached is not None, "a stale call must NOT invalidate the cache"

            # --- REAL rollback proof: same transaction() primitive finish_interview
            #     is built on; first statement succeeds, second is forced to fail,
            #     confirm NEITHER statement's effect persisted. ---
            before = await fetch_one("SELECT status FROM interviews WHERE interview_id=%s", (interview_id,))
            raised = None
            try:
                async with transaction() as cur:
                    await cur.execute(
                        "UPDATE interviews SET status = %s WHERE interview_id = %s",
                        ("ROLLBACK_SHOULD_NOT_PERSIST", interview_id),
                    )
                    # Forced failure: reports.report_id is NOT NULL / primary key.
                    await cur.execute(
                        "INSERT INTO reports (report_id, user_id, company_name) VALUES (NULL, %s, %s)",
                        (user_id, "TCS"),
                    )
            except Exception as e:  # noqa: BLE001 -- intentionally broad, asserting it raised at all
                raised = e
            assert raised is not None, "the deliberately-invalid statement should have raised"
            after = await fetch_one("SELECT status FROM interviews WHERE interview_id=%s", (interview_id,))
            assert after["status"] == before["status"], "transaction() failed to roll back the first statement"
            assert after["status"] != "ROLLBACK_SHOULD_NOT_PERSIST"
            leftover = await fetch_one("SELECT report_id FROM reports WHERE user_id=%s AND report_id IS NULL", (user_id,))
            assert leftover is None

            # --- replace_cached_report: literal delete-then-insert in one transaction ---
            report_id_c = f"scratch-report-c-{uuid.uuid4()}"
            await reports_pg.replace_cached_report(
                {"attempt_id": attempt_id, "user_id": user_id},
                {"report_id": report_id_c, "user_id": user_id, "company_name": "TCS", "attempt_id": attempt_id,
                 "created_at": "2026-01-03T00:00:00+00:00", "report": {"final": "replaced"}},
            )
            remaining = await fetch_all("SELECT report_id FROM reports WHERE attempt_id=%s", (attempt_id,))
            assert [r["report_id"] for r in remaining] == [report_id_c]

            # Explicit cleanup of the rows this test inserted outside the
            # scratch_user() cascade path that aren't otherwise torn down
            # by the context manager alone (they ARE FK'd to profiles, so
            # scratch_user()'s cascade delete on auth.users handles all of
            # them too -- this is just defensive/explicit).
            await fetch_all("DELETE FROM reports WHERE user_id=%s RETURNING 1", (user_id,))
            await fetch_all("DELETE FROM interviews WHERE user_id=%s RETURNING 1", (user_id,))
            await fetch_all("DELETE FROM oa_attempts WHERE user_id=%s RETURNING 1", (user_id,))

    run(body)


def test_question_seen_pg_live_flow():
    async def body():
        async with scratch_user() as user_id:
            seen0 = await question_seen_pg.get_seen_ids(user_id, "mcq_static", "aptitude")
            assert seen0 == set()

            await question_seen_pg.mark_seen(user_id, "mcq_static", "aptitude", ["q1", "q2"])
            seen1 = await question_seen_pg.get_seen_ids(user_id, "mcq_static", "aptitude")
            assert seen1 == {"q1", "q2"}

            await question_seen_pg.mark_seen(user_id, "mcq_static", "aptitude", ["q2", "q3"])
            seen2 = await question_seen_pg.get_seen_ids(user_id, "mcq_static", "aptitude")
            assert seen2 == {"q1", "q2", "q3"}, "addToSet-style dedup failed"

            seen_other_scope = await question_seen_pg.get_seen_ids(user_id, "mcq_static", "reasoning")
            assert seen_other_scope == set(), "scope isolation failed"

            await question_seen_pg.mark_seen(user_id, "ai_assisted", "", ["probA"])
            seen_ai = await question_seen_pg.get_seen_ids(user_id, "ai_assisted", "")
            assert seen_ai == {"probA"}, "bank isolation failed"

    run(body)


def test_review_deck_pg_live_flow():
    async def body():
        async with scratch_user() as user_id:
            attempt_id = f"scratch-attempt-{uuid.uuid4()}"
            await fetch_one(
                "INSERT INTO oa_attempts (attempt_id, user_id, status) VALUES (%s, %s, 'completed') RETURNING attempt_id",
                (attempt_id, user_id),
            )
            card_id = f"card-{uuid.uuid4()}"
            card = await review_deck_pg.add_card(
                user_id, attempt_id, "aptitude", "q1", card_id, "TCS", "Aptitude",
                "2+2=?", ["3", "4", "5"], 1, "basic math", "easy",
            )
            assert card["card_id"] == card_id and card["mastered"] is False

            dup = await review_deck_pg.add_card(
                user_id, attempt_id, "aptitude", "q1", card_id, "TCS", "Aptitude",
                "2+2=?", ["3", "4", "5"], 1, "basic math", "easy",
            )
            assert dup is None, "duplicate unique-constraint guard should produce a no-op"

            listed = await review_deck_pg.list_cards(user_id)
            assert len(listed) == 1

            got = await review_deck_pg.get_card(card_id, user_id)
            assert got is not None

            attempted = await review_deck_pg.record_attempt(card_id, user_id, [{"correct": True}], True)
            assert attempted["mastered"] is True

            listed_unmastered = await review_deck_pg.list_cards(user_id, unmastered_only=True)
            assert listed_unmastered == []

            deleted = await review_deck_pg.delete_card(card_id, user_id)
            assert deleted is True
            deleted_again = await review_deck_pg.delete_card(card_id, user_id)
            assert deleted_again is False

            await fetch_all("DELETE FROM oa_attempts WHERE user_id=%s RETURNING 1", (user_id,))

    run(body)


def test_orders_pg_live_flow_and_idempotent_mark_paid():
    async def body():
        async with scratch_user() as user_id:
            order_id = f"order-{uuid.uuid4()}"
            await orders_pg.create_order(
                order_id, user_id, "credits",
                {"razorpay_order_id": "order_mock_abc", "amount": 199, "currency": "INR", "credit_pack_id": "credit-5"},
            )
            got = await orders_pg.get_order(order_id, user_id)
            assert got is not None and got["status"] == "created"

            paid = await orders_pg.mark_paid(order_id, "pay_mock_xyz")
            assert paid is not None and paid["status"] == "paid"

            paid_again = await orders_pg.mark_paid(order_id, "pay_mock_xyz_retry")
            assert paid_again is None, "idempotent-crediting guard failed -- a retry must be a no-op"

    run(body)
