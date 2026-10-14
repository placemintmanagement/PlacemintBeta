"""Real-MongoDB verification of the turn-claim fix (double-submit race,
test_openai_spend_controls.py's test_concurrent_double_submit_* /
test_crash_mid_processing_releases_the_claim / test_stale_claim_*).

Those tests run against spark_support.py's in-memory fake `_Coll`, whose
equality matching is plain Python dict `==` -- order-independent. Real
MongoDB's whole-subdocument equality match is NOT order-independent (BSON
byte comparison): empirically confirmed here (see
test_whole_subdocument_equality_is_order_sensitive_on_real_mongo) that
{"a": 1, "b": 2} does not match a stored {"b": 2, "a": 1}, even though
they are the same dict in Python. _claim_turn_or_409/_release_turn_claim
(server.py) were written with this in mind: _subdoc_leaf_filter matches
`current_question`/`in_flight` by individual leaf field via dot-notation,
never by whole-object equality -- this file proves that design decision
against a real mongod, not just the fake stub.

Uses a throwaway local mongod via mongodb-memory-server (scratchpad/
mongo-mem/start.js) on 127.0.0.1:27117 -- a real mongod process on a temp
data directory, never Atlas, never any real/production database. Every
test here skips gracefully (pytest.skip) if that mongod is not reachable,
so a normal `pytest` run on a machine without it running is unaffected.

call_json_gpt is still mocked (same stub classes as spark_support.py/
dave_support.py/commit_support.py) -- this file verifies MongoDB
semantics, not a second OpenAI-spend check (that is conftest.py's job).

IMPORTANT: AsyncIOMotorClient is bound to whichever asyncio event loop is
running when it is first used; asyncio.run() creates and then CLOSES a
fresh loop every call, so a client (or anything awaited on it) cannot be
reused across more than one asyncio.run() call ("RuntimeError: Event loop
is closed"). Every test below therefore does its ENTIRE body -- creating
its own Motor client, seeding, exercising server.*, asserting -- inside
exactly one `async def _run(): ...` driven by exactly one
`asyncio.run(_run())`, not spread across several."""
import asyncio

import pytest

import server
from spark_support import _Clock, _attempt as _spark_attempt, PROJECTS as SPARK_PROJECTS, _Model as _SparkModel
from dave_support import _DaveModel, DAVE_PROJECTS
from commit_support import _CommitModel, COMMIT_PROJECTS

REAL_MONGO_URL = "mongodb://127.0.0.1:27117"
REAL_MONGO_DB = "real_mongo_turn_claim_test"


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


async def _seed(db, tier, projects):
    await db.interviews.delete_many({})
    await db.oa_attempts.delete_many({})
    await db.resumes.delete_many({})
    await db.reports.delete_many({})
    await db.oa_attempts.insert_one(_spark_attempt(tier))
    await db.resumes.insert_one({"resume_id": "res1", "user_id": "u1", "analysis": {"extracted_projects": projects}})


USER = {"user_id": "u1", "name": "Priya"}


class _CountingSlowModel:
    """A real await point (asyncio.sleep) is what reliably lets two
    "concurrent" asyncio.gather()'d requests interleave -- real MongoDB's
    own network round-trip for each update_one call would do this on its
    own too, but keeping an explicit sleep makes the test deterministic
    rather than racing on real I/O timing alone."""

    def __init__(self, reply):
        self.calls = 0
        self.reply = reply

    async def __call__(self, system, prompt, model=None, temperature=None, reasoning_effort=None, usage_sink=None):
        self.calls += 1
        await asyncio.sleep(0.03)
        if usage_sink is not None:
            usage_sink.append({"prompt_tokens": 10, "completion_tokens": 5, "reasoning_tokens": 0})
        return self.reply


