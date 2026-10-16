"""Regression test for the `target_tests` opt-in
(backend/banks/problem_bank.py's `_hydrate`), covering both Stage 2a
(greedy-min-platforms's tie-break fix) and Stage 2b (the 24 Easy
problems moving to seeded-generator-built tests at target_tests=10).

Proves the opt-in stays additive: every problem that does NOT set
`target_tests` in its _RAW entry produces byte-identical
visible_tests/hidden_tests, in the same order, to the bank as it existed
at BASELINE_COMMIT -- same technique test_problem_bank_tcs_regression.py
already uses (loading a historical copy of the module via `git show`
into a standalone module object, isolated from the live one).

The excluded ("intentionally changed") id set is derived DYNAMICALLY
from which live _RAW entries currently carry a `target_tests` key,
rather than hardcoded -- so this test keeps working, unmodified, as
later stages opt more problems in; it only ever asserts "every problem
that ISN'T opted in is untouched," never a fixed list of names.
"""
import pytest

from bank_baseline_support import load_commit_problem_bank

# Pinned to the last commit BEFORE Stage 2a's target_tests opt-in landed,
# not a floating "HEAD" -- see test_problem_bank_tcs_regression.py's own
# BASELINE_COMMIT comment for why floating HEAD silently breaks this once
# this diff itself is committed. Both Stage 2a and Stage 2b diff against
# this SAME baseline (the bank as it was before target_tests existed at
# all), since neither stage touches any problem the other one opted in.
BASELINE_COMMIT = "50fd038"


@pytest.fixture(scope="module")
def baseline_problem_bank():
    return load_commit_problem_bank(BASELINE_COMMIT)


@pytest.fixture(scope="module")
def live_problem_bank():
    from banks import problem_bank as live
    return live


def _opted_in_ids(live_problem_bank) -> set:
    return {r["id"] for r in live_problem_bank._RAW if "target_tests" in r}


def test_every_unopted_problem_is_byte_identical_to_baseline(baseline_problem_bank, live_problem_bank):
    baseline_by_id = {p["id"]: p for p in baseline_problem_bank._BANK}
    live_by_id = {p["id"]: p for p in live_problem_bank._BANK}
    opted_in = _opted_in_ids(live_problem_bank)

    assert set(baseline_by_id) == set(live_by_id), "problem id set changed -- not expected in this stage"

    checked = 0
    for pid, baseline_p in baseline_by_id.items():
        if pid in opted_in:
            continue
        live_p = live_by_id[pid]
        assert live_p["visible_tests"] == baseline_p["visible_tests"], f"{pid}: visible_tests changed"
        assert live_p["hidden_tests"] == baseline_p["hidden_tests"], f"{pid}: hidden_tests changed"
        checked += 1
    assert checked == len(baseline_by_id) - len(opted_in)
    print(f"\nbyte-identical-to-baseline check: {checked} non-opted-in problems confirmed unchanged "
          f"({len(opted_in)} opted into target_tests: {sorted(opted_in)})")


def test_target_tests_field_is_opt_in_only_on_the_expected_67_problems(live_problem_bank):
    EASY_IDS = {
        "two-sum", "reverse-string", "fizzbuzz", "valid-palindrome", "max-subarray-sum",
        "contains-duplicate", "missing-number", "buy-sell-stock", "climb-stairs", "merge-sorted",
        "tree-level-order", "tree-max-depth", "tree-symmetric", "tree-balanced", "tree-invert",
        "tree-min-depth", "greedy-assign-cookies", "string-valid-anagram",
        "string-longest-common-prefix", "string-isomorphic", "string-word-pattern",
        "string-roman-to-integer", "tp-remove-duplicates-sorted", "arr-majority-element",
    }
    MEDIUM_BATCH_1_IDS = {
        "group-anagrams", "longest-substring-no-repeat", "coin-change", "product-except-self",
        "rotate-image", "num-islands", "search-rotated", "container-water", "longest-palindromic",
        "combination-sum-count", "tree-validate-bst", "tree-diameter", "tree-path-sum",
        "tree-kth-smallest-bst", "tree-lca-bst", "tree-sum-root-to-leaf", "tree-right-side-view",
        "greedy-activity-selection", "greedy-merge-intervals", "greedy-non-overlapping-removals",
        "greedy-jump-game",
    }
    MEDIUM_BATCH_2_IDS = {
        "greedy-jump-game-ii", "greedy-gas-station", "greedy-boats-save-people",
        "greedy-min-arrows-balloons", "greedy-two-city-scheduling",
        "graph-connected-components", "graph-cycle-undirected", "graph-cycle-directed",
        "graph-course-schedule", "graph-topo-sort-lexo", "graph-bipartite-check",
        "graph-bfs-shortest-path", "graph-network-delay-time", "graph-rotten-oranges",
        "string-compression", "string-integer-to-roman", "string-count-and-say",
        "string-multiply-strings", "string-zigzag-conversion",
        "dp-longest-common-subsequence", "dp-longest-common-substring",
    }
    assert len(EASY_IDS) == 24
    assert len(MEDIUM_BATCH_1_IDS) == 21
    assert len(MEDIUM_BATCH_2_IDS) == 21
    opted_in = _opted_in_ids(live_problem_bank)
    assert opted_in == EASY_IDS | MEDIUM_BATCH_1_IDS | MEDIUM_BATCH_2_IDS | {"greedy-min-platforms"}
    assert len(opted_in) == 67
    # Medium/Hard stay untouched this stage beyond Stage 2a's one exception
    # and Stage 2c batches 1 and 2's 21 each.
    for r in live_problem_bank._RAW:
        if r["id"] in EASY_IDS:
            assert r["difficulty"] == "Easy"
        elif r["id"] in MEDIUM_BATCH_1_IDS or r["id"] in MEDIUM_BATCH_2_IDS:
            assert r["difficulty"] == "Medium"
        elif r["id"] != "greedy-min-platforms":
            assert "target_tests" not in r


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
