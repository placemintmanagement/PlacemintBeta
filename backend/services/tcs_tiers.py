# -*- coding: utf-8 -*-
"""TCS NQT track estimation, computed once an OA attempt is completed.

Pure functions over the stored section_results: no database access, and no
client-supplied value is read. Mirrors services/capgemini_tiers.py's shape
(TIER_ORDER highest-first, a thresholds table, evaluate()/client_view()) so
anyone already familiar with that file can read this one the same way.

Tagging convention (per the repo owner's 2026-10 decisions for this file):
  OFFICIAL-TCS          -- from https://www.tcs.com/careers/india/tcs-all-india-nqt-hiring
  STATED-BY-USER         -- the repo owner told me this directly, not from a doc.
  USER-SUPPLIED-SECONDARY -- a screenshot / AI summary the owner supplied.
  PUBLIC-SOURCE-ONLY      -- a prep-site report (e.g. FACE Prep), not TCS itself.
  CONFLICTING-SOURCES     -- two sources disagree; the value picked is noted.
  INTERPOLATED            -- my own guess/placeholder, pending real data.

TCS publishes no track-decision cutoffs and does not state how OA scores map
to Ninja/Digital/Prime -- every threshold below is INTERPOLATED, same spirit
as capgemini_tiers.py's own INTERPOLATED entries: a clearly-labelled
placeholder for the owner to correct once real data exists, not a confirmed
fact. The one rule that IS confirmed (OFFICIAL-TCS, via the official page's
own wording: "mandatory if you aspire for a Digital or Prime offer") is that
skipping Part B caps the estimate at Ninja.
"""
from typing import Any, Dict, Optional

TIER_ORDER = ["prime", "digital", "ninja"]  # highest first

# OFFICIAL-TCS -- "as listed by TCS for the 2024-2026 batches" (UG = fresher
# straight out of an undergraduate degree; PG = postgraduate). TCS gives a
# range for Digital/Prime, a single figure for Ninja.
TCS_LPA_NOTE = "As listed by TCS for the 2024-2026 batches."
TCS_LPA = {
    "ninja":   {"ug": "3.4 LPA", "pg": "3.6 LPA"},                 # OFFICIAL-TCS
    "digital": {"ug": "7.09-7.30 LPA", "pg": "7.39-7.60 LPA"},     # OFFICIAL-TCS
    "prime":   {"ug": "9.09-9.30 LPA", "pg": "11.59-11.80 LPA"},   # OFFICIAL-TCS
}

# INTERPOLATED placeholders throughout -- TCS states no cutoffs anywhere.
# Foundation is scored out of 65 (20 numerical + 25 verbal + 20 reasoning),
# Advanced out of 15 (10 quant + 5 reasoning, USER-SUPPLIED-SECONDARY /
# PUBLIC-SOURCE-ONLY count -- see tcs_recruitment_process.py), Coding as a
# 0-1 fraction (2 problems, STATED-BY-USER count).
TCS_TIER_THRESHOLDS = {
    "ninja": {
        "foundation_min": 33,          # INTERPOLATED (~50% of 65)
    },
    "digital": {
        "foundation_min": 39,          # INTERPOLATED (~60% of 65)
        "advanced_min": 9,             # INTERPOLATED (60% of 15)
        "coding_min": 0.5,             # INTERPOLATED (at least 1 of 2 problems solved)
    },
    "prime": {
        "foundation_min": 46,          # INTERPOLATED (~70% of 65)
        "advanced_min": 11,            # INTERPOLATED (~73% of 15)
        "coding_min": 1.0,             # INTERPOLATED (both problems solved)
    },
}


def _section(section_results: Dict[str, Any], key: str) -> Dict[str, Any]:
    return section_results.get(key) or {}


def _foundation_correct(section_results: Dict[str, Any]) -> int:
    num = _section(section_results, "numerical")
    verb = _section(section_results, "verbal")
    reas = _section(section_results, "reasoning")
    return int(num.get("correct") or 0) + int(verb.get("correct") or 0) + int(reas.get("correct") or 0)


def _advanced_correct(section_results: Dict[str, Any]) -> int:
    return int(_section(section_results, "advanced").get("correct") or 0)


def _coding_score(section_results: Dict[str, Any]) -> float:
    return float(_section(section_results, "coding").get("score") or 0)


def client_view(tier_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Whitelist of what a client may see of a stored track estimate. The
    per-criterion breakdown stays on the attempt document for admin use
    only, same convention as capgemini_tiers.client_view."""
    return {"tier": tier_doc.get("tier"), "lpa": tier_doc.get("lpa"), "lpa_note": TCS_LPA_NOTE}


def evaluate(section_results: Dict[str, Any], part_b_attempted: bool) -> Dict[str, Any]:
    """Return the best track ESTIMATE this codebase can make, plus every
    criterion's value and result -- "estimate" because TCS publishes no real
    cutoffs (see module docstring). `part_b_attempted` must be False whenever
    the candidate used the finish-after-Foundation choice (or otherwise never
    reached a Part B section_results entry): OFFICIAL-TCS, via the official
    page's own "mandatory if you aspire for a Digital or Prime offer" wording,
    Ninja is the best possible estimate without Part B."""
    foundation = _foundation_correct(section_results)
    advanced = _advanced_correct(section_results)
    coding = _coding_score(section_results)

    t = TCS_TIER_THRESHOLDS
    criteria: Dict[str, Dict[str, Any]] = {
        "ninja": {
            "foundation": {"value": foundation, "min": t["ninja"]["foundation_min"],
                           "met": foundation >= t["ninja"]["foundation_min"]},
        },
    }
    if part_b_attempted:
        criteria["digital"] = {
            "foundation": {"value": foundation, "min": t["digital"]["foundation_min"],
                           "met": foundation >= t["digital"]["foundation_min"]},
            "advanced": {"value": advanced, "min": t["digital"]["advanced_min"],
                        "met": advanced >= t["digital"]["advanced_min"]},
            "coding": {"value": coding, "min": t["digital"]["coding_min"],
                      "met": coding >= t["digital"]["coding_min"]},
        }
        criteria["prime"] = {
            "foundation": {"value": foundation, "min": t["prime"]["foundation_min"],
                           "met": foundation >= t["prime"]["foundation_min"]},
            "advanced": {"value": advanced, "min": t["prime"]["advanced_min"],
                        "met": advanced >= t["prime"]["advanced_min"]},
            "coding": {"value": coding, "min": t["prime"]["coding_min"],
                      "met": coding >= t["prime"]["coding_min"]},
        }

    def _all_met(block: Dict[str, Any]) -> bool:
        return all(v.get("met") for v in block.values())

    order = TIER_ORDER if part_b_attempted else ["ninja"]
    tier: Optional[str] = next((name for name in order if name in criteria and _all_met(criteria[name])), None)
    lpa = TCS_LPA.get(tier) if tier else None
    return {
        "tier": tier,
        "lpa": lpa,
        "criteria": criteria,
        "part_b_attempted": part_b_attempted,
        "foundation_score": foundation,
        "foundation_max": 65,
        "advanced_score": advanced if part_b_attempted else None,
        "advanced_max": 15,
        "coding_score": coding if part_b_attempted else None,
    }
