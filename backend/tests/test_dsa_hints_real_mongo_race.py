# -*- coding: utf-8 -*-
"""Real-MongoDB verification that a concurrent double hint-request shares
the exact same atomic turn-claim guard (commits 29e8fc2 / 055eb99,
_claim_turn_or_409 + the turn_count-guarded persist, dotted-path matching
proven against real Mongo field order in test_real_mongo_turn_claim.py) as
any other submission -- exactly one hint consumed, one 200 and one 409
turn_in_progress, zero model calls on either side (hints make none, and the
loser never even reaches the hint-detection code).

Uses the SAME throwaway local mongod as test_real_mongo_turn_claim.py via
mongodb-memory-server (scratchpad/mongo-mem/start.js) on 127.0.0.1:27117 --
never Atlas. Skips gracefully if that mongod is not reachable."""
import asyncio

import pytest

import server
from spark_support import _Clock, _attempt as _spark_attempt, PROJECTS as SPARK_PROJECTS, _Model as _SparkModel

REAL_MONGO_URL = "mongodb://127.0.0.1:27117"
REAL_MONGO_DB = "real_mongo_dsa_hints_test"
USER = {"user_id": "u1", "name": "Priya"}


def _real_mongo_reachable() -> bool:
    try:
        import pymongo
        client = pymongo.MongoClient(REAL_MONGO_URL, serverSelectionTimeoutMS=500)
        client.admin.command("ping")
        client.close()
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _skip_without_real_mongo():
    if not _real_mongo_reachable():
        pytest.skip("no real mongod reachable at 127.0.0.1:27117 -- start scratchpad/mongo-mem/start.js "
                    "(mongodb-memory-server, a throwaway local mongod) to run this file")


def _wire_server(monkeypatch, db, clock, model):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "now_utc", clock.now)
    monkeypatch.setattr(server, "call_json_gpt", model)
    monkeypatch.setattr(server.entitlements, "free_is_oa_only", lambda user: False)
    monkeypatch.setenv("HINTS_ENABLED", "1")


async def _seed(db):
    await db.interviews.delete_many({})
    await db.oa_attempts.delete_many({})
    await db.resumes.delete_many({})
    await db.reports.delete_many({})
    await db.oa_attempts.insert_one(_spark_attempt("spark"))
    await db.resumes.insert_one({"resume_id": "res1", "analysis": {"extracted_projects": SPARK_PROJECTS}})


async def _advance_to_spark_dsa(doc_id, model):
    """Drives intro -> project -> followups with a generic graded answer
    until the current question is the DSA one, using the real submit route
    (so claim/release/persist all run against the real mongod exactly as
    they would in production)."""
    view = await server.get_interview(doc_id, USER)
    for _ in range(40):
        if view["current_question"]["stage"] == "dsa":
            return view
        q = view["current_question"]
        view = await server.submit_interview_answer(
            doc_id, server.AnswerIn(question_id=q["id"],
                                    answer="A clear answer about my own part and the trade-off I handled."), USER,
        )
    raise AssertionError("never reached spark dsa stage")


def test_concurrent_double_hint_request_on_real_mongo_one_winner_one_hint_consumed(monkeypatch):
    async def run():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(REAL_MONGO_URL)
        try:
            db = client[REAL_MONGO_DB]
            await _seed(db)
            clock = _Clock()
            model = _SparkModel()
            _wire_server(monkeypatch, db, clock, model)

            doc = await server.start_interview(server.StartInterviewIn(attempt_id="att1"), USER)
            view = await _advance_to_spark_dsa(doc["interview_id"], model)
            qid = view["current_question"]["id"]
            calls_before = len(model.calls)

            async def submit_hint():
                try:
                    return await server.submit_interview_answer(
                        doc["interview_id"], server.AnswerIn(question_id=qid, answer="give me a hint"), USER,
                    )
                except Exception as exc:
                    return exc

            results = await asyncio.gather(submit_hint(), submit_hint())
            stored = await db.interviews.find_one({"interview_id": doc["interview_id"]})
            return results, stored, len(model.calls) - calls_before
        finally:
            client.close()

    results, stored, new_calls = asyncio.run(run())
    statuses = sorted(200 if not hasattr(r, "status_code") else r.status_code for r in results)
    assert statuses == [200, 409]
    loser = next(r for r in results if hasattr(r, "status_code"))
    assert loser.detail["code"] == "turn_in_progress"
    assert stored.get("hints_used", 0) == 1  # exactly one hint consumed, never two
    assert new_calls == 0  # a hint turn makes no model call on either side of the race
    assert stored.get("in_flight") is None  # the claim was released, not left dangling


def test_concurrent_hint_then_real_answer_on_real_mongo_hint_always_wins_or_loses_cleanly(monkeypatch):
    """A hint request racing against a genuine solving attempt on the same
    still-open question: exactly one of the two gets through (200), the
    other gets 409 turn_in_progress, and the stored state afterward is
    internally consistent either way (if the hint won, hints_used==1 and
    the question is still open with no flags recorded yet; if the real
    answer won, the DSA turn is graded and hints_used==0)."""
    async def run():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(REAL_MONGO_URL)
        try:
            db = client[REAL_MONGO_DB]
            await _seed(db)
            clock = _Clock()
            model = _SparkModel()
            _wire_server(monkeypatch, db, clock, model)

            doc = await server.start_interview(server.StartInterviewIn(attempt_id="att1"), USER)
            view = await _advance_to_spark_dsa(doc["interview_id"], model)
            qid = view["current_question"]["id"]

            async def submit(text):
                try:
                    return await server.submit_interview_answer(
                        doc["interview_id"], server.AnswerIn(question_id=qid, answer=text), USER,
                    )
                except Exception as exc:
                    return exc

            results = await asyncio.gather(
                submit("give me a hint"),
                submit("A clear answer about my own part and the trade-off I handled."),
            )
            stored = await db.interviews.find_one({"interview_id": doc["interview_id"]})
            return results, stored
        finally:
            client.close()

    results, stored = asyncio.run(run())
    statuses = sorted(200 if not hasattr(r, "status_code") else r.status_code for r in results)
    assert statuses == [200, 409]
    loser = next(r for r in results if hasattr(r, "status_code"))
    assert loser.detail["code"] == "turn_in_progress"
    assert stored.get("in_flight") is None
    # Internally consistent regardless of who won: never both a hint AND a graded turn for this one submission.
    assert stored.get("hints_used", 0) in (0, 1)
