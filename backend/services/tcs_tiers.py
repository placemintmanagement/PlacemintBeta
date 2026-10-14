# -*- coding: utf-8 -*-
"""TCS NQT track estimation, computed once an OA attempt is completed.

Pure functions over the stored section_results: no database access, and no
client-supplied value is read.

Tagging convention (per the repo owner's 2026-10 decisions for this file):
  OFFICIAL-TCS          -- from https://www.tcs.com/careers/india/tcs-all-india-nqt-hiring
  STATED-BY-USER         -- the repo owner told me this directly, not from a doc.
  USER-SUPPLIED-SECONDARY -- a screenshot / AI summary the owner supplied.
  PUBLIC-SOURCE-ONLY      -- a prep-site report (e.g. FACE Prep), not TCS itself.
  CONFLICTING-SOURCES     -- two sources disagree; the value picked is noted.
  INTERPOLATED            -- my own guess/placeholder, pending real data.

2026-10 REPLACEMENT (STATED-BY-USER): the previous version of this module
classified Digital/Prime using the Advanced MCQ section's score. The owner
replaced that with a classification based ONLY on Foundation's ratio and
each coding problem's sandbox test-pass RATIO (never a model call -- see
_problem_result). The Advanced MCQ section no longer participates in the
track decision at all.

TCS publishes no track-decision cutoffs and does not state how OA scores
map to Ninja/Digital/Prime -- the Foundation bars below are still
INTERPOLATED, a clearly-labelled placeholder for the owner to correct once
real data exists, not a confirmed fact. The coding-based Digital/Prime
formulas are STATED-BY-USER, the owner's own replacement rule, not sourced
from TCS or any prep site. The one rule that IS confirmed (OFFICIAL-TCS,
via the official page's own wording: "mandatory if you aspire for a
Digital or Prime offer") is that skipping Part B caps the estimate at
Ninja (or below, if Foundation itself doesn't qualify).

------------------------------------------------------------------------------
THE ONE CONFIG BLOCK every threshold in this module lives in:
------------------------------------------------------------------------------
"""
from typing import Any, Dict, List

TCS_TRACK_CONFIG: Dict[str, float] = {
    # INTERPOLATED -- TCS publishes no cutoffs anywhere. Below this
    # Foundation ratio, the candidate does not qualify for ANY track
    # (including Ninja), regardless of Part B.
    "QUALIFY_FOUNDATION": 0.50,
    # INTERPOLATED -- Foundation floor for Digital/Prime to even be in play.
    "DIGITAL_FOUNDATION_MIN": 0.60,
    "PRIME_FOUNDATION_MIN": 0.60,
    # STATED-BY-USER -- per-problem sandbox pass_ratio thresholds.
    "DIGITAL_PROBLEM_PASS_RATIO_MIN": 0.50,
    "PRIME_PROBLEM_PASS_RATIO_MIN": 0.50,
    # STATED-BY-USER -- below this many total tests for a problem, the
    # resulting pass_ratio is flagged "coarse_ratio" (too few tests for the
    # ratio to be a meaningful signal), not excluded from the decision.
    "COARSE_RATIO_TEST_COUNT_THRESHOLD": 6,
}

FOUNDATION_MAX = 65  # 20 numerical + 25 verbal + 20 reasoning -- USER-SUPPLIED-SECONDARY, see companies.py

NOT_QUALIFIED = "not_qualified"
TIER_ORDER = ["prime", "digital", "ninja", NOT_QUALIFIED]  # highest first, for display/reference only

# Human-facing display name per tier -- the one place this mapping lives for
# backend-rendered text (server.py's final-report narrative). The frontend
# (OAReview.jsx) keeps its own copy of this same mapping in JS; there's no
# cross-language constant-sharing mechanism in this repo, so it's duplicated
# deliberately, not an oversight. NOT_QUALIFIED's phrase is STATED-BY-USER
# (2026-10): "Below the estimated Foundation cutoff", not "Not Qualified" --
# reads as a measurement against an estimate, not a verdict on the candidate.
TCS_TIER_DISPLAY_NAMES = {
    "prime": "Prime",
    "digital": "Digital",
    "ninja": "Ninja",
    NOT_QUALIFIED: "Below the estimated Foundation cutoff",
}

