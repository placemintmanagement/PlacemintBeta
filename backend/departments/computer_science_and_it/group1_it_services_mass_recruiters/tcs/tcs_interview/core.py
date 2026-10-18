# -*- coding: utf-8 -*-
"""TCS NQT interview: the single home for TCS interview information.

REWRITE (2026-10, part 1 of the 4-part "real TCS structure" task). The
previous version of this module modelled TCS as three SEPARATE stages
(Technical/Managerial/HR) -- a third-party guess at TCS's format. The
product owner has since corrected that assumption with real facts, listed
below as USER-STATED. This rewrite REPLACES the old TR/MR/HR stage model;
it does not add to it. The managerial and HR banks/questions/logistics
grading are gone (see banks/ directory -- managerial.py and hr.py were
deleted in this commit).

USER-STATED facts (supersede the old TR/MR/HR assumption):
  - TCS has 3 tiers (Ninja, Digital, Prime) with ONE interview round each
    -- no separate managerial or HR rounds.
  - Durations: Ninja 30 minutes; Digital and Prime 60 minutes each.
  - Core CS covers OOP, DBMS/SQL, Networks, OS, and Software Development.
    Core CS comes LAST in every tier.
  - Coding discussion is Easy for Ninja, Medium for Digital and Prime.
    Never Hard (TCS does not use Hard).
  - Architecture / tech-stack justification comes right after the project
    discussion (Digital and Prime only).
  - Puzzles are asked in Digital and Prime interviews only, no puzzle for
    Ninja. (Frequency unverified -- noted as unverified where relevant.)

Shape: ONE stage, literally named "interview", per tier. Within that single
stage, a tier works through an ordered list of PHASES (see
TCS_TIER_PHASE_ORDER below) -- expressed as plain per-tier config (a list),
not hardcoded per-tier control flow, so reordering a tier's phases later is
a one-line config edit, not a code change.

  ninja:   project -> coding (EASY) -> core
  digital: project -> architecture -> coding (MEDIUM) -> puzzle -> core
  prime:   project -> architecture -> coding (MEDIUM, deeper follow-ups) ->
           puzzle -> core

Prime differs from Digital by follow-up DEPTH and WEIGHTS, never by harder
coding problems (both Medium, never Hard).

Every numeric constant below not covered by a USER-STATED fact is tagged
`# OUR ESTIMATE` -- this repo's own choice, no independent TCS source.
Seed question content is tagged `# SEED CONTENT` in the bank files.

This module is pure: no imports from server.py, no database, no clock, no
LLM. orchestration.py (this package) calls these functions; ai_service.py
builds the grading prompt.
"""
import random
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview import (
    pick_project as _pick_project,
)
from .banks._kp import kp
from .banks.oop import OOP_QUESTIONS
from .banks.dbms_sql import DBMS_SQL_QUESTIONS
from .banks.os_bank import OS_QUESTIONS
from .banks.networking import NETWORKING_QUESTIONS
from .banks.coding_discussion import CODING_DISCUSSION_QUESTIONS
from .banks.software_development import SOFTWARE_DEVELOPMENT_QUESTIONS

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


# ---- Durations (USER-STATED) ------------------------------------------------
TCS_TIER_DURATION_MINUTES = {"ninja": 30, "digital": 60, "prime": 60}  # USER-STATED
TCS_TIER_DURATION_SECONDS = {t: m * 60 for t, m in TCS_TIER_DURATION_MINUTES.items()}

# ---- Phase order per tier: CONFIG, not control flow ------------------------
# A plain ordered list per tier. The engine (advance(), below) walks this
# list generically -- reordering a tier's phases is a one-line edit here,
# never a code change to the stage machine. Ninja has no "architecture" and
# no "puzzle" phase at all (not even a stub call) -- USER-STATED.
TCS_TIER_PHASE_ORDER: Dict[str, List[str]] = {
    "ninja":   ["project", "coding", "core"],
    "digital": ["project", "architecture", "coding", "puzzle", "core"],
    "prime":   ["project", "architecture", "coding", "puzzle", "core"],
}
PHASE_LABELS = {
    "project": "Project", "architecture": "Architecture", "coding": "Coding Discussion",
    "puzzle": "Puzzle", "core": "Core CS", "done": "Done",
}

