"""Quality gates (Stage 2b, extended Stage 2c): a sweep over EVERY
problem currently opted into `target_tests` -- greedy-min-platforms
(Stage 2a), the 24 Easy problems (Stage 2b), and the first 42 Medium
problems across batches 1 and 2 (Stage 2c) -- checking:

1. Every one of its test_inputs is valid under the problem's own
   declared constraints (via problem_input_gen.SPECS[...].validate for
   every Easy/Medium problem; a small inline check for
   greedy-min-platforms, which predates problem_input_gen.py and isn't
   part of its registry).
2. The reference solution actually runs within the SAME sandbox timeout
   production grading uses (services.code_runner.run_code,
   DEFAULT_TIMEOUT=5s) -- the real grading code path, not just
   _hydrate's own (also 5s, but separate) _run_ref used at import time.
3. The expected outputs for a problem aren't degenerate: not all the
   same value, and not confined to only 2 distinct values -- either of
   those would mean the test set can't tell a correct submission from a
   broken one.
4. No duplicate inputs within a problem's own test_inputs (the builders
   already dedup at construction time; this re-checks the stored result
   rather than trusting that).
5. Wherever problem_input_gen declares an independent/brute-force
   checker, problem_bank.verify_with_independent_checker is actually run
   against it here (not just assumed to work because it exists) -- for
   problems whose checker is deliberately the naive/slow algorithm (4
   from batch 1: container-water, greedy-merge-intervals, greedy-
   activity-selection, greedy-non-overlapping-removals; 8 more from
   batch 2: greedy-jump-game-ii, greedy-gas-station, greedy-boats-save-
   people, greedy-min-arrows-balloons, greedy-two-city-scheduling,
   graph-topo-sort-lexo, graph-rotten-oranges, dp-longest-common-
   substring -- see each checker's docstring in problem_input_gen.py),
   their large_cases are excluded from JUST this check (see
   LARGE_CASES_EXCLUDED_FROM_CHECKER below), since those large inputs
   are sized at the full constraint ceiling to timeout-differentiate a
   naive GRADED submission from the reference, and running the equally
   -naive (or, for some batch-2 checkers, combinatorially/exponentially
   worse) checker against them would defeat that purpose or simply
   never finish. The reference solution still always runs on every
   stored input regardless; checker correctness for these 12 is instead
   fully covered by the 200-trial differential fuzz on small inputs.
6. Uniqueness, wherever the problem allows a direct check for it:
   two-sum (batch 1) and greedy-gas-station (batch 2) are the only two
   of the opted-in problems whose correct answer is "a valid X" rather
   than boolean/count/a single deterministic value/a canonically-unique
   structure (audited by hand across every opted-in problem -- see each
   stage's commit message for the category breakdown), and both
   explicitly state their own "exactly one X exists" precondition, so
   their stored tests get an explicit uniqueness re-check here.

No model is used anywhere in this file.
"""
import pytest

from banks import problem_bank
from banks import problem_input_gen
from services import code_runner


def _opted_in_ids():
    return sorted(r["id"] for r in problem_bank._RAW if "target_tests" in r)


def _greedy_min_platforms_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    dep = list(map(int, lines[2].split()))
    return len(arr) == n and len(dep) == n and 1 <= n <= 10000


VALIDATORS = {"greedy-min-platforms": _greedy_min_platforms_validate}
for _pid, _spec in problem_input_gen.SPECS.items():
    VALIDATORS[_pid] = _spec.validate

CHECKERS = {pid: spec.checker for pid, spec in problem_input_gen.SPECS.items() if spec.checker is not None}
# greedy-min-platforms also has an independent (brute-force) checker --
# registered and proven separately in test_greedy_min_platforms_fix.py,
# not duplicated here, but counted in the coverage report below.
WITH_CHECKER_IDS = sorted(set(CHECKERS) | {"greedy-min-platforms"})

