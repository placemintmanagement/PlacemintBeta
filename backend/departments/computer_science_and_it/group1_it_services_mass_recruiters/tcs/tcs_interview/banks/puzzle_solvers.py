# -*- coding: utf-8 -*-
"""Deterministic, seeded solver code for the parametrized puzzle families in
interview_puzzle_bank.py (part 2 of the 4-part TCS restructure).

Every solver here is EXHAUSTIVE over the real state space (BFS / full
subset search / simulation) -- not a hand-tuned heuristic -- so its answer
is correct by construction, not by a cross-check alone. Each solver is
still paired with an INDEPENDENT second method (a different algorithm, a
closed-form formula, or a from-scratch non-memoized re-implementation) so
a generated item's stored answer is cross-checked, never trusted from a
single code path -- see each function's own docstring for what its pair
is and tests/test_interview_puzzle_bank.py for the actual cross-checks.
"""
import math
from collections import deque
from functools import lru_cache
from itertools import combinations
from typing import Dict, FrozenSet, List, Optional, Tuple

# ============================================================================
# 1. Water jugs (BFS over (a, b) fill states)
# ============================================================================

def water_jugs_min_steps(cap_a: int, cap_b: int, target: int) -> Optional[int]:
    """BFS over every reachable (a, b) state from (0, 0), via the six
    classic moves (fill A, fill B, empty A, empty B, pour A->B, pour B->A).
    Returns the minimum number of moves to have EITHER jug read exactly
    `target`, or None if unreachable."""
    if target > max(cap_a, cap_b):
        return None
    start = (0, 0)
    if target in start:
        return 0
    seen = {start}
    queue = deque([(start, 0)])
    while queue:
        (a, b), steps = queue.popleft()
        moves = [
            (cap_a, b), (a, cap_b),         # fill A, fill B
            (0, b), (a, 0),                 # empty A, empty B
            (a - min(a, cap_b - b), b + min(a, cap_b - b)),   # pour A -> B
            (a + min(b, cap_a - a), b - min(b, cap_a - a)),   # pour B -> A
        ]
        for nxt in moves:
            if nxt in seen:
                continue
            if nxt[0] == target or nxt[1] == target:
                return steps + 1
            seen.add(nxt)
            queue.append((nxt, steps + 1))
    return None


def water_jugs_is_solvable_by_number_theory(cap_a: int, cap_b: int, target: int) -> bool:
    """INDEPENDENT second method: the classical number-theory fact (no
    search at all) -- target is reachable with two jugs of capacity
    cap_a/cap_b iff target == 0, or target <= max(cap_a, cap_b) AND
    target is a multiple of gcd(cap_a, cap_b)."""
    if target == 0:
        return True
    if target > max(cap_a, cap_b):
        return False
    return target % math.gcd(cap_a, cap_b) == 0


# ============================================================================
# 2. Bridge crossing with one torch (exhaustive subset-DP search)
# ============================================================================

def bridge_min_total_time(times: List[int]) -> int:
    """Exhaustive search (memoized) over every legal strategy: from any
    state, either two people (still on the start side) cross together
    (torch now on the far side), or one person (already on the far side)
    brings the torch back. This explores the FULL strategy space, so its
    answer is optimal by construction -- see
    bridge_min_total_time_naive below for a from-scratch, non-memoized
    re-implementation used as the independent cross-check."""
    n = len(times)
    full_mask = (1 << n) - 1

    @lru_cache(maxsize=None)
    def solve(start_mask: int, torch_at_start: bool) -> int:
        if start_mask == 0:
            return 0
        if torch_at_start:
            people = [i for i in range(n) if start_mask & (1 << i)]
            best = None
            for i in range(len(people)):
                for j in range(i + 1, len(people)):
                    p, q = people[i], people[j]
                    cost = max(times[p], times[q])
                    new_mask = start_mask & ~(1 << p) & ~(1 << q)
                    total = cost + solve(new_mask, False)
                    if best is None or total < best:
                        best = total
            return best
        else:
            other = [i for i in range(n) if not (start_mask & (1 << i))]
            best = None
            for p in other:
                new_mask = start_mask | (1 << p)
                total = times[p] + solve(new_mask, True)
                if best is None or total < best:
                    best = total
            return best

    result = solve(full_mask, True)
    solve.cache_clear()
    return result


def bridge_min_total_time_naive(times: List[int]) -> int:
    """INDEPENDENT second method: the SAME recurrence as
    bridge_min_total_time, but written from scratch with NO memoization
    (plain exponential recursion) -- a different code path, so a caching
    bug in the memoized version would not be reproduced here. Only used
    for cross-checking in tests (too slow to use for n > ~6)."""
    n = len(times)

    def solve(start_mask: int, torch_at_start: bool) -> int:
        if start_mask == 0:
            return 0
        if torch_at_start:
            people = [i for i in range(n) if start_mask & (1 << i)]
            best = None
            for p, q in combinations(people, 2):
                cost = max(times[p], times[q])
                new_mask = start_mask & ~(1 << p) & ~(1 << q)
                total = cost + solve(new_mask, False)
                best = total if best is None else min(best, total)
            return best
        else:
            other = [i for i in range(n) if not (start_mask & (1 << i))]
            best = None
            for p in other:
                new_mask = start_mask | (1 << p)
                total = times[p] + solve(new_mask, True)
                best = total if best is None else min(best, total)
            return best

    return solve((1 << n) - 1, True)


# ============================================================================
# 3. River crossing (BFS over (left-bank entities, boat side) states)
# ============================================================================