# ---- Per-phase time/question budgets (OUR ESTIMATE, every value) ----------
# Each tier's phase minutes sum to that tier's total duration above.
# min_questions is a sensible small integer consistent with that budget --
# NOT a hard cap (a phase may ask slightly more if content calls for it),
# but the engine will never let an EARLIER phase eat into whatever phase
# comes after it beyond this budget once that later phase's own minimum has
# been met (see advance()'s overrun-skip below) -- and because "core" is
# always the LAST phase, nothing ever comes after it to protect itself
# against, so core's own pre-selected question list is delivered in full
# (bounded only by the overall interview deadline), never shortened by an
# earlier phase's overrun.
TCS_PHASE_BUDGETS: Dict[str, Dict[str, Dict[str, int]]] = {
    "ninja": {  # OUR ESTIMATE (sums to 30)
        "project": {"minutes": 8, "min_questions": 1},
        "coding":  {"minutes": 9, "min_questions": 1},
        "core":    {"minutes": 13, "min_questions": 5},
    },
    "digital": {  # OUR ESTIMATE (sums to 60)
        "project":      {"minutes": 10, "min_questions": 1},
        "architecture": {"minutes": 8, "min_questions": 1},
        "coding":       {"minutes": 18, "min_questions": 2},
        "puzzle":       {"minutes": 6, "min_questions": 1},
        "core":         {"minutes": 18, "min_questions": 5},
    },
    "prime": {  # OUR ESTIMATE (sums to 60)
        "project":      {"minutes": 7, "min_questions": 1},
        "architecture": {"minutes": 10, "min_questions": 1},
        "coding":       {"minutes": 18, "min_questions": 2},
        "puzzle":       {"minutes": 7, "min_questions": 1},
        "core":         {"minutes": 18, "min_questions": 5},
    },
}

# ---- Core-CS sub-mix (OUR ESTIMATE; sums to 1.0 per tier) ------------------
TCS_CORE_SUBMIX: Dict[str, Dict[str, float]] = {
    "ninja":   {"oop": 0.25, "dbms_sql": 0.25, "networking": 0.20, "os": 0.15, "software_development": 0.15},
    "digital": {"oop": 0.25, "dbms_sql": 0.25, "networking": 0.20, "os": 0.15, "software_development": 0.15},
    "prime":   {"oop": 0.25, "dbms_sql": 0.25, "networking": 0.20, "os": 0.20, "software_development": 0.10},
}
_CORE_BANKS = {
    "oop": OOP_QUESTIONS, "dbms_sql": DBMS_SQL_QUESTIONS, "networking": NETWORKING_QUESTIONS,
    "os": OS_QUESTIONS, "software_development": SOFTWARE_DEVELOPMENT_QUESTIONS,
}

# ---- Phase weights for final scoring (OUR ESTIMATE; sums to 1.0 per tier) --
# "communication" is NOT a flow phase (no questions/time budget of its own
# above) -- it is graded via the existing piggyback "communication_clarity"
# flag on every grading call (see ai_service.tcs_key_point_flags_prompt's
# extra_signal), never a separate AI call. It only appears here, as a
# scoring dimension.
TCS_PHASE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "ninja":   {"project": 0.25, "coding": 0.25, "core": 0.35, "communication": 0.15},
    "digital": {"project": 0.15, "architecture": 0.10, "coding": 0.25, "puzzle": 0.10,
                "core": 0.30, "communication": 0.10},
    "prime":   {"project": 0.10, "architecture": 0.15, "coding": 0.25, "puzzle": 0.10,
                "core": 0.30, "communication": 0.10},
}

EXTRA_SIGNAL = "communication_clarity"  # piggybacked onto every question's grading call


def _clean(value: Any, limit: int = 120) -> str:
    return " ".join(str(value or "").split())[:limit]


