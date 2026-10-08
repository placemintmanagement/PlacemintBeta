# -*- coding: utf-8 -*-
"""Capgemini interview: the single home for Capgemini interview information.

Tags on every constant:
  STATED       -- from the repo owner's written spec.
  INTERPOLATED -- my choice to fill a gap in the spec; pending the owner's review.
  CONFIRMED    -- verified by the owner (none yet for the Spark flow).

Only the Spark tier has a designed flow. Dave and Commit are "not_designed":
their entries are empty and they keep the generic interview. Any tier that is
not "designed", and every non-Capgemini company, keeps the generic interview.

This module is pure: no imports from server.py, no database, no clock, no LLM.
server.py calls these functions and ai_service.py builds the prompts.
"""
import os
import random
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from services.ai_service import GPT_MINI
from .capgemini_interview_dsa import SPARK_DSA_PROBLEMS
from .capgemini_interview_dsa_dave import DAVE_DSA_PROBLEMS
from .capgemini_interview_hr import select_hr_first_two, select_hr_third, question_text as hr_question_text
from .capgemini_interview_cs import (
    OOPS_QUESTIONS as CS_OOPS_QUESTIONS,
    SQL_QUESTIONS as CS_SQL_QUESTIONS,
    OS_QUESTIONS as CS_OS_QUESTIONS,
    BY_TOPIC as CS_BY_TOPIC,
    CS_TOPIC_WEIGHTS,
)

# ---- Tier table -----------------------------------------------------------
_EMPTY_TIER = {
    "status": "not_designed",
    "duration_seconds": None,
    "stages": [],
    "budgets_seconds": {},
    "followups": {},
    "signals": {},
    "weights": {},
    "comment": "Flow pending the repo owner's input. Keeps the generic interview until designed.",
}

SPARK_DURATION_SECONDS = 35 * 60                       # STATED: 35-minute interview
SPARK_STAGES = ["intro", "project", "followups", "dsa"]  # STATED: order, advanced only by code

# Soft stage budgets (INTERPOLATED). Project and follow-ups share one budget.
# Budgets never end the interview early on their own: they trigger a wrap-up
# instruction and, for follow-ups, the sixth-question decision. The 35-minute
# deadline is the only hard stop.
SPARK_BUDGETS_SECONDS = {
    "intro": 3 * 60,        # INTERPOLATED
    "project_followups": 15 * 60,  # INTERPOLATED
    "dsa": 12 * 60,         # INTERPOLATED
    "buffer": 5 * 60,       # INTERPOLATED (intro + pf + dsa + buffer = 35 min)
}
FOLLOWUP_MIN = 5            # STATED: five follow-ups minimum
FOLLOWUP_MAX = 6            # STATED: a sixth only when the time budget allows (rule is INTERPOLATED)
DSA_COMPLEXITY_PROMPTS = 1  # STATED: one prompt for complexity when it is not stated

# Scoring (INTERPOLATED). Report-only: there is no pass or fail for Spark.
SPARK_WEIGHTS = {"project_followups": 0.6, "dsa": 0.4}

# Signal definitions for element-flag grading (INTERPOLATED).
PROJECT_SIGNALS = ("concrete_detail", "own_contribution", "tech_choice_reason", "tradeoff_or_challenge")
DSA_EXTRA_SIGNALS = ("edge_cases_named", "complexity_stated")

# Model choice (STATED: GPT_MINI in one place, switchable here). Question writing
# uses 0.7 (INTERPOLATED; a live probe accepted it). Grading is always 0 (STATED).
INTERVIEW_MODEL = GPT_MINI
WRITER_TEMPERATURE = 0.7  # INTERPOLATED
GRADING_TEMPERATURE = 0   # STATED

# Used only when the follow-up writer call fails or returns no question (INTERPOLATED).
FALLBACK_FOLLOWUP = "Which decision in that part of the project would you change now, and why?"

# ---- Dave tier (text, 55 minutes) ------------------------------------------
DAVE_DURATION_SECONDS = 55 * 60                                           # STATED
DAVE_STAGES = ["intro", "project1", "followups", "project2", "dsa",      # STATED: order, advanced only by code
              "time_complexity", "space_complexity", "cs_fundamentals", "hr"]

# Soft stage budgets (STATED values). project1+followups share one budget
# (same pattern as Spark). The 55-minute deadline is the only hard stop.
DAVE_BUDGETS_SECONDS = {
    "intro": 3 * 60,              # STATED
    "project1_followups": 14 * 60,  # STATED
    "project2": 6 * 60,           # STATED
    "dsa": 8 * 60,                # STATED
    "complexity": 4 * 60,         # STATED (shared by time_complexity + space_complexity)
    "cs_fundamentals": 10 * 60,   # STATED
    "hr": 5 * 60,                 # STATED
    "buffer": 5 * 60,             # STATED (3+14+6+8+4+10+5+5 = 55 min)
}

# Report-only weights (STATED, named constants). No pass or fail for Dave.
DAVE_WEIGHTS = {"project1_followups": 0.30, "project2": 0.10, "dsa_complexity": 0.25,
                "cs_fundamentals": 0.20, "hr": 0.15}

# Signal definitions (INTERPOLATED, as given).
PROJECT2_SIGNALS = ("own_contribution", "challenge_described")
DAVE_COMPLEXITY_SIGNALS = ("time_stated", "time_correct", "space_stated", "space_correct")
HR_SIGNALS = ("direct_answer", "concrete_example_or_reason", "reflection_or_outcome")