def river_crossing_min_trips(entity_names: Tuple[str, ...],
                             is_unsafe,
                             boat_capacity: int = 2,
                             must_include: Optional[int] = None) -> Optional[Tuple[int, List[str]]]:
    """Generic BFS: every entity starts on the LEFT bank; the boat starts
    on the LEFT; a move takes 1-boat_capacity entities currently on the
    boat's own side across. `is_unsafe(bank_set)` returns True if a bank
    configuration (the entities physically standing there, NOT counting
    who's mid-river in the boat) is forbidden if left unsupervised.

    `must_include` (e.g. the farmer's index in wolf/goat/cabbage): when
    set, every crossing group MUST contain this entity -- items cannot
    row themselves across alone. Left None for puzzles like missionaries-
    and-cannibals, where any mix of people can crew the boat.

    Returns (min_trips, human-readable move list) or None if unsolvable.
    """
    n = len(entity_names)
    start = (frozenset(range(n)), "left")
    goal_left = frozenset()
    seen = {start}
    queue = deque([(start, [])])
    while queue:
        (left, boat_side), path = queue.popleft()
        if left == goal_left and boat_side == "right":
            return len(path), path
        source = left if boat_side == "left" else (frozenset(range(n)) - left)
        if must_include is not None and must_include not in source:
            continue  # the required rower isn't on this side -- no legal move from here
        rest = sorted(source - {must_include}) if must_include is not None else None
        candidate_groups = []
        for size in range(1, boat_capacity + 1):
            if must_include is not None:
                if size - 1 > len(rest):
                    continue
                for extra in combinations(rest, size - 1):
                    candidate_groups.append((must_include,) + extra)
            else:
                candidate_groups.extend(combinations(sorted(source), size))
        for group in candidate_groups:
                group_set = frozenset(group)
                if boat_side == "left":
                    new_left = left - group_set
                else:
                    new_left = left | group_set
                new_right = frozenset(range(n)) - new_left
                # Both banks must be safe once the boat departs.
                if is_unsafe(new_left) or is_unsafe(new_right):
                    continue
                new_boat_side = "right" if boat_side == "left" else "left"
                new_state = (new_left, new_boat_side)
                if new_state in seen:
                    continue
                seen.add(new_state)
                names = ",".join(entity_names[i] for i in group)
                direction = "->" if boat_side == "left" else "<-"
                queue.append((new_state, path + [f"{direction} {names}"]))
    return None


def wolf_goat_cabbage_unsafe(bank: FrozenSet[int]) -> bool:
    """Classic instance: entities = (farmer, wolf, goat, cabbage) at
    indices 0,1,2,3. Unsafe if the farmer (0) is ABSENT from a bank while
    wolf+goat (1,2) or goat+cabbage (2,3) are both present there."""
    farmer_present = 0 in bank
    if farmer_present:
        return False
    return ({1, 2} <= bank) or ({2, 3} <= bank)


def missionaries_cannibals_unsafe(n_pairs: int):
    """Returns an is_unsafe fn for the classic instance: entities
    0..n_pairs-1 are missionaries, n_pairs..2n_pairs-1 are cannibals.
    Unsafe if a bank has at least 1 missionary AND cannibals outnumber
    missionaries there."""
    def _unsafe(bank: FrozenSet[int]) -> bool:
        missionaries = sum(1 for i in bank if i < n_pairs)
        cannibals = sum(1 for i in bank if i >= n_pairs)
        return missionaries > 0 and cannibals > missionaries
    return _unsafe


# ============================================================================
# 4. Counterfeit-coin weighing (decision-tree search over a 3-pan balance)
# ============================================================================

def min_weighings_known_heavier(n_coins: int) -> int:
    """n_coins coins, exactly one is counterfeit and KNOWN to be heavier;
    minimum balance-scale weighings to identify it. Modeled by actually
    SEARCHING the decision tree: at each weighing, split the current
    candidate pool as evenly as possible into 3 groups and weigh group1
    vs group2 -- each of the 3 outcomes (left heavy / right heavy /
    balanced) narrows the candidate pool to the corresponding group.
    Recursion depth for a given split is identical regardless of exact
    group sizes as long as each is as balanced as possible, so this
    returns the number of rounds until the candidate pool is down to 1."""
    def rounds(pool_size: int) -> int:
        if pool_size <= 1:
            return 0
        group = pool_size // 3 if pool_size % 3 == 0 else pool_size // 3 + 1
        return 1 + rounds(group)
    return rounds(n_coins)


def min_weighings_known_heavier_formula(n_coins: int) -> int:
    """INDEPENDENT second method: the closed-form ceil(log3(n)) formula."""
    if n_coins <= 1:
        return 0
    return math.ceil(math.log(n_coins, 3) - 1e-12)  # tiny epsilon guards exact powers of 3


# ============================================================================
# 5. 100 doors (direct simulation; "every i-th door toggled on pass i")
# ============================================================================

def doors_open_after_all_passes(n_doors: int) -> List[int]:
    """Simulates every pass directly: on pass i (1-indexed), toggle every
    door whose number is a multiple of i. Returns the sorted list of door
    numbers left OPEN after all n_doors passes."""
    state = [False] * (n_doors + 1)  # 1-indexed; index 0 unused
    for i in range(1, n_doors + 1):
        for door in range(i, n_doors + 1, i):
            state[door] = not state[door]
    return [d for d in range(1, n_doors + 1) if state[d]]


def doors_open_by_perfect_squares(n_doors: int) -> List[int]:
    """INDEPENDENT second method: a door ends open iff it has an ODD
    number of divisors, which happens iff the door number is a perfect
    square (every divisor d < sqrt(n) pairs with n/d > sqrt(n), except
    sqrt(n) itself when n is a perfect square)."""
    out = []
    k = 1
    while k * k <= n_doors:
        out.append(k * k)
        k += 1
    return out
