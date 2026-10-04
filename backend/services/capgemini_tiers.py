"""Capgemini tier eligibility, computed once an OA attempt is completed.

Pure functions over the stored section_results: no database access, and no
client-supplied value is read. Round 1 (round1_communication) is deliberately
excluded from every criterion.

Each threshold below is tagged CONFIRMED or INTERPOLATED. INTERPOLATED values are
guesses (or placeholders where no number exists yet) and must be corrected here
without touching the logic in this file. The candidate-facing copy does not hedge,
but these comments must keep the distinction for future correction.
"""
from typing import Any, Dict, Optional

TIER_ORDER = ["commit", "dave", "spark"]  # highest first

TIER_LPA = {"spark": 4.25, "dave": 5.75, "commit": 7.50}

CAPGEMINI_TIER_THRESHOLDS = {
    "spark": {
        # Technical Module = AI Literacy + Technical Assessment correct answers, out of 40.
        "technical_module_min": 25,                    # CONFIRMED
        "debugging_or_ai_assisted": "at_least_one",    # CONFIRMED
        "cognitive_min": "qualifying_bar",             # CONFIRMED (see cognitive note below)
    },
    "dave": {
        "technical_module_min": 30,        # INTERPOLATED
        "debugging_required": True,        # INTERPOLATED
        "ai_assisted_min": 0.5,            # INTERPOLATED
        "cognitive_min": "comfortable",    # INTERPOLATED, no number yet
        # Placeholder accuracy for the "comfortable" wording. INTERPOLATED; replace
        # with the real figure when it is known.
        "cognitive_accuracy_min": 0.5,     # INTERPOLATED placeholder
    },
    "commit": {
        "technical_module_min": 35,        # CONFIRMED
        "debugging_min": 0.9,              # CONFIRMED wording "near-perfect"; 0.9 value INTERPOLATED
        "ai_assisted_min": 0.9,            # CONFIRMED wording "near-perfect"; 0.9 value INTERPOLATED
        "cognitive_min": "strong",         # INTERPOLATED, no number yet
        # Placeholder accuracy for the "strong" wording. INTERPOLATED; replace
        # with the real figure when it is known.
        "cognitive_accuracy_min": 0.75,    # INTERPOLATED placeholder
    },
}

# Qualifying bar for the cognitive round: the section's own configured cutoff
# (companies.py round5_cognitive cutoff 0.5). The "existing 60% qualifying bar"
# named in the brief does not appear anywhere in the code.
_COGNITIVE_SECTION_KEY = "round5_cognitive"


def _section(section_results: Dict[str, Any], key: str) -> Dict[str, Any]:
    return section_results.get(key) or {}


def _technical_module_score(section_results: Dict[str, Any]) -> int:
    ai = _section(section_results, "ai_literacy")
    tech = _section(section_results, "technical_assessment")
    return int(ai.get("correct") or 0) + int(tech.get("correct") or 0)


def evaluate(section_results: Dict[str, Any]) -> Dict[str, Any]:
    """Return the highest tier met plus every criterion's value and result."""
    tech = _technical_module_score(section_results)
    debugging = _section(section_results, "round3_debugging")
    ai_assisted = _section(section_results, "round4_ai_assisted")
    cognitive = _section(section_results, _COGNITIVE_SECTION_KEY)

    debug_score = float(debugging.get("score") or 0)
    debug_passed = bool(debugging.get("passed"))
    ai_score = float(ai_assisted.get("score") or 0)
    ai_passed = bool(ai_assisted.get("passed"))
    cog_score = float(cognitive.get("score") or 0)
    cog_passed = bool(cognitive.get("passed"))

    t = CAPGEMINI_TIER_THRESHOLDS
    criteria: Dict[str, Dict[str, Any]] = {}

    # Spark
    s = t["spark"]
    criteria["spark"] = {
        "technical_module": {"value": tech, "min": s["technical_module_min"], "met": tech >= s["technical_module_min"]},
        "debugging_or_ai_assisted": {
            "debugging_passed": debug_passed, "ai_assisted_passed": ai_passed,
            "met": debug_passed or ai_passed,
        },
        "cognitive": {"score": cog_score, "passed": cog_passed, "met": cog_passed},
    }
    # Dave
    d = t["dave"]
    criteria["dave"] = {
        "technical_module": {"value": tech, "min": d["technical_module_min"], "met": tech >= d["technical_module_min"]},
        "debugging": {"passed": debug_passed, "score": debug_score, "met": debug_passed},
        "ai_assisted": {"score": ai_score, "min": d["ai_assisted_min"], "met": ai_score >= d["ai_assisted_min"]},
        "cognitive": {"score": cog_score, "min": d["cognitive_accuracy_min"], "met": cog_score >= d["cognitive_accuracy_min"]},
    }
    # Commit
    c = t["commit"]
    criteria["commit"] = {
        "technical_module": {"value": tech, "min": c["technical_module_min"], "met": tech >= c["technical_module_min"]},
        "debugging": {"score": debug_score, "min": c["debugging_min"], "met": debug_score >= c["debugging_min"]},
        "ai_assisted": {"score": ai_score, "min": c["ai_assisted_min"], "met": ai_score >= c["ai_assisted_min"]},
        "cognitive": {"score": cog_score, "min": c["cognitive_accuracy_min"], "met": cog_score >= c["cognitive_accuracy_min"]},
    }

    def _all_met(block: Dict[str, Any]) -> bool:
        return all(v.get("met") for v in block.values())

    tier: Optional[str] = next((name for name in TIER_ORDER if _all_met(criteria[name])), None)
    return {
        "tier": tier,
        "lpa": TIER_LPA.get(tier) if tier else None,
        "criteria": criteria,
        "technical_module_score": tech,
        "technical_module_max": 40,
    }
