# -*- coding: utf-8 -*-
"""TCS interview orchestration: the DB-touching, clock-touching, model-
calling glue -- the one part of this package that is deliberately NOT pure
(core.py explicitly is pure; this file is where that purity ends).

Lives inside the tcs_interview package rather than server.py, unlike
Capgemini's own _start_spark_interview/_spark_answer/_spark_refresh (which
live directly in server.py and reach server.py's module-level `db`/
`call_json_gpt`/`now_utc`/`new_id`/`iso` as globals) -- a deliberate
difference, not an oversight: the task that built this module required
commit 2 (this file) to be self-contained NEW FILES ONLY, with ZERO lines
touched in server.py until commit 3. Since this module cannot import
server.py (server.py will import THIS package, and Python can't have both
directions), every function below takes its db/clock/model/id dependencies
as explicit keyword arguments instead of reaching for globals. Commit 3's
server.py wiring is then mechanical: five thin trampoline functions
(_start_tcs_interview, _tcs_answer, _tcs_refresh, _finalize_if_expired's
TCS branch) that each do nothing but forward server.py's own `db`,
`now_utc`, `new_id`, `iso`, `call_json_gpt` into the matching function here
-- see server.py's own TCS section for exactly those five call sites.

Mirrors Capgemini Spark's shape closely (one turn = one graded Q&A, a
turn_count-guarded optimistic persist, timeout finalization idempotent on
read) but is simpler by design: v1 has no humanizer, no pushback, no DSA
hints (explicit product scope -- see core.py's module docstring), and
every TCS question is fixed SEED-content bank text, never a live model-
written follow-up -- so there is exactly one kind of model call anywhere
in this file (grading the current answer against its key_points), unlike
Spark's writer-and-grader split.
"""
import logging
import random
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from services.ai_service import GPT_MINI, GRADING_INJECTION_DEFENSE, tcs_key_point_flags_prompt

from . import core

logger = logging.getLogger(__name__)

_SYSTEM_GRADER = ("You grade interview answers as an experienced engineer. Return only strict JSON.\n\n"
                  + GRADING_INJECTION_DEFENSE)
GRADING_TEMPERATURE = 0  # STATED (matches Capgemini's own grading temperature convention)
_MODEL_ANSWER_CAP = 4000   # OUR ESTIMATE: characters of one answer sent to the model
_STORED_ANSWER_CAP = 8000  # OUR ESTIMATE: characters of one answer kept


