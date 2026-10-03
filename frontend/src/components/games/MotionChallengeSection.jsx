import React, { useEffect, useRef, useState, useCallback } from "react";
import { Play, Clock, Target, Undo2, CheckCircle2, XCircle } from "lucide-react";
import api from "../../api";
import { TID } from "../../testIds";

// Genuinely new flow-wrapper, same precedent as GridChallengeSection --
// reuses only the outer container language (#FAF8F3 page background,
// rounded-xl white cards, soft shadow, no border, the instructions-
// screen-with-Play-button convention). Nothing about the sliding-block
// board has anything visually in common with any other type here.
//
// Unlike GridChallengeSection (which owns ONE puzzleId and fetches phases
// progressively because part of ITS content is secret), this type is the
// opposite of secret -- the whole board is safe to reveal upfront, same
// as the flat-list types -- but interaction is live and stateful (each
// move is a real round trip). So this component receives `puzzles` (all
// 4 levels' full public docs, pre-fetched, same as DeductiveGridSection/
// SwitchChallengeSection/InductiveChallengeSection) but ALSO needs
// attemptId/sectionKey (like GridChallengeSection) to call the real
// /motion-challenge/move and /undo endpoints per move.
//
// Props: puzzles (array of up to 4 public-safe docs: {id|puzzle_id, rows,
// cols, walls, hole, blocks:[{id,row,col,width,height,color}], ballStart,
// moveBudget}), attemptId, sectionKey, config, onComplete().
//
// Timer model is genuinely different from every other type here: ONE
// pooled countdown (default 240s) runs across all 4 levels, not a
// per-item countdown that resets. If it hits 0 mid-level, the section
// ends immediately -- whatever move history already exists server-side
// for the in-progress level just stands, and grade_motion_challenge_session
// naturally scores it as a loss (not won) with zero special-casing needed
// here (see gamified_round.py's docstring for why that falls out for free).
//
// INTERACTION (judgment call, matching the "click a block, then click an
// adjacent valid cell" spec): selecting a block/ball shows up to 4 small
// target overlays, one per direction the shape's axis allows (see
// allowedDirections below, same formula as the server's
// motion_challenge._allowed_directions), each positioned on the SPECIFIC
// single cell immediately adjacent to that edge of the block -- clicking
// one submits that direction's move. The client does NOT pre-validate
// occupancy/legality beyond shape-axis filtering (that's server's job,
// per "not optimistic client-side prediction beyond basic UI
// responsiveness") -- an illegal target just comes back invalid=false
// and flashes briefly.
const DEFAULT_POOL_SECONDS = 240;

const DIRECTIONS = ["up", "down", "left", "right"];
const DELTA = { up: [-1, 0], down: [1, 0], left: [0, -1], right: [0, 1] };

function allowedDirections(width, height) {
  const dirs = [];
  if (width > 1 || width === height) dirs.push("left", "right");
  if (height > 1 || width === height) dirs.push("up", "down");
  return dirs;
}

function targetCellFor(row, col, width, height, direction) {
  if (direction === "up") return [row - 1, col];
  if (direction === "down") return [row + height, col];
  if (direction === "left") return [row, col - 1];
  return [row, col + width]; // "right"
}

function describeError(err) {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;
  if (status === 401) return "Not signed in (401) -- this fixture needs a valid auth token for the account that owns it.";
  if (status === 403) return `Not allowed (403)${detail ? `: ${detail}` : ""} -- this puzzle wasn't served to this session.`;
  if (status === 404) return `Not found (404)${detail ? `: ${detail}` : ""} -- likely signed in as a different account than the one that owns this fixture.`;
  if (status) return `Request failed (${status})${detail ? `: ${detail}` : ""}`;
  return err?.message || "Request failed";
}

function formatMMSS(totalSeconds) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function initialBoardState(puzzle) {
  return {
    ballPos: puzzle.ballStart,
    blockPositions: Object.fromEntries((puzzle.blocks || []).map((b) => [b.id, [b.row, b.col]])),
  };
}

const CELL_BASE = "rounded-md shadow-[0_2px_8px_-4px_rgba(0,0,0,0.15)]";

