"""Golden transcript tests: a full Spark, Dave and Commit interview, each
driven start-to-finish through the REAL route handlers (server.start_interview
/ server.submit_interview_answer / server.get_interview / server.final_report
-- the same call path test_spark_interview.py / test_dave_interview.py /
test_commit_interview.py already use), with a fixed clock (the `world`/
`dave_world`/`commit_world` fixtures from spark_support.py/dave_support.py/
commit_support.py), a deterministic stubbed AI boundary (the same `_Model`/
`_DaveModel`/`_CommitModel` those fixtures install), and a fixed `random`
seed set immediately before each run (project/DSA-problem/HR-question/
CS-question selection all draw from the stdlib `random` module's global
state, never an injected Random instance, when called through server.py's
real route handlers -- see capgemini_interview/core.py's pick_project et
al., which default to the global `random` module whenever the caller
passes no explicit rng, and server.py's call sites never pass one).

Each run's transcript (questions asked, in order; every stage transition, in
order; the final stored score dict; the final report JSON from
server.final_report) is snapshotted to a golden file under tests/golden/ and
compared byte-for-byte (normalised line endings, two volatile uuid4-based id
fields blanked out -- everything else, including every timestamp, is left in
place and must match exactly, since the fixed clock makes them deterministic
too and a refactor that quietly shifts budget timing should show up here).

Regeneration: run with UPDATE_GOLDEN=1 to (re)write the stored golden file
from the current code's actual behaviour -- this is how the golden files
were produced in the first place; a normal run only compares and fails loudly
on any drift.

Scope (explicit, so the gap is not silently assumed away): this file drives
only ONE deterministic happy-path run per tier -- default answer text, no
spent follow-up/project2/cs/hr budgets, no timeout, no abandonment, no
injected/fake quotes, no hints, no humanizer/pushback feature flags. Those
edge cases are already covered by test_spark_interview.py, test_dave_interview.py,
test_commit_interview.py and the humanize/pushback/dsa_hints test files; this
file's only job is byte-for-byte behavioural pinning of one representative
full run per tier, for a later refactor to diff against."""
import asyncio
import json
import os
import random
from pathlib import Path

import server

import spark_support as sp
import dave_support as dv
import commit_support as cm
from spark_support import world  # noqa: F401 (pytest fixture)
from dave_support import dave_world  # noqa: F401 (pytest fixture)
from commit_support import commit_world  # noqa: F401 (pytest fixture)

GOLDEN_DIR = Path(__file__).parent / "golden"
UPDATE = os.environ.get("UPDATE_GOLDEN") == "1"

# The only two fields that are inherently non-reproducible across runs: both
# are uuid4()-based (server.new_id), which draws from os.urandom, not the
# stdlib `random` module, so seeding `random` has no effect on them.
_VOLATILE_KEYS = {"interview_id", "report_id"}


