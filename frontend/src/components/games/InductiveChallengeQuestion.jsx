import React, { useEffect, useRef, useState } from "react";
import { Clock, ArrowDown, Check } from "lucide-react";
import { TID } from "../../testIds";

// Matches deductive_grid.SHAPE_COLORS / inductive_challenge.py's
// SHAPE_COLORS exactly for the 4 shapes this type uses. Self-contained (no
// cross-import from DeductiveGridQuestion), same convention every other
// game-type frontend file in this suite follows -- each type owns its own
// rendering.
const SHAPE_COLORS = {
  navy: "#2C3E56",   // circle
  olive: "#6F7D3C",  // square
  brick: "#B23E23",  // triangle
  plum: "#6B4E71",   // cross
};

const DEFAULT_SECONDS_PER_PUZZLE = 30;

function ShapeIcon({ shape, color, size = 22 }) {
  const fill = SHAPE_COLORS[color] || "#4B5563";
  if (shape === "circle") {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <circle cx="16" cy="16" r="12" fill={fill} />
      </svg>
    );
  }
  if (shape === "square") {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <rect x="5" y="5" width="22" height="22" rx="4" fill={fill} />
      </svg>
    );
  }
  if (shape === "triangle") {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <polygon points="16,4 28,27 4,27" fill={fill} />
      </svg>
    );
  }
  if (shape === "cross") {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <polygon points="12,4 20,4 20,12 28,12 28,20 20,20 20,28 12,28 12,20 4,20 4,12 12,12" fill={fill} />
      </svg>
    );
  }
  return null;
}

// Compact 3x3 grid -- unlike deductive_grid's cell-per-symbol tiles (built
// to be the sole focus of the screen), up to 6 of these render on screen at
// once here (demo before/after + 4 candidates), so cells stay small and
// every cell is always filled (no sparse/target-cell reveal -- the whole
// point is comparing two fully-visible grids).
function MiniGrid({ grid }) {
  return (
    <div className="inline-grid grid-cols-3 gap-1 bg-white rounded-lg p-2 shadow-[0_6px_20px_-8px_rgba(0,0,0,0.12)]">
      {grid.map((row, r) =>
        row.map((cell, c) => (
          <div key={`${r}-${c}`} className="w-7 h-7 flex items-center justify-center">
            <ShapeIcon shape={cell.shape} color={cell.color} />
          </div>
        ))
      )}
    </div>
  );
}

// question shape (public-safe, post strip_answer()): { id|puzzle_id,
// demoBefore: 3x3 of {shape,color}, demoAfter: 3x3 of {shape,color},
// candidates: [4x (3x3 of {shape,color})] } -- never includes
// correctAnswer (a 2-element index list); grading happens server-side.
//
// Single-subpart view: owns its own 30s countdown and fires onAnswer
// exactly once, then locks -- same contract as DeductiveGridQuestion/
// SwitchChallengeQuestion, just with a 2-element `selected` array instead
// of a single index (matches game_types._pair_answer_check's expected
// shape). The flow wrapper (InductiveChallengeSection) owns the level
// badge / running-score bar and auto-advance, same division of
// responsibility as the other two flat-list types.
//
// SELECTION UX (judgment call, flagged per your ask): clicking an
// unselected candidate adds it (up to 2); clicking an already-selected one
// deselects it. As soon as a SECOND candidate is picked, this locks and
// submits immediately -- no separate "Submit" button, matching every other
// type in this suite's click-to-commit pattern. There's no "swap out the
// oldest pick" behavior to reason about: since submission is immediate on
// reaching 2, a 3rd click is simply ignored until the candidate set locks
// (which happens right away) rather than silently replacing a prior pick.
export default function InductiveChallengeQuestion({
  question, index, total, onAnswer, secondsPerPuzzle = DEFAULT_SECONDS_PER_PUZZLE,
}) {
  const q = question;
  const qid = q.id ?? q.puzzle_id;
  const [remaining, setRemaining] = useState(secondsPerPuzzle);
  const [locked, setLocked] = useState(false);
  const [selected, setSelected] = useState([]);
  const startRef = useRef(Date.now());
  const onAnswerRef = useRef(onAnswer);
  onAnswerRef.current = onAnswer;

  useEffect(() => {
    setRemaining(secondsPerPuzzle);
    setLocked(false);
    setSelected([]);
    startRef.current = Date.now();
    const interval = setInterval(() => {
      setRemaining((r) => (r > 0 ? r - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qid, secondsPerPuzzle]);

  useEffect(() => {
    if (remaining === 0 && !locked) {
      setLocked(true);
      onAnswerRef.current(qid, { selected: null, timedOut: true, timeTakenMs: Date.now() - startRef.current });
    }
  }, [remaining, locked, qid]);

  useEffect(() => {
    if (selected.length === 2 && !locked) {
      setLocked(true);
      const ordered = [...selected].sort((a, b) => a - b);
      onAnswerRef.current(qid, { selected: ordered, timedOut: false, timeTakenMs: Date.now() - startRef.current });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, locked, qid]);

  const handleToggle = (ix) => {
    if (locked) return;
    setSelected((prev) => {
      if (prev.includes(ix)) return prev.filter((x) => x !== ix);
      if (prev.length < 2) return [...prev, ix];
      return prev; // already 2 picked -- ignore a 3rd click until it locks
    });
  };

  return (
    <div className="pm-card p-6">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-mono uppercase text-pm-text2">
          Q{index + 1} of {total} · Inductive Challenge
        </div>
        <div className={`flex items-center gap-1.5 font-mono text-xs font-semibold ${remaining <= 5 ? "text-pm-secondary" : "text-pm-text2"}`}>
          <Clock size={14} />
          00:{String(remaining).padStart(2, "0")}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
        <div>
          <div className="font-display text-sm font-semibold mb-3">These two grids follow a rule.</div>
          <div className="flex flex-col items-center gap-2 bg-pm-muted rounded-xl p-4">
            <MiniGrid grid={q.demoBefore} />
            <ArrowDown size={16} className="text-pm-text2 my-1" />
            <MiniGrid grid={q.demoAfter} />
          </div>
        </div>

        <div>
          <div className="font-display text-sm font-semibold mb-3">
            Which two of these grids follow the same rule?
          </div>
          <div className="grid grid-cols-2 gap-3">
            {(q.candidates || []).map((cand, ix) => {
              const isSelected = selected.includes(ix);
              const pickNumber = selected.indexOf(ix) + 1;
              const isDisabled = locked || (selected.length === 2 && !isSelected);
              return (
                <button
                  key={ix}
                  data-testid={TID.oaQuestionOption(qid, ix)}
                  onClick={() => handleToggle(ix)}
                  disabled={isDisabled}
                  className={`relative flex items-center justify-center p-3 rounded-xl border-2 transition disabled:opacity-60 ${
                    isSelected ? "border-pm-primary bg-pm-primary/5" : "border-transparent bg-pm-muted"
                  }`}
                >
                  <MiniGrid grid={cand} />
                  {isSelected && (
                    <div className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-pm-primary text-white text-[10px] font-bold flex items-center justify-center">
                      {pickNumber}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
          <div className="text-xs font-mono text-pm-text2 mt-3 flex items-center gap-1.5">
            {selected.length === 2 ? (
              <>
                <Check size={13} className="text-pm-primary" /> 2 of 2 selected
              </>
            ) : (
              `${selected.length} of 2 selected`
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
