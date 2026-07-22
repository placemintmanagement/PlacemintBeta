"""Capgemini's real cognitive-round category names (Deductive/Inductive/
Grid/Switch/Motion/Digit Challenge), reimplemented as fully procedural
generators — ZERO AI involvement. A wrong answer key here directly harms a
real candidate's composite score, so every generator below produces
algorithmically-verifiable correctness, not an LLM guess.

These are ORIGINAL implementations built from the publicly-known category
NAMES only — no vendor item banks, question content, or proprietary
material was referenced or copied.

REBUILD COMPLETE (2026-07-19): all 6 categories are now genuine bespoke
interactive puzzles, each a SET of 4-5 sub-puzzles (shape: {id, type,
sub_puzzles: [...]}, rendered by dedicated frontend components) — not the
single-shot MCQ items (old shape: {id, style, prompt, options, correct_index,
explanation}, rendered via the shared CognitiveGameSection component) this
module started with. Built across three batches: Deductive + Grid Challenge
(batch 1), Switch + Motion Challenge (batch 2), Inductive + Digit Challenge
(batch 3).

_GENERATORS (old-shape) is now empty, but generate_capgemini_challenges()
and server.py's generation/grading code still handle both shapes — any OA
attempt generated before this deploy may have old-shape items already
persisted in its stored oa_attempts document, and those must keep rendering
and grading correctly if a candidate resumes or reviews one.

New-shape puzzle types follow a stricter answer-secrecy standard than the
old MCQ shape: where correctness hinges on one secret value (e.g. Grid
Challenge's correct number), that value is NEVER included in the public
sub-puzzle dict — it's returned separately as `secret` and stored
server-side only (see server.py's _store_hidden_answer_key), unlike the old
shape's correct_index which ships to the client openly. Where correctness is
a publicly-checkable constraint instead (Deductive Challenge's sudoku
rules), there's no secret to hide at all.
"""
from __future__ import annotations
import hashlib
import json
import random
from typing import Any, Dict, List, Optional, Set, Tuple

CATEGORIES = [
    "deductive_challenge",
    "inductive_challenge",
    "grid_challenge",
    "switch_challenge",
    "motion_challenge",
    "digit_challenge",
]

CATEGORY_LABELS = {
    "deductive_challenge": "Deductive Challenge",
    "inductive_challenge": "Inductive Challenge",
    "grid_challenge": "Grid Challenge",
    "switch_challenge": "Switch Challenge",
    "motion_challenge": "Motion Challenge",
    "digit_challenge": "Digit Challenge",
}


# ---- shared helpers ----------------------------------------------------------

def _make_id(category: str, rng: random.Random) -> str:
    return f"{category}_{rng.randrange(10**6):06d}"


def _numeric_options(correct: int, rng: random.Random, spread: int = 5) -> tuple:
    """Build 4 distinct int options containing `correct`, shuffled.
    Returns (options, correct_index)."""
    spread = max(2, spread)
    options: Set[int] = {correct}
    guard = 0
    while len(options) < 4 and guard < 50:
        guard += 1
        delta = rng.choice([-3, -2, -1, 1, 2, 3, spread, -spread])
        options.add(correct + delta)
    opts = list(options)
    rng.shuffle(opts)
    return opts, opts.index(correct)


