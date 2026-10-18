# -*- coding: utf-8 -*-
"""TCS NQT interview: the single home for TCS interview information.

Built as a brand-new module beside the Capgemini interview package
(`capgemini/capgemini_interview/`), NOT as a refactor of it -- see the
design review this module came from (scratchpad `tcs_interview_spec.md`,
session of 2026-10). Reuse is deliberately narrow: the ONLY Capgemini-
package import anywhere in this file is `pick_project` (core.py's own
module-level docstring there confirms it is pure, generic, tier/company-
blind -- operates on plain {name, tech_stack, one_line_summary} dicts).
Everything else -- banks, prompts (ai_service.py, a shared/non-Capgemini
service module), scoring, the stage machine, the client-view projection --
is new code owned entirely by this package. Humanizer, pushback and DSA
hints are explicitly OUT OF SCOPE for v1 (product decision, not a technical
limitation) -- see the per-feature config tables in pushback.py/
dsa_hints.py, which live inside the Capgemini package itself and would
need an edit there to extend to TCS; v1 skips that trade entirely.

Three stages, kept separate: Technical (TR), Managerial (MR), HR. Tier
(ninja/digital/prime) changes question SELECTION and emphasis only --
never the stage list, durations or weights (explicit product decision).

Tags on every constant, same convention as capgemini_interview/core.py:
  OUR ESTIMATE -- this repo's own choice, no independent TCS source; every
                  one of the six headline numbers (three durations, three
                  stage weights) is tagged this way, per the product
                  owner's explicit instruction, because TCS publishes no
                  interview-structure timing or weighting data anywhere.

This module is pure: no imports from server.py, no database, no clock, no
LLM. server.py calls these functions; ai_service.py builds the grading
prompt.
"""
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview import (
    pick_project as _pick_project,
)
from .banks._kp import kp
from .banks.oop import OOP_QUESTIONS
from .banks.dbms_sql import DBMS_SQL_QUESTIONS
from .banks.os_bank import OS_QUESTIONS
from .banks.networking import NETWORKING_QUESTIONS
from .banks.coding_discussion import CODING_DISCUSSION_QUESTIONS
from .banks.managerial import MANAGERIAL_SITUATIONAL_QUESTIONS, GAP_EXPLANATION_QUESTIONS
from .banks.hr import (
    MOTIVATION_QUESTIONS, STRENGTHS_WEAKNESSES_QUESTIONS,
    COMPANY_KNOWLEDGE_QUESTIONS, LOGISTICS_QUESTIONS,
)

# ---- Tiers -----------------------------------------------------------------
# Real, already-live tier identifiers on the OA side (services/tcs_tiers.py:
# TIER_ORDER = ["prime", "digital", "ninja", NOT_QUALIFIED]) -- the interview
# reuses the SAME three names, never inventing its own.
TCS_INTERVIEW_TIERS: Tuple[str, ...] = ("ninja", "digital", "prime")
_TIER_RANK = {"ninja": 0, "digital": 1, "prime": 2}  # ascending difficulty


def is_ninja(tier: Optional[str]) -> bool:
    return tier == "ninja"


def is_digital(tier: Optional[str]) -> bool:
    return tier == "digital"


def is_prime(tier: Optional[str]) -> bool:
    return tier == "prime"


def is_tcs_interview_tier(tier: Optional[str]) -> bool:
    return tier in TCS_INTERVIEW_TIERS


# ---- The six mandated headline numbers (OUR ESTIMATE, all six) ------------
TCS_TECHNICAL_DURATION_SECONDS = 25 * 60  # OUR ESTIMATE
TCS_MANAGERIAL_DURATION_SECONDS = 10 * 60  # OUR ESTIMATE
TCS_HR_DURATION_SECONDS = 10 * 60  # OUR ESTIMATE

TCS_TECHNICAL_WEIGHT = 0.50  # OUR ESTIMATE
TCS_MANAGERIAL_WEIGHT = 0.25  # OUR ESTIMATE
TCS_HR_WEIGHT = 0.25  # OUR ESTIMATE

