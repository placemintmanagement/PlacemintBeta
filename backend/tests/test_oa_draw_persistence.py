"""Regression test (2026-10, follow-up to the Capgemini/non-TCS draw-
randomization fix): a genuinely random draw is only safe if it happens
EXACTLY ONCE per attempt, at generation time, and reload/resume/refresh
never re-trigger it -- otherwise a candidate could see a DIFFERENT set of
questions on a page refresh than the one they started answering.

Audit (read-only, no code change needed -- see this task's own report for
the full per-caller breakdown):
  - Every mcq_static_bank draw call in server.py (_generate_extra_topics,
    _generate_topic_mix, _generate_section_questions's pooled-key/topic_mcq/
    pseudocode branches, and the extra_topics-per-piece loop in
    _gen_and_persist_section) runs ONLY inside the background generation
    task kicked off once by POST /oa/start (_generate_all_sections_bg ->
    _gen_and_persist_section), and persists its result to
    oa_attempts.sections.{index}.questions via $set (first write) or $push
    (later chunks/pieces) before that task moves on.
  - mark_seen() is called INSIDE each draw function itself, i.e. at that
    same generation-time moment -- never deferred to submit time.
  - GET /oa/{attempt_id} (reload/resume/refresh) is a pure read of the
    stored attempt doc -- no draw function is ever called there.
  - POST /oa/{attempt_id}/section (submit) reads `section` from the
    STORED attempt's own `sections` list and grades it -- no draw
    function is ever called there either.
  - POST /oa/start itself has a double-start guard (409
    oa_already_in_progress for a still-in_progress attempt), so a second
    background-generation task can never be spawned for the same attempt
    while reload/resume are the only other reachable operations.
  - Within _gen_and_persist_section's extra_topics-per-piece loop, each
    piece draws a DIFFERENT topic (oops/dbms/os/cn/architecture/...),
    which are disjoint question_id namespaces in mcq_static_bank -- no
    topic's draw can structurally repeat or skip another topic's.

This test proves the end-to-end contract for the most common real shape
(a plain mcq section drawn via the pooled-topic static/live split, same
as nearly every company's basic aptitude/verbal/reasoning section) PLUS
the static-only extra_topics shape (Capgemini Round 2 Technical): generate
once, then "reload" (GET /oa/{attempt_id}) and "resume" (a second GET,
simulating a later page revisit) repeatedly -- the served question ids
must be byte-identical every time, and the underlying stored doc must
never change.
"""
import asyncio

from mongomock_motor import AsyncMongoMockClient

import server
from banks import mcq_static_bank, mcq_pool, problem_bank


def _mcq_doc(topic, qid):
    return {
        "topic": topic, "question_id": qid, "prompt": f"{topic} question {qid}",
        "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "because",
        "difficulty": "Medium",
    }


def _seed_topic(db, topic, n):
    docs = [_mcq_doc(topic, f"{topic}-{i:04d}") for i in range(n)]
    asyncio.run(db.mcq_static_bank.insert_many(docs))


def _fresh_db():
    client = AsyncMongoMockClient()
    db = client["test"]
    mcq_static_bank.init(db)
    mcq_pool.init(db)
    problem_bank.init(db)
    server.db = db
    return db


def _raising_call_json(*a, **k):
    raise AssertionError("call_json was invoked -- this draw must be AI-free / not re-triggered")


async def _reload_question_ids(attempt_id, user, section_key):
    doc = await server.get_oa(attempt_id, user)
    section = next(s for s in doc["sections"] if s["key"] == section_key)
    return [q["id"] for q in section["questions"]]


