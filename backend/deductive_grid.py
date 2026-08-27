"""deductive_grid game type -- Latin square puzzle matching Capgemini's real
gamified-round rule: "neither a row nor a column should have similar
symbols." An NxN grid (N in {3,4,5}) is filled with a complete Latin square
(each symbol appears exactly once per row and once per column), only a
SPARSE subset of cells is revealed, one revealed... no, one BLANK cell
among the grid is the "?" target, and the candidate picks the missing
symbol from a small options list by row/column elimination.

Two independent code paths exist on purpose:
  - generate_puzzle(): builds a complete Latin square (cyclic base square +
    random row/column permutation), reveals a sparse subset of cells near
    the target (so it's actually solvable), and picks distractor options
    that are symbols CONFIRMED present in the target's revealed row/column
    (i.e. genuinely conflicting, not just plausible).
  - solve_puzzle(): given ONLY the revealed grid + target position +
    options list (never the generator's rng state, alphabet choice, or the
    full unrevealed square), re-derives the answer by elimination: which
    option's symbol does NOT appear anywhere in the target's revealed row
    or revealed column. Returns None (a hard rejection) unless EXACTLY ONE
    option survives elimination.

verify_puzzle() asserts solve_puzzle()'s prediction matches what
generate_puzzle() actually placed, before a puzzle is allowed into
puzzle_bank -- this is what catches both generator bugs and accidentally
ambiguous puzzles (more than one option looks valid from the sparse
revealed data alone).
"""
from __future__ import annotations
import hashlib
import json
import random
from typing import Any, Dict, List, Optional, Tuple

# Symbol identity is SHAPE ONLY. Color is a fixed 1:1 rendering aid per
# shape, never chosen independently -- two different-colored triangles
# would be ambiguous to a candidate glancing at shape alone (which is
# exactly the mistake the original (shape, color)-combo alphabet made:
# sampling from all 9 combos could hand a puzzle two triangles that only
# differ by color). This map guarantees that can never happen again: color
# is fully determined by shape, so "conflicting symbol" and "conflicting
# shape" are the same thing. Keep this in sync with the frontend's
# SHAPE_COLORS in DeductiveGridQuestion.jsx (color NAMES only here --
# the hex values live frontend-side).
SHAPES = ["circle", "square", "triangle", "cross", "diamond"]
SHAPE_COLORS = {
    "circle": "navy",
    "square": "olive",
    "triangle": "brick",
    "cross": "plum",
    "diamond": "amber",
}

GRID_SIZES = [3, 4, 5]

# "Roughly 3 revealed cells felt right" for 3x3 (confirmed against the
# approved reference mockup) -- scaled linearly with N for 4x4/5x5, tunable
# per call via generate_puzzle(reveal_count=...).
DEFAULT_REVEAL_COUNT = {3: 3, 4: 4, 5: 5}

# Kept fixed at 3 for every grid size rather than scaling with N.
# Judgment call: scaling options up to N would force some distractors to be
# symbols NOT confirmed present in the sparse revealed row/column (since at
# low reveal density there often aren't N-1 distinct revealed conflicts to
# draw from). An unrevealed symbol looks "valid" under sparse info even
# when it isn't -- exactly the ambiguity the "exactly one valid answer"
# requirement forbids. 3 options, built only from CONFIRMED conflicts, is
# what keeps every accepted puzzle genuinely unambiguous.
DEFAULT_NUM_OPTIONS = 3

Symbol = str  # shape name; color is derived via SHAPE_COLORS, never chosen independently
Cell = Optional[Dict[str, str]]  # {"shape":..., "color":...} or None if unrevealed/target


def _symbol_to_cell(sym: Symbol) -> Dict[str, str]:
    return {"shape": sym, "color": SHAPE_COLORS[sym]}


def _cell_to_symbol(cell: Dict[str, str]) -> Symbol:
    return cell["shape"]  # identity is shape only -- color is redundant/derived, never compared


# ============================================================
# GENERATION
# ============================================================

def _build_latin_square(n: int, rng: random.Random) -> Tuple[List[List[Symbol]], List[Symbol]]:
    """Cyclic base square (base[i][j] = alphabet[(i+j) % n]) + random row and
    column permutations. Permuting the order of rows (or columns) of a
    Latin square yields another Latin square -- each row/column is still a
    permutation of the same n symbols, just reordered -- so this preserves
    the row/column-uniqueness property while giving real placement variety
    across puzzles instead of always the same cyclic pattern."""
    alphabet = rng.sample(SHAPES, n)
    base = [[alphabet[(i + j) % n] for j in range(n)] for i in range(n)]
    row_perm = list(range(n))
    col_perm = list(range(n))
    rng.shuffle(row_perm)
    rng.shuffle(col_perm)
    grid = [[base[row_perm[i]][col_perm[j]] for j in range(n)] for i in range(n)]
    return grid, alphabet


