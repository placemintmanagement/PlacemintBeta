# -*- coding: utf-8 -*-
"""Seeded, deterministic input generators for problem_bank.py test
authoring (Stage 2b, 2026-10). NEVER used by the live OA grading path --
this module builds NEW test_inputs for a problem's _RAW entry at
authoring time only. Expected outputs always still come from running the
reference solution (problem_bank._hydrate), never from here, and no
model is used anywhere in this module.

Shapes found among the 24 Easy problems, built from 5 core generic
generators (int, string, int_array, two_int_arrays, matrix -- the last
of these, matrix, is included for completeness/future reuse; none of
the 24 Easy problems actually need one):

  int                    fizzbuzz, climb-stairs
  string                 reverse-string, valid-palindrome,
                         string-roman-to-integer (alphabet-constrained)
  int_array              max-subarray-sum, contains-duplicate,
                         buy-sell-stock
  two_int_arrays         merge-sorted, greedy-assign-cookies

Composed/specialized shapes, each built by post-processing one of the
core generators above (so the "one generator per shape" requirement is
met at the primitive level; these are the per-problem compositions on
top of it, not new unrelated primitives):

  int_array_with_target      two-sum (target engineered so a solution
                              always exists, matching the problem's own
                              "exactly one solution" promise)
  sorted_int_array           tp-remove-duplicates-sorted
  permutation_minus_one      missing-number
  majority_array             arr-majority-element
  two_strings                string-valid-anagram
  two_strings_equal_length   string-isomorphic
  list_of_strings            string-longest-common-prefix
  pattern_and_words          string-word-pattern
  tree_level_order           the 6 tree-* problems
"""
from __future__ import annotations

import random
import string as _string_mod
from collections import deque
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

LOWER = _string_mod.ascii_lowercase


# =============================================================================
# Core generic shape generators
# =============================================================================

def gen_int(rng: random.Random, lo: int, hi: int) -> int:
    return rng.randint(lo, hi)


def gen_int_array(rng: random.Random, n: int, lo: int, hi: int) -> List[int]:
    return [rng.randint(lo, hi) for _ in range(n)]


def gen_string(rng: random.Random, length: int, alphabet: str = LOWER) -> str:
    return "".join(rng.choice(alphabet) for _ in range(length))


def gen_two_int_arrays(rng: random.Random, n: int, m: int, lo: int, hi: int) -> Tuple[List[int], List[int]]:
    return gen_int_array(rng, n, lo, hi), gen_int_array(rng, m, lo, hi)


def gen_matrix(rng: random.Random, rows: int, cols: int, lo: int, hi: int) -> List[List[int]]:
    """Included for completeness/future reuse -- no Easy problem needs this shape."""
    return [gen_int_array(rng, cols, lo, hi) for _ in range(rows)]


def _fmt_arr(arr: List[int]) -> str:
    return " ".join(map(str, arr))


# =============================================================================
# Spec type + registry
# =============================================================================

@dataclass
class ProblemInputSpec:
    problem_id: str
    shape: str
    constraints: dict               # structured, used by the quality-gate test
    edge_cases: List[str]
    random_input: Callable[[random.Random], str]
    validate: Callable[[str], bool]
    checker: Optional[Callable[[str], str]] = None  # independent/brute-force, if practical
    large_cases: List[str] = None   # Stage 2c: >=2 inputs sized to stress the problem's
                                     # intended complexity (see each registration's comment)


SPECS: dict = {}


def _register(spec: ProblemInputSpec) -> None:
    SPECS[spec.problem_id] = spec


# =============================================================================
# 1. two-sum  --  shape: int_array_with_target
# =============================================================================

def _two_sum_pair_count(vals: List[int], target: int) -> int:
    return sum(1 for a in range(len(vals)) for b in range(a + 1, len(vals)) if vals[a] + vals[b] == target)


def _two_sum_random(rng: random.Random) -> str:
    # Rejection sampling (Stage 2c, after a differential-fuzz run found a
    # 23-element draw with TWO valid pairs): the problem's own statement
    # promises "each input has exactly one solution" -- picking i,j and
    # setting target=vals[i]+vals[j] only guarantees AT LEAST one pair;
    # with enough random values a second coincidental pair is possible.
    # Retry until the drawn array genuinely has exactly one.
    for _ in range(500):
        n = rng.choice([2, 3, 5, rng.randint(6, 60)])
        vals = rng.sample(range(-500, 500), n) if n <= 1000 else [rng.randint(-500, 500) for _ in range(n)]
        i, j = rng.sample(range(n), 2)
        target = vals[i] + vals[j]
        if _two_sum_pair_count(vals, target) == 1:
            return f"{n}\n{_fmt_arr(vals)}\n{target}\n"
    raise RuntimeError("two-sum: could not draw a unique-solution input in 500 attempts")


def _two_sum_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    target = int(lines[2])
    return (len(arr) == n and 2 <= n <= 10000
            and _two_sum_pair_count(arr, target) == 1)  # the problem's own "exactly one solution" precondition


def _two_sum_checker(stdin: str) -> str:
    """Brute-force O(n^2) pair scan -- reference uses a hash map."""
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    target = int(lines[2])
    for i in range(n):
        for j in range(i + 1, n):
            if arr[i] + arr[j] == target:
                return f"{i} {j}"
    return ""


# The "large" edge case is 2000, not the full 10^4 constraint ceiling --
# its independent checker (below) is an O(n^2) brute force, and this
# same string is exercised by BOTH the sandbox-timeout check and the
# checker-agreement check (test_problem_bank_opted_in_quality_gates.py),
# so it has to stay fast for the checker too, not just for the
# reference solution's own O(n) hash-map pass.
_TWO_SUM_LARGE_ARR = list(range(2000))
_register(ProblemInputSpec(
    "two-sum", "int_array_with_target",
    {"n_min": 2, "n_max": 10000},
    ["2\n0 0\n0\n", "2\n-5 5\n0\n",
     f"{2000}\n{_fmt_arr(_TWO_SUM_LARGE_ARR)}\n{_TWO_SUM_LARGE_ARR[-1] + _TWO_SUM_LARGE_ARR[-2]}\n"],
    _two_sum_random, _two_sum_validate, _two_sum_checker,
))


# =============================================================================
# 2. reverse-string  --  shape: string
# =============================================================================

def _reverse_string_random(rng: random.Random) -> str:
    length = rng.choice([1, 2, rng.randint(3, 200)])
    return gen_string(rng, length, LOWER + LOWER.upper() + "0123456789")


def _reverse_string_validate(stdin: str) -> bool:
    return 1 <= len(stdin) <= 100000 and "\n" not in stdin


_register(ProblemInputSpec(
    "reverse-string", "string",
    {"len_min": 1, "len_max": 100000},
    ["a", "aa", "a" * 100000],
    _reverse_string_random, _reverse_string_validate, None,
))


# =============================================================================
# 3. fizzbuzz  --  shape: int
# =============================================================================

def _fizzbuzz_random(rng: random.Random) -> str:
    return str(gen_int(rng, 1, 100))


def _fizzbuzz_validate(stdin: str) -> bool:
    n = int(stdin)
    return 1 <= n <= 100


def _fizzbuzz_checker(stdin: str) -> str:
    """Independent re-implementation: builds the list first, no incremental if/elif chain order dependency."""
    n = int(stdin)
    out = []
    for i in range(1, n + 1):
        label = ("Fizz" if i % 3 == 0 else "") + ("Buzz" if i % 5 == 0 else "")
        out.append(label if label else str(i))
    return "\n".join(out)


_register(ProblemInputSpec(
    "fizzbuzz", "int",
    {"n_min": 1, "n_max": 100},
    ["1", "100"],
    _fizzbuzz_random, _fizzbuzz_validate, _fizzbuzz_checker,
))


# =============================================================================
# 4. valid-palindrome  --  shape: string
# =============================================================================

def _valid_palindrome_random(rng: random.Random) -> str:
    length = rng.randint(1, 60)
    core = gen_string(rng, length, LOWER)
    if rng.random() < 0.5:
        core = core + core[::-1]  # bias toward real palindromes
    # sprinkle punctuation/case to exercise the ignore-non-alnum/ignore-case rule
    noisy = []
    for ch in core:
        if rng.random() < 0.2:
            noisy.append(rng.choice(", .-:!"))
        noisy.append(ch.upper() if rng.random() < 0.5 else ch)
    return "".join(noisy) if noisy else "a"