def test_a_pooled_mcq_section_is_drawn_once_then_only_reread_on_reload(monkeypatch):
    """Caller shape: server.py:1603 (plain pooled-key mcq section, inside
    _generate_section_questions) -- the most common shape, used by nearly
    every company's basic aptitude/verbal/reasoning section."""
    db = _fresh_db()
    monkeypatch.setattr(server, "call_json", _raising_call_json)
    monkeypatch.setattr(server, "call_json_gpt", _raising_call_json)
    # Generous static bank (bigger than count) so the 90/10 split's live
    # 10% backfill still has SOME live_n > 0 -- stub the live pool
    # deterministically instead of mocking it away entirely, so this
    # covers the REAL mixed static+live shape, not an artificially
    # static-only one.
    _seed_topic(db, "aptitude", 200)
    monkeypatch.setattr(server.mcq_pool, "pop_from_pool", lambda *a, **k: asyncio.sleep(0, result=[
        {"id": "live-1", "prompt": "live q1", "options": ["A", "B"], "correct_index": 0},
        {"id": "live-2", "prompt": "live q2", "options": ["A", "B"], "correct_index": 0},
    ]))

    attempt_id = "att-pooled"
    user = {"user_id": "u-pooled"}
    company = {
        "id": "synthetic-pooled", "name": "Synthetic Pooled Co",
        "sections": [{"key": "aptitude", "name": "Aptitude", "type": "mcq", "count": 20, "minutes": 20, "cutoff": 0.5}],
    }
    attempt = {
        "attempt_id": attempt_id, "user_id": user["user_id"], "company_id": company["id"],
        "company_name": company["name"], "status": "in_progress", "generation_status": "generating",
        "sections": [{**company["sections"][0], "questions": []}],
        "answers": {}, "section_results": {}, "current_section_index": 0,
    }
    asyncio.run(db.oa_attempts.insert_one(attempt))

    asyncio.run(server._gen_and_persist_section(attempt_id, company["name"], 0, company["sections"][0], user["user_id"], company_id=company["id"]))

    stored = asyncio.run(db.oa_attempts.find_one({"attempt_id": attempt_id}))
    generated_ids = [q["id"] for q in stored["sections"][0]["questions"]]
    assert len(generated_ids) == 20
    assert len(set(generated_ids)) == 20  # no duplicates from the draw itself

    # "Reload" and "resume" -- just GET /oa/{attempt_id}, repeatedly. Must
    # never change, since no draw function is ever called from there.
    for _ in range(3):
        reloaded_ids = asyncio.run(_reload_question_ids(attempt_id, user, "aptitude"))
        assert reloaded_ids == generated_ids

    # The underlying stored doc itself is also unchanged, not just the response shape.
    restored = asyncio.run(db.oa_attempts.find_one({"attempt_id": attempt_id}))
    assert [q["id"] for q in restored["sections"][0]["questions"]] == generated_ids


def test_capgemini_round2_technical_extra_topics_section_persists_once(monkeypatch):
    """Caller shape: server.py:979 (_generate_extra_topics, static_only=True
    -- Capgemini Round 2 Technical), reached via _generate_section_questions's
    "capgemini_round2_technical" branch. Zero live-pool dependency by
    design, so this also proves the static-only shape never touches
    call_json/mcq_pool at all, same precedent as
    test_static_reuse.py's static-only test."""
    db = _fresh_db()
    monkeypatch.setattr(server, "call_json", _raising_call_json)
    monkeypatch.setattr(server, "call_json_gpt", _raising_call_json)
    monkeypatch.setattr(server.mcq_pool, "pop_from_pool", _raising_call_json)
    monkeypatch.setattr(server.mcq_pool, "fallback_live_verify_topic", _raising_call_json)
    for topic in ("programming_logic", "dsa", "oops", "dbms", "swe_fundamentals", "cn", "modern_engineering"):
        _seed_topic(db, topic, 30)

    attempt_id = "att-r2tech"
    user = {"user_id": "u-r2tech"}
    company = {
        "id": "synthetic-capgemini", "name": "Synthetic Capgemini",
        "sections": [{"key": "technical", "name": "Technical Assessment", "type": "capgemini_round2_technical", "count": 20, "minutes": 20, "cutoff": 0.5}],
    }
    attempt = {
        "attempt_id": attempt_id, "user_id": user["user_id"], "company_id": company["id"],
        "company_name": company["name"], "status": "in_progress", "generation_status": "generating",
        "sections": [{**company["sections"][0], "questions": []}],
        "answers": {}, "section_results": {}, "current_section_index": 0,
    }
    asyncio.run(db.oa_attempts.insert_one(attempt))

    asyncio.run(server._gen_and_persist_section(attempt_id, company["name"], 0, company["sections"][0], user["user_id"], company_id=company["id"]))

    stored = asyncio.run(db.oa_attempts.find_one({"attempt_id": attempt_id}))
    generated_ids = [q["id"] for q in stored["sections"][0]["questions"]]
    assert len(generated_ids) == 20
    assert len(set(generated_ids)) == 20

    for _ in range(3):
        reloaded_ids = asyncio.run(_reload_question_ids(attempt_id, user, "technical"))
        assert reloaded_ids == generated_ids
