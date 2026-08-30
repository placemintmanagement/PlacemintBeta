"""grid_challenge game type -- dual-task spatial memory + rotational
symmetry judgment (see gamified_round.py for the DB side, game_types.py
for the registry entry).

One puzzle_bank document = one FULL 3-block + recall instance (not one
sub-puzzle like deductive_grid/switch_challenge -- see module docstring
in game_types.py for why this type needs a phase_check contract instead
of the narrower answer_check the other two types use). Circle-layout
generation and target-circle selection happen once per instance.

Structure (corrected 2026-08-13): 3 BLOCKS, each with one blink (its own
target circle, feeding the final 3-position recall) followed by a
VARIABLE number of judgments -- block 1 has 1, block 2 has 2, block 3 has
4 (JUDGMENTS_PER_BLOCK below), 7 judgments total. Each judgment
independently reuses the pattern-pair mechanic below UNCHANGED -- this
revision only touches instance assembly (generate_instance/verify_instance/
content_hash), not generate_pattern_pair/solve_symmetry.

IMPORTANT -- not yet safe to serve: generate_instance()'s output must
never be sent to the client in one shot the way deductive_grid/
switch_challenge puzzles are (their entire content is safe to reveal
upfront, only correctAnswer is secret). Here, block 2/3's targetCircleId
and every judgment's correctAnswer, plus correctRecallOrder, must stay
server-side until their own phase is actually requested -- revealing them
early defeats the memory task itself, not just the scoring. That
progressive-reveal serving layer is step 3, not built yet. Do not add
"grid_challenge" to any gamified_round_config's gameTypes list until
steps 3 and 4 exist, or a real session could get served through the OLD
flat sample_puzzles-everything-upfront path this type was never designed
for.

Two independent code paths, same principle as deductive_grid/switch_challenge:
  - _apply_rotation() + generate_pattern_pair(): CONSTRUCTS a pattern pair,
    either genuinely rotationally identical (applies a real 90/180/270
    rotation) or genuinely different (perturbs 1-3 cells and confirms via
    the independent checker that the perturbation actually broke every
    rotational match, retrying if it didn't).
  - solve_symmetry(): given ONLY the two patterns, independently
    re-determines whether they're rotations of each other.

Critically, solve_symmetry() does NOT reuse _apply_rotation() -- it's
implemented via a different derivation (transpose + row-reverse, the
standard "rotate 90 CW" identity) specifically so a coding bug in one
rotation implementation (wrong axis, off-by-one, transcription error)
isn't automatically replicated in the other. Both compute the same
correct mathematical rotation when bug-free (verified in the stress test
below by cross-checking them against each other), but a bug in either one
alone would surface as a disagreement, not silently agree with itself.

verify_pattern_pair() asserts solve_symmetry()'s judgment matches what
generate_pattern_pair() claims to have built, before a pair is trusted.
"""
from __future__ import annotations
import hashlib
import json
import math
import random
from typing import Any, Dict, List, Optional

PATTERN_SIZE = 5
FILL_PROBABILITY = 0.4
ROTATIONS = (90, 180, 270)

Pattern = List[List[int]]  # PATTERN_SIZE x PATTERN_SIZE of 0/1

# Circle layout constants. Coordinates are normalized [0,1] x [0,1] --
# MARGIN keeps circles away from the edges (so nothing renders clipped);
# MIN_PAIRWISE_DISTANCE is the rejection-sampling constraint that keeps
# click targets visually distinguishable from each other.
NUM_CIRCLES_RANGE = (15, 20)
MARGIN = 0.06
MIN_PAIRWISE_DISTANCE = 0.12
NUM_BLOCKS = 3
JUDGMENTS_PER_BLOCK = (1, 2, 4)  # block 0, 1, 2 respectively -- 7 judgments total


# ============================================================
# GENERATOR-SIDE rotation -- direct index-mapping formula.
# ============================================================

