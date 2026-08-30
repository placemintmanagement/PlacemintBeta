"""inductive_challenge game type -- shown a demo "before"/"after" grid pair
related by a fixed rule (a shape-substitution cycle applied uniformly to
every cell), the candidate must pick which 2 of 4 further candidate grids
relate to each other via that SAME rule (unordered pair, multi-select
exactly 2 of 4).

v1 rule scope (confirmed): a single full cyclic permutation across a fixed
4-shape alphabet (circle, square, triangle, cross) -- matches the one
confirmed reference example (cross->circle->triangle->square->cross)
exactly. Color is never an independent axis: reuses deductive_grid's fixed
shape->color map, so a shape substitution inherently carries its color
change with it. Rotation, position-shift, and color-only rules are
explicitly out of scope for v1.

Two independent code paths exist on purpose, same discipline as every
other type in this suite:
  - generate_true_pair/generate_decoy/generate_instance() (generator
    side): KNOWS the mapping it chose (it built it), uses that knowledge
    to construct a true pair plus two "near miss" decoys -- each decoy is
    an independent base grid transformed by the SAME mapping, then
    perturbed at 1-2 cells so it looks like it could almost be a valid
    transform without actually being one.
  - solve_inductive() (verifier side): re-derives the rule from the demo
    pair's own VISIBLE cells only -- never reads the generator's `mapping`
    variable. Rejects if the demo pair is internally inconsistent or
    doesn't cover all 4 shapes (insufficient info to test candidates
    against), then exhaustively checks all 6 possible pairs among the 4
    candidates and hard-rejects unless EXACTLY ONE pair satisfies the rule
    (checked in both directions, since selection is unordered).

Unlike grid_challenge's rotation math, "apply a dict-lookup substitution"
has essentially no room for two genuinely different correct
implementations -- so both sides call the same apply_shape_mapping()
helper. What IS kept independent, and is the thing actually worth
protecting against a generator bug, is WHICH mapping gets used: the
generator's own choice is never passed into solve_inductive(); it must be
rediscovered from the demo pair's cells, exactly like every other type in
this suite never trusts its own bookkeeping.

generate_instance()'s mandatory retry check regenerates a decoy (never
the true pair) whenever that decoy would create an accidental second
valid pair, an accidental duplicate grid, or an accidental relation to any
other shown grid -- then, as a final hard gate before returning, calls
solve_inductive() itself (the fully independent path) and rejects the
whole set (raising RuntimeError, caught by the caller and retried with
fresh randomness) if it disagrees with what the generator intended.

Session fit: like deductive_grid/switch_challenge, NOT grid_challenge --
everything (demoBefore/demoAfter/all 4 candidates) is safe to reveal
upfront, only `correctAnswer` is server-only. Registered in game_types.py
with `answer_check` (a puzzle produces exactly one gradable sub-answer,
just shaped as a 2-element index list instead of a single index), not
`phase_check` -- no progressive-reveal endpoint layer needed for this type.

STATUS: solver/verifier + generator/verify/content_hash wrapper, and the
game_types.py registry entry, are built (Steps 1-2). No puzzle_bank
writes, no gamified_round_config wiring, no frontend component -- those
are later, unapproved steps.
"""
from __future__ import annotations
import hashlib
import json
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

Grid = List[List[Dict[str, str]]]

# Matches deductive_grid.SHAPE_COLORS exactly for the 4 shapes shared
# between the two types, so a "circle" always renders the same regardless
# of which game type it appears in.
SHAPES = ["circle", "square", "triangle", "cross"]
SHAPE_COLORS = {
    "circle": "navy",
    "square": "olive",
    "triangle": "brick",
    "cross": "plum",
}

GRID_SIZE = 3


# ---------------------------------------------------------------------------
# Shared primitives (grid construction, mapping application, comparison)
# ---------------------------------------------------------------------------

def random_cycle(rng: random.Random) -> List[str]:
    """A random ordering of all 4 shapes, read as a single cycle:
    shapes[i] -> shapes[(i+1) % 4]. Because every one of the 4 elements is
    included and the link step is exactly 1, this is ALWAYS a single full
    4-cycle with zero fixed points -- never a degenerate 2-swap or partial
    cycle, matching the one confirmed reference example's structure.
    """
    order = SHAPES[:]
    rng.shuffle(order)
    return order


def cycle_to_mapping(cycle_order: Sequence[str]) -> Dict[str, str]:
    n = len(cycle_order)
    return {cycle_order[i]: cycle_order[(i + 1) % n] for i in range(n)}


def _cell(shape: str) -> Dict[str, str]:
    return {"shape": shape, "color": SHAPE_COLORS[shape]}


def random_grid(rng: random.Random, size: int = GRID_SIZE) -> Grid:
    return [[_cell(rng.choice(SHAPES)) for _ in range(size)] for _ in range(size)]


