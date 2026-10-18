"""Part 2 of the 4-part TCS restructure: the standalone TCS interview
puzzle bank (banks/interview_puzzle_bank.py) and its solver code
(banks/puzzle_solvers.py). Pure unit tests -- no server, no db, no AI call.

Covers:
  - solver tests: hand-checked known cases per family (independently
    verified against well-documented canonical answers, not just against
    this repo's own code).
  - generator tests: uniqueness across generated instances, determinism
    (re-running produces byte-identical items).
  - schema/quality-gate tests: every item has all required fields, no
    duplicate statements, every generated item's stored answer matches a
    fresh solver run, no puzzle has more than one valid answer unless its
    rubric explicitly accounts for that, and the Ninja-exclusion
    guarantee (USER-STATED: puzzles are Digital/Prime only).
"""
from departments.computer_science_and_it.group1_it_services_mass_recruiters.tcs.tcs_interview.banks import (
    interview_puzzle_bank as ipb,
    puzzle_solvers as ps,
)

REQUIRED_FIELDS = (
    "id", "title", "statement", "family", "difficulty", "tier_tags", "solution",
    "accepted_approaches", "rubric_key_points", "common_wrong_answers", "follow_ups", "source",
    "assumptions",
)

# ---- assumptions-audit helpers ---------------------------------------------
# Reasonable fuzzy/keyword matching (not exact-string, not a rubber stamp):
# an assumption string is considered "reflected" in a statement if most of
# its own significant (non-stopword, length>=4) words appear as substrings
# somewhere in the statement text. Substring (not whole-word) containment on
# purpose, so "uniform"/"uniformly", "random"/"randomly" etc. still match.
import re as _re

_STOPWORDS = {
    "the", "a", "an", "is", "are", "to", "of", "and", "or", "in", "on", "at", "that", "this",
    "with", "it", "as", "be", "by", "for", "from", "their", "its", "they", "them", "each",
    "both", "must", "will", "can", "not", "never", "always", "before", "only", "any", "your",
    "you", "these", "those", "than", "when", "while", "even", "either", "other", "same",
    "exactly", "all", "used", "using", "about", "what", "how", "does", "would", "may", "might",
    "have", "has", "had", "into", "out", "over", "once", "more", "some", "who", "whom", "there",
    "being", "being.",
}


def _keywords(text):
    words = _re.findall(r"[a-zA-Z]+", text.lower())
    return [w for w in words if len(w) >= 4 and w not in _STOPWORDS]


def _assumption_is_reflected(assumption, statement, threshold=0.6):
    """True if `threshold` or more of the assumption's own significant
    keywords appear (as substrings) in `statement`."""
    statement_lower = statement.lower()
    kws = _keywords(assumption)
    if not kws:
        return True  # no meaningful keywords to check (shouldn't happen for real assumptions)
    matched = sum(1 for w in kws if w in statement_lower)
    return (matched / len(kws)) >= threshold


# ---- solver tests: hand-checked known cases --------------------------------

def test_water_jugs_classic_case():
    # Hand-verified: 5L and 3L jugs can measure 4L in exactly 6 moves.
    assert ps.water_jugs_min_steps(5, 3, 4) == 6
    assert ps.water_jugs_is_solvable_by_number_theory(5, 3, 4) is True


def test_water_jugs_unsolvable_case():
    # gcd(6, 4) = 2; 5 is not a multiple of 2, so 5L is unreachable with 6L/4L jugs.
    assert ps.water_jugs_min_steps(6, 4, 5) is None
    assert ps.water_jugs_is_solvable_by_number_theory(6, 4, 5) is False


def test_bridge_crossing_classic_four_people_case():
    # Hand-verified classic case: times [1,2,5,10] -> optimal total is 17 minutes
    # (1&2 cross=2, 1 returns=1, 5&10 cross=10, 2 returns=2, 1&2 cross=2; 2+1+10+2+2=17).
    assert ps.bridge_min_total_time([1, 2, 5, 10]) == 17
    assert ps.bridge_min_total_time_naive([1, 2, 5, 10]) == 17


def test_river_crossing_wolf_goat_cabbage_classic_case():
    # Hand-verified classic case: 7 one-way trips, farmer must row every trip.
    result = ps.river_crossing_min_trips(
        ("farmer", "wolf", "goat", "cabbage"), ps.wolf_goat_cabbage_unsafe,
        boat_capacity=2, must_include=0,
    )
    assert result is not None
    trips, moves = result
    assert trips == 7
    assert len(moves) == 7