export default function MotionChallengeSection({ puzzles, attemptId, sectionKey, config, onComplete }) {
  const [phase, setPhase] = useState("instructions"); // instructions | playing | done
  const [levelIndex, setLevelIndex] = useState(0);
  const [boardState, setBoardState] = useState(null);
  const [movesUsed, setMovesUsed] = useState(0);
  const [selectedBlockId, setSelectedBlockId] = useState(null);
  const [levelOutcome, setLevelOutcome] = useState(null); // null | "won" | "lost"
  const [invalidDirection, setInvalidDirection] = useState(null); // which target shakes, or null
  const [poolRemaining, setPoolRemaining] = useState(config?.poolSeconds ?? DEFAULT_POOL_SECONDS);
  const [results, setResults] = useState([]); // [{puzzleId, outcome}]
  const [loadError, setLoadError] = useState(null); // request failure message, or null
  const movingRef = useRef(false);
  const finishedRef = useRef(false); // guards against double-firing onComplete
  const levelTokenRef = useRef(0); // bumped on every goToLevel(); guards a stale state-sync response
  const hasMovedRef = useRef(false); // true once a real move/undo has landed for the CURRENT level

  const instructions = config?.instructions || {
    title: "Motion Challenge",
    rule: "Move the colored blocks out of the way to clear a path, then get the red ball into the black hole.",
    scoringNote: "+4 for solving a level within its move budget, -1 if the budget runs out (or time runs out) before you solve it.",
    timerNote: "You have 4 minutes total across all levels -- moves used counts up toward each level's budget.",
  };

  const current = puzzles[levelIndex];
  const currentId = current?.id ?? current?.puzzle_id;

  // Sets the puzzle's pristine start as an OPTIMISTIC placeholder (avoids
  // a blank flash), then immediately syncs to the REAL server-held state
  // -- a level must never be assumed to start fresh on mount. A page
  // reload (or, as caught during Step 4/5 verification, simply
  // re-entering a level that already has moves recorded server-side)
  // would otherwise silently show the wrong board while the server holds
  // the correct one.
  //
  // RACE GUARD (found during the same verification pass, via a real,
  // intermittent repro -- not a hypothetical): if the candidate moves
  // fast enough, a real move's response can land BEFORE this sync fetch
  // resolves. Applying the sync response after that would silently
  // stomp the fresher, already-applied move state back to what the
  // level looked like when the fetch was ISSUED. levelTokenRef guards
  // against a stale response from a since-abandoned level (e.g. rapid
  // level transitions); hasMovedRef guards the more common case of a
  // real move landing first on the SAME level -- once either fires, the
  // sync response is simply discarded, since the move/undo response is
  // always at least as current and is itself server-authoritative.
  // Best-effort otherwise: if the sync call fails outright, the
  // optimistic placeholder stands, and the next real move response
  // corrects it regardless.
  const finishSection = useCallback(() => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    setPhase("done");
  }, []);

  // Takes explicit puzzleId/fromIdx rather than reading currentId/levelIndex
  // from the closure -- needed because goToLevel's state-sync path (below)
  // can discover an already-decided outcome for a level OTHER than the one
  // reflected in this render's closure (e.g. re-entering a level that was
  // already won/lost in a prior visit), and calling this with the stale
  // closure's currentId/levelIndex would record the wrong puzzleId and
  // transition from the wrong index.
  const advanceAfterLevel = (outcome, puzzleId, fromIdx) => {
    setResults((prev) => [...prev, { puzzleId, outcome }]);
    setLevelOutcome(outcome);
    setTimeout(() => {
      setLevelOutcome(null);
      if (fromIdx + 1 < puzzles.length) {
        goToLevel(fromIdx + 1);
      } else {
        finishSection();
      }
    }, 1200);
  };

  const goToLevel = useCallback((idx) => {
    const p = puzzles[idx];
    const pid = p.id ?? p.puzzle_id;
    levelTokenRef.current += 1;
    const myToken = levelTokenRef.current;
    hasMovedRef.current = false;
    setLevelIndex(idx);
    setBoardState(initialBoardState(p));
    setMovesUsed(0);
    setSelectedBlockId(null);

    api
      .post(`/oa/${attemptId}/section/motion-challenge/state`, { section_key: sectionKey, puzzle_id: pid })
      .then(({ data }) => {
        if (levelTokenRef.current !== myToken || hasMovedRef.current) return; // superseded -- discard
        setLoadError(null);
        setBoardState(data.boardState);
        setMovesUsed(data.movesUsed);
        // A level can already be won/lost from a PRIOR visit (page reload,
        // or simply navigating back into it) -- the server-held history is
        // authoritative, so this must be treated as a real outcome, not
        // silently left in interactive mode (which is what let the ball
        // sit invisibly-won on top of the hole with no "Solved!" screen).
        if (data.won) advanceAfterLevel("won", pid, idx);
        else if (data.budgetExhausted) advanceAfterLevel("lost", pid, idx);
      })
      .catch((err) => {
        if (levelTokenRef.current !== myToken || hasMovedRef.current) return; // superseded -- discard
        setLoadError(describeError(err)); // optimistic placeholder stands, but surface why the sync failed
      });
  }, [puzzles, attemptId, sectionKey, advanceAfterLevel]);

  useEffect(() => {
    if (phase !== "done") return;
    const t = setTimeout(() => onComplete?.({}), 1800);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  const handlePlay = () => {
    goToLevel(0);
    setPhase("playing");
  };

  // ONE pooled countdown for the whole section -- starts when play begins,
  // never resets on level transitions.
  useEffect(() => {
    if (phase !== "playing") return;
    const interval = setInterval(() => {
      setPoolRemaining((r) => (r > 0 ? r - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [phase]);

  useEffect(() => {
    if (phase === "playing" && poolRemaining === 0) {
      finishSection(); // pool timer expired mid-level -- stop immediately, don't start/continue another level
    }
  }, [poolRemaining, phase, finishSection]);

  const handleSelectBlock = (id) => {
    if (movingRef.current || levelOutcome) return;
    setSelectedBlockId((prev) => (prev === id ? null : id));
  };

  const handleTargetClick = async (direction) => {
    if (!selectedBlockId || movingRef.current || levelOutcome) return;
    movingRef.current = true;
    try {
      const blockId = selectedBlockId === "ball" ? null : selectedBlockId;
      const { data } = await api.post(`/oa/${attemptId}/section/motion-challenge/move`, {
        section_key: sectionKey, puzzle_id: currentId, blockId, direction,
      });
      setLoadError(null);
      if (data.valid) {
        hasMovedRef.current = true; // a real move landed -- any in-flight state-sync response is now stale
        setBoardState(data.boardState);
        setMovesUsed(data.movesUsed);
        setSelectedBlockId(null);
        if (data.won) advanceAfterLevel("won", currentId, levelIndex);
        else if (data.budgetExhausted) advanceAfterLevel("lost", currentId, levelIndex);
      } else {
        // Shake the specific target cell that was clicked -- localized
        // "that didn't work" feedback rather than the whole board, so a
        // candidate probing multiple directions can tell exactly which
        // one just failed. Purely client-side CSS (see tailwind.config.js's
        // `shake` keyframe); no backend involvement.
        setInvalidDirection(direction);
        setTimeout(() => setInvalidDirection(null), 400);
        if (data.budgetExhausted) advanceAfterLevel("lost", currentId, levelIndex);
      }
    } catch (err) {
      setLoadError(describeError(err));
    } finally {
      movingRef.current = false;
    }
  };

  const handleUndo = async () => {
    if (movesUsed === 0 || movingRef.current || levelOutcome) return;
    movingRef.current = true;
    try {
      const { data } = await api.post(`/oa/${attemptId}/section/motion-challenge/undo`, {
        section_key: sectionKey, puzzle_id: currentId,
      });
      setLoadError(null);
      hasMovedRef.current = true; // same race guard as a real move -- see goToLevel's comment
      setBoardState(data.boardState);
      setMovesUsed(data.movesUsed);
      setSelectedBlockId(null);
    } catch (err) {
      setLoadError(describeError(err));
    } finally {
      movingRef.current = false;
    }
  };

  if (phase === "instructions") {
    return (
      <div className="pm-card p-8 max-w-lg mx-auto text-center">
        <div className="text-xs pm-eyebrow tracking-widest text-pm-primary-dark mb-2">Gamified Round</div>
        <h2 className="font-display text-2xl font-bold mb-4">{instructions.title}</h2>
        <p className="text-pm-text2 mb-6">{instructions.rule}</p>
        <div className="flex flex-col gap-3 text-left mb-8">
          <div className="flex items-center gap-3 text-sm text-pm-text2">
            <Target size={16} className="text-pm-primary shrink-0" /> {instructions.scoringNote}
          </div>
          <div className="flex items-center gap-3 text-sm text-pm-text2">
            <Clock size={16} className="text-pm-primary shrink-0" /> {instructions.timerNote}
          </div>
        </div>
        <button onClick={handlePlay} className="pm-btn pm-btn-primary inline-flex items-center gap-2 px-6 py-3">
          <Play size={16} /> Play
        </button>
      </div>
    );
  }

  if (phase === "done") {
    const solved = results.filter((r) => r.outcome === "won").length;
    return (
      <div className="pm-card p-8 max-w-lg mx-auto text-center">
        <div className="font-display text-lg font-semibold mb-4">Motion Challenge complete</div>
        <div className="flex justify-center gap-3 mb-4">
          {puzzles.map((p, i) => {
            const r = results[i];
            return (
              <div
                key={p.id ?? p.puzzle_id}
                className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ${
                  r?.outcome === "won" ? "bg-[var(--pm-teal-deep)]" : r ? "bg-pm-secondary" : "bg-[#D8D3C4]"
                }`}
              >
                {i + 1}
              </div>
            );
          })}
        </div>
        <div className="text-sm text-pm-text2">{solved} of {puzzles.length} levels solved</div>
      </div>
    );
  }

  if (!current || !boardState) return null;

  const { rows, cols } = current;
  const wallSet = new Set((current.walls || []).map(([r, c]) => `${r},${c}`));
  const [holeR, holeC] = current.hole;
  const selectedBlock = current.blocks.find((b) => b.id === selectedBlockId);
  const isBallSelected = selectedBlockId === "ball";

  // Everything here (walls, every block's current position, the ball's
  // current position) is already fully visible on the board -- nothing
  // secret, unlike grid_challenge -- so it's safe to pre-filter out
  // target cells that can NEVER succeed (occupied by a wall, another
  // block, or the ball) instead of showing a target overlay stacked on
  // top of an obstruction. The server remains the sole source of truth
  // for whether a move is actually legal; this only removes overlays
  // that are deterministically pointless given data the client already has.
  const occupiedSet = new Set(wallSet);
  current.blocks.forEach((b) => {
    if (b.id === selectedBlockId) return; // the selected block's own cells never block its own targets
    const [br, bc] = boardState.blockPositions[b.id];
    for (let dr = 0; dr < b.height; dr++) {
      for (let dc = 0; dc < b.width; dc++) occupiedSet.add(`${br + dr},${bc + dc}`);
    }
  });
  if (!isBallSelected) occupiedSet.add(`${boardState.ballPos[0]},${boardState.ballPos[1]}`);

  let targets = [];
  if (selectedBlock) {
    const anchor = boardState.blockPositions[selectedBlock.id];
    targets = allowedDirections(selectedBlock.width, selectedBlock.height).map((d) => ({
      direction: d, cell: targetCellFor(anchor[0], anchor[1], selectedBlock.width, selectedBlock.height, d),
    }));
  } else if (isBallSelected) {
    targets = DIRECTIONS.map((d) => ({
      direction: d, cell: [boardState.ballPos[0] + DELTA[d][0], boardState.ballPos[1] + DELTA[d][1]],
    }));
  }
  targets = targets.filter(
    (t) =>
      t.cell[0] >= 0 && t.cell[0] < rows && t.cell[1] >= 0 && t.cell[1] < cols &&
      !occupiedSet.has(`${t.cell[0]},${t.cell[1]}`)
  );

  return (
    <div>
      {loadError && (
        <div className="mb-3 px-4 py-2.5 rounded-lg bg-[rgba(11,42,48,0.06)] border border-[rgba(11,42,48,0.15)] text-pm-text text-sm flex items-center justify-between gap-3">
          <span>{loadError}</span>
          <button onClick={() => setLoadError(null)} className="text-pm-text2 hover:text-pm-text shrink-0">&times;</button>
        </div>
      )}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="pm-chip text-xs">LEVEL {levelIndex + 1} OF {puzzles.length}</div>
        <div className="flex items-center gap-4">
          <div className="text-xs font-display tabular-nums text-pm-text2">{movesUsed} / {current.moveBudget} moves</div>
          <div className={`flex items-center gap-1.5 font-display tabular-nums text-xs font-semibold ${poolRemaining <= 30 ? "text-pm-secondary" : "text-pm-text2"}`}>
            <Clock size={14} /> {formatMMSS(poolRemaining)}
          </div>
        </div>
      </div>

      <div className="pm-card p-6">
        {levelOutcome ? (
          <div className="py-10 text-center">
            {levelOutcome === "won" ? (
              <>
                <CheckCircle2 className="mx-auto text-emerald-600 mb-2" size={32} />
                <div className="font-display text-lg font-semibold">Solved!</div>
              </>
            ) : (
              <>
                <XCircle className="mx-auto text-pm-secondary mb-2" size={32} />
                <div className="font-display text-lg font-semibold">Out of moves</div>
              </>
            )}
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-4">
              <div className="font-display text-sm font-semibold">
                {selectedBlockId ? "Pick a direction to move it" : "Select a block or the ball to move"}
              </div>
              <button
                data-testid={TID.motionUndo}
                onClick={handleUndo}
                disabled={movesUsed === 0 || movingRef.current}
                className="pm-btn pm-btn-ghost text-xs py-1.5 px-3 inline-flex items-center gap-1.5 disabled:opacity-40"
              >
                <Undo2 size={14} /> Undo
              </button>
            </div>

            <div
              className="relative mx-auto max-w-md"
              style={{
                display: "grid",
                gridTemplateColumns: `repeat(${cols}, 1fr)`,
                gridTemplateRows: `repeat(${rows}, 1fr)`,
                gap: "6px",
                aspectRatio: `${cols} / ${rows}`,
              }}
            >
              {Array.from({ length: rows }).map((_, r) =>
                Array.from({ length: cols }).map((_, c) => {
                  const isWall = wallSet.has(`${r},${c}`);
                  return (
                    <div
                      key={`bg-${r}-${c}`}
                      style={{ gridColumn: `${c + 1} / span 1`, gridRow: `${r + 1} / span 1` }}
                      className={`${CELL_BASE} flex items-center justify-center ${
                        isWall ? "bg-[#2C2C2C]" : "bg-white"
                      }`}
                    >
                      {isWall && <span className="text-[#C4C4C4] text-xs font-bold">&times;</span>}
                    </div>
                  );
                })
              )}

              {current.blocks.map((b) => {
                const [r, c] = boardState.blockPositions[b.id];
                return (
                  <button
                    key={b.id}
                    data-testid={TID.motionBlock(currentId, b.id)}
                    onClick={() => handleSelectBlock(b.id)}
                    style={{
                      gridColumn: `${c + 1} / span ${b.width}`,
                      gridRow: `${r + 1} / span ${b.height}`,
                      backgroundColor: b.color,
                    }}
                    className={`rounded-lg transition ${
                      selectedBlockId === b.id ? "ring-4 ring-white ring-offset-2 ring-offset-[#FAF8F3]" : ""
                    }`}
                  />
                );
              })}

              <button
                data-testid={TID.motionBall(currentId)}
                onClick={() => handleSelectBlock("ball")}
                style={{
                  gridColumn: `${boardState.ballPos[1] + 1} / span 1`,
                  gridRow: `${boardState.ballPos[0] + 1} / span 1`,
                }}
                className="flex items-center justify-center"
              >
                <div className={`w-2/3 h-2/3 rounded-full bg-[#C0392B] ${isBallSelected ? "ring-4 ring-white" : ""}`} />
              </button>

              {targets.map((t) => {
                const isInvalid = t.direction === invalidDirection;
                return (
                  <button
                    key={t.direction}
                    data-testid={TID.motionTarget(currentId, t.direction)}
                    onClick={() => handleTargetClick(t.direction)}
                    style={{ gridColumn: `${t.cell[1] + 1} / span 1`, gridRow: `${t.cell[0] + 1} / span 1` }}
                    className={`flex items-center justify-center z-10 ${isInvalid ? "animate-shake" : ""}`}
                  >
                    <div
                      className={`w-1/2 h-1/2 rounded-full border-2 ${
                        isInvalid
                          ? "bg-pm-secondary/50 border-pm-secondary"
                          : "bg-pm-primary/40 border-pm-primary animate-pulse"
                      }`}
                    />
                  </button>
                );
              })}

              {/* Always rendered on its own top layer (highest z-index,
                  non-interactive) instead of only in the floor background --
                  a block or the ball can legitimately sit on the hole's
                  cell (both as a starting layout and as the winning move),
                  and the goal must stay visibly marked either way instead
                  of being fully hidden underneath whatever's occupying it. */}
              <div
                style={{ gridColumn: `${holeC + 1} / span 1`, gridRow: `${holeR + 1} / span 1` }}
                className="flex items-center justify-center pointer-events-none z-20"
              >
                <div className="w-2/5 h-2/5 rounded-full bg-black border-2 border-white shadow-[0_0_0_1px_rgba(0,0,0,0.5)]" />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
