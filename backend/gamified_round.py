"""New registry-driven gamified-round system (replaces the deleted
capgemini_challenges.py / cognizant_games.py / accenture_games.py, each of
which reimplemented the same sub-puzzle-set machinery independently).

Three MongoDB collections, one code-level registry (game_types.py):
  gamified_round_config -- one doc per company: which game types it uses,
      how puzzles are picked, sub-puzzle count, per-puzzle timer.
      PROVISIONAL (as of 2026-08-13): perType.deductive_grid.timerPerPuzzle
      (15s) and perType.switch_challenge.timerPerPuzzle (20s) were early
      judgment calls made during the initial build, never validated
      against real user testing -- don't treat them as settled spec. The
      live config documents themselves also carry a `_timerNote` field on
      each of those two entries saying the same thing, so the flag travels
      with the data even for someone querying the collection directly
      rather than reading this file. grid_challenge has no single
      timerPerPuzzle -- its timing is per-phase (2s blink / 6s judgment /
      untimed recall), fixed by the game's mechanic rather than a tunable.
  puzzle_bank            -- ONE shared pool across all companies, filtered by
      gameType + companyTags at serve time. Every doc's `correctAnswer` MUST
      be stripped before any response reaches the client -- see
      strip_answer() below. This is the puzzle_bank equivalent of
      oa_attempts's _hidden_answer_keys.<section_key>.<question_id> pattern
      already used elsewhere: card_matching/memory_recall (the old
      cognizant_games.py types) were killed specifically because they leaked
      answers to the client, per that file's own docstring -- not repeating
      that mistake here.
  game_session            -- one doc per gamified_round section attempt.
      A section now runs EVERY game type listed in that company's config
      together (not a random pick-1-of-N) -- puzzle_ids are grouped by
      type under puzzleIdsByType, and per-type grading breakdowns live
      under gradingByType.<gameType> (never overwriting each other); the
      section's OVERALL raw_score/correct/incorrect/total/graded_at (set
      by server.py's _grade_gamified_round_section, which sums the
      per-type results) live at the top level. Doubles as the
      repetition-tracking source of truth (see get_seen_puzzle_ids) -- no
      separate "seen" collection needed at this scale (SuperMAX's worst
      case is 36 attempts total).
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import game_types
import motion_challenge

_db = None  # set by init(db)


def init(db) -> None:
    global _db
    _db = db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_answer(puzzle_doc: dict) -> dict:
    """CRITICAL: removes correctAnswer (and its explanation, which would
    give the answer away just as directly) before a puzzle is allowed
    anywhere near a response the client will receive. Every code path that
    serves a puzzle to the frontend MUST go through this -- never return a
    raw puzzle_bank doc directly."""
    return {k: v for k, v in puzzle_doc.items() if k not in ("correctAnswer", "explanation")}


async def get_config(company: str) -> Optional[dict]:
    if _db is None:
        return None
    return await _db.gamified_round_config.find_one({"company": company}, {"_id": 0})


async def get_seen_puzzle_ids(user_id: str, game_type: str) -> set:
    """Union of puzzle_ids across this user's past game_session docs for
    this game type specifically. game_session IS the repetition-tracking
    source of truth -- see module docstring for why no separate collection
    exists. Every gamified_round session now runs ALL configured game
    types together (not one type per session), so a session's puzzle_ids
    are grouped by type under puzzleIdsByType -- this reads just the
    slice for the requested type, unioned across all past sessions."""
    if _db is None:
        return set()
    seen: set = set()
    async for doc in _db.game_session.find({"user_id": user_id}, {"puzzleIdsByType": 1, "_id": 0}):
        seen.update((doc.get("puzzleIdsByType") or {}).get(game_type, []))
    return seen


async def sample_puzzles(company: str, game_type: str, user_id: str, count: int) -> List[dict]:
    """Pull up to `count` puzzles for this company+gameType, excluding ones
    this user has already been served in a past session. Returns PUBLIC-SAFE
    dicts only (see strip_answer) -- callers must never bypass this to read
    puzzle_bank directly for a client-facing response. Returns fewer than
    `count` (down to zero) if the pool is exhausted for this user -- callers
    should treat that as a graceful shortfall, not a hard failure, same
    convention as mcq_static_bank.sample_static()."""
    if _db is None or count <= 0:
        return []
    seen = await get_seen_puzzle_ids(user_id, game_type)
    cursor = _db.puzzle_bank.find(
        {"gameType": game_type, "companyTags": company, "puzzle_id": {"$nin": list(seen)}},
        {"_id": 0},
    )
    docs = await cursor.to_list(length=count)
    return [strip_answer(d) for d in docs]


async def create_session(user_id: str, attempt_id: str, company: str, section_key: str,
                          puzzle_ids_by_type: Dict[str, List[str]]) -> str:
    """Records which puzzles were served -- this is both the generic
    session/attempt record the registry model calls for AND the
    repetition-tracking source of truth (see get_seen_puzzle_ids).

    A gamified_round section now runs EVERY configured game type together
    (not a random pick-1-of-N), so puzzle_ids are grouped by type rather
    than one flat list + one gameType field -- this is what lets
    get_seen_puzzle_ids/grade_session/grade_grid_challenge_session pull
    just one type's slice back out without the different types'
    dedup/grading getting tangled together."""
    if _db is None:
        return ""
    session_id = f"{attempt_id}_{section_key}"
    await _db.game_session.update_one(
        {"session_id": session_id},
        {"$set": {
            "session_id": session_id,
            "user_id": user_id,
            "attempt_id": attempt_id,
            "company": company,
            "section_key": section_key,
            "gameTypes": list(puzzle_ids_by_type.keys()),
            "puzzleIdsByType": puzzle_ids_by_type,
            "created_at": _now_iso(),
        }},
        upsert=True,
    )
    return session_id


async def check_answer(
    attempt_id: str, section_key: str, puzzle_id: str,
    selected: Optional[Union[int, List[int]]], timed_out: bool = False, time_taken_ms: Optional[int] = None,
) -> dict:
    """Live, per-puzzle feedback used DURING play (the orange running-score
    bar) -- distinct from grade_session, which remains the sole source of
    truth for pass/fail at final submit. Returns ONLY {correct, pointsAwarded,
    runningScore} -- never correctAnswer, even on a wrong guess.

    Persists each check under game_session.live_checks (keyed by puzzle_id,
    so repeat/retry calls overwrite rather than double-count) so runningScore
    survives a refresh/reconnect mid-session. grade_session does NOT read
    live_checks -- it independently re-grades from the final submitted
    `answers` dict, so a bug here can never silently become the real grade.
    """
    empty = {"correct": False, "pointsAwarded": 0, "runningScore": 0}
    if _db is None:
        return empty
    session_id = f"{attempt_id}_{section_key}"
    session = await _db.game_session.find_one({"session_id": session_id})
    if not session:
        return empty
    doc = await _db.puzzle_bank.find_one({"puzzle_id": puzzle_id}, {"_id": 0})
    if not doc:
        return {**empty, "runningScore": session.get("running_score", 0)}

    type_entry = game_types.GAME_TYPES.get(doc.get("gameType"), {})
    checker = type_entry.get("answer_check")
    scoring = type_entry.get("scoring", {"correct": 1, "incorrect": -1})
    is_correct = (not timed_out) and bool(checker and checker(doc, selected))
    points = scoring["correct"] if is_correct else scoring["incorrect"]

    live_checks = session.get("live_checks") or {}
    live_checks[puzzle_id] = {
        "selected": selected, "timedOut": timed_out, "timeTakenMs": time_taken_ms,
        "correct": is_correct, "pointsAwarded": points,
    }
    running_score = sum(v["pointsAwarded"] for v in live_checks.values())

    await _db.game_session.update_one(
        {"session_id": session_id},
        {"$set": {"live_checks": live_checks, "running_score": running_score}},
    )
    return {"correct": is_correct, "pointsAwarded": points, "runningScore": running_score}


async def grade_session(session_id: str, game_type: str, answers: Dict[str, dict]) -> dict:
    """Grades ONE game type's puzzles within a session, server-side against
    puzzle_bank's stored correctAnswer -- the client only ever submitted
    option indices (or a timeout), never saw the answer. Dispatches
    per-puzzle through game_types.GAME_TYPES[...]['answer_check'] rather
    than hardcoding "submitted index == correctAnswer" here, so a future
    game type with a differently-shaped answer doesn't need this function
    to change.

    A gamified_round session now runs every configured game type
    together, so this only grades the slice of puzzle_ids belonging to
    `game_type` (via puzzleIdsByType) -- the caller (server.py's
    _grade_gamified_round_section) grades each present type separately
    via this function and combines the results into one section score.
    Persists this type's breakdown under gradingByType.<game_type> (never
    overwrites another type's breakdown in the same session doc).

    `answers` is keyed by puzzle_id, each value:
        {"selected": <option index> | None, "timedOut": bool, "timeTakenMs": int}
    A timeout (timedOut=True, selected=None -- the per-puzzle auto-advance
    case) is scored identically to a wrong answer. The point delta itself is
    NOT a fixed +1/-1 -- it's looked up per puzzle's gameType via
    game_types.GAME_TYPES[...]['scoring'], since different game types use
    different ratios (deductive_grid +1/-1, switch_challenge +3/-1).
    """
    empty = {"raw_score": 0, "correct": 0, "incorrect": 0, "total": 0, "items": []}
    if _db is None:
        return empty
    session = await _db.game_session.find_one({"session_id": session_id})
    if not session:
        return empty
    puzzle_ids = (session.get("puzzleIdsByType") or {}).get(game_type, [])
    docs = await _db.puzzle_bank.find(
        {"puzzle_id": {"$in": puzzle_ids}}, {"_id": 0}
    ).to_list(length=len(puzzle_ids) or 1)
    by_id = {d["puzzle_id"]: d for d in docs}

    raw_score = 0
    correct = 0
    incorrect = 0
    per_item = []
    for pid in puzzle_ids:
        doc = by_id.get(pid)
        if not doc:
            continue
        entry = answers.get(pid) or {}
        selected = entry.get("selected")
        timed_out = bool(entry.get("timedOut"))
        time_taken_ms = entry.get("timeTakenMs")

        type_entry = game_types.GAME_TYPES.get(doc.get("gameType"), {})
        checker = type_entry.get("answer_check")
        scoring = type_entry.get("scoring", {"correct": 1, "incorrect": -1})
        is_correct = (not timed_out) and bool(checker and checker(doc, selected))
        raw_score += scoring["correct"] if is_correct else scoring["incorrect"]
        if is_correct:
            correct += 1
        else:
            incorrect += 1
        per_item.append({
            "puzzle_id": pid,
            "correct": is_correct,
            "timedOut": timed_out,
            "selected": selected,
            "timeTakenMs": time_taken_ms,
        })

    total = len(puzzle_ids)
    result = {"raw_score": raw_score, "correct": correct, "incorrect": incorrect, "total": total, "items": per_item}
    await _db.game_session.update_one(
        {"session_id": session_id},
        {"$set": {f"gradingByType.{game_type}": {**result, "graded_at": _now_iso()}}},
    )
    return result


# ============================================================
# grid_challenge -- phase-gated progressive reveal.
#
# game_session EXTENSION for this game type: no new top-level fields.
# The existing `live_checks` dict (already used by check_answer above,
# keyed by puzzle_id for deductive_grid/switch_challenge) is reused
# as-is, just with grid_challenge choosing composite string keys instead
# of a bare puzzle_id -- since a grid_challenge session only ever has ONE
# puzzle_id, there's no collision risk with the other types' convention:
#   "judgment_{blockIndex}_{judgmentIndex}" -> {answer, timeTakenMs, correct, pointsAwarded}
#   "recall"                                -> {answer, timeTakenMs, perPosition, pointsAwarded}
# `running_score` (already computed as sum(live_checks[*].pointsAwarded))
# needs no change either -- it already sums whatever's in the dict
# regardless of key shape. This is deliberately NOT a new field: the
# phase-gating check below (_is_block_fully_answered) is derived by
# checking which judgment keys are present, so there's no separate
# "revealed"/"progress" state to keep in sync or let drift.
# ============================================================

def _grid_challenge_judgment_key(block_index: int, judgment_index: int) -> str:
    return f"judgment_{block_index}_{judgment_index}"


_GRID_CHALLENGE_RECALL_KEY = "recall"


def _is_block_fully_answered(puzzle_doc: dict, live_checks: dict, block_index: int) -> bool:
    """Derives "has block N been fully answered" from live_checks alone --
    no separate progress field to fall out of sync. Judgment COUNT for the
    block comes from the puzzle doc itself (1/2/4 per JUDGMENTS_PER_BLOCK),
    not a hardcoded constant, so this stays correct even if that scaling
    ever changes."""
    blocks = puzzle_doc.get("blocks") or []
    if block_index < 0 or block_index >= len(blocks):
        return False
    expected = len(blocks[block_index].get("judgments") or [])
    if expected == 0:
        return False
    return all(_grid_challenge_judgment_key(block_index, j) in live_checks for j in range(expected))


def _phase_block_index(phase: str, num_blocks: int) -> Optional[int]:
    for i in range(num_blocks):
        if phase in (f"block{i + 1}_blink", f"block{i + 1}_judgments"):
            return i
    return None


async def get_grid_challenge_phase(
    attempt_id: str, section_key: str, puzzle_id: str, phase: str, block_index_hint: Optional[int] = None,
) -> dict:
    """Phase-gated content reveal -- returns ONLY the requested phase's
    safe subset of a single full instance, never the whole document.

    HARD REQUIREMENT enforced HERE, server-side, against game_session
    state (never client-trusted sequencing): block N (blink OR judgments)
    is unreachable until block N-1's judgments are ALL present in
    live_checks; recall_board is unreachable until the last block is
    fully answered. Raises PermissionError (mapped to HTTP 403 by the
    route) if the gate isn't satisfied -- this is a real rejection, not a
    client-side "don't ask" convention.
    """
    if _db is None:
        raise ValueError("db not initialized")
    session_id = f"{attempt_id}_{section_key}"
    session = await _db.game_session.find_one({"session_id": session_id})
    if not session:
        raise ValueError("session not found")
    doc = await _db.puzzle_bank.find_one({"puzzle_id": puzzle_id}, {"_id": 0})
    if not doc or doc.get("gameType") != "grid_challenge":
        raise ValueError("grid_challenge puzzle not found")

    live_checks = session.get("live_checks") or {}
    blocks = doc.get("blocks") or []

    if phase == "recall_board":
        last_block = len(blocks) - 1
        if not _is_block_fully_answered(doc, live_checks, last_block):
            raise PermissionError("recall_board requested before the final block's judgments were fully answered")
        return {"circleLayout": doc["circleLayout"]}

    idx = _phase_block_index(phase, len(blocks))
    if idx is None:
        raise ValueError(f"unknown phase: {phase}")
    if block_index_hint is not None and block_index_hint != idx:
        raise ValueError(f"blockIndex ({block_index_hint}) doesn't match phase ({phase})")
    if idx > 0 and not _is_block_fully_answered(doc, live_checks, idx - 1):
        raise PermissionError(f"{phase} requested before block {idx} (0-indexed) was fully answered")

    if phase.endswith("_blink"):
        return {"circleLayout": doc["circleLayout"], "targetCircleId": blocks[idx]["targetCircleId"]}
    # "_judgments" -- patternA/patternB only, correctAnswer never leaves this function
    return {"judgments": [{"patternA": j["patternA"], "patternB": j["patternB"]} for j in blocks[idx]["judgments"]]}


async def check_grid_challenge_answer(
    attempt_id: str, section_key: str, puzzle_id: str, phase: str,
    block_index: Optional[int], judgment_index: Optional[int], answer: Any,
    time_taken_ms: Optional[int] = None, timed_out: bool = False,
) -> dict:
    """Live per-sub-answer feedback (7 judgments + 3 recall positions),
    same discipline as check_answer(): never returns the puzzle's stored
    correct value(s), only derived correctness signals. Also enforces the
    same server-side sequencing gate as get_grid_challenge_phase -- an
    out-of-order ANSWER attempt (not just a fetch) is rejected the same
    way, scored as if nothing was submitted, rather than silently
    accepted.

    timed_out=True FORCES is_correct=False regardless of what `answer`
    happens to be (matches deductive_grid/switch_challenge's convention:
    `is_correct = (not timed_out) and checker(...)`) -- without this, a
    timeout submitting answer=None would evaluate bool(None)==False, which
    would silently register as CORRECT whenever the true answer happens to
    be False. timed_out is also stored in live_checks so
    grade_grid_challenge_session's independent re-derivation honors it too."""
    empty = {"correct": False, "pointsAwarded": 0, "runningScore": 0}
    if _db is None:
        return empty
    session_id = f"{attempt_id}_{section_key}"
    session = await _db.game_session.find_one({"session_id": session_id})
    if not session:
        return empty
    doc = await _db.puzzle_bank.find_one({"puzzle_id": puzzle_id}, {"_id": 0})
    if not doc or doc.get("gameType") != "grid_challenge":
        return {**empty, "runningScore": session.get("running_score", 0)}

    type_entry = game_types.GAME_TYPES.get("grid_challenge", {})
    checker = type_entry.get("phase_check")
    scoring = type_entry.get("scoring", {"correct": 3, "incorrect": -1})
    live_checks = session.get("live_checks") or {}
    blocks = doc.get("blocks") or []

    def _persist(key: str, entry: dict) -> int:
        live_checks[key] = entry
        return sum(v.get("pointsAwarded", 0) for v in live_checks.values())

    if phase == "judgment":
        if block_index is None or judgment_index is None:
            return {**empty, "runningScore": session.get("running_score", 0)}
        if block_index > 0 and not _is_block_fully_answered(doc, live_checks, block_index - 1):
            return {"correct": False, "pointsAwarded": 0, "runningScore": session.get("running_score", 0)}

        result = checker(doc, "judgment", block_index, judgment_index, answer) if checker else {"correct": False}
        is_correct = (not timed_out) and bool(result.get("correct"))
        points = scoring["correct"] if is_correct else scoring["incorrect"]
        key = _grid_challenge_judgment_key(block_index, judgment_index)
        running_score = _persist(key, {
            "answer": answer, "timedOut": timed_out, "timeTakenMs": time_taken_ms,
            "correct": is_correct, "pointsAwarded": points,
        })
        await _db.game_session.update_one(
            {"session_id": session_id}, {"$set": {"live_checks": live_checks, "running_score": running_score}},
        )
        return {"correct": is_correct, "pointsAwarded": points, "runningScore": running_score}

    if phase == "recall":
        last_block = len(blocks) - 1
        if not _is_block_fully_answered(doc, live_checks, last_block):
            return {"perPositionCorrect": [False, False, False], "pointsAwarded": 0, "runningScore": session.get("running_score", 0)}

        result = checker(doc, "recall", None, None, answer) if checker else {"perPosition": [False, False, False]}
        per_position = result.get("perPosition") or [False, False, False]
        points = sum(scoring["correct"] if p else scoring["incorrect"] for p in per_position)
        running_score = _persist(_GRID_CHALLENGE_RECALL_KEY, {
            "answer": answer, "timeTakenMs": time_taken_ms, "perPosition": per_position, "pointsAwarded": points,
        })
        await _db.game_session.update_one(
            {"session_id": session_id}, {"$set": {"live_checks": live_checks, "running_score": running_score}},
        )
        return {"perPositionCorrect": per_position, "pointsAwarded": points, "runningScore": running_score}

    return empty


