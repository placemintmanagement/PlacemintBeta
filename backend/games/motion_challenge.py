"""motion_challenge game type -- an interactive sliding-block pathing
puzzle. A grid holds colored rectangular blocks (1x2 horizontal, 2x1
vertical, 2x2 square), permanently-blocked (wall) cells, one red ball, and
one black hole (target). Each move shifts ONE block or the ball by exactly
one cell into an adjacent, currently-unoccupied cell (blocks can move onto
the hole cell; nothing may move onto the ball). Goal: get the ball onto the
hole within the level's move budget.

Unlike the first 4 game types (generate content, then verify it's valid
after the fact), this type's generator must GUARANTEE solvability up
front, because "is this level solvable in N moves" isn't checkable by
re-deriving a stored answer -- it requires an actual state-space search.

Two independent code paths, same discipline as every other type here:
  - generate_level() (generator side): builds a SOLVED board (ball already
    on the hole), then scrambles it by taking random LEGAL moves from that
    solved state. This guarantees solvability by construction -- the
    scramble sequence, reversed, is itself a valid solution -- without
    ever needing to reject an unsolvable layout.
  - bfs_min_moves() (verifier side): a breadth-first search over board
    configurations, run FRESH from the scrambled starting position, with
    NO knowledge of how that position was produced. This is what actually
    computes the true minimum move count (a scramble can accidentally
    create a shortcut shorter than the scramble itself) and is what makes
    the "independent verification" guarantee real: the search never reads
    the generator's scramble history, so a generator bug can't silently
    agree with itself the way it could if verification just replayed the
    known-reverse solution.

verify_level() re-derives minMoves via a FRESH bfs_min_moves() call on the
instance's own stored board/startPositions and checks it matches what
generate_level() claims, before a level is allowed into puzzle_bank (a
later step) -- same verify-before-accept discipline as every prior type.

DIFFICULTY FLOOR (confirmed 2026-08-14, after board-size and wall-density
experiments both failed to move true minMoves in the desired direction on
the 4x6/baseline-wall config): generate_instance() bakes in an acceptance
filter, MIN_MOVES_THRESHOLD, rejecting and regenerating any candidate
below it -- measured yield ~27.8% at threshold=3 on the baseline config
(roughly 3.6x raw generate_level() calls per accepted instance). This
filtering lives in the generator wrapper itself, not pushed onto callers
(batch scripts, the registry) to reimplement.

Registry contract (Step 2): unlike the first 4 types, this one doesn't fit
answer_check (no single stored answer) or phase_check (nothing is secret
-- the whole board is visible from move one; what's needed is incremental
STATE-MUTATION validation, not progressive reveal). Two new functions
instead:
  - move_check(instance, move_history, block_id, direction) -> validates
    ONE next move against the board state replayed fresh from the
    instance's own stored board/startPositions plus the move history so
    far -- never trusts a client-claimed "current board."
  - grade_interactive(instance, move_history) -> re-derives final
    won/lost from the full stored move history, independent of whatever
    a live move_check call may have returned along the way (same
    never-trust-a-running-tally discipline as grade_grid_challenge_session
    re-deriving from live_checks instead of summing cached points).
Both operate on move_history entries shaped {"blockId": str | None,
"direction": "up"|"down"|"left"|"right"} (blockId=None means "move the
ball"). History entries are trusted to have already been validated at
write time (by a prior successful move_check call) -- replay applies them
directly rather than re-validating each one's legality a second time,
matching how grade_grid_challenge_session trusts each historical
live_checks entry's own validation rather than re-checking it.

STATUS: generator (with the minMoves filter baked in) + independent BFS
verifier + move_check/grade_interactive wired into game_types.py (Step 2),
plus instance_to_doc()/doc_to_instance() (the puzzle_bank Mongo doc shape
and its inverse) and the /motion-challenge/move + /undo HTTP endpoints in
server.py/gamified_round.py (Step 3). No frontend yet, and
"motion_challenge" is not yet added to any gamified_round_config's
gameTypes list -- both are later, unapproved steps.
"""
from __future__ import annotations
import hashlib
import json
import random
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

Cell = Tuple[int, int]

ROWS = 4
COLS = 6

# Confirmed examples only (blue 2x2, yellow/green strips) -- v1 scope.
# (width, height). The movement/occupancy code below is fully generic over
# arbitrary rectangles, so supporting longer strips (1x3 etc.) later is a
# content-only change, not an algorithm change.
BLOCK_SHAPES = [(2, 1), (1, 2), (2, 2)]

