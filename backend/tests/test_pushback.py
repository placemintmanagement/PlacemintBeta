# -*- coding: utf-8 -*-
"""Unit tests for capgemini_interview/pushback.py (FEATURE B), independent of
server.py wiring -- this module is pure, so these tests call it directly."""
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview import pushback as pb


def test_wrong_answer_enough_words_zero_key_points_triggers_pushback():
    answer = "word " * 20
    assert pb.should_pushback(answer, {"kp0": False, "kp1": False, "kp2": False})


def test_partial_answer_does_not_trigger_pushback():
    answer = "word " * 20
    assert not pb.should_pushback(answer, {"kp0": True, "kp1": False, "kp2": False})


def test_short_answer_under_min_words_does_not_trigger_pushback():
    answer = "word " * (pb.MIN_ATTEMPT_WORDS - 1)
    assert not pb.should_pushback(answer, {"kp0": False})


def test_complexity_rejected_triggers_pushback():
    answer = "word " * 20
    assert pb.should_pushback(answer, {"time_stated": True, "time_correct": False}, "time")


def test_complexity_accepted_does_not_trigger_pushback():
    answer = "word " * 20
    assert not pb.should_pushback(answer, {"time_stated": True, "time_correct": True}, "time")


def test_space_dimension_uses_its_own_key_not_times():
    answer = "word " * 20
    # time_correct True must not leak into a space-dimension check
    assert pb.should_pushback(answer, {"space_stated": True, "space_correct": False,
                                       "time_stated": True, "time_correct": True}, "space")


def test_eligible_stages_are_cs_and_complexity_only():
    assert pb.is_pushback_eligible_stage("cs_fundamentals")
    assert pb.is_pushback_eligible_stage("cs_grilling")
    assert pb.is_pushback_eligible_stage("time_complexity")
    assert pb.is_pushback_eligible_stage("space_complexity")
    for ineligible in ("project1", "project2", "followups", "dsa", "hr", "intro", "project1_followups"):
        assert not pb.is_pushback_eligible_stage(ineligible)


def test_pushback_allowed_respects_once_per_question():
    assert not pb.pushback_allowed(already_pushed_back_this_question=True,
                                   pushbacks_used_this_interview=0, remaining_seconds=600,
                                   budget_exceeded=False)


def test_pushback_allowed_respects_interview_cap():
    assert not pb.pushback_allowed(already_pushed_back_this_question=False,
                                   pushbacks_used_this_interview=pb.MAX_PUSHBACKS_PER_INTERVIEW,
                                   remaining_seconds=600, budget_exceeded=False)


def test_pushback_allowed_respects_two_minute_floor():
    assert not pb.pushback_allowed(already_pushed_back_this_question=False,
                                   pushbacks_used_this_interview=0,
                                   remaining_seconds=pb.PUSHBACK_MIN_REMAINING_SECONDS - 1,
                                   budget_exceeded=False)


def test_pushback_allowed_respects_budget_spent():
    assert not pb.pushback_allowed(already_pushed_back_this_question=False,
                                   pushbacks_used_this_interview=0, remaining_seconds=600,
                                   budget_exceeded=True)


def test_pushback_allowed_true_when_nothing_blocks_it():
    assert pb.pushback_allowed(already_pushed_back_this_question=False,
                               pushbacks_used_this_interview=pb.MAX_PUSHBACKS_PER_INTERVIEW - 1,
                               remaining_seconds=pb.PUSHBACK_MIN_REMAINING_SECONDS + 1,
                               budget_exceeded=False)


def test_pushback_line_never_repeats_back_to_back_over_many_draws():
    rng = random.Random(9)
    previous = None
    for _ in range(500):
        line = pb.pick_pushback_line(rng, previous)
        assert line != previous
        previous = line


def test_lint_catches_every_forbidden_word_in_a_synthetic_line():
    for bad_word, sample in [("wrong", "That's wrong, think again."),
                             ("incorrect", "That was incorrect."),
                             ("not right", "That's not right."),
                             ("no,", "No, try again.")]:
        violations = pb.lint_pushback_line(sample)
        assert violations, f"expected a violation for: {sample!r}"


def test_lint_catches_a_key_point_fragment():
    violations = pb.lint_pushback_line("Think about the hash table bucket again.",
                                       forbidden_fragments=["hash table bucket"])
    assert violations


def test_every_stored_pushback_variant_passes_the_lint():
    for line in pb.PUSHBACK_LINES:
        assert pb.lint_pushback_line(line) == [], line


def test_stored_variant_count_is_within_the_stated_five_to_eight_range():
    assert 5 <= len(pb.PUSHBACK_LINES) <= 8


def test_hint_credit_first_attempt_keeps_full_value():
    credited = pb.apply_hint_credit({"kp0": True}, {"kp0": False})
    assert credited["kp0"] == 1.0


def test_hint_credit_second_attempt_only_earns_partial_value():
    credited = pb.apply_hint_credit({"kp0": False}, {"kp0": True})
    assert credited["kp0"] == pb.HINT_CREDIT


def test_hint_credit_neither_attempt_scores_zero():
    credited = pb.apply_hint_credit({"kp0": False}, {"kp0": False})
    assert credited["kp0"] == 0.0


def test_hint_credit_does_not_double_count_when_both_attempts_hit():
    """A key point found in BOTH attempts still keeps exactly full value, not
    1.0 + HINT_CREDIT -- the first-attempt branch short-circuits."""
    credited = pb.apply_hint_credit({"kp0": True}, {"kp0": True})
    assert credited["kp0"] == 1.0