async def grade_grid_challenge_session(session_id: str) -> dict:
    """Final grading -- independently RE-DERIVES the full score from the
    raw answers stored server-side in live_checks (the "answer" field each
    check_grid_challenge_answer call persisted), by calling phase_check
    fresh on each one. Deliberately does NOT just sum up live_checks'
    already-computed pointsAwarded fields -- that would mean a bug in the
    live-scoring path silently becomes the final grade. A judgment or the
    recall that was never answered (candidate abandoned mid-session) is
    graded as incorrect, same convention as a timeout elsewhere."""
    empty = {"raw_score": 0, "correct": 0, "incorrect": 0, "total": 0, "items": []}
    if _db is None:
        return empty
    session = await _db.game_session.find_one({"session_id": session_id})
    if not session:
        return empty
    puzzle_ids = (session.get("puzzleIdsByType") or {}).get("grid_challenge") or []
    if not puzzle_ids:
        return empty
    doc = await _db.puzzle_bank.find_one({"puzzle_id": puzzle_ids[0]}, {"_id": 0})
    if not doc or doc.get("gameType") != "grid_challenge":
        return empty

    type_entry = game_types.GAME_TYPES.get("grid_challenge", {})
    checker = type_entry.get("phase_check")
    scoring = type_entry.get("scoring", {"correct": 3, "incorrect": -1})
    live_checks = session.get("live_checks") or {}
    blocks = doc.get("blocks") or []

    raw_score = 0
    correct = 0
    incorrect = 0
    items = []

    for block_idx, block in enumerate(blocks):
        for judgment_idx in range(len(block.get("judgments") or [])):
            key = _grid_challenge_judgment_key(block_idx, judgment_idx)
            entry = live_checks.get(key)
            raw_answer = entry.get("answer") if entry else None
            was_timed_out = bool(entry.get("timedOut")) if entry else False
            result = checker(doc, "judgment", block_idx, judgment_idx, raw_answer) if checker else {"correct": False}
            is_correct = (not was_timed_out) and bool(result.get("correct"))
            points = scoring["correct"] if is_correct else scoring["incorrect"]
            raw_score += points
            correct += 1 if is_correct else 0
            incorrect += 0 if is_correct else 1
            items.append({
                "phase": "judgment", "blockIndex": block_idx, "judgmentIndex": judgment_idx,
                "correct": is_correct, "answered": entry is not None,
            })

    recall_entry = live_checks.get(_GRID_CHALLENGE_RECALL_KEY)
    recall_raw_answer = recall_entry.get("answer") if recall_entry else None
    recall_result = checker(doc, "recall", None, None, recall_raw_answer) if checker else {"perPosition": [False, False, False]}
    per_position = recall_result.get("perPosition") or [False, False, False]
    for i, p in enumerate(per_position):
        points = scoring["correct"] if p else scoring["incorrect"]
        raw_score += points
        correct += 1 if p else 0
        incorrect += 0 if p else 1
        items.append({"phase": "recall", "position": i, "correct": p, "answered": recall_entry is not None})

    total = len(items)
    result = {"raw_score": raw_score, "correct": correct, "incorrect": incorrect, "total": total, "items": items}
    await _db.game_session.update_one(
        {"session_id": session_id},
        {"$set": {"gradingByType.grid_challenge": {**result, "graded_at": _now_iso()}}},
    )
    return result


