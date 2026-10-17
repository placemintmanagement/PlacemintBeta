"""Cross-check both copies of the greedy-min-platforms problem --
dave/dsa.py's DAVE_DSA_PROBLEMS entry and banks/problem_bank.py's _RAW
entry -- against a from-scratch brute-force checker on 200 deterministically
seeded random cases, with ties (an arrival exactly equal to another train's
departure) deliberately forced at a high rate.

Context (2026-10 audit, re-verified fresh for this task): an earlier audit
claimed dave/dsa.py's reference_solution used `arr[i] < dep[j]` while
problem_bank.py's used `arr[i] <= dep[j]` (a real divergence at the time).
Since that audit, problem_bank.py's own copy was ALSO changed to the strict
`<` comparison (see test_greedy_min_platforms_fix.py, Stage 2a) -- so as of
this file, BOTH copies use `arr[i] < dep[j]` and BOTH agree with each other
and with the problem's own stated tie rule ("a departure at the same time as
another arrival frees the platform in time" -- i.e. a same-minute
arrival+departure does NOT need an extra platform). dave/dsa.py's own module
docstring still describes the old divergence; that prose is now stale, but
fixing prose is out of scope here -- this file's job is to pin down the
ACTUAL behavior of both reference_solution strings with an independent
checker, not to trust either file's comments.

Both tests below are expected to PASS: there is no known current divergence
between the two implementations, and both match the brute-force checker
on every seeded case. If a future edit reintroduces `<=` in either file, the
corresponding test here fails and names the exact failing case.
"""
import random

import pytest

from banks import problem_bank
from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview.dave.dsa import (
    DAVE_DSA_PROBLEMS,
)

PROBLEM_ID = "greedy-min-platforms"
NUM_CASES = 200
SEED = 20261018  # today's date at authoring time; fixed for determinism


def _dave_reference_solution() -> str:
    return next(p for p in DAVE_DSA_PROBLEMS if p["id"] == PROBLEM_ID)["reference_solution"]


def _bank_reference_solution() -> str:
    return next(r for r in problem_bank._RAW if r["id"] == PROBLEM_ID)["reference_solution"]


def _brute_force_min_platforms(arr, dep) -> int:
    """Obviously-correct-by-construction checker, independent of either
    greedy sweep-line implementation: a train occupies its platform for the
    half-open interval [arrival, departure) -- i.e. it has already vacated
    AT its departure minute, matching the problem's own stated rule that a
    departure frees the platform in time for a same-minute arrival. For
    every arrival instant, directly counts how many trains have an interval
    covering that instant, and returns the max over all arrival instants
    (the busiest moment can only ever be exactly at some train's arrival)."""
    best = 0
    for t in arr:
        count = sum(1 for a, d in zip(arr, dep) if a <= t < d)
        best = max(best, count)
    return best


def _to_stdin(arr, dep) -> str:
    n = len(arr)
    return f"{n}\n" + " ".join(map(str, arr)) + "\n" + " ".join(map(str, dep)) + "\n"


def _random_case(rng: random.Random):
    """n trains with arrival/departure times drawn from a small pool (so
    organic collisions are common on their own), PLUS a deliberate pass
    that forces some trains' arrival times to land exactly on another
    train's departure time (or vice versa) -- the exact boundary the
    `<` vs `<=` comparison governs. Every train's own departure is kept
    strictly after its own arrival (a train can't depart before/at its own
    arrival), so only cross-train ties are introduced."""
    n = rng.randint(1, 12)
    pool = list(range(0, 15))
    arr = [rng.choice(pool) for _ in range(n)]
    dep = [a + rng.randint(1, 10) for a in arr]

    if n >= 2:
        # Force several cross-train ties per case so the <= / < boundary is
        # exercised heavily, not just occasionally.
        for _ in range(max(1, n // 2)):
            if rng.random() < 0.7:
                i, j = rng.sample(range(n), 2)
                if rng.random() < 0.5:
                    # train i's arrival lands exactly on train j's departure
                    arr[i] = dep[j]
                else:
                    # train i's departure lands exactly on train j's arrival
                    dep[i] = arr[j]
                # keep train i's own interval valid (dep strictly > arr)
                if dep[i] <= arr[i]:
                    dep[i] = arr[i] + rng.randint(1, 5)

    return arr, dep


def _build_cases():
    rng = random.Random(SEED)
    cases = []
    for idx in range(NUM_CASES):
        arr, dep = _random_case(rng)
        expected = _brute_force_min_platforms(arr, dep)
        cases.append((idx, arr, dep, expected))
    return cases


CASES = _build_cases()


def _tie_count(arr, dep) -> int:
    """How many (arrival, departure) cross-train ties a case contains --
    used only to assert the generator actually exercises the boundary."""
    dep_set = set(dep)
    return sum(1 for a in arr if a in dep_set)


def test_case_generator_exercises_ties_at_a_high_rate():
    cases_with_ties = sum(1 for _, arr, dep, _ in CASES if _tie_count(arr, dep) > 0)
    assert cases_with_ties >= NUM_CASES * 0.5, (
        f"only {cases_with_ties}/{NUM_CASES} seeded cases contain an arrival==departure "
        "tie -- the generator should force ties far more often than this so the "
        "< vs <= boundary is actually well-exercised, not just occasionally hit"
    )


@pytest.mark.parametrize(
    "idx,arr,dep,expected", CASES, ids=[f"case{c[0]:03d}" for c in CASES]
)
def test_dave_dsa_min_platforms_matches_brute_force(idx, arr, dep, expected):
    stdin = _to_stdin(arr, dep)
    actual = problem_bank._run_ref(_dave_reference_solution(), stdin)
    assert actual == str(expected), (
        f"dave/dsa.py's greedy-min-platforms reference_solution diverged from the "
        f"brute-force checker on seeded case {idx} (arr={arr!r}, dep={dep!r}): "
        f"expected {expected}, got {actual!r}"
    )


@pytest.mark.parametrize(
    "idx,arr,dep,expected", CASES, ids=[f"case{c[0]:03d}" for c in CASES]
)
def test_problem_bank_min_platforms_matches_brute_force(idx, arr, dep, expected):
    stdin = _to_stdin(arr, dep)
    actual = problem_bank._run_ref(_bank_reference_solution(), stdin)
    assert actual == str(expected), (
        f"banks/problem_bank.py's greedy-min-platforms reference_solution diverged from "
        f"the brute-force checker on seeded case {idx} (arr={arr!r}, dep={dep!r}): "
        f"expected {expected}, got {actual!r}"
    )


def test_dave_and_bank_currently_use_the_same_comparison_operator():
    """Documents the CURRENT state explicitly: as of this file, both copies
    use strict `<` and agree with each other, so there is no live
    cross-file divergence to xfail/skip. If this ever fails, dave/dsa.py
    and problem_bank.py have diverged again and whichever side fails
    test_dave_dsa_min_platforms_matches_brute_force /
    test_problem_bank_min_platforms_matches_brute_force above (not
    necessarily both) identifies which one regressed."""
    dave_src = _dave_reference_solution()
    bank_src = _bank_reference_solution()
    assert "arr[i] < dep[j]" in dave_src
    assert "arr[i] < dep[j]" in bank_src
    assert "arr[i] <= dep[j]" not in dave_src
    assert "arr[i] <= dep[j]" not in bank_src
