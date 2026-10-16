"""Direct proof (Stage 2c batch 2) that, for every batch-2 problem whose
intended complexity is actually faster than naive at its own stated
constraint ceiling, the REFERENCE solution passes within the real
production sandbox timeout on that problem's full-scale large input while
a genuinely naive "submission" does not. Mirrors
test_problem_bank_large_input_complexity.py's batch-1 pattern exactly.

Problems deliberately EXCLUDED from this file, with the reason stated
directly in their own generator registration comment in
problem_input_gen.py (no naive-vs-reference timing gap exists for them
within their own stated constraints): graph-network-delay-time (n<=100,
both Dijkstra and Bellman-Ford finish instantly), string-compression,
string-integer-to-roman, string-count-and-say, string-multiply-strings,
and string-zigzag-conversion (all O(n) or O(1)-ish regardless of
implementation, nothing slower to time out against at their own ceilings).

Uses services.code_runner.run_code directly -- the exact same function
and DEFAULT_TIMEOUT (5s) production grading uses for a real submission,
not problem_bank's own authoring-time _run_ref. A naive solution that's
genuinely too slow at this scale is expected to really run for well over
5s (or, for the two exponential-recursion cases, effectively forever) if
left uninterrupted; code_runner's timeout kills it at 5s, so this test's
own wall-clock cost is bounded at roughly 5s per naive case.

No model is used anywhere in this file.
"""
import time

import pytest

from banks import problem_bank
from banks import problem_input_gen as pig
from services import code_runner

TIMEOUT = code_runner.DEFAULT_TIMEOUT

# Each is a deliberately naive re-implementation of the problem the
# reference solves efficiently. Where the problem's own independent
# checker (problem_input_gen.py) is ALREADY the natural "slow but
# correct" counterpart, its exact source is reused verbatim here rather
# than reinvented; where the checker uses a different (exponential/
# combinatorial, capped-to-tiny-n) technique instead, a separate,
# genuinely naive-but-polynomial (or honestly exponential, where that's
# the natural "naive" story -- e.g. exhaustive search) script is used.
NAIVE_SOLUTIONS = {
    "greedy-jump-game-ii": """
n = int(input())
a = list(map(int, input().split()))
dp = [0] * n
for i in range(n - 2, -1, -1):
    reach = min(i + a[i], n - 1)
    best = None
    for j in range(i + 1, reach + 1):
        if best is None or dp[j] + 1 < best:
            best = dp[j] + 1
    dp[i] = best if best is not None else 10 ** 9
print(dp[0])
""",
    "greedy-gas-station": """
n = int(input())
gas = list(map(int, input().split()))
cost = list(map(int, input().split()))
for s in range(n):
    tank = 0
    ok = True
    for k in range(n):
        i = (s + k) % n
        tank += gas[i] - cost[i]
        if tank < 0:
            ok = False
            break
    if ok:
        print(s)
        break
""",
    "greedy-boats-save-people": """
n = int(input())
w = list(map(int, input().split()))
limit = int(input())
remaining = w[:]
boats = 0
while remaining:
    hi = max(remaining)
    remaining.remove(hi)
    if remaining:
        lo = min(remaining)
        if hi + lo <= limit:
            remaining.remove(lo)
    boats += 1
print(boats)
""",
    "greedy-min-arrows-balloons": """
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
print(max(dp) if dp else 0)
""",
    "greedy-two-city-scheduling": """
import sys
sys.setrecursionlimit(5000)
n = int(input())
costA = list(map(int, input().split()))
costB = list(map(int, input().split()))
total = 2 * n
def rec(i, a_used, cost):
    if i == total:
        return cost if a_used == n else None
    best = None
    if a_used < n:
        r = rec(i + 1, a_used + 1, cost + costA[i])
        if r is not None and (best is None or r < best):
            best = r
    if (total - i - 1) >= (n - a_used):
        r = rec(i + 1, a_used, cost + costB[i])
        if r is not None and (best is None or r < best):
            best = r
    return best
print(rec(0, 0, 0))
""",
    "graph-connected-components": """
n, m = map(int, input().split())
edges = [tuple(map(int, input().split())) for _ in range(m)]
seen = [False] * n
count = 0
for i in range(n):
    if not seen[i]:
        count += 1
        seen[i] = True
        stack = [i]
        while stack:
            x = stack.pop()
            for u, v in edges:
                if u == x and not seen[v]:
                    seen[v] = True; stack.append(v)
                elif v == x and not seen[u]:
                    seen[u] = True; stack.append(u)
print(count)
""",
    "graph-cycle-undirected": """
n, m = map(int, input().split())
edges = []
has_cycle = False
def connected(a, b, edge_list):
    if a == b:
        return True
    seen = {a}
    stack = [a]
    while stack:
        x = stack.pop()
        for u, v in edge_list:
            if u == x and v not in seen:
                if v == b:
                    return True
                seen.add(v); stack.append(v)
            elif v == x and u not in seen:
                if u == b:
                    return True
                seen.add(u); stack.append(u)
    return False
for _ in range(m):
    u, v = map(int, input().split())
    if connected(u, v, edges):
        has_cycle = True
    edges.append((u, v))
print('YES' if has_cycle else 'NO')
""",
    "graph-cycle-directed": """
from collections import deque
n, m = map(int, input().split())
edges = [tuple(map(int, input().split())) for _ in range(m)]
indeg = [0] * n
for u, v in edges:
    indeg[v] += 1
q = deque([i for i in range(n) if indeg[i] == 0])
processed = 0
while q:
    u = q.popleft(); processed += 1
    for a, b in edges:
        if a == u:
            indeg[b] -= 1
            if indeg[b] == 0:
                q.append(b)
print('YES' if processed < n else 'NO')
""",
    "graph-course-schedule": """
from collections import deque
n = int(input())
m = int(input())
edges = []
for _ in range(m):
    a, b = map(int, input().split())
    edges.append((b, a))
indeg = [0] * n
for u, v in edges:
    indeg[v] += 1
q = deque([i for i in range(n) if indeg[i] == 0])
processed = 0
while q:
    u = q.popleft(); processed += 1
    for a, b in edges:
        if a == u:
            indeg[b] -= 1
            if indeg[b] == 0:
                q.append(b)
print('YES' if processed == n else 'NO')
""",
    "graph-topo-sort-lexo": """
n, m = map(int, input().split())
adj = [[] for _ in range(n)]
indeg = [0] * n
for _ in range(m):
    u, v = map(int, input().split())
    adj[u].append(v); indeg[v] += 1
used = [False] * n
order = []
for _ in range(n):
    best = None
    for i in range(n):
        if not used[i] and indeg[i] == 0 and (best is None or i < best):
            best = i
    used[best] = True
    order.append(best)
    for v in adj[best]:
        indeg[v] -= 1
print(' '.join(map(str, order)))
""",
    "graph-bipartite-check": """
from collections import deque
n, m = map(int, input().split())
edges = [tuple(map(int, input().split())) for _ in range(m)]
color = [-1] * n
ok = True
for i in range(n):
    if color[i] == -1:
        color[i] = 0
        q = deque([i])
        while q:
            u = q.popleft()
            for a, b in edges:
                if a == u:
                    v = b
                elif b == u:
                    v = a
                else:
                    continue
                if color[v] == -1:
                    color[v] = 1 - color[u]
                    q.append(v)
                elif color[v] == color[u]:
                    ok = False
print('YES' if ok else 'NO')
""",
    "graph-bfs-shortest-path": """
from collections import deque
n, m = map(int, input().split())
edges = [tuple(map(int, input().split())) for _ in range(m)]
src, dst = map(int, input().split())
dist = [-1] * n
dist[src] = 0
q = deque([src])
while q:
    u = q.popleft()
    for a, b in edges:
        if a == u:
            v = b
        elif b == u:
            v = a
        else:
            continue
        if dist[v] == -1:
            dist[v] = dist[u] + 1
            q.append(v)
print(dist[dst])
""",
    "graph-rotten-oranges": """
rows, cols = map(int, input().split())
g = [list(map(int, input().split())) for _ in range(rows)]
minutes = 0
while True:
    to_rot = []
    for i in range(rows):
        for j in range(cols):
            if g[i][j] == 1:
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ni, nj = i + di, j + dj
                    if 0 <= ni < rows and 0 <= nj < cols and g[ni][nj] == 2:
                        to_rot.append((i, j))
                        break
    if not to_rot:
        break
    for i, j in to_rot:
        g[i][j] = 2
    minutes += 1
fresh_left = any(g[i][j] == 1 for i in range(rows) for j in range(cols))
print(-1 if fresh_left else minutes)
""",
    "dp-longest-common-subsequence": """
import sys
sys.setrecursionlimit(5000)
a = input()
b = input()
def lcs(i, j):
    if i == 0 or j == 0:
        return 0
    if a[i - 1] == b[j - 1]:
        return 1 + lcs(i - 1, j - 1)
    return max(lcs(i - 1, j), lcs(i, j - 1))
print(lcs(len(a), len(b)))
""",
    "dp-longest-common-substring": """
a = input()
b = input()
n, m = len(a), len(b)
best = 0
for i in range(n):
    for j in range(m):
        k = 0
        while i + k < n and j + k < m and a[i + k] == b[j + k]:
            k += 1
        if k > best:
            best = k
print(best)
""",
}


