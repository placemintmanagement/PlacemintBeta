# -*- coding: utf-8 -*-
"""Unit tests for capgemini_interview/humanize.py (FEATURE A), independent
of server.py wiring -- this module is pure, so these tests call it directly."""
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview import humanize as h


def test_acknowledgement_never_repeats_back_to_back_over_many_draws():
    rng = random.Random(1)
    previous = None
    seen_any = False
    for _ in range(500):
        line = h.maybe_acknowledgement(rng, previous, is_first_turn_after_intro=False)
        if line is not None:
            assert line != previous
            seen_any = True
            previous = line
    assert seen_any


def test_acknowledgement_never_fires_on_first_turn_after_intro():
    rng = random.Random(2)
    for _ in range(200):
        assert h.maybe_acknowledgement(rng, None, is_first_turn_after_intro=True) is None


def test_acknowledgement_rate_is_roughly_the_stated_probability():
    rng = random.Random(3)
    fired = sum(1 for _ in range(2000) if h.maybe_acknowledgement(rng, None, False) is not None)
    rate = fired / 2000
    assert 0.5 <= rate <= 0.7  # ACK_PROBABILITY is 0.6; allow sampling slack


def test_acknowledgement_signature_cannot_see_grade_or_answer_content():
    """Structural guarantee: the picker function takes no grade/flags/answer
    parameter at all, so it is impossible for it to be influenced by them --
    verified here by introspecting its signature rather than just by
    behaviour, since a signature change would be the first sign of a future
    regression on this guarantee."""
    import inspect
    params = list(inspect.signature(h.maybe_acknowledgement).parameters)
    for forbidden in ("flags", "verdict", "grade", "answer", "correct", "score"):
        assert forbidden not in params


def test_acknowledgement_same_seed_different_grades_identical_lines():
    """Two runs with the same seed and RNG call sequence produce the exact
    same acknowledgement lines regardless of what the (unused) grade would
    have been -- there is nothing for a grade to influence."""
    rng_a = random.Random(7)
    rng_b = random.Random(7)
    lines_a = [h.maybe_acknowledgement(rng_a, None, False) for _ in range(50)]
    lines_b = [h.maybe_acknowledgement(rng_b, None, False) for _ in range(50)]
    assert lines_a == lines_b


def test_stage_transition_never_repeats_back_to_back():
    rng = random.Random(4)
    previous = None
    for _ in range(200):
        line = h.stage_transition_line("dsa", rng, previous)
        assert line != previous
        previous = line


def test_stage_transition_name_variant_can_include_the_name():
    rng = random.Random(5)
    found_name = False
    for _ in range(50):
        line = h.stage_transition_line("hr", rng, None, name="Priya")
        if "Priya" in line:
            found_name = True
    assert found_name


def test_time_remaining_line_shows_correct_minutes():
    minutes = h.minutes_remaining(deadline_epoch=1000, now=1000 - 7 * 60)
    assert minutes == 7
    assert h.time_remaining_line(minutes) == "We have about 7 minutes left."


def test_clarification_request_detected_for_short_utterances():
    for phrase in ("can you repeat that?", "pardon?", "I didn't understand", "what do you mean",
                  "could you rephrase that"):
        assert h.is_clarification_request(phrase)


def test_clarification_request_not_misfired_by_a_long_substantive_answer():
    answer = ("I would repeat this check inside the loop for every element in the array to make sure "
             "nothing is missed before moving on to the next step of the algorithm")
    assert not h.is_clarification_request(answer)


def test_pass_phrase_detected_for_short_utterances():
    for phrase in ("I don't know", "skip", "pass", "no idea", "not sure"):
        assert h.is_pass_phrase(phrase)


def test_pass_phrase_not_misfired_by_a_long_substantive_answer_containing_pass():
    answer = ("I would use a two pointer approach to pass through the array once and track the running "
             "sum as I go, which keeps it at linear time overall")
    assert not h.is_pass_phrase(answer)


def test_rephrase_lookup_returns_stored_line_for_a_known_id():
    line = h.rephrase_for("java-2", fallback_prompt="ORIGINAL")
    assert line != "ORIGINAL"
    assert "immutable" in line.lower() or "string pool" in line.lower()


def test_rephrase_lookup_falls_back_to_original_prompt_for_an_unknown_id():
    line = h.rephrase_for("some-followup-with-no-bank-id", fallback_prompt="ORIGINAL PROMPT TEXT")
    assert line == "ORIGINAL PROMPT TEXT"


def test_rephrase_substitutes_company_name_where_the_template_uses_it():
    line = h.rephrase_for("hr-m1", fallback_prompt="ORIGINAL", company="Capgemini")
    assert "Capgemini" in line
    assert "{company}" not in line


def test_every_rephrase_entry_is_a_non_empty_string():
    assert len(h.REPHRASES) > 0
    for qid, line in h.REPHRASES.items():
        assert isinstance(line, str) and line.strip(), qid