def _allocate_counts(weights: Dict[str, float], total: int) -> Dict[str, int]:
    """Largest-remainder (Hamilton) apportionment: splits `total` whole
    items across `weights`' keys in proportion to their weight, rounding so
    the parts sum to EXACTLY `total` (ordinary rounding of each part
    independently can over/undershoot). Generic -- used for the core-CS
    sub-mix today, reusable anywhere else a weighted integer split is
    needed."""
    if total <= 0 or not weights:
        return {k: 0 for k in weights}
    quotas = {k: w * total for k, w in weights.items()}
    floors = {k: int(q) for k, q in quotas.items()}
    remainder = total - sum(floors.values())
    order = sorted(weights, key=lambda k: (quotas[k] - floors[k]), reverse=True)
    for k in order[:remainder]:
        floors[k] += 1
    return floors


_LANGUAGE_SPLIT_RE = re.compile(r"[,/;&]|\band\b", re.IGNORECASE)


def infer_top_languages(resume_projects: Optional[List[Dict[str, Any]]]) -> List[str]:
    """The candidate's most common tech_stack entries across every analyzed
    project. Returns up to 2 distinct tokens, most frequent first."""
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


NO_PROJECT_LANGUAGES_QUESTION = (
    "Which two programming languages would you like to be evaluated in during this interview, and why?"
)