def content_hash(challenge: Dict[str, Any]) -> str:
    canon = json.dumps(challenge, sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()[:16]


def _generate_subpuzzle_set(
    gen_one_fn,
    rng: random.Random,
    seen_hashes: Set[str],
    n_subpuzzles: int = 5,
    max_retries: int = 8,
) -> Tuple[List[Dict[str, Any]], List[Any], List[str]]:
    """Shared building block for every REBUILT (new-shape) challenge type.
    gen_one_fn(rng) -> (public_dict, secret_or_None) for exactly one
    sub-puzzle. Generates n_subpuzzles distinct instances — distinct both
    from what this candidate has seen before (seen_hashes, from
    challenge_repetition.py) AND from each other within this same set —
    retrying up to max_retries times per slot on a collision, which is
    always possible since generation is procedural, not LLM-sampled.

    Returns (list_of_public_dicts, list_of_secrets_aligned_by_index,
    list_of_content_hashes_aligned_by_index).
    """
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
            # Exhausted retries (should be exceedingly rare) — use the last
            # candidate anyway rather than serve fewer sub-puzzles than promised.
            chosen_public, chosen_secret = public, secret
        publics.append(chosen_public)
        secrets.append(chosen_secret)
        hashes.append(h)
    return publics, secrets, hashes


# ---- 1. Deductive Challenge: mini-sudoku ("Geo-Sudo") -----------------------
# 4x4 grid, 2x2 regions, 4 shape symbols — classic Latin-square sudoku rules.
# Correctness is a PUBLIC constraint (every row/column/region must contain
# all 4 symbols exactly once) — not a secret value — so there's nothing to
# hide server-side, unlike Grid Challenge below. Multiple valid completions
# of a given puzzle can exist; any of them is accepted, exactly like
# Cognizant's connect_pairs (verify the constraint on the SUBMITTED grid,
# never compare against one fixed stored answer).

_SUDOKU_BASE = [
    [0, 1, 2, 3],
    [2, 3, 0, 1],
    [1, 0, 3, 2],
    [3, 2, 1, 0],
]
_SUDOKU_SYMBOLS = ["circle", "square", "triangle", "star"]  # lucide-react icon names


def _random_complete_sudoku(rng: random.Random) -> List[List[int]]:
    """Apply validity-preserving symmetries (symbol relabeling, swapping
    rows/columns within a band, swapping whole bands, transposing) to the
    base grid. Each of these is a known symmetry of a Latin square with
    2x2 regions, so the result is ALWAYS a fully valid complete grid —
    no backtracking solver needed to generate one."""
    perm = list(range(4))
    rng.shuffle(perm)
    grid = [[perm[v] for v in row] for row in _SUDOKU_BASE]
    if rng.random() < 0.5:
        grid = [grid[2], grid[3], grid[0], grid[1]]  # swap row-bands
    if rng.random() < 0.5:
        grid = [[row[2], row[3], row[0], row[1]] for row in grid]  # swap col-bands
    if rng.random() < 0.5:
        grid[0], grid[1] = grid[1], grid[0]  # swap rows within top band
    if rng.random() < 0.5:
        grid[2], grid[3] = grid[3], grid[2]  # swap rows within bottom band
    if rng.random() < 0.5:
        for row in grid:
            row[0], row[1] = row[1], row[0]  # swap cols within left band
    if rng.random() < 0.5:
        for row in grid:
            row[2], row[3] = row[3], row[2]  # swap cols within right band
    if rng.random() < 0.5:
        grid = [[grid[c][r] for c in range(4)] for r in range(4)]  # transpose
    return grid


def gen_deductive_subpuzzle(rng: random.Random) -> Tuple[Dict[str, Any], None]:
    grid_idx = _random_complete_sudoku(rng)
    n_remove = rng.randint(6, 8)
    cells = [(r, c) for r in range(4) for c in range(4)]
    rng.shuffle(cells)
    remove_set = set(cells[:n_remove])
    display_grid = [
        [None if (r, c) in remove_set else _SUDOKU_SYMBOLS[grid_idx[r][c]] for c in range(4)]
        for r in range(4)
    ]
    public = {
        "size": 4,
        "region_size": 2,
        "symbols": _SUDOKU_SYMBOLS,
        "grid": display_grid,
    }
    return public, None


def _verify_sudoku(size: int, region_size: int, symbols: List[str], filled_grid: List[List[str]]) -> bool:
    expected = set(symbols)
    n = size
    for r in range(n):
        row = filled_grid[r]
        if not isinstance(row, list) or len(row) != n or set(row) != expected:
            return False
    for c in range(n):
        col = [filled_grid[r][c] for r in range(n)]
        if set(col) != expected:
            return False
    for br in range(0, n, region_size):
        for bc in range(0, n, region_size):
            block = [filled_grid[r][c] for r in range(br, br + region_size) for c in range(bc, bc + region_size)]
            if set(block) != expected:
                return False
    return True


def grade_deductive_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"grid": [[...]]} — the candidate's fully filled 4x4 grid.
    Binary 1.0/0.0: does it (a) leave every originally-given cell untouched
    and (b) satisfy row/column/region uniqueness. `secret` is unused (always
    None for this type) — kept in the signature for a uniform grader interface."""
    if not isinstance(answer, dict):
        return 0.0
    filled = answer.get("grid")
    if not isinstance(filled, list) or len(filled) != public["size"]:
        return 0.0
    original = public["grid"]
    try:
        for r in range(public["size"]):
            if not isinstance(filled[r], list) or len(filled[r]) != public["size"]:
                return 0.0
            for c in range(public["size"]):
                if original[r][c] is not None and filled[r][c] != original[r][c]:
                    return 0.0
    except (IndexError, TypeError):
        return 0.0
    return 1.0 if _verify_sudoku(public["size"], public["region_size"], public["symbols"], filled) else 0.0


# ---- 2. Inductive Challenge: typed inference, not multiple choice ----------
# Candidate sees 3 example (input -> output) pairs sharing a hidden rule,
# then types their predicted output for a new input into a number field —
# genuinely constructive, not a 4-option pick. The rule function and its
# computed correct_output are the secret: NEVER shipped to the frontend.

_INDUCTIVE_RULES = [
    ("doubles the number", lambda x: x * 2),
    ("adds 5", lambda x: x + 5),
    ("subtracts 3", lambda x: x - 3),
    ("squares the number", lambda x: x * x),
    ("multiplies by 3 then subtracts 1", lambda x: x * 3 - 1),
]


def gen_inductive_subpuzzle(rng: random.Random) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    _label, fn = rng.choice(_INDUCTIVE_RULES)
    inputs = rng.sample(range(2, 12), 3)
    examples = [{"input": i, "output": fn(i)} for i in inputs]
    new_input = rng.choice([x for x in range(2, 15) if x not in inputs])
    correct = fn(new_input)
    public = {"examples": examples, "new_input": new_input}
    secret = {"correct_output": correct}
    return public, secret


def grade_inductive_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"typed_value": <number the candidate typed>}."""
    if not isinstance(secret, dict) or not isinstance(answer, dict):
        return 0.0
    try:
        typed = int(answer.get("typed_value"))
    except (TypeError, ValueError):
        return 0.0
    return 1.0 if typed == secret.get("correct_output") else 0.0


