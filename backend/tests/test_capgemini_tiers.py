"""Synthetic checks for services/capgemini_tiers.py (no database, no network)."""
from services import capgemini_tiers as ct


def _results(tech_ai, tech_tech, debug_score, debug_passed, ai_score, ai_passed, cog_score, cog_passed):
    return {
        "round1_communication": {"score": 0.0, "passed": False},  # must never affect the outcome
        "ai_literacy": {"score": 0.0, "correct": tech_ai, "total": 20, "passed": True},
        "technical_assessment": {"score": 0.0, "correct": tech_tech, "total": 20, "passed": True},
        "round3_debugging": {"score": debug_score, "passed": debug_passed},
        "round4_ai_assisted": {"score": ai_score, "passed": ai_passed},
        "round5_cognitive": {"score": cog_score, "passed": cog_passed},
    }


def test_spark_only():
    # Technical 26/40, debugging failed, AI-assisted solved (>= one of the two), cognitive passed.
    r = ct.evaluate(_results(13, 13, 0.0, False, 0.6, True, 0.6, True))
    assert r["tier"] == "spark"
    assert r["lpa"] == 4.25


def test_dave_level():
    # Technical 31/40, debugging solved, AI-assisted 0.6, cognitive 0.6 (>= placeholder 0.5).
    r = ct.evaluate(_results(16, 15, 0.7, True, 0.6, True, 0.6, True))
    assert r["tier"] == "dave"
    assert r["lpa"] == 5.75


def test_commit_level():
    # Technical 36/40, debugging 1.0, AI-assisted 0.95, cognitive 0.8 (>= placeholder 0.75).
    r = ct.evaluate(_results(18, 18, 1.0, True, 0.95, True, 0.8, True))
    assert r["tier"] == "commit"
    assert r["lpa"] == 7.50


def test_no_tier_when_technical_below_spark_bar():
    r = ct.evaluate(_results(10, 10, 1.0, True, 1.0, True, 1.0, True))  # 20/40
    assert r["tier"] is None
    assert r["lpa"] is None


def test_no_tier_when_cognitive_fails_spark():
    r = ct.evaluate(_results(13, 13, 1.0, True, 1.0, True, 0.2, False))  # 26/40 but cognitive fails
    assert r["tier"] is None


def test_round1_is_ignored():
    base = _results(13, 13, 0.0, False, 0.6, True, 0.6, True)
    base["round1_communication"] = {"score": 1.0, "passed": True}
    assert ct.evaluate(base)["tier"] == "spark"


def test_empty_results_meet_no_tier():
    assert ct.evaluate({})["tier"] is None
