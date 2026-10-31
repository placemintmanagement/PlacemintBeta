"""Part 3 of the 4-part TCS restructure: wiring the real
banks/interview_puzzle_bank.py (Part 2) into the puzzle phase, replacing
Part 1's fixed stub. End-to-end through the real server.start_interview /
submit_interview_answer call path, TCS_INTERVIEW_ENABLED on, AI boundary
faked -- no real Mongo, no network, no live AI call.

Covers: puzzle chosen correctly by tier; Ninja never even calls the
provider; the same interview always gets the same puzzle (deterministic,
seeded by interview_id, not by wall-clock/global rng); grading actually
uses the puzzle's stored solution/rubric; and phase weights still sum to
1.0 per tier with the real puzzle wired in.
"""
import asyncio

import pytest

import server
from departments.computer_science_and_it.group1_it_services_mass_recruiters.tcs.tcs_interview import core
from departments.computer_science_and_it.group1_it_services_mass_recruiters.tcs.tcs_interview import orchestration
from departments.computer_science_and_it.group1_it_services_mass_recruiters.tcs.tcs_interview.banks import (
    interview_puzzle_bank as ipb,
)
from tcs_support import TCS_PROJECTS, _answer, _get, _start, _stored, tcs_world  # noqa: F401


def _advance_to_phase(w, iid, target_phase, max_steps=30):
    view = _get(w, iid)
    steps = 0
    while view["status"] == "in_progress" and view["phase"] != target_phase:
        q = view["current_question"]
        view = _answer(w, iid, q["id"], "A clear, specific answer with real detail and reasoning.")
        steps += 1
        if steps > max_steps:
            raise AssertionError(f"never reached phase {target_phase!r}")
    return view


@pytest.mark.parametrize("tier", ["digital", "prime"])
def test_puzzle_is_chosen_from_the_real_bank_and_matches_the_tier(tcs_world, tier):
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    view = _advance_to_phase(tcs_world, iid, "puzzle")
    assert view["phase"] == "puzzle"

    stored = _stored(tcs_world, iid)
    puzzle_q = stored["phase_questions"]["puzzle"][0]
    assert puzzle_q["id"].startswith("tcs-puzzle-")
    bank_id = puzzle_q["id"][len("tcs-puzzle-"):]
    bank_item = ipb.by_id(bank_id)
    assert tier in bank_item["tier_tags"]
    # It's a real bank item, not the Part-1 fixed placeholder.
    assert bank_id != "tcs-puzzle-stub-1"


def test_ninja_run_never_even_calls_the_puzzle_provider(tcs_world, monkeypatch):
    calls = []
    real = ipb.puzzle_question_for_interview

    def spy(tier, interview_id):
        calls.append((tier, interview_id))
        return real(tier, interview_id)

    monkeypatch.setattr(ipb, "puzzle_question_for_interview", spy)
    started = _start(tcs_world, company_id="tcs-nqt", tier="ninja")
    iid = started["interview_id"]
    view = _get(tcs_world, iid)
    while view["status"] == "in_progress":
        q = view["current_question"]
        view = _answer(tcs_world, iid, q["id"], "A clear, specific answer with real detail and reasoning.")
    assert view["status"] == "completed"
    assert calls == [], "the puzzle provider must never be invoked for a Ninja interview"
    stored = _stored(tcs_world, iid)
    assert "puzzle" not in stored["phase_questions"]


@pytest.mark.parametrize("tier", ["digital", "prime"])
def test_same_interview_always_gets_the_same_puzzle_deterministically(tcs_world, tier):
    """Re-deriving the puzzle choice directly from the bank's own seeded
    function, using the SAME interview_id the interview actually started
    with, must reproduce exactly what got stored -- proving the choice is
    a pure, reproducible function of interview_id, not a one-off random
    draw that merely happens to be persisted."""
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    stored = _stored(tcs_world, iid)
    stored_puzzle_question_id = stored["phase_questions"]["puzzle"][0]["id"]

    recomputed = ipb.puzzle_question_for_interview(tier, iid)
    assert recomputed["id"] == stored_puzzle_question_id

    # And repeating the recomputation again changes nothing.
    recomputed_again = ipb.puzzle_question_for_interview(tier, iid)
    assert recomputed_again["id"] == stored_puzzle_question_id


def test_different_interviews_can_get_different_puzzles():
    """Sanity check that the seed actually varies with interview_id (not
    a constant-function bug that would make every interview identical)."""
    ids = {ipb.pick_puzzle_for_interview("digital", f"intv-{i}")["id"] for i in range(10)}
    assert len(ids) > 1


@pytest.mark.parametrize("tier", ["digital", "prime"])
def test_grading_uses_the_puzzles_own_stored_solution_and_rubric(tcs_world, tier):
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    _advance_to_phase(tcs_world, iid, "puzzle")
    stored = _stored(tcs_world, iid)
    puzzle_q = stored["phase_questions"]["puzzle"][0]
    bank_id = puzzle_q["id"][len("tcs-puzzle-"):]
    bank_item = ipb.by_id(bank_id)

    # The exact key_points graded against are the puzzle's own rubric --
    # not some generic placeholder, and not re-derived differently.
    assert puzzle_q["key_points"] == bank_item["rubric_key_points"]

    # Actually answer it and confirm the grading call's prompt included
    # the puzzle's own key points (routed through the normal, spend-
    # controlled ai_service boundary -- the tcs_world fixture's stubbed
    # call_json_gpt is that same boundary, never bypassed).
    view = _get(tcs_world, iid)
    before_calls = len(tcs_world.model.calls)
    _answer(tcs_world, iid, view["current_question"]["id"], "A reasoned answer to the puzzle.")
    assert len(tcs_world.model.calls) == before_calls + 1
    prompt = tcs_world.model.calls[-1]["prompt"]
    first_point_statement = bank_item["rubric_key_points"][0]["statement"]
    assert first_point_statement in prompt


@pytest.mark.parametrize("tier", core.TCS_INTERVIEW_TIERS)
def test_phase_weights_still_sum_to_one_with_the_real_puzzle_wired_in(tier):
    assert round(sum(core.TCS_PHASE_WEIGHTS[tier].values()), 6) == 1.0