HR_NUDGE_WORD_THRESHOLD = 25                # INTERPOLATED (STATED: "start at 25")
HR_NUDGE_MIN_REMAINING_SECONDS = 2 * 60     # STATED: none if remaining time is under 2 minutes
HR_NUDGE_TEXT = "Could you give me a specific example or a bit more detail?"  # STATED fixed template

CS_NUDGE_WORD_THRESHOLD = 15                 # INTERPOLATED (STATED: "start at 15")
CS_NUDGE_MIN_REMAINING_SECONDS = 2 * 60      # STATED: none if remaining time is under 2 minutes, same rule as HR
CS_NUDGE_TEXT = "Could you explain that a bit more, or give an example?"  # STATED fixed template

TIER_TABLE: Dict[str, Dict[str, Any]] = {
    "spark": {
        "status": "designed",
        "duration_seconds": SPARK_DURATION_SECONDS,
        "stages": list(SPARK_STAGES),
        "budgets_seconds": dict(SPARK_BUDGETS_SECONDS),
        "followups": {"min": FOLLOWUP_MIN, "max": FOLLOWUP_MAX},
        "signals": {"project": list(PROJECT_SIGNALS), "dsa": list(DSA_EXTRA_SIGNALS) + ["approach elements from the rubric"]},
        "weights": dict(SPARK_WEIGHTS),
        "comment": "Designed: text interview, 35 minutes, server-enforced deadline.",
    },
    "dave": {
        "status": "designed",
        "duration_seconds": DAVE_DURATION_SECONDS,
        "stages": list(DAVE_STAGES) + ["done"],
        "budgets_seconds": dict(DAVE_BUDGETS_SECONDS),
        "followups": {"min": FOLLOWUP_MIN, "max": FOLLOWUP_MAX},
        "signals": {"project1": list(PROJECT_SIGNALS), "project2": list(PROJECT2_SIGNALS),
                    "dsa": ["approach elements from the rubric", "edge cases named"],
                    "complexity": list(DAVE_COMPLEXITY_SIGNALS),
                    "cs_fundamentals": ["key points from the fixed oops/sql/os question bank"],
                    "hr": list(HR_SIGNALS)},
        "weights": dict(DAVE_WEIGHTS),
        "comment": "Designed: text interview, 55 minutes, server-enforced deadline.",
    },
    "commit": dict(_EMPTY_TIER),
}

STAGE_LABELS = {
    "intro": "Introduction",
    "project": "Project",
    "project1": "Project 1",
    "followups": "Project follow-ups",
    "project2": "Project 2",
    "dsa": "Coding question",
    "time_complexity": "Time complexity",
    "space_complexity": "Space complexity",
    "cs_fundamentals": "CS fundamentals",
    "hr": "HR questions",
    "done": "Done",
}


def spark_duration_seconds(env: Optional[Dict[str, str]] = None) -> int:
    """35 minutes in production. A test-only override is honoured only when
    ENVIRONMENT=test, so a real deployment cannot shorten the interview."""
    env = os.environ if env is None else env
    raw = env.get("SPARK_INTERVIEW_TEST_DURATION_SECONDS")
    if env.get("ENVIRONMENT") == "test" and raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return SPARK_DURATION_SECONDS


def dave_duration_seconds(env: Optional[Dict[str, str]] = None) -> int:
    """55 minutes in production. A test-only override is honoured only when
    ENVIRONMENT=test, so a real deployment cannot shorten the interview."""
    env = os.environ if env is None else env
    raw = env.get("DAVE_INTERVIEW_TEST_DURATION_SECONDS")
    if env.get("ENVIRONMENT") == "test" and raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DAVE_DURATION_SECONDS


def tier_entry(tier: Optional[str]) -> Optional[Dict[str, Any]]:
    return TIER_TABLE.get(tier) if tier else None


def is_spark(tier: Optional[str]) -> bool:
    """True only for a designed Spark tier. dave, commit, None and unknown
    tiers are False and keep the generic interview."""
    entry = tier_entry(tier)
    return bool(entry and entry["status"] == "designed" and tier == "spark")


def is_dave(tier: Optional[str]) -> bool:
    """True only for a designed Dave tier. spark, commit, None and unknown
    tiers are False and keep their own flow (or the generic interview)."""
    entry = tier_entry(tier)
    return bool(entry and entry["status"] == "designed" and tier == "dave")