# 2026-10 follow-up (batch 1) + Stage 2c batch 2: these problems'
# independent checkers are deliberately the naive/slow (or, for a few,
# combinatorially/exponentially worse) algorithm -- see each checker's
# docstring in problem_input_gen.py -- while their large_cases are sized
# at the FULL constraint ceiling specifically so a naive submission
# times out and the reference doesn't (proven directly in
# test_problem_bank_large_input_complexity.py and
# test_problem_bank_batch2_large_input_complexity.py). Running the slow
# checker against that same full-scale input would defeat the large
# case's own purpose, or in several batch-2 cases simply never finish
# (an exhaustive bitmask/combinatorial search has no hope of completing
# at n=500-50000), so it's excluded from JUST the checker-agreement
# check below -- never from the reference-solution run, which always
# executes on every stored input regardless of this exclusion. Checker
# correctness for all of these is instead fully covered by the
# 200-trial differential fuzz on small random inputs, same as every
# other checkered problem.
LARGE_CASES_EXCLUDED_FROM_CHECKER = {
    pid: set(problem_input_gen.SPECS[pid].large_cases or [])
    for pid in (
        # batch 1
        "container-water", "greedy-activity-selection",
        "greedy-merge-intervals", "greedy-non-overlapping-removals",
        # batch 2
        "greedy-jump-game-ii", "greedy-gas-station", "greedy-boats-save-people",
        "greedy-min-arrows-balloons", "greedy-two-city-scheduling",
        "graph-topo-sort-lexo", "graph-rotten-oranges", "dp-longest-common-substring",
    )
}


def _raw_by_id(pid):
    return next(r for r in problem_bank._RAW if r["id"] == pid)


def _hydrated_by_id(pid):
    return next(p for p in problem_bank._BANK if p["id"] == pid)


def test_every_opted_in_problem_has_a_validator_registered():
    missing = [pid for pid in _opted_in_ids() if pid not in VALIDATORS]
    assert missing == [], f"no constraint validator registered for: {missing}"


def test_exactly_67_problems_are_opted_in():
    assert len(_opted_in_ids()) == 67, _opted_in_ids()


@pytest.mark.parametrize("pid", _opted_in_ids())
def test_no_duplicate_inputs_within_a_problem(pid):
    raw = _raw_by_id(pid)
    tests = raw["test_inputs"]
    assert len(tests) == len(set(tests)), f"{pid}: duplicate input(s) among {tests!r}"


@pytest.mark.parametrize("pid", _opted_in_ids())
def test_every_test_input_is_valid_under_its_own_constraints(pid):
    raw = _raw_by_id(pid)
    validate = VALIDATORS[pid]
    for stdin in raw["test_inputs"]:
        assert validate(stdin), f"{pid}: an input failed its own declared constraints: {stdin!r}"


@pytest.mark.parametrize("pid", _opted_in_ids())
def test_reference_solution_runs_within_the_real_sandbox_timeout(pid):
    raw = _raw_by_id(pid)
    ref = raw["reference_solution"]
    for stdin in raw["test_inputs"]:
        result = code_runner.run_code("python", ref, stdin)
        assert not result["timed_out"], f"{pid}: reference solution timed out on {stdin!r}"
        assert result["exit_code"] == 0, (
            f"{pid}: reference solution exited {result['exit_code']} on {stdin!r}: "
            f"{(result.get('stderr') or '')[:200]}"
        )


# Problems whose OWN stated output_format is exactly "YES or NO." have a
# structurally binary output space -- ">2 distinct values" can never be
# satisfied for them no matter how good the generator is, so ">2" is the
# wrong bar for this class. The real degenerate failure mode for a
# boolean-output problem is collapsing to ONE value (e.g. all "YES"),
# not having both -- both values present IS full coverage of the output
# space, so that's the bar used for them instead.
BOOLEAN_OUTPUT_IDS = {
    pid for pid in _opted_in_ids()
    if _raw_by_id(pid).get("output_format") == "YES or NO."
}