SLACK = 1  # moveBudget = minMoves + SLACK, tightened from +2 (2026-08-14) after
# the difficulty investigation (board-size and wall-density experiments)
# found neither lever moved true minMoves in the desired direction on the
# 4x6/baseline-wall config -- kept as a named, tunable constant rather than
# hardcoded, same as every other tunable in this suite.

MIN_MOVES_THRESHOLD = 3  # generate_instance() rejects/regenerates anything
# below this -- confirmed 2026-08-14 after the unfiltered baseline showed
# ~44-48% of instances landing at the trivial minMoves=1 case regardless of
# board size or wall density. Measured yield ~27.8% at this threshold on
# the baseline config (~3.6x raw attempts per accepted instance).

DEFAULT_NUM_BLOCKS = 5  # confirmed final baseline config (with 3 walls, 4x6 board)

DIRECTION_DELTA: Dict[str, Tuple[int, int]] = {
    "up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1),
}
_REVERSE = {"up": "down", "down": "up", "left": "right", "right": "left"}


def _allowed_directions(shape: Tuple[int, int]) -> List[str]:
    """Strips (width != height, one dim == 1) move along their long axis
    only, matching Rush-Hour-style convention. The 2x2 square has no long
    axis, so -- per the confirmed judgment call -- it moves on BOTH axes,
    one cell at a time. A hypothetical 1x1 also gets all 4 (unused by any
    v1 block shape, but the ball reuses this same convention implicitly).
    """
    w, h = shape
    dirs: List[str] = []
    if w > 1 or w == h:
        dirs += ["left", "right"]
    if h > 1 or w == h:
        dirs += ["up", "down"]
    return dirs


def _cells_for(anchor: Cell, shape: Tuple[int, int]) -> Set[Cell]:
    r, c = anchor
    w, h = shape
    return {(r + dr, c + dc) for dr in range(h) for dc in range(w)}


def _in_bounds(cells: Set[Cell], rows: int, cols: int) -> bool:
    return all(0 <= r < rows and 0 <= c < cols for r, c in cells)


# ---------------------------------------------------------------------------
# Board generation (solved state + placement)
# ---------------------------------------------------------------------------