def _raw_by_id(pid):
    return next(r for r in problem_bank._RAW if r["id"] == pid)


def test_exactly_15_batch2_problems_have_a_naive_comparison():
    assert len(NAIVE_SOLUTIONS) == 15, sorted(NAIVE_SOLUTIONS)


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
        n_label = stdin.split("\n", 1)[0]

        t0 = time.time()
        ref_result = code_runner.run_code("python", ref, stdin, TIMEOUT)
        ref_elapsed = time.time() - t0
        assert not ref_result["timed_out"], (
            f"{pid}: reference solution timed out on its own large case ({n_label}) within "
            f"{TIMEOUT}s -- the reference is supposed to be the EFFICIENT algorithm"
        )
        assert ref_result["exit_code"] == 0, (
            f"{pid}: reference solution exited {ref_result['exit_code']} on {n_label}: "
            f"{(ref_result.get('stderr') or '')[:200]}"
        )

        t0 = time.time()
        naive_result = code_runner.run_code("python", naive, stdin, TIMEOUT)
        naive_elapsed = time.time() - t0
        assert naive_result["timed_out"], (
            f"{pid}: naive solution did NOT time out on {n_label} within {TIMEOUT}s "
            f"(finished in {naive_elapsed:.2f}s instead) -- this large case no longer "
            f"demonstrates a real timeout gap at this size"
        )

        print(
            f"\n{pid} ({n_label}): reference passed in {ref_elapsed:.3f}s; "
            f"naive timed out (>= {naive_elapsed:.3f}s wall, capped at {TIMEOUT}s)"
        )
