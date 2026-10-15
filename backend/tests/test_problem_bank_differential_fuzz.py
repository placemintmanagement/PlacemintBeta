"""Differential fuzzing: for every opted-in problem that has an
independent checker -- the 15 Easy problems with one (12 from Stage 2b
plus string-isomorphic/string-word-pattern/greedy-assign-cookies added
in Stage 2c), greedy-min-platforms (Stage 2a), and all 21 Stage 2c
batch-1 Medium problems (added in the uniqueness/checker follow-up) --
compares the reference solution against the checker on FUZZ_TRIALS
fresh seeded random inputs per problem. These are generated on the fly,
never written into the bank's stored test_inputs. Any disagreement
fails loudly with the exact input, per instruction: a real disagreement
here means the reference or the checker is wrong, and that gets
reported, not silently patched.

No model is used anywhere in this file.

Comparison mode: exact string equality is used for every problem below,
never "any valid answer" validity-checking. An audit of all 46 opted-in
problems' output semantics (Stage 2c uniqueness follow-up) found
exactly one case where the "correct" answer isn't inherently unique --
two-sum's indices -- and that is resolved at the SOURCE
(problem_input_gen.py's _two_sum_random now rejection-samples until the
drawn array has exactly one valid pair, matching the problem's own
stated precondition) rather than by loosening this file's comparison.
Every other checkered problem outputs a boolean, a count, a single
deterministic value, or a structurally/mathematically unique answer
(see each problem's checker docstring in problem_input_gen.py, and the
Stage 2c uniqueness-follow-up commit message, for the per-problem
reasoning for the 21 Medium problems specifically) -- none of them has
a legitimate "multiple valid answers" case to begin with, so exact
equality is correct everywhere here.
"""
import random

import pytest

from banks import problem_bank
from banks import problem_input_gen as pig

FUZZ_TRIALS = 200


def _min_platforms_small_random(rng: random.Random) -> str:
    n = rng.randint(1, 8)
    arr = [rng.randint(0, 50) for _ in range(n)]
    dep = [a + rng.randint(1, 20) for a in arr]
    return f"{n}\n" + " ".join(map(str, arr)) + "\n" + " ".join(map(str, dep)) + "\n"


def _min_platforms_checker(stdin: str) -> str:
    """Same brute-force half-open-interval sweep already proven in
    test_greedy_min_platforms_fix.py, reused here for fuzzing."""
    lines = stdin.strip().split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    dep = list(map(int, lines[2].split()))
    best = 0
    for t in arr:
        count = sum(1 for a, d in zip(arr, dep) if a <= t < d)
        best = max(best, count)
    return str(best)


FUZZ_TARGETS = {
    pid: (spec.random_input, spec.checker)
    for pid, spec in pig.SPECS.items() if spec.checker is not None
}
FUZZ_TARGETS["greedy-min-platforms"] = (_min_platforms_small_random, _min_platforms_checker)


def _raw_by_id(pid):
    return next(r for r in problem_bank._RAW if r["id"] == pid)


def test_exactly_37_problems_have_a_checker_to_fuzz():
    assert len(FUZZ_TARGETS) == 37, sorted(FUZZ_TARGETS)


@pytest.mark.parametrize("pid", sorted(FUZZ_TARGETS))
def test_differential_fuzz_reference_vs_checker(pid):
    random_input, checker = FUZZ_TARGETS[pid]
    ref = _raw_by_id(pid)["reference_solution"]
    rng = random.Random(f"fuzz:{pid}")
    for trial in range(FUZZ_TRIALS):
        stdin = random_input(rng)
        ref_out = problem_bank._run_ref(ref, stdin)
        checker_out = str(checker(stdin)).strip()
        assert ref_out == checker_out, (
            f"{pid} trial {trial}/{FUZZ_TRIALS}: reference and checker disagree on "
            f"input {stdin!r} -- reference={ref_out!r} checker={checker_out!r}"
        )
