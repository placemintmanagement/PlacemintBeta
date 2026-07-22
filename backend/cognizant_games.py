"""Cognizant's gamified round — a bespoke design, not drawn from real
Cognizant OA content, but built to the exact same engineering standard as
capgemini_challenges.py's rebuilt cognitive challenges: every category is a
SET of procedurally-generated sub-puzzles, zero AI involvement, and where a
puzzle's correctness hinges on one secret fact, that fact is NEVER included
in the public payload — it's returned separately as `secret` and stored
server-side only (see server.py's _store_hidden_answer_key), same as
Capgemini's Grid/Switch/Motion/Digit Challenge.

REBUILT 2026-07-19: previously 3 casual-game types (card matching, memory
recall, connect-the-pairs), two of which (card matching, memory recall) are
now DROPPED rather than fixed — rendering a memory game at all requires
sending the client the full board/sequence in the same payload later tested
on, so there is no way to give them a real hidden secret the way Capgemini's
puzzles have one. `connect_pairs` is kept (its geometric puzzle genuinely
doesn't reveal the answer by being rendered) and its one real bug is fixed:
`_reference_matching` used to leak to the candidate because nothing upstream
stripped it before persisting the item into an attempt's stored section
questions — it's now never returned in `public` at all. Three new categories
(`pattern_break`, `speed_math_chain`, `shape_rotation`) replace the dropped
two, each with a genuine hidden secret.
"""
from __future__ import annotations
import hashlib
import json
import random
from typing import Any, Dict, List, Optional, Set, Tuple

CATEGORIES = ["connect_pairs", "pattern_break", "speed_math_chain", "shape_rotation"]

CATEGORY_LABELS = {
    "connect_pairs": "Connect the Pairs",
    "pattern_break": "Pattern Break",
    "speed_math_chain": "Speed Math Chain",
    "shape_rotation": "Shape Rotation",
}

CATEGORY_INSTRUCTIONS = {
    "connect_pairs": "Connect every point to exactly one other point so that no two lines cross.",
    "pattern_break": "Find the one number that breaks the pattern.",
    "speed_math_chain": "Follow the chain of operations and enter the final result.",
    "shape_rotation": "Click the option that is a true rotation of the base shape (not a mirror image).",
}

N_SUBPUZZLES_PER_CHALLENGE = 4
N_CATEGORIES_PER_SESSION = 3


def content_hash(payload: Dict[str, Any]) -> str:
    canon = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()[:16]


def _make_id(category: str, rng: random.Random) -> str:
    return f"{category}_{rng.randrange(10**6):06d}"


def _generate_subpuzzle_set(
    gen_one_fn,
    rng: random.Random,
    seen_hashes: Set[str],
    n_subpuzzles: int = N_SUBPUZZLES_PER_CHALLENGE,
    max_retries: int = 8,
) -> Tuple[List[Dict[str, Any]], List[Any], List[str]]:
    """Shared building block for every category below. gen_one_fn(rng) ->
    (public_dict, secret_or_None) for exactly one sub-puzzle. Generates
    n_subpuzzles distinct instances — distinct both from what this candidate
    has seen before (seen_hashes, from challenge_repetition.py) AND from each
    other within this same set — retrying up to max_retries times per slot on
    a collision, always possible since generation is procedural.

    Returns (list_of_public_dicts, list_of_secrets_aligned_by_index,
    list_of_content_hashes_aligned_by_index)."""
    publics: List[Dict[str, Any]] = []
    secrets: List[Any] = []
    hashes: List[str] = []
    for _ in range(n_subpuzzles):
        chosen_public, chosen_secret, h = None, None, ""
        for _ in range(max_retries):
            public, secret = gen_one_fn(rng)
            h = content_hash(public)
            if h not in seen_hashes and h not in hashes:
                chosen_public, chosen_secret = public, secret
                break
        if chosen_public is None:
            chosen_public, chosen_secret = public, secret
        publics.append(chosen_public)
        secrets.append(chosen_secret)
        hashes.append(h)
    return publics, secrets, hashes