def full_coverage_random_grid(rng: random.Random, size: int = GRID_SIZE, max_attempts: int = 200) -> Grid:
    """A random grid guaranteed to contain all 4 shapes at least once, so
    any mapping derived from it (as a demo pair) is always FULLY derivable
    -- never partial -- and can be applied to any candidate grid without a
    lookup miss. About 71% of random 3x3 grids already satisfy this by
    chance, so this converges in ~1.4 attempts on average.
    """
    for _ in range(max_attempts):
        grid = random_grid(rng, size)
        if {cell["shape"] for row in grid for cell in row} == set(SHAPES):
            return grid
    raise RuntimeError("full_coverage_random_grid: exceeded max_attempts")


def apply_shape_mapping(grid: Grid, mapping: Dict[str, str]) -> Grid:
    return [[_cell(mapping[cell["shape"]]) for cell in row] for row in grid]


def grids_equal(g1: Grid, g2: Grid) -> bool:
    """Symbol identity is shape only (color is a deterministic function of
    shape), matching deductive_grid's convention.
    """
    if len(g1) != len(g2):
        return False
    for row1, row2 in zip(g1, g2):
        if len(row1) != len(row2):
            return False
        for c1, c2 in zip(row1, row2):
            if c1["shape"] != c2["shape"]:
                return False
    return True


def _grid_signature(grid: Grid) -> Tuple[str, ...]:
    return tuple(cell["shape"] for row in grid for cell in row)


def _pair_matches_mapping(mapping: Dict[str, str], g1: Grid, g2: Grid) -> bool:
    """True if g1->g2 or g2->g1 under `mapping`. Well-defined as an
    UNORDERED check for a single cycle of length >= 3: applying a 4-cycle
    twice does not return you to the start, so rule(g1)=g2 does not itself
    imply rule(g2)=g1 -- checking both directions here cannot create a
    spurious double-match against some THIRD grid for the rule class this
    module supports.
    """
    return grids_equal(apply_shape_mapping(g1, mapping), g2) or grids_equal(apply_shape_mapping(g2, mapping), g1)


# ---------------------------------------------------------------------------
# Generator side
# ---------------------------------------------------------------------------

def generate_true_pair(rng: random.Random, mapping: Dict[str, str]) -> Tuple[Grid, Grid]:
    before = full_coverage_random_grid(rng)
    after = apply_shape_mapping(before, mapping)
    return before, after


def generate_decoy(rng: random.Random, mapping: Dict[str, str]) -> Grid:
    """An independent base grid transformed by the SAME mapping, then
    perturbed at 1-2 cells so it's no longer an exact rule-application of
    its own (discarded) base -- a "near miss" that requires checking every
    cell rather than pattern-matching at a glance, same spirit as
    grid_challenge's perturb-and-verify-independently pattern pairs.
    """
    base = full_coverage_random_grid(rng)
    near = apply_shape_mapping(base, mapping)

    num_perturb = rng.choice([1, 2])
    cells = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)]
    rng.shuffle(cells)

    perturbed = [row[:] for row in near]
    for i in range(num_perturb):
        r, c = cells[i]
        cur_shape = perturbed[r][c]["shape"]
        alt_shapes = [s for s in SHAPES if s != cur_shape]
        perturbed[r] = perturbed[r][:]
        perturbed[r][c] = _cell(rng.choice(alt_shapes))
    return perturbed


def generate_instance(rng: random.Random, max_retries: int = 50) -> Dict[str, Any]:
    """Assembles one full puzzle instance: a demo pair + 4 shuffled
    candidates + which 2 (by post-shuffle index) are the true pair.

    Returns a dict with `demoBefore`, `demoAfter`, `candidates` (list of 4
    grids), and `correctAnswer` (sorted 2-element list of indices into
    `candidates`) -- everything here is safe to reveal EXCEPT
    correctAnswer, which strip_answer() (gamified_round.py) strips before
    any puzzle reaches the client, exactly like the other 3 types.

    Raises RuntimeError if retries are exhausted (caller retries with a
    fresh instance, same convention as every other type's generate_*()).
    """
    cycle_order = random_cycle(rng)
    mapping = cycle_to_mapping(cycle_order)

    demo_before, demo_after = generate_true_pair(rng, mapping)
    true_before, true_after = generate_true_pair(rng, mapping)
    fixed_grids = [demo_before, demo_after, true_before, true_after]

    def _clean_decoy(also_avoid: Sequence[Grid] = ()) -> Grid:
        avoid = list(fixed_grids) + list(also_avoid)
        for _ in range(max_retries):
            candidate = generate_decoy(rng, mapping)
            cand_sig = _grid_signature(candidate)
            if any(cand_sig == _grid_signature(g) for g in avoid):
                continue
            if any(_pair_matches_mapping(mapping, candidate, g) for g in avoid):
                continue
            return candidate
        raise RuntimeError("generate_instance: could not build a clean decoy")

    decoy1 = _clean_decoy()
    decoy2 = _clean_decoy(also_avoid=[decoy1])

    slots: List[Grid] = [true_before, true_after, decoy1, decoy2]
    true_pair_slots = (0, 1)

    order = [0, 1, 2, 3]
    rng.shuffle(order)
    shuffled = [slots[i] for i in order]
    true_pair_shuffled = tuple(sorted((order.index(0), order.index(1))))

    # Final mandatory gate: fully independent re-derivation, never reads
    # `mapping` above. Disagreement means the set is rejected outright
    # (not silently "fixed") -- the caller regenerates from scratch.
    result = solve_inductive(demo_before, demo_after, shuffled)
    if result is None or set(result) != set(true_pair_shuffled):
        raise RuntimeError("generate_instance: independent solver disagreed with generator intent")

    return {
        "demoBefore": demo_before,
        "demoAfter": demo_after,
        "candidates": shuffled,
        "correctAnswer": sorted(true_pair_shuffled),
    }