def _valid_palindrome_validate(stdin: str) -> bool:
    return 1 <= len(stdin) <= 100000


_register(ProblemInputSpec(
    "valid-palindrome", "string",
    {"len_min": 1, "len_max": 100000},
    ["a", "ab", ".,!", "a" * 100000],
    _valid_palindrome_random, _valid_palindrome_validate, None,
))


# =============================================================================
# 5. max-subarray-sum  --  shape: int_array
# =============================================================================

def _max_subarray_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 100)])
    arr = gen_int_array(rng, n, -100, 100)
    return f"{n}\n{_fmt_arr(arr)}"


def _max_subarray_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    return len(arr) == n and 1 <= n <= 100000


def _max_subarray_checker(stdin: str) -> str:
    """Brute-force O(n^2) over all subarrays -- reference uses Kadane's O(n)."""
    lines = stdin.split("\n")
    arr = list(map(int, lines[1].split()))
    best = arr[0]
    for i in range(len(arr)):
        s = 0
        for j in range(i, len(arr)):
            s += arr[j]
            best = max(best, s)
    return str(best)


_register(ProblemInputSpec(
    "max-subarray-sum", "int_array",
    {"n_min": 1, "n_max": 100000},
    # "Large" edge capped at 2000, not the full 10^5 ceiling -- its
    # independent checker is an O(n^2) brute force over all subarrays,
    # and this same string is also run through that checker (not just
    # the reference solution's O(n) Kadane pass), so it has to stay fast.
    ["1\n-5", "1\n0", "5\n-1 -2 -3 -4 -5", f"2000\n{_fmt_arr([((i * 37) % 201) - 100 for i in range(2000)])}"],
    _max_subarray_random, _max_subarray_validate, _max_subarray_checker,
))


# =============================================================================
# 6. contains-duplicate  --  shape: int_array
# =============================================================================

def _contains_dup_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 100)])
    if rng.random() < 0.5 and n > 1:
        base = gen_int_array(rng, max(1, n // 2), -50, 50)
        arr = (base * 2)[:n]
        rng.shuffle(arr)
    else:
        arr = rng.sample(range(-1000, 1000), n) if n <= 2000 else gen_int_array(rng, n, -1000, 1000)
    return f"{n}\n{_fmt_arr(arr)}"


def _contains_dup_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    return len(arr) == n and 1 <= n <= 100000


def _contains_dup_checker(stdin: str) -> str:
    """Sort + adjacent-compare -- reference uses set-length comparison."""
    lines = stdin.split("\n")
    arr = sorted(map(int, lines[1].split()))
    for i in range(1, len(arr)):
        if arr[i] == arr[i - 1]:
            return "YES"
    return "NO"


_register(ProblemInputSpec(
    "contains-duplicate", "int_array",
    {"n_min": 1, "n_max": 100000},
    ["1\n7", "5\n1 1 1 1 1", f"100000\n{_fmt_arr(list(range(100000)))}"],
    _contains_dup_random, _contains_dup_validate, _contains_dup_checker,
))


# =============================================================================
# 7. missing-number  --  shape: permutation_minus_one
# =============================================================================

def _missing_number_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 200)])
    full = list(range(n + 1))
    missing = rng.choice(full)
    arr = [x for x in full if x != missing]
    rng.shuffle(arr)
    return f"{n}\n{_fmt_arr(arr)}"


def _missing_number_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split())) if n else []
    return len(arr) == n and 1 <= n <= 10000 and len(set(arr)) == n and all(0 <= x <= n for x in arr)


def _missing_number_checker(stdin: str) -> str:
    """XOR-based -- reference uses the Gauss sum formula."""
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    x = 0
    for i in range(n + 1):
        x ^= i
    for v in arr:
        x ^= v
    return str(x)


_register(ProblemInputSpec(
    "missing-number", "permutation_minus_one",
    {"n_min": 1, "n_max": 10000},
    ["1\n0", "1\n1", f"10000\n{_fmt_arr([x for x in range(10001) if x != 5000])}"],
    _missing_number_random, _missing_number_validate, _missing_number_checker,
))


# =============================================================================
# 8. buy-sell-stock  --  shape: int_array
# =============================================================================

def _buy_sell_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 100)])
    arr = gen_int_array(rng, n, 0, 1000)
    return f"{n}\n{_fmt_arr(arr)}"


def _buy_sell_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    return len(arr) == n and 1 <= n <= 100000


def _buy_sell_checker(stdin: str) -> str:
    """Brute-force O(n^2) over all buy/sell pairs -- reference tracks a running min."""
    lines = stdin.split("\n")
    arr = list(map(int, lines[1].split()))
    best = 0
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            best = max(best, arr[j] - arr[i])
    return str(best)


_register(ProblemInputSpec(
    "buy-sell-stock", "int_array",
    {"n_min": 1, "n_max": 100000},
    # "Large" edge capped at 2000, not the full 10^5 ceiling -- same
    # reasoning as max-subarray-sum above: its independent checker is an
    # O(n^2) brute force over all buy/sell pairs, and this same string
    # is also run through that checker, not just the reference
    # solution's own O(n) running-min pass.
    ["1\n5", "5\n9 9 9 9 9", f"2000\n{_fmt_arr([2000 - i for i in range(2000)])}"],
    _buy_sell_random, _buy_sell_validate, _buy_sell_checker,
))


# =============================================================================
# 9. climb-stairs  --  shape: int
# =============================================================================

def _climb_stairs_random(rng: random.Random) -> str:
    return str(gen_int(rng, 1, 45))


def _climb_stairs_validate(stdin: str) -> bool:
    n = int(stdin)
    return 1 <= n <= 45


def _climb_stairs_checker(stdin: str) -> str:
    """Top-down memoized recursion -- reference is bottom-up iterative."""
    n = int(stdin)
    memo = {0: 1, 1: 1}

    def f(k):
        if k not in memo:
            memo[k] = f(k - 1) + f(k - 2)
        return memo[k]

    return str(f(n))


_register(ProblemInputSpec(
    "climb-stairs", "int",
    {"n_min": 1, "n_max": 45},
    ["1", "45"],
    _climb_stairs_random, _climb_stairs_validate, _climb_stairs_checker,
))


# =============================================================================
# 10. merge-sorted  --  shape: two_int_arrays (each sorted)
# =============================================================================

def _merge_sorted_random(rng: random.Random) -> str:
    n = rng.choice([0, 1, rng.randint(2, 80)])
    m = rng.choice([0, 1, rng.randint(2, 80)])
    a = sorted(gen_int_array(rng, n, -100, 100)) if n else []
    b = sorted(gen_int_array(rng, m, -100, 100)) if m else []
    parts = [str(n)]
    if n:
        parts.append(_fmt_arr(a))
    parts.append(str(m))
    if m:
        parts.append(_fmt_arr(b))
    return "\n".join(parts) + "\n"


def _merge_sorted_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    i = 0
    n = int(lines[i]); i += 1
    a = list(map(int, lines[i].split())) if n else []
    if n:
        i += 1
    m = int(lines[i]); i += 1
    b = list(map(int, lines[i].split())) if m else []
    return (len(a) == n and len(b) == m and 0 <= n <= 10000 and 0 <= m <= 10000
            and a == sorted(a) and b == sorted(b))


def _merge_sorted_checker(stdin: str) -> str:
    """Full sort of the concatenation -- reference does a linear merge."""
    lines = stdin.split("\n")
    i = 0
    n = int(lines[i]); i += 1
    a = list(map(int, lines[i].split())) if n else []
    if n:
        i += 1
    m = int(lines[i]); i += 1
    b = list(map(int, lines[i].split())) if m else []
    return " ".join(map(str, sorted(a + b)))


_register(ProblemInputSpec(
    "merge-sorted", "two_int_arrays",
    {"n_min": 0, "n_max": 10000, "m_min": 0, "m_max": 10000},
    ["0\n0", "1\n5\n0", f"10000\n{_fmt_arr(list(range(10000)))}\n10000\n{_fmt_arr(list(range(10000)))}"],
    _merge_sorted_random, _merge_sorted_validate, _merge_sorted_checker,
))


