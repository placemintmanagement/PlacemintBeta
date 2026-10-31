# -*- coding: utf-8 -*-
"""TCS interview orchestration: the DB-touching, clock-touching, model-
calling glue -- the one part of this package that is deliberately NOT pure
(core.py explicitly is pure; this file is where that purity ends).

Lives inside the tcs_interview package rather than server.py. Every
function below takes its db/clock/model/id dependencies as explicit
keyword arguments (no module-level globals), so this module never needs
to import server.py.

REWRITE (part 1 of the 4-part TCS restructure): the old TR/MR/HR three-
stage model is gone. There is now a single "interview" stage with an
ordered list of PHASES per tier (core.TCS_TIER_PHASE_ORDER) -- all of
`technical_questions`/`managerial_questions`/`hr_questions` are replaced
by one `phase_questions: {phase_name: [questions]}` dict per interview
doc.

Long-sitting hygiene (new in this rewrite): Digital/Prime sittings run up
to 60 minutes. _rolling_context() below builds a BOUNDED context block --
short one-line summaries of already-finished phases, plus a capped window
of the most recent turns within the phase in progress -- instead of ever
resending the whole transcript to the model. See _rolling_context's own
docstring and tests/test_tcs_interview.py's prompt-size-bounded test.
"""
import logging
import random
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from services.ai_service import GPT_MINI, GRADING_INJECTION_DEFENSE, tcs_key_point_flags_prompt

from . import core
from .banks import interview_puzzle_bank

logger = logging.getLogger(__name__)


def _seeded_real_puzzle_provider(interview_id: str) -> core.PuzzleProvider:
    """Part 3: the real puzzle-provider, replacing core.py's Part-1 stub.
    Ignores the `rng` argument core.PuzzleProvider's interface passes --
    the real pick is seeded by `interview_id` alone (see
    interview_puzzle_bank.pick_puzzle_for_interview's own docstring for
    why), not by the per-start-call rng used for everything else."""
    def _provider(tier: str, rng: random.Random) -> Dict[str, Any]:
        return interview_puzzle_bank.puzzle_question_for_interview(tier, interview_id)
    return _provider

_SYSTEM_GRADER = ("You grade interview answers as an experienced engineer. Return only strict JSON.\n\n"
                  + GRADING_INJECTION_DEFENSE)
GRADING_TEMPERATURE = 0  # STATED (matches Capgemini's own grading temperature convention)
_MODEL_ANSWER_CAP = 4000   # OUR ESTIMATE: characters of one answer sent to the model
_STORED_ANSWER_CAP = 8000  # OUR ESTIMATE: characters of one answer kept

# ---- Rolling per-phase summary (long-sitting hygiene) ----------------------
_RECENT_TURNS_IN_CONTEXT = 3     # OUR ESTIMATE: only this many of the CURRENT phase's own turns
_CONTEXT_SNIPPET_CHARS = 160     # OUR ESTIMATE: per-turn snippet cap inside the context block
_PHASE_SUMMARY_CHARS = 200       # OUR ESTIMATE: cap on one phase's rolling summary line


def _phase_summary_line(phase: str, turns: List[Dict[str, Any]]) -> str:
    """A short, DETERMINISTIC (no extra AI call) one-line summary of a
    just-finished phase, built from already-computed flags -- never from a
    fresh model call. Stored once, re-used on every later grading call
    instead of ever re-sending that phase's own turns in full."""
    phase_turns = [t for t in turns if t["phase"] == phase]
    if not phase_turns:
        return f"{phase}: not reached."
    scored = [core.flags_score({k: v for k, v in t["flags"].items() if k != core.EXTRA_SIGNAL}) for t in phase_turns]
    avg = round(100 * (sum(scored) / len(scored)))
    line = f"{phase}: {len(phase_turns)} question(s) answered, avg content score {avg}%."
    return line[:_PHASE_SUMMARY_CHARS]


def _rolling_context(interview: Dict[str, Any]) -> Optional[str]:
    """Bounded context for the NEXT grading call: one short line per
    already-finished phase (interview['phase_summaries'], updated once per
    phase transition -- see _advance_and_persist below), plus at most the
    last `_RECENT_TURNS_IN_CONTEXT` turns of the phase CURRENTLY in
    progress (never the whole interview). Size is bounded by construction:
    it never grows past (number of phases in this tier's order) summary
    lines + `_RECENT_TURNS_IN_CONTEXT` snippets, regardless of how many
    turns the sitting has actually taken so far."""
    summaries = interview.get("phase_summaries") or {}
    state = interview["state"]
    phase = state["phase"]
    turns = interview.get("turns", [])
    current_phase_turns = [t for t in turns if t["phase"] == phase][-_RECENT_TURNS_IN_CONTEXT:]
    lines: List[str] = [summaries[p] for p in summaries]
    for t in current_phase_turns:
        q_snip = " ".join(str(t["question"]).split())[:_CONTEXT_SNIPPET_CHARS]
        v_snip = " ".join(str(t.get("verdict") or "").split())[:_CONTEXT_SNIPPET_CHARS]
        lines.append(f"- (this phase) Q: {q_snip} -> {v_snip}")
    return "\n".join(lines) if lines else None


