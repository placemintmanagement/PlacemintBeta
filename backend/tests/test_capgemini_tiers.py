"""Synthetic checks for services/capgemini_tiers.py (no database, no network)."""
from services import capgemini_tiers as ct

DEFAULT_R4_COMPONENTS = {"self_review_correct": 1.0, "bug_explanation_quality": 0.9, "stage_efficiency": 0.5}


def _results(tech_ai, tech_tech, debug_score, debug_passed, ai_score, ai_passed, cog_score, cog_passed,
             r4_components=None):
    return {
        "round1_communication": {"score": 0.0, "passed": False},  # must never affect the outcome
        "ai_literacy": {"score": 0.0, "correct": tech_ai, "total": 20, "passed": True},
        "technical_assessment": {"score": 0.0, "correct": tech_tech, "total": 20, "passed": True},
        "round3_debugging": {"score": debug_score, "passed": debug_passed},
        "round4_ai_assisted": {
            "score": ai_score,
            "passed": ai_passed,
            "components": dict(DEFAULT_R4_COMPONENTS if r4_components is None else r4_components),
        },
        "round5_cognitive": {"score": cog_score, "passed": cog_passed},
    }


def test_spark_only():
    # Technical 26/40, debugging failed, AI-assisted solved (>= one of the two), cognitive 0.6 (= Spark's 0.6).
    r = ct.evaluate(_results(13, 13, 0.0, False, 0.6, True, 0.6, True))
    assert r["tier"] == "spark"
    assert r["lpa"] == 4.25


def test_dave_level():
    # Technical 31/40, debugging solved, AI-assisted 0.6, cognitive 0.7 (>= Dave's 0.65).
    r = ct.evaluate(_results(16, 15, 0.7, True, 0.6, True, 0.7, True))
    assert r["tier"] == "dave"
    assert r["lpa"] == 5.75


def test_commit_level():
    # Technical 36/40, debugging 1.0, self-review correct, bug explanation 0.9, cognitive 0.8 (>= 0.75).
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


def test_cognitive_055_with_spark_results_returns_no_tier():
    # Otherwise Spark-qualifying, but 0.55 is below the confirmed 0.6 bar even though
    # round5's own passed flag is True (0.55 clears its old 0.5 cutoff). The numeric score must decide.
    r = ct.evaluate(_results(13, 13, 0.0, False, 0.6, True, 0.55, True))
    assert r["tier"] is None


def test_commit_with_low_stage_efficiency_still_commit():
    # Efficiency 0.0 must not matter: Commit's Round 4 bar uses self-review and bug quality only.
    low_eff = {"self_review_correct": 1.0, "bug_explanation_quality": 0.9, "stage_efficiency": 0.0}
    r = ct.evaluate(_results(18, 18, 1.0, True, 0.4, False, 0.8, True, r4_components=low_eff))
    assert r["tier"] == "commit"


def test_commit_needs_self_review_correct():
    no_self_review = {"self_review_correct": 0.0, "bug_explanation_quality": 1.0, "stage_efficiency": 1.0}
    r = ct.evaluate(_results(18, 18, 1.0, True, 1.0, True, 0.8, True, r4_components=no_self_review))
    assert r["tier"] == "dave"


def test_client_view_whitelists_tier_and_lpa_only():
    stored = ct.evaluate(_results(18, 18, 1.0, True, 0.95, True, 0.8, True))
    stored["computed_at"] = "2026-10-05T00:00:00+00:00"
    view = ct.client_view(stored)
    assert set(view) == {"tier", "lpa"}
    assert view == {"tier": "commit", "lpa": 7.50}