# =============================================================================
# 11-16. tree-level-order / tree-max-depth / tree-symmetric / tree-balanced /
#        tree-invert / tree-min-depth  --  shape: tree_level_order
# =============================================================================
# No independent checker for the tree problems: all 6 share the exact same
# build() level-order parser, so a "brute-force" re-implementation would
# mostly be re-testing that shared parser a second time, not catching a
# differently-sourced bug in each problem's own (genuinely distinct) logic.

TREE_IDS = [
    "tree-level-order", "tree-max-depth", "tree-symmetric",
    "tree-balanced", "tree-invert", "tree-min-depth",
]


def _gen_tree_tokens(rng: random.Random, max_nodes: int, symmetric_bias: float = 0.0,
                      lo: int = -100, hi: int = 100) -> List[str]:
    """Builds a level-order token list ('N' = missing child) for a random
    binary tree with at most max_nodes real nodes, BFS-style (the same
    shape build() in problem_bank.py expects). symmetric_bias > 0 skews
    toward actually-symmetric trees so tree-symmetric's generator doesn't
    only ever produce 'NO' cases. `lo`/`hi` (Stage 2c) let a caller
    constrain node values -- e.g. tree-sum-root-to-leaf needs digits 0-9."""
    if max_nodes <= 0:
        return ["N"]
    n_real = rng.randint(1, max_nodes)
    tokens = [str(gen_int(rng, lo, hi))]
    real_so_far = 1
    i = 0
    while i < len(tokens) and real_so_far < n_real:
        if tokens[i] == "N":
            i += 1
            continue
        for _ in range(2):
            if real_so_far < n_real and rng.random() < 0.7:
                tokens.append(str(gen_int(rng, lo, hi)))
                real_so_far += 1
            else:
                tokens.append("N")
        i += 1
    if rng.random() < symmetric_bias:
        # Force symmetry: mirror the left subtree's token layout onto the right.
        return _force_symmetric(tokens)
    return tokens


def _force_symmetric(tokens: List[str]) -> List[str]:
    # Simplest reliable symmetric tree: a root with no children, or a root
    # whose two children are equal leaves -- always valid level-order output.
    if len(tokens) == 1:
        return tokens
    root = tokens[0]
    return [root, "5", "5"]


def _max_size_tree_tokens() -> List[str]:
    """A perfect binary tree with exactly 1000 real nodes, no 'N' tokens --
    the stated maximum (<= 1000 real nodes)."""
    return [str((i % 50) + 1) for i in range(1000)]


def _tree_random(rng: random.Random, symmetric_bias: float = 0.0) -> str:
    max_nodes = rng.choice([1, 2, rng.randint(3, 60)])
    return " ".join(_gen_tree_tokens(rng, max_nodes, symmetric_bias))


def _tree_validate(stdin: str) -> bool:
    tokens = stdin.split()
    real_nodes = sum(1 for t in tokens if t != "N")
    return 1 <= real_nodes <= 1000 and all(t == "N" or t.lstrip("-").isdigit() for t in tokens)


for _tid in TREE_IDS:
    _bias = 0.5 if _tid == "tree-symmetric" else (0.5 if _tid == "tree-balanced" else 0.0)
    _register(ProblemInputSpec(
        _tid, "tree_level_order",
        {"real_nodes_min": 1, "real_nodes_max": 1000},
        ["1", "1 2 N", " ".join(_max_size_tree_tokens())],
        (lambda rng, b=_bias: _tree_random(rng, b)),
        _tree_validate, None,
    ))


# ---- Shared BST builder (Stage 2c, Medium batch 1) -------------------------
# Used by tree-validate-bst (mixed with plain random trees), tree-kth-
# smallest-bst, and tree-lca-bst -- all three need a genuinely valid BST,
# not just any binary tree, since their correctness depends on the BST
# property. Builds by inserting distinct values in random order (so the
# resulting shape varies, not just a sorted chain), then serializes with
# the SAME BFS level-order convention _gen_tree_tokens/build() use.

class _BSTNode:
    __slots__ = ("v", "l", "r")

    def __init__(self, v):
        self.v = v
        self.l = None
        self.r = None


def _bst_insert(root, v):
    if root is None:
        return _BSTNode(v)
    if v < root.v:
        root.l = _bst_insert(root.l, v)
    else:
        root.r = _bst_insert(root.r, v)
    return root


def _serialize_level_order(root) -> List[str]:
    if root is None:
        return ["N"]
    tokens = [str(root.v)]
    q = deque([root])
    while q:
        node = q.popleft()
        for child in (node.l, node.r):
            if child is not None:
                tokens.append(str(child.v))
                q.append(child)
            else:
                tokens.append("N")
    return tokens


def _build_random_bst(rng: random.Random, n_nodes: int, lo: int = -1000, hi: int = 1000):
    """Returns (root, values) -- values is the exact set of distinct
    values inserted, so a caller building a 'p q' / 'k' companion line
    can pick from values actually present in the tree."""
    n_nodes = max(1, n_nodes)
    pool = list(range(lo, hi + 1))
    rng.shuffle(pool)
    values = pool[:n_nodes]
    root = None
    insert_order = values[:]
    rng.shuffle(insert_order)
    for v in insert_order:
        root = _bst_insert(root, v)
    return root, values


# =============================================================================
# 17. greedy-assign-cookies  --  shape: two_int_arrays
# =============================================================================

def _cookies_random(rng: random.Random) -> str:
    # Capped at 10, not the stated 10^4 -- its independent checker below
    # is a small-n brute force over value-combinations (Stage 2c), and
    # this generator feeds BOTH the stored-test fill and the
    # differential fuzz, both of which run through that checker.
    n = rng.choice([1, 2, rng.randint(3, 10)])
    m = rng.choice([1, 2, rng.randint(3, 10)])
    g = gen_int_array(rng, n, 1, 20)
    s = gen_int_array(rng, m, 1, 20)
    return f"{n}\n{_fmt_arr(g)}\n{m}\n{_fmt_arr(s)}\n"


def _cookies_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); g = list(map(int, lines[1].split()))
    m = int(lines[2]); s = list(map(int, lines[3].split()))
    return len(g) == n and len(s) == m and 1 <= n <= 10000 and 1 <= m <= 10000


def _cookies_checker(stdin: str) -> str:
    """Small-n brute force over value-combinations (Stage 2c): for
    decreasing k, checks whether SOME k-subset of greeds and SOME
    k-subset of cookie sizes admits a feasible 1-1 assignment -- which,
    for two fixed same-size multisets, is possible iff their SORTED
    forms dominate elementwise (a standard exchange-argument fact,
    independent of the reference's single greedy sweep). Only valid for
    small n, m -- the generator above caps both at 10 specifically so
    this stays fast."""
    lines = stdin.split("\n")
    n = int(lines[0]); g = list(map(int, lines[1].split()))
    m = int(lines[2]); s = list(map(int, lines[3].split()))
    if n > 12 or m > 12:
        raise ValueError("cookies brute-force checker only valid for small n, m")
    from itertools import combinations
    for k in range(min(n, m), 0, -1):
        for gc in combinations(sorted(g), k):
            for sc in combinations(sorted(s), k):
                if all(a <= b for a, b in zip(sorted(gc), sorted(sc))):
                    return str(k)
    return "0"


_register(ProblemInputSpec(
    "greedy-assign-cookies", "two_int_arrays",
    {"n_min": 1, "n_max": 10000, "m_min": 1, "m_max": 10000},
    ["1\n1\n1\n1", "1\n100\n1\n1",
     f"10\n{_fmt_arr([1] * 10)}\n10\n{_fmt_arr([1] * 10)}"],
    _cookies_random, _cookies_validate, _cookies_checker,
))


# =============================================================================
# 18. string-valid-anagram  --  shape: two_strings
# =============================================================================

def _anagram_random(rng: random.Random) -> str:
    length = rng.choice([0, 1, rng.randint(2, 100)])
    a = gen_string(rng, length, LOWER)
    if rng.random() < 0.5:
        b = list(a)
        rng.shuffle(b)
        b = "".join(b)
    else:
        b = gen_string(rng, length, LOWER)
    return f"{a}\n{b}\n"