def _stage_questions(interview: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    return interview["phase_questions"]


def _current_bank_question(interview: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    state = interview["state"]
    questions = interview["phase_questions"][state["phase"]]
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


_FOLLOWUP_TEXT_CAP = 300  # OUR ESTIMATE: a follow-up question is meant to be ONE short sentence


def _follow_up_text(raw: Any) -> Optional[str]:
    """None unless the SAME grading call's response both asked for a
    follow-up AND supplied real question text -- a model that sets
    needs_follow_up=true but leaves follow_up_question empty (or vice
    versa) is treated as "no follow-up", never half-trusted."""
    if not isinstance(raw, dict) or raw.get("needs_follow_up") is not True:
        return None
    text = raw.get("follow_up_question")
    if not isinstance(text, str):
        return None
    cleaned = " ".join(text.split())[:_FOLLOWUP_TEXT_CAP]
    return cleaned or None


def _log_rejections(interview_id: str, question_id: str, rejections: List[Dict[str, Any]]) -> None:
    for r in rejections:
        logger.warning("tcs interview %s question %s: flag %r rejected (%s)",
                       interview_id, question_id, r["flag"], r["reason"])


def _score_doc(tier: str, turns: list) -> Dict[str, Any]:
    return core.tcs_interview_score(tier, turns)


def _report_answers(turns: list) -> list:
    """Canonical {question_id, answer, grade:{one_line_verdict, score}}
    shape -- the SAME shape _report_answer_entry (server.py) already
    produces for Spark/Dave/Commit, built independently here so server.py's
    already-generic _build_interview_summary/final_report_prompt work on a
    TCS interview for free, same as every other tier."""
    return [
        {"question_id": t["question_id"], "answer": t["answer"],
         "grade": {"one_line_verdict": t.get("verdict") or "", "score": round(100 * core.flags_score(
             {k: v for k, v in t["flags"].items() if k != core.EXTRA_SIGNAL}))}}
        for t in turns
    ]


async def _invalidate_cached_report(db, interview: Dict[str, Any]) -> None:
    await db.reports.delete_many({"interview_id": interview["interview_id"], "user_id": interview["user_id"]})
    if interview.get("attempt_id"):
        await db.reports.delete_many({"attempt_id": interview["attempt_id"], "user_id": interview["user_id"]})


async def _persist(db, interview: Dict[str, Any], expected_turn_count: int, changes: Dict[str, Any]) -> None:
    """Optimistic guard: a double-submitted answer cannot advance the
    phase twice -- same turn_count convention as _spark_persist/
    _dave_persist/_commit_persist in server.py. This is also WHY resuming
    an interrupted sitting (reload, closed tab, idle-but-not-expired) works
    correctly: every single answer is written to db.interviews here, not
    just held in memory, so the next read (refresh_interview, below, or a
    fresh GET after a reload) always sees the latest state/turns/
    current_question from the database, never from a server-process-local
    variable that a reload would lose."""
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
        "tcs_score": _score_doc(interview["tier"], turns),
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
    _commit_finalize_if_expired. This is also the resume path for an idle-
    past-deadline sitting: the NEXT read (reload, or the report route)
    closes it out from whatever was last persisted, never from in-memory
    state, because `interview` here is whatever the caller freshly loaded
    from db.interviews."""
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
                          tier_source: str = "oa_designated", company_id: str = "tcs-nqt",
                          puzzle_provider: Optional[core.PuzzleProvider] = None) -> dict:
    """Same call signature _start_spark_interview uses (server.py), so
    server.py's `_tier_start_fn` dispatch needs no special case for TCS.

    `puzzle_provider` (Part 3: real wiring, replacing Part 1's stub):
    left as None by every real caller, which seeds the REAL
    banks/interview_puzzle_bank.py-backed provider to THIS interview's own
    id (see _seeded_real_puzzle_provider below) -- one puzzle per sitting,
    reproducible on replay/resume because it is a pure function of
    interview_id, not of wall-clock time. A test may still pass its own
    puzzle_provider explicitly (e.g. core.stub_puzzle_provider, or a spy)
    to bypass the real bank entirely.

    `rng` (time-filling adaptive flow -- determinism): seeded by
    `interview_id` alone, same pattern _seeded_real_puzzle_provider already
    used for the puzzle pick -- so EVERY pre-selected pick for this sitting
    (project's inferred question, the coding/core draws, not just the
    puzzle) is a pure, reproducible function of interview_id, never of
    wall-clock time or call order. Re-deriving a sitting's own
    phase_questions from its stored interview_id always reproduces exactly
    what was persisted at start time."""
    now = now_utc().timestamp()
    interview_id = new_id("intv")
    rng = random.Random(f"tcs-interview:{interview_id}")
    project = core.pick_project(resume_projects, rng)
    provider = puzzle_provider or _seeded_real_puzzle_provider(interview_id)
    phase_questions = core.build_phase_questions(tier, resume_projects, project, rng, provider)
    first_phase = core.TCS_TIER_PHASE_ORDER[tier][0]
    first = phase_questions[first_phase][0]
    interview = {
        "interview_id": interview_id,
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
        "state": core.new_state(tier, now),
        "status": "in_progress",
        "turn_count": 0,
        "project": project,
        "phase_questions": phase_questions,
        "phase_summaries": {},
        "current_question": {"id": first["id"], "phase": first_phase, "prompt": first["text"]},
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
    tier = interview["tier"]
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
    phase = state["phase"]

    bank_q = _current_bank_question(interview)
    is_followup = bool(current.get("is_followup"))
    key_points = core.FOLLOWUP_KEY_POINTS if is_followup else bank_q.get("key_points", [])
    extra_signal = core.EXTRA_SIGNAL
    context = _rolling_context(interview)

    # Time-filling adaptive flow: this SAME grading call also decides
    # whether to probe deeper -- but only offered when the tier's own
    # follow-up depth cap AND this phase's own time budget both still
    # allow one (see core.follow_up_depth_allows/follow_up_time_budget_
    # allows' own docstrings for the non-last-vs-last-phase asymmetry).
    # Never offered on an already-maxed-out depth, so a model that (bugged
    # or not) keeps asking for "just one more" follow-up is hard-capped
    # regardless of what it returns.
    depth = state.get("followup_depth", 0)
    allow_follow_up = (core.follow_up_depth_allows(tier, depth)
                       and core.follow_up_time_budget_allows(tier, phase, state, now))

    prompt = tcs_key_point_flags_prompt(current["prompt"], key_points, model_answer, extra_signal, context,
                                        allow_follow_up=allow_follow_up)
    raw = await _tcs_call(call_json_gpt, prompt, _SYSTEM_GRADER, GRADING_TEMPERATURE, usage, f"grade_{phase}")
    flags, rejections = core.normalize_key_point_flags(raw, len(key_points), model_answer, extra_signal)
    verdict = _verdict(raw, "Your answer is recorded.")

    turn = {"phase": phase, "topic": bank_q["topic"], "question_id": current["id"], "question": current["prompt"],
            "answer": stored, "verdict": verdict, "flags": flags}
    turns.append(turn)
    _log_rejections(interview.get("interview_id"), current["id"], rejections)

    follow_up_text = _follow_up_text(raw) if allow_follow_up else None
    if follow_up_text:
        # Serve the follow-up: the engine stays on this SAME top-level
        # question (state["index"] untouched), only followup_depth moves
        # -- core.advance() is not called this turn, so no extra top-level
        # question/phase is consumed by this follow-up.
        new_depth = depth + 1
        state["followup_depth"] = new_depth
        nxt = core.make_followup_question(bank_q["id"], phase, follow_up_text, new_depth)
    else:
        state["followup_depth"] = 0
        nxt = core.advance(tier, _stage_questions(interview), state, now)

    phase_summaries = dict(interview.get("phase_summaries") or {})
    if nxt is None or nxt["phase"] != phase:
        # The phase just ended (either the whole interview is done, or we
        # moved to the next phase) -- freeze its rolling summary now, once,
        # deterministically (no extra AI call), so later grading calls
        # never need that phase's own turns again.
        phase_summaries[phase] = _phase_summary_line(phase, turns)

    changes: Dict[str, Any] = {
        "state": state, "turns": turns, "turn_count": count + 1, "usage": usage,
        "phase_summaries": phase_summaries,
    }
    if nxt is None:
        changes.update({
            "status": state["status"], "current_question": None,
            "tcs_score": _score_doc(tier, turns),
            "answers": _report_answers(turns),
            "completed_at": iso(now_utc()),
        })
    else:
        changes["current_question"] = nxt
    await _persist(db, interview, count, changes)
    interview.update(changes)
    return core.client_view(interview, now)
