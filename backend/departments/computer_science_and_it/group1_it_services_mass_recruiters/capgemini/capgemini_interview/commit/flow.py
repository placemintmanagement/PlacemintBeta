# -*- coding: utf-8 -*-
"""Capgemini Commit tier (text, 75 minutes, 7.50 LPA) -- stage machine,
budgets, weights, and CS-grilling/project-followup selection. Pure: no
imports from server.py, no database, no clock, no LLM (same discipline as
core.py). Mirrors core.py's dave_* function patterns (stage machine driven
by code, element-flag grading via core.py's existing quote-injection
defence, server-enforced deadline with soft stage budgets that trigger
wrap-up and never end the interview) but commit_* functions are entirely
its own -- nothing here calls or changes any Spark- or Dave-only function,
and nothing in core.py's Spark/Dave functions was touched to build this.

Reuses, read-only, from core.py: pick_dave_dsa_problem/get_dave_dsa_problem/
dsa_question/normalize_dave_dsa_flags/dave_dsa_complexity_score (the medium
DSA bank and its complexity stages), dave_pick_two_projects/project_text/
project_question (two different resume projects, same fallback behaviour),
dave_pick_hr_first_two/dave_pick_hr_third/hr_question_text (HR selection,
unchanged), PROJECT_SIGNALS/normalize_project_flags (project-answer
grading), flags_score/project_followups_score (scoring), quote_rejection/
_checked_flag indirectly via normalize_cs_flags-style use below.
Reuses, read-only, from dave/cs.py: SQL_QUESTIONS/BY_TOPIC["sql"] (the SQL
bank only -- oops/os are Commit's own, deeper banks in java_bank.py/
oops_bank.py). Dave's own oops/os/sql module is never modified.

PROJECT1/PROJECT2 FOLLOW-UPS (STATED): minimum 6 follow-ups on project 1,
minimum 5 on project 2, one more only if that project's stage budget is not
yet spent (INTERPOLATED rule, same pattern as core.py's FOLLOWUP_MIN/MAX).
One combined budget per project covers both its "ask about the project" turn
and all its follow-ups (STATED budget keys: "project1_followups" 14 min,
"project2_followups" 12 min) -- same pattern as Dave's project1_followups
budget.

DSA (STATED): reuses Dave's medium DSA bank and complexity stages unchanged.
One additional fixed-template prompt ("Is there a more efficient approach?")
is asked at most once, only if the rubric's efficiency flag
(required_approach[1], always the "reaches the more efficient approach" item
in every Dave DSA rubric) is absent after the main DSA grading -- code
decides (INTERPOLATED mechanism: the follow-up answer is graded with the
same DSA rubric, and the efficiency flag is OR'd with the new result, so a
candidate who recovers it under the nudge still earns credit).

CS GRILLING (STATED selection rule, INTERPOLATED tie-breaks): Q1 always
OOPs, Q2 always Java (order shuffled in which is asked first between the
two), Q3 a weighted draw (oops 0.4, java 0.4, sql 0.2), Q4 the same weighted
draw only if the cs_grilling budget is not spent. No question repeats.
Each question has exactly 2 fixed follow-ups (from the bank, never
model-written); follow-up 1 is always asked, follow-up 2 only if the
cs_grilling budget allows (INTERPOLATED: same budget-gated pattern as the
Q3->Q4 and follow-up-count decisions elsewhere in this module). Nudge
(STATED): one fixed template if an answer is under 15 words, at most once
per MAIN question (INTERPOLATED: not applied to follow-up answers, since
follow-ups are themselves a prompt for more specific detail), none if under
2 minutes remain. Question score (STATED): fraction of key points present
across the main question and whichever follow-ups were actually asked,
pooled into one score per question (same merge-dict pattern as core.py's
dave_dsa_complexity_score for dsa+complexity).

HR (STATED): reuses Dave's HR bank and selection unchanged (2-3 questions),
via core.py's existing dave_pick_hr_first_two/dave_pick_hr_third/
hr_question_text/dave_budget_exceeded-style gating, re-implemented here only
because the *state* shape differs (own budget_started_at/stage), not because
the selection logic itself differs.
"""
import os
import random
from typing import Any, Dict, List, Optional, Tuple

from .. import core

