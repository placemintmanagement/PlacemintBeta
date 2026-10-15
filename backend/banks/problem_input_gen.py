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


SPECS: dict = {}


def _register(spec: ProblemInputSpec) -> None:
    SPECS[spec.problem_id] = spec


# =============================================================================
# 1. two-sum  --  shape: int_array_with_target
# =============================================================================

def _two_sum_random(rng: random.Random) -> str:
    n = rng.choice([2, 3, 5, rng.randint(6, 60)])
    vals = rng.sample(range(-500, 500), n) if n <= 1000 else [rng.randint(-500, 500) for _ in range(n)]
    i, j = rng.sample(range(n), 2)
    target = vals[i] + vals[j]
    return f"{n}\n{_fmt_arr(vals)}\n{target}\n"


def _two_sum_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0])
    arr = list(map(int, lines[1].split()))
    int(lines[2])  # target must parse
    return len(arr) == n and 2 <= n <= 10000


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


def _gen_tree_tokens(rng: random.Random, max_nodes: int, symmetric_bias: float = 0.0) -> List[str]:
    """Builds a level-order token list ('N' = missing child) for a random
    binary tree with at most max_nodes real nodes, BFS-style (the same
    shape build() in problem_bank.py expects). symmetric_bias > 0 skews
    toward actually-symmetric trees so tree-symmetric's generator doesn't
    only ever produce 'NO' cases."""
    if max_nodes <= 0:
        return ["N"]
    n_real = rng.randint(1, max_nodes)
    tokens = [str(gen_int(rng, -100, 100))]
    real_so_far = 1
    i = 0
    while i < len(tokens) and real_so_far < n_real:
        if tokens[i] == "N":
            i += 1
            continue
        for _ in range(2):
            if real_so_far < n_real and rng.random() < 0.7:
                tokens.append(str(gen_int(rng, -100, 100)))
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


# =============================================================================
# 17. greedy-assign-cookies  --  shape: two_int_arrays
# =============================================================================

def _cookies_random(rng: random.Random) -> str:
    n = rng.choice([1, 2, rng.randint(3, 80)])
    m = rng.choice([1, 2, rng.randint(3, 80)])
    g = gen_int_array(rng, n, 1, 100)
    s = gen_int_array(rng, m, 1, 100)
    return f"{n}\n{_fmt_arr(g)}\n{m}\n{_fmt_arr(s)}\n"


def _cookies_validate(stdin: str) -> bool:
    lines = stdin.split("\n")
    n = int(lines[0]); g = list(map(int, lines[1].split()))
    m = int(lines[2]); s = list(map(int, lines[3].split()))
    return len(g) == n and len(s) == m and 1 <= n <= 10000 and 1 <= m <= 10000


_register(ProblemInputSpec(
    "greedy-assign-cookies", "two_int_arrays",
    {"n_min": 1, "n_max": 10000, "m_min": 1, "m_max": 10000},
    ["1\n1\n1\n1", "1\n100\n1\n1",
     f"10000\n{_fmt_arr([1] * 10000)}\n10000\n{_fmt_arr([1] * 10000)}"],
    _cookies_random, _cookies_validate, None,
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


_register(ProblemInputSpec(
    "string-isomorphic", "two_strings_equal_length",
    {"len_min": 0, "len_max": 100000},
    # "\n\n", not "\n" -- same EOF reasoning as string-valid-anagram above.
    ["\n\n", "a\na\n", "ab\naa\n"],
    _isomorphic_random, _isomorphic_validate, None,
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


_register(ProblemInputSpec(
    "string-word-pattern", "pattern_and_words",
    {"pattern_len_min": 1, "pattern_len_max": 300},
    ["a\ndog", f"{'a' * 300}\n" + " ".join(["w0"] * 300)],
    _word_pattern_random, _word_pattern_validate, None,
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