# ---- 3. Grid Challenge: 3x3 spatial pattern, click-to-fill -----------------
# Unlike Deductive Challenge, correctness here IS one secret value (the
# arithmetic rule's result at the blank cell) — per the stricter standard,
# that value is NEVER shipped to the frontend, not even as a correct_index
# alongside the options. Only the grid, blank position, and the 4 (shuffled,
# unlabeled) candidate values are public; grading recomputes the correct
# value from `secret` server-side and compares it to whichever VALUE the
# candidate clicked (no index/ordering dependency at all).

def gen_grid_subpuzzle(rng: random.Random) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    base = rng.randint(1, 9)
    row_step = rng.randint(1, 4)
    col_step = rng.randint(1, 4)
    if row_step == col_step:
        col_step += 1
    full_grid = [[base + r * row_step + c * col_step for c in range(3)] for r in range(3)]
    blank_r, blank_c = rng.randrange(3), rng.randrange(3)
    correct = full_grid[blank_r][blank_c]
    display_grid = [
        [None if (r, c) == (blank_r, blank_c) else full_grid[r][c] for c in range(3)]
        for r in range(3)
    ]
    options, _ = _numeric_options(correct, rng, spread=row_step + col_step)
    public = {
        "grid": display_grid,
        "blank_position": [blank_r, blank_c],
        "options": options,  # shuffled; which one is correct is deliberately NOT included
    }
    secret = {"correct_value": correct}
    return public, secret