# OFFICIAL-TCS -- "as listed by TCS for the 2024-2026 batches" (UG = fresher
# straight out of an undergraduate degree; PG = postgraduate). TCS gives a
# range for Digital/Prime, a single figure for Ninja. Unchanged by the
# 2026-10 classification-rule replacement above -- only HOW a tier is
# reached changed, not what each tier itself pays.
TCS_LPA_NOTE = "As listed by TCS for the 2024-2026 batches."
TCS_LPA = {
    "ninja":   {"ug": "3.4 LPA", "pg": "3.6 LPA"},                 # OFFICIAL-TCS
    "digital": {"ug": "7.09-7.30 LPA", "pg": "7.39-7.60 LPA"},     # OFFICIAL-TCS
    "prime":   {"ug": "9.09-9.30 LPA", "pg": "11.59-11.80 LPA"},   # OFFICIAL-TCS
}


def _section(section_results: Dict[str, Any], key: str) -> Dict[str, Any]:
    return section_results.get(key) or {}


def _foundation_correct(section_results: Dict[str, Any]) -> int:
    num = _section(section_results, "numerical")
    verb = _section(section_results, "verbal")
    reas = _section(section_results, "reasoning")
    return int(num.get("correct") or 0) + int(verb.get("correct") or 0) + int(reas.get("correct") or 0)


def _problem_result(problems: List[Dict[str, Any]], index: int) -> Dict[str, Any]:
    """Builds {passed, total, solved, pass_ratio[, coarse_ratio]} for the
    problem at `index` in the coding section's stored `problems` list
    (_grade_coding_section's own shape: each entry has `visible`/`hidden`
    {passed, total} sandbox test-run counts -- never a model call).

    Positional, not difficulty-keyed: "problem 2" means the SECOND problem
    PRESENTED (list index 1), which tcs_recruitment_process.apply_coding_
    profile already guarantees is always a medium problem for both profile
    A and profile B -- this function doesn't need to re-check difficulty,
    just read the position.

    A missing index (section not drawn, or fewer problems than expected)
    or a skipped problem (`_reference_broken` -- see _grade_coding_section)
    counts as passed=0, total=0, solved=False, pass_ratio=0.0 -- never
    crashes, never silently treats a skip/missing problem as a pass.

    Ratio-based, not fixed-count: reads whatever `total` the stored tests
    actually have, so this keeps working unchanged if the bank's test
    counts differ per problem or change over time. If `total` is below
    COARSE_RATIO_TEST_COUNT_THRESHOLD, adds `coarse_ratio: True` as an
    advisory flag (the ratio is still used in the decision -- this is a
    warning, not an exclusion)."""
    cfg = TCS_TRACK_CONFIG
    if index >= len(problems):
        return {"passed": 0, "total": 0, "solved": False, "pass_ratio": 0.0}
    p = problems[index]
    if p.get("skipped"):
        return {"passed": 0, "total": 0, "solved": False, "pass_ratio": 0.0}
    visible = p.get("visible") or {}
    hidden = p.get("hidden") or {}
    passed = int(visible.get("passed") or 0) + int(hidden.get("passed") or 0)
    total = int(visible.get("total") or 0) + int(hidden.get("total") or 0)
    pass_ratio = (passed / total) if total else 0.0
    solved = total > 0 and passed == total
    result: Dict[str, Any] = {
        "passed": passed, "total": total, "solved": solved, "pass_ratio": round(pass_ratio, 4),
    }
    if total < cfg["COARSE_RATIO_TEST_COUNT_THRESHOLD"]:
        result["coarse_ratio"] = True
    return result


def _build_reason(
    tier: str, foundation_correct: int, part_b_attempted: bool,
    problem_1: Dict[str, Any], problem_2: Dict[str, Any],
) -> str:
    """Plain-language, server-computed explanation for the result page --
    e.g. 'Foundation 41/65; coding problem 2 solved, so estimated Prime.'"""
    base = f"Foundation {foundation_correct}/{FOUNDATION_MAX}"
    if not part_b_attempted:
        if tier == NOT_QUALIFIED:
            return f"{base}; Part B was not attempted, and Foundation did not qualify."
        return f"{base}; Part B was not attempted, so the best estimate is {tier.capitalize()}."
    if tier == NOT_QUALIFIED:
        return f"{base}; Foundation did not qualify."
    if tier == "prime":
        if problem_2.get("solved"):
            detail = "coding problem 2 solved"
        else:
            detail = (
                f"problem 1 at {problem_1['pass_ratio'] * 100:.0f}% and "
                f"problem 2 at {problem_2['pass_ratio'] * 100:.0f}% pass rate"
            )
        return f"{base}; {detail}, so estimated Prime."
    if tier == "digital":
        if problem_1["pass_ratio"] >= TCS_TRACK_CONFIG["DIGITAL_PROBLEM_PASS_RATIO_MIN"]:
            detail = f"problem 1 at {problem_1['pass_ratio'] * 100:.0f}% pass rate"
        else:
            detail = f"problem 2 at {problem_2['pass_ratio'] * 100:.0f}% pass rate"
        return f"{base}; {detail}, so estimated Digital."
    return f"{base}; coding results below Digital's bar, so estimated Ninja."


