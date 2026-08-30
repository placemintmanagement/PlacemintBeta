"""Code-level registry of gamified-round game types (NOT a DB collection --
see gamified_round.py for the DB side: gamified_round_config/puzzle_bank/
game_session).

Each entry maps a `gameType` string to everything generic serving/grading
code needs, so adding a new game type means registering it here -- nothing
in gamified_round.py or server.py's dispatch should need a per-type branch.

    generator(...) -> puzzle dict, signature varies by type (see the
        individual game modules).
    solver(...) -> independently re-derived answer, used only at
        puzzle-authoring time to verify a puzzle before it's inserted into
        puzzle_bank -- never called at serve/grade time.
    answer_check(puzzle_doc, submitted) -> bool, used at grading time against
        the full (server-only) puzzle_doc including correctAnswer. Used by
        types where one puzzle produces exactly ONE gradable sub-answer
        (deductive_grid, switch_challenge).
    phase_check(puzzle_doc, phase, block_index, judgment_index, submitted) ->
        dict, the richer alternative to answer_check for types where one
        puzzle_bank document produces MULTIPLE independently-gradable
        sub-answers delivered across separate phases (grid_challenge: 3
        blocks with 1/2/4 judgments each = 7 judgments + a 3-position
        recall, not a single index comparison). Returns a phase-shaped
        result -- {"correct": bool} for a judgment (block_index selects
        the block, judgment_index selects which of that block's 1/2/4
        judgments), {"perPosition": [bool,bool,bool], "correctCount": int}
        for a recall (block_index/judgment_index unused) -- never the
        puzzle_doc's own stored correct value(s). A game type defines
        answer_check OR phase_check, not both; callers (gamified_round.py)
        must check which one is present before serving or grading a
        puzzle of that type.
    move_check(instance, move_history, block_id, direction) -> dict, a
        THIRD alternative (motion_challenge only) for types where nothing
        is secret (the whole board is visible from move one -- there's no
        "answer" to check or reveal) but interaction is INCREMENTAL and
        needs server-side state-mutation validation per move, replayed
        fresh from the puzzle's own stored board each time rather than
        trusting a client-claimed "current board." Returns
        {"valid": bool, "won": bool, ...updated board fields} -- never a
        correctness verdict against a stored answer, because there isn't
        one.
    grade_interactive(instance, move_history) -> dict, motion_challenge's
        final-grading counterpart to grade_session/grade_grid_challenge_session
        -- re-derives won/lost from the FULL stored move history rather
        than trusting any cached result from a live move_check call along
        the way. A game type defines answer_check, phase_check, OR
        move_check+grade_interactive -- never more than one of these three
        shapes.
    scoring: {"correct": int, "incorrect": int} -- the point delta applied
        per sub-answer in gamified_round.grade_session/check_answer.
        Different game types use different ratios on purpose (deductive_grid
        +1/-1, switch_challenge +3/-1, grid_challenge +3/-1, motion_challenge
        +4/-1) -- looked up per puzzle's gameType rather than hardcoding one
        ratio everywhere.
    frontend_component: string name matched by the frontend's own registry
        to pick which React component renders a puzzle of this gameType.
"""
from typing import Any, Callable, Dict, List, Optional

from . import deductive_grid
from . import switch_challenge
from . import grid_challenge
from . import inductive_challenge
from . import motion_challenge


def _index_answer_check(puzzle_doc: dict, submitted: Any) -> bool:
    try:
        submitted_index = int(submitted)
    except (TypeError, ValueError):
        return False
    return submitted_index == puzzle_doc.get("correctAnswer")


def _pair_answer_check(puzzle_doc: dict, submitted: Any) -> bool:
    """inductive_challenge's correctAnswer is a 2-element index list, not
    a single index -- unordered comparison (sorted on both sides), since
    selection is unordered (see inductive_challenge.py's module docstring
    for why that's well-defined for this rule class)."""
    try:
        submitted_pair = sorted(int(x) for x in submitted)
    except (TypeError, ValueError):
        return False
    if len(submitted_pair) != 2:
        return False
    correct = puzzle_doc.get("correctAnswer")
    if not isinstance(correct, list) or len(correct) != 2:
        return False
    return submitted_pair == sorted(correct)