# ---------------------------------------------------------------------------
# Verifier side (independent of everything above)
# ---------------------------------------------------------------------------

def derive_mapping_from_demo(demo_before: Grid, demo_after: Grid) -> Optional[Dict[str, str]]:
    """Re-derives the substitution rule purely from the demo pair's own
    visible cells. Returns None (hard reject) if the demo pair is
    internally inconsistent (some shape maps to two different results),
    isn't a full bijection over the 4-shape alphabet, or doesn't cover all
    4 shapes (insufficient information to test arbitrary candidates).
    """
    if len(demo_before) != GRID_SIZE or len(demo_after) != GRID_SIZE:
        return None

    mapping: Dict[str, str] = {}
    for row_b, row_a in zip(demo_before, demo_after):
        if len(row_b) != GRID_SIZE or len(row_a) != GRID_SIZE:
            return None
        for cell_b, cell_a in zip(row_b, row_a):
            b, a = cell_b["shape"], cell_a["shape"]
            if b not in SHAPES or a not in SHAPES:
                return None
            if b in mapping and mapping[b] != a:
                return None  # demo pair contradicts itself
            mapping[b] = a

    if set(mapping.keys()) != set(SHAPES):
        return None  # demo pair didn't reveal the full rule
    if len(set(mapping.values())) != len(mapping):
        return None  # not injective -- not a valid bijection
    if any(mapping[s] == s for s in SHAPES):
        return None  # a fixed point -- not a valid derangement/cycle

    return mapping


def solve_inductive(demo_before: Grid, demo_after: Grid, candidates: Sequence[Grid]) -> Optional[Tuple[int, int]]:
    """Given a demo pair and exactly 4 candidate grids, returns the
    (i, j) index pair (i < j) that satisfies the demo pair's rule, or None
    if the demo pair is malformed or if the candidates don't yield EXACTLY
    ONE valid pair (ambiguous or unsolvable are both hard-rejected, never
    guessed).
    """
    if len(candidates) != 4:
        return None

    mapping = derive_mapping_from_demo(demo_before, demo_after)
    if mapping is None:
        return None

    valid_pairs = [
        (i, j)
        for i in range(4)
        for j in range(i + 1, 4)
        if _pair_matches_mapping(mapping, candidates[i], candidates[j])
    ]
    if len(valid_pairs) != 1:
        return None
    return valid_pairs[0]


def verify_instance(instance: Dict[str, Any]) -> bool:
    """Re-derives every guarantee from the instance's own public fields
    only -- never trusts whatever generate_instance() thinks it built.
    This is the gate called before any instance is allowed into
    puzzle_bank, same role as verify_puzzle()/verify_instance() play for
    the other three types.
    """
    demo_before = instance.get("demoBefore")
    demo_after = instance.get("demoAfter")
    candidates = instance.get("candidates")
    correct = instance.get("correctAnswer")

    if not isinstance(candidates, list) or len(candidates) != 4:
        return False
    if not isinstance(correct, list) or len(correct) != 2:
        return False
    try:
        correct_ints = sorted(int(x) for x in correct)
    except (TypeError, ValueError):
        return False
    if correct_ints[0] == correct_ints[1] or not (0 <= correct_ints[0] < 4) or not (0 <= correct_ints[1] < 4):
        return False

    result = solve_inductive(demo_before, demo_after, candidates)
    if result is None:
        return False
    return list(result) == correct_ints


def content_hash(instance: Dict[str, Any]) -> str:
    payload = json.dumps({
        "demoBefore": instance["demoBefore"],
        "demoAfter": instance["demoAfter"],
        "candidates": instance["candidates"],
    }, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
