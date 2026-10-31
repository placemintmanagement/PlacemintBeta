"""Tests for the 2026-10 replacement TCS track-classification rules in
services/tcs_tiers.py: Foundation ratio (over 65) + per-problem sandbox
test-pass ratio ({passed, total, solved} -- never a model call), with the
old Advanced-MCQ-based route to Digital removed entirely.

Pure unit tests over tcs_tiers.evaluate()/client_view() -- no database, no
server startup, no model calls, no subagents, no scheduled checks.

Covers every boundary/profile the rule replacement specified: the
Foundation qualify/Digital-Prime boundaries at 32/33 and 38/39 of 65; the
per-problem 50%-pass-ratio boundary at two different total-test counts
(14 and 10, proving the classifier works on ratios, not fixed counts);
Prime via problem 2 solved alone; Prime via both problems at exactly 50%
without problem 2 being solved; Digital via each problem alone at exactly
50%; problem 1 solved but problem 2 at 0% giving Digital, not Prime; a
property sweep proving every Prime profile also meets Digital; Part B
skipped (both the qualified-floors-at-Ninja case and the never-qualified
case); Foundation failing despite perfect coding; the coarse_ratio warning
under 6 tests; that the old Advanced MCQ route is truly gone; and that
nothing about the call shape lets a client set or influence the track.
"""
import inspect
import random

import pytest

from services import tcs_tiers

FOUNDATION_MAX = tcs_tiers.FOUNDATION_MAX  # 65


def _problem(passed: int, total: int) -> dict:
    # Split arbitrarily across visible/hidden -- _problem_result only cares
    # about the passed/total SUM, matching _grade_coding_section's real
    # shape ({"visible": {"passed","total"}, "hidden": {"passed","total"}}).
    return {"visible": {"passed": passed, "total": total}, "hidden": {"passed": 0, "total": 0}}


def _sr(foundation_correct: int, problem_1: tuple = None, problem_2: tuple = None) -> dict:
    sr = {
        "numerical": {"correct": foundation_correct},
        "verbal": {"correct": 0},
        "reasoning": {"correct": 0},
    }
    problems = []
    if problem_1 is not None:
        problems.append(_problem(*problem_1))
    if problem_2 is not None:
        problems.append(_problem(*problem_2))
    if problems:
        sr["coding"] = {"problems": problems}
    return sr


# ---- 1. Foundation boundaries ----------------------------------------------

@pytest.mark.parametrize("correct,expected_qualified", [(32, False), (33, True)])
def test_foundation_qualify_boundary_32_33_of_65(correct, expected_qualified):
    result = tcs_tiers.evaluate(_sr(correct), part_b_attempted=False)
    assert result["qualified"] is expected_qualified
    assert (result["tier"] == tcs_tiers.NOT_QUALIFIED) != expected_qualified


@pytest.mark.parametrize("correct,reaches_digital_or_prime_bar", [(38, False), (39, True)])
def test_foundation_digital_prime_boundary_38_39_of_65(correct, reaches_digital_or_prime_bar):
    # Perfect coding (both problems fully solved) -- the only variable left
    # is whether Foundation clears the Digital/Prime-specific 0.60 bar.
    sr = _sr(correct, problem_1=(10, 10), problem_2=(10, 10))
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    if reaches_digital_or_prime_bar:
        assert result["tier"] == "prime"
    else:
        assert result["tier"] == "ninja"  # qualified (>=32.5) but below the 39-of-65 Digital/Prime bar


# ---- 2. Per-problem 50% boundary at two different total-test counts -------

@pytest.mark.parametrize("passed,total,meets_50pct", [
    (6, 14, False), (7, 14, True), (4, 10, False), (5, 10, True),
])
def test_problem_pass_ratio_boundary_at_different_totals(passed, total, meets_50pct):
    # Foundation fixed high enough to clear the Digital/Prime bar; problem_2
    # fixed at 0% so Digital can only be reached via problem_1 alone here --
    # isolates exactly this one boundary, at two different stored test
    # counts, proving the classifier reads the RATIO, not a fixed count.
    sr = _sr(50, problem_1=(passed, total), problem_2=(0, total))
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    assert result["tier"] == ("digital" if meets_50pct else "ninja")


def test_classifier_uses_ratio_not_fixed_count():
    sr_a = _sr(50, problem_1=(7, 14), problem_2=(0, 14))
    sr_b = _sr(50, problem_1=(5, 10), problem_2=(0, 10))
    result_a = tcs_tiers.evaluate(sr_a, part_b_attempted=True)
    result_b = tcs_tiers.evaluate(sr_b, part_b_attempted=True)
    assert result_a["tier"] == result_b["tier"] == "digital"