def client_view(tier_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Whitelist of what a client may see of a stored track estimate --
    EXACTLY tier/lpa/lpa_note/reason/qualified (2026-10, tightened on
    request). No thresholds, no per-problem {passed, total, solved,
    pass_ratio} breakdown, no foundation_correct/foundation_max as
    separate fields, no part_b_attempted -- the plain-language `reason`
    string already carries the raw Foundation/per-problem counts in prose
    (e.g. "Foundation 41/65; coding problem 2 solved..."), so there's no
    need to ALSO expose them as separate structured fields. Everything
    else evaluate() computes stays server-side only, same whitelist
    philosophy as capgemini_tiers.client_view."""
    return {
        "tier": tier_doc.get("tier"),
        "lpa": tier_doc.get("lpa"),
        "lpa_note": TCS_LPA_NOTE,
        "reason": tier_doc.get("reason"),
        "qualified": tier_doc.get("qualified"),
    }


def evaluate(section_results: Dict[str, Any], part_b_attempted: bool) -> Dict[str, Any]:
    """Return the best track ESTIMATE this codebase can make -- "estimate"
    because TCS publishes no real cutoffs (see module docstring).

    `part_b_attempted` must be False whenever the candidate used the
    finish-after-Foundation choice (or otherwise never reached a Part B
    section_results entry): Digital/Prime are structurally unreachable
    without Part B (OFFICIAL-TCS, via the official page's own "mandatory
    if you aspire for a Digital or Prime offer" wording) -- the best
    possible estimate without Part B is Ninja, PROVIDED Foundation itself
    qualifies; otherwise not_qualified, same as with Part B attempted.

    Server-side only: every input here is read from section_results, which
    submit_section/finish_oa_part_a populate purely from re-derived grading
    (sandbox test results for coding, never a model call) -- nothing the
    client sends can set or influence the inputs or the outcome."""
    cfg = TCS_TRACK_CONFIG
    foundation_correct = _foundation_correct(section_results)
    foundation_ratio = foundation_correct / FOUNDATION_MAX
    qualified = foundation_ratio >= cfg["QUALIFY_FOUNDATION"]

    coding = _section(section_results, "coding")
    problems = coding.get("problems") or []
    problem_1 = _problem_result(problems, 0)
    problem_2 = _problem_result(problems, 1)

    prime_met = False
    digital_met = False
    if part_b_attempted:
        prime_met = foundation_ratio >= cfg["PRIME_FOUNDATION_MIN"] and (
            problem_2["solved"]
            or (
                problem_1["pass_ratio"] >= cfg["PRIME_PROBLEM_PASS_RATIO_MIN"]
                and problem_2["pass_ratio"] >= cfg["PRIME_PROBLEM_PASS_RATIO_MIN"]
            )
        )
        digital_met = foundation_ratio >= cfg["DIGITAL_FOUNDATION_MIN"] and (
            problem_1["pass_ratio"] >= cfg["DIGITAL_PROBLEM_PASS_RATIO_MIN"]
            or problem_2["pass_ratio"] >= cfg["DIGITAL_PROBLEM_PASS_RATIO_MIN"]
        )

    # Prime outranks Digital outranks Ninja -- checked in that order, with
    # not-qualified short-circuiting everything (a candidate who doesn't
    # even clear the Foundation floor can't be Ninja regardless of coding).
    if not qualified:
        tier = NOT_QUALIFIED
    elif prime_met:
        tier = "prime"
    elif digital_met:
        tier = "digital"
    else:
        tier = "ninja"

    reason = _build_reason(tier, foundation_correct, part_b_attempted, problem_1, problem_2)

    return {
        "tier": tier,
        "lpa": TCS_LPA.get(tier),
        "reason": reason,
        "qualified": qualified,
        "foundation_correct": foundation_correct,
        "foundation_max": FOUNDATION_MAX,
        "foundation_ratio": round(foundation_ratio, 4),
        "part_b_attempted": part_b_attempted,
        "problem_1": problem_1 if part_b_attempted else None,
        "problem_2": problem_2 if part_b_attempted else None,
    }
