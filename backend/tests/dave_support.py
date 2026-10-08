"""Shared fixtures and helpers for test_dave_interview.py. Reuses spark_support's
tier-agnostic/parameterized helpers (_Coll, _Result, _attempt, _Clock) directly;
defines its own `world` fixture and model stub because those are coupled to
exact prompt wording, which differs for Dave's extra stages (project2, split
complexity, hr)."""
import asyncio
import json
import re
from types import SimpleNamespace

import pytest

import server
from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini import (
    capgemini_interview as ci,
)
from spark_support import START, PROJECTS, _attempt, _Clock, _Coll, _candidate_text, _quote  # noqa: F401

CLOSE_PRIYA = "Thank you, Priya, for attending the interview. We will update you soon."

# A second, distinct project pair so dave_pick_two_projects always has two to choose from.
DAVE_PROJECTS = PROJECTS + [
    {"name": "Analytics dashboard", "tech_stack": "React, Postgres", "one_line_summary": "Shows usage metrics."},
]


class _DaveModel:
    """Stub for call_json_gpt. Records every call; returns grader or writer JSON
    matching whichever Dave prompt builder produced the prompt text."""

    def __init__(self):
        self.calls = []
        self.project1_value = True
        self.project2_value = True
        self.dsa_value = True
        self.time_value = True
        self.space_value = True
        self.hr_value = True
        self.cs_value = True
        self.quote_mode = "real"

    async def __call__(self, system, prompt, model=None, temperature=None, reasoning_effort=None, usage_sink=None):
        self.calls.append({"system": system, "prompt": prompt, "model": model, "temperature": temperature})
        if usage_sink is not None:
            usage_sink.append({"prompt_tokens": 100, "completion_tokens": 20, "reasoning_tokens": 0})

        if "writing the next question in a technical interview about the candidate's second project" in prompt:
            n = sum(1 for c in self.calls if "second project" in c["prompt"])
            return {"question": f"Project2 Q{n}: tell me more about that, specifically?"}
        if "Write exactly ONE follow-up" in prompt:
            n = sum(1 for c in self.calls if "Write exactly ONE follow-up" in c["prompt"])
            return {"question": f"Follow-up {n}: what did you change, and why?"}
        if "challenge_described" in prompt:
            flags = {"own_contribution": _quote(prompt, self.project2_value, self.quote_mode),
                     "challenge_described": _quote(prompt, self.project2_value, self.quote_mode)}
            return {"flags": flags, "verdict": "Project2 answer noted."}
        if "Judge this interview answer about a project" in prompt:
            flags = {k: _quote(prompt, self.project1_value, self.quote_mode) for k in ci.PROJECT_SIGNALS}
            return {"flags": flags, "verdict": "Clear project answer."}
        if "Judge the coding answer against the rubric" in prompt:
            return {"approach_elements": [_quote(prompt, self.dsa_value, self.quote_mode)] * 2,
                    "edge_cases_named": _quote(prompt, True, self.quote_mode),
                    "verdict": "Solid approach."}
        if "complexity of the approach they used" in prompt:
            dim = "time" if "the time complexity" in prompt else "space"
            val = self.time_value if dim == "time" else self.space_value
            return {f"{dim}_stated": _quote(prompt, val, self.quote_mode),
                    f"{dim}_correct": _quote(prompt, val, self.quote_mode),
                    "verdict": "Complexity noted."}
        if "Judge this CS-fundamentals interview answer" in prompt:
            block = prompt.split("Key points (in order):", 1)[1].split("Candidate answer:", 1)[0]
            n = len(re.findall(r"\n\s*\d+\.\s", block))
            key_points = [_quote(prompt, self.cs_value, self.quote_mode) for _ in range(n)]
            return {"key_points": key_points, "verdict": "CS answer noted."}
        if "Judge this HR interview answer" in prompt:
            flags = {k: _quote(prompt, self.hr_value, self.quote_mode) for k in ci.HR_SIGNALS}
            return {"flags": flags, "verdict": "HR answer noted."}
        raise AssertionError("unexpected prompt: " + prompt[:200])


@pytest.fixture
def dave_world(monkeypatch):
    clock = _Clock()
    model = _DaveModel()
    fake = SimpleNamespace(interviews=_Coll(), oa_attempts=_Coll([_attempt("dave")]), reports=_Coll(),
                           resumes=_Coll([{"resume_id": "res1", "analysis": {"extracted_projects": DAVE_PROJECTS}}]))
    monkeypatch.setattr(server, "db", fake)
    monkeypatch.setattr(server, "now_utc", clock.now)
    monkeypatch.setattr(server, "call_json_gpt", model)
    monkeypatch.setattr(server.entitlements, "free_is_oa_only", lambda user: False)
    monkeypatch.delenv("DAVE_INTERVIEW_TEST_DURATION_SECONDS", raising=False)
    return SimpleNamespace(db=fake, clock=clock, model=model, user={"user_id": "u1", "name": "Priya"})


def _start(w, attempt_id="att1"):
    return asyncio.run(server.start_interview(server.StartInterviewIn(attempt_id=attempt_id), w.user))


def _answer(w, iid, qid, text):
    return asyncio.run(server.submit_interview_answer(iid, server.AnswerIn(question_id=qid, answer=text), w.user))


def _get(w, iid):
    return asyncio.run(server.get_interview(iid, w.user))


def _stored(w, iid):
    return next(d for d in w.db.interviews.docs if d["interview_id"] == iid)


def _run_to_end(w, iid, *, followup_budget_spent=False, text=None, max_steps=60):
    """Drive a full Dave interview answer by answer. Returns the view after each answer."""
    view = _get(w, iid)
    steps = []
    answer_text = text or "A clear answer about my own part and the trade-off I handled."
    spent = False
    while view["status"] == "in_progress":
        q = view["current_question"]
        if followup_budget_spent and not spent and q["stage"] == "followups":
            w.clock.t += ci.DAVE_BUDGETS_SECONDS["project1_followups"]
            spent = True
        view = _answer(w, iid, q["id"], answer_text)
        steps.append(view)
        if len(steps) > max_steps:
            raise AssertionError("interview did not end")
    return steps
