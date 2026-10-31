# -*- coding: utf-8 -*-
"""Pure unit tests for dsa_hints.py -- STAGE 2 of the DSA-hints build
(detection + dispensing + penalty maths). No server, no DB, no event loop,
no model call possible even in principle (the module itself makes none).

Exercises the phrase banks DIRECTLY (dsa_hints.HINT_PHRASES etc.) rather than
a hand-duplicated list, so every phrase the module actually matches on is
covered, and the bank's own size (24 hint phrases, 17 answer-request, 16
confirmation -- all well over the "at least 12" ask, each including the
Hinglish examples for the hint bank) is what's being asserted against."""
import random

import pytest

from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview import (
    dsa_hints,
)


# ---- Phrase-bank coverage (>= 12 phrasings per type, incl. Hinglish for hint) -
@pytest.mark.parametrize("phrase", dsa_hints.HINT_PHRASES)
def test_every_hint_phrase_classifies_as_hint(phrase):
    assert dsa_hints.classify_dsa_message(phrase) == "hint"
    assert dsa_hints.classify_dsa_message(phrase.upper()) == "hint"  # case-insensitive


@pytest.mark.parametrize("phrase", dsa_hints.ANSWER_REQUEST_PHRASES)
def test_every_answer_request_phrase_classifies_as_answer_request(phrase):
    assert dsa_hints.classify_dsa_message(phrase) == "answer_request"


@pytest.mark.parametrize("phrase", dsa_hints.CONFIRMATION_PHRASES)
def test_every_confirmation_phrase_classifies_as_confirmation(phrase):
    assert dsa_hints.classify_dsa_message(phrase) == "confirmation"


def test_at_least_twelve_phrasings_per_type():
    assert len(dsa_hints.HINT_PHRASES) >= 12
    assert len(dsa_hints.ANSWER_REQUEST_PHRASES) >= 12
    assert len(dsa_hints.CONFIRMATION_PHRASES) >= 12
    assert any("dijiye" in p or "karo" in p or "do" in p for p in dsa_hints.HINT_PHRASES)  # Hinglish present


# ---- False positives: real content must never be swallowed as a hint request -
def test_code_with_hint_in_comment_is_an_attempt_not_a_hint():
    text = "def solve(a):\n    # hint: skip duplicates by tracking seen values\n    return len(set(a))"
    assert dsa_hints.classify_dsa_message(text) is None


def test_long_substantive_approach_ending_in_a_hint_question_is_an_attempt():
    text = ("I would track every value I have already seen in a hash set, and the moment a new value is "
            "already present in that set I know it is a duplicate and can return true immediately, any hint?")
    assert len(text.split()) >= 15
    assert dsa_hints.classify_dsa_message(text) is None


def test_short_real_code_snippet_is_an_attempt():
    assert dsa_hints.classify_dsa_message("```\nreturn len(set(a)) != len(a)\n```") is None


def test_for_loop_snippet_is_an_attempt():
    text = "for i in range(len(a)):\n    pass"
    assert dsa_hints.classify_dsa_message(text) is None


def test_empty_or_whitespace_message_is_not_classified():
    assert dsa_hints.classify_dsa_message("") is None
    assert dsa_hints.classify_dsa_message("   ") is None


def test_unmatched_short_chatter_falls_through_to_none():
    assert dsa_hints.classify_dsa_message("ok sounds good") is None


# ---- is_dsa_solving_question ------------------------------------------------
@pytest.mark.parametrize("qid,expected", [
    ("spark-dsa", True), ("dave-dsa", True), ("commit-dsa", True), ("commit-dsa-efficiency", True),
    ("spark-dsa-complexity", False), ("dave-time-complexity", False), ("commit-time-complexity", False),
    ("spark-project", False), (None, False), ("", False),
])
def test_is_dsa_solving_question(qid, expected):
    assert dsa_hints.is_dsa_solving_question(qid) is expected


# ---- Ladder dispensing: order, no repeat, per-tier limit, exhausted line ----
def test_hints_dispensed_in_order_no_repeat_spark():
    pid = "contains-duplicate"
    ladder = dsa_hints.SPARK_DSA_HINTS[pid]
    rng = random.Random(1)
    seen_levels = []
    for used in range(len(ladder)):
        result = dsa_hints.handle_dsa_message("spark", "any hint please", pid, used, rng)
        assert result["kind"] == "hint"
        assert ladder[used] in result["reply"]
        seen_levels.append(ladder[used])
    assert seen_levels == ladder  # L1 then L2 then L3, never repeated