def _choose_reveal_positions(n: int, target: Tuple[int, int], reveal_count: int, rng: random.Random) -> set:
    """Reveals cells ONLY within the target's own row and column (never
    elsewhere in the grid) -- directly implements "pick target cell's
    row/column to have enough revealed cells nearby that the puzzle is
    actually solvable by row/column elimination." Splits the reveal budget
    roughly half to the row, half to the column, capped at each line's
    n-1 non-target cells."""
    tr, tc = target
    nontarget_row = [c for c in range(n) if c != tc]
    nontarget_col = [r for r in range(n) if r != tr]

    want_row = min(len(nontarget_row), (reveal_count + 1) // 2)
    want_col = min(len(nontarget_col), reveal_count - want_row)
    leftover = reveal_count - want_row - want_col
    if leftover > 0:
        extra_row = min(leftover, len(nontarget_row) - want_row)
        want_row += extra_row
        leftover -= extra_row
    if leftover > 0:
        extra_col = min(leftover, len(nontarget_col) - want_col)
        want_col += extra_col
        leftover -= extra_col

    revealed_row_cols = rng.sample(nontarget_row, want_row) if want_row else []
    revealed_col_rows = rng.sample(nontarget_col, want_col) if want_col else []

    positions = {(tr, c) for c in revealed_row_cols} | {(r, tc) for r in revealed_col_rows}
    return positions


def generate_puzzle(
    grid_size: int,
    rng: random.Random,
    reveal_count: Optional[int] = None,
    num_options: int = DEFAULT_NUM_OPTIONS,
    max_attempts: int = 200,
) -> Dict[str, Any]:
    n = grid_size
    if n not in GRID_SIZES:
        raise ValueError(f"unsupported grid_size: {n} (must be one of {GRID_SIZES})")
    if reveal_count is None:
        reveal_count = DEFAULT_REVEAL_COUNT[n]

    for _ in range(max_attempts):
        grid, _alphabet = _build_latin_square(n, rng)
        tr, tc = rng.randrange(n), rng.randrange(n)
        correct_symbol = grid[tr][tc]

        revealed_positions = _choose_reveal_positions(n, (tr, tc), reveal_count, rng)

        # Symbols CONFIRMED present in the target's revealed row/column --
        # these are real conflicts, safe as distractors. correct_symbol can
        # never legitimately be in here (Latin square guarantees it's
        # absent from the rest of its own row and column).
        conflicting = {grid[i][j] for (i, j) in revealed_positions}
        conflicting.discard(correct_symbol)
        conflicting_list = list(conflicting)
        if len(conflicting_list) < num_options - 1:
            continue  # not enough confirmed conflicts revealed -- retry with a fresh grid/target
        rng.shuffle(conflicting_list)
        distractors = conflicting_list[: num_options - 1]

        option_symbols = [correct_symbol] + distractors
        idx_order = list(range(num_options))
        rng.shuffle(idx_order)
        shuffled: List[Optional[Symbol]] = [None] * num_options
        correct_index = None
        for slot, orig in zip(idx_order, range(num_options)):
            shuffled[slot] = option_symbols[orig]
            if orig == 0:
                correct_index = slot

        public_grid: List[List[Cell]] = [
            [(_symbol_to_cell(grid[i][j]) if (i, j) in revealed_positions else None) for j in range(n)]
            for i in range(n)
        ]
        options = [_symbol_to_cell(s) for s in shuffled]

        return {
            "gridSize": n,
            "grid": public_grid,
            "targetCell": {"row": tr, "col": tc},
            "options": options,
            "correctAnswer": correct_index,
            "_full_grid_for_verification": [[_symbol_to_cell(sym) for sym in row] for row in grid],
        }

    raise RuntimeError(
        f"generate_puzzle: failed to build a solvable {n}x{n} puzzle after {max_attempts} attempts "
        f"(reveal_count={reveal_count} may be too low for num_options={num_options})"
    )


# ============================================================
# SOLVER -- independent re-derivation from revealed row/column + options
# only. Never reads the generator's rng, alphabet, or full square.
# ============================================================

def solve_puzzle(
    grid: List[List[Cell]],
    target: Tuple[int, int],
    options: List[Dict[str, str]],
) -> Optional[int]:
    """Returns the index into `options` that is absent from every revealed
    cell in the target's row AND column -- i.e. the only symbol that
    doesn't conflict with what's already visible. Returns None (hard
    rejection) unless EXACTLY ONE option satisfies that, since more than
    one "looks valid" means the puzzle is ambiguous from the visible data,
    and zero means it's unsolvable as given -- callers must treat None as a
    rejection, never fall back to trusting the generator."""
    tr, tc = target
    n = len(grid)

    excluded: set = set()
    for c in range(n):
        if c != tc and grid[tr][c] is not None:
            excluded.add(_cell_to_symbol(grid[tr][c]))
    for r in range(n):
        if r != tr and grid[r][tc] is not None:
            excluded.add(_cell_to_symbol(grid[r][tc]))

    candidates = [i for i, opt in enumerate(options) if _cell_to_symbol(opt) not in excluded]
    if len(candidates) != 1:
        return None
    return candidates[0]


def verify_puzzle(puzzle: Dict[str, Any]) -> bool:
    """Re-derives the answer from ONLY the public fields (grid/targetCell/
    options) -- exactly what a client or a later re-verification pass would
    have -- and checks it matches the stored correctAnswer."""
    target = (puzzle["targetCell"]["row"], puzzle["targetCell"]["col"])
    predicted = solve_puzzle(puzzle["grid"], target, puzzle["options"])
    return predicted == puzzle["correctAnswer"]


def content_hash(grid: List[List[Cell]], target: Tuple[int, int], grid_size: int) -> str:
    payload = json.dumps({"gridSize": grid_size, "grid": grid, "target": list(target)}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