# ============================================================
# motion_challenge -- interactive sliding-block pathing puzzle. Unlike
# grid_challenge's progressive REVEAL, nothing here is secret (the whole
# board is visible from move one -- see motion_challenge.py's
# instance_to_doc, which never writes minMoves into anything client-
# reachable). What needs server enforcement instead is incremental
# STATE-MUTATION validation: each move mutates a server-held board state
# that's always re-derived by replaying the FULL stored move history from
# the puzzle's own initial board, never trusted from a client-claimed
# "current board."
#
# game_session EXTENSION for this game type -- ONE new top-level field:
#   "motionChallengeMoves": {
#       "<puzzle_id>": [{"blockId": str | None, "direction": str}, ...],
#       ...
#   }
# Genuinely new, not a repurposing of live_checks (shaped for one-shot
# writes keyed by a flat string -- a move history is an ORDERED, GROWING
# list per puzzle_id, a different shape entirely). Deliberately does NOT
# also store a separate movesUsed/won/status field -- both are always
# DERIVED by replaying this history through grade_interactive (see
# motion_challenge.py), same never-trust-a-running-tally discipline as
# grid_challenge's _is_block_fully_answered/grade_grid_challenge_session.
# Undo is simply "pop the last entry": since movesUsed is never tracked
# separately, there's no refund bookkeeping to get wrong -- the popped
# move just un-happened.
# ============================================================