def _stage_questions(interview: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    return {
        "technical": interview["technical_questions"],
        "managerial": interview["managerial_questions"],
        "hr": interview["hr_questions"],
    }


def _current_bank_question(interview: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    state = interview["state"]
    questions = _stage_questions(interview)[state["stage"]]
    idx = state["index"]
    return questions[idx] if idx < len(questions) else None


async def _tcs_call(call_json_gpt, prompt: str, system: str, temperature: float, usage: list, purpose: str) -> Any:
    sink: list = []
    try:
        out = await call_json_gpt(system, prompt, model=GPT_MINI, temperature=temperature, usage_sink=sink)
    except Exception:
        logger.exception("tcs %s: model call failed", purpose)
        out = None
    usage.extend({**rec, "purpose": purpose} for rec in sink)
    return out


def _verdict(raw: Any, fallback: str) -> str:
    text = raw.get("verdict") if isinstance(raw, dict) else None
    return " ".join(text.split())[:300] if isinstance(text, str) and text.strip() else fallback


def _log_rejections(interview_id: str, question_id: str, rejections: List[Dict[str, Any]]) -> None:
    for r in rejections:
        logger.warning("tcs interview %s question %s: flag %r rejected (%s)",
                       interview_id, question_id, r["flag"], r["reason"])


def _score_doc(turns: list) -> Dict[str, Any]:
    tr = core.technical_score([t for t in turns if t["stage"] == "technical"])
    mr = core.managerial_score([t for t in turns if t["stage"] == "managerial"])
    hr = core.hr_score([t for t in turns if t["stage"] == "hr"])
    return core.tcs_interview_score(tr, mr, hr)


def _report_answers(turns: list) -> list:
    """Canonical {question_id, answer, grade:{one_line_verdict, score}}
    shape -- the SAME shape _report_answer_entry (server.py) already
    produces for Spark/Dave/Commit, built independently here (not by
    importing server.py's helper, which this package cannot import; not
    by importing capgemini_interview.flags_score either, to keep this
    package's scoring 100% its own) so server.py's already-generic
    _build_interview_summary/final_report_prompt work on a TCS interview
    for free, same as every other tier."""
    return [
        {"question_id": t["question_id"], "answer": t["answer"],
         "grade": {"one_line_verdict": t.get("verdict") or "", "score": round(100 * core.flags_score(t["flags"]))}}
        for t in turns
    ]


async def _invalidate_cached_report(db, interview: Dict[str, Any]) -> None:
    await db.reports.delete_many({"interview_id": interview["interview_id"], "user_id": interview["user_id"]})
    if interview.get("attempt_id"):
        await db.reports.delete_many({"attempt_id": interview["attempt_id"], "user_id": interview["user_id"]})


async def _persist(db, interview: Dict[str, Any], expected_turn_count: int, changes: Dict[str, Any]) -> None:
    """Optimistic guard: a double-submitted answer cannot advance the stage
    twice -- same turn_count convention as _spark_persist/_dave_persist/
    _commit_persist in server.py (and the same one _claim_turn_or_409's
    atomic claim, applied generically by server.py before this is ever
    reached, also keys off)."""
    res = await db.interviews.update_one(
        {"interview_id": interview["interview_id"], "turn_count": expected_turn_count},
        {"$set": changes},
    )
    if res.matched_count == 0:
        raise HTTPException(409, {"code": "stale_turn", "message": "That question was already answered. Refresh to continue."})
    if changes.get("status") in ("completed", "timed_out"):
        await _invalidate_cached_report(db, interview)


async def _finish(db, iso, now_utc, interview: Dict[str, Any], now: float, timed_out: bool) -> None:
    state = dict(interview["state"])
    if timed_out:
        core.finish_timed_out(state)
    turns = interview.get("turns", [])
    count = interview.get("turn_count", 0)
    changes = {
        "state": state, "status": state["status"], "current_question": None,
        "tcs_score": _score_doc(turns),
        "answers": _report_answers(turns),
        "completed_at": iso(now_utc()),
        "turn_count": count + 1,
    }
    await _persist(db, interview, count, changes)
    interview.update(changes)


async def finalize_if_expired(*, db, now_utc, iso, interview: Dict[str, Any]) -> Dict[str, Any]:
    """Idempotent: a TCS interview past its deadline is closed as timed out
    the first time anything reads it -- same pattern as
    _spark_finalize_if_expired/_dave_finalize_if_expired/
    _commit_finalize_if_expired."""
    now = now_utc().timestamp()
    state = interview["state"]
    if state["status"] != "in_progress" or not core.is_expired(state, now):
        return interview
    try:
        await _finish(db, iso, now_utc, interview, now, timed_out=True)
    except HTTPException as exc:
        if exc.status_code != 409:
            raise
        fresh = await db.interviews.find_one({"interview_id": interview["interview_id"]}, {"_id": 0})
        return fresh or interview
    return interview


async def refresh_interview(*, db, now_utc, iso, interview: Dict[str, Any]) -> Dict[str, Any]:
    interview = await finalize_if_expired(db=db, now_utc=now_utc, iso=iso, interview=interview)
    return core.client_view(interview, now_utc().timestamp())


async def start_interview(*, db, now_utc, new_id, iso, attempt: dict, attempt_id: Optional[str],
                          resume_projects: List[dict], user: Dict[str, Any], tier: str = "ninja",
                          tier_source: str = "oa_designated", company_id: str = "tcs-nqt") -> dict:
    """Same call signature _start_spark_interview uses (server.py:4345),
    so server.py's `_tier_start_fn` dispatch (which calls every start
    function identically: positional attempt/attempt_id/resume_projects/
    user, then keyword tier/tier_source/company_id) needs no special case
    for TCS -- see commit 3's thin `_start_tcs_interview` trampoline."""
    now = now_utc().timestamp()
    rng = random.Random()
    project = core.pick_project(resume_projects, rng)
    tr_questions = core.select_technical_questions(tier, resume_projects, project, rng)
    mr_questions = core.select_managerial_questions(tier, project, rng)
    hr_questions = core.select_hr_questions(tier, rng)
    first = tr_questions[0]
    interview = {
        "interview_id": new_id("intv"),
        "user_id": attempt["user_id"],
        "attempt_id": attempt_id,
        "company_id": company_id,
        "company_name": attempt["company_name"],
        "resume_id": attempt.get("resume_id"),
        "tier": tier,
        "tier_source": tier_source,
        # Account name, validated (no email, no placeholder), used only for
        # the closing message. Never sent to a model.
        "candidate_name": core.usable_account_name(user.get("name"), user.get("email")),
        "mode": "tcs",
        "state": core.new_state(now),
        "status": "in_progress",
        "turn_count": 0,
        "project": project,
        "technical_questions": tr_questions,
        "managerial_questions": mr_questions,
        "hr_questions": hr_questions,
        "current_question": {"id": first["id"], "stage": "technical", "prompt": first["text"]},
        "turns": [],
        "answers": [],
        "usage": [],
        "tcs_score": None,
        "created_at": iso(now_utc()),
    }
    await db.interviews.insert_one(interview)
    interview.pop("_id", None)
    return core.client_view(interview, now)


async def answer_interview(*, db, now_utc, iso, call_json_gpt, interview: Dict[str, Any], body) -> dict:
    """`body` only needs .question_id/.answer (server.py's AnswerIn
    satisfies this by duck typing; no pydantic import needed here)."""
    now = now_utc().timestamp()
    state = interview["state"]
    if state["status"] != "in_progress":
        raise HTTPException(409, {"code": "interview_closed", "message": "This interview is already finished."})
    if core.is_expired(state, now):
        await _finish(db, iso, now_utc, interview, now, timed_out=True)
        raise HTTPException(409, {"code": "time_up", "message": "Time is up. Your answers so far are saved."})
    current = interview.get("current_question") or {}
    if str(body.question_id) != str(current.get("id")):
        raise HTTPException(409, {"code": "stale_question", "message": "That question is no longer open. Refresh to continue."})
    answer = (body.answer or "").strip()
    if not answer:
        raise HTTPException(400, "Answer is empty")

    stored = answer[:_STORED_ANSWER_CAP]
    model_answer = answer[:_MODEL_ANSWER_CAP]
    usage = list(interview.get("usage", []))
    turns = list(interview.get("turns", []))
    count = interview.get("turn_count", 0)
    stage = state["stage"]

    bank_q = _current_bank_question(interview)
    key_points = bank_q.get("key_points", [])
    extra_signal = bank_q.get("extra_signal")
    prompt = tcs_key_point_flags_prompt(current["prompt"], key_points, model_answer, extra_signal)
    raw = await _tcs_call(call_json_gpt, prompt, _SYSTEM_GRADER, GRADING_TEMPERATURE, usage, f"grade_{stage}")
    flags, rejections = core.normalize_key_point_flags(raw, len(key_points), model_answer, extra_signal)
    verdict = _verdict(raw, "Your answer is recorded.")

    turn = {"stage": stage, "topic": bank_q["topic"], "question_id": current["id"], "question": current["prompt"],
            "answer": stored, "verdict": verdict, "flags": flags}
    turns.append(turn)
    _log_rejections(interview.get("interview_id"), current["id"], rejections)

    nxt = core.advance(_stage_questions(interview), state, now)

    changes: Dict[str, Any] = {"state": state, "turns": turns, "turn_count": count + 1, "usage": usage}
    if nxt is None:
        changes.update({
            "status": state["status"], "current_question": None,
            "tcs_score": _score_doc(turns),
            "answers": _report_answers(turns),
            "completed_at": iso(now_utc()),
        })
    else:
        changes["current_question"] = nxt
    await _persist(db, interview, count, changes)
    interview.update(changes)
    return core.client_view(interview, now)
