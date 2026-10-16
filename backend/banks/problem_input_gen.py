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


def _anagrams_checker(stdin: str) -> str:
    """Independent of the reference's sort-the-letters canonicalization:
    groups by a 26-length per-letter COUNT vector instead (no sorting at
    all). Same O(n*L) order, so it stays fast on the 10000-word large
    case -- deliberately a different technique, not a slower one."""
    lines = stdin.split("\n")
    n = int(lines[0])
    words = lines[1].split() if len(lines) > 1 else []
    assert len(words) == n

    def count_vector(w: str) -> tuple:
        vec = [0] * 26
        for ch in w:
            vec[ord(ch) - ord('a')] += 1
        return tuple(vec)

    groups = {count_vector(w) for w in words}
    return str(len(groups))


_ANAGRAMS_LARGE_WORDS = [
    "".join(chr(ord('a') + (i * 7 + j) % 5) for j in range(6)) for i in range(10000)
]
_register(ProblemInputSpec(
    "group-anagrams", "list_of_strings",
    {"n_min": 1, "n_max": 10000},
    ["1\nsolo", "4\nab ba abc cba"],
    _anagrams_random, _anagrams_validate, _anagrams_checker,
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


def _no_repeat_checker(stdin: str) -> str:
    """Independent of the reference's last-seen-index jump technique:
    a genuine two-pointer/sliding-set shrink-from-the-left loop instead
    (still O(n), since 5*10^4 chars rules out an O(n^2) brute force)."""
    s = stdin.split("\n")[0]
    seen = set()
    left = 0
    best = 0
    for right, ch in enumerate(s):
        while ch in seen:
            seen.discard(s[left])
            left += 1
        seen.add(ch)
        best = max(best, right - left + 1)
    return str(best)


_register(ProblemInputSpec(
    "longest-substring-no-repeat", "string",
    {"len_min": 0, "len_max": 50000},
    ["\n", "a"],
    _no_repeat_random, _no_repeat_validate, _no_repeat_checker,
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


def _coin_change_checker(stdin: str) -> str:
    """Independent of the reference's bottom-up DP table: an explicit
    BFS shortest-path over amounts (0 .. amount, edge amount->amount+coin)
    instead -- a different traversal, same O(n*amount) order."""
    lines = stdin.split("\n")
    n = int(lines[0])
    coins = list(map(int, lines[1].split()))
    amount = int(lines[2])
    assert len(coins) == n
    dist = [-1] * (amount + 1)
    dist[0] = 0
    q = deque([0])
    while q:
        cur = q.popleft()
        for c in coins:
            nxt = cur + c
            if nxt <= amount and dist[nxt] == -1:
                dist[nxt] = dist[cur] + 1
                q.append(nxt)
    return str(dist[amount])


_register(ProblemInputSpec(
    "coin-change", "coins_and_amount",
    {"n_min": 1, "n_max": 12, "amount_min": 1, "amount_max": 10000},
    ["1\n2\n3", "1\n1\n1", "3\n1 3 4\n6"],
    _coin_change_random, _coin_change_validate, _coin_change_checker,
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


def _product_except_self_checker(stdin: str) -> str:
    """Independent of the reference's prefix/suffix sweep: direct
    division (total product / a[i]), explicitly allowed here since this
    is a verification-only checker, not a graded submission -- the
    problem's own "no division" rule only binds contestants. Handles
    zero(s) specially since division by zero isn't otherwise defined."""
    lines = stdin.split("\n")
    n = int(lines[0])
    a = list(map(int, lines[1].split()))
    assert len(a) == n
    zero_count = a.count(0)
    if zero_count >= 2:
        out = [0] * n
    elif zero_count == 1:
        idx = a.index(0)
        prod_nonzero = 1
        for i, v in enumerate(a):
            if i != idx:
                prod_nonzero *= v
        out = [0] * n
        out[idx] = prod_nonzero
    else:
        total = 1
        for v in a:
            total *= v
        out = [total // v for v in a]
    return " ".join(map(str, out))


_register(ProblemInputSpec(
    "product-except-self", "int_array",
    {"n_min": 2, "n_max": 100000},
    ["2\n2 3", "3\n1 1 1"],
    _product_except_self_random, _product_except_self_validate, _product_except_self_checker,
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


def _rotate_image_checker(stdin: str) -> str:
    """Independent of the reference's direct index-mapping formula:
    transpose-then-reverse-each-row (the standard two-step technique)."""
    lines = stdin.split("\n")
    n = int(lines[0])
    m = [list(map(int, lines[1 + i].split())) for i in range(n)]
    transposed = [[m[r][c] for r in range(n)] for c in range(n)]
    rotated = [row[::-1] for row in transposed]
    return "\n".join(" ".join(map(str, row)) for row in rotated)


_register(ProblemInputSpec(
    "rotate-image", "matrix",
    {"n_min": 1, "n_max": 100},
    ["1\n5", "2\n1 2\n3 4"],
    _rotate_image_random, _rotate_image_validate, _rotate_image_checker,
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


def _num_islands_checker(stdin: str) -> str:
    """Independent of the reference's recursive DFS: iterative
    union-find over adjacent 1-cells instead (also avoids any recursion
    -depth concern, as a side benefit)."""
    lines = stdin.split("\n")
    rows, cols = map(int, lines[0].split())
    grid = [list(map(int, lines[1 + i].split())) for i in range(rows)]
    parent = list(range(rows * cols))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1:
                idx = r * cols + c
                if r + 1 < rows and grid[r + 1][c] == 1:
                    union(idx, (r + 1) * cols + c)
                if c + 1 < cols and grid[r][c + 1] == 1:
                    union(idx, r * cols + c + 1)
    roots = {find(r * cols + c) for r in range(rows) for c in range(cols) if grid[r][c] == 1}
    return str(len(roots))


_register(ProblemInputSpec(
    "num-islands", "binary_grid",
    {"rows_min": 1, "rows_max": 300, "cols_min": 1, "cols_max": 300},
    ["1 1\n0", "2 4\n1 0 1 0\n0 1 0 1"],
    _num_islands_random, _num_islands_validate, _num_islands_checker,
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


def _search_rotated_checker(stdin: str) -> str:
    """Independent of the reference's O(log n) binary search: a plain
    O(n) linear scan. (Also the honest point made in this problem's
    large-case comment below -- at n<=10^4 the linear scan is not
    meaningfully slower, so this checker has no timing concern either.)"""
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    t = int(lines[2])
    for i, v in enumerate(arr):
        if v == t:
            return str(i)
    return "-1"


_SEARCH_ROTATED_BASE = sorted(range(-5000, 5000))
_SEARCH_ROTATED_LARGE = _SEARCH_ROTATED_BASE[3000:] + _SEARCH_ROTATED_BASE[:3000]
_register(ProblemInputSpec(
    "search-rotated", "rotated_sorted_array",
    {"n_min": 1, "n_max": 10000},
    ["1\n1\n0", "5\n5 1 2 3 4\n1"],
    _search_rotated_random, _search_rotated_validate, _search_rotated_checker,
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


def _container_water_checker(stdin: str) -> str:
    """Independent of the reference's O(n) two-pointer sweep: the
    textbook O(n^2) brute force (every i<j pair). Deliberately slow,
    per the problem's own large-case size being reduced below (see
    that comment) specifically so this checker finishes in reasonable
    time against it."""
    lines = stdin.split("\n")
    n = int(lines[0])
    h = list(map(int, lines[1].split()))
    best = 0
    for i in range(n):
        for j in range(i + 1, n):
            area = min(h[i], h[j]) * (j - i)
            if area > best:
                best = area
    return str(best)


_register(ProblemInputSpec(
    "container-water", "int_array",
    {"n_min": 2, "n_max": 100000},
    ["2\n1 1", "5\n1 2 3 4 5"],
    _container_water_random, _container_water_validate, _container_water_checker,
    large_cases=[
        # Intended complexity: O(n) two-pointer. A naive O(n^2) all-pairs
        # check is 10^10 at the full n=10^5 ceiling -- times out, and
        # test_naive_times_out_reference_does_not_on_large_input (in
        # test_problem_bank_large_input_complexity.py) proves it directly
        # against this exact stored input, with the actual sizes/timings
        # observed. RESTORED to the full n=10^5 ceiling (2026-10 follow-up;
        # briefly reduced to n=2000 so the O(n^2) independent checker above
        # could verify it directly, but that traded away the very
        # timeout-differentiation this large case exists for). These large
        # inputs now run the REFERENCE SOLUTION ONLY -- see
        # LARGE_CASES_EXCLUDED_FROM_CHECKER in
        # test_problem_bank_opted_in_quality_gates.py, which skips exactly
        # these two stdins when verifying this problem's checker, since the
        # checker is deliberately the slow O(n^2) approach and was never
        # meant to run at this scale. Checker correctness is instead fully
        # covered by the 200-trial differential fuzz on small inputs.
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


def _longest_palindromic_checker(stdin: str) -> str:
    """Independent of the reference's expand-around-center technique:
    a bottom-up O(n^2) is_palindrome[i][j] DP table instead."""
    s = stdin.split("\n")[0]
    n = len(s)
    if n == 0:
        return "0"
    dp = [[False] * n for _ in range(n)]
    best = 1
    for i in range(n):
        dp[i][i] = True
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            if s[i] == s[j] and (length == 2 or dp[i + 1][j - 1]):
                dp[i][j] = True
                best = max(best, length)
    return str(best)


_register(ProblemInputSpec(
    "longest-palindromic", "string",
    {"len_min": 1, "len_max": 1000},
    ["a", "ac"],
    _longest_palindromic_random, _longest_palindromic_validate, _longest_palindromic_checker,
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


def _combo_sum_count_checker(stdin: str) -> str:
    """Independent of the reference's unmemoized DFS over combinations:
    a bottom-up unbounded-knapsack-count DP instead (coins outer loop,
    amounts inner loop -- the standard technique for counting UNordered
    combinations with repetition, same as LeetCode 518). O(n*target),
    so (unlike the reference) it has no combinatorial-blowup risk at
    all, including against this problem's own large cases below."""
    lines = stdin.split("\n")
    n = int(lines[0])
    coins = list(map(int, lines[1].split()))
    target = int(lines[2])
    assert len(coins) == n
    dp = [0] * (target + 1)
    dp[0] = 1
    for c in coins:
        for amt in range(c, target + 1):
            dp[amt] += dp[amt - c]
    return str(dp[target])


_register(ProblemInputSpec(
    "combination-sum-count", "coins_and_target_count",
    {"n_min": 1, "n_max": 30, "target_min": 1, "target_max": 500},
    ["2\n2 3\n5", "1\n2\n1"],
    _combo_sum_count_random, _combo_sum_count_validate, _combo_sum_count_checker,
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

def _validate_bst_checker(stdin: str) -> str:
    """Independent of the reference's top-down min/max bounds
    recursion: build the tree, then an EXPLICIT-STACK (non-recursive)
    inorder traversal checking the value sequence is strictly
    increasing instead."""
    tokens = stdin.split()

    class _N:
        __slots__ = ("v", "l", "r")

        def __init__(self, v):
            self.v = int(v)
            self.l = None
            self.r = None

    if not tokens or tokens[0] == "N":
        return "YES"
    root = _N(tokens[0])
    q = deque([root])
    i = 1
    while q and i < len(tokens):
        node = q.popleft()
        if i < len(tokens) and tokens[i] != "N":
            node.l = _N(tokens[i])
            q.append(node.l)
        i += 1
        if i < len(tokens) and tokens[i] != "N":
            node.r = _N(tokens[i])
            q.append(node.r)
        i += 1
    stack = []
    cur = root
    prev = None
    ok = True
    while stack or cur:
        while cur:
            stack.append(cur)
            cur = cur.l
        cur = stack.pop()
        if prev is not None and cur.v <= prev:
            ok = False
            break
        prev = cur.v
        cur = cur.r
    return "YES" if ok else "NO"


_VALIDATE_BST_LARGE_VALID = " ".join(_serialize_level_order(_build_random_bst(random.Random("2c-validate-bst-valid"), 1000)[0]))
_VALIDATE_BST_LARGE_INVALID = " ".join(_gen_tree_tokens(random.Random("2c-validate-bst-invalid"), 1000))
_register(ProblemInputSpec(
    "tree-validate-bst", "tree_level_order",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["5 N 3", "3 1 5"],
    _validate_bst_random, _BST_TOKEN_VALIDATE, _validate_bst_checker,
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


def _tree_diameter_checker(stdin: str) -> str:
    """Independent of the reference's single-pass DFS height-tracking:
    brute-force BFS-from-every-node over the tree's (undirected)
    adjacency, taking the max over all pairwise distances -- O(n^2)
    overall, fine at this problem's n<=1000 ceiling (10^6)."""
    tokens = stdin.split()

    class _N:
        __slots__ = ("l", "r")

        def __init__(self):
            self.l = None
            self.r = None

    if not tokens or tokens[0] == "N":
        return "0"
    root = _N()
    nodes = [root]
    adj = {id(root): []}
    q = deque([root])
    i = 1
    while q and i < len(tokens):
        node = q.popleft()
        if i < len(tokens) and tokens[i] != "N":
            child = _N()
            node.l = child
            nodes.append(child)
            adj.setdefault(id(node), []).append(child)
            adj.setdefault(id(child), []).append(node)
            q.append(child)
        i += 1
        if i < len(tokens) and tokens[i] != "N":
            child = _N()
            node.r = child
            nodes.append(child)
            adj.setdefault(id(node), []).append(child)
            adj.setdefault(id(child), []).append(node)
            q.append(child)
        i += 1
    best = 0
    for start in nodes:
        dist = {id(start): 0}
        bq = deque([start])
        while bq:
            cur = bq.popleft()
            for nb in adj.get(id(cur), []):
                if id(nb) not in dist:
                    dist[id(nb)] = dist[id(cur)] + 1
                    if dist[id(nb)] > best:
                        best = dist[id(nb)]
                    bq.append(nb)
    return str(best)


_DIAMETER_LARGE = " ".join(_gen_tree_tokens(random.Random("2c-diameter-large"), 1000))
_register(ProblemInputSpec(
    "tree-diameter", "tree_level_order",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["1 2 N N 3", "1 2 3 4 5"],
    _tree_diameter_random, _tree_validate, _tree_diameter_checker,
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


def _tree_path_sum_checker(stdin: str) -> str:
    """Independent of the reference's recursive short-circuit `has`:
    an explicit-stack iterative DFS that carries the accumulated sum
    along with each stack entry."""
    lines = stdin.split("\n")
    tokens = lines[0].split()
    target = int(lines[1])

    class _N:
        __slots__ = ("v", "l", "r")

        def __init__(self, v):
            self.v = int(v)
            self.l = None
            self.r = None

    root = _N(tokens[0])
    q = deque([root])
    i = 1
    while q and i < len(tokens):
        node = q.popleft()
        if i < len(tokens) and tokens[i] != "N":
            node.l = _N(tokens[i])
            q.append(node.l)
        i += 1
        if i < len(tokens) and tokens[i] != "N":
            node.r = _N(tokens[i])
            q.append(node.r)
        i += 1
    stack = [(root, root.v)]
    found = False
    while stack:
        node, total = stack.pop()
        if node.l is None and node.r is None:
            if total == target:
                found = True
                break
            continue
        if node.l:
            stack.append((node.l, total + node.l.v))
        if node.r:
            stack.append((node.r, total + node.r.v))
    return "YES" if found else "NO"


_PATH_SUM_LARGE_TOKENS = _gen_tree_tokens(random.Random("2c-path-sum-large"), 1000)
_register(ProblemInputSpec(
    "tree-path-sum", "tree_and_target",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["1 2 3\n5", "1\n1"],
    _tree_path_sum_random, _tree_path_sum_validate, _tree_path_sum_checker,
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


def _kth_smallest_checker(stdin: str) -> str:
    """Independent of the reference's inorder-gives-sorted-order
    traversal: doesn't even reconstruct the tree -- the value SET of a
    BST's nodes is tree-structure-independent, so collecting every
    real-node value straight from the level-order tokens and sorting
    gives the same k-th smallest, without relying on inorder order at
    all."""
    lines = stdin.split("\n")
    tokens = lines[0].split()
    k = int(lines[1])
    values = sorted(int(t) for t in tokens if t != "N")
    return str(values[k - 1])


_KTH_ROOT, _KTH_VALUES = _build_random_bst(random.Random("2c-kth-large"), 1000)
_register(ProblemInputSpec(
    "tree-kth-smallest-bst", "bst_and_k",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["5 3 8 1 4 7 9\n1", "1\n1"],
    _kth_smallest_random, _kth_smallest_validate, _kth_smallest_checker,
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


def _lca_bst_checker(stdin: str) -> str:
    """Independent of the reference's single simultaneous descent:
    walks the root-to-p and root-to-q paths SEPARATELY (two independent
    BST descents), then finds the last value common to both paths --
    the classic "paths from root" LCA technique."""
    lines = stdin.split("\n")
    tokens = lines[0].split()
    p, q_val = map(int, lines[1].split())

    class _N:
        __slots__ = ("v", "l", "r")

        def __init__(self, v):
            self.v = int(v)
            self.l = None
            self.r = None

    root = _N(tokens[0])
    bq = deque([root])
    i = 1
    while bq and i < len(tokens):
        node = bq.popleft()
        if i < len(tokens) and tokens[i] != "N":
            node.l = _N(tokens[i])
            bq.append(node.l)
        i += 1
        if i < len(tokens) and tokens[i] != "N":
            node.r = _N(tokens[i])
            bq.append(node.r)
        i += 1

    def path_to(target: int) -> list:
        path = []
        node = root
        while node:
            path.append(node.v)
            if target < node.v:
                node = node.l
            elif target > node.v:
                node = node.r
            else:
                break
        return path

    path_p = path_to(p)
    path_q = path_to(q_val)
    lca = path_p[0]
    for a, b in zip(path_p, path_q):
        if a != b:
            break
        lca = a
    return str(lca)


_LCA_ROOT, _LCA_VALUES = _build_random_bst(random.Random("2c-lca-large"), 1000)
_register(ProblemInputSpec(
    "tree-lca-bst", "bst_and_pq",
    {"real_nodes_min": 2, "real_nodes_max": 1000},
    ["5 3 8 1 4 7 9\n1 4", "6 2 8 0 4 7 9\n0 9"],
    _lca_bst_random, _lca_bst_validate, _lca_bst_checker,
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


def _sum_root_to_leaf_checker(stdin: str) -> str:
    """Independent of the reference's recursive `dfs`: an explicit-
    stack iterative DFS carrying the accumulated number along with
    each stack entry."""
    tokens = stdin.split()

    class _N:
        __slots__ = ("v", "l", "r")

        def __init__(self, v):
            self.v = int(v)
            self.l = None
            self.r = None

    root = _N(tokens[0])
    q = deque([root])
    i = 1
    while q and i < len(tokens):
        node = q.popleft()
        if i < len(tokens) and tokens[i] != "N":
            node.l = _N(tokens[i])
            q.append(node.l)
        i += 1
        if i < len(tokens) and tokens[i] != "N":
            node.r = _N(tokens[i])
            q.append(node.r)
        i += 1
    total = 0
    stack = [(root, root.v)]
    while stack:
        node, num = stack.pop()
        if node.l is None and node.r is None:
            total += num
            continue
        if node.l:
            stack.append((node.l, num * 10 + node.l.v))
        if node.r:
            stack.append((node.r, num * 10 + node.r.v))
    return str(total)


_SUM_R2L_LARGE = " ".join(_gen_tree_tokens(random.Random("2c-sum-r2l-large"), 1000, lo=0, hi=9))
_register(ProblemInputSpec(
    "tree-sum-root-to-leaf", "tree_level_order",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["1 2 3", "0"],
    _sum_root_to_leaf_random, _sum_root_to_leaf_validate, _sum_root_to_leaf_checker,
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


def _right_side_view_checker(stdin: str) -> str:
    """Independent of the reference's iterative BFS level-by-level
    scan: an explicit-stack DFS that visits each node's RIGHT child
    before its left child, recording the first value seen at each
    depth -- since right is explored first, that first-seen value at
    a given depth is exactly the rightmost node at that depth."""
    tokens = stdin.split()

    class _N:
        __slots__ = ("v", "l", "r")

        def __init__(self, v):
            self.v = int(v)
            self.l = None
            self.r = None

    root = _N(tokens[0])
    q = deque([root])
    i = 1
    while q and i < len(tokens):
        node = q.popleft()
        if i < len(tokens) and tokens[i] != "N":
            node.l = _N(tokens[i])
            q.append(node.l)
        i += 1
        if i < len(tokens) and tokens[i] != "N":
            node.r = _N(tokens[i])
            q.append(node.r)
        i += 1
    result = {}
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        if depth not in result:
            result[depth] = node.v
        if node.l:
            stack.append((node.l, depth + 1))
        if node.r:
            stack.append((node.r, depth + 1))
    out = [result[d] for d in sorted(result)]
    return " ".join(map(str, out))


_RIGHT_VIEW_LARGE = " ".join(_gen_tree_tokens(random.Random("2c-right-view-large"), 1000))
_register(ProblemInputSpec(
    "tree-right-side-view", "tree_level_order",
    {"real_nodes_min": 1, "real_nodes_max": 1000},
    ["1 N 2", "1 2 3 4"],
    _right_side_view_random, _tree_validate, _right_side_view_checker,
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


def _max_non_overlap_bruteforce(intervals: List[Tuple[int, int]]) -> int:
    """Shared by greedy-activity-selection and
    greedy-non-overlapping-removals' checkers below: an O(n^2) DP
    cross-check (classic unweighted interval-scheduling DP), genuinely
    different from the reference's single-pass sort-by-end-and-sweep
    greedy loop in both problems."""
    ivs = sorted(intervals, key=lambda x: x[1])
    n = len(ivs)
    dp = [0] * n
    for i in range(n):
        best = 1
        for j in range(i):
            if ivs[j][1] <= ivs[i][0]:
                best = max(best, dp[j] + 1)
        dp[i] = best
    return max(dp) if dp else 0


def _activity_selection_checker(stdin: str) -> str:
    lines = stdin.split("\n")
    n = int(lines[0])
    starts = list(map(int, lines[1].split()))
    ends = list(map(int, lines[2].split()))
    assert len(starts) == n and len(ends) == n
    return str(_max_non_overlap_bruteforce(list(zip(starts, ends))))


_ACT_SEL_LARGE_STARTS = [(i * 3) % 10000 for i in range(10000)]
_ACT_SEL_LARGE_ENDS = [s + 5 for s in _ACT_SEL_LARGE_STARTS]
_register(ProblemInputSpec(
    "greedy-activity-selection", "two_int_arrays",
    {"n_min": 1, "n_max": 10000},
    ["1\n0\n5", "3\n1 1 1\n2 2 2"],
    _activity_selection_random, _activity_selection_validate, _activity_selection_checker,
    large_cases=[
        # Intended complexity: O(n log n) (sort by end time). A naive
        # O(n^2) pairwise overlap-and-select scan is 10^8 at the full
        # n=10^4 ceiling -- times out, and
        # test_naive_times_out_reference_does_not_on_large_input (in
        # test_problem_bank_large_input_complexity.py) proves it directly
        # against this exact stored input, with the actual sizes/timings
        # observed. RESTORED to the full n=10^4 ceiling (2026-10 follow-up;
        # briefly reduced to n=2000 so the O(n^2) independent checker above
        # could verify it directly, but that traded away the very
        # timeout-differentiation this large case exists for). These large
        # inputs now run the REFERENCE SOLUTION ONLY -- see
        # LARGE_CASES_EXCLUDED_FROM_CHECKER in
        # test_problem_bank_opted_in_quality_gates.py, which skips exactly
        # these two stdins when verifying this problem's checker, since the
        # checker is deliberately the slow O(n^2) approach and was never
        # meant to run at this scale. Checker correctness is instead fully
        # covered by the 200-trial differential fuzz on small inputs.
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
    # RESTORED to the full n=10^4 ceiling (2026-10 follow-up; briefly
    # reduced to n=2000 so the O(n^2) independent checkers below could
    # verify it directly, but that traded away the very timeout-
    # differentiation this large case exists for). These large inputs
    # now run the REFERENCE SOLUTION ONLY -- see
    # LARGE_CASES_EXCLUDED_FROM_CHECKER in
    # test_problem_bank_opted_in_quality_gates.py, which skips exactly
    # these stdins when verifying greedy-merge-intervals'/greedy-non-
    # overlapping-removals' checkers, since both checkers are
    # deliberately the slow O(n^2) approach and were never meant to run
    # at this scale. Checker correctness is instead fully covered by the
    # 200-trial differential fuzz on small inputs.
    # test_naive_times_out_reference_does_not_on_large_input (in
    # test_problem_bank_large_input_complexity.py) proves the naive-vs-
    # reference timeout gap directly against this exact stored input.
    n = 10000
    lines = [str(n)]
    for _ in range(n):
        s = rng.randint(0, 2000)
        e = s + rng.randint(0, 10)
        lines.append(f"{s} {e}")
    return "\n".join(lines) + "\n"


def _merge_intervals_checker(stdin: str) -> str:
    """Independent of the reference's sort-by-start-then-sweep merge:
    union-find over PAIRWISE overlap tests instead (connected
    components of the "overlap" graph) -- an interval graph's connected
    components are always contiguous (no coverage gaps), so each
    component's [min start, max end] is exactly its merged interval.
    O(n^2) pairwise check, by design, as a genuinely different
    technique (graph components vs a sorted sweep)."""
    lines = stdin.split("\n")
    n = int(lines[0])
    ivs = [tuple(map(int, lines[1 + i].split())) for i in range(n)]
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
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
    merged = sorted(groups.values())
    return "\n".join(f"{s} {e}" for s, e in merged)


def _non_overlap_removals_checker(stdin: str) -> str:
    """Reuses the same O(n^2) DP cross-check as
    greedy-activity-selection's checker (max non-overlapping count),
    then reports n minus that count -- genuinely different from the
    reference's own sort-by-end-and-sweep."""
    lines = stdin.split("\n")
    n = int(lines[0])
    ivs = [tuple(map(int, lines[1 + i].split())) for i in range(n)]
    return str(n - _max_non_overlap_bruteforce(ivs))


_register(ProblemInputSpec(
    "greedy-merge-intervals", "interval_list",
    {"n_min": 1, "n_max": 10000},
    ["1\n1 1", "2\n1 4\n4 5"],
    _interval_list_random, _interval_list_validate, _merge_intervals_checker,
    large_cases=[
        # Intended complexity: O(n log n) (sort by start, one merge pass).
        # A naive O(n^2) pairwise merge-and-rescan is 10^8 at the full
        # n=10^4 ceiling -- times out. See _interval_list_large above for
        # the restoration/checker-exclusion reasoning.
        _interval_list_large("2c-merge-intervals-large-1"),
        _interval_list_large("2c-merge-intervals-large-2"),
    ],
))

_register(ProblemInputSpec(
    "greedy-non-overlapping-removals", "interval_list",
    {"n_min": 1, "n_max": 10000},
    ["1\n1 2", "2\n1 2\n1 2"],
    _interval_list_random, _interval_list_validate, _non_overlap_removals_checker,
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


def _jump_game_checker(stdin: str) -> str:
    """Independent of the reference's forward greedy reach-tracking: a
    backward greedy pass instead (classic "last good index" technique,
    O(n))."""
    lines = stdin.split("\n")
    n = int(lines[0])
    a = list(map(int, lines[1].split()))
    last_good = n - 1
    for i in range(n - 2, -1, -1):
        if i + a[i] >= last_good:
            last_good = i
    return "YES" if last_good == 0 else "NO"


_register(ProblemInputSpec(
    "greedy-jump-game", "int_array",
    {"n_min": 1, "n_max": 100000},
    ["1\n0", "3\n1 0 1"],
    _jump_game_random, _jump_game_validate, _jump_game_checker,
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
# Stage 2c batch 2 (2026-10): the next 21 Medium problems, by order in
# problem_bank.py, after batch 1's 21 (greedy-min-platforms, Stage 2a's own
# exception, is already opted in separately and is skipped here).
#
# New shapes this batch (reusing gen_int_array/gen_string/gen_int/_fmt_arr
# and batch 1's _interval_list_random/_interval_list_validate/
# _max_non_overlap_bruteforce wherever the underlying structure already
# matches, rather than inventing a new generator for something that already
# exists):
#   edge_list                undirected or directed graph: "n m" header line,
#                             then m "u v" edge lines (0-indexed)
#   edge_list_separate_nm     same, but n and m are on their OWN lines before
#                             the edges (graph-course-schedule's own format)
#   edge_list_with_query      edge_list + one trailing "src dst" query line
#   weighted_edge_list        directed, weighted, 1-indexed nodes, with its
#                             own n / m / edges / source-node line layout
#                             (graph-network-delay-time)
#   dag_edge_list             edge_list restricted to a draw that is
#                             acyclic BY CONSTRUCTION (a random permutation
#                             stands in for a topological order; every edge
#                             only goes from an earlier position to a later
#                             one), not by rejection sampling
#   rotting_grid              rows/cols grid of 0/1/2 values
#   array_with_limit          int array + one trailing single-int limit
#   single_string             reuses gen_string directly
#   two_strings               a pair of strings, one per line
#   digit_strings_pair        a pair of decimal-digit-only strings
#   string_and_rows           a string + a trailing row-count integer
#   single_int                reuses gen_int directly
# =============================================================================

def _gen_simple_edges(rng: random.Random, n: int, m_target: int, directed: bool) -> List[Tuple[int, int]]:
    """n distinct nodes, up to m_target distinct simple edges (no self
    loops, no duplicates/parallel edges -- or their reverse, for an
    undirected graph)."""
    edges: List[Tuple[int, int]] = []
    seen = set()
    max_m = n * (n - 1) if directed else n * (n - 1) // 2
    m = min(m_target, max_m)
    attempts = 0
    while len(edges) < m and attempts < m * 20 + 50 and n >= 2:
        attempts += 1
        u, v = rng.sample(range(n), 2)
        key = (u, v) if directed else tuple(sorted((u, v)))
        if key in seen:
            continue
        seen.add(key)
        edges.append((u, v))
    return edges


def _gen_dag_edges(rng: random.Random, n: int, m_target: int) -> List[Tuple[int, int]]:
    """A uniformly random permutation stands in for a topological order;
    every edge only goes from an earlier position in it to a later one,
    so the graph is acyclic by construction -- no rejection sampling
    needed."""
    order = list(range(n))
    rng.shuffle(order)
    pos = {node: i for i, node in enumerate(order)}
    edges: List[Tuple[int, int]] = []
    seen = set()
    max_m = n * (n - 1) // 2
    m = min(m_target, max_m)
    attempts = 0
    while len(edges) < m and attempts < m * 20 + 50 and n >= 2:
        attempts += 1
        a, b = rng.sample(range(n), 2)
        u, v = (a, b) if pos[a] < pos[b] else (b, a)
        if (u, v) in seen:
            continue
        seen.add((u, v))
        edges.append((u, v))
    return edges


def _fmt_edge_list(n: int, edges: List[Tuple[int, int]]) -> str:
    lines = [f"{n} {len(edges)}"]
    lines.extend(f"{u} {v}" for u, v in edges)
    return "\n".join(lines) + "\n"


def _edge_list_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n, m = map(int, lines[0].split())
    edge_lines = lines[1:1 + m]
    if len(edge_lines) != m or not (1 <= n <= 10000) or not (0 <= m <= 10000):
        return False
    for line in edge_lines:
        u, v = map(int, line.split())
        if not (0 <= u < n and 0 <= v < n) or u == v:
            return False
    return True


def _directed_has_cycle(n: int, adj: List[List[int]]) -> bool:
    """Shared by graph-cycle-directed and graph-course-schedule's
    checkers: DFS-based 3-color (white/gray/black) cycle detection,
    genuinely different from the reference's Kahn's-algorithm indegree/
    BFS processed-count check in both problems. Iterative (explicit
    stack), not recursive, so it has no recursion-depth concern at any
    graph size."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = [WHITE] * n
    has_cycle = False
    for start in range(n):
        if color[start] != WHITE:
            continue
        color[start] = GRAY
        stack = [(start, iter(adj[start]))]
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if color[nxt] == GRAY:
                    has_cycle = True
                elif color[nxt] == WHITE:
                    color[nxt] = GRAY
                    stack.append((nxt, iter(adj[nxt])))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()
    return has_cycle


# ---- greedy-jump-game-ii  --  shape: int_array -----------------------------

def _jump_game_ii_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 60)])
    # The last index must always be reachable (the problem guarantees
    # this) -- build so every position can reach at least the next one.
    a = [0] * n
    for i in range(n - 1):
        a[i] = rng.randint(1, max(1, n - 1 - i))
    return f"{n}\n{_fmt_arr(a)}\n"


def _jump_game_ii_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); a = list(map(int, lines[1].split()))
    if not (len(a) == n and 1 <= n <= 100000 and all(v >= 0 for v in a)):
        return False
    reach = 0
    for i in range(n):
        if i > reach:
            return False
        reach = max(reach, i + a[i])
    return True


def _jump_game_ii_checker(stdin: str) -> str:
    """Independent of the reference's forward greedy range-expansion: a
    backward DP (dp[i] = minimum jumps from i to the last index), O(n^2)
    worst case -- a genuinely different technique (DP vs greedy),
    deliberately not the fast one."""
    lines = stdin.split("\n")
    n = int(lines[0]); a = list(map(int, lines[1].split()))
    dp = [0] * n
    for i in range(n - 2, -1, -1):
        reach = min(i + a[i], n - 1)
        best = None
        for j in range(i + 1, reach + 1):
            if best is None or dp[j] + 1 < best:
                best = dp[j] + 1
        dp[i] = best if best is not None else 10 ** 9
    return str(dp[0])


_JUMP_II_LARGE_1 = f"100000\n{_fmt_arr([100000] * 99999 + [0])}\n"
_JUMP_II_LARGE_2 = f"100000\n{_fmt_arr([(100000 - i) for i in range(99999)] + [0])}\n"
_register(ProblemInputSpec(
    "greedy-jump-game-ii", "int_array",
    {"n_min": 1, "n_max": 100000},
    ["1\n0", "2\n1 1"],
    _jump_game_ii_random, _jump_game_ii_validate, _jump_game_ii_checker,
    large_cases=[
        # Intended complexity: O(n) (forward greedy range expansion). The
        # backward-DP checker above is O(n^2) -- 10^10 at this ceiling --
        # and is excluded from the checker-agreement quality gate for
        # exactly these 2 inputs (see LARGE_CASES_EXCLUDED_FROM_CHECKER);
        # checker correctness stays covered by the 200-trial small-input
        # fuzz. Both use a huge per-step jump range so the DP's own inner
        # scan is as wide as possible at every step -- see
        # test_problem_bank_batch2_large_input_complexity.py for the
        # naive-vs-reference proof and actual timings.
        _JUMP_II_LARGE_1,
        _JUMP_II_LARGE_2,
    ],
))


# ---- greedy-gas-station  --  shape: two_int_arrays -------------------------

def _gas_station_unique_start(gas: List[int], cost: List[int]) -> Tuple[int, int]:
    """O(n): the classic prefix-sum characterization -- the valid
    starting index/indices are exactly the argmin(s) of the cumulative
    (gas[i]-cost[i]) prefix sum P[0..n-1] (P[0]=0). Returns (the first
    argmin, how many indices tie for the minimum) -- ties>1 means more
    than one valid start exists."""
    n = len(gas)
    prefix = 0
    best = 0
    best_idx = 0
    ties = 1
    for k in range(1, n):
        prefix += gas[k - 1] - cost[k - 1]
        if prefix < best:
            best = prefix
            best_idx = k
            ties = 1
        elif prefix == best:
            ties += 1
    return best_idx, ties


def _gas_station_random(rng: random.Random) -> str:
    # The problem's own precondition is "exactly one starting index
    # exists" -- sum(gas) >= sum(cost) alone does NOT guarantee that (a
    # perfectly balanced circuit, or one with a repeated minimum prefix
    # sum, can have several equally-valid starts; confirmed directly: 2
    # of this problem's own original 5 stored tests already had more
    # than one -- see the Stage 2c batch 2 commit message). Rejection-
    # sample until the draw genuinely has exactly one.
    for _ in range(500):
        n = rng.choice([1, 2, rng.randint(3, 40)])
        gas = gen_int_array(rng, n, 0, 20)
        cost = gen_int_array(rng, n, 0, 20)
        total_diff = sum(gas) - sum(cost)
        if total_diff < 0:
            gas[0] += -total_diff  # enforce the problem's own sum(gas) >= sum(cost)
        _, ties = _gas_station_unique_start(gas, cost)
        if ties == 1:
            return f"{n}\n{_fmt_arr(gas)}\n{_fmt_arr(cost)}\n"
    raise RuntimeError("greedy-gas-station: could not draw a unique-start input in 500 attempts")


def _gas_station_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); gas = list(map(int, lines[1].split())); cost = list(map(int, lines[2].split()))
    if not (len(gas) == n and len(cost) == n and 1 <= n <= 10000 and sum(gas) >= sum(cost)):
        return False
    _, ties = _gas_station_unique_start(gas, cost)
    return ties == 1


def _gas_station_checker(stdin: str) -> str:
    """Independent of the reference's single-pass tank-reset greedy: a
    brute-force O(n^2) simulate-the-full-circuit-from-every-candidate-
    start scan."""
    lines = stdin.split("\n")
    n = int(lines[0]); gas = list(map(int, lines[1].split())); cost = list(map(int, lines[2].split()))
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
            return str(s)
    raise AssertionError("greedy-gas-station checker: no valid start found (should be impossible)")


def _gas_station_large(n: int) -> str:
    # Deterministic construction, not rejection sampling (brute-force
    # uniqueness-checking the result is fine at O(n), but we want this
    # callable at n=10^4 without any retry risk). The one big shortfall
    # (diff[n-2] = -(n-1)) sits second-to-last, making the UNIQUE valid
    # start index n-1 -- the LAST candidate a brute-force simulate-
    # from-every-start loop tries (candidates are tried in increasing
    # order: 0, 1, 2, ..., n-1). Each wrong candidate s < n-2 only
    # reaches the shortfall after (n-2-s) steps of accumulating +1, so
    # it fails late (near a full circuit), costing genuine O(n) per
    # candidate -- confirmed directly: two earlier versions (shortfall
    # at the very end, then shortfall at the very start) both put the
    # UNIQUE valid start at an index reached after only 1-2 candidates,
    # so the loop exited almost immediately regardless of how slow each
    # individual candidate-check was, finishing in ~0.1s instead of the
    # intended O(n) vs O(n^2) gap. Putting the shortfall right before
    # the end means EVERY one of the n-1 wrong candidates must be tried
    # (and each costs close to O(n)) before the loop ever reaches the
    # one valid start. Sum(gas) == sum(cost) exactly either way.
    dip = n - 2
    gas = [2] * n
    cost = [1] * n
    gas[dip] = 1
    cost[dip] = n
    return f"{n}\n{_fmt_arr(gas)}\n{_fmt_arr(cost)}\n"


_register(ProblemInputSpec(
    "greedy-gas-station", "two_int_arrays",
    {"n_min": 1, "n_max": 10000},
    ["5\n1 2 3 4 5\n3 4 5 1 2", "2\n5 1\n4 2"],
    _gas_station_random, _gas_station_validate, _gas_station_checker,
    large_cases=[
        # Intended complexity: O(n) single pass. The checker's brute
        # force is O(n^2) -- 10^8 at this ceiling -- and is excluded
        # from the checker-agreement quality gate for exactly these 2
        # inputs (see LARGE_CASES_EXCLUDED_FROM_CHECKER); checker
        # correctness stays covered by the 200-trial small-input fuzz.
        # See test_problem_bank_batch2_large_input_complexity.py for
        # the naive-vs-reference proof and actual timings.
        _gas_station_large(10000),
        _gas_station_large(9999),
    ],
))


# ---- greedy-boats-save-people  --  shape: array_with_limit (NEW) ----------

def _boats_random(rng: random.Random) -> str:
    # Capped at a small n (not the stated 5*10^4) -- its independent
    # checker below is an exhaustive bitmask DP (2^n), feeding both the
    # stored-test fill and the 200-trial fuzz; the large_cases further
    # down separately exercise the real 5*10^4 ceiling against the
    # reference only.
    n = rng.choice([1, 2, rng.randint(3, 12)])
    limit = rng.randint(1, 20)
    w = [rng.randint(1, limit) for _ in range(n)]
    return f"{n}\n{_fmt_arr(w)}\n{limit}\n"


def _boats_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); w = list(map(int, lines[1].split())); limit = int(lines[2])
    return len(w) == n and 1 <= n <= 50000 and all(1 <= x <= limit for x in w)


def _boats_checker(stdin: str) -> str:
    """Independent of the reference's sort-then-two-pointer: an
    exhaustive bitmask DP over all pairings of unassigned people (does
    pairing i with j ever help?) -- O(2^n * n), capped to small n by
    the generator above. A general subset-matching search, not
    dependent on the two-pointer's own sortedness insight."""
    from functools import lru_cache
    lines = stdin.split("\n")
    n = int(lines[0]); w = list(map(int, lines[1].split())); limit = int(lines[2])

    @lru_cache(maxsize=None)
    def solve(mask):
        if mask == 0:
            return 0
        i = (mask & -mask).bit_length() - 1
        rest = mask & ~(1 << i)
        best = solve(rest)
        m = rest
        while m:
            j = (m & -m).bit_length() - 1
            m &= ~(1 << j)
            if w[i] + w[j] <= limit:
                best = max(best, 1 + solve(rest & ~(1 << j)))
        return best

    max_pairs = solve((1 << n) - 1)
    solve.cache_clear()
    return str(n - max_pairs)


def _boats_large(n: int) -> str:
    w = [((i % 50) + 1) for i in range(n)]
    return f"{n}\n{_fmt_arr(w)}\n51\n"


_register(ProblemInputSpec(
    "greedy-boats-save-people", "array_with_limit",
    {"n_min": 1, "n_max": 50000},
    ["4\n1 2 2 3\n3", "1\n5\n5"],
    _boats_random, _boats_validate, _boats_checker,
    large_cases=[
        # Intended complexity: O(n log n) (sort, two pointers). The
        # exhaustive bitmask checker above is excluded entirely from the
        # checker-agreement quality gate for these 2 inputs -- it's
        # already capped to tiny n by the generator and was never meant
        # to run at this scale; checker correctness stays covered by the
        # 200-trial small-input fuzz. See
        # test_problem_bank_batch2_large_input_complexity.py for a naive
        # O(n^2) re-implementation of the SAME greedy idea (using
        # repeated list max/min/remove -- each O(n) -- inside an O(n)
        # outer loop) that times out here while the reference doesn't.
        _boats_large(50000),
        _boats_large(49999),
    ],
))


# ---- greedy-min-arrows-balloons  --  shape: interval_list (reused) --------

def _min_arrows_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    ivs = lines[1:1 + n]
    if len(ivs) != n or not (1 <= n <= 100000):
        return False
    for iv in ivs:
        s, e = map(int, iv.split())
        if e < s:
            return False
    return True


def _max_non_overlap_bruteforce_strict(intervals: List[Tuple[int, int]]) -> int:
    """Same O(n^2) DP shape as batch 1's _max_non_overlap_bruteforce,
    but with a STRICTLY different compatibility rule, deliberately not
    reused as-is: confirmed directly (a 200-trial fuzz disagreement,
    reference=11 vs this-reused-as-is=13 on a 50-balloon input) that
    activity-selection's own "touching endpoints don't overlap" rule
    does NOT apply to the balloon-arrow problem. There, an arrow at x
    bursts a balloon whose interval endpoint EQUALS x too (the
    problem's own stated rule) -- so two balloons that only touch at a
    single point (one's end == the other's start) DO share a point and
    CAN be hit by the same arrow; they are only counted as needing
    SEPARATE arrows when one ends STRICTLY before the other starts.
    Swapping batch 1's `<=` for a strict `<` here is the entire fix."""
    ivs = sorted(intervals, key=lambda x: x[1])
    n = len(ivs)
    dp = [0] * n
    for i in range(n):
        best = 1
        for j in range(i):
            if ivs[j][1] < ivs[i][0]:  # strict -- see docstring above
                best = max(best, dp[j] + 1)
        dp[i] = best
    return max(dp) if dp else 0


def _min_arrows_checker(stdin: str) -> str:
    """Min arrows to burst every balloon equals the MAXIMUM number of
    pairwise non-overlapping balloons (classic interval-point-cover /
    interval-scheduling LP duality -- confirmed directly with a
    counterexample against the weaker "connected components of the
    overlap graph" guess, which is wrong here: a bridging interval can
    connect two balloons that share no common point at all), using the
    STRICT non-overlap rule this problem actually needs -- see
    _max_non_overlap_bruteforce_strict's own docstring for why batch
    1's non-strict version was wrong here and how that was confirmed."""
    lines = stdin.split("\n")
    n = int(lines[0])
    ivs = [tuple(map(int, lines[1 + i].split())) for i in range(n)]
    return str(_max_non_overlap_bruteforce_strict(ivs))


def _min_arrows_large(seed: str, n: int = 100000) -> str:
    rng = random.Random(seed)
    lines = [str(n)]
    for _ in range(n):
        s = rng.randint(0, 4000)
        e = s + rng.randint(0, 10)
        lines.append(f"{s} {e}")
    return "\n".join(lines) + "\n"


_register(ProblemInputSpec(
    "greedy-min-arrows-balloons", "interval_list",
    {"n_min": 1, "n_max": 100000},
    ["4\n10 16\n2 8\n1 6\n7 12", "1\n1 1"],
    _interval_list_random, _min_arrows_validate, _min_arrows_checker,
    large_cases=[
        # Intended complexity: O(n log n) (sort by end, sweep). The
        # reused O(n^2) DP checker is excluded from the checker-
        # agreement quality gate for these 2 inputs (10^10 at this
        # ceiling) -- see LARGE_CASES_EXCLUDED_FROM_CHECKER. See
        # test_problem_bank_batch2_large_input_complexity.py for a naive
        # O(n^2) pairwise-rescan re-implementation that times out here.
        _min_arrows_large("2c-batch2-arrows-large-1"),
        _min_arrows_large("2c-batch2-arrows-large-2", n=99999),
    ],
))


# ---- greedy-two-city-scheduling  --  shape: two_int_arrays -----------------

def _two_city_random(rng: random.Random) -> str:
    # Capped small (checker is an exhaustive C(2n, n) combinatorial
    # search) -- large_cases separately exercise the real n<=500
    # ceiling against the reference only.
    n = rng.choice([1, 2, rng.randint(3, 8)])
    costA = gen_int_array(rng, 2 * n, 1, 100)
    costB = gen_int_array(rng, 2 * n, 1, 100)
    return f"{n}\n{_fmt_arr(costA)}\n{_fmt_arr(costB)}\n"


def _two_city_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); costA = list(map(int, lines[1].split())); costB = list(map(int, lines[2].split()))
    return len(costA) == 2 * n and len(costB) == 2 * n and 1 <= n <= 500


def _two_city_checker(stdin: str) -> str:
    """Independent of the reference's sort-by-cost-difference greedy:
    an exhaustive search over every way to choose which n of the 2n
    people go to city A (itertools.combinations), capped to small n by
    the generator above."""
    from itertools import combinations
    lines = stdin.split("\n")
    n = int(lines[0]); costA = list(map(int, lines[1].split())); costB = list(map(int, lines[2].split()))
    total = 2 * n
    best = None
    for a_group in combinations(range(total), n):
        a_set = set(a_group)
        cost = sum(costA[i] if i in a_set else costB[i] for i in range(total))
        if best is None or cost < best:
            best = cost
    return str(best)


def _two_city_large(n: int) -> str:
    rng = random.Random(f"2c-batch2-two-city-large-{n}")
    costA = gen_int_array(rng, 2 * n, 1, 1000)
    costB = gen_int_array(rng, 2 * n, 1, 1000)
    return f"{n}\n{_fmt_arr(costA)}\n{_fmt_arr(costB)}\n"


_register(ProblemInputSpec(
    "greedy-two-city-scheduling", "two_int_arrays",
    {"n_min": 1, "n_max": 500},
    ["2\n10 30 400 30\n20 200 50 20", "1\n10 20\n30 40"],
    _two_city_random, _two_city_validate, _two_city_checker,
    large_cases=[
        # Intended complexity: O(n log n) (sort by cost difference). The
        # exhaustive checker above is excluded entirely from the
        # checker-agreement quality gate for these 2 inputs -- C(1000,
        # 500) is astronomical, it was never meant to run at this scale;
        # checker correctness stays covered by the 200-trial small-input
        # fuzz. See test_problem_bank_batch2_large_input_complexity.py
        # for a naive unmemoized recursive exhaustive A/B search (2^(2n)
        # branches, no pruning) that never finishes here.
        _two_city_large(500),
        _two_city_large(499),
    ],
))


# ---- graph-connected-components  --  shape: edge_list ----------------------

def _conn_components_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 30)])
    m_target = rng.randint(0, min(30, n * (n - 1) // 2)) if n > 1 else 0
    edges = _gen_simple_edges(rng, n, m_target, directed=False)
    return _fmt_edge_list(n, edges)


def _conn_components_checker(stdin: str) -> str:
    """Independent of the reference's iterative stack-based DFS:
    union-find instead."""
    lines = stdin.split("\n")
    n, m = map(int, lines[0].split())
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(1, 1 + m):
        u, v = map(int, lines[i].split())
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
    return str(len({find(i) for i in range(n)}))


_CONN_LARGE_CHAIN = _fmt_edge_list(10000, [(i, i + 1) for i in range(9999)])
_CONN_LARGE_SCATTERED = _fmt_edge_list(10000, [(2 * i, 2 * i + 1) for i in range(5000)])
_register(ProblemInputSpec(
    "graph-connected-components", "edge_list",
    {"n_min": 1, "n_max": 10000, "m_min": 0, "m_max": 10000},
    ["5 3\n0 1\n1 2\n3 4", "4 0"],
    _conn_components_random, _edge_list_validate, _conn_components_checker,
    large_cases=[
        # Intended complexity: O(n + m) (one DFS/union-find pass). The
        # checker is also O(n+m) and fast at full scale -- not excluded.
        # See test_problem_bank_batch2_large_input_complexity.py for a
        # naive O(n*m) re-scan-the-whole-edge-list-per-node approach
        # (instead of pre-building an adjacency list) that times out here.
        _CONN_LARGE_CHAIN,
        _CONN_LARGE_SCATTERED,
    ],
))


# ---- graph-cycle-undirected  --  shape: edge_list --------------------------

def _cycle_undirected_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 30)])
    want_cycle = rng.random() < 0.5
    if want_cycle and n >= 3:
        ring = [(i, (i + 1) % n) for i in range(n)]
        extra = _gen_simple_edges(rng, n, rng.randint(0, 5), directed=False)
        edges = list(dict.fromkeys(tuple(sorted(e)) for e in ring + extra))
    else:
        nodes = list(range(n))
        rng.shuffle(nodes)
        edges = []
        for i in range(1, n):
            if rng.random() < 0.8:
                parent = nodes[rng.randint(0, i - 1)]
                edges.append((parent, nodes[i]))
    return _fmt_edge_list(n, edges)


def _cycle_undirected_checker(stdin: str) -> str:
    """Independent of the reference's union-find: BFS/DFS with explicit
    parent-tracking (seeing an already-visited neighbor that ISN'T your
    immediate parent means a cycle) -- iterative (explicit stack), not
    recursive, so there's no recursion-depth concern at any graph size."""
    lines = stdin.split("\n")
    n, m = map(int, lines[0].split())
    adj = [[] for _ in range(n)]
    for i in range(1, 1 + m):
        u, v = map(int, lines[i].split())
        adj[u].append(v); adj[v].append(u)
    seen = [False] * n
    has_cycle = False
    for start in range(n):
        if seen[start]:
            continue
        seen[start] = True
        stack = [(start, -1)]
        while stack:
            u, parent = stack.pop()
            for v in adj[u]:
                if v == parent:
                    continue
                if seen[v]:
                    has_cycle = True
                    continue
                seen[v] = True
                stack.append((v, u))
    return "YES" if has_cycle else "NO"


_CYCLE_U_LARGE_RING = _fmt_edge_list(10000, [(i, (i + 1) % 10000) for i in range(10000)])
_CYCLE_U_LARGE_TREE = _fmt_edge_list(10000, [(i // 2, i) for i in range(1, 10000)])
_register(ProblemInputSpec(
    "graph-cycle-undirected", "edge_list",
    {"n_min": 1, "n_max": 10000, "m_min": 0, "m_max": 10000},
    ["4 3\n0 1\n1 2\n2 3", "1 0"],
    _cycle_undirected_random, _edge_list_validate, _cycle_undirected_checker,
    large_cases=[
        # Intended complexity: O(n + m). The checker is also O(n+m) and
        # fast at full scale -- not excluded. See
        # test_problem_bank_batch2_large_input_complexity.py for a naive
        # O(n*m) edge-list-rescan approach that times out here. One ring
        # (has a cycle) and one binary tree (acyclic) at the full n=10^4
        # ceiling -- both deliberately shallow/bushy where relevant so
        # neither this checker nor the reference risks deep recursion
        # (both are iterative here regardless, so it's a non-issue, but
        # kept consistent with the rest of the bank's convention).
        _CYCLE_U_LARGE_RING,
        _CYCLE_U_LARGE_TREE,
    ],
))


# ---- graph-cycle-directed  --  shape: edge_list (directed) -----------------

def _cycle_directed_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 30)])
    want_cycle = rng.random() < 0.5
    if want_cycle and n >= 2:
        ring = [(i, (i + 1) % n) for i in range(n)]
        extra = _gen_simple_edges(rng, n, rng.randint(0, 5), directed=True)
        edges = list(dict.fromkeys(ring + extra))
    else:
        edges = _gen_dag_edges(rng, n, rng.randint(0, min(20, n * (n - 1) // 2)))
    return _fmt_edge_list(n, edges)


def _cycle_directed_checker(stdin: str) -> str:
    """Independent of the reference's Kahn's-algorithm indegree/BFS
    processed-count check -- see _directed_has_cycle's own docstring."""
    lines = stdin.split("\n")
    n, m = map(int, lines[0].split())
    adj = [[] for _ in range(n)]
    for i in range(1, 1 + m):
        u, v = map(int, lines[i].split())
        adj[u].append(v)
    return "YES" if _directed_has_cycle(n, adj) else "NO"


def _chain_with_late_back_edge(n: int) -> List[Tuple[int, int]]:
    """A long chain 0->1->...->(n-2) PLUS one extra edge (n-2)->(n-1)
    AND (n-1)->(n-2) (a 2-cycle at the very end) -- Kahn's algorithm
    must pop its way through almost the WHOLE chain (n-2 pops, each an
    O(m) rescan for a naive submission) before the cycle's extra
    indegree is ever discovered, unlike a pure ring, where EVERY node
    already has indegree >=1 and the queue starts completely empty --
    confirmed directly that a pure ring makes even an O(n*m) naive
    submission finish in ~0.1s, since there's nothing to pop at all."""
    edges = [(i, i + 1) for i in range(n - 2)]
    edges.append((n - 2, n - 1))
    edges.append((n - 1, n - 2))
    return edges


_CYCLE_D_LARGE_RING = _fmt_edge_list(10000, _chain_with_late_back_edge(10000))
_CYCLE_D_LARGE_DAG = _fmt_edge_list(10000, [(i, i + 1) for i in range(9999)])
_register(ProblemInputSpec(
    "graph-cycle-directed", "edge_list",
    {"n_min": 1, "n_max": 10000, "m_min": 0, "m_max": 10000},
    ["3 3\n0 1\n1 2\n2 0", "4 3\n0 1\n1 2\n2 3"],
    _cycle_directed_random, _edge_list_validate, _cycle_directed_checker,
    large_cases=[
        # Intended complexity: O(n + m) (Kahn's algorithm). The checker
        # is also O(n+m) and fast at full scale -- not excluded. See
        # test_problem_bank_batch2_large_input_complexity.py for a naive
        # O(n*m) edge-list-rescan approach that times out here (on BOTH
        # of these -- see _chain_with_late_back_edge's own docstring for
        # why the cyclic one is a long chain with a cycle at the far end,
        # not a pure ring).
        _CYCLE_D_LARGE_RING,
        _CYCLE_D_LARGE_DAG,
    ],
))


# ---- graph-course-schedule  --  shape: edge_list_separate_nm (NEW) --------

def _course_schedule_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 30)])
    want_cycle = rng.random() < 0.5
    if want_cycle and n >= 2:
        ring = [(i, (i + 1) % n) for i in range(n)]
        extra = _gen_simple_edges(rng, n, rng.randint(0, 5), directed=True)
        edges = list(dict.fromkeys(ring + extra))
    else:
        edges = _gen_dag_edges(rng, n, rng.randint(0, min(20, n * (n - 1) // 2)))
    lines = [str(n), str(len(edges))]
    lines.extend(f"{a} {b}" for a, b in edges)
    return "\n".join(lines) + "\n"


def _course_schedule_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); m = int(lines[1])
    edge_lines = lines[2:2 + m]
    if len(edge_lines) != m or not (1 <= n <= 10000) or not (0 <= m <= 10000):
        return False
    for line in edge_lines:
        a, b = map(int, line.split())
        if not (0 <= a < n and 0 <= b < n):
            return False
    return True


def _course_schedule_checker(stdin: str) -> str:
    """Independent of the reference's Kahn's-algorithm indegree/BFS
    processed-count check: a schedule is feasible iff the prerequisite
    graph has no cycle -- see _directed_has_cycle."""
    lines = stdin.split("\n")
    n = int(lines[0]); m = int(lines[1])
    adj = [[] for _ in range(n)]
    for i in range(2, 2 + m):
        a, b = map(int, lines[i].split())
        adj[b].append(a)
    return "NO" if _directed_has_cycle(n, adj) else "YES"


def _course_schedule_large(n: int, cyclic: bool) -> str:
    if cyclic:
        # Processing-graph edges (the reference/checker both build
        # adj[b]->a from each "a b" input pair) should form a long
        # chain with a 2-cycle only at the very end -- NOT a pure ring,
        # which gives every node indegree>=1 and an empty initial Kahn's
        # queue, finishing in O(1) regardless of algorithm (confirmed
        # directly -- same issue as graph-cycle-directed's own large
        # case). To get processing-graph edges 0->1->...->(n-2), plus a
        # 2-cycle between the last two nodes, each input pair is
        # written "a b" = "(i+1) i" so adj[i].append(i+1), i.e. edge
        # i->(i+1).
        edges = [(i + 1, i) for i in range(n - 2)]
        edges.append((n - 2, n - 1))
        edges.append((n - 1, n - 2))
    else:
        edges = [(i, i + 1) for i in range(n - 1)]
    lines = [str(n), str(len(edges))]
    lines.extend(f"{a} {b}" for a, b in edges)
    return "\n".join(lines) + "\n"


_register(ProblemInputSpec(
    "graph-course-schedule", "edge_list_separate_nm",
    {"n_min": 1, "n_max": 10000, "m_min": 0, "m_max": 10000},
    ["2\n1\n1 0", "2\n2\n1 0\n0 1"],
    _course_schedule_random, _course_schedule_validate, _course_schedule_checker,
    large_cases=[
        # Intended complexity: O(n + m) (Kahn's algorithm). The checker
        # is also O(n+m) and fast at full scale -- not excluded. See
        # test_problem_bank_batch2_large_input_complexity.py for a naive
        # O(n*m) edge-list-rescan approach that times out here.
        _course_schedule_large(10000, cyclic=True),
        _course_schedule_large(9999, cyclic=False),
    ],
))


# ---- graph-topo-sort-lexo  --  shape: dag_edge_list (NEW) ------------------

def _topo_lexo_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 30)])
    edges = _gen_dag_edges(rng, n, rng.randint(0, min(20, n * (n - 1) // 2)))
    return _fmt_edge_list(n, edges)


def _topo_lexo_checker(stdin: str) -> str:
    """The lexicographically-smallest topological order has no
    fundamentally different correct algorithm -- picking the smallest
    available (indegree-0) node at each step is provably necessary, not
    just one valid heuristic among several. Independent of the
    reference's HEAP-based selection, though: a plain O(n) linear scan
    for the smallest available node each round instead -- O(n^2)
    overall, deliberately the slower implementation of the same
    necessarily-correct greedy rule."""
    lines = stdin.split("\n")
    n, m = map(int, lines[0].split())
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for i in range(1, 1 + m):
        u, v = map(int, lines[i].split())
        adj[u].append(v); indeg[v] += 1
    remaining = {i for i in range(n) if indeg[i] == 0}
    order = []
    while remaining:
        u = min(remaining)
        remaining.discard(u)
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                remaining.add(v)
    return " ".join(map(str, order))


_TOPO_LARGE_NO_EDGES = _fmt_edge_list(10000, [])
_TOPO_LARGE_WIDE = _fmt_edge_list(10000, [(0, i) for i in range(1, 10000)])
_register(ProblemInputSpec(
    "graph-topo-sort-lexo", "dag_edge_list",
    {"n_min": 1, "n_max": 10000, "m_min": 0, "m_max": 10000},
    ["4 3\n0 1\n0 2\n1 3", "3 2\n0 1\n0 2"],
    _topo_lexo_random, _edge_list_validate, _topo_lexo_checker,
    large_cases=[
        # Intended complexity: O((n+m) log n) (heap-based Kahn's). The
        # O(n^2) linear-scan checker above is excluded from the checker
        # -agreement quality gate for exactly these 2 inputs (10^8 at
        # this ceiling -- plausibly too slow for a routine check); see
        # LARGE_CASES_EXCLUDED_FROM_CHECKER. Checker correctness stays
        # covered by the 200-trial small-input fuzz. A plain CHAIN is
        # deliberately NOT used here (confirmed directly): with every
        # node depending on exactly one predecessor, the naive linear
        # scan's "remaining" set never holds more than 1 element, so
        # min() is O(1) throughout and the naive finishes in ~0.1s --
        # these two large cases instead keep "remaining" as large as
        # possible (no dependencies at all, and a star from node 0,
        # which frees all 9999 other nodes simultaneously after one
        # pop) so the O(n^2) gap actually shows up.
        _TOPO_LARGE_NO_EDGES,
        _TOPO_LARGE_WIDE,
    ],
))


# ---- graph-bipartite-check  --  shape: edge_list ---------------------------

def _bipartite_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 30)])
    m_target = rng.randint(0, min(30, n * (n - 1) // 2)) if n > 1 else 0
    edges = _gen_simple_edges(rng, n, m_target, directed=False)
    return _fmt_edge_list(n, edges)


def _bipartite_checker(stdin: str) -> str:
    """Independent of the reference's BFS 2-coloring: a STACK-based
    (not queue-based) 2-coloring traversal instead -- a different
    traversal order, same correctness argument."""
    lines = stdin.split("\n")
    n, m = map(int, lines[0].split())
    adj = [[] for _ in range(n)]
    for i in range(1, 1 + m):
        u, v = map(int, lines[i].split())
        adj[u].append(v); adj[v].append(u)
    color = [-1] * n
    ok = True
    for start in range(n):
        if color[start] != -1:
            continue
        color[start] = 0
        stack = [start]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if color[v] == -1:
                    color[v] = 1 - color[u]
                    stack.append(v)
                elif color[v] == color[u]:
                    ok = False
    return "YES" if ok else "NO"


_BIPARTITE_LARGE_YES = _fmt_edge_list(10000, [(i, i + 1) for i in range(9999)])
_BIPARTITE_LARGE_NO = _fmt_edge_list(9999, [(i, (i + 1) % 9999) for i in range(9999)])
_register(ProblemInputSpec(
    "graph-bipartite-check", "edge_list",
    {"n_min": 1, "n_max": 10000, "m_min": 0, "m_max": 10000},
    ["4 4\n0 1\n1 2\n2 3\n3 0", "3 3\n0 1\n1 2\n2 0"],
    _bipartite_random, _edge_list_validate, _bipartite_checker,
    large_cases=[
        # Intended complexity: O(n + m). The checker is also O(n+m) and
        # fast at full scale -- not excluded. See
        # test_problem_bank_batch2_large_input_complexity.py for a naive
        # O(n*m) edge-list-rescan approach that times out here. A path
        # (bipartite: YES) and an odd-length cycle of 9999 nodes
        # (NOT bipartite: NO) at the full ceiling.
        _BIPARTITE_LARGE_YES,
        _BIPARTITE_LARGE_NO,
    ],
))


# ---- graph-bfs-shortest-path  --  shape: edge_list_with_query (NEW) -------

def _bfs_shortest_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 30)])
    m_target = rng.randint(0, min(30, n * (n - 1) // 2)) if n > 1 else 0
    edges = _gen_simple_edges(rng, n, m_target, directed=False)
    src = rng.randint(0, n - 1)
    dst = rng.randint(0, n - 1)
    return _fmt_edge_list(n, edges) + f"{src} {dst}\n"


def _bfs_shortest_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n, m = map(int, lines[0].split())
    edge_lines = lines[1:1 + m]
    if len(edge_lines) != m or not (1 <= n <= 10000) or not (0 <= m <= 10000):
        return False
    for line in edge_lines:
        u, v = map(int, line.split())
        if not (0 <= u < n and 0 <= v < n) or u == v:
            return False
    src, dst = map(int, lines[1 + m].split())
    return 0 <= src < n and 0 <= dst < n


def _bfs_shortest_checker(stdin: str) -> str:
    """Independent of the reference's plain BFS (FIFO queue): Dijkstra's
    algorithm via a priority queue, treating every edge as weight 1 --
    the same shortest-path result, a completely different traversal
    mechanism (heap-ordered relaxation vs a FIFO queue)."""
    import heapq
    lines = stdin.split("\n")
    n, m = map(int, lines[0].split())
    adj = [[] for _ in range(n)]
    for i in range(1, 1 + m):
        u, v = map(int, lines[i].split())
        adj[u].append(v); adj[v].append(u)
    src, dst = map(int, lines[1 + m].split())
    best = {src: 0}
    dist_found = {}
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if u in dist_found:
            continue
        dist_found[u] = d
        for v in adj[u]:
            nd = d + 1
            if nd < best.get(v, float("inf")):
                best[v] = nd
                heapq.heappush(pq, (nd, v))
    return str(dist_found.get(dst, -1))


_BFS_LARGE_CHAIN = _fmt_edge_list(10000, [(i, i + 1) for i in range(9999)]) + "0 9999\n"
# Deliberately NOT "many small disjoint pairs" (confirmed directly: with
# src and dst both in the SAME 2-node pair, or in separate tiny
# components, BFS visits only 1-2 nodes total before concluding either
# way, finishing in ~0.1s regardless of algorithm). Instead: one big
# chain covering almost every node (so BFS must actually visit nearly
# all of them, each needing an O(m) edge-list rescan for a naive
# submission) plus 2 nodes in a SEPARATE tiny component holding the
# destination, genuinely unreachable only after exploring the whole
# big component first.
_BFS_LARGE_UNREACHABLE = _fmt_edge_list(10000, [(i, i + 1) for i in range(9997)] + [(9998, 9999)]) + "0 9999\n"
_register(ProblemInputSpec(
    "graph-bfs-shortest-path", "edge_list_with_query",
    {"n_min": 1, "n_max": 10000, "m_min": 0, "m_max": 10000},
    ["5 4\n0 1\n1 2\n2 3\n3 4\n0 4", "4 2\n0 1\n2 3\n0 3"],
    _bfs_shortest_random, _bfs_shortest_validate, _bfs_shortest_checker,
    large_cases=[
        # Intended complexity: O(n + m) (plain BFS). The checker is
        # O((n+m) log n) and fast at full scale -- not excluded. See
        # test_problem_bank_batch2_large_input_complexity.py for a naive
        # O(n*m) edge-list-rescan approach that times out here.
        _BFS_LARGE_CHAIN,
        _BFS_LARGE_UNREACHABLE,
    ],
))


# ---- graph-network-delay-time  --  shape: weighted_edge_list (NEW) --------

def _network_delay_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 20)])
    edges = []
    seen = set()
    m_target = rng.randint(0, min(30, n * (n - 1))) if n > 1 else 0
    attempts = 0
    while len(edges) < m_target and attempts < m_target * 20 + 50 and n >= 2:
        attempts += 1
        u, v = rng.sample(range(1, n + 1), 2)
        if (u, v) in seen:
            continue
        seen.add((u, v))
        edges.append((u, v, rng.randint(1, 100)))
    k = rng.randint(1, n)
    lines = [str(n), str(len(edges))]
    lines.extend(f"{u} {v} {w}" for u, v, w in edges)
    lines.append(str(k))
    return "\n".join(lines) + "\n"


def _network_delay_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); m = int(lines[1])
    edge_lines = lines[2:2 + m]
    if len(edge_lines) != m or not (1 <= n <= 100) or not (0 <= m <= n * (n - 1)):
        return False
    for line in edge_lines:
        u, v, w = map(int, line.split())
        if not (1 <= u <= n and 1 <= v <= n):
            return False
    k = int(lines[2 + m])
    return 1 <= k <= n


def _network_delay_checker(stdin: str) -> str:
    """Independent of the reference's Dijkstra (heap): Bellman-Ford --
    relax every edge repeatedly for up to n-1 rounds, O(V*E), a
    completely different shortest-path algorithm."""
    lines = stdin.split("\n")
    n = int(lines[0]); m = int(lines[1])
    edges = []
    for i in range(2, 2 + m):
        u, v, w = map(int, lines[i].split())
        edges.append((u, v, w))
    k = int(lines[2 + m])
    INF = float("inf")
    dist = [INF] * (n + 1)
    dist[k] = 0
    for _ in range(max(0, n - 1)):
        changed = False
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changed = True
        if not changed:
            break
    mx = max(dist[1:n + 1]) if n >= 1 else 0
    return str(mx if mx != INF else -1)


def _network_delay_large(n: int, k: int) -> str:
    # n<=100 is this problem's own (deliberately small) ceiling -- dense
    # complete graph at that ceiling is the largest input it allows.
    edges = [(u, v, ((u * 7 + v * 13) % 50) + 1) for u in range(1, n + 1) for v in range(1, n + 1) if u != v]
    lines = [str(n), str(len(edges))]
    lines.extend(f"{u} {v} {w}" for u, v, w in edges)
    lines.append(str(k))
    return "\n".join(lines) + "\n"


_register(ProblemInputSpec(
    "graph-network-delay-time", "weighted_edge_list",
    {"n_min": 1, "n_max": 100},
    ["4\n4\n2 1 1\n2 3 1\n3 4 1\n1 4 3\n2", "2\n1\n1 2 1\n2"],
    _network_delay_random, _network_delay_validate, _network_delay_checker,
    large_cases=[
        # HONEST NOTE: this problem's own ceiling is n<=100, deliberately
        # small (a dense graph already has up to n*(n-1)~10^4 edges at
        # that size). Both the reference's O((V+E) log V) Dijkstra and
        # the checker's O(V*E) Bellman-Ford finish near-instantly at
        # this scale -- there is no input within the stated constraints
        # where one times out and the other doesn't. These two large
        # cases (both at the full n=100 ceiling, one dense complete
        # graph) confirm correctness/timing at the ceiling only, not a
        # genuine complexity gap -- see
        # test_problem_bank_batch2_large_input_complexity.py, which
        # documents this explicitly rather than fabricating a naive
        # solution that would also finish instantly.
        _network_delay_large(100, 1),
        _network_delay_large(99, 50),
    ],
))


# ---- graph-rotten-oranges  --  shape: rotting_grid (NEW) -------------------

def _rotten_random(rng: random.Random) -> str:
    rows = rng.choice([1, 2, rng.randint(3, 15)])
    cols = rng.choice([1, 2, rng.randint(3, 15)])
    grid = [[rng.choices([0, 1, 2], weights=[1, 3, 1])[0] for _ in range(cols)] for _ in range(rows)]
    return f"{rows} {cols}\n" + "\n".join(_fmt_arr(row) for row in grid) + "\n"


def _rotten_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    rows, cols = map(int, lines[0].split())
    grid_lines = lines[1:1 + rows]
    return (len(grid_lines) == rows and 1 <= rows <= 300 and 1 <= cols <= 300
            and all(len(r.split()) == cols for r in grid_lines)
            and all(v in ("0", "1", "2") for r in grid_lines for v in r.split()))


def _rotten_checker(stdin: str) -> str:
    """Independent of the reference's multi-source BFS queue: brute-
    force minute-by-minute simulation -- repeatedly rescan the WHOLE
    grid and rot every fresh orange adjacent to a rotten one, stopping
    once a full pass makes no change. O((rows*cols)*(rows+cols)) worst
    case -- deliberately the slow, obviously-correct simulation instead
    of a queue that only ever visits each cell once."""
    lines = stdin.split("\n")
    rows, cols = map(int, lines[0].split())
    g = [list(map(int, lines[1 + i].split())) for i in range(rows)]
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
    return str(-1 if fresh_left else minutes)


_ROTTEN_LARGE_CHECKER = "300 300\n" + "\n".join(_fmt_arr([(2 if (r == 0 and c == 0) else 1) for c in range(300)]) for r in range(300)) + "\n"
# Deliberately NOT a checkerboard with no rotten seed at all (confirmed
# directly: with no "2" anywhere, the very first simulation pass finds
# nothing adjacent to rot, so it terminates after 0 minutes in ~0.1s,
# regardless of algorithm -- a degenerate case, not a slow one).
# Instead: the SAME single-corner rotten seed as the case above (so
# rotting genuinely spreads through nearly the whole 300x300 grid over
# ~600 minutes of real simulation work first), but with one single
# cell in the opposite corner walled off by 0s on both of its interior
# neighbors, so it's fresh forever -- unreachability is only concluded
# AFTER all that spreading, not instantly.
def _rotten_large_unreachable_pocket() -> str:
    rows, cols = 300, 300
    g = [[1] * cols for _ in range(rows)]
    g[0][0] = 2
    g[rows - 1][cols - 2] = 0
    g[rows - 2][cols - 1] = 0
    return f"{rows} {cols}\n" + "\n".join(_fmt_arr(row) for row in g) + "\n"


_ROTTEN_LARGE_UNREACHABLE = _rotten_large_unreachable_pocket()
_register(ProblemInputSpec(
    "graph-rotten-oranges", "rotting_grid",
    {"rows_min": 1, "rows_max": 300, "cols_min": 1, "cols_max": 300},
    ["3 3\n2 1 1\n1 1 0\n0 1 1", "1 1\n0"],
    _rotten_random, _rotten_validate, _rotten_checker,
    large_cases=[
        # Intended complexity: O(rows*cols) (multi-source BFS, each cell
        # visited once). The brute-force rescan checker above is O((rows
        # *cols)*(rows+cols)) -- ~5*10^7 at this ceiling, plausibly too
        # slow for a routine check -- excluded from the checker-
        # agreement quality gate for exactly these 2 inputs; see
        # LARGE_CASES_EXCLUDED_FROM_CHECKER. Checker correctness stays
        # covered by the 200-trial small-input fuzz. See
        # test_problem_bank_batch2_large_input_complexity.py for a naive
        # full-grid-rescan-per-minute re-implementation of this SAME
        # checker idea that times out at this scale (confirming the
        # exclusion was the right call, not just a guess).
        _ROTTEN_LARGE_CHECKER,
        _ROTTEN_LARGE_UNREACHABLE,
    ],
))


# ---- string-compression  --  shape: single_string --------------------------

def _compression_random(rng: random.Random) -> str:
    length = rng.choice([0, 1, rng.randint(2, 60)])
    if length == 0:
        return "\n"
    return gen_string(rng, length, "abc")


def _compression_validate(stdin: str) -> bool:
    return len(stdin) <= 100001


def _compression_checker(stdin: str) -> str:
    """Independent of the reference's manual index-scanning loop:
    itertools.groupby instead."""
    import itertools
    s = stdin.split("\n")[0]
    if not s:
        return ""
    return "".join(f"{ch}{sum(1 for _ in g)}" for ch, g in itertools.groupby(s))


_register(ProblemInputSpec(
    "string-compression", "single_string",
    {"len_min": 0, "len_max": 100000},
    ["\n", "a"],
    _compression_random, _compression_validate, _compression_checker,
    large_cases=[
        # HONEST NOTE: run-length encoding is O(n) by its very nature --
        # there's no slower-vs-faster algorithmic choice to time-
        # differentiate here (even the most naive correct approach is a
        # single linear scan). These two confirm the reference handles
        # the full n=10^5 ceiling: one all-distinct-characters case (no
        # compression at all) and one single-run case (maximally
        # compressed) -- not a complexity gap demonstration.
        "".join(chr(ord('a') + i % 26) for i in range(100000)),
        "a" * 100000,
    ],
))


# ---- string-integer-to-roman  --  shape: single_int ------------------------

_ROMAN_THOUSANDS = ["", "M", "MM", "MMM"]
_ROMAN_HUNDREDS = ["", "C", "CC", "CCC", "CD", "D", "DC", "DCC", "DCCC", "CM"]
_ROMAN_TENS = ["", "X", "XX", "XXX", "XL", "L", "LX", "LXX", "LXXX", "XC"]
_ROMAN_ONES = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]


def _int_to_roman_random(rng: random.Random) -> str:
    return str(gen_int(rng, 1, 3999))


def _int_to_roman_validate(stdin: str) -> bool:
    n = int(stdin.split("\n")[0])
    return 1 <= n <= 3999


def _int_to_roman_checker(stdin: str) -> str:
    """Independent of the reference's greedy subtract-the-largest-
    symbol-value loop: direct positional lookup tables (thousands/
    hundreds/tens/ones digit -> symbol group) instead."""
    n = int(stdin.split("\n")[0])
    return (_ROMAN_THOUSANDS[n // 1000] + _ROMAN_HUNDREDS[(n // 100) % 10]
            + _ROMAN_TENS[(n // 10) % 10] + _ROMAN_ONES[n % 10])


_register(ProblemInputSpec(
    "string-integer-to-roman", "single_int",
    {"n_min": 1, "n_max": 3999},
    ["3", "58"],
    _int_to_roman_random, _int_to_roman_validate, _int_to_roman_checker,
    large_cases=[
        # HONEST NOTE: n<=3999 is this problem's own small, fixed
        # ceiling (the largest standard Roman numeral) -- both the
        # reference's greedy loop and the checker's lookup tables are
        # O(1)-ish regardless of n. No complexity gap exists to
        # demonstrate; these two just confirm correctness at the two
        # boundary-shaped values (near the ceiling, and a value that
        # exercises every subtractive-pair symbol).
        "3999",
        "3888",
    ],
))


# ---- string-count-and-say  --  shape: single_int ---------------------------

def _count_and_say_random(rng: random.Random) -> str:
    # Capped at 28, not the stated 30 -- 29 and 30 are reserved
    # exclusively for the 2 large_cases below (this problem's value
    # space is small enough that the random fill could otherwise draw
    # one of them directly, colliding with the reserved large slot).
    return str(gen_int(rng, 1, 28))


def _count_and_say_validate(stdin: str) -> bool:
    n = int(stdin.split("\n")[0])
    return 1 <= n <= 30


def _count_and_say_checker(stdin: str) -> str:
    """Independent of the reference's manual index-scanning run
    detector: a regex (`(.)\\1*`) to find each maximal run instead."""
    import re
    n = int(stdin.split("\n")[0])
    s = "1"
    for _ in range(n - 1):
        s = "".join(f"{len(m.group(0))}{m.group(1)}" for m in re.finditer(r"(.)\1*", s))
    return s


_register(ProblemInputSpec(
    "string-count-and-say", "single_int",
    {"n_min": 1, "n_max": 30},
    ["1", "2"],
    _count_and_say_random, _count_and_say_validate, _count_and_say_checker,
    large_cases=[
        # HONEST NOTE: n<=30 is this problem's own small, fixed ceiling
        # -- deliberately so, because the sequence's own string length
        # grows exponentially (~1.303^n, Conway's constant) regardless
        # of implementation; there is no smarter algorithm than direct
        # simulation, so no naive-vs-reference timing gap exists to
        # demonstrate. This is just the ceiling itself.
        "30",
        "29",
    ],
))


# ---- string-multiply-strings  --  shape: digit_strings_pair (NEW) ---------

def _multiply_strings_random(rng: random.Random) -> str:
    def digit_string(length):
        if length == 1:
            return str(rng.randint(0, 9))
        first = str(rng.randint(1, 9))
        rest = "".join(str(rng.randint(0, 9)) for _ in range(length - 1))
        return first + rest

    la = rng.choice([1, 2, rng.randint(3, 20)])
    lb = rng.choice([1, 2, rng.randint(3, 20)])
    return f"{digit_string(la)}\n{digit_string(lb)}\n"


def _multiply_strings_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    a, b = lines[0], lines[1]
    return (1 <= len(a) <= 200 and 1 <= len(b) <= 200
            and a.isdigit() and b.isdigit()
            and (a == "0" or a[0] != "0") and (b == "0" or b[0] != "0"))


def _multiply_strings_checker(stdin: str) -> str:
    """Independent of the reference's manual digit-by-digit convolution
    with carrying: Python's own arbitrary-precision integer
    multiplication instead -- a completely different (and, deliberately,
    much faster, not slower) implementation path, using the very
    operation the problem asks contestants not to rely on directly for
    this specific verification purpose."""
    lines = stdin.split("\n")
    a, b = lines[0], lines[1]
    return str(int(a) * int(b))


_register(ProblemInputSpec(
    "string-multiply-strings", "digit_strings_pair",
    {"len_min": 1, "len_max": 200},
    ["2\n3", "123\n456"],
    _multiply_strings_random, _multiply_strings_validate, _multiply_strings_checker,
    large_cases=[
        # HONEST NOTE: |a|,|b|<=200 is this problem's own small ceiling
        # -- the reference's O(|a|*|b|) convolution is at most 4*10^4
        # operations there, instant either way. No naive-vs-reference
        # timing gap exists to demonstrate; these two just confirm
        # correctness at the full-length ceiling (all-9s, the worst case
        # for carry propagation, and a value ending in zeros).
        "9" * 200 + "\n" + "9" * 200,
        ("1" + "0" * 199) + "\n" + ("1" + "0" * 199),
    ],
))


# ---- string-zigzag-conversion  --  shape: string_and_rows (NEW) -----------

def _zigzag_random(rng: random.Random) -> str:
    length = rng.choice([1, 2, rng.randint(3, 60)])
    s = gen_string(rng, length, "ABCDE")
    rows = rng.randint(1, max(1, length))
    return f"{s}\n{rows}\n"


def _zigzag_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    s = lines[0]; rows = int(lines[1])
    return 1 <= len(s) <= 1000 and 1 <= rows <= 1000


def _zigzag_checker(stdin: str) -> str:
    """Independent of the reference's direction-pointer row-walk
    simulation: a closed-form modular computation of each character's
    target row, using the zigzag's fixed cycle length (2*rows-2)."""
    lines = stdin.split("\n")
    s = lines[0]; rows = int(lines[1])
    if rows == 1 or rows >= len(s):
        return s
    cycle = 2 * rows - 2
    buckets = [[] for _ in range(rows)]
    for i, ch in enumerate(s):
        pos = i % cycle
        r = pos if pos < rows else cycle - pos
        buckets[r].append(ch)
    return "".join("".join(b) for b in buckets)


_register(ProblemInputSpec(
    "string-zigzag-conversion", "string_and_rows",
    {"len_min": 1, "len_max": 1000, "rows_min": 1, "rows_max": 1000},
    ["PAYPALISHIRING\n3", "PAYPALISHIRING\n4"],
    _zigzag_random, _zigzag_validate, _zigzag_checker,
    large_cases=[
        # HONEST NOTE: both the reference's pointer-walk and the
        # checker's modular formula are O(n) regardless of rows -- no
        # naive-vs-reference timing gap exists to demonstrate at this
        # problem's own n,rows<=1000 ceiling. These two confirm
        # correctness at the full-length ceiling instead (a modest row
        # count that actually zigzags, and rows deliberately close to
        # len(s) so almost every row holds very few characters).
        "".join(chr(ord('A') + i % 26) for i in range(1000)) + "\n17\n",
        "".join(chr(ord('A') + i % 26) for i in range(1000)) + "\n999\n",
    ],
))


# ---- dp-longest-common-subsequence  --  shape: two_strings -----------------

def _lcs_random(rng: random.Random) -> str:
    la = rng.choice([0, 1, rng.randint(2, 30)])
    lb = rng.choice([0, 1, rng.randint(2, 30)])
    a = gen_string(rng, la, "ab") if la else ""
    b = gen_string(rng, lb, "ab") if lb else ""
    return f"{a}\n{b}\n"


def _lcs_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    a = lines[0] if len(lines) > 0 else ""
    b = lines[1] if len(lines) > 1 else ""
    return len(a) <= 1000 and len(b) <= 1000


def _lcs_checker(stdin: str) -> str:
    """Independent of the reference's bottom-up DP table: a top-down
    memoized recursion instead -- same asymptotic complexity, a
    genuinely different implementation technique (recursion + cache vs
    iterative table-filling). Recursion limit is raised defensively
    (depth can reach len(a)+len(b) <= 2000). Uses a plain dict for
    memoization, NOT functools.lru_cache -- confirmed directly that
    lru_cache's own per-call overhead is enough to trip CPython's
    C-stack-based recursion guard at this depth even with
    sys.setrecursionlimit raised well above it (the guard isn't purely
    the logical Python frame count), while an equivalent plain-dict-
    memoized recursion at the identical depth does not."""
    import sys
    sys.setrecursionlimit(5000)
    lines = stdin.split("\n")
    a = lines[0] if len(lines) > 0 else ""
    b = lines[1] if len(lines) > 1 else ""
    memo = {}

    def solve(i, j):
        if i == 0 or j == 0:
            return 0
        key = (i, j)
        if key in memo:
            return memo[key]
        if a[i - 1] == b[j - 1]:
            r = 1 + solve(i - 1, j - 1)
        else:
            r = max(solve(i - 1, j), solve(i, j - 1))
        memo[key] = r
        return r

    result = solve(len(a), len(b))
    return str(result)


_register(ProblemInputSpec(
    "dp-longest-common-subsequence", "two_strings",
    {"len_min": 0, "len_max": 1000},
    ["abcde\nace", "abc\nabc"],
    _lcs_random, _lcs_validate, _lcs_checker,
    large_cases=[
        # Intended complexity: O(n*m) DP. A naive unmemoized recursive
        # re-implementation of the SAME recurrence is O(2^(n+m)) -- see
        # test_problem_bank_batch2_large_input_complexity.py -- and times
        # out at this ceiling while both the reference and this
        # memoized checker (same O(n*m), just a different technique,
        # fast enough to stay IN the checker-agreement quality gate at
        # full scale) finish instantly. Both strings in EACH pair use
        # COMPLETELY DISJOINT alphabets (not just "mismatched at the
        # same diagonal position") -- confirmed directly that this is
        # necessary, not just sufficient: two attempts with same-
        # alphabet patterns mismatched only at the i==j diagonal (an
        # alternating "ab"/"ba" pair, and a block-split variant) still
        # let the unmemoized recursion find an OFF-diagonal character
        # match at roughly half of all (i,j) pairs it explores purely
        # by chance (since solve(i,j) explores many i!=j pairs too),
        # each one a free single-path shortcut with no further
        # branching -- both finished in well under 0.1s instead of
        # timing out. With NO character in common at all between the
        # two strings, a[i-1]==b[j-1] is never true anywhere, so every
        # single call is forced into the full max(solve(i-1,j),
        # solve(i,j-1)) branch, with no shortcut possible.
        "a" * 1000 + "\n" + "b" * 1000,
        "p" * 999 + "\n" + "q" * 999,
    ],
))


# ---- dp-longest-common-substring  --  shape: two_strings -------------------

def _lc_substring_random(rng: random.Random) -> str:
    la = rng.choice([0, 1, rng.randint(2, 25)])
    lb = rng.choice([0, 1, rng.randint(2, 25)])
    a = gen_string(rng, la, "ab") if la else ""
    b = gen_string(rng, lb, "ab") if lb else ""
    return f"{a}\n{b}\n"


def _lc_substring_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    a = lines[0] if len(lines) > 0 else ""
    b = lines[1] if len(lines) > 1 else ""
    return len(a) <= 1000 and len(b) <= 1000


def _lc_substring_checker(stdin: str) -> str:
    """Independent of the reference's DP table: brute-force every
    (i, j) starting-alignment pair and extend a match as far as it goes
    -- O(n*m*min(n,m)) worst case, capped to small lengths by the
    generator above so it's usable in the 200-trial fuzz; deliberately
    the slow, obviously-correct approach."""
    lines = stdin.split("\n")
    a = lines[0] if len(lines) > 0 else ""
    b = lines[1] if len(lines) > 1 else ""
    n, m = len(a), len(b)
    best = 0
    for i in range(n):
        for j in range(m):
            k = 0
            while i + k < n and j + k < m and a[i + k] == b[j + k]:
                k += 1
            if k > best:
                best = k
    return str(best)


_register(ProblemInputSpec(
    "dp-longest-common-substring", "two_strings",
    {"len_min": 0, "len_max": 1000},
    ["abcdxyz\nxyzabcd", "zxabcdezy\nyzabcdezy"],
    _lc_substring_random, _lc_substring_validate, _lc_substring_checker,
    large_cases=[
        # Intended complexity: O(n*m) DP. The brute-force-every-
        # alignment checker above is O(n*m*min(n,m)) -- ~10^9 at this
        # ceiling with many repeated characters -- excluded from the
        # checker-agreement quality gate for exactly these 2 inputs; see
        # LARGE_CASES_EXCLUDED_FROM_CHECKER. Checker correctness stays
        # covered by the 200-trial small-input fuzz. See
        # test_problem_bank_batch2_large_input_complexity.py for a
        # naive O(n*m*min(n,m)) re-implementation of this SAME checker
        # idea that times out at this scale.
        "a" * 1000 + "\n" + "a" * 1000,
        ("ab" * 500) + "\n" + ("ab" * 500),
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