def generate_solved_board(
    rng: random.Random, rows: int = ROWS, cols: int = COLS,
    num_blocks: int = 4, num_walls: int = 3, max_attempts: int = 200,
    shape_pool: Optional[List[Tuple[int, int]]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Returns (board_static, positions) where the ball already sits on the
    hole (a SOLVED state) -- board_static holds everything that never
    changes during play (rows/cols/walls/hole/blockShapes), positions holds
    everything that does (ballPos/blockPositions).
    """
    shapes = shape_pool if shape_pool is not None else BLOCK_SHAPES
    for _ in range(max_attempts):
        all_cells = [(r, c) for r in range(rows) for c in range(cols)]
        rng.shuffle(all_cells)
        occupied: Set[Cell] = set()
        walls: Set[Cell] = set()

        for _ in range(num_walls):
            if not all_cells:
                break
            cell = all_cells.pop()
            walls.add(cell)
            occupied.add(cell)

        hole: Optional[Cell] = None
        for cell in list(all_cells):
            if cell not in occupied:
                hole = cell
                all_cells.remove(cell)
                occupied.add(cell)
                break
        if hole is None:
            continue

        block_shapes: Dict[str, Tuple[int, int]] = {}
        block_positions: Dict[str, Cell] = {}
        placement_ok = True
        for i in range(num_blocks):
            shape = rng.choice(shapes)
            candidates = [(r, c) for r in range(rows) for c in range(cols)]
            rng.shuffle(candidates)
            placed = False
            for anchor in candidates:
                cells = _cells_for(anchor, shape)
                if _in_bounds(cells, rows, cols) and not (cells & occupied):
                    bid = f"b{i + 1}"
                    block_shapes[bid] = shape
                    block_positions[bid] = anchor
                    occupied |= cells
                    placed = True
                    break
            if not placed:
                placement_ok = False
                break
        if not placement_ok:
            continue

        board = {"rows": rows, "cols": cols, "walls": walls, "hole": hole, "blockShapes": block_shapes}
        positions = {"ballPos": hole, "blockPositions": block_positions}
        return board, positions

    raise RuntimeError("generate_solved_board: exceeded max_attempts")


# ---------------------------------------------------------------------------
# Move legality (shared by scrambling, BFS, and -- eventually -- the live
# per-move endpoint's move_check)
# ---------------------------------------------------------------------------

def _all_block_cells(board: Dict[str, Any], positions: Dict[str, Any], exclude: Optional[str] = None) -> Set[Cell]:
    cells: Set[Cell] = set()
    for bid, anchor in positions["blockPositions"].items():
        if bid == exclude:
            continue
        cells |= _cells_for(anchor, board["blockShapes"][bid])
    return cells


def legal_block_move(board: Dict[str, Any], positions: Dict[str, Any], block_id: str, direction: str) -> Optional[Cell]:
    """Returns the block's new anchor if the move is legal, else None."""
    shape = board["blockShapes"][block_id]
    if direction not in _allowed_directions(shape):
        return None
    anchor = positions["blockPositions"][block_id]
    dr, dc = DIRECTION_DELTA[direction]
    new_anchor = (anchor[0] + dr, anchor[1] + dc)
    new_cells = _cells_for(new_anchor, shape)
    if not _in_bounds(new_cells, board["rows"], board["cols"]):
        return None
    if new_cells & board["walls"]:
        return None
    if positions["ballPos"] in new_cells:
        return None  # never move onto the ball
    if new_cells & _all_block_cells(board, positions, exclude=block_id):
        return None
    return new_anchor  # moving onto the hole cell is explicitly allowed


def legal_ball_move(board: Dict[str, Any], positions: Dict[str, Any], direction: str) -> Optional[Cell]:
    dr, dc = DIRECTION_DELTA[direction]
    ball = positions["ballPos"]
    new_pos = (ball[0] + dr, ball[1] + dc)
    if not (0 <= new_pos[0] < board["rows"] and 0 <= new_pos[1] < board["cols"]):
        return None
    if new_pos in board["walls"]:
        return None
    if new_pos in _all_block_cells(board, positions):
        return None
    return new_pos  # landing on the hole is the win condition, checked by the caller


Move = Tuple[str, Optional[str], str]  # ("block", block_id, direction) | ("ball", None, direction)


def list_legal_moves(board: Dict[str, Any], positions: Dict[str, Any]) -> List[Move]:
    moves: List[Move] = []
    for bid in board["blockShapes"]:
        for d in _allowed_directions(board["blockShapes"][bid]):
            if legal_block_move(board, positions, bid, d) is not None:
                moves.append(("block", bid, d))
    for d in DIRECTION_DELTA:
        if legal_ball_move(board, positions, d) is not None:
            moves.append(("ball", None, d))
    return moves


def apply_move(board: Dict[str, Any], positions: Dict[str, Any], move: Move) -> Dict[str, Any]:
    kind, bid, direction = move
    new_positions = {"ballPos": positions["ballPos"], "blockPositions": dict(positions["blockPositions"])}
    if kind == "block":
        new_anchor = legal_block_move(board, positions, bid, direction)
        if new_anchor is None:
            raise ValueError(f"apply_move: illegal move {move}")
        new_positions["blockPositions"][bid] = new_anchor
    else:
        new_pos = legal_ball_move(board, positions, direction)
        if new_pos is None:
            raise ValueError(f"apply_move: illegal move {move}")
        new_positions["ballPos"] = new_pos
    return new_positions


def _state_key(positions: Dict[str, Any]) -> Tuple[Any, ...]:
    return (positions["ballPos"], tuple(sorted(positions["blockPositions"].items())))


# ---------------------------------------------------------------------------
# Scrambling (generator side -- guarantees solvability by construction)
# ---------------------------------------------------------------------------

def scramble(rng: random.Random, board: Dict[str, Any], start_positions: Dict[str, Any], steps: int) -> Tuple[Dict[str, Any], List[Move]]:
    """Random walk of `steps` LEGAL moves from a solved state. Avoids
    immediately reversing the previous move (pure scramble-quality
    heuristic -- makes the scramble less likely to collapse into a
    trivially-short true solution -- falls back to allowing a repeat if
    it's genuinely the only legal move available, never gets stuck).
    """
    positions = {"ballPos": start_positions["ballPos"], "blockPositions": dict(start_positions["blockPositions"])}
    last_move: Optional[Move] = None
    taken: List[Move] = []

    for _ in range(steps):
        moves = list_legal_moves(board, positions)
        if not moves:
            break
        if last_move is not None:
            reverse = (last_move[0], last_move[1], _REVERSE[last_move[2]])
            filtered = [m for m in moves if m != reverse]
            moves = filtered or moves
        move = rng.choice(moves)
        positions = apply_move(board, positions, move)
        taken.append(move)
        last_move = move

    return positions, taken


# ---------------------------------------------------------------------------
# Verifier side -- independent forward BFS, no knowledge of scramble history
# ---------------------------------------------------------------------------

def bfs_min_moves(
    board: Dict[str, Any], start_positions: Dict[str, Any],
    max_states: int = 200_000, max_depth: int = 60,
) -> Tuple[Optional[int], int]:
    """Returns (min_moves, states_explored). min_moves is None if the
    search budget was exhausted before finding a solution (treated as
    "inconclusive, reject and retry" by the caller -- never treated as
    "confirmed unsolvable" past the budget) or if the state space was
    fully exhausted with no path to the hole (genuinely unsolvable,
    shouldn't occur for backward-generated levels but must be handled
    correctly regardless, since this function has no idea how the start
    state was produced).
    """
    if start_positions["ballPos"] == board["hole"]:
        return 0, 1

    start_key = _state_key(start_positions)
    visited = {start_key}
    queue = deque([(start_positions, 0)])
    states_explored = 0

    while queue:
        positions, depth = queue.popleft()
        states_explored += 1
        if states_explored > max_states or depth >= max_depth:
            return None, states_explored

        for move in list_legal_moves(board, positions):
            new_positions = apply_move(board, positions, move)
            if new_positions["ballPos"] == board["hole"]:
                return depth + 1, states_explored + 1
            key = _state_key(new_positions)
            if key not in visited:
                visited.add(key)
                queue.append((new_positions, depth + 1))

    return None, states_explored  # exhausted -- genuinely unsolvable


# ---------------------------------------------------------------------------
# Full level generation + independent verification
# ---------------------------------------------------------------------------

def generate_level(
    rng: random.Random,
    rows: int = ROWS, cols: int = COLS,
    num_blocks: int = 4, num_walls: int = 3,
    scramble_min: int = 8, scramble_max: int = 16,
    slack: int = SLACK, max_attempts: int = 100,
    max_bfs_states: int = 200_000,
    shape_pool: Optional[List[Tuple[int, int]]] = None,
) -> Dict[str, Any]:
    for _ in range(max_attempts):
        board, solved_positions = generate_solved_board(
            rng, rows=rows, cols=cols, num_blocks=num_blocks, num_walls=num_walls, shape_pool=shape_pool,
        )
        steps = rng.randint(scramble_min, scramble_max)
        scrambled_positions, taken = scramble(rng, board, solved_positions, steps)

        if scrambled_positions["ballPos"] == board["hole"]:
            continue  # scramble never displaced the ball -- degenerate, retry

        min_moves, states_explored = bfs_min_moves(board, scrambled_positions, max_states=max_bfs_states)
        if min_moves is None or min_moves == 0:
            continue  # search budget exceeded, or degenerate -- retry

        return {
            "board": board,
            "startPositions": scrambled_positions,
            "moveBudget": min_moves + slack,
            "minMoves": min_moves,
            "_statesExplored": states_explored,   # generation-time diagnostics only,
            "_scrambleStepsUsed": len(taken),      # not part of any future puzzle_bank doc
        }

    raise RuntimeError("generate_level: exceeded max_attempts")


def verify_level(instance: Dict[str, Any]) -> bool:
    """Re-derives minMoves via a FRESH bfs_min_moves() call -- never trusts
    generate_level()'s own stored minMoves/moveBudget."""
    board = instance["board"]
    positions = instance["startPositions"]

    if positions["ballPos"] == board["hole"]:
        return False  # degenerate: already solved

    min_moves, _ = bfs_min_moves(board, positions)
    if min_moves is None or min_moves == 0:
        return False
    if min_moves != instance.get("minMoves"):
        return False
    if instance.get("moveBudget") != min_moves + SLACK:
        return False
    return True


# ---------------------------------------------------------------------------
# Step 2 -- generator wrapper (with the confirmed minMoves filter baked in),
# independent verifier, content hash, and the move_check/grade_interactive
# registry contract.
# ---------------------------------------------------------------------------

def generate_instance(
    rng: random.Random,
    rows: int = ROWS, cols: int = COLS,
    num_blocks: int = DEFAULT_NUM_BLOCKS, num_walls: int = 3,
    scramble_min: int = 8, scramble_max: int = 16,
    slack: int = SLACK, min_moves_threshold: int = MIN_MOVES_THRESHOLD,
    max_attempts: int = 200, max_bfs_states: int = 200_000,
    shape_pool: Optional[List[Tuple[int, int]]] = None,
) -> Dict[str, Any]:
    """generate_level() plus the confirmed minMoves>=MIN_MOVES_THRESHOLD
    acceptance filter, baked into generation itself so callers (batch
    scripts, the registry) never see a sub-threshold instance and never
    need to reimplement the filter. Internally retries -- measured yield
    ~27.8% at the default threshold on the baseline config, so
    max_attempts=200 carries generous margin over the ~3.6x-raw-attempts-
    per-accepted expectation.
    """
    for _ in range(max_attempts):
        try:
            instance = generate_level(
                rng, rows=rows, cols=cols, num_blocks=num_blocks, num_walls=num_walls,
                scramble_min=scramble_min, scramble_max=scramble_max, slack=slack,
                max_bfs_states=max_bfs_states, shape_pool=shape_pool,
            )
        except RuntimeError:
            continue  # generate_level's own internal retries were exhausted -- try a fresh attempt
        if instance["minMoves"] < min_moves_threshold:
            continue  # below the confirmed difficulty floor -- discard, regenerate
        return instance

    raise RuntimeError("generate_instance: exceeded max_attempts trying to clear the minMoves threshold")


def verify_instance(instance: Dict[str, Any], min_moves_threshold: int = MIN_MOVES_THRESHOLD) -> bool:
    """verify_level() plus an independent re-check that the instance
    actually clears the minMoves acceptance filter -- re-checked here too
    rather than just trusting generate_instance()'s own filtering, same
    never-trust-the-generator discipline as every other check in this
    module."""
    if not verify_level(instance):
        return False
    return instance.get("minMoves", 0) >= min_moves_threshold


def content_hash(instance: Dict[str, Any]) -> str:
    """Hashes only the board + starting positions -- moveBudget/minMoves
    are deterministic functions of those (re-derivable via bfs_min_moves),
    so two instances with the same board+start are the same puzzle
    regardless of what's cached alongside them."""
    board = instance["board"]
    positions = instance["startPositions"]
    payload = json.dumps({
        "rows": board["rows"], "cols": board["cols"],
        "walls": sorted([list(w) for w in board["walls"]]),
        "hole": list(board["hole"]),
        "blockShapes": {bid: list(shape) for bid, shape in board["blockShapes"].items()},
        "ballPos": list(positions["ballPos"]),
        "blockPositions": {bid: list(pos) for bid, pos in positions["blockPositions"].items()},
    }, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _replay_state(instance: Dict[str, Any], move_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Rebuilds the CURRENT board state by replaying move_history from the
    instance's own stored startPositions -- never starts from a
    client-claimed "current board." Each history entry is trusted to have
    already been validated at write time (by a prior successful
    move_check() call that only gets appended to history on success) --
    replay applies moves directly rather than re-validating each one's
    legality a second time, same convention grade_grid_challenge_session
    uses for its own stored live_checks history."""
    board = instance["board"]
    positions = instance["startPositions"]
    for entry in move_history:
        block_id = entry.get("blockId")
        direction = entry["direction"]
        move: Move = ("ball", None, direction) if block_id is None else ("block", block_id, direction)
        positions = apply_move(board, positions, move)
    return positions


def move_check(instance: Dict[str, Any], move_history: List[Dict[str, Any]], block_id: Optional[str], direction: str) -> Dict[str, Any]:
    """Validates ONE next move against the board state replayed fresh from
    the instance's own stored board + the move history so far -- never
    trusts a client-claimed "current board." block_id=None means "move the
    ball." Returns {"valid": False} on any illegal move (out of bounds,
    wrong axis for that block's shape, target occupied, onto the ball,
    etc. -- see legal_block_move/legal_ball_move), never raises."""
    board = instance["board"]
    positions = _replay_state(instance, move_history)

    if block_id is None:
        new_pos = legal_ball_move(board, positions, direction)
        if new_pos is None:
            return {"valid": False}
        won = new_pos == board["hole"]
        return {
            "valid": True, "won": won,
            "ballPos": new_pos, "blockPositions": dict(positions["blockPositions"]),
        }

    new_anchor = legal_block_move(board, positions, block_id, direction)
    if new_anchor is None:
        return {"valid": False}
    new_block_positions = dict(positions["blockPositions"])
    new_block_positions[block_id] = new_anchor
    return {
        "valid": True, "won": False,
        "ballPos": positions["ballPos"], "blockPositions": new_block_positions,
    }


def grade_interactive(instance: Dict[str, Any], move_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Re-derives final won/lost from the FULL stored move history,
    independent of whatever a live move_check() call may have returned
    along the way -- same never-trust-a-running-tally discipline as
    grade_grid_challenge_session re-deriving from live_checks instead of
    summing cached points. A win only counts if the ball is on the hole
    AND it took no more than moveBudget total moves -- defensively checked
    here even though the (not-yet-built) endpoint layer should never let
    move_history exceed the budget in the first place."""
    board = instance["board"]
    move_budget = instance["moveBudget"]
    moves_used = len(move_history)
    final_positions = _replay_state(instance, move_history)
    won = final_positions["ballPos"] == board["hole"] and moves_used <= move_budget
    return {"won": won, "movesUsed": moves_used, "moveBudget": move_budget}


# ---------------------------------------------------------------------------
# Step 3 -- puzzle_bank doc shape (JSON/Mongo-safe) and its inverse. The
# whole board is safe to reveal upfront (nothing is hidden like
# grid_challenge, no correctAnswer to strip like the other 3 types) --
# EXCEPT minMoves, which is deliberately left OUT of this doc shape
# entirely rather than stored-then-stripped: nothing serving-time needs it
# (move_check/grade_interactive only ever read board/moveBudget), and
# revealing "the optimal solution takes exactly N moves" is a real,
# unnecessary partial-answer leak. minMoves only ever exists in the
# in-memory instance dict generate_instance()/verify_instance() work with,
# never in anything that reaches puzzle_bank or the client.
# ---------------------------------------------------------------------------

# Cosmetic only -- never read by any movement/legality/scoring logic,
# purely a rendering aid so the frontend can tell blocks apart. Matches
# the reference's blue/yellow/green examples, extended with 2 more for
# boards with more than 3 blocks. Assigned by sorted block id order at
# doc-build time (not generation time -- color has no bearing on
# solvability, so it doesn't belong in the in-memory `instance` shape
# content_hash() hashes).
BLOCK_COLOR_PALETTE = ["#2C6FA8", "#D4A017", "#3D8B54", "#8B4F9F", "#C1652F"]


def instance_to_doc(instance: Dict[str, Any]) -> Dict[str, Any]:
    board = instance["board"]
    positions = instance["startPositions"]
    sorted_blocks = sorted(positions["blockPositions"].items())
    return {
        "rows": board["rows"], "cols": board["cols"],
        "walls": [list(w) for w in sorted(board["walls"])],
        "hole": list(board["hole"]),
        "blocks": [
            {
                "id": bid, "row": pos[0], "col": pos[1],
                "width": board["blockShapes"][bid][0], "height": board["blockShapes"][bid][1],
                "color": BLOCK_COLOR_PALETTE[i % len(BLOCK_COLOR_PALETTE)],
            }
            for i, (bid, pos) in enumerate(sorted_blocks)
        ],
        "ballStart": list(positions["ballPos"]),
        "moveBudget": instance["moveBudget"],
    }


def doc_to_instance(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Inverse of instance_to_doc() -- rebuilds the tuple/set-based shape
    that all the move/board logic above expects, from a stored (or
    served) puzzle_bank doc. Safe to call on a doc that's already been
    through strip_answer() -- there's nothing for strip_answer to strip
    here (no correctAnswer/explanation keys ever exist on this doc shape),
    so this always round-trips cleanly regardless."""
    block_shapes = {b["id"]: (b["width"], b["height"]) for b in doc["blocks"]}
    block_positions = {b["id"]: (b["row"], b["col"]) for b in doc["blocks"]}
    board = {
        "rows": doc["rows"], "cols": doc["cols"],
        "walls": {tuple(w) for w in doc["walls"]},
        "hole": tuple(doc["hole"]),
        "blockShapes": block_shapes,
    }
    positions = {"ballPos": tuple(doc["ballStart"]), "blockPositions": block_positions}
    return {"board": board, "startPositions": positions, "moveBudget": doc["moveBudget"]}