# ---- Project phase ----------------------------------------------------------
def build_project_question(resume_projects: Optional[List[Dict[str, Any]]],
                           project: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Every tier's FIRST phase. Infers the candidate's two most-used
    languages from resume tech_stack entries; if fewer than 2 can be
    inferred, asks directly instead."""
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
    return {"id": "tcs-project-1", "phase": "project", "topic": "project", "text": text, "key_points": key_points}


def select_project_questions(resume_projects: Optional[List[Dict[str, Any]]],
                             project: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [build_project_question(resume_projects, project)]


# ---- Architecture phase (Digital/Prime only) -------------------------------
def build_architecture_question(project: Optional[Dict[str, Any]], tier: str) -> Dict[str, Any]:
    """Right after the project phase (USER-STATED order), about the
    student's OWN project: Digital asks tech-stack justification (why this
    database, how the parts talk to each other); Prime asks the same ground
    PLUS an explicit design-tradeoff framing (same question family, deeper
    follow-up framing -- Prime differs from Digital by depth, not by a
    different topic)."""
    name = _clean(project.get("name")) if project else ""
    subject = f"\"{name}\"" if name else "a project you built"
    if is_prime(tier):
        text = (
            f"Think about the architecture of {subject}. Why did you choose the database and overall "
            "structure you used, how do the different parts of the system talk to each other, and what "
            "is one tradeoff you accepted in that design -- what would you reconsider if you were "
            "rebuilding it today?"
        )
        key_points = [
            kp("gives a specific reason for the database/technology choice, not just naming it"),
            kp("explains how the parts of the system communicate (e.g. API calls, shared DB, events)"),
            kp("names a real tradeoff accepted in the design, not a generic 'it works fine' answer"),
            kp("reflects on what they would reconsider or do differently, showing design judgement"),
        ]
    else:
        text = (
            f"Think about the architecture of {subject}. Why did you choose the database you used, and "
            "how do the different parts of the system talk to each other?"
        )
        key_points = [
            kp("gives a specific reason for the database/technology choice, not just naming it"),
            kp("explains how the parts of the system communicate (e.g. API calls, shared DB, function calls)"),
        ]
    return {"id": "tcs-arch-1", "phase": "architecture", "topic": "architecture", "text": text, "key_points": key_points}


def select_architecture_questions(project: Optional[Dict[str, Any]], tier: str) -> List[Dict[str, Any]]:
    if is_ninja(tier):
        return []
    return [build_architecture_question(project, tier)]


# ---- Coding-discussion phase ------------------------------------------------
# USER-STATED: Easy for Ninja, Medium for Digital and Prime, never Hard.
_CODING_DIFFICULTY_FOR_TIER = {"ninja": "easy", "digital": "medium", "prime": "medium"}


def select_coding_questions(tier: str, rng: random.Random) -> List[Dict[str, Any]]:
    difficulty = _CODING_DIFFICULTY_FOR_TIER.get(tier, "easy")
    n = TCS_PHASE_BUDGETS[tier]["coding"]["min_questions"]
    pool = [q for q in CODING_DISCUSSION_QUESTIONS if q.get("difficulty") == difficulty]
    if len(pool) < n:
        pool = CODING_DISCUSSION_QUESTIONS  # safety fallback, should not trigger with a healthy bank
    n = min(n, len(pool))
    chosen = [dict(q) for q in rng.sample(pool, n)]
    for q in chosen:
        q["phase"] = "coding"
    return chosen


# ---- Puzzle phase (Digital/Prime only) -------------------------------------
# STUB (Part 1 only): Part 3 wires in the real banks/interview_puzzle_bank.py
# (Part 2), chosen deterministically per-interview (seeded) by tier. For now
# this is a fixed, deterministic placeholder so Part 1's tests pass
# end-to-end without Part 2/3 existing yet. No NotImplementedError -- the
# flow must work today, just with placeholder content.
_PUZZLE_STUB_QUESTION: Dict[str, Any] = {
    "id": "tcs-puzzle-stub-1", "phase": "puzzle", "topic": "puzzle",
    "text": (
        "You have two identical eggs and a 100-floor building. You want to find the highest floor from "
        "which an egg can be dropped without breaking, using as few drops as possible in the worst case. "
        "Walk me through how you would approach this."
    ),
    "key_points": [
        kp("recognizes this is a worst-case minimization problem, not just a guess-and-check search",
           "names it as an optimization-under-uncertainty problem"),
        kp("describes a strategy better than a naive linear floor-by-floor search with one egg",
           "proposes some form of stepped or decreasing-interval search"),
    ],
}


def stub_puzzle_provider(tier: str, rng: random.Random) -> Dict[str, Any]:
    """Default puzzle-provider function (STUB). Part 3 replaces the
    default passed into select_puzzle_questions/build_phase_questions with
    a real provider backed by banks/interview_puzzle_bank.py."""
    return dict(_PUZZLE_STUB_QUESTION)


PuzzleProvider = Callable[[str, random.Random], Dict[str, Any]]


def select_puzzle_questions(tier: str, rng: random.Random,
                            puzzle_provider: PuzzleProvider = stub_puzzle_provider) -> List[Dict[str, Any]]:
    if is_ninja(tier):
        return []
    q = puzzle_provider(tier, rng)
    q = dict(q)
    q["phase"] = "puzzle"
    q.setdefault("topic", "puzzle")
    return [q]


# ---- Core-CS phase (always LAST; largest weight) ---------------------------
def _draw(bank: List[Dict[str, Any]], n: int, tier: str, rng: random.Random) -> List[Dict[str, Any]]:
    """n questions, drawn without replacement, preferring items at or below
    this tier's difficulty rank (falling back to the whole eligible pool if
    that preferred pool is too small). `tier_tags`, when present on an
    item, is a HARD allow-list (e.g. CI/CD / REST items tagged
    digital/prime-only must never reach Ninja even under that fallback) --
    applied before the rank-preference logic, never bypassed by it."""
    if n <= 0:
        return []
    eligible = [q for q in bank if not q.get("tier_tags") or tier in q["tier_tags"]]
    rank = _TIER_RANK.get(tier, 0)
    preferred = [q for q in eligible if _TIER_RANK.get(q.get("difficulty"), 0) <= rank]
    pool = preferred if len(preferred) >= n else eligible
    n = min(n, len(pool))
    return [dict(q) for q in rng.sample(pool, n)]


def select_core_questions(tier: str, rng: random.Random) -> List[Dict[str, Any]]:
    total = TCS_PHASE_BUDGETS[tier]["core"]["min_questions"]
    counts = _allocate_counts(TCS_CORE_SUBMIX[tier], total)
    questions: List[Dict[str, Any]] = []
    for topic, n in counts.items():
        questions += _draw(_CORE_BANKS[topic], n, tier, rng)
    for q in questions:
        q["phase"] = "core"
    return questions


# ---- Whole-interview question selection ------------------------------------
def build_phase_questions(tier: str, resume_projects: Optional[List[Dict[str, Any]]],
                          project: Optional[Dict[str, Any]], rng: random.Random,
                          puzzle_provider: PuzzleProvider = stub_puzzle_provider
                          ) -> Dict[str, List[Dict[str, Any]]]:
    """Every phase's full, pre-selected question list, built ONCE at
    interview start -- same "select everything up front into independent
    per-stage lists" shape the old TR/MR/HR version used, just generalized
    over this tier's phase list. Each phase's list is selected
    independently of every other phase's list (no shared pool to draw
    down), which is exactly what makes core.py's "protect the last phase's
    budget" guarantee hold: nothing an earlier phase does can shrink core's
    question list, because there was never a shared budget to take from."""
    builders = {
        "project": lambda: select_project_questions(resume_projects, project),
        "architecture": lambda: select_architecture_questions(project, tier),
        "coding": lambda: select_coding_questions(tier, rng),
        "puzzle": lambda: select_puzzle_questions(tier, rng, puzzle_provider),
        "core": lambda: select_core_questions(tier, rng),
    }
    phases = TCS_TIER_PHASE_ORDER[tier]
    out = {phase: builders[phase]() for phase in phases}
    for phase, qs in out.items():
        if not qs:
            raise ValueError(f"TCS phase {phase!r} for tier {tier!r} produced zero questions")
    return out


# ---- Stage machine (pure; advanced only by code) ---------------------------
# Single stage, literally "interview", for every tier (USER-STATED: TCS has
# ONE interview round per tier, not separate TR/MR/HR rounds). "phase"
# tracks progress through that tier's TCS_TIER_PHASE_ORDER.
STAGE_NAME = "interview"


def new_state(tier: str, now: float) -> Dict[str, Any]:
    first_phase = TCS_TIER_PHASE_ORDER[tier][0]
    return {
        "stage": STAGE_NAME,
        "phase": first_phase,
        "status": "in_progress",
        "timed_out": False,
        "started_at": now,
        "deadline_at": now + TCS_TIER_DURATION_SECONDS[tier],
        "phase_started_at": {first_phase: now},
        "index": 0,  # index within the CURRENT phase's question list
    }


def is_expired(state: Dict[str, Any], now: float) -> bool:
    return now >= state["deadline_at"]


def finish_timed_out(state: Dict[str, Any]) -> Dict[str, Any]:
    state["stage"] = "done"
    state["phase"] = "done"
    state["status"] = "timed_out"
    state["timed_out"] = True
    return state


def _client_question(q: Dict[str, Any], phase: str) -> Dict[str, Any]:
    return {"id": q["id"], "stage": STAGE_NAME, "phase": phase, "prompt": q["text"]}


def advance(tier: str, phase_questions: Dict[str, List[Dict[str, Any]]], state: Dict[str, Any],
           now: float) -> Optional[Dict[str, Any]]:
    """Call AFTER grading the question at phase_questions[state['phase']]
    [state['index']]. Mutates `state` in place and returns the next
    question (client-shaped), or None once every phase is exhausted
    (state['status'] set to 'completed' then).

    Budget protection: once a NON-LAST phase has met its own
    TCS_PHASE_BUDGETS min_questions AND has run longer than its own minutes
    budget, any remaining (optional, beyond-minimum) questions in that
    phase are skipped so the next phase starts sooner -- this is what
    reserves time for whatever comes after. The LAST phase (core, by
    construction, every tier) has no "next phase" to protect itself
    against this way, so it is never skipped into early: its full
    pre-selected question list (see build_phase_questions) is always
    offered in full, bounded only by the overall interview deadline, never
    by an earlier phase's overrun."""
    phase_order = TCS_TIER_PHASE_ORDER[tier]
    budgets = TCS_PHASE_BUDGETS[tier]
    phase = state["phase"]
    state["index"] += 1
    current_list = phase_questions[phase]
    pos = phase_order.index(phase)
    is_last_phase = pos + 1 >= len(phase_order)

    more_in_phase = state["index"] < len(current_list)
    overrun = False
    if more_in_phase and not is_last_phase:
        asked = state["index"]
        elapsed_minutes = (now - state["phase_started_at"][phase]) / 60.0
        budget = budgets[phase]
        overrun = asked >= budget["min_questions"] and elapsed_minutes >= budget["minutes"]

    if more_in_phase and not overrun:
        q = current_list[state["index"]]
        return _client_question(q, phase)

    if is_last_phase:
        state["stage"] = "done"
        state["phase"] = "done"
        state["status"] = "completed"
        return None

    nxt = phase_order[pos + 1]
    state["phase"] = nxt
    state["index"] = 0
    state["phase_started_at"][nxt] = now
    q = phase_questions[nxt][0]
    return _client_question(q, nxt)


