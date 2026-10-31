"""Tests for the 2026-10 TCS NQT template rebuild (owner-reviewed source
pass). Pure data/unit tests -- no model calls, no database, no server
startup required beyond importing companies.py/services/banks modules
directly. Covers: the updated totals (82 questions / 190 minutes), the
part_b_optional config flag, services/tcs_tiers.py's track-estimate rules
(including the "no Part B -> capped at Ninja" rule), and
tcs_recruitment_process.py's seeded per-attempt coding-profile draw.
"""
import random

import pytest

from companies import get_company
from services import tcs_tiers
from departments.computer_science_and_it.group1_it_services_mass_recruiters.tcs import (
    tcs_recruitment_process as tcs,
)


# ---- Totals (decision #9: 82 questions, 190 minutes) -----------------------

def _tcs():
    cfg = get_company("tcs-nqt")
    assert cfg is not None
    return cfg


def test_total_minutes_is_190():
    cfg = _tcs()
    assert cfg["time_minutes"] == 190
    summed = sum(s["minutes"] for s in cfg["sections"])
    assert summed == 190, f"section minutes sum to {summed}, not time_minutes (190)"


def test_total_questions_is_82():
    cfg = _tcs()
    # "count" is the question/problem count per section; Advanced Coding's 2
    # is a problem count, not an MCQ count, but decision #9 explicitly folds
    # it into "82 questions" as the grand total of all gradeable items.
    summed = sum(s["count"] for s in cfg["sections"])
    assert summed == 82


def test_foundation_sections_unchanged_and_non_optional():
    cfg = _tcs()
    by_key = {s["key"]: s for s in cfg["sections"]}
    for key, count, minutes in (("numerical", 20, 25), ("verbal", 25, 25), ("reasoning", 20, 25)):
        s = by_key[key]
        assert s["count"] == count
        assert s["minutes"] == minutes
        assert not s.get("optional"), f"{key} is Foundation -- must never be optional"
    assert sum(by_key[k]["count"] for k in ("numerical", "verbal", "reasoning")) == 65
    assert sum(by_key[k]["minutes"] for k in ("numerical", "verbal", "reasoning")) == 75


def test_advanced_section_is_10_quant_5_reasoning_and_optional():
    cfg = _tcs()
    advanced = next(s for s in cfg["sections"] if s["key"] == "advanced")
    assert advanced["count"] == 15
    assert advanced["minutes"] == 25
    assert advanced["optional"] is True
    topics = {t["key"]: t["count"] for t in advanced["extra_topics"]}
    assert topics == {"aptitude": 10, "reasoning": 5}


def test_coding_section_is_2_problems_90_minutes_and_optional():
    cfg = _tcs()
    coding = next(s for s in cfg["sections"] if s["key"] == "coding")
    assert coding["count"] == 2
    assert coding["minutes"] == 90
    assert coding["optional"] is True


def test_part_b_optional_flag_is_set():
    assert _tcs()["part_b_optional"] is True


def test_only_part_b_sections_are_optional():
    cfg = _tcs()
    optional_keys = {s["key"] for s in cfg["sections"] if s.get("optional")}
    assert optional_keys == {"advanced", "coding"}


# ---- Coding languages (decision #4) ----------------------------------------

def test_coding_languages_exclude_csharp_and_javascript():
    assert tcs.TCS_CODING_LANGUAGES == ["c", "cpp", "java", "python"]
    assert "csharp" not in tcs.TCS_CODING_LANGUAGES
    assert "c#" not in tcs.TCS_CODING_LANGUAGES
    assert "javascript" not in tcs.TCS_CODING_LANGUAGES


def test_coding_languages_are_a_subset_of_sandbox_support():
    from services.code_runner import SUPPORTED_LANGUAGES
    for lang in tcs.TCS_CODING_LANGUAGES:
        assert lang in SUPPORTED_LANGUAGES, f"{lang} is not in the sandbox's SUPPORTED_LANGUAGES"


# ---- Coding profile draw (decision #4: seeded RNG, 50/50, no repeats) -----

def test_profile_draw_is_deterministic_per_attempt_id():
    r1 = tcs.roll_coding_profile("attempt-abc")
    r2 = tcs.roll_coding_profile("attempt-abc")
    assert r1 == r2


def test_profile_a_is_one_easy_one_medium_profile_b_is_two_medium():
    for attempt_id in ("a1", "a2", "a3", "a4", "a5"):
        roll = tcs.roll_coding_profile(attempt_id)
        assert roll["profile"] in ("A", "B")
        if roll["profile"] == "A":
            assert roll["difficulty_targets"] == ["easy", "medium"]
        else:
            assert roll["difficulty_targets"] == ["medium", "medium"]
        assert len(roll["difficulty_targets"]) == 2  # exactly 2 problems, matches coding count


def test_profile_draw_is_roughly_50_50_over_many_attempts():
    # Statistical sanity check only (INTERPOLATED weight is 50/50) -- not a
    # proof, just confirms neither branch is dead code. 500 draws, generous
    # tolerance (35-65%) to avoid flaking on a legitimate RNG spread.
    profiles = [tcs.roll_coding_profile(f"stat-check-{i}")["profile"] for i in range(500)]
    frac_a = profiles.count("A") / len(profiles)
    assert 0.35 < frac_a < 0.65, f"profile A fraction {frac_a} looks far from 50/50"


def test_apply_coding_profile_only_touches_the_coding_section():
    cfg = _tcs()
    sections = [{**s, "questions": []} for s in cfg["sections"]]
    out = tcs.apply_coding_profile(sections, "attempt-xyz")
    for orig, mutated in zip(sections, out):
        if orig["key"] == "coding":
            assert "difficulty_targets" in mutated
            assert "coding_profile" in mutated
        else:
            # Every other section (including "advanced", which has its own
            # unrelated extra_topics split) is byte-identical to the input --
            # apply_coding_profile must not touch anything but "coding".
            assert orig == mutated


def test_apply_coding_profile_is_a_noop_on_a_list_without_a_coding_key():
    sections = [{"key": "numerical", "questions": []}]
    out = tcs.apply_coding_profile(sections, "attempt-no-coding")
    assert out == sections


# ---- services/tcs_tiers.py --------------------------------------------------
# The full classification-rule test suite (Foundation-ratio + per-problem
# sandbox-pass-ratio based, 2026-10 replacement of the old Advanced-MCQ-based
# rules) lives in its own dedicated file: test_tcs_track_classification.py.
# Only the LPA table's basic shape is re-checked here, since it's unrelated
# to which rule set decides the tier.

def test_lpa_table_has_all_three_paying_tiers_with_ug_and_pg():
    for tier in ("ninja", "digital", "prime"):
        assert "ug" in tcs_tiers.TCS_LPA[tier]
        assert "pg" in tcs_tiers.TCS_LPA[tier]


# ---- problem_bank.py 'easy' difficulty_target (small additive change) -----

def test_sample_problems_easy_target_returns_only_easy():
    from banks.problem_bank import sample_problems
    random.seed(1234)
    picks = sample_problems(3, difficulty_target="easy")
    assert len(picks) == 3
    # Bank has 24 Easy (comfortably more than 3), so no top-up should be needed.
    assert all(p["difficulty"] == "Easy" for p in picks)