def _grid_challenge_phase_check(
    puzzle_doc: dict, phase: str, block_index: Optional[int], judgment_index: Optional[int], submitted: Any,
) -> Dict[str, Any]:
    """Never returns the puzzle_doc's own correctAnswer/correctRecallOrder
    values -- only derived correctness signals. `judgment` grades ONE
    judgment within ONE block (block_index selects the block; judgment_index
    selects which of that block's 1/2/4 judgments) against that judgment's
    stored correctAnswer. `recall` grades each of the 3 submitted positions
    independently, order-sensitive (submitted[i] must match
    correctRecallOrder[i] specifically, not just appear somewhere in the
    set) -- matches the confirmed partial-credit scoring interpretation."""
    if phase == "judgment":
        blocks = puzzle_doc.get("blocks") or []
        if block_index is None or not (0 <= block_index < len(blocks)):
            return {"correct": False}
        judgments = blocks[block_index].get("judgments") or []
        if judgment_index is None or not (0 <= judgment_index < len(judgments)):
            return {"correct": False}
        correct_answer = judgments[judgment_index].get("correctAnswer")
        try:
            submitted_bool = bool(submitted)
        except Exception:
            return {"correct": False}
        return {"correct": submitted_bool == correct_answer}

    if phase == "recall":
        correct_order: List[str] = puzzle_doc.get("correctRecallOrder") or []
        submitted_list = submitted if isinstance(submitted, list) else []
        per_position = [
            (i < len(submitted_list)) and submitted_list[i] == correct_order[i]
            for i in range(len(correct_order))
        ]
        return {"perPosition": per_position, "correctCount": sum(per_position)}

    return {"correct": False}


GAME_TYPES: Dict[str, Dict[str, Any]] = {
    "deductive_grid": {
        "gridSizes": deductive_grid.GRID_SIZES,
        "generator": deductive_grid.generate_puzzle,
        "solver": deductive_grid.solve_puzzle,
        "verify": deductive_grid.verify_puzzle,
        "content_hash": deductive_grid.content_hash,
        "answer_check": _index_answer_check,
        "scoring": {"correct": 1, "incorrect": -1},
        "frontend_component": "DeductiveGridQuestion",
    },
    "switch_challenge": {
        "generator": switch_challenge.generate_puzzle,
        "solver": switch_challenge.solve_puzzle,
        "verify": switch_challenge.verify_puzzle,
        "content_hash": switch_challenge.content_hash,
        "answer_check": _index_answer_check,
        "scoring": {"correct": 3, "incorrect": -1},
        "frontend_component": "SwitchChallengeQuestion",
    },
    "grid_challenge": {
        # NOT yet safe to serve -- see grid_challenge.py's module docstring.
        # The progressive-reveal serving layer (step 3) and frontend (step
        # 4) don't exist yet; do not add "grid_challenge" to any
        # gamified_round_config's gameTypes list until both do.
        "generator": grid_challenge.generate_instance,
        "solver": grid_challenge.solve_symmetry,
        "verify": grid_challenge.verify_instance,
        "content_hash": grid_challenge.content_hash,
        "phase_check": _grid_challenge_phase_check,  # NOT answer_check -- see module docstring above
        "scoring": {"correct": 3, "incorrect": -1},
        "frontend_component": "GridChallengeSection",  # not yet built (step 4)
    },
    "inductive_challenge": {
        # Generator/verifier/registry entry built (Steps 1-2). No
        # puzzle_bank writes and no frontend component yet -- do not add
        # "inductive_challenge" to any gamified_round_config's gameTypes
        # list until both exist.
        "generator": inductive_challenge.generate_instance,
        "solver": inductive_challenge.solve_inductive,
        "verify": inductive_challenge.verify_instance,
        "content_hash": inductive_challenge.content_hash,
        "answer_check": _pair_answer_check,  # NOT phase_check -- everything is safe to reveal upfront, same pattern as deductive_grid/switch_challenge
        "scoring": {"correct": 3, "incorrect": -1},
        "frontend_component": "InductiveChallengeSection",  # not yet built
    },
    "motion_challenge": {
        # Generator (with the confirmed minMoves>=3 acceptance filter baked
        # into generate_instance itself)/verifier/registry entry built
        # (Steps 1-2). No puzzle_bank writes, no HTTP endpoints, no frontend
        # component yet -- do not add "motion_challenge" to any
        # gamified_round_config's gameTypes list until all three exist.
        "generator": motion_challenge.generate_instance,
        "solver": motion_challenge.bfs_min_moves,  # returns (min_moves, states_explored), not an index -- see module docstring
        "verify": motion_challenge.verify_instance,
        "content_hash": motion_challenge.content_hash,
        "move_check": motion_challenge.move_check,            # NOT answer_check or phase_check -- see module docstring above
        "grade_interactive": motion_challenge.grade_interactive,
        "scoring": {"correct": 4, "incorrect": -1},
        "frontend_component": "MotionChallengeSection",  # not yet built
    },
}