def _anagram_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    a, b = lines[0], lines[1] if len(lines) > 1 else ""
    return len(a) <= 100000 and len(b) <= 100000


def _anagram_checker(stdin: str) -> str:
    """Counter-equality -- reference compares sorted() lists."""
    from collections import Counter
    lines = stdin.split("\n")
    a, b = lines[0], lines[1] if len(lines) > 1 else ""
    return "YES" if Counter(a) == Counter(b) else "NO"


_register(ProblemInputSpec(
    "string-valid-anagram", "two_strings",
    {"len_min": 0, "len_max": 100000},
    # "\n\n" (two empty LINES), not "\n" -- the reference always does a
    # second input() call, which would raise EOFError against "\n" (a
    # single already-consumed newline leaves nothing for it to read).
    ["\n\n", "a\na\n", f"{'a' * 100000}\n{'a' * 99999 + 'b'}\n"],
    _anagram_random, _anagram_validate, _anagram_checker,
))


# =============================================================================
# 19. string-longest-common-prefix  --  shape: list_of_strings
# =============================================================================

def _lcp_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 30)])
    if rng.random() < 0.5:
        prefix = gen_string(rng, rng.randint(0, 5), LOWER)
        words = [prefix + gen_string(rng, rng.randint(0, 10), LOWER) for _ in range(n)]
    else:
        words = [gen_string(rng, rng.randint(1, 10), LOWER) for _ in range(n)]
    return f"{n}\n" + "\n".join(words) + "\n"


def _lcp_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    words = lines[1:1 + n]
    return len(words) == n and 1 <= n <= 200


_register(ProblemInputSpec(
    "string-longest-common-prefix", "list_of_strings",
    {"n_min": 1, "n_max": 200},
    ["1\na", f"200\n" + "\n".join("prefix" + str(i) for i in range(200))],
    _lcp_random, _lcp_validate, None,
))


# =============================================================================
# 20. string-isomorphic  --  shape: two_strings_equal_length
# =============================================================================

def _isomorphic_random(rng: random.Random) -> str:
    length = rng.choice([0, 1, rng.randint(2, 100)])
    s = gen_string(rng, length, LOWER[:6])
    if rng.random() < 0.5:
        mapping = {}
        used = set()
        t_chars = []
        for ch in s:
            if ch not in mapping:
                choices = [c for c in LOWER[:10] if c not in used]
                mapping[ch] = rng.choice(choices) if choices else ch
                used.add(mapping[ch])
            t_chars.append(mapping[ch])
        t = "".join(t_chars)
    else:
        t = gen_string(rng, length, LOWER[:6])
    return f"{s}\n{t}\n"


def _isomorphic_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    s = lines[0]
    t = lines[1] if len(lines) > 1 else ""
    return len(s) == len(t) and len(s) <= 100000


def _isomorphic_checker(stdin: str) -> str:
    """First-occurrence index-pattern matching (Stage 2c): s and t are
    isomorphic iff mapping each character to the index of its first
    occurrence gives the same sequence for both -- genuinely different
    representation from the reference's mutual m1/m2 dict-consistency
    walk, though both are O(n)."""
    lines = stdin.split("\n")
    s = lines[0]
    t = lines[1] if len(lines) > 1 else ""
    if len(s) != len(t):
        return "NO"
    first = {}
    pattern_s = [first.setdefault(c, i) for i, c in enumerate(s)]
    first = {}
    pattern_t = [first.setdefault(c, i) for i, c in enumerate(t)]
    return "YES" if pattern_s == pattern_t else "NO"


_register(ProblemInputSpec(
    "string-isomorphic", "two_strings_equal_length",
    {"len_min": 0, "len_max": 100000},
    # "\n\n", not "\n" -- same EOF reasoning as string-valid-anagram above.
    ["\n\n", "a\na\n", "ab\naa\n"],
    _isomorphic_random, _isomorphic_validate, _isomorphic_checker,
))


# =============================================================================
# 21. string-word-pattern  --  shape: pattern_and_words
# =============================================================================

def _word_pattern_random(rng: random.Random) -> str:
    length = rng.choice([1, 2, rng.randint(3, 30)])
    pattern = gen_string(rng, length, "abc")
    if rng.random() < 0.5:
        mapping = {}
        used = set()
        words = []
        for ch in pattern:
            if ch not in mapping:
                mapping[ch] = f"w{len(used)}"
                used.add(mapping[ch])
            words.append(mapping[ch])
    else:
        words = [f"w{rng.randint(0, length)}" for _ in pattern]
    return f"{pattern}\n{' '.join(words)}\n"


def _word_pattern_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    pattern = lines[0]
    return 1 <= len(pattern) <= 300


def _word_pattern_checker(stdin: str) -> str:
    """Same first-occurrence index-pattern trick as string-isomorphic's
    checker, applied to the pattern's characters and the words list --
    an independent representation from the reference's mutual
    dict-consistency walk."""
    lines = stdin.split("\n")
    pattern = lines[0]
    words = lines[1].split() if len(lines) > 1 else []
    if len(pattern) != len(words):
        return "NO"
    first = {}
    pattern_seq = [first.setdefault(c, i) for i, c in enumerate(pattern)]
    first = {}
    words_seq = [first.setdefault(w, i) for i, w in enumerate(words)]
    return "YES" if pattern_seq == words_seq else "NO"


_register(ProblemInputSpec(
    "string-word-pattern", "pattern_and_words",
    {"pattern_len_min": 1, "pattern_len_max": 300},
    ["a\ndog", f"{'a' * 300}\n" + " ".join(["w0"] * 300)],
    _word_pattern_random, _word_pattern_validate, _word_pattern_checker,
))


# =============================================================================
# 22. string-roman-to-integer  --  shape: string (constrained alphabet)
# =============================================================================

def _int_to_roman(n: int) -> str:
    vals = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
            (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = []
    for v, sym in vals:
        while n >= v:
            out.append(sym)
            n -= v
    return "".join(out)


def _roman_random(rng: random.Random) -> str:
    n = rng.choice([1, 3999, rng.randint(2, 3998)])
    return _int_to_roman(n)


def _roman_validate(stdin: str) -> bool:
    return 1 <= len(stdin) <= 20 and all(c in "IVXLCDM" for c in stdin)


def _roman_checker(stdin: str) -> str:
    """Left-to-right with 2-char lookahead for subtractive pairs -- reference
    scans right-to-left tracking the previous symbol's value."""
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    subtractive = {"IV": 4, "IX": 9, "XL": 40, "XC": 90, "CD": 400, "CM": 900}
    total = 0
    i = 0
    while i < len(stdin):
        pair = stdin[i:i + 2]
        if pair in subtractive:
            total += subtractive[pair]
            i += 2
        else:
            total += vals[stdin[i]]
            i += 1
    return str(total)


_register(ProblemInputSpec(
    "string-roman-to-integer", "string",
    {"value_min": 1, "value_max": 3999},
    ["I", _int_to_roman(3999)],
    _roman_random, _roman_validate, _roman_checker,
))


# =============================================================================
# 23. tp-remove-duplicates-sorted  --  shape: sorted_int_array
# =============================================================================

def _dedup_sorted_random(rng: random.Random) -> str:
    n = rng.choice([0, 1, rng.randint(2, 100)])
    if n == 0:
        # The reference ALWAYS does a second input() call regardless of n --
        # "0\n\n" (an explicit, present-but-empty second line), not "0\n"
        # (which would leave nothing for that second input() to read and
        # raise EOFError). Matches the bank's own pre-existing "0\n\n" case.
        return "0\n\n"
    raw = sorted(gen_int_array(rng, n, -50, 50))
    if rng.random() < 0.4:
        # Force some duplicates so "all equal"/"duplicates" cases are common.
        pivot = raw[0]
        raw = sorted([pivot if rng.random() < 0.5 else v for v in raw])
    return f"{n}\n{_fmt_arr(raw)}\n"


def _dedup_sorted_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split())) if n and len(lines) > 1 and lines[1].strip() else []
    return len(arr) == n and 0 <= n <= 30000 and arr == sorted(arr)


