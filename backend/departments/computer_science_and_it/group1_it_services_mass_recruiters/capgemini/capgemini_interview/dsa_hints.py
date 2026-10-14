# -*- coding: utf-8 -*-
"""DSA hint detection and dispensing -- FEATURE: on-demand hints during the
DSA solving stage of Spark/Dave/Commit (STAGE 2 of the DSA-hints build; the
static ladders themselves -- spark/hints.py, dave/hints.py -- are STAGE 1).

Pure module, same discipline as pushback.py and humanize.py: no import from
server.py, no database, no clock, and -- the whole point of this feature --
NO model call anywhere in this file. Detection is rule-based (keyword/phrase
matching plus a cheap "does this look like a real attempt" heuristic);
dispensing just indexes into the static ladders built in Stage 1. Cost is
zero regardless of how many times a candidate asks for a hint.

Behaviour (STATED by the owner):
  - A candidate can ask for a HINT, ask for the ANSWER outright (refused), or
    ask for CONFIRMATION that their approach is right (refused, neutrally).
  - A message that actually contains real solution content -- a code block,
    or a substantive (15+ word) description of an approach -- is never any
    of the above, even if it happens to contain the word "hint" (e.g. in a
    code comment, or as a throwaway aside at the end of a long answer). It
    is a genuine attempt and must fall through to the normal grading path
    with zero special handling here.
  - Hints are dispensed in order (L1, then L2, then L3), never repeated,
    capped per tier: Spark 3, Dave 3, Commit 2 (Commit's cap is BELOW the
    3-level ladder by design -- STATED -- so a Commit candidate can reach L2
    but never L3, the tier's harder 75-minute format expecting more
    self-sufficiency once nudged).
  - None of the fixed replies below may say or imply whether the candidate's
    own approach is right or wrong -- that judgement stays with the real
    grader on the candidate's actual submitted answer, never with a hint.

Tags: STATED = given directly in the spec. INTERPOLATED = my own choice to
fill a gap, pending the owner's review (flagged individually below).
"""
import re
from typing import Dict, List, Optional

from .spark.hints import SPARK_DSA_HINTS
from .dave.hints import DAVE_DSA_HINTS

# ---- Per-tier limits (STATED) ----------------------------------------------
HINT_LIMITS: Dict[str, int] = {"spark": 3, "dave": 3, "commit": 2}

# The DSA solving question ids this feature applies to -- i.e. "the DSA
# solving stage" (STATED: "only during the DSA solving stage"). Deliberately
# excludes Spark's separate "spark-dsa-complexity" question and Dave/Commit's
# separate "*-time-complexity"/"*-space-complexity" stages: those ask about
# Big-O, not algorithmic approach, and the hint ladders are approach-only.
# "commit-dsa-efficiency" IS included -- it is Commit's own optional
# more-efficient-approach nudge on the SAME DSA problem, still squarely
# "the DSA solving stage" (INTERPOLATED: the alternative, excluding it,
# would leave a candidate who reached this sub-question with no way to ask
# for help on the very question that's pushing them toward a better
# approach).
DSA_SOLVING_QUESTION_IDS = frozenset({"spark-dsa", "dave-dsa", "commit-dsa", "commit-dsa-efficiency"})


def is_dsa_solving_question(current_question_id: Optional[str]) -> bool:
    return current_question_id in DSA_SOLVING_QUESTION_IDS


def _ladder_bank(tier: str) -> Dict[str, List[str]]:
    # Commit reuses Dave's bank verbatim (see dave/hints.py's own docstring
    # and commit/flow.py: Commit draws its DSA problem from the same bank).
    return SPARK_DSA_HINTS if tier == "spark" else DAVE_DSA_HINTS


def get_ladder(tier: str, problem_id: Optional[str]) -> Optional[List[str]]:
    if not problem_id:
        return None
    return _ladder_bank(tier).get(problem_id)


# ---- Detection: real-attempt heuristic --------------------------------------
# A message is treated as a genuine solving attempt -- never as a hint/
# answer/confirmation request, regardless of keyword overlap -- the moment it
# contains a code block OR is a substantive (15+ word) description. This is
# intentionally cheap and a little generous toward "treat it as an attempt":
# the failure mode of under-detecting a hint request is a candidate having to
# ask again in plainer words; the failure mode of over-detecting one is a
# real attempt getting swallowed and never graded, which is far worse.
_SUBSTANTIVE_WORD_THRESHOLD = 15  # STATED ("a substantive approach of 15+ words")