# ---- 3. Prime routes --------------------------------------------------------

def test_prime_via_problem_2_solved_alone_with_problem_1_at_zero():
    sr = _sr(50, problem_1=(0, 10), problem_2=(10, 10))
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    assert result["tier"] == "prime"
    assert result["problem_2"]["solved"] is True
    assert "problem 2 solved" in result["reason"]


def test_prime_via_both_problems_exactly_50pct_without_problem_2_solved():
    sr = _sr(50, problem_1=(5, 10), problem_2=(5, 10))
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    assert result["tier"] == "prime"
    assert result["problem_2"]["solved"] is False


# ---- 4. Digital routes ------------------------------------------------------

@pytest.mark.parametrize("problem_1,problem_2", [((5, 10), (0, 10)), ((0, 10), (5, 10))])
def test_digital_via_each_problem_alone_at_exactly_50pct(problem_1, problem_2):
    sr = _sr(50, problem_1=problem_1, problem_2=problem_2)
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    assert result["tier"] == "digital"


def test_problem_1_solved_problem_2_zero_gives_digital_not_prime():
    sr = _sr(50, problem_1=(10, 10), problem_2=(0, 10))
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    assert result["tier"] == "digital"


# ---- 5. Property test: every Prime profile also meets Digital -------------

def test_every_prime_profile_also_meets_digital_condition():
    rng = random.Random(12345)
    checked_prime = 0
    for _ in range(500):
        foundation_correct = rng.randint(0, FOUNDATION_MAX)
        p1_total = rng.choice([5, 7, 10, 14, 20])
        p2_total = rng.choice([5, 7, 10, 14, 20])
        p1_passed = rng.randint(0, p1_total)
        p2_passed = rng.randint(0, p2_total)
        sr = _sr(foundation_correct, problem_1=(p1_passed, p1_total), problem_2=(p2_passed, p2_total))
        result = tcs_tiers.evaluate(sr, part_b_attempted=True)
        if result["tier"] != "prime":
            continue
        checked_prime += 1
        cfg = tcs_tiers.TCS_TRACK_CONFIG
        foundation_ratio = foundation_correct / FOUNDATION_MAX
        p1_ratio = p1_passed / p1_total
        p2_ratio = p2_passed / p2_total
        digital_condition = foundation_ratio >= cfg["DIGITAL_FOUNDATION_MIN"] and (
            p1_ratio >= cfg["DIGITAL_PROBLEM_PASS_RATIO_MIN"] or p2_ratio >= cfg["DIGITAL_PROBLEM_PASS_RATIO_MIN"]
        )
        assert digital_condition, f"Prime profile did not meet Digital's condition: {sr}"
    assert checked_prime > 0, "the random sweep never produced a Prime profile -- widen the ranges"


# ---- 6. Part B skipped -------------------------------------------------------

def test_part_b_skipped_caps_at_ninja_when_foundation_qualifies():
    result = tcs_tiers.evaluate(_sr(50), part_b_attempted=False)
    assert result["tier"] == "ninja"
    assert result["problem_1"] is None
    assert result["problem_2"] is None
    assert "Part B was not attempted" in result["reason"]


def test_part_b_skipped_and_foundation_fails_is_not_qualified():
    result = tcs_tiers.evaluate(_sr(10), part_b_attempted=False)
    assert result["tier"] == tcs_tiers.NOT_QUALIFIED


def test_not_qualified_display_name_is_the_user_specified_phrase():
    # STATED-BY-USER (2026-10): "Below the estimated Foundation cutoff",
    # not "Not Qualified" -- reads as a measurement, not a verdict.
    assert tcs_tiers.TCS_TIER_DISPLAY_NAMES[tcs_tiers.NOT_QUALIFIED] == "Below the estimated Foundation cutoff"


# ---- 7. Foundation fail overrides perfect coding ---------------------------

def test_foundation_fail_with_perfect_coding_is_still_not_qualified():
    sr = _sr(10, problem_1=(10, 10), problem_2=(10, 10))  # 10/65 Foundation, both problems solved
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    assert result["tier"] == tcs_tiers.NOT_QUALIFIED


def test_missing_coding_section_entirely_does_not_crash():
    result = tcs_tiers.evaluate(_sr(50), part_b_attempted=True)  # no "coding" key at all
    assert result["tier"] == "ninja"
    assert result["problem_1"]["total"] == 0
    assert result["problem_2"]["total"] == 0


