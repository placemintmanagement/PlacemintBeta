"""Dev/test OpenAI-spend-cutting work (2026-10): the spend guard + cache in
services/ai_service.py, and empirical call-count proofs for the retry/
duplicate-call questions raised in that audit. No interview behaviour,
prompt, or grading logic is touched by this file -- it only counts calls
against the existing commit_world/dave_world stubs, and exercises
ai_service.call_json_gpt directly with a fake OpenAI client for the cache/
cap tests (never a real call)."""
import asyncio
from types import SimpleNamespace

import pytest

import server
import services.ai_service as ai_service
from spark_support import world  # noqa: F401
from dave_support import dave_world  # noqa: F401
from commit_support import commit_world  # noqa: F401


# ---- Part A: gpt-5.4-mini pricing defaults ---------------------------------
# Defaults are read from the environment once, at module import time, so
# testing them honestly means a fresh process per case (importlib.reload
# would leave stale singletons/double atexit registrations behind for every
# later test in this session) -- subprocess gives a clean process boundary,
# the same way an env-var override actually gets applied in real use.

def _pricing_in_subprocess(env_overrides: dict) -> dict:
    import json
    import os
    import subprocess
    import sys
    code = (
        "import json, services.ai_service as a; "
        "print(json.dumps({'input': a._GPT_MINI_INPUT_USD_PER_1M, "
        "'output': a._GPT_MINI_OUTPUT_USD_PER_1M, 'inr': a._USD_TO_INR}))"
    )
    env = dict(os.environ)
    for k in ("GPT_MINI_INPUT_USD_PER_1M", "GPT_MINI_OUTPUT_USD_PER_1M", "USD_TO_INR"):
        env.pop(k, None)
    env.update(env_overrides)
    result = subprocess.run([sys.executable, "-c", code], cwd=os.path.dirname(__file__) + "/..",
                             env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_pricing_defaults_match_gpt_5_4_mini_rate_card():
    values = _pricing_in_subprocess({})
    assert values == {"input": 0.75, "output": 4.50, "inr": 88.0}


def test_pricing_defaults_are_env_overridable():
    values = _pricing_in_subprocess(
        {"GPT_MINI_INPUT_USD_PER_1M": "1.23", "GPT_MINI_OUTPUT_USD_PER_1M": "9.87", "USD_TO_INR": "90"}
    )
    assert values == {"input": 1.23, "output": 9.87, "inr": 90.0}


def test_record_model_call_computes_cost_at_the_gpt_5_4_mini_rate(monkeypatch):
    monkeypatch.setattr(ai_service, "_GPT_MINI_INPUT_USD_PER_1M", 0.75)
    monkeypatch.setattr(ai_service, "_GPT_MINI_OUTPUT_USD_PER_1M", 4.50)
    monkeypatch.setattr(ai_service, "_USD_TO_INR", 88.0)
    ai_service.reset_model_call_stats()
    ai_service._record_model_call("gpt-5.4-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    stats = ai_service.get_model_call_stats()
    assert stats["est_cost_usd"] == pytest.approx(0.75 + 4.50)  # 1M in + 1M out, at the rate card
    assert stats["est_cost_usd"] * ai_service._USD_TO_INR == pytest.approx((0.75 + 4.50) * 88)


# ---- Part 4: dev cache is OFF by default -----------------------------------

def test_dev_model_cache_off_by_default(monkeypatch):
    monkeypatch.delenv("DEV_MODEL_CACHE", raising=False)
    assert ai_service._dev_model_cache_enabled() is False


def test_dev_model_cache_never_on_in_production(monkeypatch):
    monkeypatch.setenv("DEV_MODEL_CACHE", "1")
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert ai_service._dev_model_cache_enabled() is False


def test_dev_model_cache_on_when_explicitly_enabled(monkeypatch):
    monkeypatch.setenv("DEV_MODEL_CACHE", "1")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert ai_service._dev_model_cache_enabled() is True


# ---- Part 4: an identical repeat call costs nothing when the cache is on --

class _FakeChoice:
    def __init__(self, content):
        self.message = SimpleNamespace(content=content)


class _FakeUsage:
    def __init__(self, p, c):
        self.prompt_tokens = p
        self.completion_tokens = c
        self.completion_tokens_details = None


class _FakeResp:
    def __init__(self, content, p=10, c=5):
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage(p, c)


class _FakeOpenAIClient:
    """Counts real `.chat.completions.create` calls -- this is the layer
    DEV_MODEL_CACHE must prevent a second hit on, not just call_json_gpt's
    own entry point (a cache bug that still called the real client but
    discarded the result wouldn't be caught by counting call_json_gpt calls
    alone)."""

    def __init__(self, reply="{\"ok\": true}"):
        self.create_calls = 0
        self.reply = reply
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.create_calls += 1
        return _FakeResp(self.reply)


@pytest.fixture
def fake_openai(monkeypatch, tmp_path):
    client = _FakeOpenAIClient()
    monkeypatch.setattr(ai_service, "_get_openai_client", lambda: client)
    monkeypatch.setattr(ai_service, "_DEV_MODEL_CACHE_DIR", str(tmp_path / "dev_model_cache"))
    monkeypatch.delenv("DEV_MAX_MODEL_CALLS", raising=False)
    ai_service.reset_model_call_stats()
    return client


def test_identical_repeat_call_is_free_with_cache_on(monkeypatch, fake_openai):
    monkeypatch.setenv("DEV_MODEL_CACHE", "1")
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    async def run():
        a = await ai_service.call_json_gpt("sys", "same prompt", temperature=0)
        b = await ai_service.call_json_gpt("sys", "same prompt", temperature=0)
        return a, b

    a, b = asyncio.run(run())
    assert a == b == {"ok": True}
    assert fake_openai.create_calls == 1  # second call served from cache, zero real cost
    assert ai_service.get_model_call_stats()["calls"] == 1


def test_different_prompt_is_not_a_cache_hit(monkeypatch, fake_openai):
    monkeypatch.setenv("DEV_MODEL_CACHE", "1")
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    async def run():
        await ai_service.call_json_gpt("sys", "prompt A", temperature=0)
        await ai_service.call_json_gpt("sys", "prompt B", temperature=0)

    asyncio.run(run())
    assert fake_openai.create_calls == 2


def test_cache_off_means_every_call_is_real(monkeypatch, fake_openai):
    monkeypatch.delenv("DEV_MODEL_CACHE", raising=False)

    async def run():
        await ai_service.call_json_gpt("sys", "same prompt", temperature=0)
        await ai_service.call_json_gpt("sys", "same prompt", temperature=0)

    asyncio.run(run())
    assert fake_openai.create_calls == 2  # no cache -> paid for twice, as before this change


# ---- Part 3: DEV_MAX_MODEL_CALLS caps before the over-cap call fires -------

def test_dev_max_model_calls_raises_before_the_extra_real_call(monkeypatch, fake_openai):
    monkeypatch.setenv("DEV_MAX_MODEL_CALLS", "2")
    monkeypatch.delenv("DEV_MODEL_CACHE", raising=False)

    async def run():
        await ai_service.call_json_gpt("sys", "p1")
        await ai_service.call_json_gpt("sys", "p2")
        await ai_service.call_json_gpt("sys", "p3")  # should raise, not call the client

    with pytest.raises(RuntimeError, match="DEV_MAX_MODEL_CALLS"):
        asyncio.run(run())
    assert fake_openai.create_calls == 2  # the 3rd attempt never reached the real client


def test_dev_max_model_calls_zero_is_unlimited_default(monkeypatch, fake_openai):
    monkeypatch.delenv("DEV_MAX_MODEL_CALLS", raising=False)  # default 0
    monkeypatch.delenv("DEV_MODEL_CACHE", raising=False)

    async def run():
        for _ in range(5):
            await ai_service.call_json_gpt("sys", "p")

    asyncio.run(run())
    assert fake_openai.create_calls == 5


# ---- Part 5: no retry on a successful-but-slow response --------------------

def test_slow_but_successful_response_is_not_retried(monkeypatch, fake_openai):
    """A slow call is still just ONE call -- call_json_gpt and the _spark_
    call/_dave_call/_commit_call wrappers around it have no retry loop at
    all (verified by reading server.py and services/ai_service.py; this
    proves it behaviourally). Latency alone is not a retry trigger -- only
    the OpenAI SDK's own internal max_retries (default 2, invisible to this
    codebase) fires, and only on a transient error/5xx/429, never merely on
    a slow-but-200 response."""
    monkeypatch.delenv("DEV_MODEL_CACHE", raising=False)
    monkeypatch.delenv("DEV_MAX_MODEL_CALLS", raising=False)

    real_create = fake_openai._create

    async def slow_create(**kwargs):
        await asyncio.sleep(0.05)
        return await real_create(**kwargs)

    fake_openai.chat.completions.create = slow_create

    asyncio.run(ai_service.call_json_gpt("sys", "p"))
    assert fake_openai.create_calls == 1


# ---- Part 5: double-submit call count (empirical, not assumed) ------------

class _CountingSlowModel:
    """Stands in for call_json_gpt at the server.py call site. Unlike
    commit_support.py's/dave_support.py's own stub (which resolves with no
    internal await, so two "concurrent" asyncio.gather()'d requests never
    actually interleave -- see this file's own investigation notes below),
    this one awaits a real suspension point before returning, the same way
    the real `await client.chat.completions.create(...)` genuinely suspends
    on network I/O -- this is what lets two independent concurrent HTTP
    requests' coroutines actually interleave in production."""

    def __init__(self, reply):
        self.calls = 0
        self.reply = reply

    async def __call__(self, system, prompt, model=None, temperature=None, reasoning_effort=None, usage_sink=None):
        self.calls += 1
        await asyncio.sleep(0.02)
        if usage_sink is not None:
            usage_sink.append({"prompt_tokens": 10, "completion_tokens": 5, "reasoning_tokens": 0})
        return self.reply


def _start_commit(w, attempt_id="att1"):
    return asyncio.run(server.start_interview(server.StartInterviewIn(attempt_id=attempt_id), w.user))


def _run_double_submit(w, monkeypatch, intro_answer="Hi, I'm Priya.",
                       real_answer="A clear, specific answer about my own part."):
    """Generic across Spark/Dave/Commit -- submit_interview_answer dispatches
    on interview["mode"] itself, so this only needs server.start_interview/
    submit_interview_answer plus whatever `w` (any of world/dave_world/
    commit_world) already set up. Advances past "intro" (no grading call
    there at all, so it's not a useful stage for this test) onto the first
    real grading stage, swaps in a counting-slow model to force a genuine
    interleaving opportunity (see _CountingSlowModel's own docstring), then
    fires two concurrent submits for that same still-open question.
    Returns (model, statuses)."""
    doc = asyncio.run(server.start_interview(server.StartInterviewIn(attempt_id="att1"), w.user))
    intro_qid = doc["current_question"]["id"]
    view = asyncio.run(server.submit_interview_answer(
        doc["interview_id"], server.AnswerIn(question_id=intro_qid, answer=intro_answer), w.user,
    ))
    qid = view["current_question"]["id"]

    model = _CountingSlowModel({"flags": {}, "verdict": "noted"})
    monkeypatch.setattr(server, "call_json_gpt", model)

    async def submit():
        try:
            return await server.submit_interview_answer(
                doc["interview_id"], server.AnswerIn(question_id=qid, answer=real_answer), w.user,
            )
        except Exception as exc:  # HTTPException, raised directly (no FastAPI routing layer here)
            return exc

    async def run_both():
        return await asyncio.gather(submit(), submit())

    results = asyncio.run(run_both())
    statuses = sorted(200 if not hasattr(r, "status_code") else r.status_code for r in results)
    return model, statuses


@pytest.mark.parametrize("world_fixture_name", ["world", "dave_world", "commit_world"])
def test_concurrent_double_submit_gives_one_winner_one_loser_zero_wasted_calls(world_fixture_name, request, monkeypatch):
    """FIX (see report): submit_interview_answer now atomically claims the
    turn (_claim_turn_or_409) BEFORE dispatching into _spark_answer/
    _dave_answer/_commit_answer at all -- not just a late, turn_count-only
    guard at persist time (_spark_persist/_dave_persist/_commit_persist,
    UNCHANGED, still the source of truth for whether a write lands). A
    genuine concurrent double-submit on the same still-open question (first
    real grading stage, which makes TWO real calls per attempt -- grade +
    write-next-followup) now makes exactly 2 real calls total for 2
    attempts, not 4: the loser is rejected at the claim, before it ever
    reaches the grader. One request succeeds (200), the other gets 409
    turn_in_progress (not stale_turn -- it never reached persist at all)."""
    w = request.getfixturevalue(world_fixture_name)
    model, statuses = _run_double_submit(w, monkeypatch)
    assert statuses == [200, 409], f"expected one success and one 409; got {statuses}"
    assert model.calls == 2, f"expected exactly 2 real calls total (1 winner's grade+write pair); got {model.calls}"


def test_double_submit_loser_gets_turn_in_progress_not_stale_turn(commit_world, monkeypatch):
    """The loser's 409 code is turn_in_progress (rejected at the claim,
    before ever reaching the grader or persist), distinct from stale_turn
    (the OLD code path, which only ever fires now if persist's own
    turn_count guard is reached at all -- it no longer is, for this exact
    race)."""
    doc = asyncio.run(server.start_interview(server.StartInterviewIn(attempt_id="att1"), commit_world.user))
    intro_qid = doc["current_question"]["id"]
    view = asyncio.run(server.submit_interview_answer(
        doc["interview_id"], server.AnswerIn(question_id=intro_qid, answer="hi"), commit_world.user,
    ))
    qid = view["current_question"]["id"]
    model = _CountingSlowModel({"flags": {}, "verdict": "noted"})
    monkeypatch.setattr(server, "call_json_gpt", model)

    async def submit():
        return await server.submit_interview_answer(
            doc["interview_id"], server.AnswerIn(question_id=qid, answer="A real answer here."), commit_world.user,
        )

    async def run_both():
        return await asyncio.gather(submit(), submit(), return_exceptions=True)

    results = asyncio.run(run_both())
    loser = next(r for r in results if isinstance(r, Exception))
    assert loser.detail["code"] == "turn_in_progress"


# ---- Part 5: a genuinely stale (already-answered) question makes zero -----

def test_stale_question_id_makes_zero_grading_calls(commit_world):
    """Distinct from the double-submit case above: this is a request for a
    question_id that is no longer current at all (e.g. a retried/duplicate
    request arriving after the interview has already moved on). This is
    rejected by the early stale_question check before any grading call --
    the "cheap" 409 path the task description had in mind."""
    w = commit_world
    doc = _start_commit(w)
    model = w.model
    calls_before = len(model.calls)

    with pytest.raises(Exception) as exc_info:
        asyncio.run(server.submit_interview_answer(
            doc["interview_id"],
            server.AnswerIn(question_id="commit-some-other-question-not-current", answer="x"),
            w.user,
        ))
    assert getattr(exc_info.value, "status_code", None) == 409
    assert len(model.calls) == calls_before  # zero grading calls for a genuinely stale question_id


# ---- Part C tests 3-4: crash releases the claim; a stale one self-heals ---

def test_crash_mid_processing_releases_the_claim(commit_world):
    """Simulates a crash between the claim and persist (e.g. an unexpected
    bug -- NOT a model-call failure; those are already caught inside
    _commit_call/_dave_call/_spark_call and never propagate this far). The
    claim must still be released by submit_interview_answer's own
    `finally`, not left to the 60s staleness fallback -- proven by a
    normal follow-up submit on the same question succeeding IMMEDIATELY
    afterward, not after any wait."""
    w = commit_world
    doc = _start_commit(w)
    intro_qid = doc["current_question"]["id"]
    view = asyncio.run(server.submit_interview_answer(
        doc["interview_id"], server.AnswerIn(question_id=intro_qid, answer="hi"), w.user,
    ))
    qid = view["current_question"]["id"]

    real_commit_answer = server._commit_answer

    async def crashing_commit_answer(interview, body):
        raise RuntimeError("simulated crash mid-processing")

    server._commit_answer = crashing_commit_answer
    try:
        with pytest.raises(RuntimeError, match="simulated crash"):
            asyncio.run(server.submit_interview_answer(
                doc["interview_id"], server.AnswerIn(question_id=qid, answer="A real answer here."), w.user,
            ))
    finally:
        server._commit_answer = real_commit_answer  # restore, without touching commit_world's own patches

    stored = next(d for d in w.db.interviews.docs if d["interview_id"] == doc["interview_id"])
    assert stored.get("in_flight") is None  # released by the `finally`, not left dangling

    # A normal follow-up submit on the SAME question succeeds immediately --
    # not blocked, proving the claim didn't leak.
    result = asyncio.run(server.submit_interview_answer(
        doc["interview_id"], server.AnswerIn(question_id=qid, answer="A real answer here."), w.user,
    ))
    assert result["status"] == "in_progress"


def test_stale_claim_older_than_60s_does_not_block(commit_world):
    """A marker left behind by a crashed process (or anything that skipped
    the `finally` entirely, e.g. a hard process kill) self-heals: once
    _TURN_CLAIM_STALE_SECONDS has passed, the next request may override
    it rather than being permanently blocked."""
    w = commit_world
    doc = _start_commit(w)
    intro_qid = doc["current_question"]["id"]
    view = asyncio.run(server.submit_interview_answer(
        doc["interview_id"], server.AnswerIn(question_id=intro_qid, answer="hi"), w.user,
    ))
    qid = view["current_question"]["id"]

    stored = next(d for d in w.db.interviews.docs if d["interview_id"] == doc["interview_id"])
    stored["in_flight"] = {
        "question_id": qid,
        "claimed_at": w.clock.t - server._TURN_CLAIM_STALE_SECONDS - 1,  # 61s old -- stale
    }

    result = asyncio.run(server.submit_interview_answer(
        doc["interview_id"], server.AnswerIn(question_id=qid, answer="A real answer here."), w.user,
    ))
    assert result["status"] == "in_progress"  # not blocked despite the (stale) marker


def test_live_claim_under_60s_still_blocks(commit_world):
    """Converse of the above -- a marker that is NOT yet stale still
    blocks, confirming the 60s boundary actually does something (rather
    than every marker being treated as stale by some bug)."""
    w = commit_world
    doc = _start_commit(w)
    intro_qid = doc["current_question"]["id"]
    view = asyncio.run(server.submit_interview_answer(
        doc["interview_id"], server.AnswerIn(question_id=intro_qid, answer="hi"), w.user,
    ))
    qid = view["current_question"]["id"]

    stored = next(d for d in w.db.interviews.docs if d["interview_id"] == doc["interview_id"])
    stored["in_flight"] = {"question_id": qid, "claimed_at": w.clock.t - 5}  # 5s old -- still live

    with pytest.raises(Exception) as exc_info:
        asyncio.run(server.submit_interview_answer(
            doc["interview_id"], server.AnswerIn(question_id=qid, answer="A real answer here."), w.user,
        ))
    assert exc_info.value.detail["code"] == "turn_in_progress"
