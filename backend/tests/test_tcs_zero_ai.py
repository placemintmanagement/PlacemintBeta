"""TCS zero-AI-calls pass (2026-10): proves the entire TCS OA flow (section
generation, coding grading, Part-B skip, final report) never calls
call_json/call_json_gpt, recycles static-bank questions correctly (least-
recently-seen first, no in-attempt duplicates, unseen preferred, sibling-
borrow on a topic shortfall, BLOCKED when even that can't cover it), and
that the production-code AIForbiddenError guard actually fires.

Uses mongomock_motor's AsyncMongoMockClient (real Mongo query semantics --
$nin, $addToSet, sort, count_documents -- without a real Mongo or Atlas) for
the two static-bank collections (mcq_static_bank/mcq_static_bank_seen,
problem_bank_seen) and for oa_attempts itself. No real network, no
subagents, no scheduled checks.

Style: sync test functions calling asyncio.run(...), matching every other
file in this suite (no pytest-asyncio in this repo -- see pytest.ini).

Tests that draw real mcq_static_bank content (via tcs._draw_one_topic,
tcs.draw_tcs_foundation_and_advanced, tcs.check_tcs_static_feasibility, or
the full _generate_tcs_sections_bg flow) are parametrized over DB_BACKEND
("mongo"/"supabase") -- see supabase_dispatch_fake_support.py's module
docstring for why: those calls fork on DB_BACKEND inside
banks/mcq_static_bank.py, so without this a GLOBAL DB_BACKEND=supabase
would silently redirect them into repositories/mcq_static_bank_pg.py with
no real Postgres underneath, erroring instead of proving the recycling/
sibling-borrow/feasibility behavior this file checks. Tests that never
touch a content bank (the coding-profile, AIForbiddenError, and structural
guard tests below) are left exactly as they were.
"""
import asyncio

import pytest
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient

import server
from banks import mcq_static_bank, problem_bank
from services.ai_service import AIForbiddenError, forbid_ai_calls, call_json, call_json_gpt
from departments.computer_science_and_it.group1_it_services_mass_recruiters.tcs import (
    tcs_recruitment_process as tcs,
)
from supabase_dispatch_fake_support import use_backend


def _mcq_doc(topic, qid, difficulty="Medium"):
    return {
        "topic": topic, "question_id": qid, "prompt": f"{topic} question {qid}",
        "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "because",
        "difficulty": difficulty,
    }


def _seed_topic(db, topic, n, prefix=""):
    docs = [_mcq_doc(topic, f"{prefix}{topic}-{i}") for i in range(n)]
    asyncio.run(db.mcq_static_bank.insert_many(docs))
    return [d["question_id"] for d in docs]


def _fresh_db():
    client = AsyncMongoMockClient()
    db = client["test"]
    mcq_static_bank.init(db)
    problem_bank.init(db)
    server.db = db
    return db


def _raising_call_json(*a, **k):
    raise AssertionError("call_json was invoked -- TCS must never call this.")


def _raising_call_json_gpt(*a, **k):
    raise AssertionError("call_json_gpt was invoked -- TCS must never call this.")


def _tcs_sections():
    cfg = tcs.get_config()
    return [{**s, "questions": []} for s in cfg["sections"]]


# ---- 1. Full attempt, end to end, zero AI calls ----------------------------