# ---- Stages (STATED order) --------------------------------------------------
COMMIT_DURATION_SECONDS = 75 * 60  # STATED
COMMIT_STAGES = ["intro", "project1", "project1_followups", "project2", "project2_followups",
                 "dsa", "time_complexity", "space_complexity", "cs_grilling", "hr"]  # STATED order

# Soft stage budgets (STATED values; sum to 75 minutes). Budgets never end
# the interview early: they trigger a wrap-up instruction / the
# "ask one more" decision. The 75-minute deadline is the only hard stop.
COMMIT_BUDGETS_SECONDS = {
    "intro": 3 * 60,                 # STATED
    "project1_followups": 14 * 60,   # STATED (covers project1 + project1_followups)
    "project2_followups": 12 * 60,   # STATED (covers project2 + project2_followups)
    "dsa": 15 * 60,                  # STATED
    "complexity": 4 * 60,            # STATED (shared by time_complexity + space_complexity)
    "cs_grilling": 15 * 60,          # STATED
    "hr": 6 * 60,                    # STATED
    "buffer": 6 * 60,                # STATED (3+14+12+15+4+15+6+6 = 75 min)
}

# Report-only weights (STATED, named constants). No pass or fail.
COMMIT_WEIGHTS = {"project1": 0.18, "project2": 0.18, "dsa_complexity": 0.24, "cs_grilling": 0.28, "hr": 0.12}

COMMIT_P1_FOLLOWUP_MIN = 6   # STATED
COMMIT_P1_FOLLOWUP_MAX = 7   # INTERPOLATED: one more only if the budget allows
COMMIT_P2_FOLLOWUP_MIN = 5   # STATED
COMMIT_P2_FOLLOWUP_MAX = 6   # INTERPOLATED: one more only if the budget allows

COMMIT_MORE_EFFICIENT_QUESTION = "Is there a more efficient approach?"  # STATED fixed template

CS_NUDGE_WORD_THRESHOLD = 15                # STATED
CS_NUDGE_MIN_REMAINING_SECONDS = 2 * 60     # STATED
CS_NUDGE_TEXT = "Could you explain that a bit more, or give an example?"  # STATED fixed template

CS_TOPIC_WEIGHTS: Dict[str, float] = {"oops": 0.4, "java": 0.4, "sql": 0.2}  # STATED

# core.py's STAGE_LABELS doesn't have Commit's own stage names
# (project1_followups, project2, project2_followups, cs_grilling) -- own
# copy here since the only edit allowed in core.py is the TIER_TABLE entry.
# STATED: 9 frontend stage pills -- project1_followups collapses into the
# "Project 1" pill and project2_followups into the "Project 2" pill, same
# collapsing idea as Dave's "followups" stage sharing Project 1's budget,
# just also collapsed in the PILL display here (Dave shows followups as its
# own pill; Commit's 9-pill spec does not leave room for a 10th/11th pill).
COMMIT_STAGE_LABELS = {
    "intro": "Intro",
    "project1": "Project 1",
    "project1_followups": "Project 1",
    "project2": "Project 2",
    "project2_followups": "Project 2",
    "dsa": "DSA",
    "time_complexity": "Time",
    "space_complexity": "Space",
    "cs_grilling": "OOPs & Java",
    "hr": "HR",
    "done": "Done",
}

# The 9 distinct pills shown in the UI (STATED order/set): internal stages
# project1_followups and project2_followups are not separate pills.
COMMIT_PILL_STAGES = ["intro", "project1", "project2", "dsa", "time_complexity",
                      "space_complexity", "cs_grilling", "hr", "done"]


def is_commit(tier: Optional[str]) -> bool:
    """True only for a designed Commit tier. spark, dave, None and unknown
    tiers are False and keep their own flow (or the generic interview). Same
    shape as core.py's is_spark/is_dave, defined here (not in core.py) since
    the only edit allowed in core.py is the TIER_TABLE entry itself."""
    entry = core.tier_entry(tier)
    return bool(entry and entry["status"] == "designed" and tier == "commit")


def commit_duration_seconds(env: Optional[Dict[str, str]] = None) -> int:
    """75 minutes in production. A test-only override is honoured only when
    ENVIRONMENT=test, so a real deployment cannot shorten the interview.
    Same pattern as core.py's spark_duration_seconds/dave_duration_seconds."""
    env = os.environ if env is None else env
    raw = env.get("COMMIT_INTERVIEW_TEST_DURATION_SECONDS")
    if env.get("ENVIRONMENT") == "test" and raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return COMMIT_DURATION_SECONDS


