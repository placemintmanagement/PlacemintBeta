"""Quality gates (Stage 2b, extended Stage 2c): a sweep over EVERY
problem currently opted into `target_tests` -- greedy-min-platforms
(Stage 2a), the 24 Easy problems (Stage 2b), and the first 21 Medium
problems (Stage 2c batch 1) -- checking:

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
   against it here (not just assumed to work because it exists).
6. Uniqueness, wherever the problem allows a direct check for it:
   two-sum is the only one of the 46 opted-in problems whose correct
   answer is "a valid X" rather than boolean/count/a single deterministic
   value/a canonically-unique structure (audited by hand across all 46 --
   see the Stage 2c commit message for the category breakdown), and it
   explicitly states its own "exactly one solution" precondition, so its
   stored tests get an explicit uniqueness re-check here.

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


def _raw_by_id(pid):
    return next(r for r in problem_bank._RAW if r["id"] == pid)


def _hydrated_by_id(pid):
    return next(p for p in problem_bank._BANK if p["id"] == pid)


def test_every_opted_in_problem_has_a_validator_registered():
    missing = [pid for pid in _opted_in_ids() if pid not in VALIDATORS]
    assert missing == [], f"no constraint validator registered for: {missing}"


def test_exactly_46_problems_are_opted_in():
    assert len(_opted_in_ids()) == 46, _opted_in_ids()


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
    checked = problem_bank.verify_with_independent_checker(pid, CHECKERS[pid])
    assert checked == len(raw["test_inputs"])


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


def test_checker_coverage_report():
    """Not a correctness assertion on its own (the coverage split is a
    judgment call, not a bug if it changes) -- records, for the record,
    which opted-in problems have an independent checker and which
    don't, and sanity-checks the two groups partition all 46 opted-in
    problems (37 with a checker after the Stage 2c uniqueness/checker
    follow-up added one to each of the 21 Medium batch-1 problems)."""
    opted_in = set(_opted_in_ids())
    without_checker = sorted(opted_in - set(WITH_CHECKER_IDS))
    assert set(WITH_CHECKER_IDS) | set(without_checker) == opted_in
    assert set(WITH_CHECKER_IDS) & set(without_checker) == set()
    total = len(opted_in)
    print(f"\nindependent checker: {len(WITH_CHECKER_IDS)}/{total} problems -- {WITH_CHECKER_IDS}")
    print(f"no independent checker: {len(without_checker)}/{total} problems -- {without_checker}")