def _dedup_sorted_checker(stdin: str) -> str:
    """sorted(set(...)) -- an entirely different approach from the
    reference's in-place walk-and-compact."""
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split())) if n and len(lines) > 1 and lines[1].strip() else []
    deduped = sorted(set(arr))
    return f"{len(deduped)}\n{' '.join(map(str, deduped))}"


_register(ProblemInputSpec(
    "tp-remove-duplicates-sorted", "sorted_int_array",
    {"n_min": 0, "n_max": 30000},
    ["0\n\n", "1\n5\n", "5\n2 2 2 2 2\n", f"30000\n{_fmt_arr([i // 3 for i in range(30000)])}\n"],
    _dedup_sorted_random, _dedup_sorted_validate, _dedup_sorted_checker,
))


# =============================================================================
# 24. arr-majority-element  --  shape: majority_array
# =============================================================================

def _majority_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 100)])
    majority_val = gen_int(rng, -50, 50)
    majority_count = n // 2 + 1
    rest_count = n - majority_count
    arr = [majority_val] * majority_count + gen_int_array(rng, rest_count, -50, 50)
    rng.shuffle(arr)
    return f"{n}\n{_fmt_arr(arr)}"


def _majority_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    if len(arr) != n or not (1 <= n <= 50000):
        return False
    from collections import Counter
    return Counter(arr).most_common(1)[0][1] > n // 2


def _majority_checker(stdin: str) -> str:
    """Counter.most_common -- reference uses Boyer-Moore voting."""
    from collections import Counter
    lines = stdin.split("\n")
    arr = list(map(int, lines[1].split()))
    return str(Counter(arr).most_common(1)[0][0])


_register(ProblemInputSpec(
    "arr-majority-element", "majority_array",
    {"n_min": 1, "n_max": 50000},
    ["1\n7", f"50000\n{_fmt_arr([1] * 25001 + [2] * 24999)}"],
    _majority_random, _majority_validate, _majority_checker,
))


# =============================================================================
# STAGE 2c, MEDIUM BATCH 1 (first 21 Medium problems by order in
# problem_bank.py). No checkers required for this batch (none declared
# below) -- only Easy problems got the "close the checker gap" treatment
# this stage. New shapes needed beyond the Easy-stage core/composed set:
#
#   coins_and_amount        coin-change
#   coins_and_target_count  combination-sum-count
#   binary_grid             num-islands
#   rotated_sorted_array    search-rotated
#   tree_and_target         tree-path-sum
#   bst_and_k               tree-kth-smallest-bst
#   bst_and_pq              tree-lca-bst
#   interval_list           greedy-merge-intervals, greedy-non-overlapping-removals
#
# Reused as-is from the Easy stage: list_of_strings (group-anagrams),
# string (longest-substring-no-repeat, longest-palindromic), int_array
# (product-except-self, container-water, greedy-jump-game), matrix
# (rotate-image -- its first real use), two_int_arrays
# (greedy-activity-selection), tree_level_order (the plain-tree and BST
# problems below, via _gen_tree_tokens/_build_random_bst).
# =============================================================================

# ---- group-anagrams  --  shape: list_of_strings ----------------------------

def _anagrams_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 40)])
    words = []
    for _ in range(n):
        length = rng.randint(1, 6)
        if rng.random() < 0.4 and words:
            # Reuse an earlier word's letters, shuffled -- guarantees some
            # real anagram groups instead of (almost certainly) all-distinct.
            base = rng.choice(words)
            chars = list(base)
            rng.shuffle(chars)
            words.append("".join(chars))
        else:
            words.append(gen_string(rng, length, "abcde"))
    return f"{n}\n" + " ".join(words) + "\n"


def _anagrams_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    words = lines[1].split() if len(lines) > 1 else []
    return len(words) == n and 1 <= n <= 10000


_ANAGRAMS_LARGE_WORDS = [
    "".join(chr(ord('a') + (i * 7 + j) % 5) for j in range(6)) for i in range(10000)
]
_register(ProblemInputSpec(
    "group-anagrams", "list_of_strings",
    {"n_min": 1, "n_max": 10000},
    ["1\nsolo", "4\nab ba abc cba"],
    _anagrams_random, _anagrams_validate, None,
    large_cases=[
        # Intended complexity: O(n * L log L) (sort each word's letters,
        # group by the sorted tuple). A naive O(n^2 * L) pairwise-compare
        # would be 10^4 * 10^4 * 6 = 6*10^8 -- plausibly too slow.
        f"10000\n" + " ".join(_ANAGRAMS_LARGE_WORDS) + "\n",
        f"10000\n" + " ".join(["zzzzzz"] * 10000) + "\n",
    ],
))


# ---- longest-substring-no-repeat  --  shape: string -------------------------

def _no_repeat_random(rng: random.Random) -> str:
    length = rng.choice([0, 1, rng.randint(2, 200)])
    if length == 0:
        # A bare "" gives input() zero bytes at all -- EOFError. An
        # empty LINE ("\n") is what reads back as "" via input().
        return "\n"
    return gen_string(rng, length, "ab")


def _no_repeat_validate(stdin: str) -> bool:
    return len(stdin) <= 50001  # +1 tolerates the "\n" stand-in for an empty string


_register(ProblemInputSpec(
    "longest-substring-no-repeat", "string",
    {"len_min": 0, "len_max": 50000},
    ["\n", "a"],
    _no_repeat_random, _no_repeat_validate, None,
    large_cases=[
        # Intended complexity: O(n) sliding window. A naive O(n^2)
        # check-every-substring approach is 2.5*10^9 at n=5*10^4 -- times out.
        "ab" * 25000,
        "".join(chr(ord('a') + i % 26) for i in range(50000)),
    ],
))


# ---- coin-change  --  shape: coins_and_amount (NEW) ------------------------

def _coin_change_random(rng: random.Random) -> str:
    n = rng.randint(1, 12)
    coins = rng.sample(range(1, 50), n)
    amount = rng.randint(1, 200)
    return f"{n}\n{_fmt_arr(coins)}\n{amount}\n"


def _coin_change_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); coins = list(map(int, lines[1].split()))
    amount = int(lines[2])
    return len(coins) == n and 1 <= n <= 12 and 1 <= amount <= 10000


_register(ProblemInputSpec(
    "coin-change", "coins_and_amount",
    {"n_min": 1, "n_max": 12, "amount_min": 1, "amount_max": 10000},
    ["1\n2\n3", "1\n1\n1", "3\n1 3 4\n6"],
    _coin_change_random, _coin_change_validate, None,
    large_cases=[
        # Intended complexity: O(n * amount) DP (the reference's own
        # approach, pseudo-polynomial). The problem's n<=12 cap means no
        # naive-exponential-recursion variant could realistically be worse
        # here than this DP already is; this just confirms the DP itself
        # stays fast at the full amount ceiling.
        "12\n" + _fmt_arr([1, 3, 4, 5, 7, 9, 11, 13, 17, 19, 23, 29]) + "\n10000\n",
        "12\n" + _fmt_arr([2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]) + "\n9999\n",
    ],
))


# ---- product-except-self  --  shape: int_array -----------------------------

def _product_except_self_random(rng: random.Random) -> str:
    n = rng.choice([2, 3, rng.randint(4, 60)])
    arr = gen_int_array(rng, n, -5, 5)
    return f"{n}\n{_fmt_arr(arr)}\n"


def _product_except_self_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); arr = list(map(int, lines[1].split()))
    return len(arr) == n and 2 <= n <= 100000


_register(ProblemInputSpec(
    "product-except-self", "int_array",
    {"n_min": 2, "n_max": 100000},
    ["2\n2 3", "3\n1 1 1"],
    _product_except_self_random, _product_except_self_validate, None,
    large_cases=[
        # Intended complexity: O(n) (prefix/suffix product passes). A
        # naive O(n^2) (recompute each product from scratch) is 10^10 at
        # n=10^5 -- times out. Mostly-1 values with only a handful of
        # small perturbations (not every-5th-element alternating +-2,
        # which compounds to a 40000-digit product and trips Python
        # 3.11+'s int-to-str conversion limit, confirmed directly) keeps
        # every printed product small while still exercising the full
        # n=10^5 loop count the complexity gap is actually about.
        f"100000\n{_fmt_arr([(2 if i % 5000 == 0 else (-2 if i % 7000 == 0 else 1)) for i in range(100000)])}\n",
        f"100000\n{_fmt_arr([1] * 100000)}\n",
    ],
))


