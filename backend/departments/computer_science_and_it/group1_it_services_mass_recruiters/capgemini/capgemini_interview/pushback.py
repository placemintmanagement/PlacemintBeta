# -*- coding: utf-8 -*-
"""Soft pushback ("think again") for the Capgemini interviews -- FEATURE B.

Pure module: no import from server.py, no database, no clock, no LLM call --
the trigger decision below is made entirely from grader flags the caller
already has in hand (see server.py's synchronous grading, audited in the
build report); this module adds no model call of its own.

Behaviour (STATED by the owner): an interviewer never tells the candidate an
answer is wrong to their face; they say something like "think again". This
is independent of FEATURE A's neutral acknowledgements, which stay
uncorrelated with grade -- pushback is the one place grade DOES drive a
candidate-facing line, by design.

Tags: STATED = given directly in the spec. INTERPOLATED = my choice to fill
a gap, pending the owner's review (flagged individually below).
"""
import random
import re
from typing import Dict, List, Optional

# ---- Named constants (STATED starting values) --------------------------------
MIN_ATTEMPT_WORDS = 15               # STATED starting value
MAX_PUSHBACKS_PER_INTERVIEW = 4      # STATED starting value
HINT_CREDIT = 0.5                    # STATED starting value
PUSHBACK_MIN_REMAINING_SECONDS = 120  # STATED ("never when under 2 minutes remain")

# Stages this applies to (STATED): fixed CS questions (Dave's cs_fundamentals,
# Commit's cs_grilling) and the time/space complexity answers (Dave + Commit).
# NOT projects, HR, or the DSA solution stage. Spark has no CS stage and no
# complexity stage of its own (complexity is folded into the single DSA
# turn's `complexity_stated` flag, not a separate answer) -- STATED to mean
# nothing in Spark triggers pushback; confirmed against core.py's SPARK_STAGES
# (no time_complexity/space_complexity stage exists for Spark).
PUSHBACK_ELIGIBLE_STAGES = {"cs_fundamentals", "cs_grilling", "time_complexity", "space_complexity"}


def is_pushback_eligible_stage(stage: str) -> bool:
    return stage in PUSHBACK_ELIGIBLE_STAGES


# ---- Trigger (STATED: code decides from grader flags already in hand) -------
def should_pushback(answer: str, flags: Dict[str, bool], complexity_dimension: Optional[str] = None) -> bool:
    """True iff: the answer has >= MIN_ATTEMPT_WORDS words, AND zero key
    points (or, for a complexity answer, the accepted-complexity flag) came
    back present. A partial answer (>=1 key point present) does NOT trigger
    this -- it continues to the stage's normal fixed follow-up instead. A
    pass is handled upstream by FEATURE A's is_pass_phrase() before grading
    is even attempted, so it never reaches this function with a real `flags`
    dict (INTERPOLATED call-order: pass-detection must run before grading,
    since a pass should not be graded at all).

    `complexity_dimension` is "time" or "space" for the complexity stages,
    None for CS-fundamentals/CS-grilling. normalize_dave_complexity_flags
    returns TWO keys per dimension -- f"{dim}_stated" (a quote was given at
    all) and f"{dim}_correct" (the accepted-complexity check itself) -- so
    the trigger must name the `_correct` key explicitly rather than guessing
    from dict order (a real bug caught while writing this: dict iteration
    order happened to put `_stated` first, which is not the same check)."""
    word_count = len((answer or "").split())
    if word_count < MIN_ATTEMPT_WORDS:
        return False
    if complexity_dimension:
        return not flags.get(f"{complexity_dimension}_correct", False)
    return not any(flags.values())


# ---- Pushback limits (STATED) ------------------------------------------------
def pushback_allowed(already_pushed_back_this_question: bool, pushbacks_used_this_interview: int,
                     remaining_seconds: float, budget_exceeded: bool) -> bool:
    if already_pushed_back_this_question:
        return False
    if pushbacks_used_this_interview >= MAX_PUSHBACKS_PER_INTERVIEW:
        return False
    if remaining_seconds < PUSHBACK_MIN_REMAINING_SECONDS:
        return False
    if budget_exceeded:
        return False
    return True


# ---- Pushback lines (STATED: 5-8 variants, no back-to-back repeat) ----------
PUSHBACK_LINES: List[str] = [
    "Hmm, take a moment and think about that again.",
    "Are you sure about that? Walk me through it once more.",
    "Let's look at that once more. Anything you'd like to reconsider?",
    "Take another pass at that one -- what else comes to mind?",
    "I'd like you to think about that a bit more before we move on.",
    "Let's revisit that for a second. Want to try again?",
]  # STATED (3 examples given verbatim, used here unchanged); 3 more added (INTERPOLATED) to reach 6, within 5-8

# STATED lint rule: no line may contain these, or any part of the expected
# answer or a hint. The forbidden-word check is unconditional (runs over the
# fixed line set itself, below); the key-point check is parameterized since
# it depends on the bank's own wording per question.
_FORBIDDEN_SUBSTRINGS = ("wrong", "incorrect", "not right", "no,")


def lint_pushback_line(line: str, forbidden_fragments: Optional[List[str]] = None) -> List[str]:
    """Returns the list of violations (empty if the line is clean). Checked
    case-insensitively. `forbidden_fragments` is the set of key-point/hint
    fragments to additionally screen for, for a specific question."""
    violations = []
    lowered = line.lower()
    for bad in _FORBIDDEN_SUBSTRINGS:
        if bad in lowered:
            violations.append(f"contains forbidden word/phrase: {bad!r}")
    for frag in (forbidden_fragments or []):
        frag = (frag or "").strip().lower()
        if frag and frag in lowered:
            violations.append(f"contains a key-point/hint fragment: {frag!r}")
    return violations


def pick_pushback_line(rng: random.Random, previous: Optional[str]) -> str:
    choices = [line for line in PUSHBACK_LINES if line != previous] or PUSHBACK_LINES
    return rng.choice(choices)


# ---- Second-attempt hint credit (STATED) -------------------------------------
def apply_hint_credit(first_attempt_flags: Dict[str, bool], second_attempt_flags: Dict[str, bool]
                      ) -> Dict[str, float]:
    """Per STATED rule 5: key points found in the FIRST attempt keep full
    value (1.0); key points found only in the SECOND attempt earn HINT_CREDIT
    of their normal value. A key point present in neither attempt scores 0.
    Returns a dict of the same keys as the flags, with float values (not
    bool) -- the caller's scoring function is responsible for summing these
    at whatever per-key-point weight it already uses, same as it already
    sums booleans today (a bool True is weight 1.0; this just allows 0.5
    too)."""
    credited: Dict[str, float] = {}
    for key in first_attempt_flags:
        if first_attempt_flags.get(key):
            credited[key] = 1.0
        elif second_attempt_flags.get(key):
            credited[key] = HINT_CREDIT
        else:
            credited[key] = 0.0
    return credited