# ---- Question text (code-owned; never model-written) ----------------------
INTRO_QUESTION = "Please introduce yourself in a few sentences: your background and what you are working on now."
NO_PROJECT_QUESTION = (
    "There is no project on your resume that I can ask about. Tell me about an academic or practice "
    "project you worked on: what it did, and which parts you built yourself."
)
COMPLEXITY_QUESTION = "What are the time and space complexity of your approach?"
DAVE_TIME_COMPLEXITY_QUESTION = "What is the time complexity of your solution?"      # STATED fixed template
DAVE_SPACE_COMPLEXITY_QUESTION = "What is the space complexity?"                     # STATED fixed template
DAVE_PROJECT2_INTRO_FOCUS = "Ask the candidate for a brief overview of what this project does."  # INTERPOLATED
DAVE_PROJECT2_ROLE_FOCUS = (
    "Ask specifically what the candidate's own role or contribution was on this project -- what they "
    "personally built, owned or was responsible for."
)  # INTERPOLATED
DAVE_PROJECT2_CHALLENGE_FOCUS = (
    "Ask specifically about a challenge, problem or difficulty the candidate faced while working on this "
    "project, and how they handled it."
)  # INTERPOLATED
DAVE_PROJECT2_THIN_ROLE_FOCUS = (
    "The candidate's answer about their own role on this project was vague or team-level rather than "
    "personal and specific. Ask a more specific follow-up that presses for what they personally built, "
    "owned or were responsible for."
)  # INTERPOLATED
DAVE_PROJECT2_THIN_CHALLENGE_FOCUS = (
    "The candidate's answer about a challenge on this project was vague or did not say what they actually "
    "did about it. Ask a more specific follow-up that presses for a concrete problem and what they did."
)  # INTERPOLATED