# ---- rotate-image  --  shape: matrix ---------------------------------------

def _rotate_image_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 15)])
    m = gen_matrix(rng, n, n, -9, 9)
    return f"{n}\n" + "\n".join(_fmt_arr(row) for row in m) + "\n"


def _rotate_image_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    rows = lines[1:1 + n]
    return len(rows) == n and 1 <= n <= 100 and all(len(r.split()) == n for r in rows)


_register(ProblemInputSpec(
    "rotate-image", "matrix",
    {"n_min": 1, "n_max": 100},
    ["1\n5", "2\n1 2\n3 4"],
    _rotate_image_random, _rotate_image_validate, None,
    large_cases=[
        # Intended complexity: O(n^2) -- optimal and required (every one
        # of the n^2 output cells must be produced), so no asymptotically
        # slower alternative exists to time out here; this large case
        # just confirms the reference handles the stated ceiling.
        f"100\n" + "\n".join(_fmt_arr([((r * 100 + c) % 19) - 9 for c in range(100)]) for r in range(100)) + "\n",
        f"100\n" + "\n".join(_fmt_arr([1] * 100) for _ in range(100)) + "\n",
    ],
))


# ---- num-islands  --  shape: binary_grid (NEW) -----------------------------

def _num_islands_random(rng: random.Random) -> str:
    rows = rng.choice([1, 2, rng.randint(3, 15)])
    cols = rng.choice([1, 2, rng.randint(3, 15)])
    grid = gen_matrix(rng, rows, cols, 0, 1)
    return f"{rows} {cols}\n" + "\n".join(_fmt_arr(row) for row in grid) + "\n"


def _num_islands_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    rows, cols = map(int, lines[0].split())
    grid_lines = lines[1:1 + rows]
    return (len(grid_lines) == rows and 1 <= rows <= 300 and 1 <= cols <= 300
            and all(len(r.split()) == cols for r in grid_lines)
            and all(v in ("0", "1") for r in grid_lines for v in r.split()))


_register(ProblemInputSpec(
    "num-islands", "binary_grid",
    {"rows_min": 1, "rows_max": 300, "cols_min": 1, "cols_max": 300},
    ["1 1\n0", "2 4\n1 0 1 0\n0 1 0 1"],
    _num_islands_random, _num_islands_validate, None,
    large_cases=[
        # Intended complexity: O(rows*cols) (visit every cell once).
        # Deliberately a CHECKERBOARD at the full 300x300 ceiling, not one
        # giant blob -- the reference's DFS is plain recursion with no
        # explicit stack, so a single large connected island could recurse
        # deep enough to risk a genuine C-stack overflow (not just a slow
        # run); many small islands exercise the full cell count safely.
        "300 300\n" + "\n".join(_fmt_arr([(r + c) % 2 for c in range(300)]) for r in range(300)) + "\n",
        "300 300\n" + "\n".join(_fmt_arr([0] * 300) for _ in range(300)) + "\n",
    ],
))


# ---- search-rotated  --  shape: rotated_sorted_array (NEW) -----------------

def _search_rotated_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 60)])
    base = sorted(rng.sample(range(-500, 500), n))
    pivot = rng.randint(0, n - 1)
    arr = base[pivot:] + base[:pivot]
    target = rng.choice(arr) if rng.random() < 0.6 else rng.randint(-600, 600)
    return f"{n}\n{_fmt_arr(arr)}\n{target}\n"


def _search_rotated_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); arr = list(map(int, lines[1].split()))
    int(lines[2])
    return len(arr) == n and 1 <= n <= 10000 and len(set(arr)) == n


_SEARCH_ROTATED_BASE = sorted(range(-5000, 5000))
_SEARCH_ROTATED_LARGE = _SEARCH_ROTATED_BASE[3000:] + _SEARCH_ROTATED_BASE[:3000]
_register(ProblemInputSpec(
    "search-rotated", "rotated_sorted_array",
    {"n_min": 1, "n_max": 10000},
    ["1\n1\n0", "5\n5 1 2 3 4\n1"],
    _search_rotated_random, _search_rotated_validate, None,
    large_cases=[
        # Intended complexity: O(log n) binary search. HONEST NOTE: at
        # this problem's own ceiling (n<=10^4), even the "bad" O(n) linear
        # scan finishes in microseconds -- there's no input size within
        # the stated constraints where a slower-but-still-polynomial
        # approach would time out while O(log n) succeeds. These two
        # large inputs confirm correctness/timing at the ceiling only,
        # not a complexity gap.
        f"10000\n{_fmt_arr(_SEARCH_ROTATED_LARGE)}\n{_SEARCH_ROTATED_LARGE[0]}\n",
        f"10000\n{_fmt_arr(_SEARCH_ROTATED_LARGE)}\n123456\n",
    ],
))


# ---- container-water  --  shape: int_array ---------------------------------

def _container_water_random(rng: random.Random) -> str:
    n = rng.choice([2, 3, rng.randint(4, 60)])
    arr = gen_int_array(rng, n, 0, 100)
    return f"{n}\n{_fmt_arr(arr)}\n"


def _container_water_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); arr = list(map(int, lines[1].split()))
    return len(arr) == n and 2 <= n <= 100000


_register(ProblemInputSpec(
    "container-water", "int_array",
    {"n_min": 2, "n_max": 100000},
    ["2\n1 1", "5\n1 2 3 4 5"],
    _container_water_random, _container_water_validate, None,
    large_cases=[
        # Intended complexity: O(n) two-pointer. A naive O(n^2) all-pairs
        # check is 10^10 at n=10^5 -- times out.
        f"100000\n{_fmt_arr([(i * 13) % 1000 for i in range(100000)])}\n",
        f"100000\n{_fmt_arr([100000 - i for i in range(100000)])}\n",
    ],
))


# ---- longest-palindromic  --  shape: string --------------------------------

def _longest_palindromic_random(rng: random.Random) -> str:
    length = rng.randint(1, 40)
    core = gen_string(rng, length, "ab")
    if rng.random() < 0.5:
        core = core + core[::-1]
    return core


def _longest_palindromic_validate(stdin: str) -> bool:
    return 1 <= len(stdin) <= 1000


_register(ProblemInputSpec(
    "longest-palindromic", "string",
    {"len_min": 1, "len_max": 1000},
    ["a", "ac"],
    _longest_palindromic_random, _longest_palindromic_validate, None,
    large_cases=[
        # Intended complexity: O(n^2) (expand-around-every-center -- the
        # reference's own approach, and what n<=1000 is specifically
        # sized for). A naive O(n^3) check-every-substring-for-palindrome
        # is ~10^9 at n=1000 -- plausibly too slow.
        "a" * 1000,
        ("ab" * 500),
    ],
))


# ---- combination-sum-count  --  shape: coins_and_target_count (NEW) --------

def _combo_sum_count_random(rng: random.Random) -> str:
    n = rng.randint(1, 6)
    coins = rng.sample(range(1, 15), n)
    target = rng.randint(1, 40)
    return f"{n}\n{_fmt_arr(coins)}\n{target}\n"


def _combo_sum_count_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); coins = list(map(int, lines[1].split()))
    target = int(lines[2])
    return len(coins) == n and len(set(coins)) == n and 1 <= n <= 30 and 1 <= target <= 500


_register(ProblemInputSpec(
    "combination-sum-count", "coins_and_target_count",
    {"n_min": 1, "n_max": 30, "target_min": 1, "target_max": 500},
    ["2\n2 3\n5", "1\n2\n1"],
    _combo_sum_count_random, _combo_sum_count_validate, None,
    large_cases=[
        # Intended complexity: O(n * target) with memoization. The
        # reference itself is UNMEMOIZED DFS -- its real worst case is
        # combinatorial (e.g. coins=[1,2,3,4,5], target=500 alone takes
        # >8s, confirmed directly), not n*target. Picking coins close in
        # value to the target keeps the branching (and so the reference's
        # own runtime) bounded while still exercising the full n=30 and
        # target=500 ceilings: at most 1 of these ~500-valued coins can
        # ever fit in a 500 target, so the DFS is effectively O(n).
        "30\n" + _fmt_arr(list(range(471, 501))) + "\n500\n",
        # Second large case instead maxes out n (30 SMALL coins) but
        # keeps target modest (60, not 500) so branching stays bounded --
        # the reverse trade-off from the case above.
        "30\n" + _fmt_arr(list(range(1, 31))) + "\n60\n",
    ],
))