# Fixed, tier-independent total: tier changes question selection/emphasis
# only, never the duration (explicit product decision) -- so there is only
# ONE deadline, the sum of the three stage budgets, same for every tier.
TCS_DURATION_SECONDS = TCS_TECHNICAL_DURATION_SECONDS + TCS_MANAGERIAL_DURATION_SECONDS + TCS_HR_DURATION_SECONDS

TCS_STAGE_ORDER: List[str] = ["technical", "managerial", "hr"]
TCS_STAGE_BUDGETS_SECONDS = {
    "technical": TCS_TECHNICAL_DURATION_SECONDS,
    "managerial": TCS_MANAGERIAL_DURATION_SECONDS,
    "hr": TCS_HR_DURATION_SECONDS,
}
STAGE_LABELS = {"technical": "Technical", "managerial": "Managerial", "hr": "HR", "done": "Done"}

# ---- Within-stage dimension weights (OUR ESTIMATE; design choices beyond ---
# the six mandated numbers above, kept as named constants for the same
# reason). Each sums to 1.0 within its own stage.
TCS_TECHNICAL_DIMENSION_WEIGHTS = {  # OUR ESTIMATE
    "resume_language": 0.20,
    "oop": 0.15,
    "dbms_sql": 0.15,
    "os": 0.15,
    "networking": 0.10,
    "coding_discussion": 0.25,
}
TCS_MANAGERIAL_DIMENSION_WEIGHTS = {  # OUR ESTIMATE
    "situational": 0.40,
    "gap_explanation": 0.15,
    "technical_depth_followup": 0.30,
    "communication_clarity": 0.15,
}
TCS_HR_DIMENSION_WEIGHTS = {  # OUR ESTIMATE
    "motivation": 0.30,
    "strengths_weaknesses": 0.25,
    "company_knowledge": 0.20,
    "logistics": 0.25,
}

# ---- Per-tier question-selection depth (OUR ESTIMATE; emphasis only -- -----
# never changes the stage list, durations or weights above). Prime draws
# more/harder questions in the heavier topics; Ninja/Digital draw the bank's
# minimum per topic. HR's draw is fixed at 1 per category for every tier
# (one motivation + one strengths/weaknesses + one company-knowledge + one
# logistics question, always) -- HR wasn't part of the brief's tier-emphasis
# examples, so this module keeps it uniform rather than inventing a split.
TCS_TECHNICAL_TOPIC_COUNTS = {  # OUR ESTIMATE
    "ninja":   {"oop": 1, "dbms_sql": 1, "os": 1, "networking": 1, "coding_discussion": 1},
    "digital": {"oop": 1, "dbms_sql": 1, "os": 1, "networking": 1, "coding_discussion": 1},
    "prime":   {"oop": 2, "dbms_sql": 2, "os": 1, "networking": 1, "coding_discussion": 2},
}
TCS_MANAGERIAL_SITUATIONAL_COUNTS = {"ninja": 1, "digital": 2, "prime": 2}  # OUR ESTIMATE

# ---- Question text (code-owned; never model-written) -----------------------
NO_PROJECT_LANGUAGES_QUESTION = (
    "Which two programming languages would you like to be evaluated in during this interview, and why?"
)


def _clean(value: Any, limit: int = 120) -> str:
    return " ".join(str(value or "").split())[:limit]


_LANGUAGE_SPLIT_RE = re.compile(r"[,/;&]|\band\b", re.IGNORECASE)


def infer_top_languages(resume_projects: Optional[List[Dict[str, Any]]]) -> List[str]:
    """The candidate's most common tech_stack entries across every analyzed
    project (same `extracted_projects` resume data Capgemini's interview
    reads -- no new schema). Returns up to 2 distinct tokens, most frequent
    first, in their first-seen casing. An empty/short list means fewer than
    2 distinct languages could be inferred this way -- the caller then asks
    directly instead (see build_opener_question)."""
    from collections import Counter
    counts: "Counter[str]" = Counter()
    display: Dict[str, str] = {}
    for p in resume_projects or []:
        if not isinstance(p, dict):
            continue
        tech = str(p.get("tech_stack") or "")
        for piece in _LANGUAGE_SPLIT_RE.split(tech):
            piece = piece.strip(" .")
            if not piece:
                continue
            key = piece.lower()
            counts[key] += 1
            display.setdefault(key, piece)
    return [display[k] for k, _ in counts.most_common(2)]


