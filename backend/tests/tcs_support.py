"""Shared fixtures and helpers for test_tcs_interview.py. In-memory fake db,
mocked clock, stubbed model -- no Mongo, no network, no real AI call.
Mirrors dave_support.py's/spark_support.py's own pattern closely; reuses
their generic, tier-agnostic _Coll/_Result/_Clock/_quote/_candidate_text
directly (those have no Capgemini-specific content at all -- see
spark_support.py).

Updated for the part-1 TCS restructure: single "interview" stage with
per-tier phases (project/architecture/coding/puzzle/core), no more TR/MR/
HR. `_TcsModel` is otherwise unchanged -- it already grades generically
off "Key points (in order):"/"Candidate answer:", which every phase's
prompt still uses."""
import asyncio
import re
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import server
from spark_support import _Clock, _Coll, _candidate_text, _quote  # noqa: F401

TCS_PROJECTS = [
    {"name": "Shop inventory tracker", "tech_stack": "Python, SQLite",
     "one_line_summary": "Tracks stock levels for a small shop."},
]

# A resume with only ONE distinct tech_stack token, to exercise the "ask
# directly" opener branch (fewer than 2 languages inferable).
TCS_PROJECTS_SINGLE_LANGUAGE = [
    {"name": "Personal blog", "tech_stack": "Python", "one_line_summary": "A simple static blog."},
]


class _TcsModel:
    """Stub for call_json_gpt. Records every call; returns key-point-flag
    grading JSON matching tcs_key_point_flags_prompt's shape -- the only
    kind of prompt the TCS interview ever sends to a model (no live
    follow-up writer, unlike Spark/Dave)."""

    def __init__(self):
        self.calls = []
        self.key_point_value = True
        self.clarity_value = True
        self.quote_mode = "real"  # "real" | "fake" | "instruction"
        # Time-filling adaptive flow: when the prompt itself offers a
        # follow-up slot (allow_follow_up=True was passed -- detectable
        # generically because the JSON schema instruction then asks for
        # "needs_follow_up"), this model answers needs_follow_up with
        # `self.needs_follow_up_value` -- a fast-answering simulated
        # student is driven with this False (never probed further), a
        # slow/thorough one with this True (always probed, up to the
        # tier's own depth cap, enforced by core.py, not by this stub).
        self.needs_follow_up_value = False

    async def __call__(self, system, prompt, model=None, temperature=None, reasoning_effort=None, usage_sink=None):
        self.calls.append({"system": system, "prompt": prompt, "model": model, "temperature": temperature})
        if usage_sink is not None:
            usage_sink.append({"prompt_tokens": 100, "completion_tokens": 20, "reasoning_tokens": 0})
        if "Key points (in order):" not in prompt:
            raise AssertionError("unexpected prompt: " + prompt[:200])
        block = prompt.split("Key points (in order):", 1)[1].split("Candidate answer:", 1)[0]
        n = len(re.findall(r"\n\s*\d+\.\s", block))
        key_points = [_quote(prompt, self.key_point_value, self.quote_mode) for _ in range(n)]
        result = {"key_points": key_points, "verdict": "Answer noted."}
        if "communication_clarity" in prompt:
            result["communication_clarity"] = _quote(prompt, self.clarity_value, self.quote_mode)
        if "needs_follow_up" in prompt:
            result["needs_follow_up"] = bool(self.needs_follow_up_value)
            result["follow_up_question"] = (
                "Can you go one level deeper on that?" if self.needs_follow_up_value else ""
            )
        return result


def _tcs_attempt(tier=None):
    doc = {"attempt_id": "att1", "user_id": "u1", "company_name": "TCS NQT", "company_id": "tcs-nqt",
           "resume_id": "res1"}
    if tier is not None:
        doc["tcs_tier"] = {"tier": tier}
    return doc


def _make_tcs_world(monkeypatch):
    """Factored out of the `tcs_world` fixture below so a test that needs
    MORE THAN ONE independent "world" in a single test (e.g. a determinism
    check that runs a sitting twice and compares results) can call this
    directly, sequentially, with the same `monkeypatch` fixture -- each
    call simply re-patches the same module attributes with a fresh fake
    db/clock/model, exactly as the pytest fixture does for a single world."""
    monkeypatch.setenv("TCS_INTERVIEW_ENABLED", "1")
    clock = _Clock()
    model = _TcsModel()
    fake = SimpleNamespace(
        interviews=_Coll(), oa_attempts=_Coll([_tcs_attempt()]), reports=_Coll(),
        # company_id is REQUIRED here (unlike Spark/Dave's own resume fixtures,
        # which only ever start via attempt_id): the company_id start path's
        # resume-required gate (_latest_resume_for_company) looks up
        # {"user_id", "company_id"} together, not by resume_id/attempt_id.
        resumes=_Coll([{"resume_id": "res1", "user_id": "u1", "company_id": "tcs-nqt",
                        "analysis": {"extracted_projects": TCS_PROJECTS}}]),
    )
    monkeypatch.setattr(server, "db", fake)
    monkeypatch.setattr(server, "now_utc", clock.now)
    monkeypatch.setattr(server, "call_json_gpt", model)
    monkeypatch.setattr(server.entitlements, "free_is_oa_only", lambda user: False)
    return SimpleNamespace(db=fake, clock=clock, model=model, user={"user_id": "u1", "name": "Priya"})


@pytest.fixture
def tcs_world(monkeypatch):
    return _make_tcs_world(monkeypatch)


def _start(w, **kwargs):
    body = server.StartInterviewIn(**kwargs)
    return asyncio.run(server.start_interview(body, w.user))


def _answer(w, iid, qid, text):
    return asyncio.run(server.submit_interview_answer(iid, server.AnswerIn(question_id=qid, answer=text), w.user))


def _get(w, iid):
    return asyncio.run(server.get_interview(iid, w.user))


def _stored(w, iid):
    return next(d for d in w.db.interviews.docs if d["interview_id"] == iid)


def _run_to_end(w, iid, text=None, max_steps=200, latency_seconds=0):
    """Drive a full TCS interview answer by answer. Returns the view after
    each answer. `latency_seconds` (time-filling adaptive flow): advances
    the fake clock by this much BEFORE each answer is submitted, simulating
    how long the candidate took to answer -- 0 (the default) means every
    answer lands "instantly" on the fake clock, matching every pre-existing
    caller's behaviour byte-for-byte."""
    view = _get(w, iid)
    steps = []
    answer_text = text or "A clear, specific answer with real detail, reasoning and a concrete example."
    while view["status"] == "in_progress":
        if latency_seconds:
            w.clock.t += latency_seconds
        q = view["current_question"]
        try:
            view = _answer(w, iid, q["id"], answer_text)
        except HTTPException as exc:
            if isinstance(exc.detail, dict) and exc.detail.get("code") == "time_up":
                # The simulated latency pushed this submission past the
                # overall deadline -- same as a real candidate running out
                # of time mid-answer. The interview is already finished
                # server-side (_finish was called before this raised); the
                # final view reflects that.
                view = _get(w, iid)
                steps.append(view)
                break
            raise
        steps.append(view)
        if len(steps) > max_steps:
            raise AssertionError("interview did not end")
    return steps