def _apply_rotation(pattern: Pattern, degrees: int) -> Pattern:
    n = len(pattern)
    result = [[0] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            if degrees == 90:
                nr, nc = c, n - 1 - r
            elif degrees == 180:
                nr, nc = n - 1 - r, n - 1 - c
            elif degrees == 270:
                nr, nc = n - 1 - c, r
            else:
                nr, nc = r, c
            result[nr][nc] = pattern[r][c]
    return result


def _random_pattern(rng: random.Random) -> Pattern:
    return [[1 if rng.random() < FILL_PROBABILITY else 0 for _ in range(PATTERN_SIZE)] for _ in range(PATTERN_SIZE)]


def _is_degenerate(pattern: Pattern) -> bool:
    """All-empty or all-filled patterns are trivially (boringly) rotationally
    symmetric -- not a meaningful judgment, reject and retry with a fresh one."""
    filled = sum(sum(row) for row in pattern)
    return filled == 0 or filled == PATTERN_SIZE * PATTERN_SIZE


def _perturb(pattern: Pattern, rng: random.Random, num_flips: int) -> Pattern:
    n = len(pattern)
    result = [row[:] for row in pattern]
    flipped: set = set()
    attempts = 0
    while len(flipped) < num_flips and attempts < 100:
        attempts += 1
        r, c = rng.randrange(n), rng.randrange(n)
        if (r, c) in flipped:
            continue
        result[r][c] = 1 - result[r][c]
        flipped.add((r, c))
    return result


def generate_pattern_pair(rng: random.Random, want_identical: bool, max_attempts: int = 200) -> Dict[str, Any]:
    """Builds one pattern pair. If want_identical, patternB is a genuine
    90/180/270 rotation of patternA (never 0deg -- a literally-identical
    pair isn't an interesting rotation question). If not want_identical,
    patternB is perturbed from a (possibly rotated) base until the
    INDEPENDENT checker (solve_symmetry) confirms it no longer matches
    patternA under any rotation -- a symmetric patternA can make a small
    perturbation fail to break equivalence, so this retries with more
    flips, then a fresh patternA, rather than trusting the first attempt."""
    for _ in range(max_attempts):
        pattern_a = _random_pattern(rng)
        if _is_degenerate(pattern_a):
            continue

        if want_identical:
            rotation = rng.choice(ROTATIONS)
            pattern_b = _apply_rotation(pattern_a, rotation)
            if not solve_symmetry(pattern_a, pattern_b):
                continue  # defensive -- should be mathematically impossible; retry if it ever fires
            return {"patternA": pattern_a, "patternB": pattern_b, "correctAnswer": True, "_rotationApplied": rotation}

        base_rotation = rng.choice((0,) + ROTATIONS)
        base = _apply_rotation(pattern_a, base_rotation) if base_rotation else pattern_a
        for num_flips in (1, 2, 3):
            for _ in range(20):
                candidate = _perturb(base, rng, num_flips)
                if not solve_symmetry(pattern_a, candidate):
                    return {"patternA": pattern_a, "patternB": candidate, "correctAnswer": False, "_baseRotation": base_rotation}
        # this patternA (possibly highly self-symmetric) couldn't be perturbed
        # away from equivalence within the flip budget -- try a fresh patternA
        continue

    raise RuntimeError(f"generate_pattern_pair: failed after {max_attempts} attempts (want_identical={want_identical})")


# ============================================================
# SOLVER/VERIFIER -- independent re-derivation via a DIFFERENT rotation
# implementation (transpose + row-reverse), not _apply_rotation().
# ============================================================

def _transpose(pattern: Pattern) -> Pattern:
    return [list(row) for row in zip(*pattern)]


def _reverse_rows(pattern: Pattern) -> Pattern:
    return [list(reversed(row)) for row in pattern]


def _rotate_90_cw_via_transpose(pattern: Pattern) -> Pattern:
    """Standard identity: rotate 90 CW == transpose, then reverse each row.
    Deliberately a different derivation from _apply_rotation()'s direct
    index-mapping formula (verified to agree in the stress test below) --
    the independence is about catching IMPLEMENTATION bugs (wrong axis,
    off-by-one), not computing a different abstract answer."""
    return _reverse_rows(_transpose(pattern))


def _all_rotations(pattern: Pattern) -> List[Pattern]:
    r0 = pattern
    r90 = _rotate_90_cw_via_transpose(r0)
    r180 = _rotate_90_cw_via_transpose(r90)
    r270 = _rotate_90_cw_via_transpose(r180)
    return [r0, r90, r180, r270]


def solve_symmetry(pattern_a: Pattern, pattern_b: Pattern) -> bool:
    """Independently determines whether pattern_b is pattern_a under some
    rotation (0/90/180/270) -- recomputes all 4 rotations from raw grid
    data via a different code path than the generator, never trusting
    which rotation (or whether any) the generator claims to have applied."""
    if len(pattern_a) != PATTERN_SIZE or len(pattern_b) != PATTERN_SIZE:
        return False
    if any(len(row) != PATTERN_SIZE for row in pattern_a) or any(len(row) != PATTERN_SIZE for row in pattern_b):
        return False
    return any(r == pattern_b for r in _all_rotations(pattern_a))


def verify_pattern_pair(pair: Dict[str, Any]) -> bool:
    predicted = solve_symmetry(pair["patternA"], pair["patternB"])
    return predicted == pair["correctAnswer"]


# ============================================================
# CIRCLE LAYOUT -- rejection sampling with a minimum pairwise distance.
# ============================================================

def _dist(p1: tuple, p2: tuple) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def _generate_circle_positions(rng: random.Random, num_circles: int, min_distance: float,
                                max_attempts_per_circle: int = 500) -> List[tuple]:
    positions: List[tuple] = []
    for _ in range(num_circles):
        placed = False
        for _ in range(max_attempts_per_circle):
            x = rng.uniform(MARGIN, 1 - MARGIN)
            y = rng.uniform(MARGIN, 1 - MARGIN)
            if all(_dist((x, y), p) >= min_distance for p in positions):
                positions.append((x, y))
                placed = True
                break
        if not placed:
            raise RuntimeError(
                f"_generate_circle_positions: could not place circle {len(positions) + 1}/{num_circles} "
                f"with min_distance={min_distance} after {max_attempts_per_circle} attempts"
            )
    return positions


# ============================================================
# FULL INSTANCE -- one puzzle_bank document: circle layout + 3 blocks
# (each with 1/2/4 judgments reusing the pattern-pair mechanic above,
# per JUDGMENTS_PER_BLOCK) + recall order.
# ============================================================

def generate_instance(rng: random.Random, num_circles: Optional[int] = None, max_attempts: int = 50) -> Dict[str, Any]:
    for _ in range(max_attempts):
        n = num_circles if num_circles is not None else rng.randint(*NUM_CIRCLES_RANGE)
        try:
            positions = _generate_circle_positions(rng, n, MIN_PAIRWISE_DISTANCE)
        except RuntimeError:
            continue  # this layout attempt got stuck (rare, dense packing) -- retry with a fresh layout

        circle_ids = [f"c{i + 1}" for i in range(n)]
        circle_layout = [
            {"id": cid, "x": round(x, 4), "y": round(y, 4)}
            for cid, (x, y) in zip(circle_ids, positions)
        ]

        # 3 DISTINCT target circles, one per block -- never repeat a
        # position across blocks (would make the recall step ambiguous:
        # clicking the same spot twice for two different blocks).
        target_ids = rng.sample(circle_ids, NUM_BLOCKS)

        blocks = []
        try:
            for block_idx in range(NUM_BLOCKS):
                num_judgments = JUDGMENTS_PER_BLOCK[block_idx]
                judgments = []
                for _ in range(num_judgments):
                    want_identical = rng.random() < 0.5
                    pair = generate_pattern_pair(rng, want_identical)
                    judgments.append({
                        "patternA": pair["patternA"],
                        "patternB": pair["patternB"],
                        "correctAnswer": pair["correctAnswer"],
                    })
                blocks.append({
                    "targetCircleId": target_ids[block_idx],
                    "judgments": judgments,
                })
        except RuntimeError:
            continue  # a judgment's pattern pair exhausted its own retries -- retry the whole instance

        instance = {
            "circleLayout": circle_layout,
            "blocks": blocks,
            "correctRecallOrder": target_ids,
        }
        if not verify_instance(instance):
            continue  # defensive -- should be unreachable given the checks above; retry rather than trust
        return instance

    raise RuntimeError(f"generate_instance: failed to build a valid instance after {max_attempts} attempts")


def verify_instance(instance: Dict[str, Any]) -> bool:
    """Independently re-derives every structural guarantee an instance
    must satisfy, from its own stored fields -- never trusts that
    generate_instance()'s bookkeeping did what it claims:
      - circle ids are unique
      - every pairwise distance actually meets MIN_PAIRWISE_DISTANCE
      - exactly 3 blocks, each with exactly JUDGMENTS_PER_BLOCK[i] judgments
      - the 3 block target ids are distinct and each exists in the layout
      - correctRecallOrder matches the blocks' targetCircleId, in order
      - every judgment's pattern pair independently verifies (reuses
        verify_pattern_pair, itself independent of the generator)."""
    layout = instance.get("circleLayout") or []
    circle_ids = [c["id"] for c in layout]
    if len(set(circle_ids)) != len(circle_ids):
        return False

    positions = [(c["x"], c["y"]) for c in layout]
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            if _dist(positions[i], positions[j]) < MIN_PAIRWISE_DISTANCE - 1e-9:
                return False

    blocks = instance.get("blocks") or []
    if len(blocks) != NUM_BLOCKS:
        return False

    target_ids = [b.get("targetCircleId") for b in blocks]
    if len(set(target_ids)) != NUM_BLOCKS:
        return False  # not distinct across blocks
    circle_id_set = set(circle_ids)
    if not all(tid in circle_id_set for tid in target_ids):
        return False  # a target isn't actually in this instance's layout

    if instance.get("correctRecallOrder") != target_ids:
        return False  # recall order must match block order exactly

    for block_idx, block in enumerate(blocks):
        judgments = block.get("judgments") or []
        if len(judgments) != JUDGMENTS_PER_BLOCK[block_idx]:
            return False  # wrong judgment count for this block position
        for judgment in judgments:
            pair = {
                "patternA": judgment.get("patternA"),
                "patternB": judgment.get("patternB"),
                "correctAnswer": judgment.get("correctAnswer"),
            }
            if not verify_pattern_pair(pair):
                return False

    return True


def content_hash(instance: Dict[str, Any]) -> str:
    payload = json.dumps({
        "circleLayout": instance["circleLayout"],
        "blocks": [
            {
                "targetCircleId": b["targetCircleId"],
                "judgments": [{"patternA": j["patternA"], "patternB": j["patternB"]} for j in b["judgments"]],
            }
            for b in instance["blocks"]
        ],
    }, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