def pick_project(resume_projects: Optional[List[Dict[str, Any]]],
                 rng: Optional[random.Random] = None) -> Optional[Dict[str, Any]]:
    """Reuses capgemini_interview.pick_project unchanged (confirmed generic:
    operates on plain {name, tech_stack, one_line_summary} dicts, no
    Capgemini-specific content) -- one random resume project, or None."""
    return _pick_project(resume_projects, rng)


def build_opener_question(resume_projects: Optional[List[Dict[str, Any]]],
                          project: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The Technical stage's FIRST question. Per the product decision: infer
    the candidate's two most-used languages from their resume's tech_stack
    entries; if fewer than 2 distinct languages can be inferred, the opener
    itself asks the candidate directly instead."""
    langs = infer_top_languages(resume_projects)
    if len(langs) >= 2:
        lang1, lang2 = langs[0], langs[1]
        project_name = _clean(project.get("name")) if project else ""
        if project_name:
            text = (
                f"Your resume shows you've worked with {lang1} and {lang2}, including on the project "
                f"\"{project_name}\". Tell me about that project, and why {lang1} and {lang2} were good "
                "fits for it."
            )
        else:
            text = (
                f"Your resume shows you've worked with {lang1} and {lang2}. Tell me about a project where "
                f"you used them, and why they were good fits for it."
            )
        key_points = [
            kp(f"clearly explains how or why {lang1} fit the project (not just naming it)"),
            kp(f"clearly explains how or why {lang2} fit the project (not just naming it)"),
            kp("gives a concrete project detail, not only a restatement of the languages"),
        ]
    else:
        text = NO_PROJECT_LANGUAGES_QUESTION
        key_points = [
            kp("names two specific programming languages"),
            kp("gives a real reason for choosing them (comfort, experience, project use), not just naming them"),
        ]
    return {"id": "tcs-opener", "topic": "resume_language", "text": text, "key_points": key_points}


def build_tech_depth_followup_question(project: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Managerial stage: a technical-depth follow-up framed from an
    ownership/management angle (not pure technical correctness), tied to
    the same resume project the Technical-stage opener used."""
    name = _clean(project.get("name")) if project else ""
    subject = f"\"{name}\"" if name else "a project you built"
    text = (
        f"Imagine you had to hand off {subject} to a new teammate under a tight deadline. What would you "
        "prioritize explaining to them first, and why?"
    )
    key_points = [
        kp("names a concrete priority rather than a generic answer"),
        kp("shows ownership-level understanding of the project, not just a surface description"),
        kp("explains the reasoning behind the priority chosen"),
    ]
    return {"id": "tcs-mgr-followup", "topic": "managerial_followup", "text": text, "key_points": key_points}


# ---- Question selection (SEED-content banks; see banks/*.py) --------------
def _draw(bank: List[Dict[str, Any]], n: int, tier: str, rng: random.Random) -> List[Dict[str, Any]]:
    """n questions, preferring items at or below this tier's difficulty rank
    (falling back to the whole bank if the preferred pool is too small),
    drawn without replacement. Returns fresh dict copies (never the bank's
    own stored dicts) so later per-question tagging (e.g. extra_signal)
    never mutates the shared bank."""
    if n <= 0:
        return []
    rank = _TIER_RANK.get(tier, 0)
    preferred = [q for q in bank if _TIER_RANK.get(q.get("difficulty"), 0) <= rank]
    pool = preferred if len(preferred) >= n else bank
    n = min(n, len(pool))
    return [dict(q) for q in rng.sample(pool, n)]


def select_technical_questions(tier: str, resume_projects: Optional[List[Dict[str, Any]]],
                               project: Optional[Dict[str, Any]],
                               rng: Optional[random.Random] = None) -> List[Dict[str, Any]]:
    r = rng or random
    counts = TCS_TECHNICAL_TOPIC_COUNTS.get(tier, TCS_TECHNICAL_TOPIC_COUNTS["ninja"])
    questions = [build_opener_question(resume_projects, project)]
    questions += _draw(OOP_QUESTIONS, counts["oop"], tier, r)
    questions += _draw(DBMS_SQL_QUESTIONS, counts["dbms_sql"], tier, r)
    questions += _draw(OS_QUESTIONS, counts["os"], tier, r)
    questions += _draw(NETWORKING_QUESTIONS, counts["networking"], tier, r)
    questions += _draw(CODING_DISCUSSION_QUESTIONS, counts["coding_discussion"], tier, r)
    return questions


def select_managerial_questions(tier: str, project: Optional[Dict[str, Any]],
                                rng: Optional[random.Random] = None) -> List[Dict[str, Any]]:
    r = rng or random
    n_situational = TCS_MANAGERIAL_SITUATIONAL_COUNTS.get(tier, 1)
    situational = _draw(MANAGERIAL_SITUATIONAL_QUESTIONS, n_situational, tier, r)
    gap = dict(r.choice(GAP_EXPLANATION_QUESTIONS))
    followup = build_tech_depth_followup_question(project)
    # Every MR question ALSO carries a "communication_clarity" extra signal
    # (OUR ESTIMATE: graded holistically per answer, not from a dedicated
    # question) -- tagged here at selection time, not baked into the bank
    # files, so the bank stays stage-agnostic.
    return [dict(q, extra_signal="communication_clarity") for q in (situational + [gap, followup])]


def select_hr_questions(tier: str, rng: Optional[random.Random] = None) -> List[Dict[str, Any]]:
    r = rng or random
    return (
        _draw(MOTIVATION_QUESTIONS, 1, tier, r)
        + _draw(STRENGTHS_WEAKNESSES_QUESTIONS, 1, tier, r)
        + _draw(COMPANY_KNOWLEDGE_QUESTIONS, 1, tier, r)
        + _draw(LOGISTICS_QUESTIONS, 1, tier, r)
    )


# ---- Stage machine (pure; advanced only by code) ---------------------------
def new_state(now: float) -> Dict[str, Any]:
    return {
        "stage": "technical",
        "status": "in_progress",
        "timed_out": False,
        "started_at": now,
        "deadline_at": now + TCS_DURATION_SECONDS,
        "budget_started_at": {"technical": now},
        "index": 0,
    }


def is_expired(state: Dict[str, Any], now: float) -> bool:
    return now >= state["deadline_at"]


def finish_timed_out(state: Dict[str, Any]) -> Dict[str, Any]:
    state["stage"] = "done"
    state["status"] = "timed_out"
    state["timed_out"] = True
    return state


def advance(stage_questions: Dict[str, List[Dict[str, Any]]], state: Dict[str, Any],
           now: float) -> Optional[Dict[str, Any]]:
    """Call AFTER grading the question at stage_questions[state['stage']]
    [state['index']]. Mutates `state` in place and returns the next
    question (as a client-shaped {id, stage, prompt} dict), or None once
    every stage is exhausted (state['status'] is set to 'completed' then).
    Every tier draws at least 1 question per stage by construction (see
    TCS_TECHNICAL_TOPIC_COUNTS/TCS_MANAGERIAL_SITUATIONAL_COUNTS/
    select_hr_questions), so no stage's question list is ever empty."""
    stage = state["stage"]
    state["index"] += 1
    current_list = stage_questions[stage]
    if state["index"] < len(current_list):
        q = current_list[state["index"]]
        return {"id": q["id"], "stage": stage, "prompt": q["text"]}
    pos = TCS_STAGE_ORDER.index(stage)
    if pos + 1 >= len(TCS_STAGE_ORDER):
        state["stage"] = "done"
        state["status"] = "completed"
        return None
    nxt = TCS_STAGE_ORDER[pos + 1]
    state["stage"] = nxt
    state["index"] = 0
    state["budget_started_at"][nxt] = now
    q = stage_questions[nxt][0]
    return {"id": q["id"], "stage": nxt, "prompt": q["text"]}


# ---- Element flags (normalised; never trusted raw) -------------------------
# Same evidence-quote defence philosophy as capgemini_interview/core.py's
# own normalize_*_flags functions (re-authored here, not imported, to keep
# this package's grading logic 100% independent of the Capgemini package).
QUOTE_MIN_CHARS = 12  # OUR ESTIMATE: shorter quotes are too thin to prove a signal
QUOTE_STRIP_CHARS = " \"'“”‘’.…"
INSTRUCTION_LIKE = ("ignore", "disregard", "mark all", "mark every", "score 100", "system:",
                    "you must", "as the grader", "grader:")


def _normalise_text(text: Any) -> str:
    return " ".join(str(text or "").lower().split())


def quote_rejection(quote: Any, answer: str) -> Optional[str]:
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


def normalize_key_point_flags(raw: Any, key_point_count: int, answer: str,
                              extra_signal: Optional[str] = None) -> Tuple[Dict[str, bool], List[Dict[str, Any]]]:
    """The one generic grader-output normalizer every TCS question uses
    (Technical, Managerial and HR alike) -- one flag per key point, plus an
    optional extra signal (Managerial's "communication_clarity")."""
    src = raw if isinstance(raw, dict) else {}
    points = src.get("key_points")
    points = points if isinstance(points, list) else []
    rejections: List[Dict[str, Any]] = []
    flags: Dict[str, bool] = {}
    for i in range(key_point_count):
        item = points[i] if i < len(points) else None
        flags[f"key_point_{i}"] = _checked_flag(item, answer, f"key_point_{i}", rejections)
    if extra_signal:
        flags[extra_signal] = _checked_flag(src.get(extra_signal), answer, extra_signal, rejections)
    return flags, rejections


# ---- Scoring (OUR ESTIMATE, report-only -- no pass/fail for TCS) ----------
def flags_score(flags: Dict[str, bool]) -> float:
    if not flags:
        return 0.0
    return sum(float(v) for v in flags.values()) / len(flags)


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _content_flags(flags: Dict[str, bool], extra_signal: Optional[str]) -> Dict[str, bool]:
    if not extra_signal:
        return flags
    return {k: v for k, v in flags.items() if k != extra_signal}


def technical_score(turns: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_topic: Dict[str, List[float]] = {}
    for t in turns:
        by_topic.setdefault(t["topic"], []).append(flags_score(t["flags"]))
    dims = {topic: _avg(vals) for topic, vals in by_topic.items()}
    not_reached = [d for d in TCS_TECHNICAL_DIMENSION_WEIGHTS if d not in dims]
    total = sum(TCS_TECHNICAL_DIMENSION_WEIGHTS[d] * dims.get(d, 0.0) for d in TCS_TECHNICAL_DIMENSION_WEIGHTS)
    return {"dimensions": dims, "score": round(total, 4), "not_reached": not_reached}


def managerial_score(turns: List[Dict[str, Any]]) -> Dict[str, Any]:
    situational = [flags_score(_content_flags(t["flags"], "communication_clarity"))
                   for t in turns if t["topic"] == "managerial_situational"]
    gap = [flags_score(_content_flags(t["flags"], "communication_clarity"))
           for t in turns if t["topic"] == "managerial_gap"]
    followup = [flags_score(_content_flags(t["flags"], "communication_clarity"))
                for t in turns if t["topic"] == "managerial_followup"]
    clarity = [1.0 if t["flags"].get("communication_clarity") else 0.0
               for t in turns if "communication_clarity" in t.get("flags", {})]
    dims = {
        "situational": _avg(situational),
        "gap_explanation": _avg(gap),
        "technical_depth_followup": _avg(followup),
        "communication_clarity": _avg(clarity),
    }
    not_reached = [d for d, vals in (("situational", situational), ("gap_explanation", gap),
                                      ("technical_depth_followup", followup)) if not vals]
    total = sum(TCS_MANAGERIAL_DIMENSION_WEIGHTS[d] * dims[d] for d in TCS_MANAGERIAL_DIMENSION_WEIGHTS)
    return {"dimensions": dims, "score": round(total, 4), "not_reached": not_reached}


_HR_TOPIC_TO_DIMENSION = {
    "hr_motivation": "motivation",
    "hr_strengths_weaknesses": "strengths_weaknesses",
    "hr_company_knowledge": "company_knowledge",
    "hr_logistics": "logistics",
}


def hr_score(turns: List[Dict[str, Any]]) -> Dict[str, Any]:
    dims: Dict[str, float] = {}
    not_reached = []
    for topic, name in _HR_TOPIC_TO_DIMENSION.items():
        matches = [flags_score(t["flags"]) for t in turns if t["topic"] == topic]
        dims[name] = _avg(matches)
        if not matches:
            not_reached.append(name)
    total = sum(TCS_HR_DIMENSION_WEIGHTS[d] * dims[d] for d in TCS_HR_DIMENSION_WEIGHTS)
    return {"dimensions": dims, "score": round(total, 4), "not_reached": not_reached}


def tcs_interview_score(tr: Dict[str, Any], mr: Dict[str, Any], hr: Dict[str, Any]) -> Dict[str, Any]:
    total = (TCS_TECHNICAL_WEIGHT * tr["score"] + TCS_MANAGERIAL_WEIGHT * mr["score"]
            + TCS_HR_WEIGHT * hr["score"])
    return {"technical": tr, "managerial": mr, "hr": hr, "interview": round(total, 4)}


# ---- Closing message (fixed template, emitted by code, never a model) -----
# Small, self-contained duplicate of capgemini_interview.closing_message's
# account-name sanitization (not imported) -- keeps this package's only
# Capgemini-package dependency the single pick_project import above.
CLOSING_TEMPLATE = "Thank you, {name}, for attending the interview. We will update you soon."
CLOSING_FALLBACK = "Thank you for attending the interview. We will update you soon."
_PLACEHOLDER_NAMES = {"", "auth0 user", "user", "unknown", "anonymous", "guest", "test user",
                      "none", "null", "undefined", "n/a", "name"}


def usable_account_name(name: Any, email: Any = None) -> Optional[str]:
    if not isinstance(name, str):
        return None
    text = " ".join(name.split())
    if not text or "@" in text or text.lower() in _PLACEHOLDER_NAMES:
        return None
    if isinstance(email, str) and "@" in email and text.lower() == email.split("@", 1)[0].strip().lower():
        return None
    return text


def closing_message(raw_name: Any, email: Any = None) -> str:
    name = usable_account_name(raw_name, email)
    return CLOSING_TEMPLATE.format(name=name) if name else CLOSING_FALLBACK


# ---- Client projection (whitelist) -----------------------------------------
def client_view(doc: Dict[str, Any], now: float) -> Dict[str, Any]:
    """The only shape the browser receives for a TCS interview. Strips
    flags, scores, question banks, rubrics and feedback -- same whitelist
    philosophy as capgemini_interview.client_view/dave_client_view."""
    state = doc["state"]
    finished = state["status"] != "in_progress"
    view: Dict[str, Any] = {
        "interview_id": doc["interview_id"],
        "attempt_id": doc.get("attempt_id"),
        "mode": "tcs",
        "company_name": doc.get("company_name"),
        "tier": doc.get("tier"),
        "tier_source": doc.get("tier_source"),
        "status": state["status"],
        "stage": state["stage"],
        "stage_label": STAGE_LABELS.get(state["stage"], state["stage"]),
        "stages": [{"stage": s, "label": STAGE_LABELS[s]} for s in TCS_STAGE_ORDER],
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