def _clean_label(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def pick_project(projects: List[Dict[str, Any]], rng: Optional[random.Random] = None) -> Optional[Dict[str, Any]]:
    """Pick one parsed resume project uniformly at random (STATED). Entries
    without a usable name are ignored."""
    usable = [p for p in (projects or []) if isinstance(p, dict) and _clean_label(p.get("name"))]
    if not usable:
        return None
    return (rng or random).choice(usable)


def project_question(project: Optional[Dict[str, Any]]) -> str:
    if not project:
        return NO_PROJECT_QUESTION
    return (f"Your resume lists the project \"{_clean_label(project.get('name'))}\". Walk me through what it does "
            "and which parts you built yourself.")


def project_text(project: Optional[Dict[str, Any]]) -> str:
    """Text the follow-up writer sees (candidate-controlled; wrapped by the caller)."""
    if not project:
        return "No resume project. The candidate was asked about an academic or practice project."
    return "\n".join([
        f"Name: {_clean_label(project.get('name'))}",
        f"Tech: {_clean_label(project.get('tech_stack'), 200)}",
        f"Summary: {_clean_label(project.get('one_line_summary'), 400)}",
    ])


def dsa_problem_ids() -> List[str]:
    return [p["id"] for p in SPARK_DSA_PROBLEMS]


def get_dsa_problem(problem_id: str) -> Optional[Dict[str, Any]]:
    return next((p for p in SPARK_DSA_PROBLEMS if p["id"] == problem_id), None)


def pick_dsa_problem(rng: Optional[random.Random] = None) -> Dict[str, Any]:
    return (rng or random).choice(SPARK_DSA_PROBLEMS)


# ---- Dave: two different projects, a second-project fallback --------------
DAVE_NO_PROJECT2_QUESTION = (
    "Tell me about another project, internship, course project, hackathon or other hands-on work you've "
    "done: what it did, and what your role was."
)


def dave_pick_two_projects(projects: List[Dict[str, Any]],
                           rng: Optional[random.Random] = None) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Two DIFFERENT parsed resume projects, picked uniformly at random
    without replacement (STATED). Fewer than two usable projects: whichever
    exist go to project 1 first; project 2 is None (the caller uses the
    fixed fallback question)."""
    usable = [p for p in (projects or []) if isinstance(p, dict) and _clean_label(p.get("name"))]
    r = rng or random
    if len(usable) >= 2:
        a, b = r.sample(usable, 2)
        return a, b
    if len(usable) == 1:
        return usable[0], None
    return None, None


def dave_project2_question(project: Optional[Dict[str, Any]]) -> str:
    if not project:
        return DAVE_NO_PROJECT2_QUESTION
    return (f"Let's talk about another project on your resume: \"{_clean_label(project.get('name'))}\". "
            "Give me a brief overview of what it does.")


# ---- Dave: Medium DSA problems ---------------------------------------------
def dave_dsa_problem_ids() -> List[str]:
    return [p["id"] for p in DAVE_DSA_PROBLEMS]


def get_dave_dsa_problem(problem_id: str) -> Optional[Dict[str, Any]]:
    return next((p for p in DAVE_DSA_PROBLEMS if p["id"] == problem_id), None)


def pick_dave_dsa_problem(rng: Optional[random.Random] = None) -> Dict[str, Any]:
    return (rng or random).choice(DAVE_DSA_PROBLEMS)


# ---- Dave: HR question selection (2-3 questions) ---------------------------
def dave_pick_hr_first_two(rng: Optional[random.Random] = None) -> Tuple[List[Dict[str, Any]], str]:
    """Q1 is always Motivation; Q2 is Teamwork or Strengths, chosen at random
    (STATED). Returns (questions, second_category) -- second_category is kept
    so a later, budget-gated third draw knows which categories are still
    unused."""
    return select_hr_first_two(rng)


def dave_pick_hr_third(second_category: str, first_two: List[Dict[str, Any]],
                       rng: Optional[random.Random] = None) -> Dict[str, Any]:
    """The optional third HR question (STATED): from the remaining categories
    (the other of Teamwork/Strengths, Career, Flexibility, Situational),
    never repeating a category already used, never drawing both mistake
    questions in one interview."""
    return select_hr_third(second_category, first_two, rng)


# ---- Dave: CS-fundamentals question selection (oops/sql/os) ----------------
def dave_cs_pick_first_two(rng: Optional[random.Random] = None) -> List[Dict[str, Any]]:
    """Q1 from oops and Q2 from sql, with the order shuffled (STATED)."""
    r = rng or random
    pair = [r.choice(CS_OOPS_QUESTIONS), r.choice(CS_SQL_QUESTIONS)]
    r.shuffle(pair)
    return pair


def dave_cs_pick_weighted(exclude_ids: Any, rng: Optional[random.Random] = None) -> Dict[str, Any]:
    """Q3/Q4 (STATED): a weighted-random topic draw (CS_TOPIC_WEIGHTS), never
    repeating a question already asked this interview."""
    r = rng or random
    topics = list(CS_TOPIC_WEIGHTS.keys())
    weights = list(CS_TOPIC_WEIGHTS.values())
    exclude_ids = set(exclude_ids or ())
    for _ in range(50):
        topic = r.choices(topics, weights=weights, k=1)[0]
        pool = [q for q in CS_BY_TOPIC[topic] if q["id"] not in exclude_ids]
        if pool:
            return r.choice(pool)
    all_pool = [q for qs in CS_BY_TOPIC.values() for q in qs if q["id"] not in exclude_ids]
    return r.choice(all_pool)


def get_cs_question(question_id: str) -> Optional[Dict[str, Any]]:
    for qs in CS_BY_TOPIC.values():
        for q in qs:
            if q["id"] == question_id:
                return q
    return None


def cs_question_ids() -> List[str]:
    return [q["id"] for qs in CS_BY_TOPIC.values() for q in qs]


def dsa_question(problem: Dict[str, Any]) -> str:
    return (f"Coding question: {problem['title']}\n\n{problem['statement']}\n\n"
            f"Input: {problem['input_format']}\nOutput: {problem['output_format']}\n"
            f"Constraints: {problem['constraints']}\n\n"
            "You may answer with the algorithm or with full code.")


# ---- Stage machine (pure; advanced only by code) --------------------------
def new_state(now: float, duration_seconds: int) -> Dict[str, Any]:
    return {
        "stage": "intro",
        "status": "in_progress",
        "timed_out": False,
        "started_at": now,
        "deadline_at": now + duration_seconds,
        "budget_started_at": {"intro": now},
        "followups_asked": 0,
        "dsa_turns": 0,
    }


def is_expired(state: Dict[str, Any], now: float) -> bool:
    return now >= state["deadline_at"]


def budget_exceeded(state: Dict[str, Any], now: float, budget_key: str) -> bool:
    started = state["budget_started_at"].get(budget_key)
    if started is None:
        return False
    return now - started >= SPARK_BUDGETS_SECONDS[budget_key]


def wrap_up_now(state: Dict[str, Any], now: float) -> bool:
    """True when the current stage has run past its soft budget. The next
    question is then told to wrap up."""
    if state["stage"] == "intro":
        return budget_exceeded(state, now, "intro")
    if state["stage"] in ("project", "followups"):
        return budget_exceeded(state, now, "project_followups")
    if state["stage"] == "dsa":
        return budget_exceeded(state, now, "dsa")
    return False


def advance_after_intro(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    state["stage"] = "project"
    state["budget_started_at"]["project_followups"] = now
    return state


def advance_after_project(state: Dict[str, Any]) -> Dict[str, Any]:
    state["stage"] = "followups"
    return state


def advance_after_followup(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    """Called after a follow-up is answered. Counts it, then decides: one more
    follow-up, or the DSA stage. Five is the minimum. A sixth only while the
    project-and-follow-up budget is not yet spent (INTERPOLATED rule)."""
    state["followups_asked"] += 1
    n = state["followups_asked"]
    if n < FOLLOWUP_MIN:
        return state
    if n == FOLLOWUP_MIN and FOLLOWUP_MAX > FOLLOWUP_MIN and not budget_exceeded(state, now, "project_followups"):
        return state
    state["stage"] = "dsa"
    state["budget_started_at"]["dsa"] = now
    return state


def advance_after_dsa_turn(state: Dict[str, Any], complexity_stated: bool) -> Dict[str, Any]:
    """Called after a DSA answer. One complexity prompt if the answer did not
    state complexity (STATED); otherwise the interview is complete."""
    state["dsa_turns"] += 1
    if not complexity_stated and state["dsa_turns"] <= DSA_COMPLEXITY_PROMPTS:
        return state
    state["stage"] = "done"
    state["status"] = "completed"
    return state


def finish_timed_out(state: Dict[str, Any]) -> Dict[str, Any]:
    """Deadline passed: no further answers. Stages not yet reached stay
    unreached (see the stored turns). Generic: used by both Spark and Dave."""
    state["stage"] = "done"
    state["status"] = "timed_out"
    state["timed_out"] = True
    return state


# ---- Dave stage machine (pure; advanced only by code; own functions so ----
# ---- nothing here can change Spark's behaviour) ----------------------------
def dave_new_state(now: float, duration_seconds: int) -> Dict[str, Any]:
    return {
        "stage": "intro",
        "status": "in_progress",
        "timed_out": False,
        "started_at": now,
        "deadline_at": now + duration_seconds,
        "budget_started_at": {"intro": now},
        "followups_asked": 0,
        "project2_turns": 0,
        "project2_optional_asked": False,
        "dsa_turns": 0,
        "cs_index": 0,
        "cs_nudge_used": [False, False, False, False],
        "hr_index": 0,
        "hr_nudge_used": [False, False, False],
        "hr_second_category": None,
    }


def dave_budget_exceeded(state: Dict[str, Any], now: float, budget_key: str) -> bool:
    started = state["budget_started_at"].get(budget_key)
    if started is None:
        return False
    return now - started >= DAVE_BUDGETS_SECONDS[budget_key]


def dave_wrap_up_now(state: Dict[str, Any], now: float) -> bool:
    stage = state["stage"]
    if stage == "intro":
        return dave_budget_exceeded(state, now, "intro")
    if stage in ("project1", "followups"):
        return dave_budget_exceeded(state, now, "project1_followups")
    if stage == "project2":
        return dave_budget_exceeded(state, now, "project2")
    if stage == "dsa":
        return dave_budget_exceeded(state, now, "dsa")
    if stage in ("time_complexity", "space_complexity"):
        return dave_budget_exceeded(state, now, "complexity")
    if stage == "cs_fundamentals":
        return dave_budget_exceeded(state, now, "cs_fundamentals")
    if stage == "hr":
        return dave_budget_exceeded(state, now, "hr")
    return False


def dave_advance_after_intro(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    state["stage"] = "project1"
    state["budget_started_at"]["project1_followups"] = now
    return state


def dave_advance_after_project1(state: Dict[str, Any]) -> Dict[str, Any]:
    state["stage"] = "followups"
    return state


def dave_advance_after_followup(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    """Same rule as Spark's advance_after_followup (STATED: 'Project 1: as
    Spark'): five follow-ups minimum, a sixth only while the project1+
    follow-ups budget is not yet spent. Then moves to project2, not dsa."""
    state["followups_asked"] += 1
    n = state["followups_asked"]
    if n < FOLLOWUP_MIN:
        return state
    if n == FOLLOWUP_MIN and FOLLOWUP_MAX > FOLLOWUP_MIN and not dave_budget_exceeded(state, now, "project1_followups"):
        return state
    state["stage"] = "project2"
    state["budget_started_at"]["project2"] = now
    return state


def dave_advance_after_project2_overview(state: Dict[str, Any]) -> Dict[str, Any]:
    """After project2's brief-overview answer: stage stays project2; the
    caller asks the role question next."""
    return state


def dave_advance_after_project2_role(state: Dict[str, Any]) -> Dict[str, Any]:
    """After the role question (turn 1 of 2-3): stage stays project2; the
    caller asks the challenge question next."""
    state["project2_turns"] += 1
    return state


def dave_advance_after_project2_challenge(state: Dict[str, Any], now: float, ask_optional: bool) -> Dict[str, Any]:
    """After the challenge question (turn 2 of 2-3). `ask_optional` is
    pre-computed by the caller from the role/challenge flags and the
    remaining project2 budget (STATED: an optional third question on
    whichever was thin, while budget allows)."""
    state["project2_turns"] += 1
    if ask_optional:
        state["project2_optional_asked"] = True
        return state
    state["stage"] = "dsa"
    state["budget_started_at"]["dsa"] = now
    return state


def dave_advance_after_project2_optional(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    """After the optional third project2 question (turn 3 of 3, only when asked)."""
    state["project2_turns"] += 1
    state["stage"] = "dsa"
    state["budget_started_at"]["dsa"] = now
    return state


def dave_advance_after_dsa(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    state["dsa_turns"] += 1
    state["stage"] = "time_complexity"
    state["budget_started_at"]["complexity"] = now
    return state


def dave_advance_after_time_complexity(state: Dict[str, Any]) -> Dict[str, Any]:
    """STATED: the space-complexity question is always asked too, even if
    already mentioned in the DSA or time-complexity answer."""
    state["stage"] = "space_complexity"
    return state


def dave_advance_after_space_complexity(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    state["stage"] = "cs_fundamentals"
    state["budget_started_at"]["cs_fundamentals"] = now
    return state


def dave_advance_after_cs(state: Dict[str, Any], now: float, continue_to_next: bool) -> Dict[str, Any]:
    """Called after any of the (up to four) CS-fundamentals questions is
    graded. Q1->Q2 and Q2->Q3 always continue (STATED); Q3->Q4 continues only
    if the cs_fundamentals budget is not spent (the caller computes
    `continue_to_next` from that budget check); Q4, if asked, never
    continues. When this is the last question, moves on to hr."""
    state["cs_index"] += 1
    if not continue_to_next:
        state["stage"] = "hr"
        state["budget_started_at"]["hr"] = now
    return state


def dave_cs_needs_nudge(state: Dict[str, Any], answer_word_count: int, remaining_seconds: float) -> bool:
    """Same rule as dave_hr_needs_nudge, with CS's own word threshold
    (STATED: 15) and its own per-question nudge-used tracking."""
    idx = state["cs_index"]
    if idx >= len(state["cs_nudge_used"]) or state["cs_nudge_used"][idx]:
        return False
    if remaining_seconds < CS_NUDGE_MIN_REMAINING_SECONDS:
        return False
    return answer_word_count < CS_NUDGE_WORD_THRESHOLD


def dave_mark_cs_nudged(state: Dict[str, Any]) -> Dict[str, Any]:
    state["cs_nudge_used"][state["cs_index"]] = True
    return state


def dave_hr_needs_nudge(state: Dict[str, Any], answer_word_count: int, remaining_seconds: float) -> bool:
    """STATED: one fixed-template nudge per question, only if the answer is
    under the word threshold, none if the remaining time is under 2 minutes.
    Code decides, not the model."""
    idx = state["hr_index"]
    if idx >= len(state["hr_nudge_used"]) or state["hr_nudge_used"][idx]:
        return False
    if remaining_seconds < HR_NUDGE_MIN_REMAINING_SECONDS:
        return False
    return answer_word_count < HR_NUDGE_WORD_THRESHOLD


def dave_mark_hr_nudged(state: Dict[str, Any]) -> Dict[str, Any]:
    state["hr_nudge_used"][state["hr_index"]] = True
    return state


def dave_advance_after_hr(state: Dict[str, Any], continue_to_next: bool) -> Dict[str, Any]:
    """Called after each of the 2-3 HR questions is graded. Q1->Q2 always
    continues (STATED). Q2->Q3 continues only if the hr budget is not spent
    (the caller computes `continue_to_next` from that budget check); Q3, if
    asked, never continues. HR is Dave's last stage."""
    state["hr_index"] += 1
    if not continue_to_next:
        state["stage"] = "done"
        state["status"] = "completed"
    return state


# ---- Element flags (normalised; never trusted raw) ------------------------
# ---- Evidence-quote defence -------------------------------------------------
# Every grader flag arrives as {"present": bool, "quote": str}. A flag is true
# only if the grader claims it AND the quote is real evidence from the answer:
# long enough, copied from the answer (whitespace and case normalised), and not
# instruction-like text. Anything else is false and is returned as a rejection,
# so the server can log the answer for review.
QUOTE_MIN_CHARS = 12  # INTERPOLATED: shorter quotes are too thin to prove a signal
QUOTE_STRIP_CHARS = " \"'“”‘’.…"
INSTRUCTION_LIKE = ("ignore", "disregard", "mark all", "mark every", "score 100", "system:",
                    "you must", "as the grader", "grader:")  # INTERPOLATED list


def _normalise_text(text: Any) -> str:
    return " ".join(str(text or "").lower().split())


def quote_rejection(quote: Any, answer: str) -> Optional[str]:
    """None if the quote is acceptable evidence in this answer, else why not."""
    q = _normalise_text(quote).strip(QUOTE_STRIP_CHARS)
    if len(q) < QUOTE_MIN_CHARS:
        return "quote_too_short"
    if any(p in q for p in INSTRUCTION_LIKE):
        return "instruction_like_quote"
    if q not in _normalise_text(answer):
        return "quote_not_in_answer"
    return None


def _checked_flag(raw_flag: Any, answer: str, name: str, rejections: List[Dict[str, Any]]) -> bool:
    if not isinstance(raw_flag, dict) or raw_flag.get("present") is not True:
        return False
    reason = quote_rejection(raw_flag.get("quote"), answer)
    if reason:
        rejections.append({"flag": name, "reason": reason, "quote": str(raw_flag.get("quote") or "")[:300]})
        return False
    return True


def normalize_project_flags(raw: Any, answer: str) -> Tuple[Dict[str, bool], List[Dict[str, Any]]]:
    src = raw.get("flags") if isinstance(raw, dict) else None
    src = src if isinstance(src, dict) else {}
    rejections: List[Dict[str, Any]] = []
    flags = {k: _checked_flag(src.get(k), answer, k, rejections) for k in PROJECT_SIGNALS}
    return flags, rejections


def normalize_dsa_flags(raw: Any, approach_count: int, answer: str) -> Tuple[Dict[str, bool], List[Dict[str, Any]]]:
    src = raw if isinstance(raw, dict) else {}
    approach = src.get("approach_elements")
    approach = approach if isinstance(approach, list) else []
    rejections: List[Dict[str, Any]] = []
    flags = {}
    for i in range(approach_count):
        item = approach[i] if i < len(approach) else None
        flags[f"approach_{i}"] = _checked_flag(item, answer, f"approach_{i}", rejections)
    flags["edge_cases_named"] = _checked_flag(src.get("edge_cases_named"), answer, "edge_cases_named", rejections)
    flags["complexity_stated"] = _checked_flag(src.get("complexity_stated"), answer, "complexity_stated", rejections)
    return flags, rejections


def normalize_dave_dsa_flags(raw: Any, approach_count: int, answer: str) -> Tuple[Dict[str, bool], List[Dict[str, Any]]]:
    """Like normalize_dsa_flags, but without complexity_stated: Dave's DSA
    stage never judges complexity -- time_complexity/space_complexity are
    always asked afterward regardless (STATED)."""
    src = raw if isinstance(raw, dict) else {}
    approach = src.get("approach_elements")
    approach = approach if isinstance(approach, list) else []
    rejections: List[Dict[str, Any]] = []
    flags = {}
    for i in range(approach_count):
        item = approach[i] if i < len(approach) else None
        flags[f"approach_{i}"] = _checked_flag(item, answer, f"approach_{i}", rejections)
    flags["edge_cases_named"] = _checked_flag(src.get("edge_cases_named"), answer, "edge_cases_named", rejections)
    return flags, rejections


def normalize_project2_flags(raw: Any, answer: str) -> Tuple[Dict[str, bool], List[Dict[str, Any]]]:
    src = raw.get("flags") if isinstance(raw, dict) else None
    src = src if isinstance(src, dict) else {}
    rejections: List[Dict[str, Any]] = []
    flags = {k: _checked_flag(src.get(k), answer, k, rejections) for k in PROJECT2_SIGNALS}
    return flags, rejections


def normalize_dave_complexity_flags(raw: Any, dimension: str, answer: str) -> Tuple[Dict[str, bool], List[Dict[str, Any]]]:
    """dimension is 'time' or 'space'. 'Correct' is judged by the grading
    prompt against the approach the candidate actually described in their
    DSA answer (STATED); this just applies the evidence-quote defence to
    whatever the grader returned for that dimension."""
    src = raw if isinstance(raw, dict) else {}
    rejections: List[Dict[str, Any]] = []
    stated_key, correct_key = f"{dimension}_stated", f"{dimension}_correct"
    flags = {
        stated_key: _checked_flag(src.get(stated_key), answer, stated_key, rejections),
        correct_key: _checked_flag(src.get(correct_key), answer, correct_key, rejections),
    }
    return flags, rejections


def normalize_cs_flags(raw: Any, key_point_count: int, answer: str) -> Tuple[Dict[str, bool], List[Dict[str, Any]]]:
    """CS-fundamentals grader: one flag per key point (3-4, dynamic per
    question), same evidence-quote defence as every other grader here."""
    src = raw if isinstance(raw, dict) else {}
    points = src.get("key_points")
    points = points if isinstance(points, list) else []
    rejections: List[Dict[str, Any]] = []
    flags = {}
    for i in range(key_point_count):
        item = points[i] if i < len(points) else None
        flags[f"key_point_{i}"] = _checked_flag(item, answer, f"key_point_{i}", rejections)
    return flags, rejections


def normalize_hr_flags(raw: Any, answer: str) -> Tuple[Dict[str, bool], List[Dict[str, Any]]]:
    src = raw.get("flags") if isinstance(raw, dict) else None
    src = src if isinstance(src, dict) else {}
    rejections: List[Dict[str, Any]] = []
    flags = {k: _checked_flag(src.get(k), answer, k, rejections) for k in HR_SIGNALS}
    return flags, rejections


# ---- Scoring (INTERPOLATED, report-only) ----------------------------------
def flags_score(flags: Dict[str, bool]) -> float:
    if not flags:
        return 0.0
    return sum(1 for v in flags.values() if v) / len(flags)


def project_followups_score(turn_flags: List[Dict[str, bool]]) -> Optional[float]:
    """Mean of each project or follow-up answer's element-flag score. None if
    the candidate never reached these stages."""
    if not turn_flags:
        return None
    return sum(flags_score(f) for f in turn_flags) / len(turn_flags)


def dsa_score(dsa_flags: Optional[Dict[str, bool]]) -> Optional[float]:
    """Element-flag score over the approach elements, edge cases and complexity.
    None if the DSA stage was not reached."""
    if not dsa_flags:
        return None
    return flags_score(dsa_flags)


def interview_score(pf: Optional[float], dsa: Optional[float]) -> Dict[str, Any]:
    """0.6 project-and-follow-ups + 0.4 DSA. An unreached stage counts as 0
    and is named in not_reached. Report-only: no pass or fail."""
    not_reached = []
    if pf is None:
        not_reached.append("followups")
    if dsa is None:
        not_reached.append("dsa")
    weights = SPARK_WEIGHTS
    total = weights["project_followups"] * (pf or 0.0) + weights["dsa"] * (dsa or 0.0)
    return {"project_followups": pf, "dsa": dsa, "interview": round(total, 4), "not_reached": not_reached}


def dave_dsa_complexity_score(dsa_flags: Optional[Dict[str, bool]], time_flags: Optional[Dict[str, bool]],
                              space_flags: Optional[Dict[str, bool]]) -> Optional[float]:
    """One combined score over the DSA approach/edge-case flags plus both
    complexity dimensions (STATED weight: dsa+complexity 0.30 together).
    None if the DSA stage was never reached."""
    if dsa_flags is None:
        return None
    combined = dict(dsa_flags)
    if time_flags:
        combined.update({f"time_{k}": v for k, v in time_flags.items()})
    if space_flags:
        combined.update({f"space_{k}": v for k, v in space_flags.items()})
    return flags_score(combined)


def dave_interview_score(p1f: Optional[float], p2: Optional[float], dsa_complexity: Optional[float],
                         cs_fundamentals: Optional[float], hr: Optional[float]) -> Dict[str, Any]:
    """0.30 project1+followups + 0.10 project2 + 0.25 dsa+complexity + 0.20
    cs_fundamentals + 0.15 hr (STATED weights). An unreached stage counts as
    0 and is named in not_reached. Report-only: no pass or fail."""
    not_reached = []
    if p1f is None:
        not_reached.append("followups")
    if p2 is None:
        not_reached.append("project2")
    if dsa_complexity is None:
        not_reached.append("dsa_complexity")
    if cs_fundamentals is None:
        not_reached.append("cs_fundamentals")
    if hr is None:
        not_reached.append("hr")
    w = DAVE_WEIGHTS
    total = (w["project1_followups"] * (p1f or 0.0) + w["project2"] * (p2 or 0.0)
            + w["dsa_complexity"] * (dsa_complexity or 0.0) + w["cs_fundamentals"] * (cs_fundamentals or 0.0)
            + w["hr"] * (hr or 0.0))
    return {"project1_followups": p1f, "project2": p2, "dsa_complexity": dsa_complexity,
            "cs_fundamentals": cs_fundamentals, "hr": hr,
            "interview": round(total, 4), "not_reached": not_reached}


# ---- Client projection (whitelist) ----------------------------------------
CLIENT_DSA_FIELDS = ("id", "title", "statement", "input_format", "output_format", "constraints")

# ---- Closing message (fixed template, emitted by code, never by a model) ----
CLOSING_TEMPLATE = "Thank you, {name}, for attending the interview. We will update you soon."
CLOSING_FALLBACK = "Thank you for attending the interview. We will update you soon."
NAME_MAX_CHARS = 60  # INTERPOLATED: a sane length for the name in the closing message

# Characters that can start markup or markdown. Removed from names so the
# closing message is plain text whatever the account name contains.
_MARKUP_CHARS = set("<>`*_[]{}\\|")


def clean_display_name(raw: Any) -> Optional[str]:
    """Plain-text version of an account name for the closing message: control
    characters, markup and markdown characters removed, whitespace collapsed,
    truncated. Returns None when nothing usable is left."""
    if not isinstance(raw, str):
        return None
    kept = []
    for ch in raw:
        if ch in _MARKUP_CHARS:
            continue
        if unicodedata.category(ch).startswith("C"):
            kept.append(" ")
            continue
        kept.append(ch)
    text = " ".join("".join(kept).split())[:NAME_MAX_CHARS].strip()
    return text or None


# Account names that are placeholders, not a person's name (INTERPOLATED list).
PLACEHOLDER_NAMES = {"", "auth0 user", "user", "unknown", "anonymous", "guest", "test user",
                     "none", "null", "undefined", "n/a", "name"}


def usable_account_name(name: Any, email: Any = None) -> Optional[str]:
    """The account name if it can be shown to a candidate, else None.
    Rejected: anything containing "@" (an email address), placeholder names,
    and a name that is just the email's local part (the default the sign-in
    flow fills in when the provider sends no name)."""
    if not isinstance(name, str):
        return None
    text = " ".join(name.split())
    if not text or "@" in text or text.lower() in PLACEHOLDER_NAMES:
        return None
    if isinstance(email, str) and "@" in email and text.lower() == email.split("@", 1)[0].strip().lower():
        return None
    return text


def closing_message(raw_name: Any) -> str:
    name = clean_display_name(raw_name)
    return CLOSING_TEMPLATE.format(name=name) if name else CLOSING_FALLBACK


def client_view(doc: Dict[str, Any], now: float) -> Dict[str, Any]:
    """The only shape the browser receives for a Spark interview. Strips
    flags, scores, projects, rubrics, reference solutions, tests and every
    piece of feedback: during the interview the candidate sees only the
    countdown, stage progress and the conversation. After the interview the
    only text is the closing message."""
    state = doc["state"]
    finished = state["status"] != "in_progress"
    view: Dict[str, Any] = {
        "interview_id": doc["interview_id"],
        "attempt_id": doc.get("attempt_id"),
        "mode": "spark",
        "company_name": doc.get("company_name"),
        "status": state["status"],
        "stage": state["stage"],
        "stage_label": STAGE_LABELS[state["stage"]],
        "stages": [{"stage": s, "label": STAGE_LABELS[s]} for s in SPARK_STAGES],
        "deadline_epoch": state["deadline_at"],
        "server_now_epoch": now,
        "turns": [{"stage": t["stage"], "question": t["question"], "answer": t["answer"]}
                  for t in doc.get("turns", [])],
        "current_question": None,
        "closing_message": closing_message(doc.get("candidate_name")) if finished else None,
    }
    if not finished and doc.get("current_question"):
        q = doc["current_question"]
        view["current_question"] = {"id": q["id"], "stage": q["stage"], "prompt": q["prompt"]}
    return view


def dave_client_view(doc: Dict[str, Any], now: float) -> Dict[str, Any]:
    """Same whitelist philosophy as client_view, for the Dave tier: no flags,
    scores, projects, rubrics, reference solutions, tests, HR question bank
    or any feedback reach the browser during or after the interview."""
    state = doc["state"]
    finished = state["status"] != "in_progress"
    view: Dict[str, Any] = {
        "interview_id": doc["interview_id"],
        "attempt_id": doc.get("attempt_id"),
        "mode": "dave",
        "company_name": doc.get("company_name"),
        "status": state["status"],
        "stage": state["stage"],
        "stage_label": STAGE_LABELS[state["stage"]],
        "stages": [{"stage": s, "label": STAGE_LABELS[s]} for s in DAVE_STAGES],
        "deadline_epoch": state["deadline_at"],
        "server_now_epoch": now,
        "turns": [{"stage": t["stage"], "question": t["question"], "answer": t["answer"]}
                  for t in doc.get("turns", [])],
        "current_question": None,
        "closing_message": closing_message(doc.get("candidate_name")) if finished else None,
    }
    if not finished and doc.get("current_question"):
        q = doc["current_question"]
        view["current_question"] = {"id": q["id"], "stage": q["stage"], "prompt": q["prompt"]}
    return view