def test_whole_subdocument_equality_is_order_sensitive_on_real_mongo():
    """Documents why server.py's claim/release filters use per-leaf-field
    dot-notation (_subdoc_leaf_filter) rather than whole-object equality
    on `current_question`/`in_flight` -- both are built as fresh dict
    literals at multiple call sites across server.py, so relying on every
    one of them using the exact same key order would be fragile and, as
    shown here, genuinely wrong against real MongoDB (even though the
    fake test `_Coll` cannot catch this, since Python dict `==` is
    order-independent)."""
    async def run():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(REAL_MONGO_URL)
        try:
            db = client[REAL_MONGO_DB]
            await db.docs.delete_many({})
            await db.docs.insert_one({"_id": "d1", "sub": {"a": 1, "b": 2}})
            same_order = await db.docs.find_one({"sub": {"a": 1, "b": 2}})
            diff_order = await db.docs.find_one({"sub": {"b": 2, "a": 1}})
            dotted = await db.docs.find_one({"sub.a": 1, "sub.b": 2})
            return same_order, diff_order, dotted
        finally:
            client.close()

    same_order, diff_order, dotted = asyncio.run(run())
    assert same_order is not None
    assert diff_order is None  # the actual finding: order DOES matter for whole-object equality
    assert dotted is not None  # dot-notation (per leaf field) is order-independent, as used in server.py


_TIER_PARAMS = [
    ("spark", _SparkModel, SPARK_PROJECTS),
    ("dave", _DaveModel, DAVE_PROJECTS),
    ("commit", _CommitModel, COMMIT_PROJECTS),
]


@pytest.mark.parametrize("tier,model_cls,projects", _TIER_PARAMS, ids=[t[0] for t in _TIER_PARAMS])
def test_double_submit_on_real_mongo_one_winner_one_loser_zero_wasted(monkeypatch, tier, model_cls, projects):
    """Against a REAL mongod: two concurrent submits on the same still-open
    question give exactly one 200 and one 409 turn_in_progress, and the
    loser makes ZERO model calls (rejected at the claim, before dispatch)."""
    async def run():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(REAL_MONGO_URL)
        try:
            db = client[REAL_MONGO_DB]
            await _seed(db, tier, projects)
            clock = _Clock()
            _wire_server(monkeypatch, db, clock, model_cls())

            doc = await server.start_interview(server.StartInterviewIn(attempt_id="att1"), USER)
            intro_qid = doc["current_question"]["id"]
            view = await server.submit_interview_answer(
                doc["interview_id"], server.AnswerIn(question_id=intro_qid, answer="Hi, I'm Priya."), USER,
            )
            qid = view["current_question"]["id"]

            slow_model = _CountingSlowModel({"flags": {}, "verdict": "noted"})
            monkeypatch.setattr(server, "call_json_gpt", slow_model)

            async def submit():
                try:
                    return await server.submit_interview_answer(
                        doc["interview_id"],
                        server.AnswerIn(question_id=qid, answer="A clear, specific answer about my own part."),
                        USER,
                    )
                except Exception as exc:
                    return exc

            results = await asyncio.gather(submit(), submit())
            return results, slow_model.calls
        finally:
            client.close()

    results, calls = asyncio.run(run())
    statuses = sorted(200 if not hasattr(r, "status_code") else r.status_code for r in results)
    assert statuses == [200, 409], f"[{tier}] expected one success and one 409; got {statuses}"
    loser = next(r for r in results if hasattr(r, "status_code"))
    assert loser.detail["code"] == "turn_in_progress", f"[{tier}] {loser.detail}"
    # Exactly 2, not 4: the single winner's own grade+write-next-followup
    # pair. The LOSER made zero real calls -- it never reached the grader.
    assert calls == 2, f"[{tier}] expected exactly 2 real calls (the single winner's pair); got {calls}"


@pytest.mark.parametrize("tier,model_cls,projects", _TIER_PARAMS, ids=[t[0] for t in _TIER_PARAMS])
def test_marker_cleared_after_success_on_real_mongo(monkeypatch, tier, model_cls, projects):
    async def run():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(REAL_MONGO_URL)
        try:
            db = client[REAL_MONGO_DB]
            await _seed(db, tier, projects)
            clock = _Clock()
            _wire_server(monkeypatch, db, clock, model_cls())

            doc = await server.start_interview(server.StartInterviewIn(attempt_id="att1"), USER)
            intro_qid = doc["current_question"]["id"]
            await server.submit_interview_answer(
                doc["interview_id"], server.AnswerIn(question_id=intro_qid, answer="hi"), USER,
            )
            return await db.interviews.find_one({"interview_id": doc["interview_id"]})
        finally:
            client.close()

    stored = asyncio.run(run())
    assert stored.get("in_flight") is None, f"[{tier}] marker not cleared after a successful submit"


