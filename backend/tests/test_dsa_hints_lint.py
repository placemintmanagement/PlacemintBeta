"""Lint for the static DSA hint ladders (Capgemini Spark/Dave/Commit --
STAGE 1 of the DSA-hints build, hints only, no wiring yet). Pure string
checks against spark/hints.py and dave/hints.py; no model call, no
server.py import, no DB. Commit tier is not checked separately here since
it reuses dave/hints.py verbatim (see that module's own docstring) --
there is nothing Commit-specific to lint.

Rules enforced (per the task spec):
  1. Every problem in the matching DSA bank has exactly one hint ladder,
     and every ladder has exactly 3 hints (1:1 id match, both directions).
  2. No hint exceeds 40 words.
  3. No hint contains a code fence, backticks, "def ", "for i in", "the
     answer", "solution", "correct", "wrong", "incorrect", or "not right"
     (case-insensitive for the word-ish ones; literal for the others).
  4. L1 (the first hint in each ladder) names no technique or data
     structure, checked against a fixed list via whole-word matching (so
     "sorted"/"mapping"/"pointing" are not false positives for
     "sort"/"map"/"pointer" -- the point of the rule is that L1 stays a
     plain-language nudge, not that any unlucky substring trips it)."""
import re

import pytest

from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview.spark.dsa import (
    SPARK_DSA_PROBLEMS,
)
from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview.spark.hints import (
    SPARK_DSA_HINTS,
)
from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview.dave.dsa import (
    DAVE_DSA_PROBLEMS,
)
from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview.dave.hints import (
    DAVE_DSA_HINTS,
)

FORBIDDEN_SUBSTRINGS = [
    "```", "`", "def ", "for i in",
    "the answer", "solution", "correct", "wrong", "incorrect", "not right",
]

# Whole-word, case-insensitive. "binary search" is two words, matched as a
# phrase; everything else is a single word.
TECHNIQUE_TERMS = [
    "hash", "map", "set", "stack", "queue", "heap", "pointer", "pointers", "sort", "sorted", "sorting",
    "binary search", "dp", "dynamic", "greedy", "graph", "bfs", "dfs", "tree", "trees",
    "recursion", "recursive", "sliding",
]
_TECHNIQUE_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in TECHNIQUE_TERMS) + r")\b", re.IGNORECASE)


def _banks_and_hints():
    return [
        ("spark", SPARK_DSA_PROBLEMS, SPARK_DSA_HINTS),
        ("dave", DAVE_DSA_PROBLEMS, DAVE_DSA_HINTS),
    ]


def _word_count(text: str) -> int:
    return len(text.split())


def test_hint_ids_match_problem_banks_1_to_1():
    for tier, problems, hints in _banks_and_hints():
        problem_ids = {p["id"] for p in problems}
        hint_ids = set(hints.keys())
        missing = problem_ids - hint_ids
        extra = hint_ids - problem_ids
        assert not missing, f"[{tier}] problems with no hint ladder: {sorted(missing)}"
        assert not extra, f"[{tier}] hint ladders with no matching problem: {sorted(extra)}"


def test_every_ladder_has_exactly_three_hints():
    for tier, _problems, hints in _banks_and_hints():
        for pid, ladder in hints.items():
            assert len(ladder) == 3, f"[{tier}:{pid}] expected exactly 3 hints, got {len(ladder)}"


def test_no_hint_exceeds_forty_words():
    for tier, _problems, hints in _banks_and_hints():
        for pid, ladder in hints.items():
            for level, text in zip(("L1", "L2", "L3"), ladder):
                n = _word_count(text)
                assert n <= 40, f"[{tier}:{pid}:{level}] {n} words (max 40): {text!r}"


def test_no_hint_contains_forbidden_substrings():
    for tier, _problems, hints in _banks_and_hints():
        for pid, ladder in hints.items():
            for level, text in zip(("L1", "L2", "L3"), ladder):
                lowered = text.lower()
                for bad in FORBIDDEN_SUBSTRINGS:
                    assert bad not in lowered, f"[{tier}:{pid}:{level}] contains forbidden {bad!r}: {text!r}"


def test_l1_never_names_a_technique_or_data_structure():
    for tier, _problems, hints in _banks_and_hints():
        for pid, ladder in hints.items():
            l1 = ladder[0]
            m = _TECHNIQUE_RE.search(l1)
            assert m is None, f"[{tier}:{pid}:L1] names a technique ({m.group(0)!r}): {l1!r}"


def test_hints_are_non_empty_strings():
    for tier, _problems, hints in _banks_and_hints():
        for pid, ladder in hints.items():
            for level, text in zip(("L1", "L2", "L3"), ladder):
                assert isinstance(text, str) and text.strip(), f"[{tier}:{pid}:{level}] empty or non-string hint"
