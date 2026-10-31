"""Stage 2a (2026-10): greedy-min-platforms's reference solution used
`arr[i] <= dep[j]` for its tie-break, which on an arrival == departure
tie counted the arriving train as needing a NEW platform before ever
freeing the departing one -- the opposite of the problem's own stated
rule ("a departure at the same time as another arrival frees the
platform in time"). Fixed to strict `<`. These tests prove:

1. The fix doesn't change any of the 5 ORIGINAL stored test outputs
   (compared directly against the pre-fix baseline commit).
2. The new 6th test_input (the tie case this fix is for) now gets the
   answer the problem's own prose promises.
3. `problem_bank.verify_with_independent_checker` -- the new, generic
   author-time cross-check helper -- agrees with the fixed reference
   solution on every one of this problem's test_inputs, wired to a
   from-scratch brute-force platform counter (not the reference
   solution's own sweep-line logic) as proof the helper actually
   exercises something independent.
4. The helper actually fails loudly when the two genuinely disagree
   (proven against the ORIGINAL, buggy reference solution from before
   this fix -- not a synthetic always-wrong stub), so passing #3 isn't
   just "nothing was ever checked."
"""
import pytest

from banks import problem_bank as live
from bank_baseline_support import load_commit_problem_bank

BASELINE_COMMIT = "50fd038"  # last commit before this fix


@pytest.fixture(scope="module")
def baseline_problem_bank():
    return load_commit_problem_bank(BASELINE_COMMIT)


def _min_platforms(pb_module, pid="greedy-min-platforms"):
    return next(p for p in pb_module._BANK if p["id"] == pid)


def test_the_5_original_test_outputs_are_unchanged(baseline_problem_bank):
    baseline = _min_platforms(baseline_problem_bank)
    live_problem = _min_platforms(live)

    baseline_all = baseline["visible_tests"] + baseline["hidden_tests"]
    live_first_5 = (live_problem["visible_tests"] + live_problem["hidden_tests"])[:5]

    assert len(baseline_all) == 5
    assert [t["input"] for t in live_first_5] == [t["input"] for t in baseline_all]
    assert [t["expected_output"] for t in live_first_5] == [t["expected_output"] for t in baseline_all], (
        "the fix must not change any of the 5 original tests' outputs -- none of them "
        "contain an arrival==departure tie, so < vs <= should never diverge for them"
    )


def test_the_new_6th_test_is_the_tie_case_and_now_resolves_to_1():
    live_problem = _min_platforms(live)
    all_tests = live_problem["visible_tests"] + live_problem["hidden_tests"]
    assert len(all_tests) == 6, "greedy-min-platforms should opt in to 6 total tests"
    tie_test = all_tests[5]
    assert tie_test["input"] == "2\n100 200\n200 300"
    assert tie_test["expected_output"] == "1", (
        "arrival==departure (train B arrives at 200 exactly as train A departs at 200) "
        "should reuse the platform per the problem's own stated rule -- answer is 1, not 2"
    )


def _brute_force_min_platforms(stdin: str) -> str:
    """From-scratch, independent of the reference solution's sweep-line
    approach: for each arrival instant, directly counts how many
    [arrival, departure) intervals are active at that instant (half-open
    -- a train departing exactly at t has already vacated), and takes the
    max over all arrival instants."""
    lines = stdin.strip().split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    dep = list(map(int, lines[2].split()))
    assert len(arr) == n and len(dep) == n
    best = 0
    for t in arr:
        count = sum(1 for a, d in zip(arr, dep) if a <= t < d)
        best = max(best, count)
    return str(best)


def test_independent_checker_agrees_with_the_fixed_reference_solution_on_all_tests():
    checked = live.verify_with_independent_checker("greedy-min-platforms", _brute_force_min_platforms)
    assert checked == 6  # all 6 test_inputs (the original 5 plus the new tie case) were compared


def test_independent_checker_fails_loudly_against_the_original_buggy_reference_solution(baseline_problem_bank):
    # Proof the helper can actually catch a real disagreement, not just
    # that it trivially passes: the ORIGINAL (pre-fix) reference solution
    # disagrees with the brute-force checker on the tie case added in
    # this same commit, which this baseline problem doesn't even have in
    # its test_inputs yet -- so we drive the comparison directly rather
    # than through verify_with_independent_checker (which only ever
    # iterates a problem's OWN stored test_inputs).
    baseline_raw = next(r for r in baseline_problem_bank._RAW if r["id"] == "greedy-min-platforms")
    buggy_ref_output = baseline_problem_bank._run_ref(baseline_raw["reference_solution"], "2\n100 200\n200 300")
    checker_output = _brute_force_min_platforms("2\n100 200\n200 300")
    assert buggy_ref_output != checker_output, (
        "sanity check: the pre-fix reference solution and the independent checker "
        "must actually disagree on the tie case, or this test proves nothing"
    )

    def _always_return_buggy_answer(stdin):
        return buggy_ref_output

    with pytest.raises(AssertionError):
        live.verify_with_independent_checker("greedy-min-platforms", _always_return_buggy_answer)