def _motion_challenge_moves(session: dict, puzzle_id: str) -> List[Dict[str, Any]]:
    return ((session.get("motionChallengeMoves") or {}).get(puzzle_id)) or []


def _motion_challenge_board_state(positions: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ballPos": list(positions["ballPos"]),
        "blockPositions": {bid: list(pos) for bid, pos in positions["blockPositions"].items()},
    }


async def _motion_challenge_load(attempt_id: str, section_key: str, puzzle_id: str):
    """Shared ownership + doc lookup for both the move and undo endpoints.
    Raises PermissionError if this puzzle_id was never served to this
    session -- the only case treated as a real rejection (mapped to HTTP
    403 by the route), same convention as grid_challenge's phase-gating.
    Already-won/already-lost are NOT treated as errors here -- those are
    normal finished-level responses, handled by the callers below."""
    if _db is None:
        raise PermissionError("db not initialized")
    session_id = f"{attempt_id}_{section_key}"
    session = await _db.game_session.find_one({"session_id": session_id})
    if not session:
        raise PermissionError("session not found")
    served = (session.get("puzzleIdsByType") or {}).get("motion_challenge") or []
    if puzzle_id not in served:
        raise PermissionError("puzzle_id was not served to this session")
    doc = await _db.puzzle_bank.find_one({"puzzle_id": puzzle_id}, {"_id": 0})
    if not doc or doc.get("gameType") != "motion_challenge":
        raise PermissionError("motion_challenge puzzle not found")
    return session_id, session, doc


