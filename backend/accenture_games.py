"""Accenture's gamified round — a bespoke design, not drawn from real
Accenture OA content, built to the exact same engineering standard as
capgemini_challenges.py / cognizant_games.py's rebuilt cognitive challenges:
every category is a SET of procedurally-generated sub-puzzles, zero AI
involvement, and where a puzzle's correctness hinges on one secret fact, that
fact is NEVER included in the public payload — it's returned separately as
`secret` and stored server-side only (see server.py's _store_hidden_answer_key).

Only 3 categories (vs Capgemini's 6 / Cognizant's 4) — REPLACES Accenture's
previous "cognitive_game" section (a plain per-question-timer MCQ round,
shared machinery with IBM's "game" type) entirely. All 3 categories are
always generated every session (no N-of-M random selection — with exactly 3
types and a 3-item section, the pool equals the count, so there's nothing to
select from; variation instead comes from each generator's own procedural
randomness plus non-repetition tracking).

Secrecy per category:
  - number_sort: NO secret — correctness is a publicly-checkable constraint
    (the grader re-evaluates each item's own displayed expression and checks
    the submission's order against it), same reasoning as Capgemini's
    Deductive Challenge (sudoku rules).
  - path_finding, key_door_maze: hidden secret (stricter default) — each has
    exactly one correct fact that isn't a structurally-checkable constraint,
    same treatment as Capgemini's Grid/Digit Challenge.
"""
from __future__ import annotations
import hashlib
import json
import random
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

CATEGORIES = ["number_sort", "path_finding", "key_door_maze"]

CATEGORY_LABELS = {
    "number_sort": "Number Sorting",
    "path_finding": "Path-Finding",
    "key_door_maze": "Key-Door Maze",
}

CATEGORY_INSTRUCTIONS = {
    "number_sort": "Click the tiles in order from smallest value to largest.",
    "path_finding": "Starting at the marked cell, follow each arrow to the next cell until you exit the grid. Click where you exit.",
    "key_door_maze": "Click the one key that's both reachable from the start (no walls in the way) and matches the door's color.",
}

N_SUBPUZZLES_PER_CHALLENGE = 4

DIRS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
_KEY_COLORS = ["red", "blue", "green", "yellow", "purple"]


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
    """Same generic building block as capgemini_challenges.py /
    cognizant_games.py: gen_one_fn(rng) -> (public_dict, secret_or_None) for
    exactly one sub-puzzle. Generates n_subpuzzles distinct instances,
    retrying on a repetition collision (own history + this candidate's)."""
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


# ---- 1. number_sort: sort tiles by computed value --------------------------
# Each tile is a plain number or a short arithmetic expression in a strictly
# controlled format ("A + B" / "A - B" / "A × B" / a bare integer). Grading
# re-evaluates every displayed expression from the public data itself — no
# eval(), just a small deterministic parser matching the exact format this
# module itself generates — and checks the submitted order is truly
# ascending. Nothing is hidden: any candidate can already verify their own
# answer with pen and paper from what's shown.

def _make_expr(rng: random.Random) -> Tuple[str, int]:
    kind = rng.choice(["number", "add", "subtract", "multiply"])
    if kind == "number":
        v = rng.randint(1, 50)
        return str(v), v
    if kind == "add":
        a, b = rng.randint(1, 20), rng.randint(1, 20)
        return f"{a} + {b}", a + b
    if kind == "subtract":
        a = rng.randint(10, 30)
        b = rng.randint(1, a - 1)
        return f"{a} - {b}", a - b
    a, b = rng.randint(2, 9), rng.randint(2, 9)
    return f"{a} × {b}", a * b


def gen_number_sort_subpuzzle(rng: random.Random, n_items: int = 5) -> Tuple[Dict[str, Any], None]:
    items = []
    used_values: Set[int] = set()
    for i in range(n_items):
        for _ in range(30):
            display, value = _make_expr(rng)
            if value not in used_values:
                used_values.add(value)
                items.append({"id": f"n{i}", "display": display})
                break
        else:
            raise RuntimeError("number_sort: failed to generate a distinct-valued item after 30 attempts")
    public = {"items": items}
    return public, None


def _evaluate_display(display: str) -> int:
    display = display.strip()
    for op, fn in ((" + ", lambda a, b: a + b), (" - ", lambda a, b: a - b), (" × ", lambda a, b: a * b)):
        if op in display:
            a_str, b_str = display.split(op)
            return fn(int(a_str), int(b_str))
    return int(display)


