"""Differential fuzzing: for every opted-in problem that has an
independent checker -- the 15 Easy problems with one (12 from Stage 2b
plus string-isomorphic/string-word-pattern/greedy-assign-cookies added
in Stage 2c), greedy-min-platforms (Stage 2a), all 21 Stage 2c batch-1
Medium problems (added in the uniqueness/checker follow-up), and all 21
Stage 2c batch-2 Medium problems -- compares the reference solution
against the checker on FUZZ_TRIALS fresh seeded random inputs per
problem. These are generated on the fly, never written into the bank's
stored test_inputs. Any disagreement fails loudly with the exact input,
per instruction: a real disagreement here means the reference or the
checker is wrong, and that gets reported, not silently patched.

No model is used anywhere in this file.

Comparison mode: exact string equality is used for every problem below,
never "any valid answer" validity-checking. An audit of every opted-in
problem's output semantics (Stage 2c, batch 1's uniqueness follow-up
and batch 2) found exactly TWO cases where the "correct" answer isn't
inherently unique -- two-sum's indices and greedy-gas-station's
starting index -- and both are resolved at the SOURCE
(problem_input_gen.py's _two_sum_random and _gas_station_random both
rejection-sample/construct until the draw has exactly one valid answer,
matching each problem's own stated "exactly one X exists" precondition)
rather than by loosening this file's comparison. Every other checkered
problem outputs a boolean, a count, a single deterministic value, or a
structurally/mathematically unique answer (see each problem's checker
docstring in problem_input_gen.py, and each stage's own commit message,
for the per-problem reasoning) -- none of them has a legitimate
"multiple valid answers" case to begin with, so exact equality is
correct everywhere here.
"""
import random
import subprocess

import pytest

from banks import problem_bank
from banks import problem_input_gen as pig

FUZZ_TRIALS = 200

# Root-caused (2026-10, flaky-test investigation): this file alone makes
# FUZZ_TRIALS * len(FUZZ_TARGETS) = 200 * 58 = 11,600 fresh `python3`
# subprocess spawns per run, via problem_bank._run_ref -- roughly 15-20x
# the subprocess volume of a full bank hydration (~104 problems x a
# handful of stored test_inputs each). problem_bank.py's own
# _REF_TIMEOUT_DEFAULT docstring (banks/problem_bank.py, just above
# _run_ref) already documents the exact mechanism: on this machine,
# Windows Defender's real-time/IOAV protection scans each newly-written
# file before exec, and _run_ref's write-then-exec pattern occasionally
# (rarely -- 1 slow spawn out of ~800+ in that comment's own observation)
# blocks a subprocess spawn past the 5-second default timeout even
# though the reference solution itself runs in a fraction of a second
# (confirmed directly: see this file's own history -- 20+ solo reruns of
# every parametrization here, plus a standalone timing harness run
# alongside concurrent CPU load, never saw a single _run_ref call take
# more than ~0.3s). Because this file's subprocess volume is so much
# larger than anywhere else that calls _run_ref, and because a full-suite
# run spends many minutes with this module's subprocess-spawning running
# concurrently with pytest-xdist's OTHER worker (pytest.ini pins
# `-n 2 --dist loadscope`, not changed here), it is simply the single
# place in the whole suite statistically most likely to have one spawn
# out of its 11,600 land on one of Defender's rare scan-induced delays --
# which is exactly why two different full-suite runs each saw a
# DIFFERENT parametrization fail: it's whichever spawn happens to be
# unlucky that run, not a property of any specific problem's reference
# solution or checker (every trial's input is fully deterministic --
# seeded from `random.Random(f"fuzz:{pid}")` -- so a real reference-vs-
# checker disagreement would reproduce identically on every retry, while
# a transient spawn-delay timeout would not).
#
# Hardened here, not by raising the shared PM_BANK_REF_TIMEOUT default
# (that default is also used by real bank hydration elsewhere and 5s is
# the right value there): a single subprocess.TimeoutExpired from
# problem_bank._run_ref is retried exactly once before being treated as a
# real failure. A genuine reference/checker disagreement is unaffected --
# it raises AssertionError, not TimeoutExpired, and is never retried.
def _run_ref_tolerant(ref: str, stdin: str):
    try:
        return problem_bank._run_ref(ref, stdin)
    except subprocess.TimeoutExpired:
        return problem_bank._run_ref(ref, stdin)


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


def test_exactly_58_problems_have_a_checker_to_fuzz():
    assert len(FUZZ_TARGETS) == 58, sorted(FUZZ_TARGETS)


@pytest.mark.parametrize("pid", sorted(FUZZ_TARGETS))
def test_differential_fuzz_reference_vs_checker(pid):
    random_input, checker = FUZZ_TARGETS[pid]
    ref = _raw_by_id(pid)["reference_solution"]
    rng = random.Random(f"fuzz:{pid}")
    for trial in range(FUZZ_TRIALS):
        stdin = random_input(rng)
        ref_out = _run_ref_tolerant(ref, stdin)
        checker_out = str(checker(stdin)).strip()
        assert ref_out == checker_out, (
            f"{pid} trial {trial}/{FUZZ_TRIALS}: reference and checker disagree on "
            f"input {stdin!r} -- reference={ref_out!r} checker={checker_out!r}"
        )