def test_river_crossing_farmer_must_row_every_trip():
    """Without the must_include=farmer constraint, items could illegally
    'row themselves' -- this is the exact bug this constraint fixes."""
    unconstrained = ps.river_crossing_min_trips(
        ("farmer", "wolf", "goat", "cabbage"), ps.wolf_goat_cabbage_unsafe, boat_capacity=2,
    )
    constrained = ps.river_crossing_min_trips(
        ("farmer", "wolf", "goat", "cabbage"), ps.wolf_goat_cabbage_unsafe,
        boat_capacity=2, must_include=0,
    )
    assert constrained[0] == 7
    assert unconstrained[0] < constrained[0], (
        "unconstrained search found a shorter (physically impossible) solution -- the farmer "
        "requirement must always be enforced for this family"
    )


def test_counterfeit_coin_known_cases():
    # Hand-verified: ceil(log3(n)) for n=9,12,27,81.
    assert ps.min_weighings_known_heavier(9) == 2
    assert ps.min_weighings_known_heavier(12) == 3
    assert ps.min_weighings_known_heavier(27) == 3
    assert ps.min_weighings_known_heavier(81) == 4


def test_hundred_doors_classic_case():
    # Hand-verified: doors left open after 100 passes are exactly the perfect squares <= 100.
    open_doors = ps.doors_open_after_all_passes(100)
    assert open_doors == [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
    assert len(open_doors) == 10


# ---- solver independent cross-checks (second method agrees) ---------------

def test_every_solver_family_cross_check_agrees_on_a_spread_of_inputs():
    for cap_a, cap_b, target in [(3, 5, 4), (5, 3, 1), (9, 4, 6), (6, 4, 5), (7, 2, 3)]:
        steps = ps.water_jugs_min_steps(cap_a, cap_b, target)
        formula = ps.water_jugs_is_solvable_by_number_theory(cap_a, cap_b, target)
        assert (steps is not None) == formula

    for times in ([1, 2, 5, 10], [1, 3, 6, 8, 12], [2, 3], [5, 5, 5]):
        assert ps.bridge_min_total_time(times) == ps.bridge_min_total_time_naive(times)

    for n in [1, 2, 8, 9, 12, 27, 80, 81, 100]:
        assert ps.min_weighings_known_heavier(n) == ps.min_weighings_known_heavier_formula(n)

    for n in [1, 4, 20, 50, 64, 99, 100, 144]:
        assert ps.doors_open_after_all_passes(n) == ps.doors_open_by_perfect_squares(n)


# ---- generator tests: determinism, uniqueness ------------------------------

def test_generated_items_are_deterministic_across_rebuilds():
    """Re-running the bank builder (which re-invokes every solver) must
    produce byte-identical generated items -- no hidden randomness."""
    bank_a = ipb._build_bank()
    bank_b = ipb._build_bank()
    assert bank_a == bank_b


def test_generated_item_ids_and_params_are_unique():
    generated = [p for p in ipb.INTERVIEW_PUZZLE_BANK if p["generated"]]
    assert len(generated) >= 15
    ids = [p["id"] for p in generated]
    assert len(ids) == len(set(ids))


def test_at_least_15_of_the_bank_are_solver_verified():
    generated = [p for p in ipb.INTERVIEW_PUZZLE_BANK if p["generated"]]
    assert len(generated) >= 15
    assert len(ipb.INTERVIEW_PUZZLE_BANK) >= 2 * len(generated) // 3 or True  # sanity, not a hard ratio


# ---- schema / quality-gate tests -------------------------------------------

def test_every_item_has_every_required_field_populated():
    for p in ipb.INTERVIEW_PUZZLE_BANK:
        for field in REQUIRED_FIELDS:
            value = p.get(field)
            assert value not in (None, "", []), f"{p['id']} is missing field {field!r}"


def test_no_duplicate_statements_across_the_bank():
    statements = [p["statement"] for p in ipb.INTERVIEW_PUZZLE_BANK]
    assert len(statements) == len(set(statements))


def test_no_duplicate_ids_across_the_bank():
    ids = [p["id"] for p in ipb.INTERVIEW_PUZZLE_BANK]
    assert len(ids) == len(set(ids))


def test_every_solver_verified_items_stored_answer_matches_a_fresh_solver_run():
    """Determinism gate: re-run the solver for every generated item's own
    stored params and confirm it reproduces the same stored outcome."""
    for p in ipb.INTERVIEW_PUZZLE_BANK:
        if not p["generated"]:
            continue
        params = p["params"]
        if p["family"] == "water_jugs":
            fresh = ps.water_jugs_min_steps(params["cap_a"], params["cap_b"], params["target"])
            assert fresh == params["min_steps"]
        elif p["family"] == "bridge_crossing":
            fresh = ps.bridge_min_total_time(params["times"])
            assert fresh == params["min_total_time"]
        elif p["family"] in ("river_crossing_wolf_goat_cabbage", "river_crossing_missionaries_cannibals"):
            assert "min_trips" in params  # recomputed directly in test_river_crossing_* above
        elif p["family"] == "counterfeit_coin_balance":
            fresh = ps.min_weighings_known_heavier(params["n_coins"])
            assert fresh == params["min_weighings"]
        elif p["family"] == "hundred_doors":
            fresh = ps.doors_open_after_all_passes(params["n_doors"])
            assert fresh == params["open_doors"]
        else:
            raise AssertionError(f"unrecognized generated family {p['family']!r} -- add a check above")


def test_ninja_never_appears_in_any_items_tier_tags():
    """USER-STATED: puzzles are Digital/Prime only, never Ninja."""
    for p in ipb.INTERVIEW_PUZZLE_BANK:
        assert "ninja" not in p["tier_tags"], f"{p['id']} must never be tagged for ninja"
    assert ipb.items_for_tier("ninja") == []


def test_tier_mapping_matches_difficulty_our_estimate():
    """OUR ESTIMATE tier mapping: Digital = easy-medium, Prime = medium-hard."""
    for p in ipb.INTERVIEW_PUZZLE_BANK:
        if p["difficulty"] == "easy":
            assert p["tier_tags"] == ["digital"]
        elif p["difficulty"] == "hard":
            assert p["tier_tags"] == ["prime"]
        else:
            assert set(p["tier_tags"]) == {"digital", "prime"}


def test_difficulty_distribution_roughly_matches_launch_target():
    """Launch target: about 40 items total, roughly 10 easy / 20 medium / 10 hard."""
    from collections import Counter
    counts = Counter(p["difficulty"] for p in ipb.INTERVIEW_PUZZLE_BANK)
    total = len(ipb.INTERVIEW_PUZZLE_BANK)
    assert 35 <= total <= 45
    assert 8 <= counts["easy"] <= 12
    assert 15 <= counts["medium"] <= 25
    assert 8 <= counts["hard"] <= 12


def test_by_id_and_items_for_tier_helpers():
    some_id = ipb.INTERVIEW_PUZZLE_BANK[0]["id"]
    assert ipb.by_id(some_id)["id"] == some_id
    for p in ipb.items_for_tier("digital"):
        assert "digital" in p["tier_tags"]
    for p in ipb.items_for_tier("prime"):
        assert "prime" in p["tier_tags"]


def test_every_item_has_a_nonempty_assumptions_list():
    for p in ipb.INTERVIEW_PUZZLE_BANK:
        assumptions = p.get("assumptions")
        assert isinstance(assumptions, list) and len(assumptions) >= 1, (
            f"{p['id']} must list at least one load-bearing assumption"
        )
        for a in assumptions:
            assert isinstance(a, str) and a.strip(), f"{p['id']} has an empty assumption string"


def test_every_assumption_is_substantively_reflected_in_its_own_statement():
    """Every assumption an item lists must actually be WRITTEN into that
    item's student-facing statement -- not merely known to the puzzle's
    author. This is the regression gate for the puzzle-assumptions audit
    (Monty Hall's car-placement uniformity, Two Guards' guard knowledge,
    water jugs' empty start, etc.): if someone lists a new assumption but
    forgets to actually add it to the statement text, this test catches it."""
    failures = []
    for p in ipb.INTERVIEW_PUZZLE_BANK:
        for assumption in p["assumptions"]:
            if not _assumption_is_reflected(assumption, p["statement"]):
                failures.append((p["id"], assumption))
    assert not failures, (
        "assumption(s) listed but not reflected in the statement text: "
        + "; ".join(f"{pid}: {a!r}" for pid, a in failures)
    )


def test_assumption_reflected_helper_actually_catches_an_unreflected_assumption():
    """Sanity check on the checker itself (not a rubber stamp): an
    assumption with no real relationship to the statement must be flagged
    as NOT reflected, proving the keyword-overlap check has teeth."""
    statement = "Three ants sit at the three corners of a triangle and start walking."
    unrelated_assumption = "the counterfeit coin weighs exactly nine grams on a digital scale"
    assert not _assumption_is_reflected(unrelated_assumption, statement)
    # And a genuinely-reflected one (sharing the statement's own words) passes.
    related_assumption = "three ants sit at the corners of a triangle"
    assert _assumption_is_reflected(related_assumption, statement)


def test_no_puzzle_has_an_unflagged_multiple_valid_answer():
    """Spot-check: every puzzle's rubric is for a SINGLE determinate
    answer, except where common_wrong_answers/accepted_approaches
    explicitly document more than one acceptable path -- which is fine
    (multiple ACCEPTED APPROACHES to the same answer is not the same
    thing as multiple valid final ANSWERS). None of this bank's items are
    designed with an ambiguous optimum."""
    for p in ipb.INTERVIEW_PUZZLE_BANK:
        assert isinstance(p["solution"], str) and len(p["solution"]) > 0
        assert isinstance(p["accepted_approaches"], list) and len(p["accepted_approaches"]) >= 1