@pytest.mark.parametrize("pid", _opted_in_ids())
def test_expected_outputs_are_not_degenerate(pid):
    hydrated = _hydrated_by_id(pid)
    all_tests = hydrated["visible_tests"] + hydrated["hidden_tests"]
    outputs = [t["expected_output"] for t in all_tests]
    distinct = set(outputs)
    if pid in BOOLEAN_OUTPUT_IDS:
        assert distinct == {"YES", "NO"}, (
            f"{pid}: boolean-output problem produced {sorted(distinct)} across {len(outputs)} tests -- "
            f"both YES and NO must actually appear, or a naive always-X submission would pass"
        )
    else:
        assert len(distinct) > 2, (
            f"{pid}: only {len(distinct)} distinct expected output(s) across {len(outputs)} tests "
            f"({sorted(distinct)}) -- this test set can't separate right from wrong code"
        )


@pytest.mark.parametrize("pid", sorted(CHECKERS))
def test_independent_checker_agrees_where_one_exists(pid):
    raw = _raw_by_id(pid)
    exclude = LARGE_CASES_EXCLUDED_FROM_CHECKER.get(pid)
    checked = problem_bank.verify_with_independent_checker(pid, CHECKERS[pid], exclude=exclude)
    expected = len(raw["test_inputs"]) - len(exclude or ())
    assert checked == expected


def test_two_sum_stored_tests_each_have_exactly_one_valid_pair():
    """two-sum promises its own candidate/grader "exactly one solution" --
    explicit uniqueness re-check over its CURRENT stored test_inputs,
    independent of validate() (which also enforces this at generation
    time) so a future direct edit to the stored list can't silently
    reintroduce an ambiguous input."""
    raw = _raw_by_id("two-sum")
    for stdin in raw["test_inputs"]:
        lines = stdin.split("\n")
        n = int(lines[0])
        arr = list(map(int, lines[1].split()))
        target = int(lines[2])
        pair_count = sum(1 for a in range(n) for b in range(a + 1, n) if arr[a] + arr[b] == target)
        assert pair_count == 1, f"two-sum: {stdin!r} has {pair_count} valid pairs, not exactly 1"


def test_gas_station_stored_tests_each_have_exactly_one_valid_start():
    """greedy-gas-station promises its own "exactly one starting index
    exists" -- explicit uniqueness re-check over its CURRENT stored
    test_inputs, independent of validate() (which also enforces this at
    generation time) so a future direct edit to the stored list can't
    silently reintroduce an input with more than one valid start. Uses
    the classic O(n) prefix-sum argmin/tie-count characterization
    directly (not problem_input_gen's own helper) so this check doesn't
    depend on that module's internals staying the same."""
    raw = _raw_by_id("greedy-gas-station")
    for stdin in raw["test_inputs"]:
        lines = stdin.split("\n")
        gas = list(map(int, lines[1].split()))
        cost = list(map(int, lines[2].split()))
        n = len(gas)
        prefix = 0
        best = 0
        ties = 1
        for k in range(1, n):
            prefix += gas[k - 1] - cost[k - 1]
            if prefix < best:
                best = prefix
                ties = 1
            elif prefix == best:
                ties += 1
        assert ties == 1, f"greedy-gas-station: {stdin!r} has {ties} valid starts, not exactly 1"


def test_checker_coverage_report():
    """Not a correctness assertion on its own (the coverage split is a
    judgment call, not a bug if it changes) -- records, for the record,
    which opted-in problems have an independent checker and which
    don't, and sanity-checks the two groups partition all 67 opted-in
    problems (58 with a checker: 37 after batch 1 + the uniqueness/
    checker follow-up, plus one to each of the 21 Medium batch-2
    problems)."""
    opted_in = set(_opted_in_ids())
    without_checker = sorted(opted_in - set(WITH_CHECKER_IDS))
    assert set(WITH_CHECKER_IDS) | set(without_checker) == opted_in
    assert set(WITH_CHECKER_IDS) & set(without_checker) == set()
    total = len(opted_in)
    print(f"\nindependent checker: {len(WITH_CHECKER_IDS)}/{total} problems -- {WITH_CHECKER_IDS}")
    print(f"no independent checker: {len(without_checker)}/{total} problems -- {without_checker}")