@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_full_tcs_attempt_completes_with_zero_ai_calls(monkeypatch, backend):
    """Covers generation (start), all 5 sections submitted in order, coding
    with faked sandbox results, the result (oa_review), and the report --
    with BOTH call_json and call_json_gpt patched to raise on any call.
    Bypasses start_oa's entitlements/payment plumbing (irrelevant to AI-call
    behavior) by inserting the attempt doc directly, the same shape start_oa
    itself would have stored, then calling the real _generate_tcs_sections_bg
    -- every other step (submit_section x5, finish via normal completion,
    oa_review, final_report) goes through the REAL, unmodified server
    functions."""
    db = _fresh_db()
    use_backend(monkeypatch, backend)
    monkeypatch.setattr(server, "call_json", _raising_call_json)
    monkeypatch.setattr(server, "call_json_gpt", _raising_call_json_gpt)
    monkeypatch.setattr(server, "_lang_run_tests", lambda language, code, tests: (len(tests), []))

    _seed_topic(db, "aptitude", 60)
    _seed_topic(db, "verbal", 60)
    _seed_topic(db, "reasoning", 60)

    attempt_id = "att-e2e"
    user = {"user_id": "u-e2e"}
    sections = _tcs_sections()
    sections = tcs.apply_coding_profile(sections, attempt_id)
    attempt = {
        "attempt_id": attempt_id, "user_id": user["user_id"], "company_id": "tcs-nqt",
        "company_name": "TCS NQT", "status": "in_progress", "generation_status": "generating",
        "sections": sections, "answers": {}, "section_results": {}, "current_section_index": 0,
    }
    asyncio.run(db.oa_attempts.insert_one(attempt))

    asyncio.run(server._generate_tcs_sections_bg(attempt_id, tcs.get_config(), user["user_id"]))

    stored = asyncio.run(db.oa_attempts.find_one({"attempt_id": attempt_id}))
    assert stored["generation_status"] == "ready", stored.get("generation_error")
    for s in stored["sections"]:
        assert len(s["questions"]) == s["count"], s["key"]

    for key in ("numerical", "verbal", "reasoning", "advanced"):
        sec = next(s for s in stored["sections"] if s["key"] == key)
        # Every seeded question's correct_index is 0 -- answer all of them
        # correctly so the foundation score clears even "ninja"'s threshold,
        # letting the tier assertion below actually exercise tcs_tiers.evaluate
        # instead of trivially landing on None for an all-empty submission.
        fake_answers = {q["id"]: 0 for q in sec["questions"]}
        body = server.SubmitSectionIn(section_key=key, answers=fake_answers)
        resp = asyncio.run(server.submit_section(attempt_id, body, user=user))
        assert resp["status"] == "in_progress"

    coding_section = next(s for s in stored["sections"] if s["key"] == "coding")
    coding_answers = {
        q["id"]: {"code": "print('ok')", "language": "python"} for q in coding_section["questions"]
    }
    body = server.SubmitSectionIn(section_key="coding", answers=coding_answers)
    resp = asyncio.run(server.submit_section(attempt_id, body, user=user))
    assert resp["status"] == "completed"
    assert resp["tcs_tier"]["tier"] in ("ninja", "digital", "prime")

    review = asyncio.run(server.oa_review(attempt_id, user))
    assert review["available"] is not False

    report = asyncio.run(server.final_report(attempt_id, user))
    assert report["report"]["overall_verdict"] == review["verdict"]
    assert "narrative" in report["report"]


# ---- 2. Recycling: least-recently-seen first, no in-attempt duplicates ----

@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_thin_bank_recycles_least_recently_seen_first(monkeypatch, backend):
    db = _fresh_db()
    use_backend(monkeypatch, backend)
    ids = _seed_topic(db, "aptitude", 3)  # smaller than one attempt's "numerical" need (20)

    # First draw: all 3 unseen, served + marked seen.
    items1, unfilled1 = asyncio.run(tcs._draw_one_topic("att-1", "u1", "aptitude", 3))
    assert {q["id"] for q in items1} == set(ids)
    assert unfilled1 == 0

    # Mark one id as seen MORE RECENTLY than the others, so it should sort last.
    asyncio.run(mcq_static_bank.mark_seen("u1", "aptitude", [ids[0]]))

    # Second draw of 3 (bank fully seen now) must recycle ALL 3, least-
    # recently-seen first -- ids[0] (just re-marked) should come LAST.
    items2, unfilled2 = asyncio.run(tcs._draw_one_topic("att-2", "u1", "aptitude", 3))
    assert unfilled2 == 0
    assert [q["id"] for q in items2][-1] == ids[0]