# ---- Stage machine (pure; advanced only by code) ----------------------------
def commit_new_state(now: float, duration_seconds: int) -> Dict[str, Any]:
    return {
        "stage": "intro",
        "status": "in_progress",
        "timed_out": False,
        "started_at": now,
        "deadline_at": now + duration_seconds,
        "budget_started_at": {"intro": now},
        "p1_followups_asked": 0,
        "p2_followups_asked": 0,
        "dsa_efficiency_nudge_used": False,
        "cs_index": 0,
        "cs_sub": 0,            # 0 = main question, 1 = follow-up 1, 2 = follow-up 2
        "cs_nudge_used": [False, False, False, False],
        "hr_index": 0,
        "hr_nudge_used": [False, False, False],
        "hr_second_category": None,
    }


def commit_budget_exceeded(state: Dict[str, Any], now: float, budget_key: str) -> bool:
    started = state["budget_started_at"].get(budget_key)
    if started is None:
        return False
    return now - started >= COMMIT_BUDGETS_SECONDS[budget_key]


def commit_wrap_up_now(state: Dict[str, Any], now: float) -> bool:
    stage = state["stage"]
    if stage == "intro":
        return commit_budget_exceeded(state, now, "intro")
    if stage in ("project1", "project1_followups"):
        return commit_budget_exceeded(state, now, "project1_followups")
    if stage in ("project2", "project2_followups"):
        return commit_budget_exceeded(state, now, "project2_followups")
    if stage == "dsa":
        return commit_budget_exceeded(state, now, "dsa")
    if stage in ("time_complexity", "space_complexity"):
        return commit_budget_exceeded(state, now, "complexity")
    if stage == "cs_grilling":
        return commit_budget_exceeded(state, now, "cs_grilling")
    if stage == "hr":
        return commit_budget_exceeded(state, now, "hr")
    return False