# Code-block fence, or a line that looks like actual code (def/class/for/
# while/import/return at the start of a line). Matches "code with 'hint' in
# a comment" too, since the fence/keyword check runs independently of any
# word content.
_CODE_MARKERS_RE = re.compile(
    r"```|^\s*(def\s|class\s|for\s+\w+\s+in\s|while\s.+:|import\s|return\s)", re.MULTILINE)


def _word_count(text: str) -> int:
    return len((text or "").split())


def _has_code(text: str) -> bool:
    return bool(_CODE_MARKERS_RE.search(text or ""))


def _looks_like_attempt(text: str) -> bool:
    return _has_code(text) or _word_count(text) >= _SUBSTANTIVE_WORD_THRESHOLD


# ---- Detection: phrase banks (STATED examples, INTERPOLATED variants/
# Hinglish spellings added to reach reasonable phrasing coverage) -----------
HINT_PHRASES: List[str] = [
    "can i get a hint", "can you give me a hint", "could i get a hint",
    "any hint", "any hints", "any more hint", "any more hints", "more hints", "another hint",
    "got any hints", "got any more hints", "give me a hint", "give a hint", "give me another hint",
    "i'm stuck", "im stuck", "i am stuck", "i'm blank", "im blank", "i am blank",
    "give me a clue", "give a clue", "how should i approach this",
    "how do i approach this", "which algorithm should i use",
    "what algorithm should i use", "need a hint", "need help on this",
    "a hint please", "hint please",
    # Hinglish (STATED examples, verbatim) + a few natural variants (INTERPOLATED)
    "hint dijiye", "kuch hint do", "hint de do", "thoda help karo",
    "koi hint do", "thoda hint do", "ek hint do", "madad kar do",
]

ANSWER_REQUEST_PHRASES: List[str] = [
    "just tell me the answer", "tell me the answer", "what's the answer", "whats the answer",
    "give me the solution", "give the solution", "what's the solution", "whats the solution",
    "what is the solution", "tell me the solution", "just give me the answer",
    "can you give me the answer", "please give me the answer",
    "show me the code", "show the code", "give me the code", "just show me the solution",
]

CONFIRMATION_PHRASES: List[str] = [
    "is this right", "is this correct", "is this approach right", "is this the right approach",
    "am i on the right track", "am i on the right path", "am i right", "am i correct",
    "is my approach correct", "is my approach right", "is my logic correct",
    "does this look right", "does this sound right", "does that look right",
    "is that correct", "is that right",
]


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def classify_dsa_message(text: str) -> Optional[str]:
    """Returns "hint", "answer_request", "confirmation", or None (treat as a
    normal solving attempt -- either a genuine answer, or simply unmatched
    chatter, which must fail SAFE into the normal grading path rather than
    being swallowed here)."""
    if not text or not text.strip():
        return None
    if _looks_like_attempt(text):
        return None
    norm = _normalize(text)
    if any(p in norm for p in HINT_PHRASES):
        return "hint"
    if any(p in norm for p in ANSWER_REQUEST_PHRASES):
        return "answer_request"
    if any(p in norm for p in CONFIRMATION_PHRASES):
        return "confirmation"
    return None


# ---- Fixed replies (STATED wording) ----------------------------------------
ANSWER_REFUSAL = "I can't give you the answer, but I can nudge you. Want a hint?"
CONFIRMATION_REPLY = "Walk me through it and let's see where it goes."
HINTS_EXHAUSTED_REPLY = "I've given you what I can on this one. Give it your best shot."

# Lead-ins (STATED: "a short spoken lead-in (max 12 words)"; each one here is
# well under that). INTERPOLATED: the exact wording and count (6, mirroring
# pushback.py's PUSHBACK_LINES precedent of "5-8 variants, no back-to-back
# repeat") -- two of these are the owner's own examples, used verbatim.
HINT_LEAD_INS: List[str] = [
    "Sure, think about this:",          # STATED example, verbatim
    "Okay, here's a nudge:",            # STATED example, verbatim
    "Here's something to consider:",
    "Let's try this angle:",
    "Fair enough, here's a nudge:",
    "Sure, here's a thought:",
]


def pick_lead_in(rng, previous: Optional[str] = None) -> str:
    """Same no-back-to-back-repeat shape as pushback.pick_pushback_line."""
    choices = [line for line in HINT_LEAD_INS if line != previous] or HINT_LEAD_INS
    return rng.choice(choices)