# ---- tree-validate-bst  --  shape: tree_level_order ------------------------

def _validate_bst_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 60)])
    if rng.random() < 0.5:
        root, _ = _build_random_bst(rng, n)
        tokens = _serialize_level_order(root)
    else:
        tokens = _gen_tree_tokens(rng, n)
    return " ".join(tokens)


_BST_TOKEN_VALIDATE = _tree_validate  # same shape/bounds as plain trees

_VALIDATE_BST_LARGE_VALID = " ".join(_serialize_level_order(_build_random_bst(random.Random("2c-validate-bst-valid"), 1000)[0]))
_VALIDATE_BST_LARGE_INVALID = " ".join(_gen_tree_tokens(random.Random("2c-validate-bst-invalid"), 1000))
_register(ProblemInputSpec(
    "tree-validate-bst", "tree_level_order",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["5 N 3", "3 1 5"],
    _validate_bst_random, _BST_TOKEN_VALIDATE, None,
    large_cases=[
        # Intended complexity: O(n) (one bounds-checked recursive walk).
        # Both large cases are built via randomized-order insertion /
        # the existing bushy tree generator specifically to keep tree
        # HEIGHT small -- a degenerate 1000-deep chain would risk
        # RecursionError against the reference's plain (unlimited-depth)
        # recursive valid(), since it never raises sys.setrecursionlimit.
        _VALIDATE_BST_LARGE_VALID,
        _VALIDATE_BST_LARGE_INVALID,
    ],
))


# ---- tree-diameter  --  shape: tree_level_order ----------------------------

def _tree_diameter_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 60)])
    return " ".join(_gen_tree_tokens(rng, n))


_DIAMETER_LARGE = " ".join(_gen_tree_tokens(random.Random("2c-diameter-large"), 1000))
_register(ProblemInputSpec(
    "tree-diameter", "tree_level_order",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["1 2 N N 3", "1 2 3 4 5"],
    _tree_diameter_random, _tree_validate, None,
    large_cases=[
        # Intended complexity: O(n). Same recursion-depth caution as
        # tree-validate-bst above -- the bushy generator keeps height low.
        _DIAMETER_LARGE,
        " ".join(_gen_tree_tokens(random.Random("2c-diameter-large-2"), 1000)),
    ],
))


# ---- tree-path-sum  --  shape: tree_and_target (NEW) -----------------------

def _tree_path_sum_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 60)])
    tokens = _gen_tree_tokens(rng, n)
    if rng.random() < 0.5:
        # Exactly reconstructing a root-to-leaf sum would mean re-walking
        # build()'s own parsing here -- instead, sum a random-length
        # prefix of the real values in BFS token order as a plausible
        # stand-in target (close enough to exercise real YES cases
        # without duplicating the tree-walk logic under test).
        reals = [int(t) for t in tokens if t != "N"]
        k = rng.randint(1, len(reals))
        target = sum(reals[:k])
    else:
        target = rng.randint(-200, 200)
    return " ".join(tokens) + f"\n{target}\n"


def _tree_path_sum_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    tokens = lines[0].split()
    int(lines[1])
    return _tree_validate(lines[0])


_PATH_SUM_LARGE_TOKENS = _gen_tree_tokens(random.Random("2c-path-sum-large"), 1000)
_register(ProblemInputSpec(
    "tree-path-sum", "tree_and_target",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["1 2 3\n5", "1\n1"],
    _tree_path_sum_random, _tree_path_sum_validate, None,
    large_cases=[
        # Intended complexity: O(n). Recursion-depth caution as above.
        " ".join(_PATH_SUM_LARGE_TOKENS) + f"\n{sum(int(t) for t in _PATH_SUM_LARGE_TOKENS if t != 'N')}\n",
        " ".join(_PATH_SUM_LARGE_TOKENS) + "\n999999\n",
    ],
))


# ---- tree-kth-smallest-bst  --  shape: bst_and_k (NEW) ---------------------

def _kth_smallest_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 60)])
    root, values = _build_random_bst(rng, n)
    k = rng.randint(1, len(values))
    return " ".join(_serialize_level_order(root)) + f"\n{k}\n"


def _kth_smallest_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    tokens = lines[0].split()
    real_nodes = sum(1 for t in tokens if t != "N")
    k = int(lines[1])
    return _tree_validate(lines[0]) and 1 <= k <= real_nodes


_KTH_ROOT, _KTH_VALUES = _build_random_bst(random.Random("2c-kth-large"), 1000)
_register(ProblemInputSpec(
    "tree-kth-smallest-bst", "bst_and_k",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["5 3 8 1 4 7 9\n1", "1\n1"],
    _kth_smallest_random, _kth_smallest_validate, None,
    large_cases=[
        # Intended complexity: O(h + k) (inorder with early exit once k
        # values are collected) -- effectively O(n) worst case for large k.
        " ".join(_serialize_level_order(_KTH_ROOT)) + "\n1\n",
        " ".join(_serialize_level_order(_KTH_ROOT)) + f"\n{len(_KTH_VALUES)}\n",
    ],
))


# ---- tree-lca-bst  --  shape: bst_and_pq (NEW) -----------------------------

def _lca_bst_random(rng: random.Random) -> str:
    n = rng.choice([2, 3, rng.randint(4, 60)])
    root, values = _build_random_bst(rng, n)
    p, q = rng.sample(values, 2)
    return " ".join(_serialize_level_order(root)) + f"\n{p} {q}\n"


def _lca_bst_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    p, q = map(int, lines[1].split())
    return _tree_validate(lines[0]) and p != q


_LCA_ROOT, _LCA_VALUES = _build_random_bst(random.Random("2c-lca-large"), 1000)
_register(ProblemInputSpec(
    "tree-lca-bst", "bst_and_pq",
    {"real_nodes_min": 2, "real_nodes_max": 1000},
    ["5 3 8 1 4 7 9\n1 4", "6 2 8 0 4 7 9\n0 9"],
    _lca_bst_random, _lca_bst_validate, None,
    large_cases=[
        # Intended complexity: O(h) -- the reference's iterative descent,
        # one comparison per level. O(log n) for the balanced-ish tree
        # our randomized-insertion builder produces.
        " ".join(_serialize_level_order(_LCA_ROOT)) + f"\n{_LCA_VALUES[0]} {_LCA_VALUES[1]}\n",
        " ".join(_serialize_level_order(_LCA_ROOT)) + f"\n{_LCA_VALUES[-1]} {_LCA_VALUES[-2]}\n",
    ],
))


# ---- tree-sum-root-to-leaf  --  shape: tree_level_order (digit-valued) -----

def _sum_root_to_leaf_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 60)])
    return " ".join(_gen_tree_tokens(rng, n, lo=0, hi=9))


def _sum_root_to_leaf_validate(stdin: str) -> bool:
    tokens = stdin.split()
    real_nodes = sum(1 for t in tokens if t != "N")
    return (1 <= real_nodes <= 1000
            and all(t == "N" or (t.isdigit() and len(t) == 1) for t in tokens))


_SUM_R2L_LARGE = " ".join(_gen_tree_tokens(random.Random("2c-sum-r2l-large"), 1000, lo=0, hi=9))
_register(ProblemInputSpec(
    "tree-sum-root-to-leaf", "tree_level_order",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["1 2 3", "0"],
    _sum_root_to_leaf_random, _sum_root_to_leaf_validate, None,
    large_cases=[
        # Intended complexity: O(n). Recursion-depth caution as above --
        # the bushy generator keeps height low despite 1000 nodes.
        _SUM_R2L_LARGE,
        " ".join(_gen_tree_tokens(random.Random("2c-sum-r2l-large-2"), 1000, lo=0, hi=9)),
    ],
))


