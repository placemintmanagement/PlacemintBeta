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
    "dave": dict(_EMPTY_TIER),
    "commit": dict(_EMPTY_TIER),
}

STAGE_LABELS = {
    "intro": "Introduction",
    "project": "Project",
    "followups": "Project follow-ups",
    "dsa": "Coding question",
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


def tier_entry(tier: Optional[str]) -> Optional[Dict[str, Any]]:
    return TIER_TABLE.get(tier) if tier else None


def is_spark(tier: Optional[str]) -> bool:
    """True only for a designed Spark tier. dave, commit, None and unknown
    tiers are False and keep the generic interview."""
    entry = tier_entry(tier)
    return bool(entry and entry["status"] == "designed" and tier == "spark")


# ---- Question text (code-owned; never model-written) ----------------------
INTRO_QUESTION = "Please introduce yourself in a few sentences: your background and what you are working on now."
NO_PROJECT_QUESTION = (
    "There is no project on your resume that I can ask about. Tell me about an academic or practice "
    "project you worked on: what it did, and which parts you built yourself."
)
COMPLEXITY_QUESTION = "What are the time and space complexity of your approach?"


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
    unreached (see the stored turns)."""
    state["stage"] = "done"
    state["status"] = "timed_out"
    state["timed_out"] = True
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
