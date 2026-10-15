"""Regression test for Stage 2a's `target_tests` opt-in
(backend/banks/problem_bank.py's `_hydrate`).

Proves the opt-in is additive: every problem that does NOT set
`target_tests` in its _RAW entry produces byte-identical
visible_tests/hidden_tests, in the same order, to the bank as it existed
at BASELINE_COMMIT -- same technique test_problem_bank_tcs_regression.py
already uses (loading a historical copy of the module via `git show`
into a standalone module object, isolated from the live one).

Exactly ONE problem is excluded from the identity check:
greedy-min-platforms, which deliberately changed in this same commit
(its reference solution was fixed and a 6th test_input was added --
test_greedy_min_platforms_fix.py covers that change on its own). Every
other one of the 104 problems must be untouched.
"""
import pytest

from bank_baseline_support import load_commit_problem_bank

# Pinned to the last commit BEFORE Stage 2a's target_tests opt-in landed,
# not a floating "HEAD" -- see test_problem_bank_tcs_regression.py's own
# BASELINE_COMMIT comment for why floating HEAD silently breaks this once
# this diff itself is committed.
BASELINE_COMMIT = "50fd038"

INTENTIONALLY_CHANGED_PROBLEM_IDS = {"greedy-min-platforms"}


@pytest.fixture(scope="module")
def baseline_problem_bank():
    return load_commit_problem_bank(BASELINE_COMMIT)


@pytest.fixture(scope="module")
def live_problem_bank():
    from banks import problem_bank as live
    return live


def test_every_unopted_problem_is_byte_identical_to_baseline(baseline_problem_bank, live_problem_bank):
    baseline_by_id = {p["id"]: p for p in baseline_problem_bank._BANK}
    live_by_id = {p["id"]: p for p in live_problem_bank._BANK}

    assert set(baseline_by_id) == set(live_by_id), "problem id set changed -- not expected in this stage"

    checked = 0
    for pid, baseline_p in baseline_by_id.items():
        if pid in INTENTIONALLY_CHANGED_PROBLEM_IDS:
            continue
        live_p = live_by_id[pid]
        assert live_p["visible_tests"] == baseline_p["visible_tests"], f"{pid}: visible_tests changed"
        assert live_p["hidden_tests"] == baseline_p["hidden_tests"], f"{pid}: hidden_tests changed"
        checked += 1
    assert checked == len(baseline_by_id) - len(INTENTIONALLY_CHANGED_PROBLEM_IDS)


def test_target_tests_field_is_opt_in_only_on_the_one_changed_problem(live_problem_bank):
    opted_in = [r["id"] for r in live_problem_bank._RAW if "target_tests" in r]
    assert opted_in == ["greedy-min-platforms"]


def test_default_target_tests_reproduces_the_original_tests_2_5_slice(live_problem_bank):
    # Direct unit check of _hydrate's default behavior, independent of
    # the baseline-diff comparison above: a raw entry with NO
    # target_tests key must hydrate exactly as the old hardcoded
    # `tests[2:5]` slice would have.
    raw = {
        "id": "t-default", "title": "t", "difficulty": "Easy", "topic": "arrays",
        "statement": "s", "input_format": "i", "output_format": "o", "constraints": "c",
        "reference_solution": "print(input())\n",
        "test_inputs": ["1", "2", "3", "4", "5", "6", "7"],
    }
    hydrated = live_problem_bank._hydrate(raw)
    assert [t["input"] for t in hydrated["visible_tests"]] == ["1", "2"]
    assert [t["input"] for t in hydrated["hidden_tests"]] == ["3", "4", "5"]  # tests[2:5] -- 6 and 7 unused


def test_target_tests_opt_in_widens_only_the_hidden_slice(live_problem_bank):
    raw = {
        "id": "t-optin", "title": "t", "difficulty": "Easy", "topic": "arrays",
        "statement": "s", "input_format": "i", "output_format": "o", "constraints": "c",
        "reference_solution": "print(input())\n",
        "test_inputs": ["1", "2", "3", "4", "5", "6", "7"],
        "target_tests": 7,
    }
    hydrated = live_problem_bank._hydrate(raw)
    assert [t["input"] for t in hydrated["visible_tests"]] == ["1", "2"]
    assert [t["input"] for t in hydrated["hidden_tests"]] == ["3", "4", "5", "6", "7"]