def test_marker_cleared_after_exception_on_real_mongo(monkeypatch):
    """Commit tier only (the three tiers share the identical claim/release
    wiring in submit_interview_answer -- see test_openai_spend_controls.py
    for the in-memory-fake version of this same proof across all three)."""
    async def run():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(REAL_MONGO_URL)
        try:
            db = client[REAL_MONGO_DB]
            await _seed(db, "commit", COMMIT_PROJECTS)
            clock = _Clock()
            _wire_server(monkeypatch, db, clock, _CommitModel())

            doc = await server.start_interview(server.StartInterviewIn(attempt_id="att1"), USER)
            intro_qid = doc["current_question"]["id"]
            view = await server.submit_interview_answer(
                doc["interview_id"], server.AnswerIn(question_id=intro_qid, answer="hi"), USER,
            )
            qid = view["current_question"]["id"]

            real_commit_answer = server._commit_answer

            async def crashing_commit_answer(interview, body):
                raise RuntimeError("simulated crash mid-processing")

            server._commit_answer = crashing_commit_answer
            crashed = False
            try:
                await server.submit_interview_answer(
                    doc["interview_id"], server.AnswerIn(question_id=qid, answer="A real answer here."), USER,
                )
            except RuntimeError as exc:
                crashed = "simulated crash" in str(exc)
            finally:
                server._commit_answer = real_commit_answer

            stored_after_crash = await db.interviews.find_one({"interview_id": doc["interview_id"]})

            result = await server.submit_interview_answer(
                doc["interview_id"], server.AnswerIn(question_id=qid, answer="A real answer here."), USER,
            )
            return crashed, stored_after_crash, result
        finally:
            client.close()

    crashed, stored_after_crash, result = asyncio.run(run())
    assert crashed
    assert stored_after_crash.get("in_flight") is None  # released by the `finally`, not left dangling
    assert result["status"] == "in_progress"  # the follow-up submit succeeded immediately, not blocked


def test_stale_marker_over_60s_overridden_on_real_mongo(monkeypatch):
    async def run():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(REAL_MONGO_URL)
        try:
            db = client[REAL_MONGO_DB]
            await _seed(db, "commit", COMMIT_PROJECTS)
            clock = _Clock()
            _wire_server(monkeypatch, db, clock, _CommitModel())

            doc = await server.start_interview(server.StartInterviewIn(attempt_id="att1"), USER)
            intro_qid = doc["current_question"]["id"]
            view = await server.submit_interview_answer(
                doc["interview_id"], server.AnswerIn(question_id=intro_qid, answer="hi"), USER,
            )
            qid = view["current_question"]["id"]

            await db.interviews.update_one(
                {"interview_id": doc["interview_id"]},
                {"$set": {"in_flight": {"question_id": qid,
                                         "claimed_at": clock.t - server._TURN_CLAIM_STALE_SECONDS - 1}}},
            )
            return await server.submit_interview_answer(
                doc["interview_id"], server.AnswerIn(question_id=qid, answer="A real answer here."), USER,
            )
        finally:
            client.close()

    result = asyncio.run(run())
    assert result["status"] == "in_progress"  # not blocked despite the (stale) marker


def test_live_marker_under_60s_still_blocks_on_real_mongo(monkeypatch):
    async def run():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(REAL_MONGO_URL)
        try:
            db = client[REAL_MONGO_DB]
            await _seed(db, "commit", COMMIT_PROJECTS)
            clock = _Clock()
            _wire_server(monkeypatch, db, clock, _CommitModel())

            doc = await server.start_interview(server.StartInterviewIn(attempt_id="att1"), USER)
            intro_qid = doc["current_question"]["id"]
            view = await server.submit_interview_answer(
                doc["interview_id"], server.AnswerIn(question_id=intro_qid, answer="hi"), USER,
            )
            qid = view["current_question"]["id"]

            await db.interviews.update_one(
                {"interview_id": doc["interview_id"]},
                {"$set": {"in_flight": {"question_id": qid, "claimed_at": clock.t - 5}}},  # 5s old -- still live
            )
            try:
                await server.submit_interview_answer(
                    doc["interview_id"], server.AnswerIn(question_id=qid, answer="A real answer here."), USER,
                )
                return None
            except Exception as exc:
                return exc
        finally:
            client.close()

    exc = asyncio.run(run())
    assert exc is not None and exc.detail["code"] == "turn_in_progress"