def grade_grid_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"selected_value": <number the candidate clicked>}."""
    if not isinstance(secret, dict) or not isinstance(answer, dict):
        return 0.0
    try:
        selected = int(answer.get("selected_value"))
    except (TypeError, ValueError):
        return 0.0
    return 1.0 if selected == secret.get("correct_value") else 0.0


# ---- 4. Switch Challenge: animated visual transformation -------------------
# An "object" is {shape, color, rotation, scale}. A transform rule maps one
# object to another via a single visual change (rotate/recolor/grow/shrink).
# The frontend renders an ANIMATED demo (Framer Motion) of the rule applied
# to example_before -> example_after, teaching the rule visually — that demo
# is intentionally public, same as a sudoku's given cells. Only WHICH of the
# 4 rendered option-tiles is the correct new_after stays hidden server-side
# (correct_index), per the stricter secrecy standard — unlike the old
# text-based version, which shipped correct_index openly.

_SWITCH_SHAPES = ["circle", "square", "triangle", "star"]
_SWITCH_COLORS = ["primary", "secondary", "dark"]
_SWITCH_ROTATIONS = [0, 90, 180, 270]
_SWITCH_SCALES = [0.7, 1.0, 1.5]

_SWITCH_RULES = {
    "rotate_cw": lambda o: {**o, "rotation": (o["rotation"] + 90) % 360},
    "rotate_180": lambda o: {**o, "rotation": (o["rotation"] + 180) % 360},
    "recolor": lambda o: {**o, "color": _SWITCH_COLORS[(_SWITCH_COLORS.index(o["color"]) + 1) % len(_SWITCH_COLORS)]},
    "grow": lambda o: {**o, "scale": 1.5} if o["scale"] != 1.5 else {**o, "scale": 1.0},
    "shrink": lambda o: {**o, "scale": 0.7} if o["scale"] != 0.7 else {**o, "scale": 1.0},
}


def _random_switch_object(rng: random.Random) -> Dict[str, Any]:
    return {
        "shape": rng.choice(_SWITCH_SHAPES),
        "color": rng.choice(_SWITCH_COLORS),
        "rotation": rng.choice(_SWITCH_ROTATIONS),
        "scale": 1.0,
    }


def _mutate_switch_object(obj: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    prop = rng.choice(["shape", "color", "rotation", "scale"])
    new_obj = dict(obj)
    if prop == "shape":
        new_obj["shape"] = rng.choice([s for s in _SWITCH_SHAPES if s != obj["shape"]])
    elif prop == "color":
        new_obj["color"] = rng.choice([c for c in _SWITCH_COLORS if c != obj["color"]])
    elif prop == "rotation":
        new_obj["rotation"] = rng.choice([r for r in _SWITCH_ROTATIONS if r != obj["rotation"]])
    else:
        new_obj["scale"] = rng.choice([s for s in _SWITCH_SCALES if s != obj["scale"]])
    return new_obj


def gen_switch_subpuzzle(rng: random.Random) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    rule_name = rng.choice(list(_SWITCH_RULES.keys()))
    rule_fn = _SWITCH_RULES[rule_name]

    example_before = _random_switch_object(rng)
    example_after = rule_fn(example_before)

    new_before = _random_switch_object(rng)
    guard = 0
    while new_before == example_before and guard < 20:
        new_before = _random_switch_object(rng)
        guard += 1
    correct_after = rule_fn(new_before)

    options = [correct_after]
    guard = 0
    while len(options) < 4 and guard < 50:
        guard += 1
        cand = _mutate_switch_object(correct_after, rng)
        if cand not in options:
            options.append(cand)
    rng.shuffle(options)
    correct_index = options.index(correct_after)

    public = {
        "rule_name": rule_name,  # descriptive only — the demo teaches the rule on purpose
        "example_before": example_before,
        "example_after": example_after,
        "new_before": new_before,
        "options": options,
    }
    secret = {"correct_index": correct_index}
    return public, secret


def grade_switch_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"selected_index": <index into public["options"]>}."""
    if not isinstance(secret, dict) or not isinstance(answer, dict):
        return 0.0
    try:
        selected = int(answer.get("selected_index"))
    except (TypeError, ValueError):
        return 0.0
    return 1.0 if selected == secret.get("correct_index") else 0.0


# ---- 5. Motion Challenge: animated rotation-sequence prediction ------------
# An arrow rotates a fixed 90° step each frame, clockwise or counter-
# clockwise. Three frames are shown as an animated sequence (frontend
# auto-plays them); the candidate predicts the 4th frame from 4 rendered
# arrow-tile options. Reuses the exact rotation-cycle math the old
# text-based version used — only the presentation and secrecy changed.