# ---- 1. connect_pairs: non-crossing perfect matching -----------------------
# The candidate is NOT told which points pair with which — the puzzle is
# purely geometric: find ANY way to connect all points in pairs such that no
# two connecting lines cross. Multiple valid solutions can exist for a given
# point layout; grading verifies the SUBMITTED matching directly via real
# segment-intersection geometry, not equality against one stored "correct"
# answer — any valid non-crossing perfect matching is accepted. No secret to
# hide: correctness is a publicly-checkable geometric constraint, same as
# Capgemini's Deductive Challenge (sudoku rules).

Point = Tuple[int, int]


def _orientation(a: Point, b: Point, c: Point) -> int:
    val = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    if val == 0:
        return 0
    return 1 if val > 0 else 2


def _on_segment(a: Point, b: Point, c: Point) -> bool:
    return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])


def _segments_cross(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    o1, o2 = _orientation(p1, p2, p3), _orientation(p1, p2, p4)
    o3, o4 = _orientation(p3, p4, p1), _orientation(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(p1, p2, p3):
        return True
    if o2 == 0 and _on_segment(p1, p2, p4):
        return True
    if o3 == 0 and _on_segment(p3, p4, p1):
        return True
    if o4 == 0 and _on_segment(p3, p4, p2):
        return True
    return False


def is_noncrossing_perfect_matching(points: Dict[int, Point], pairs: List[Tuple[int, int]]) -> bool:
    used: Set[int] = set()
    for a, b in pairs:
        if a == b or a not in points or b not in points or a in used or b in used:
            return False
        used.add(a)
        used.add(b)
    if used != set(points.keys()):
        return False
    segs = [(points[a], points[b]) for a, b in pairs]
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if _segments_cross(segs[i][0], segs[i][1], segs[j][0], segs[j][1]):
                return False
    return True


def _all_perfect_matchings(ids: List[int]):
    if not ids:
        yield []
        return
    first = ids[0]
    rest = ids[1:]
    for i, partner in enumerate(rest):
        remaining = rest[:i] + rest[i + 1:]
        for sub in _all_perfect_matchings(remaining):
            yield [(first, partner)] + sub


def _generate_points(
    n_pairs: int, rng: random.Random, width: int = 400, height: int = 280, min_dist: int = 40,
) -> Dict[int, Point]:
    points: Dict[int, Point] = {}
    attempts = 0
    target = n_pairs * 2
    while len(points) < target and attempts < 1000:
        attempts += 1
        cand = (rng.randint(20, width - 20), rng.randint(20, height - 20))
        if all((cand[0] - p[0]) ** 2 + (cand[1] - p[1]) ** 2 >= min_dist ** 2 for p in points.values()):
            points[len(points)] = cand
    return points


def gen_connect_pairs_subpuzzle(rng: random.Random, n_pairs: int = 4) -> Tuple[Dict[str, Any], None]:
    """Generate a point layout and CONFIRM (not assume) a non-crossing
    perfect matching exists for it, same brute-force-verify discipline as
    before — but the found matching is used only to confirm solvability and
    is NEVER returned; there is nothing to hide server-side since grading
    re-derives correctness geometrically from the submission itself."""
    for _ in range(20):
        points = _generate_points(n_pairs, rng)
        if len(points) < n_pairs * 2:
            continue
        ids = list(points.keys())
        solvable = any(
            is_noncrossing_perfect_matching(points, matching)
            for matching in _all_perfect_matchings(ids)
        )
        if solvable:
            public = {
                "points": [{"point_id": pid, "x": x, "y": y} for pid, (x, y) in points.items()],
                "n_pairs": n_pairs,
                "canvas_width": 400,
                "canvas_height": 280,
            }
            return public, None
    raise RuntimeError("connect_pairs: failed to generate a solvable point layout after 20 attempts")


def grade_connect_pairs_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"pairs": [[point_id_a, point_id_b], ...]}. Verified
    geometrically against the actual point layout — any valid non-crossing
    perfect matching is accepted, not just one stored answer."""
    if not isinstance(answer, dict):
        return 0.0
    submitted = answer.get("pairs")
    if not isinstance(submitted, list):
        return 0.0
    try:
        pairs = [(int(a), int(b)) for a, b in submitted]
    except (TypeError, ValueError):
        return 0.0
    points = {p["point_id"]: (p["x"], p["y"]) for p in public.get("points", [])}
    return 1.0 if is_noncrossing_perfect_matching(points, pairs) else 0.0


# ---- 2. pattern_break: find the value that breaks the sequence ------------
# A 5-number sequence follows a hidden arithmetic or geometric rule, with
# exactly one value swapped for one that breaks it. The full sequence
# (including the breaker) is shown — nothing to hide about what's rendered —
# but WHICH index is the breaker is the secret; a candidate can't tell just
# by reading the numbers off the network response which one the grader will
# treat as wrong, since more than one index can look "off" without knowing
# the rule.

def gen_pattern_break_subpuzzle(rng: random.Random, length: int = 5) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    kind = rng.choice(["arithmetic", "geometric"])
    if kind == "arithmetic":
        start = rng.randint(1, 20)
        step = rng.choice([2, 3, 4, 5, -2, -3, -4])
        sequence = [start + i * step for i in range(length)]
    else:
        start = rng.randint(1, 5)
        ratio = rng.choice([2, 3])
        sequence = [start * (ratio ** i) for i in range(length)]

    breaker_index = rng.randrange(length)
    true_value = sequence[breaker_index]
    # Perturb by a nonzero offset large enough not to collide with the true value.
    offset = rng.choice([o for o in range(-7, 8) if o != 0])
    sequence[breaker_index] = true_value + offset

    public = {"sequence": sequence}
    secret = {"breaker_index": breaker_index}
    return public, secret


def grade_pattern_break_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"selected_index": int}."""
    if not isinstance(secret, dict) or not isinstance(answer, dict):
        return 0.0
    try:
        selected = int(answer.get("selected_index"))
    except (TypeError, ValueError):
        return 0.0
    return 1.0 if selected == secret.get("breaker_index") else 0.0


# ---- 3. speed_math_chain: mental-math operation chain ----------------------
# The chain itself (start value + operations) is fully shown — it's a mental
# math task, not a puzzle with a hidden layout. Only the final computed
# result is secret, same as Capgemini's Digit Challenge: ground-truthed by
# actually evaluating the chain in Python, never an LLM guess.

def gen_speed_math_chain_subpuzzle(rng: random.Random, n_ops: int = 3) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    start = rng.randint(1, 20)
    value = start
    operations: List[Dict[str, Any]] = []
    for _ in range(n_ops):
        choices = ["add", "multiply"] if value <= 1 else ["add", "subtract", "multiply"]
        op = rng.choice(choices)
        if op == "add":
            v = rng.randint(1, 9)
            value = value + v
        elif op == "subtract":
            v = rng.randint(1, min(9, value))
            value = value - v
        else:
            v = rng.randint(2, 3)
            value = value * v
        operations.append({"op": op, "value": v})

    public = {"start": start, "operations": operations}
    secret = {"correct_result": value}
    return public, secret


def grade_speed_math_chain_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"value": int}."""
    if not isinstance(secret, dict) or not isinstance(answer, dict):
        return 0.0
    try:
        submitted = int(answer.get("value"))
    except (TypeError, ValueError):
        return 0.0
    return 1.0 if submitted == secret.get("correct_result") else 0.0


# ---- 4. shape_rotation: mental rotation vs. mirror-image decoys ------------
# A random 3x3 boolean-grid shape is generated and CONFIRMED (not assumed) to
# have none of the 8 dihedral symmetries — so its 4 rotations and 4 mirrored
# rotations are all pairwise distinct, same "verify solvability, don't rely
# on a theorem" discipline as connect_pairs. One option is a genuine rotation
# of the base; the other three are mirror-then-rotate decoys. Which option
# index is the true rotation is the secret.

Grid = Tuple[Tuple[int, ...], ...]


def _rotate90(grid: Grid) -> Grid:
    n = len(grid)
    return tuple(tuple(grid[n - 1 - c][r] for c in range(n)) for r in range(n))


def _mirror(grid: Grid) -> Grid:
    return tuple(tuple(reversed(row)) for row in grid)


def _all_dihedral(grid: Grid) -> List[Grid]:
    variants = []
    g = grid
    for _ in range(4):
        g = _rotate90(g)
        variants.append(g)
    m = _mirror(grid)
    for _ in range(4):
        m = _rotate90(m)
        variants.append(m)
    return variants


def _random_asymmetric_grid(rng: random.Random, size: int = 3, n_cells: int = 4) -> Grid:
    for _ in range(200):
        cells = rng.sample(range(size * size), n_cells)
        grid = tuple(
            tuple(1 if (r * size + c) in cells else 0 for c in range(size))
            for r in range(size)
        )
        variants = _all_dihedral(grid)
        if len(set(variants)) == 8:  # all 4 rotations + all 4 mirrored-rotations distinct
            return grid
    raise RuntimeError("shape_rotation: failed to generate an asymmetric shape after 200 attempts")


def _grid_to_list(grid: Grid) -> List[List[int]]:
    return [list(row) for row in grid]


def gen_shape_rotation_subpuzzle(rng: random.Random) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    base = _random_asymmetric_grid(rng)
    true_rotation_degrees = rng.choice([90, 180, 270])
    n_rotations = true_rotation_degrees // 90
    true_rotation = base
    for _ in range(n_rotations):
        true_rotation = _rotate90(true_rotation)

    mirrored = _mirror(base)
    decoys: List[Grid] = []
    seen: Set[Grid] = {base, true_rotation}
    attempts = 0
    while len(decoys) < 3 and attempts < 50:
        attempts += 1
        g = mirrored
        for _ in range(rng.randrange(4)):
            g = _rotate90(g)
        if g not in seen:
            decoys.append(g)
            seen.add(g)
    if len(decoys) < 3:
        raise RuntimeError("shape_rotation: failed to generate 3 distinct decoys")

    options = [true_rotation] + decoys
    order = list(range(4))
    rng.shuffle(order)
    shuffled_options = [options[i] for i in order]
    correct_option_index = order.index(0)

    public = {
        "base_grid": _grid_to_list(base),
        "options": [_grid_to_list(o) for o in shuffled_options],
    }
    secret = {"correct_option_index": correct_option_index}
    return public, secret


def grade_shape_rotation_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"selected_index": int}."""
    if not isinstance(secret, dict) or not isinstance(answer, dict):
        return 0.0
    try:
        selected = int(answer.get("selected_index"))
    except (TypeError, ValueError):
        return 0.0
    return 1.0 if selected == secret.get("correct_option_index") else 0.0