def test_skipped_problem_counts_as_zero_not_a_crash():
    sr = _sr(50, problem_1=(10, 10))
    sr["coding"]["problems"].append({"skipped": True, "reason": "bad tests"})
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    assert result["problem_2"]["solved"] is False
    assert result["problem_2"]["total"] == 0


# ---- 8. coarse_ratio warning under 6 tests ---------------------------------

def test_coarse_ratio_flag_appears_under_6_tests():
    sr = _sr(50, problem_1=(3, 5), problem_2=(10, 10))
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    assert result["problem_1"].get("coarse_ratio") is True
    assert "coarse_ratio" not in result["problem_2"]  # 10 tests, not coarse


def test_coarse_ratio_does_not_block_the_decision_just_warns():
    sr = _sr(50, problem_1=(3, 5), problem_2=(0, 10))  # 3/5 = 60% pass_ratio, coarse but still counted
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    assert result["tier"] == "digital"
    assert result["problem_1"]["coarse_ratio"] is True


# ---- 9. Sandbox-only shape, no AI fields, no Advanced MCQ route ------------

def test_per_problem_shape_is_sandbox_only_no_ai_fields():
    sr = _sr(50, problem_1=(7, 10), problem_2=(10, 10))
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    for key in ("problem_1", "problem_2"):
        assert set(result[key].keys()) <= {"passed", "total", "solved", "pass_ratio", "coarse_ratio"}


def test_advanced_mcq_section_is_never_read():
    sr_weak = _sr(50, problem_1=(0, 10), problem_2=(0, 10))
    sr_weak["advanced"] = {"correct": 0, "score": 0.0}
    sr_strong = _sr(50, problem_1=(0, 10), problem_2=(0, 10))
    sr_strong["advanced"] = {"correct": 15, "score": 1.0}
    result_weak = tcs_tiers.evaluate(sr_weak, part_b_attempted=True)
    result_strong = tcs_tiers.evaluate(sr_strong, part_b_attempted=True)
    assert result_weak["tier"] == result_strong["tier"], (
        "the Advanced MCQ section's score must never affect the tier -- that route was explicitly removed"
    )


# ---- 10. client_view / reason text -----------------------------------------

def test_client_view_returns_exactly_tier_lpa_lpa_note_reason_qualified():
    # 2026-10, tightened on request: no thresholds, no per-problem {passed,
    # total, solved, pass_ratio} breakdown, no foundation_correct/max, no
    # part_b_attempted -- the `reason` string already carries the raw
    # counts in prose, so nothing else needs to be exposed as a separate
    # structured field.
    sr = _sr(41, problem_1=(0, 10), problem_2=(10, 10))
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    view = tcs_tiers.client_view(result)
    assert set(view.keys()) == {"tier", "lpa", "lpa_note", "reason", "qualified"}
    assert "Foundation 41/65" in view["reason"]  # raw counts still conveyed, just in prose
    assert view["qualified"] is True


def test_client_view_for_not_qualified_has_no_lpa():
    sr = _sr(10)  # well under the qualify floor
    result = tcs_tiers.evaluate(sr, part_b_attempted=False)
    view = tcs_tiers.client_view(result)
    assert set(view.keys()) == {"tier", "lpa", "lpa_note", "reason", "qualified"}
    assert view["tier"] == tcs_tiers.NOT_QUALIFIED
    assert view["lpa"] is None
    assert view["qualified"] is False


def test_reason_text_matches_the_documented_example_shape():
    # The exact example from the rule-replacement spec: "Foundation 41/65;
    # coding problem 2 solved, so estimated Prime."
    sr = _sr(41, problem_1=(0, 10), problem_2=(10, 10))
    result = tcs_tiers.evaluate(sr, part_b_attempted=True)
    assert result["reason"] == "Foundation 41/65; coding problem 2 solved, so estimated Prime."


# ---- 11. The client cannot set or influence the computed track ------------

def test_evaluate_signature_takes_no_client_controlled_tier_input():
    sig = inspect.signature(tcs_tiers.evaluate)
    assert list(sig.parameters) == ["section_results", "part_b_attempted"], (
        "tcs_tiers.evaluate must only take section_results (server-derived "
        "grading) and part_b_attempted -- if a 'tier'/'track' parameter is "
        "ever added, this test will catch it and every call site needs re-auditing."
    )


def test_client_view_signature_takes_only_the_stored_doc():
    sig = inspect.signature(tcs_tiers.client_view)
    assert list(sig.parameters) == ["tier_doc"]