# ---- tree-right-side-view  --  shape: tree_level_order ---------------------

def _right_side_view_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 60)])
    return " ".join(_gen_tree_tokens(rng, n))


_RIGHT_VIEW_LARGE = " ".join(_gen_tree_tokens(random.Random("2c-right-view-large"), 1000))
_register(ProblemInputSpec(
    "tree-right-side-view", "tree_level_order",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["1 N 2", "1 2 3 4"],
    _right_side_view_random, _tree_validate, None,
    large_cases=[
        # Intended complexity: O(n). Iterative BFS reference -- no
        # recursion-depth concern here, but kept at the same bushy shape
        # as the others for consistency.
        _RIGHT_VIEW_LARGE,
        " ".join(_gen_tree_tokens(random.Random("2c-right-view-large-2"), 1000)),
    ],
))


# ---- greedy-activity-selection  --  shape: two_int_arrays ------------------

def _activity_selection_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 60)])
    starts = gen_int_array(rng, n, 0, 100)
    ends = [s + rng.randint(1, 20) for s in starts]
    return f"{n}\n{_fmt_arr(starts)}\n{_fmt_arr(ends)}\n"


def _activity_selection_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); starts = list(map(int, lines[1].split())); ends = list(map(int, lines[2].split()))
    return (len(starts) == n and len(ends) == n and 1 <= n <= 10000
            and all(e >= s for s, e in zip(starts, ends)))


_ACT_SEL_LARGE_STARTS = [(i * 3) % 10000 for i in range(10000)]
_ACT_SEL_LARGE_ENDS = [s + 5 for s in _ACT_SEL_LARGE_STARTS]
_register(ProblemInputSpec(
    "greedy-activity-selection", "two_int_arrays",
    {"n_min": 1, "n_max": 10000},
    ["1\n0\n5", "3\n1 1 1\n2 2 2"],
    _activity_selection_random, _activity_selection_validate, None,
    large_cases=[
        # Intended complexity: O(n log n) (sort by end time). A naive
        # O(n^2) pairwise overlap-and-select scan is 10^8 at n=10^4 --
        # plausibly, though not guaranteed, too slow in pure Python.
        f"10000\n{_fmt_arr(_ACT_SEL_LARGE_STARTS)}\n{_fmt_arr(_ACT_SEL_LARGE_ENDS)}\n",
        f"10000\n{_fmt_arr([0] * 10000)}\n{_fmt_arr([1] * 10000)}\n",
    ],
))


# ---- greedy-merge-intervals / greedy-non-overlapping-removals -------------
# shape: interval_list (NEW) -- n lines of "start end"

def _interval_list_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 60)])
    lines = [str(n)]
    for _ in range(n):
        s = rng.randint(0, 100)
        e = s + rng.randint(0, 20)
        lines.append(f"{s} {e}")
    return "\n".join(lines) + "\n"


def _interval_list_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    ivs = lines[1:1 + n]
    if len(ivs) != n or not (1 <= n <= 10000):
        return False
    for iv in ivs:
        s, e = map(int, iv.split())
        if e < s:
            return False
    return True


def _interval_list_large(seed: str) -> str:
    rng = random.Random(seed)
    n = 10000
    lines = [str(n)]
    for _ in range(n):
        s = rng.randint(0, 2000)
        e = s + rng.randint(0, 10)
        lines.append(f"{s} {e}")
    return "\n".join(lines) + "\n"


_register(ProblemInputSpec(
    "greedy-merge-intervals", "interval_list",
    {"n_min": 1, "n_max": 10000},
    ["1\n1 1", "2\n1 4\n4 5"],
    _interval_list_random, _interval_list_validate, None,
    large_cases=[
        # Intended complexity: O(n log n) (sort by start, one merge pass).
        # A naive O(n^2) pairwise merge-and-rescan is 10^8 at n=10^4 --
        # plausibly too slow. Many overlapping intervals (small range,
        # large n) maximizes merge work.
        _interval_list_large("2c-merge-intervals-large-1"),
        _interval_list_large("2c-merge-intervals-large-2"),
    ],
))

_register(ProblemInputSpec(
    "greedy-non-overlapping-removals", "interval_list",
    {"n_min": 1, "n_max": 10000},
    ["1\n1 2", "2\n1 2\n1 2"],
    _interval_list_random, _interval_list_validate, None,
    large_cases=[
        # Same reasoning as greedy-merge-intervals above.
        _interval_list_large("2c-non-overlap-large-1"),
        _interval_list_large("2c-non-overlap-large-2"),
    ],
))


# ---- greedy-jump-game  --  shape: int_array --------------------------------

def _jump_game_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 60)])
    arr = gen_int_array(rng, n, 0, 3)
    return f"{n}\n{_fmt_arr(arr)}\n"


def _jump_game_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); arr = list(map(int, lines[1].split()))
    return len(arr) == n and 1 <= n <= 100000 and all(v >= 0 for v in arr)


_register(ProblemInputSpec(
    "greedy-jump-game", "int_array",
    {"n_min": 1, "n_max": 100000},
    ["1\n0", "3\n1 0 1"],
    _jump_game_random, _jump_game_validate, None,
    large_cases=[
        # Intended complexity: O(n) (single greedy reach-tracking pass). A
        # naive exhaustive/DFS-over-jump-choices approach branches up to
        # ~4 ways per position and would never finish at n=10^5 (an
        # exponential blowup), while the greedy pass is instant.
        f"100000\n{_fmt_arr([(i * 5) % 4 for i in range(100000)])}\n",
        f"100000\n{_fmt_arr([1] * 100000)}\n",
    ],
))


# =============================================================================
# Public builder
# =============================================================================

def build_test_inputs(problem_id: str, visible_inputs: List[str], target_total: int = 10,
                       seed: Optional[str] = None) -> List[str]:
    """Keeps `visible_inputs` (the problem's existing first N, e.g. its 2
    visible samples) exactly as-is and in order, then fills up to
    `target_total` with this problem's declared edge cases first, then
    seeded-random cases -- skipping any duplicate of what's already been
    kept. Deterministic for a given seed (defaults to the problem_id
    itself)."""
    spec = SPECS[problem_id]
    rng = random.Random(seed if seed is not None else f"stage2b:{problem_id}")
    out = list(visible_inputs)
    seen = set(out)

    for edge in spec.edge_cases:
        if len(out) >= target_total:
            break
        if edge not in seen:
            out.append(edge)
            seen.add(edge)

    attempts = 0
    while len(out) < target_total and attempts < target_total * 50:
        attempts += 1
        candidate = spec.random_input(rng)
        if candidate not in seen:
            out.append(candidate)
            seen.add(candidate)

    return out


def build_test_inputs_with_large(problem_id: str, visible_inputs: List[str], target_total: int = 14,
                                  large_count: int = 2, seed: Optional[str] = None) -> List[str]:
    """Stage 2c variant: same edge-cases-then-random fill as
    build_test_inputs, but reserves the LAST `large_count` slots for
    this problem's declared `large_cases` -- inputs sized specifically
    to stress its intended complexity (see each registration's own
    comment for what that complexity is and why). Order is always:
    visible, then edge, then random, then large."""
    spec = SPECS[problem_id]
    if not spec.large_cases or len(spec.large_cases) < large_count:
        raise ValueError(f"{problem_id}: needs at least {large_count} large_cases, has {spec.large_cases}")
    rng = random.Random(seed if seed is not None else f"stage2c:{problem_id}")
    out = list(visible_inputs)
    seen = set(out)
    fill_target = target_total - large_count

    for edge in spec.edge_cases:
        if len(out) >= fill_target:
            break
        if edge not in seen:
            out.append(edge)
            seen.add(edge)

    attempts = 0
    while len(out) < fill_target and attempts < fill_target * 50:
        attempts += 1
        candidate = spec.random_input(rng)
        if candidate not in seen:
            out.append(candidate)
            seen.add(candidate)

    added_large = 0
    for large in spec.large_cases:
        if added_large >= large_count:
            break
        if large not in seen:
            out.append(large)
            seen.add(large)
            added_large += 1
    if added_large < large_count:
        raise ValueError(f"{problem_id}: large_cases collided with earlier inputs, only added {added_large}")

    return out