def _normalize(obj):
    if isinstance(obj, dict):
        return {k: ("<NORMALIZED>" if k in _VOLATILE_KEYS else _normalize(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    return obj


def _dump(payload) -> str:
    normalized = _normalize(payload)
    text = json.dumps(normalized, indent=2, sort_keys=True, default=str)
    # Normalise line endings so this is stable across checkouts/platforms
    # (this environment is Windows/Git Bash; the repo may have core.autocrlf
    # settings that differ from CI's).
    return text.replace("\r\n", "\n").replace("\r", "\n") + "\n"


def _compare_or_update(name: str, payload) -> None:
    path = GOLDEN_DIR / name
    text = _dump(payload)
    if UPDATE:
        path.write_text(text, encoding="utf-8", newline="\n")
        return
    assert path.exists(), f"golden file missing: {path} (run with UPDATE_GOLDEN=1 to create it first)"
    stored = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    assert text == stored, (
        f"golden transcript drift in {name}. If this is an intentional behaviour "
        f"change, re-run with UPDATE_GOLDEN=1 to regenerate it; otherwise this is "
        f"exactly the regression this test exists to catch."
    )


def _drive_and_record(get_fn, answer_fn, w, iid, answer_text, max_steps=200):
    """Generic driver (works for Spark/Dave/Commit alike, since _get/_answer
    share the same (w, iid[, qid, text]) shapes across all three support
    modules): records every question actually presented, in order, and every
    distinct stage visited, in order. Returns (questions, stages, final_view)."""
    view = get_fn(w, iid)
    questions = []
    stages = [view["stage"]]
    steps = 0
    while view["status"] == "in_progress":
        q = view["current_question"]
        questions.append({"id": q["id"], "stage": q["stage"], "prompt": q["prompt"]})
        view = answer_fn(w, iid, q["id"], answer_text)
        if view["stage"] not in stages:
            stages.append(view["stage"])
        steps += 1
        if steps > max_steps:
            raise AssertionError("interview did not end")
    return questions, stages, view


def _fake_oa_review(attempt_id, user):
    async def review(a, u):
        return {"verdict": "borderline", "composite_score": 0.5, "weakest_section": "",
                "section_results": {}}
    return review(attempt_id, user)


async def _fake_call_json(system, prompt, **kwargs):
    return {"overall_verdict": "borderline", "overall_score": 50, "narrative": "n",
            "weakest_dimension": "", "strongest_dimension": "", "next_steps": []}


def _report(monkeypatch, attempt_id, user):
    """Drive the real /report route (server.final_report) the same way
    test_spark_report_route.py's `_report` helper does: stub oa_review and
    call_json (the final synthesis call) so the report's own narrative text
    is deterministic, everything upstream of it (resume analysis, the
    interview_summary built from the real stored interview doc) is not."""
    monkeypatch.setattr(server, "oa_review", _fake_oa_review)
    monkeypatch.setattr(server, "call_json", _fake_call_json)
    return asyncio.run(server.final_report(attempt_id, user))


def _clear_feature_flags(monkeypatch):
    # Independent of whatever the ambient environment happens to have set --
    # the golden runs pin to the all-flags-off baseline (the same baseline
    # test_spark_interview.py / test_dave_interview.py / test_commit_interview.py
    # already implicitly run under).
    for var in ("HUMANIZE_ENABLED", "PUSHBACK_ENABLED", "HINTS_ENABLED"):
        monkeypatch.delenv(var, raising=False)


# ---- Spark ------------------------------------------------------------------
def test_spark_golden_transcript(world, monkeypatch):  # noqa: F811
    _clear_feature_flags(monkeypatch)
    random.seed(20240101)  # fixed seed: pick_project draws from the global `random` module
    iid = sp._start(world)["interview_id"]
    questions, stages, final_view = _drive_and_record(
        sp._get, sp._answer, world, iid,
        "A clear answer about my own part and the trade-off.",
    )
    stored = sp._stored(world, iid)
    report = _report(monkeypatch, "att1", world.user)
    payload = {
        "tier": "spark",
        "questions": questions,
        "stage_transitions": stages,
        "final_status": final_view["status"],
        "final_closing_message": final_view["closing_message"],
        "stored_turns": stored["turns"],
        "final_score": stored["spark_score"],
        "final_report": report,
    }
    _compare_or_update("spark_golden.json", payload)


# ---- Dave ---------------------------------------------------------------------
def test_dave_golden_transcript(dave_world, monkeypatch):  # noqa: F811
    _clear_feature_flags(monkeypatch)
    random.seed(20240102)  # fixed seed: dave_pick_two_projects / pick_dave_dsa_problem /
                            # dave_cs_pick_first_two / dave_cs_pick_weighted / dave_pick_hr_first_two
    iid = dv._start(dave_world)["interview_id"]
    questions, stages, final_view = _drive_and_record(
        dv._get, dv._answer, dave_world, iid,
        "A clear answer about my own part and the trade-off I handled.",
    )
    stored = dv._stored(dave_world, iid)
    report = _report(monkeypatch, "att1", dave_world.user)
    payload = {
        "tier": "dave",
        "questions": questions,
        "stage_transitions": stages,
        "final_status": final_view["status"],
        "final_closing_message": final_view["closing_message"],
        "stored_turns": stored["turns"],
        "final_score": stored["dave_score"],
        "final_report": report,
    }
    _compare_or_update("dave_golden.json", payload)


# ---- Commit ---------------------------------------------------------------------
def test_commit_golden_transcript(commit_world, monkeypatch):  # noqa: F811
    _clear_feature_flags(monkeypatch)
    random.seed(20240103)  # fixed seed: same family of draws as Dave, plus Commit's own
                            # CS-grilling (oops/java/sql) bank selection
    iid = cm._start(commit_world)["interview_id"]
    questions, stages, final_view = _drive_and_record(
        cm._get, cm._answer, commit_world, iid,
        "A clear, specific answer about my own part and the trade-off I handled.",
    )
    stored = cm._stored(commit_world, iid)
    report = _report(monkeypatch, "att1", commit_world.user)
    payload = {
        "tier": "commit",
        "questions": questions,
        "stage_transitions": stages,
        "final_status": final_view["status"],
        "final_closing_message": final_view["closing_message"],
        "stored_turns": stored["turns"],
        "final_score": stored["commit_score"],
        "final_report": report,
    }
    _compare_or_update("commit_golden.json", payload)