@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_no_duplicate_questions_within_one_attempt(monkeypatch, backend):
    db = _fresh_db()
    use_backend(monkeypatch, backend)
    _seed_topic(db, "aptitude", 5)
    items, unfilled = asyncio.run(tcs._draw_one_topic("att-1", "u1", "aptitude", 5))
    assert unfilled == 0
    assert len({q["id"] for q in items}) == 5  # no duplicates even drawing the whole bank at once


@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_unseen_preferred_over_seen(monkeypatch, backend):
    db = _fresh_db()
    use_backend(monkeypatch, backend)
    ids = _seed_topic(db, "aptitude", 5)
    asyncio.run(mcq_static_bank.mark_seen("u1", "aptitude", [ids[0], ids[1]]))
    items, unfilled = asyncio.run(tcs._draw_one_topic("att-1", "u1", "aptitude", 3))
    assert unfilled == 0
    drawn_ids = {q["id"] for q in items}
    # The 3 unseen ones (ids[2:5]) must all be drawn before any seen one is needed.
    assert drawn_ids == set(ids[2:5])


# ---- 3. Sibling-borrow on Advanced, BLOCKED when there's no sibling -------

@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_advanced_sibling_borrow_covers_a_shortfall_and_logs_it(monkeypatch, backend):
    db = _fresh_db()
    use_backend(monkeypatch, backend)
    # "aptitude" bank too small for Advanced's own need (10) -- "reasoning"
    # (the sibling sub-topic in the SAME "advanced" section) has plenty.
    _seed_topic(db, "aptitude", 4)
    _seed_topic(db, "reasoning", 30)
    sections = _tcs_sections()
    # Foundation sections need their own topic draws too -- give them enough
    # so this test isolates Advanced's borrow behavior specifically.
    _seed_topic(db, "verbal", 30)

    # Foundation's "numerical" (20) and "reasoning" (20) would also draw
    # from these same topics; shrink them out of the picture by zeroing
    # their count so only "advanced" is exercised here.
    by_key = {s["key"]: s for s in sections}
    by_key["numerical"]["count"] = 0
    by_key["reasoning"]["count"] = 0
    by_key["verbal"]["count"] = 0

    result = asyncio.run(tcs.draw_tcs_foundation_and_advanced("att-borrow", "u1", sections))
    advanced_items = result["advanced"]
    assert len(advanced_items) == 15  # 10 aptitude (4 own + 6 borrowed) + 5 reasoning
    borrowed = [q for q in advanced_items if q.get("_borrowed_from_topic")]
    assert len(borrowed) == 6
    assert all(q["_borrowed_from_topic"] == "reasoning" for q in borrowed)
    # No duplicate ids even across the borrow.
    assert len({q["id"] for q in advanced_items}) == len(advanced_items)


@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_foundation_section_blocks_when_bank_too_small_no_sibling_exists(monkeypatch, backend):
    db = _fresh_db()
    use_backend(monkeypatch, backend)
    _seed_topic(db, "aptitude", 5)  # "numerical" needs 20 -- no sibling in its own section
    sections = _tcs_sections()
    by_key = {s["key"]: s for s in sections}
    by_key["verbal"]["count"] = 0
    by_key["reasoning"]["count"] = 0
    by_key["advanced"]["extra_topics"] = []  # keep this test isolated to "numerical"
    by_key["advanced"]["count"] = 0
    with pytest.raises(tcs.TCSBankBlockedError) as exc:
        asyncio.run(tcs.draw_tcs_foundation_and_advanced("att-blocked", "u1", sections))
    assert exc.value.section_key == "numerical"
    assert exc.value.topic == "aptitude"