def grade_number_sort_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"order": [item_id, ...]} — candidate's chosen ascending order."""
    if not isinstance(answer, dict):
        return 0.0
    order = answer.get("order")
    if not isinstance(order, list):
        return 0.0
    items_by_id = {it["id"]: it for it in public.get("items", [])}
    if len(order) != len(items_by_id) or set(order) != set(items_by_id.keys()):
        return 0.0
    try:
        values = [_evaluate_display(items_by_id[iid]["display"]) for iid in order]
    except Exception:
        return 0.0
    return 1.0 if values == sorted(values) else 0.0


# ---- 2. path_finding: trace the arrow path to its true exit ---------------
# A small grid has a deterministic arrow path starting at `start` — follow
# the arrow on each cell you land on to the next cell until stepping off the
# grid. The full grid is shown (arrows are meant to be traced by hand), but
# WHICH of 4 candidate exit points is the true one is hidden server-side
# (stricter default — one derivable fact, not a checkable constraint).

def gen_path_finding_subpuzzle(
    rng: random.Random, size: int = 4, min_hops: int = 3, max_hops: int = 6,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    for _ in range(50):
        start = (rng.randrange(size), rng.randrange(size))
        pos = start
        visited = {pos}
        path_dirs: Dict[Tuple[int, int], str] = {}
        target_hops = rng.randint(min_hops, max_hops)
        ok = True
        hops = 0
        for _ in range(target_hops):
            choices = list(DIRS.items())
            rng.shuffle(choices)
            moved = False
            for dname, (dr, dc) in choices:
                nr, nc = pos[0] + dr, pos[1] + dc
                if 0 <= nr < size and 0 <= nc < size and (nr, nc) not in visited:
                    path_dirs[pos] = dname
                    pos = (nr, nc)
                    visited.add(pos)
                    hops += 1
                    moved = True
                    break
            if not moved:
                ok = False
                break
        if not ok or hops < min_hops:
            continue

        exit_dirs = []
        for dname, (dr, dc) in DIRS.items():
            nr, nc = pos[0] + dr, pos[1] + dc
            if not (0 <= nr < size and 0 <= nc < size):
                exit_dirs.append(dname)
        if not exit_dirs:
            continue
        exit_dir = rng.choice(exit_dirs)
        path_dirs[pos] = exit_dir
        er, ec = pos[0] + DIRS[exit_dir][0], pos[1] + DIRS[exit_dir][1]
        correct_exit = (er, ec)

        all_edge_points: Set[Tuple[int, int]] = set()
        for r in range(size):
            for c in range(size):
                if r == 0:
                    all_edge_points.add((r - 1, c))
                if r == size - 1:
                    all_edge_points.add((r + 1, c))
                if c == 0:
                    all_edge_points.add((r, c - 1))
                if c == size - 1:
                    all_edge_points.add((r, c + 1))
        decoy_pool = [p for p in all_edge_points if p != correct_exit]
        if len(decoy_pool) < 3:
            continue
        decoys = rng.sample(decoy_pool, 3)

        options = [correct_exit] + decoys
        order = list(range(4))
        rng.shuffle(order)
        shuffled = [options[i] for i in order]
        correct_option_index = order.index(0)

        grid = []
        for r in range(size):
            row = []
            for c in range(size):
                if (r, c) in path_dirs:
                    row.append(path_dirs[(r, c)])
                else:
                    row.append(rng.choice(list(DIRS.keys())))
            grid.append(row)

        public = {
            "grid": grid,
            "start": {"row": start[0], "col": start[1]},
            "exit_options": [{"row": p[0], "col": p[1]} for p in shuffled],
        }
        secret = {"correct_option_index": correct_option_index}
        return public, secret
    raise RuntimeError("path_finding: failed to generate a valid path after 50 attempts")


def grade_path_finding_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"selected_index": int}."""
    if not isinstance(secret, dict) or not isinstance(answer, dict):
        return 0.0
    try:
        selected = int(answer.get("selected_index"))
    except (TypeError, ValueError):
        return 0.0
    return 1.0 if selected == secret.get("correct_option_index") else 0.0


# ---- 3. key_door_maze: find the one reachable, color-matching key ---------
# A small walled grid maze. Exactly one of 3 keys is BOTH reachable from
# `start` (verified via real BFS at generation time, not assumed) AND
# color-matches the door — constructed, not just checked, same "confirm
# solvability" discipline as cognizant_games.py's connect_pairs/shape_rotation.

def _bfs_reachable(start: Tuple[int, int], walls: Set[Tuple[int, int]], size: int) -> Set[Tuple[int, int]]:
    reachable = {start}
    q = deque([start])
    while q:
        r, c = q.popleft()
        for dr, dc in DIRS.values():
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size and (nr, nc) not in walls and (nr, nc) not in reachable:
                reachable.add((nr, nc))
                q.append((nr, nc))
    return reachable


def gen_key_door_subpuzzle(
    rng: random.Random, size: int = 5, wall_density: float = 0.25,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    for _ in range(50):
        cells = [(r, c) for r in range(size) for c in range(size)]
        start = rng.choice(cells)
        remaining = [c for c in cells if c != start]
        n_walls = int(size * size * wall_density)
        walls = set(rng.sample(remaining, min(n_walls, len(remaining))))

        reachable = _bfs_reachable(start, walls, size)
        reachable_non_start = [c for c in reachable if c != start]
        unreachable = [c for c in cells if c not in reachable and c not in walls]
        if len(reachable_non_start) < 2 or len(unreachable) < 1:
            continue

        rng.shuffle(reachable_non_start)
        door_pos = reachable_non_start[0]
        door_color = rng.choice(_KEY_COLORS)

        correct_pool = [c for c in reachable_non_start if c != door_pos]
        if not correct_pool:
            continue
        correct_key_pos = rng.choice(correct_pool)

        decoy_positions: List[Tuple[int, int]] = []
        pool_unreachable = list(unreachable)
        pool_reachable_wrong = [c for c in reachable_non_start if c not in (door_pos, correct_key_pos)]
        rng.shuffle(pool_unreachable)
        rng.shuffle(pool_reachable_wrong)
        for pool in (pool_unreachable, pool_reachable_wrong):
            while pool and len(decoy_positions) < 2:
                decoy_positions.append(pool.pop())
        if len(decoy_positions) < 2:
            continue

        decoy_colors = []
        for pos in decoy_positions:
            if pos in reachable:
                wrong = [c for c in _KEY_COLORS if c != door_color]
                decoy_colors.append(rng.choice(wrong))
            else:
                decoy_colors.append(rng.choice(_KEY_COLORS))

        keys = [{"id": "k0", "row": correct_key_pos[0], "col": correct_key_pos[1], "color": door_color}]
        for i, (pos, color) in enumerate(zip(decoy_positions, decoy_colors)):
            keys.append({"id": f"k{i+1}", "row": pos[0], "col": pos[1], "color": color})
        rng.shuffle(keys)

        # Construct-then-VERIFY: exactly one key must be reachable AND color-matching.
        valid_keys = [k for k in keys if (k["row"], k["col"]) in reachable and k["color"] == door_color]
        if len(valid_keys) != 1:
            continue
        correct_key_id = valid_keys[0]["id"]

        public = {
            "size": size,
            "start": {"row": start[0], "col": start[1]},
            "walls": [{"row": r, "col": c} for (r, c) in walls],
            "door": {"row": door_pos[0], "col": door_pos[1], "color": door_color},
            "keys": [{"id": k["id"], "row": k["row"], "col": k["col"], "color": k["color"]} for k in keys],
        }
        secret = {"correct_key_id": correct_key_id}
        return public, secret
    raise RuntimeError("key_door_maze: failed to generate a valid maze after 50 attempts")


def grade_key_door_subpuzzle(public: Dict[str, Any], secret: Any, answer: Any) -> float:
    """answer: {"selected_key_id": str}."""
    if not isinstance(secret, dict) or not isinstance(answer, dict):
        return 0.0
    selected = answer.get("selected_key_id")
    return 1.0 if selected == secret.get("correct_key_id") else 0.0


GENERATORS = {
    "number_sort": gen_number_sort_subpuzzle,
    "path_finding": gen_path_finding_subpuzzle,
    "key_door_maze": gen_key_door_subpuzzle,
}

SUBPUZZLE_GRADERS = {
    "number_sort": grade_number_sort_subpuzzle,
    "path_finding": grade_path_finding_subpuzzle,
    "key_door_maze": grade_key_door_subpuzzle,
}


def generate_accenture_games(seen_hashes_by_category: Dict[str, Set[str]]) -> List[Dict[str, Any]]:
    """Always generates all 3 categories (no N-of-M selection — the pool
    equals the count). For each, a set of N_SUBPUZZLES_PER_CHALLENGE
    sub-puzzles via _generate_subpuzzle_set. Returns items shaped exactly
    like Capgemini's/Cognizant's rebuilt challenges: {id, type,
    sub_puzzles: [...], _secrets: [...], _content_hashes: [...]} —
    server.py stores each non-None secret via _store_hidden_answer_key and
    marks each hash seen via challenge_repetition.mark_seen."""
    rng = random.Random()
    out: List[Dict[str, Any]] = []
    for cat in CATEGORIES:
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
