"""Direct proof (2026-10 follow-up) that, for the 4 problems whose
independent checker is deliberately the naive/slow algorithm
(container-water, greedy-activity-selection, greedy-merge-intervals,
greedy-non-overlapping-removals), the REFERENCE solution passes within
the real production sandbox timeout on that problem's full-scale large
input while an equally-naive O(n^2) "submission" does not. This is what
justifies restoring those 3 large_cases definitions (one shared between
the latter two) to the problem's full stated constraint ceiling -- they
had been briefly shrunk to n=2000 so the newly-added independent checker
could verify them directly, which traded away the very timeout-gap
demonstration these large_cases exist for (see
test_problem_bank_opted_in_quality_gates.py's
LARGE_CASES_EXCLUDED_FROM_CHECKER for how that checker-vs-large-input
tension is resolved instead -- by excluding these specific inputs from
the CHECKER check only, never from the reference run).

Uses services.code_runner.run_code directly -- the exact same function
and DEFAULT_TIMEOUT (5s) production grading uses for a real submission,
not problem_bank's own authoring-time _run_ref. A naive solution that's
genuinely O(n^2) at this scale is expected to really run for tens of
seconds if left uninterrupted; code_runner's timeout kills it at 5s, so
this test's own wall-clock cost is bounded at roughly 5s per naive case,
not the naive algorithm's real uninterrupted runtime.

No model is used anywhere in this file.
"""
import time

import pytest

from banks import problem_bank
from banks import problem_input_gen as pig
from services import code_runner

TIMEOUT = code_runner.DEFAULT_TIMEOUT

# Each is a deliberately naive O(n^2) (or worse) implementation of the
# SAME problem the reference solves efficiently -- see each one's
# independent-checker counterpart in problem_input_gen.py, which uses
# the identical algorithm (already independently proven correct there
# via the 200-trial differential fuzz); reused verbatim here as the
# "slow submission" under test, not reinvented.
NAIVE_SOLUTIONS = {
    "container-water": """
n = int(input())
h = list(map(int, input().split()))
best = 0
for i in range(n):
    for j in range(i + 1, n):
        area = min(h[i], h[j]) * (j - i)
        if area > best:
            best = area
print(best)
""",
    "greedy-activity-selection": """
n = int(input())
starts = list(map(int, input().split()))
ends = list(map(int, input().split()))
ivs = sorted(zip(starts, ends), key=lambda x: x[1])
dp = [0] * n
for i in range(n):
    best = 1
    for j in range(i):
        if ivs[j][1] <= ivs[i][0]:
            best = max(best, dp[j] + 1)
    dp[i] = best
print(max(dp) if dp else 0)
""",
    "greedy-merge-intervals": """
n = int(input())
ivs = [tuple(map(int, input().split())) for _ in range(n)]
parent = list(range(n))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb
for i in range(n):
    si, ei = ivs[i]
    for j in range(i + 1, n):
        sj, ej = ivs[j]
        if si <= ej and sj <= ei:
            union(i, j)
groups = {}
for i in range(n):
    r = find(i)
    s, e = ivs[i]
    if r not in groups:
        groups[r] = [s, e]
    else:
        groups[r][0] = min(groups[r][0], s)
        groups[r][1] = max(groups[r][1], e)
for s, e in sorted(groups.values()):
    print(s, e)
""",
    "greedy-non-overlapping-removals": """
n = int(input())
ivs = [tuple(map(int, input().split())) for _ in range(n)]
ivs_sorted = sorted(ivs, key=lambda x: x[1])
dp = [0] * n
for i in range(n):
    best = 1
    for j in range(i):
        if ivs_sorted[j][1] <= ivs_sorted[i][0]:
            best = max(best, dp[j] + 1)
    dp[i] = best
print(n - (max(dp) if dp else 0))
""",
}


def _raw_by_id(pid):
    return next(r for r in problem_bank._RAW if r["id"] == pid)


def test_exactly_4_problems_have_a_naive_comparison():
    assert sorted(NAIVE_SOLUTIONS) == [
        "container-water", "greedy-activity-selection",
        "greedy-merge-intervals", "greedy-non-overlapping-removals",
    ]


@pytest.mark.parametrize("pid", sorted(NAIVE_SOLUTIONS))
def test_naive_times_out_reference_does_not_on_large_input(pid):
    raw = _raw_by_id(pid)
    ref = raw["reference_solution"]
    naive = NAIVE_SOLUTIONS[pid]
    large_cases = pig.SPECS[pid].large_cases
    assert large_cases and len(large_cases) == 2, f"{pid}: expected 2 large_cases, got {large_cases!r}"
    assert all(stdin in raw["test_inputs"] for stdin in large_cases), (
        f"{pid}: this problem's large_cases aren't actually present in its stored "
        f"test_inputs -- the restoration may not have taken effect"
    )

    for stdin in large_cases:
        n = int(stdin.split("\n", 1)[0])

        t0 = time.time()
        ref_result = code_runner.run_code("python", ref, stdin, TIMEOUT)
        ref_elapsed = time.time() - t0
        assert not ref_result["timed_out"], (
            f"{pid}: reference solution timed out on its own n={n} large case within "
            f"{TIMEOUT}s -- the reference is supposed to be the EFFICIENT algorithm"
        )
        assert ref_result["exit_code"] == 0, (
            f"{pid}: reference solution exited {ref_result['exit_code']} on n={n}: "
            f"{(ref_result.get('stderr') or '')[:200]}"
        )

        t0 = time.time()
        naive_result = code_runner.run_code("python", naive, stdin, TIMEOUT)
        naive_elapsed = time.time() - t0
        assert naive_result["timed_out"], (
            f"{pid}: naive O(n^2) solution did NOT time out on n={n} within {TIMEOUT}s "
            f"(finished in {naive_elapsed:.2f}s instead) -- this large case no longer "
            f"demonstrates a real timeout gap at this size"
        )

        print(
            f"\n{pid} n={n}: reference passed in {ref_elapsed:.3f}s; "
            f"naive O(n^2) timed out (>= {naive_elapsed:.3f}s wall, capped at {TIMEOUT}s)"
        )