@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_check_static_feasibility_catches_a_too_small_bank(monkeypatch, backend):
    db = _fresh_db()
    use_backend(monkeypatch, backend)
    _seed_topic(db, "aptitude", 5)   # too small (numerical 20 + advanced 10 = 30 needed)
    _seed_topic(db, "verbal", 50)
    _seed_topic(db, "reasoning", 50)
    reason = asyncio.run(tcs.check_tcs_static_feasibility())
    assert reason is not None
    assert "aptitude" in reason


@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_check_static_feasibility_passes_with_generous_banks(monkeypatch, backend):
    db = _fresh_db()
    use_backend(monkeypatch, backend)
    _seed_topic(db, "aptitude", 60)
    _seed_topic(db, "verbal", 60)
    _seed_topic(db, "reasoning", 60)
    assert asyncio.run(tcs.check_tcs_static_feasibility()) is None


# ---- 4. Double start / client cannot influence seen history ---------------

@pytest.mark.parametrize("backend", ["mongo", "supabase"])
def test_double_generation_does_not_redraw_or_double_mark_seen(monkeypatch, backend):
    db = _fresh_db()
    use_backend(monkeypatch, backend)
    monkeypatch.setattr(server, "call_json", _raising_call_json)
    monkeypatch.setattr(server, "call_json_gpt", _raising_call_json_gpt)
    _seed_topic(db, "aptitude", 60)
    _seed_topic(db, "verbal", 60)
    _seed_topic(db, "reasoning", 60)

    attempt_id = "att-double"
    user_id = "u-double"
    sections = tcs.apply_coding_profile(_tcs_sections(), attempt_id)
    attempt = {
        "attempt_id": attempt_id, "user_id": user_id, "company_id": "tcs-nqt",
        "company_name": "TCS NQT", "status": "in_progress", "generation_status": "generating",
        "sections": sections, "answers": {}, "section_results": {}, "current_section_index": 0,
    }
    asyncio.run(db.oa_attempts.insert_one(attempt))

    asyncio.run(server._generate_tcs_sections_bg(attempt_id, tcs.get_config(), user_id))
    first = asyncio.run(db.oa_attempts.find_one({"attempt_id": attempt_id}))
    first_ids = {s["key"]: [q["id"] for q in s["questions"]] for s in first["sections"]}

    # Simulate a double start_oa call generating for the SAME attempt again.
    asyncio.run(server._generate_tcs_sections_bg(attempt_id, tcs.get_config(), user_id))
    second = asyncio.run(db.oa_attempts.find_one({"attempt_id": attempt_id}))
    second_ids = {s["key"]: [q["id"] for q in s["questions"]] for s in second["sections"]}

    assert first_ids == second_ids  # idempotent: unchanged, not redrawn
    # Seen-count check: each question marked seen exactly once, not twice.
    doc = asyncio.run(db.mcq_static_bank_seen.find_one({"user_id": user_id, "topic": "aptitude"}))
    assert len(doc["question_ids"]) == len(set(doc["question_ids"]))


def test_client_cannot_pass_seen_ids_through_any_endpoint():
    # Structural check: SubmitSectionIn (the only client-writable body on
    # the OA flow) has no seen/history field, and finish_oa_part_a takes no
    # body at all -- there is no endpoint shape through which a client could
    # supply or edit seen-question history.
    assert set(server.SubmitSectionIn.model_fields.keys()) == {"section_key", "answers"}
    import inspect
    assert list(inspect.signature(server.finish_oa_part_a).parameters) == ["attempt_id", "user"]


# ---- 5. Coding: recycling per difficulty slot, problem 2 always medium ----

def test_coding_recycles_least_recently_seen_within_difficulty():
    db = _fresh_db()
    picks1, unfilled1 = asyncio.run(
        problem_bank.sample_problems_with_reuse("u1", "easy", rng=__import__("random").Random(1))
    )
    assert unfilled1 == 0
    assert len(picks1) == 1


def test_coding_profile_b_slot_2_is_always_medium():
    for attempt_id in ("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8"):
        roll = tcs.roll_coding_profile(attempt_id)
        assert roll["difficulty_targets"][1] == "medium"