GENERATORS = {
    "connect_pairs": gen_connect_pairs_subpuzzle,
    "pattern_break": gen_pattern_break_subpuzzle,
    "speed_math_chain": gen_speed_math_chain_subpuzzle,
    "shape_rotation": gen_shape_rotation_subpuzzle,
}

SUBPUZZLE_GRADERS = {
    "connect_pairs": grade_connect_pairs_subpuzzle,
    "pattern_break": grade_pattern_break_subpuzzle,
    "speed_math_chain": grade_speed_math_chain_subpuzzle,
    "shape_rotation": grade_shape_rotation_subpuzzle,
}


def generate_cognizant_games(seen_hashes_by_category: Dict[str, Set[str]]) -> List[Dict[str, Any]]:
    """Pick N_CATEGORIES_PER_SESSION distinct categories at random (mirrors
    Capgemini's partial-selection pattern). For each picked category,
    generate a set of N_SUBPUZZLES_PER_CHALLENGE sub-puzzles via
    _generate_subpuzzle_set. Returns items shaped exactly like Capgemini's
    rebuilt challenges: {id, type, sub_puzzles: [...], _secrets: [...],
    _content_hashes: [...]} — server.py stores each non-None secret via
    _store_hidden_answer_key and marks each hash seen via
    challenge_repetition.mark_seen, one call per sub-puzzle."""
    rng = random.Random()
    picked_categories = rng.sample(CATEGORIES, min(N_CATEGORIES_PER_SESSION, len(CATEGORIES)))
    out: List[Dict[str, Any]] = []
    for cat in picked_categories:
        seen = seen_hashes_by_category.get(cat, set())
        gen_one_fn = GENERATORS[cat]
        publics, secrets, hashes = _generate_subpuzzle_set(gen_one_fn, rng, seen)
        out.append({
            "id": _make_id(cat, rng),
            "type": cat,
            "sub_puzzles": publics,
            "_secrets": secrets,
            "_content_hashes": hashes,
        })
    for i, c in enumerate(out):
        c["id"] = f"q{i+1}"
    return out