# ---- Element flags (normalised; never trusted raw) -------------------------
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
    """The one generic grader-output normalizer every TCS question uses,
    whichever phase it belongs to -- one flag per key point, plus an
    optional piggybacked extra signal (communication_clarity)."""
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


def _content_score(turns: List[Dict[str, Any]]) -> float:
    return _avg([flags_score({k: v for k, v in t["flags"].items() if k != EXTRA_SIGNAL}) for t in turns])


def _simple_phase_score(turns: List[Dict[str, Any]], phase: str) -> Dict[str, Any]:
    phase_turns = [t for t in turns if t["phase"] == phase]
    return {"score": round(_content_score(phase_turns), 4), "reached": bool(phase_turns)}


def core_score(turns: List[Dict[str, Any]], tier: str) -> Dict[str, Any]:
    core_turns = [t for t in turns if t["phase"] == "core"]
    by_topic: Dict[str, List[float]] = {}
    for t in core_turns:
        by_topic.setdefault(t["topic"], []).append(
            flags_score({k: v for k, v in t["flags"].items() if k != EXTRA_SIGNAL}))
    dims = {topic: _avg(vals) for topic, vals in by_topic.items()}
    submix = TCS_CORE_SUBMIX[tier]
    not_reached = [d for d in submix if d not in dims]
    total = sum(submix[d] * dims.get(d, 0.0) for d in submix)
    return {"dimensions": dims, "score": round(total, 4), "not_reached": not_reached}