def test_per_tier_limit_commit_stops_at_two_even_though_ladder_has_three():
    pid = "product-except-self"  # Commit reuses Dave's bank
    rng = random.Random(2)
    r0 = dsa_hints.handle_dsa_message("commit", "give me a hint", pid, 0, rng)
    r1 = dsa_hints.handle_dsa_message("commit", "give me a hint", pid, 1, rng)
    r2 = dsa_hints.handle_dsa_message("commit", "give me a hint", pid, 2, rng)
    assert [r0["kind"], r1["kind"]] == ["hint", "hint"]
    assert r2["kind"] == "hint_exhausted"
    assert r2["reply"] == dsa_hints.HINTS_EXHAUSTED_REPLY
    assert r2["hints_used"] == 2  # unchanged -- exhausted request never increments


def test_per_tier_limit_spark_allows_all_three_levels():
    pid = "contains-duplicate"
    rng = random.Random(3)
    for used in range(3):
        result = dsa_hints.handle_dsa_message("spark", "any hint", pid, used, rng)
        assert result["kind"] == "hint"
    exhausted = dsa_hints.handle_dsa_message("spark", "any hint", pid, 3, rng)
    assert exhausted["kind"] == "hint_exhausted"


def test_dave_allows_all_three_levels_too():
    pid = "search-rotated"
    rng = random.Random(4)
    for used in range(3):
        result = dsa_hints.handle_dsa_message("dave", "any hint", pid, used, rng)
        assert result["kind"] == "hint"
    exhausted = dsa_hints.handle_dsa_message("dave", "any hint", pid, 3, rng)
    assert exhausted["kind"] == "hint_exhausted"


def test_hint_limits_constant_matches_spec():
    assert dsa_hints.HINT_LIMITS == {"spark": 3, "dave": 3, "commit": 2}


def test_lead_in_is_at_most_twelve_words_and_never_repeats_back_to_back():
    for line in dsa_hints.HINT_LEAD_INS:
        assert len(line.split()) <= 12
    rng = random.Random(5)
    previous = None
    for _ in range(50):
        chosen = dsa_hints.pick_lead_in(rng, previous)
        if len(dsa_hints.HINT_LEAD_INS) > 1:
            assert chosen != previous
        previous = chosen


def test_answer_request_and_confirmation_replies_are_fixed_and_neutral():
    rng = random.Random(6)
    r = dsa_hints.handle_dsa_message("spark", "just tell me the answer", "contains-duplicate", 0, rng)
    assert r == {"kind": "answer_request", "reply": dsa_hints.ANSWER_REFUSAL, "hints_used": 0,
                "lead_in": None, "is_hint": False, "text": None}
    r2 = dsa_hints.handle_dsa_message("spark", "is this right", "contains-duplicate", 0, rng)
    assert r2 == {"kind": "confirmation", "reply": dsa_hints.CONFIRMATION_REPLY, "hints_used": 0,
                 "lead_in": None, "is_hint": False, "text": None}


def test_fixed_replies_never_say_right_or_wrong():
    for text in (dsa_hints.ANSWER_REFUSAL, dsa_hints.CONFIRMATION_REPLY, dsa_hints.HINTS_EXHAUSTED_REPLY):
        lowered = text.lower()
        for bad in ("right", "wrong", "correct", "incorrect"):
            assert bad not in lowered


def test_unknown_problem_id_fails_safe_to_exhausted_rather_than_crash():
    rng = random.Random(7)
    result = dsa_hints.handle_dsa_message("spark", "give me a hint", "no-such-problem", 0, rng)
    assert result["kind"] == "hint_exhausted"


def test_a_genuine_attempt_returns_none_regardless_of_tier_or_problem():
    rng = random.Random(8)
    text = "A hash set tracks seen values so each new element is checked in constant time against it."
    assert dsa_hints.handle_dsa_message("spark", text, "contains-duplicate", 0, rng) is None


# ---- Scoring penalty maths ---------------------------------------------------
def test_apply_hint_penalty_math():
    assert dsa_hints.apply_hint_penalty(0.8, 2) == pytest.approx(0.8 * 0.8)  # 1 - 0.1*2 = 0.8


def test_apply_hint_penalty_one_hint():
    assert dsa_hints.apply_hint_penalty(1.0, 1) == pytest.approx(0.9)


def test_apply_hint_penalty_floor_never_drops_below_half():
    # hypothetically many hints -- the floor still holds even though no real
    # tier can reach this many (Dave/Spark cap at 3, Commit at 2).
    assert dsa_hints.apply_hint_penalty(1.0, 100) == pytest.approx(0.5)


def test_apply_hint_penalty_noop_cases():
    assert dsa_hints.apply_hint_penalty(None, 3) is None
    assert dsa_hints.apply_hint_penalty(0.7, 0) == 0.7


def test_apply_hint_penalty_never_touches_other_scores_itself():
    # The function is pure and score-component-agnostic -- the "only this
    # stage" guarantee is enforced by WHERE server.py calls it (the DSA
    # component alone), not by anything in this function; this test just
    # pins the pure-function contract: one float in, one float out.
    out = dsa_hints.apply_hint_penalty(0.42, 1)
    assert isinstance(out, float)
