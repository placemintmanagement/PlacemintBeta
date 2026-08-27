"""switch_challenge game type -- a fixed 4-shape input/output code puzzle.

A top row shows 4 shapes in some order; that order DEFINES positions 1-4
(the "input code"). A bottom row shows the same 4 shapes reordered (the
"output"). The candidate answers with a 4-digit sequence: for each output
shape (left to right), which input position it came from.

Example: top = circle, triangle, square, cross (positions 1,2,3,4).
bottom = triangle, square, cross, circle -> triangle is input-position 2,
square is 3, cross is 4, circle is 1 -> answer "2341".

Unlike deductive_grid, NOTHING is hidden here -- both rows are always fully
visible. The only thing to verify independently is that the digit-sequence
answer is actually the correct re-derivation from the two visible rows, not
a generator bookkeeping bug.

Two independent code paths exist on purpose, same principle as
deductive_grid:
  - generate_puzzle(): picks a random top-row order and a random (different)
    bottom-row order, computes the answer from its own placement, builds
    distractor options.
  - solve_puzzle(): given ONLY the two visible rows, re-derives the
    digit-sequence from scratch via a standalone position lookup -- shares
    no code with the generator's own answer construction.

verify_puzzle() asserts they agree before a puzzle is allowed into
puzzle_bank.
"""
from __future__ import annotations
import hashlib
import json
import random
from typing import Any, Dict, List, Optional

SHAPES = ["circle", "triangle", "square", "cross"]
NUM_SHAPES = len(SHAPES)  # fixed at 4 -- no grid/shape-count scaling for this game type

DEFAULT_NUM_OPTIONS = 4


def _random_permutation(rng: random.Random) -> List[str]:
    perm = list(SHAPES)
    rng.shuffle(perm)
    return perm


def generate_puzzle(rng: random.Random, num_options: int = DEFAULT_NUM_OPTIONS, max_attempts: int = 200) -> Dict[str, Any]:
    for _ in range(max_attempts):
        top_row = _random_permutation(rng)
        bottom_row = _random_permutation(rng)
        if bottom_row == top_row:
            continue  # trivial "1234" answer -- not a real puzzle, retry

        position = {shape: i + 1 for i, shape in enumerate(top_row)}
        correct_answer = "".join(str(position[shape]) for shape in bottom_row)

        # Distractors: other permutations of the digits 1-4, all provably
        # wrong by direct computation from the fully-visible rows (unlike
        # deductive_grid, there's no "looks plausible under sparse info"
        # ambiguity risk here -- every non-matching digit-string is
        # unambiguously wrong).
        all_digit_perms = ["".join(p) for p in _all_permutations("1234")]
        candidates = [p for p in all_digit_perms if p != correct_answer]
        rng.shuffle(candidates)
        distractors = candidates[: num_options - 1]
        if len(distractors) < num_options - 1:
            continue  # shouldn't happen with 4 shapes (24 perms available), defensive retry

        options = [correct_answer] + distractors
        idx_order = list(range(num_options))
        rng.shuffle(idx_order)
        shuffled = [None] * num_options
        correct_index = None
        for slot, orig in zip(idx_order, range(num_options)):
            shuffled[slot] = options[orig]
            if orig == 0:
                correct_index = slot

        return {
            "topRow": top_row,
            "bottomRow": bottom_row,
            "options": shuffled,
            "correctAnswer": correct_index,
        }

    raise RuntimeError(f"generate_puzzle: failed to build a valid puzzle after {max_attempts} attempts")


def _all_permutations(s: str) -> List[str]:
    if len(s) <= 1:
        return [s]
    out = []
    for i, ch in enumerate(s):
        for rest in _all_permutations(s[:i] + s[i + 1:]):
            out.append(ch + rest)
    return out


# ============================================================
# SOLVER -- independent re-derivation from the two visible rows only.
# Shares no code with generate_puzzle()'s own answer construction.
# ============================================================

def solve_puzzle(top_row: List[str], bottom_row: List[str], options: List[str]) -> Optional[int]:
    """Re-derives the digit-sequence from the two visible rows via a
    standalone position lookup, then returns the index into `options` that
    matches. Returns None (hard rejection) if the rows are malformed
    (duplicate shape, length mismatch, unknown shape) or if the derived
    answer doesn't appear in `options` at all -- callers must treat None as
    a rejection, never fall back to trusting the generator."""
    if len(top_row) != NUM_SHAPES or len(bottom_row) != NUM_SHAPES:
        return None
    if len(set(top_row)) != NUM_SHAPES or len(set(bottom_row)) != NUM_SHAPES:
        return None  # duplicate shape in a row -- malformed
    if set(top_row) != set(SHAPES) or set(bottom_row) != set(SHAPES):
        return None  # unknown shape -- malformed

    position = {}
    for i, shape in enumerate(top_row):
        position[shape] = i + 1

    digits = []
    for shape in bottom_row:
        digits.append(str(position[shape]))
    derived = "".join(digits)

    matches = [i for i, opt in enumerate(options) if opt == derived]
    if len(matches) != 1:
        return None  # answer missing from options, or duplicate options -- reject
    return matches[0]


def verify_puzzle(puzzle: Dict[str, Any]) -> bool:
    predicted = solve_puzzle(puzzle["topRow"], puzzle["bottomRow"], puzzle["options"])
    return predicted == puzzle["correctAnswer"]


def content_hash(top_row: List[str], bottom_row: List[str]) -> str:
    payload = json.dumps({"topRow": top_row, "bottomRow": bottom_row}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