def communication_score(turns: List[Dict[str, Any]]) -> float:
    marked = [1.0 if t["flags"].get(EXTRA_SIGNAL) else 0.0 for t in turns if EXTRA_SIGNAL in t.get("flags", {})]
    return round(_avg(marked), 4)


def tcs_interview_score(tier: str, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
    phases: Dict[str, Any] = {}
    for phase in TCS_TIER_PHASE_ORDER[tier]:
        phases[phase] = core_score(turns, tier) if phase == "core" else _simple_phase_score(turns, phase)
    comm = communication_score(turns)
    weights = TCS_PHASE_WEIGHTS[tier]
    total = sum(weights[p] * phases[p]["score"] for p in phases) + weights["communication"] * comm
    return {"phases": phases, "communication": comm, "interview": round(total, 4)}


# ---- Closing message (fixed template, emitted by code, never a model) -----
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
    flags, scores, question banks, rubrics and feedback."""
    state = doc["state"]
    tier = doc["tier"]
    finished = state["status"] != "in_progress"
    phases = TCS_TIER_PHASE_ORDER[tier]
    view: Dict[str, Any] = {
        "interview_id": doc["interview_id"],
        "attempt_id": doc.get("attempt_id"),
        "mode": "tcs",
        "company_name": doc.get("company_name"),
        "tier": tier,
        "tier_source": doc.get("tier_source"),
        "status": state["status"],
        "stage": STAGE_NAME,
        "phase": state["phase"],
        "phase_label": PHASE_LABELS.get(state["phase"], state["phase"]),
        "phases": [{"phase": p, "label": PHASE_LABELS[p]} for p in phases],
        "deadline_epoch": state["deadline_at"],
        "server_now_epoch": now,
        "turns": [{"phase": t["phase"], "question": t["question"], "answer": t["answer"]}
                  for t in doc.get("turns", [])],
        "current_question": None,
        "closing_message": closing_message(doc.get("candidate_name")) if finished else None,
    }
    if not finished and doc.get("current_question"):
        q = doc["current_question"]
        view["current_question"] = {"id": q["id"], "phase": q["phase"], "prompt": q["prompt"]}
    return view