async def motion_challenge_move(
    attempt_id: str, section_key: str, puzzle_id: str,
    block_id: Optional[str], direction: str,
) -> dict:
    """Validates ONE move and, if legal AND within budget, appends it to
    the server-held history. Rejects (valid=False, history unmutated) if:
    the move itself is illegal (wrong axis, target occupied, etc. -- see
    motion_challenge.move_check), the level is already won, or the level
    is already lost (budget already exhausted without winning) -- a
    client can never re-trigger moves against a finished level.

    `budgetExhausted` is returned on EVERY response: True both when THIS
    move is the one that used up the last budget slot without winning,
    and when a move is rejected because the level was already in that
    state before this request arrived -- lets the frontend distinguish
    "you just ran out" from "this level was already over" from a plain
    illegal-move rejection (valid=False, budgetExhausted=False)."""
    session_id, session, doc = await _motion_challenge_load(attempt_id, section_key, puzzle_id)
    instance = motion_challenge.doc_to_instance(doc)
    history = _motion_challenge_moves(session, puzzle_id)

    current = motion_challenge.grade_interactive(instance, history)
    already_won = current["won"]
    already_lost = (not already_won) and len(history) >= instance["moveBudget"]

    if already_won or already_lost:
        positions = motion_challenge._replay_state(instance, history)
        return {
            "valid": False, "boardState": _motion_challenge_board_state(positions),
            "movesUsed": len(history), "won": already_won, "budgetExhausted": already_lost,
        }

    result = motion_challenge.move_check(instance, history, block_id, direction)
    if not result.get("valid"):
        positions = motion_challenge._replay_state(instance, history)
        return {
            "valid": False, "boardState": _motion_challenge_board_state(positions),
            "movesUsed": len(history), "won": False, "budgetExhausted": False,
        }

    new_history = history + [{"blockId": block_id, "direction": direction}]
    moves_by_puzzle = session.get("motionChallengeMoves") or {}
    moves_by_puzzle[puzzle_id] = new_history
    await _db.game_session.update_one(
        {"session_id": session_id}, {"$set": {"motionChallengeMoves": moves_by_puzzle}},
    )

    new_grade = motion_challenge.grade_interactive(instance, new_history)
    budget_exhausted = (not new_grade["won"]) and len(new_history) >= instance["moveBudget"]
    return {
        "valid": True,
        "boardState": {"ballPos": list(result["ballPos"]), "blockPositions": {bid: list(pos) for bid, pos in result["blockPositions"].items()}},
        "movesUsed": len(new_history), "won": new_grade["won"], "budgetExhausted": budget_exhausted,
    }