def commit_advance_after_intro(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    state["stage"] = "project1"
    state["budget_started_at"]["project1_followups"] = now
    return state


def commit_advance_after_project1(state: Dict[str, Any]) -> Dict[str, Any]:
    state["stage"] = "project1_followups"
    return state


def commit_advance_after_project1_followup(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    """Same min/max-with-budget-gate pattern as core.py's advance_after_followup,
    applied to project 1 (STATED minimum 6, one more only if the budget allows)."""
    state["p1_followups_asked"] += 1
    n = state["p1_followups_asked"]
    if n < COMMIT_P1_FOLLOWUP_MIN:
        return state
    if (n == COMMIT_P1_FOLLOWUP_MIN and COMMIT_P1_FOLLOWUP_MAX > COMMIT_P1_FOLLOWUP_MIN
            and not commit_budget_exceeded(state, now, "project1_followups")):
        return state
    state["stage"] = "project2"
    state["budget_started_at"]["project2_followups"] = now
    return state


def commit_advance_after_project2(state: Dict[str, Any]) -> Dict[str, Any]:
    state["stage"] = "project2_followups"
    return state


def commit_advance_after_project2_followup(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    """Same pattern for project 2 (STATED minimum 5)."""
    state["p2_followups_asked"] += 1
    n = state["p2_followups_asked"]
    if n < COMMIT_P2_FOLLOWUP_MIN:
        return state
    if (n == COMMIT_P2_FOLLOWUP_MIN and COMMIT_P2_FOLLOWUP_MAX > COMMIT_P2_FOLLOWUP_MIN
            and not commit_budget_exceeded(state, now, "project2_followups")):
        return state
    state["stage"] = "dsa"
    state["budget_started_at"]["dsa"] = now
    return state


def commit_advance_after_dsa(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    state["stage"] = "time_complexity"
    state["budget_started_at"]["complexity"] = now
    return state


def commit_advance_after_time_complexity(state: Dict[str, Any]) -> Dict[str, Any]:
    state["stage"] = "space_complexity"
    return state


def commit_advance_after_space_complexity(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    state["stage"] = "cs_grilling"
    state["budget_started_at"]["cs_grilling"] = now
    return state


def commit_advance_cs_sub(state: Dict[str, Any], now: float, continue_question: bool,
                          continue_followup: bool) -> Dict[str, Any]:
    """Called after any CS-grilling turn (main question or a follow-up) is
    graded. `continue_followup`: move from main->followup1 or followup1->
    followup2 for the SAME question. `continue_question`: when the current
    question (main + whichever follow-ups) is done, move to the next
    question (True) or to hr (False, the caller already decided this from
    the cs_grilling budget)."""
    if continue_followup:
        state["cs_sub"] += 1
        return state
    state["cs_sub"] = 0
    if continue_question:
        state["cs_index"] += 1
        return state
    state["stage"] = "hr"
    state["budget_started_at"]["hr"] = now
    return state


def commit_cs_needs_nudge(state: Dict[str, Any], answer_word_count: int, remaining_seconds: float) -> bool:
    """Only on a question's MAIN turn (cs_sub == 0), same rule shape as
    core.py's dave_cs_needs_nudge (INTERPOLATED: not applied to follow-ups,
    since a follow-up is itself already a prompt for more detail)."""
    if state["cs_sub"] != 0:
        return False
    idx = state["cs_index"]
    if idx >= len(state["cs_nudge_used"]) or state["cs_nudge_used"][idx]:
        return False
    if remaining_seconds < CS_NUDGE_MIN_REMAINING_SECONDS:
        return False
    return answer_word_count < CS_NUDGE_WORD_THRESHOLD


def commit_mark_cs_nudged(state: Dict[str, Any]) -> Dict[str, Any]:
    state["cs_nudge_used"][state["cs_index"]] = True
    return state


# ---- CS-grilling question selection (oops/java/sql) -------------------------
def commit_cs_pick_first_two(oops_questions: List[Dict[str, Any]], java_questions: List[Dict[str, Any]],
                             rng: Optional[random.Random] = None) -> List[Dict[str, Any]]:
    """Q1 from oops and Q2 from java, order shuffled (STATED)."""
    r = rng or random
    pair = [r.choice(oops_questions), r.choice(java_questions)]
    r.shuffle(pair)
    return pair


def commit_cs_pick_weighted(by_topic: Dict[str, List[Dict[str, Any]]], exclude_ids: Any,
                            rng: Optional[random.Random] = None) -> Dict[str, Any]:
    """Q3/Q4 (STATED): a weighted-random topic draw (CS_TOPIC_WEIGHTS), never
    repeating a question already asked this interview. Same pattern as
    core.py's dave_cs_pick_weighted."""
    r = rng or random
    topics = list(CS_TOPIC_WEIGHTS.keys())
    weights = list(CS_TOPIC_WEIGHTS.values())
    exclude_ids = set(exclude_ids or ())
    for _ in range(50):
        topic = r.choices(topics, weights=weights, k=1)[0]
        pool = [q for q in by_topic[topic] if q["id"] not in exclude_ids]
        if pool:
            return r.choice(pool)
    all_pool = [q for qs in by_topic.values() for q in qs if q["id"] not in exclude_ids]
    return r.choice(all_pool)


# ---- HR (reuses core.py's Dave HR selection unchanged; own budget state) ---
def commit_advance_after_hr(state: Dict[str, Any], continue_to_next: bool) -> Dict[str, Any]:
    """Same pattern as core.py's dave_advance_after_hr. HR is Commit's last
    stage too."""
    state["hr_index"] += 1
    if not continue_to_next:
        state["stage"] = "done"
        state["status"] = "completed"
    return state


def commit_hr_needs_nudge(state: Dict[str, Any], answer_word_count: int, remaining_seconds: float,
                          word_threshold: int, min_remaining_seconds: float) -> bool:
    idx = state["hr_index"]
    if idx >= len(state["hr_nudge_used"]) or state["hr_nudge_used"][idx]:
        return False
    if remaining_seconds < min_remaining_seconds:
        return False
    return answer_word_count < word_threshold


def commit_mark_hr_nudged(state: Dict[str, Any]) -> Dict[str, Any]:
    state["hr_nudge_used"][state["hr_index"]] = True
    return state


# ---- Scoring (INTERPOLATED merge pattern, mirrors dave_dsa_complexity_score) -
def commit_dsa_complexity_score(dsa_flags: Optional[Dict[str, bool]], efficiency_followup_flags: Optional[Dict[str, bool]],
                                time_flags: Optional[Dict[str, bool]], space_flags: Optional[Dict[str, bool]]) -> Optional[float]:
    """One combined score over the DSA approach/edge-case flags (with the
    efficiency flag OR'd against the optional nudge follow-up's result),
    plus both complexity dimensions. None if DSA was never reached."""
    if dsa_flags is None:
        return None
    combined = dict(dsa_flags)
    if efficiency_followup_flags and efficiency_followup_flags.get("approach_1"):
        combined["approach_1"] = True
    if time_flags:
        combined.update({f"time_{k}": v for k, v in time_flags.items()})
    if space_flags:
        combined.update({f"space_{k}": v for k, v in space_flags.items()})
    return core.flags_score(combined)


def commit_cs_question_pooled_flags(turn_flags_for_question: List[Dict[str, bool]]) -> Dict[str, bool]:
    """Pools the main question's key-point flags with whichever follow-ups
    were actually asked (prefixed by sub-turn index to avoid key collisions)
    into ONE flags dict for the question (STATED: "fraction of key points
    present across the main question and the follow-ups actually asked").
    Feed the list of these dicts (one per question) into
    core.project_followups_score to get the overall cs_grilling score --
    same "mean of each item's own flags_score" pattern core.py already uses
    for project/follow-up turns, just applied to a pooled per-question dict
    instead of a single raw turn's flags."""
    combined: Dict[str, bool] = {}
    for sub_idx, flags in enumerate(turn_flags_for_question):
        combined.update({f"t{sub_idx}_{k}": v for k, v in flags.items()})
    return combined


def commit_interview_score(p1: Optional[float], p2: Optional[float], dsa_complexity: Optional[float],
                           cs_grilling: Optional[float], hr: Optional[float]) -> Dict[str, Any]:
    """0.18 project1 + 0.18 project2 + 0.24 dsa+complexity + 0.28 cs_grilling
    + 0.12 hr (STATED weights). An unreached stage counts as 0 and is named
    in not_reached. Report-only: no pass or fail."""
    not_reached = []
    if p1 is None:
        not_reached.append("project1")
    if p2 is None:
        not_reached.append("project2")
    if dsa_complexity is None:
        not_reached.append("dsa_complexity")
    if cs_grilling is None:
        not_reached.append("cs_grilling")
    if hr is None:
        not_reached.append("hr")
    w = COMMIT_WEIGHTS
    total = (w["project1"] * (p1 or 0.0) + w["project2"] * (p2 or 0.0)
            + w["dsa_complexity"] * (dsa_complexity or 0.0) + w["cs_grilling"] * (cs_grilling or 0.0)
            + w["hr"] * (hr or 0.0))
    return {"project1": p1, "project2": p2, "dsa_complexity": dsa_complexity,
            "cs_grilling": cs_grilling, "hr": hr, "interview": round(total, 4), "not_reached": not_reached}


# ---- Client projection (whitelist) ------------------------------------------
def _pill_stage(stage: str) -> str:
    """project1_followups -> project1, project2_followups -> project2, else
    unchanged -- maps an internal stage to the pill it should highlight."""
    if stage == "project1_followups":
        return "project1"
    if stage == "project2_followups":
        return "project2"
    return stage


def commit_client_view(doc: Dict[str, Any], now: float) -> Dict[str, Any]:
    """Same whitelist philosophy as core.py's client_view/dave_client_view:
    no flags, scores, projects, rubrics, reference solutions, tests, CS/HR
    question banks or any feedback reach the browser during or after the
    interview."""
    state = doc["state"]
    finished = state["status"] != "in_progress"
    view: Dict[str, Any] = {
        "interview_id": doc["interview_id"],
        "attempt_id": doc.get("attempt_id"),
        "mode": "commit",
        "company_name": doc.get("company_name"),
        "status": state["status"],
        "stage": _pill_stage(state["stage"]),
        "stage_label": COMMIT_STAGE_LABELS[state["stage"]],
        "stages": [{"stage": s, "label": COMMIT_STAGE_LABELS[s]} for s in COMMIT_PILL_STAGES],
        "deadline_epoch": state["deadline_at"],
        "server_now_epoch": now,
        "turns": [{"stage": t["stage"], "question": t["question"], "answer": t["answer"]}
                  for t in doc.get("turns", [])],
        "current_question": None,
        "closing_message": core.closing_message(doc.get("candidate_name")) if finished else None,
    }
    if not finished and doc.get("current_question"):
        q = doc["current_question"]
        view["current_question"] = {"id": q["id"], "stage": _pill_stage(q["stage"]), "prompt": q["prompt"]}
    return view