# ---- Dispensing --------------------------------------------------------------
def next_hint_reply(tier: str, problem_id: Optional[str], hints_used: int, rng,
                    previous_lead_in: Optional[str] = None) -> Optional[tuple]:
    """Returns (lead_in, full_reply_text) for a HINT request -- full_reply is
    the lead-in plus the next unused ladder level -- or None if the ladder/
    problem is unknown (should not happen in practice -- every bank problem
    has a ladder, verified by tests/test_dsa_hints_lint.py). Caller is
    responsible for checking hints_used against HINT_LIMITS[tier] first and
    dispensing the exhausted message instead when the cap is reached."""
    ladder = get_ladder(tier, problem_id)
    if ladder is None or hints_used >= len(ladder):
        return None
    lead_in = pick_lead_in(rng, previous_lead_in)
    return lead_in, f"{lead_in} {ladder[hints_used]}"


# ---- Scoring penalty (STATED: 0.1 per hint used, multiplicative, floor 0.5) -
HINT_PENALTY_PER_HINT = 0.1
HINT_PENALTY_FLOOR = 0.5


def apply_hint_penalty(score: Optional[float], hints_used: int) -> Optional[float]:
    """Multiplies the DSA stage score by (1 - 0.1 * hints_used), never below
    the 0.5 floor. A no-op (returns score unchanged) if there's no score to
    penalize (DSA never reached) or no hints were used. Does not touch any
    other stage's score -- callers apply this to the DSA component alone,
    before it is combined into the overall interview score."""
    if score is None or not hints_used:
        return score
    multiplier = max(HINT_PENALTY_FLOOR, 1.0 - HINT_PENALTY_PER_HINT * hints_used)
    return score * multiplier


# ---- One call per DSA-stage submission, before any grading -----------------
def handle_dsa_message(tier: str, answer_text: str, problem_id: Optional[str], hints_used: int,
                       rng, previous_lead_in: Optional[str] = None) -> Optional[Dict]:
    """The single entry point server.py calls at the top of the DSA solving
    stage, before any grading/model call. Returns None if `answer_text` is a
    genuine solving attempt (or unmatched chatter) -- the caller must then
    proceed with its normal grading flow, completely unaffected by this
    module. Otherwise returns a dict describing the system's reply and the
    new state for the caller to persist:
        {"kind": "hint" | "hint_exhausted" | "answer_request" | "confirmation",
         "reply": str, "text": Optional[str], "hints_used": int,
         "lead_in": Optional[str], "is_hint": bool}
    `hints_used` in the return value is the count to STORE (unchanged for
    every kind except "hint", which increments it by exactly one). `lead_in`
    is the lead-in actually used (for the caller to pass back in as
    `previous_lead_in` next time, for the no-back-to-back-repeat behaviour),
    or None for every kind except "hint". `text` is the raw ladder line with
    NO lead-in prepended (for the caller to persist/display as its own
    field, separate from `lead_in`) -- present only for kind=="hint", None
    otherwise; `reply` (lead_in + text combined) is kept for any caller that
    still wants one ready-made string."""
    kind = classify_dsa_message(answer_text)
    if kind is None:
        return None
    if kind == "hint":
        limit = HINT_LIMITS.get(tier, 0)
        if hints_used >= limit:
            return {"kind": "hint_exhausted", "reply": HINTS_EXHAUSTED_REPLY, "text": None,
                    "hints_used": hints_used, "lead_in": None, "is_hint": False}
        dispensed = next_hint_reply(tier, problem_id, hints_used, rng, previous_lead_in)
        if dispensed is None:
            # No ladder for this problem (should not happen -- Stage 1's lint
            # covers every bank problem) -- fail safe to the exhausted line
            # rather than crash or silently grant an empty hint.
            return {"kind": "hint_exhausted", "reply": HINTS_EXHAUSTED_REPLY, "text": None,
                    "hints_used": hints_used, "lead_in": None, "is_hint": False}
        lead_in, reply = dispensed
        ladder = get_ladder(tier, problem_id)
        return {"kind": "hint", "reply": reply, "text": ladder[hints_used], "hints_used": hints_used + 1,
                "lead_in": lead_in, "is_hint": True}
    if kind == "answer_request":
        return {"kind": "answer_request", "reply": ANSWER_REFUSAL, "text": None, "hints_used": hints_used,
                "lead_in": None, "is_hint": False}
    # kind == "confirmation"
    return {"kind": "confirmation", "reply": CONFIRMATION_REPLY, "text": None, "hints_used": hints_used,
            "lead_in": None, "is_hint": False}