async def motion_challenge_undo(attempt_id: str, section_key: str, puzzle_id: str) -> dict:
    """Pops the last move from server-held history and recomputes state
    via replay -- free to perform (doesn't cost a budget move) and
    doesn't "refund" one either, since movesUsed is never tracked
    separately from len(history): popping an entry just makes it as if
    that move never happened. Allowed even if the level is currently
    "lost" (budget exhausted without winning) -- undo IS the recovery
    path for that state, not blocked by it. Rejected only if the level is
    already WON (finished, no further mutation of any kind); a no-op
    (not an error) if there's nothing left to undo."""
    session_id, session, doc = await _motion_challenge_load(attempt_id, section_key, puzzle_id)
    instance = motion_challenge.doc_to_instance(doc)
    history = _motion_challenge_moves(session, puzzle_id)

    current = motion_challenge.grade_interactive(instance, history)
    if current["won"]:
        positions = motion_challenge._replay_state(instance, history)
        return {"boardState": _motion_challenge_board_state(positions), "movesUsed": len(history), "won": True}

    new_history = history[:-1] if history else history
    moves_by_puzzle = session.get("motionChallengeMoves") or {}
    moves_by_puzzle[puzzle_id] = new_history
    await _db.game_session.update_one(
        {"session_id": session_id}, {"$set": {"motionChallengeMoves": moves_by_puzzle}},
    )

    positions = motion_challenge._replay_state(instance, new_history)
    return {"boardState": _motion_challenge_board_state(positions), "movesUsed": len(new_history), "won": False}