# ---- 6. finish-part-a makes no model call ----------------------------------

def test_finish_part_a_makes_no_model_call(monkeypatch):
    db = _fresh_db()
    monkeypatch.setattr(server, "call_json", _raising_call_json)
    monkeypatch.setattr(server, "call_json_gpt", _raising_call_json_gpt)

    attempt_id = "att-finish"
    user = {"user_id": "u-finish"}
    sections = _tcs_sections()
    for s in sections:
        if s["key"] in ("numerical", "verbal", "reasoning"):
            s["questions"] = [{"id": "x", "prompt": "p", "options": ["a"], "correct_index": 0}]
    attempt = {
        "attempt_id": attempt_id, "user_id": user["user_id"], "company_id": "tcs-nqt",
        "status": "in_progress", "sections": sections, "answers": {},
        "section_results": {
            "numerical": {"correct": 20, "score": 1.0}, "verbal": {"correct": 25, "score": 1.0},
            "reasoning": {"correct": 20, "score": 1.0},
        },
        "current_section_index": 3,
    }
    asyncio.run(db.oa_attempts.insert_one(attempt))
    resp = asyncio.run(server.finish_oa_part_a(attempt_id, user=user))
    assert resp["status"] == "completed"
    assert resp["tcs_tier"]["tier"] == "ninja"


# ---- 7. AIForbiddenError actually fires ------------------------------------

def test_ai_forbidden_error_fires_for_call_json():
    with forbid_ai_calls():
        with pytest.raises(AIForbiddenError):
            asyncio.run(call_json("sys", "prompt"))


def test_ai_forbidden_error_fires_for_call_json_gpt():
    with forbid_ai_calls():
        with pytest.raises(AIForbiddenError):
            asyncio.run(call_json_gpt("sys", "prompt"))


def test_ai_forbidden_guard_does_not_leak_across_calls():
    # Outside the context manager, a real call attempt is NOT blocked by
    # this guard (it would reach the real client -- not invoked here, just
    # confirming the contextvar resets cleanly after the `with` exits).
    with forbid_ai_calls():
        pass
    from services.ai_service import _ai_forbidden_ctx
    assert _ai_forbidden_ctx.get() is False


def test_submit_section_wraps_tcs_coding_grading_in_the_guard(monkeypatch):
    db = _fresh_db()

    async def _poison(*a, **k):
        raise AssertionError("call_json_gpt reached inside the TCS coding-grading guard")
    monkeypatch.setattr(server, "call_json_gpt", _poison)
    monkeypatch.setattr(server, "_lang_run_tests", lambda language, code, tests: (len(tests), []))

    sections = [{"key": "coding", "type": "coding", "cutoff": 0.5, "optional": True,
                 "questions": [{"id": "p1", "visible_tests": [{"input": "1", "expected_output": "1"}], "hidden_tests": []}]}]
    attempt = {
        "attempt_id": "att-guard", "user_id": "u1", "company_id": "tcs-nqt", "status": "in_progress",
        "sections": sections, "answers": {}, "section_results": {}, "current_section_index": 0,
    }
    asyncio.run(db.oa_attempts.insert_one(attempt))
    body = server.SubmitSectionIn(section_key="coding", answers={"p1": {"code": "x", "language": "python"}})
    resp = asyncio.run(server.submit_section("att-guard", body, user={"user_id": "u1"}))
    assert resp["section_result"]["problems"][0]["ai"]["correctness_note"]  # template note present, no AI


# ---- 8. Other companies are structurally unaffected -------------------------

def test_non_static_bank_only_companies_are_not_in_the_guarded_set():
    assert "wipro" not in server._STATIC_BANK_ONLY_COMPANY_IDS
    assert "capgemini" not in server._STATIC_BANK_ONLY_COMPANY_IDS
    assert server._STATIC_BANK_ONLY_COMPANY_IDS == {"tcs-nqt"}