_MOTION_ROTATIONS = [0, 90, 180, 270]


def gen_motion_subpuzzle(rng: random.Random) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    start = rng.choice(_MOTION_ROTATIONS)
    clockwise = rng.random() < 0.5
    step = 90 if clockwise else -90
    sequence = [(start + step * i) % 360 for i in range(4)]
    shown = sequence[:3]
    correct = sequence[3]

    options = list(_MOTION_ROTATIONS)  # exactly the 4 possible rotations
    rng.shuffle(options)
    correct_index = options.index(correct)

    public = {"frames": shown, "options": options}
    secret = {"correct_index": correct_index}
    return public, secret


def grade_motion_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"selected_index": <index into public["options"]>}."""
    if not isinstance(secret, dict) or not isinstance(answer, dict):
        return 0.0
    try:
        selected = int(answer.get("selected_index"))
    except (TypeError, ValueError):
        return 0.0
    return 1.0 if selected == secret.get("correct_index") else 0.0


# ---- 6. Digit Challenge: typed input OR click-to-place tile arrangement ---
# Mixes two variants across a challenge's 5 sub-puzzles for genuine variety.
# "type_in": type the single missing next value into a number field.
# "arrange_tiles": 3 positions are blanked (with 2 leading anchors still
# shown so the rule is inferable), and the candidate places the 3 correct-
# value tiles into the right slots by clicking a tile then clicking a slot
# (same click-to-place interaction as Grid/Deductive Challenge, not drag).
# Both variants hide the actual correct value(s) server-side.

def _gen_digit_sequence(rng: random.Random) -> List[int]:
    kind = rng.choice(["arithmetic", "geometric", "fibonacci_like"])
    if kind == "arithmetic":
        a = rng.randint(1, 20)
        d = rng.choice([2, 3, 4, 5, -2, -3])
        return [a + d * i for i in range(5)]
    if kind == "geometric":
        a = rng.randint(1, 5)
        r = rng.choice([2, 3])
        return [a * (r ** i) for i in range(5)]
    a, b = rng.randint(1, 5), rng.randint(1, 5)
    seq = [a, b]
    for _ in range(3):
        seq.append(seq[-1] + seq[-2])
    return seq


def _gen_digit_type_in(rng: random.Random) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    seq = _gen_digit_sequence(rng)
    public = {"variant": "type_in", "sequence": seq[:4]}
    secret = {"correct_value": seq[4]}
    return public, secret


def _gen_digit_arrange(rng: random.Random) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    seq = _gen_digit_sequence(rng)
    blank_positions = [2, 3, 4]  # positions 0,1 stay as visible anchors
    correct_values = [seq[i] for i in blank_positions]
    tiles = list(correct_values)
    rng.shuffle(tiles)
    display_sequence = [seq[0], seq[1], None, None, None]
    public = {
        "variant": "arrange_tiles",
        "sequence": display_sequence,
        "blank_positions": blank_positions,
        "tiles": tiles,
    }
    secret = {"correct_values": correct_values}  # secret[i] <-> blank_positions[i]
    return public, secret


def gen_digit_subpuzzle(rng: random.Random) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if rng.random() < 0.5:
        return _gen_digit_type_in(rng)
    return _gen_digit_arrange(rng)


def _grade_digit_type_in(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    if not isinstance(secret, dict) or not isinstance(answer, dict):
        return 0.0
    try:
        typed = int(answer.get("typed_value"))
    except (TypeError, ValueError):
        return 0.0
    return 1.0 if typed == secret.get("correct_value") else 0.0


def _grade_digit_arrange(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"placed": {str(position): value, ...}} keyed by the actual
    sequence position (not tile index), matching how the frontend tracks
    which slot each clicked tile landed in."""
    if not isinstance(secret, dict) or not isinstance(answer, dict):
        return 0.0
    placed = answer.get("placed")
    if not isinstance(placed, dict):
        return 0.0
    correct_values = secret.get("correct_values", [])
    blank_positions = public.get("blank_positions", [])
    for pos, correct_val in zip(blank_positions, correct_values):
        try:
            candidate_val = int(placed.get(str(pos)))
        except (TypeError, ValueError):
            return 0.0
        if candidate_val != correct_val:
            return 0.0
    return 1.0


