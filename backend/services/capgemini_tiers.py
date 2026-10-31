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
        "cognitive_min": 0.6,                          # CONFIRMED (60% qualifying bar)
    },
    "dave": {
        "technical_module_min": 30,        # INTERPOLATED
        "debugging_required": True,        # INTERPOLATED
        "ai_assisted_min": 0.5,            # INTERPOLATED
        "cognitive_min": 0.65,             # INTERPOLATED (must sit above Spark's 0.6)
    },
    "commit": {
        "technical_module_min": 35,        # CONFIRMED
        "debugging_min": 0.9,              # CONFIRMED wording "near-perfect"; 0.9 value INTERPOLATED
        # Round 4 components are stored separately (round4_ai_assisted.components),
        # so Commit uses them directly. Stage efficiency is excluded on purpose:
        # it depends on the grader's non-deterministic stage judgments.
        "ai_self_review_required": True,   # INTERPOLATED (self-review correct, component == 1)
        "ai_bug_explanation_min": 0.8,     # INTERPOLATED
        "cognitive_min": 0.75,             # INTERPOLATED, no number yet
    },
}

# Cognitive criteria compare the stored round5_cognitive `score` (correct/total)
# to each tier's numeric minimum. They never read `passed`, which uses the
# section's own 0.5 cutoff in companies.py. That cutoff and the confirmed 60%
# Spark bar currently disagree; the section cutoff is left unchanged.
_COGNITIVE_SECTION_KEY = "round5_cognitive"


def _section(section_results: Dict[str, Any], key: str) -> Dict[str, Any]:
    return section_results.get(key) or {}


def _technical_module_score(section_results: Dict[str, Any]) -> int:
    ai = _section(section_results, "ai_literacy")
    tech = _section(section_results, "technical_assessment")
    return int(ai.get("correct") or 0) + int(tech.get("correct") or 0)


def client_view(tier_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Whitelist of what a client may see of a stored tier result. The per-criterion
    breakdown stays on the attempt document for admin use only."""
    return {"tier": tier_doc.get("tier"), "lpa": tier_doc.get("lpa")}


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
    components = ai_assisted.get("components") or {}
    self_review_correct = components.get("self_review_correct") == 1.0
    bug_quality = float(components.get("bug_explanation_quality") or 0)

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
        "cognitive": {"score": cog_score, "min": s["cognitive_min"], "met": cog_score >= s["cognitive_min"]},
    }
    # Dave
    d = t["dave"]
    criteria["dave"] = {
        "technical_module": {"value": tech, "min": d["technical_module_min"], "met": tech >= d["technical_module_min"]},
        "debugging": {"passed": debug_passed, "score": debug_score, "met": debug_passed},
        "ai_assisted": {"score": ai_score, "min": d["ai_assisted_min"], "met": ai_score >= d["ai_assisted_min"]},
        "cognitive": {"score": cog_score, "min": d["cognitive_min"], "met": cog_score >= d["cognitive_min"]},
    }
    # Commit
    c = t["commit"]
    criteria["commit"] = {
        "technical_module": {"value": tech, "min": c["technical_module_min"], "met": tech >= c["technical_module_min"]},
        "debugging": {"score": debug_score, "min": c["debugging_min"], "met": debug_score >= c["debugging_min"]},
        "ai_assisted": {
            "self_review_correct": self_review_correct,
            "bug_explanation_quality": bug_quality,
            "min": c["ai_bug_explanation_min"],
            "met": bool(self_review_correct) and bug_quality >= c["ai_bug_explanation_min"],
        },
        "cognitive": {"score": cog_score, "min": c["cognitive_min"], "met": cog_score >= c["cognitive_min"]},
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