async def motion_challenge_state(attempt_id: str, section_key: str, puzzle_id: str) -> dict:
    """Read-only: returns the CURRENT server-held state for this
    puzzle_id, replayed fresh from stored move history -- never mutates
    anything, safe to call any number of times. Exists because the
    frontend must never assume a level starts fresh on mount: a page
    reload mid-level (or simply re-entering a level already in progress)
    has to show the REAL state the server holds, not the puzzle's
    pristine starting position -- discovered as a genuine bug during
    Step 4/5 verification (the frontend's goToLevel() was unconditionally
    resetting to the puzzle's initial board on every mount, silently
    diverging from what the server had already recorded)."""
    session_id, session, doc = await _motion_challenge_load(attempt_id, section_key, puzzle_id)
    instance = motion_challenge.doc_to_instance(doc)
    history = _motion_challenge_moves(session, puzzle_id)
    positions = motion_challenge._replay_state(instance, history)
    grade = motion_challenge.grade_interactive(instance, history)
    already_lost = (not grade["won"]) and len(history) >= instance["moveBudget"]
    return {
        "boardState": _motion_challenge_board_state(positions),
        "movesUsed": len(history), "won": grade["won"], "budgetExhausted": already_lost,
    }


async def grade_motion_challenge_session(session_id: str) -> dict:
    """Final grading -- independently re-derives won/lost for EVERY level
    served this session (via grade_interactive, fresh from the full
    stored motionChallengeMoves history), never trusting any cached
    result from a live move_check call along the way. A level with NO
    history at all (never attempted -- e.g. the pooled 4-minute timer ran
    out before the candidate reached it) naturally grades as lost: an
    empty move history always leaves the ball off the hole (generation
    guarantees minMoves >= 3, so the start position is never already the
    win state), so this needs no special-casing -- same as how a
    never-answered grid_challenge judgment/recall falls out of that
    function's general re-derivation rather than a separate branch."""
    empty = {"raw_score": 0, "correct": 0, "incorrect": 0, "total": 0, "items": []}
    if _db is None:
        return empty
    session = await _db.game_session.find_one({"session_id": session_id})
    if not session:
        return empty
    puzzle_ids = (session.get("puzzleIdsByType") or {}).get("motion_challenge") or []
    if not puzzle_ids:
        return empty
    docs = await _db.puzzle_bank.find(
        {"puzzle_id": {"$in": puzzle_ids}}, {"_id": 0}
    ).to_list(length=len(puzzle_ids))
    by_id = {d["puzzle_id"]: d for d in docs}

    type_entry = game_types.GAME_TYPES.get("motion_challenge", {})
    grader = type_entry.get("grade_interactive")
    scoring = type_entry.get("scoring", {"correct": 4, "incorrect": -1})
    moves_by_puzzle = session.get("motionChallengeMoves") or {}

    raw_score = 0
    correct = 0
    incorrect = 0
    items = []
    for pid in puzzle_ids:
        doc = by_id.get(pid)
        if not doc:
            continue
        instance = motion_challenge.doc_to_instance(doc)
        history = moves_by_puzzle.get(pid) or []
        result = grader(instance, history) if grader else {"won": False, "movesUsed": len(history), "moveBudget": instance["moveBudget"]}
        is_won = bool(result.get("won"))
        points = scoring["correct"] if is_won else scoring["incorrect"]
        raw_score += points
        correct += 1 if is_won else 0
        incorrect += 0 if is_won else 1
        items.append({
            "puzzle_id": pid, "won": is_won,
            "movesUsed": result.get("movesUsed", len(history)),
            "moveBudget": result.get("moveBudget", instance["moveBudget"]),
        })

    total = len(items)
    result = {"raw_score": raw_score, "correct": correct, "incorrect": incorrect, "total": total, "items": items}
    await _db.game_session.update_one(
        {"session_id": session_id},
        {"$set": {"gradingByType.motion_challenge": {**result, "graded_at": _now_iso()}}},
    )
    return result