def grade_digit_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    variant = public.get("variant")
    if variant == "type_in":
        return _grade_digit_type_in(public, secret, answer)
    if variant == "arrange_tiles":
        return _grade_digit_arrange(public, secret, answer)
    return 0.0


# Old-shape (single MCQ item, correct_index shipped openly) — none remain
# pending a batch as of 2026-07-19 (all 6 rebuilt), but this dict/branch
# stays for backward compatibility: any OA attempt generated BEFORE this
# deploy may still have old-shape items persisted in its stored
# oa_attempts.sections.questions, and those must keep rendering/grading
# correctly if a candidate resumes or reviews one.
_GENERATORS: Dict[str, Any] = {}  # empty: all 6 categories rebuilt as of 2026-07-19

# New-shape (sub-puzzle set, secret hidden server-side where one exists).
_REBUILT_GENERATORS = {
    "deductive_challenge": gen_deductive_subpuzzle,
    "grid_challenge": gen_grid_subpuzzle,
    "switch_challenge": gen_switch_subpuzzle,
    "motion_challenge": gen_motion_subpuzzle,
    "inductive_challenge": gen_inductive_subpuzzle,
    "digit_challenge": gen_digit_subpuzzle,
}

SUBPUZZLE_GRADERS = {
    "deductive_challenge": grade_deductive_subpuzzle,
    "grid_challenge": grade_grid_subpuzzle,
    "switch_challenge": grade_switch_subpuzzle,
    "motion_challenge": grade_motion_subpuzzle,
    "inductive_challenge": grade_inductive_subpuzzle,
    "digit_challenge": grade_digit_subpuzzle,
}

N_SUBPUZZLES_PER_CHALLENGE = 5


def generate_capgemini_challenges(
    count: int,
    seen_hashes_by_category: Dict[str, Set[str]],
) -> List[Dict[str, Any]]:
    """Pick `count` DISTINCT categories at random (Capgemini's real 4-of-N
    selection pattern, here 4-of-6). For each picked category, generate
    either:
      - a REBUILT challenge: {id, type, sub_puzzles: [...], _secrets: [...],
        _content_hashes: [...]} — server.py stores each non-None secret via
        _store_hidden_answer_key and marks each hash seen via
        challenge_repetition.mark_seen, one call per sub-puzzle.
      - an old-shape challenge: {id, style, prompt, options, correct_index,
        explanation, _content_hash} — unchanged from before, one hash to mark.

    Both shapes coexist in the returned list during the rebuild — server.py's
    generation and grading code branches on `"sub_puzzles" in item`.
    """
    rng = random.Random()
    picked_categories = rng.sample(CATEGORIES, min(count, len(CATEGORIES)))
    out: List[Dict[str, Any]] = []
    for cat in picked_categories:
        seen = seen_hashes_by_category.get(cat, set())
        if cat in _REBUILT_GENERATORS:
            gen_one_fn = _REBUILT_GENERATORS[cat]
            publics, secrets, hashes = _generate_subpuzzle_set(gen_one_fn, rng, seen, N_SUBPUZZLES_PER_CHALLENGE)
            out.append({
                "id": _make_id(cat, rng),
                "type": cat,
                "sub_puzzles": publics,
                "_secrets": secrets,
                "_content_hashes": hashes,
            })
        else:
            gen_fn = _GENERATORS[cat]
            challenge = None
            h = ""
            for _ in range(8):
                candidate = gen_fn(rng)
                # Hash only the meaningful content, NOT the whole dict — it
                # also carries a freshly-random `id` (from _make_id) that
                # would make every hash unique and silently defeat
                # repetition detection entirely.
                h = content_hash({"prompt": candidate["prompt"], "options": candidate["options"]})
                if h not in seen:
                    challenge = candidate
                    break
            if challenge is None:
                challenge = candidate
            challenge["_content_hash"] = h
            out.append(challenge)
    for i, c in enumerate(out):
        c["id"] = f"q{i+1}"
    return out
