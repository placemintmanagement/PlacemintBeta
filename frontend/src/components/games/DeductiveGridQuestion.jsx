import React, { useEffect, useRef, useState } from "react";
import { HelpCircle, Clock } from "lucide-react";
import { TID } from "../../testIds";

// Muted palette (not saturated primary colors) -- "brick" reuses the
// product's existing coral-dark token (#B23E23, also used in pm-chip-coral
// and the DI chart palette) so this ties into the same visual language
// instead of introducing an unrelated red. Keys match deductive_grid.py's
// SHAPE_COLORS values exactly -- color is now a FIXED 1:1 lookup per shape
// (never chosen independently), so two puzzles never show the same shape
// in two different colors, which would be ambiguous to a candidate
// glancing at shape alone.
const SHAPE_COLORS = {
  olive: "#6F7D3C",   // square
  brick: "#B23E23",   // triangle
  navy: "#2C3E56",    // circle
  plum: "#6B4E71",    // cross
  amber: "#A6752C",   // diamond
};

// Tailwind's JIT scanner needs literal class strings present in source --
// can't interpolate `grid-cols-${n}` at runtime, so this lookup is required
// for the 3 supported grid sizes.
const GRID_COLS_CLASS = { 3: "grid-cols-3", 4: "grid-cols-4", 5: "grid-cols-5" };

const DEFAULT_SECONDS_PER_PUZZLE = 15;

function ShapeIcon({ shape, color, size = 32 }) {
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
  if (shape === "diamond") {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <polygon points="16,3 29,16 16,29 3,16" fill={fill} />
      </svg>
    );
  }
  return null;
}

// White rounded card, permanent soft shadow, no border -- deliberately NOT
// .pm-card (that has a visible border and only shadows on hover; the grid
// spec calls for a resting soft shadow and zero border on every cell,
// including empty/unrevealed ones, so a sparse grid still reads as "part
// of the grid" not "missing/broken").
const CELL_BASE = "bg-white rounded-xl shadow-[0_6px_20px_-8px_rgba(0,0,0,0.12)] flex items-center justify-center";

function GridCell({ cell, isTarget }) {
  return (
    <div className={`${CELL_BASE} aspect-square`}>
      {isTarget ? (
        <HelpCircle size={28} strokeWidth={1.75} className="text-pm-text2/50" />
      ) : cell ? (
        <ShapeIcon shape={cell.shape} color={cell.color} />
      ) : null}
    </div>
  );
}

// question shape (public-safe, post strip_answer()): { id|puzzle_id,
// gridSize: 3|4|5, grid: NxN of {shape,color}|null (sparse -- most cells
// are null), targetCell: {row,col}, options: [{shape,color} x3] } --
// never includes correctAnswer; grading happens server-side.
//
// Single-subpart view: owns its own 15s countdown and fires onAnswer
// exactly once (on selection OR on timeout), then locks. The flow wrapper
// (DeductiveGridSection) is what auto-advances to the next sub-puzzle --
// this component has no "next" button and no way to go back.
export default function DeductiveGridQuestion({
  question, index, total, onAnswer, secondsPerPuzzle = DEFAULT_SECONDS_PER_PUZZLE,
}) {
  const q = question;
  const qid = q.id ?? q.puzzle_id;
  const n = q.gridSize;
  const { row: tr, col: tc } = q.targetCell;
  const [remaining, setRemaining] = useState(secondsPerPuzzle);
  const [locked, setLocked] = useState(false);
  const startRef = useRef(Date.now());
  const onAnswerRef = useRef(onAnswer);
  onAnswerRef.current = onAnswer;

  useEffect(() => {
    setRemaining(secondsPerPuzzle);
    setLocked(false);
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

  const handleSelect = (ix) => {
    if (locked) return;
    setLocked(true);
    onAnswerRef.current(qid, { selected: ix, timedOut: false, timeTakenMs: Date.now() - startRef.current });
  };

  return (
    <div className="pm-card p-6">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-mono uppercase text-pm-text2">
          Q{index + 1} of {total} · Deductive Grid
        </div>
        <div className={`flex items-center gap-1.5 font-mono text-xs font-semibold ${remaining <= 5 ? "text-pm-secondary" : "text-pm-text2"}`}>
          <Clock size={14} />
          00:{String(remaining).padStart(2, "0")}
        </div>
      </div>
      <div className="font-display text-lg font-semibold mb-4">
        Neither a row nor a column should have similar symbols. Which symbol fits?
      </div>

      <div className="max-w-sm">
        <div className={`grid ${GRID_COLS_CLASS[n] || "grid-cols-3"} gap-3 sm:gap-4 pb-5 border-b border-pm-border`}>
          {q.grid.map((rowCells, r) =>
            rowCells.map((cell, c) => (
              <GridCell key={`${r}-${c}`} cell={cell} isTarget={r === tr && c === tc} />
            ))
          )}
        </div>

        <div className="text-xs font-mono uppercase text-pm-text2 mt-5 mb-3">Pick the missing symbol</div>
        <div className="flex flex-row gap-3">
          {(q.options || []).map((opt, ix) => (
            <button
              key={ix}
              data-testid={TID.oaQuestionOption(qid, ix)}
              onClick={() => handleSelect(ix)}
              disabled={locked}
              className={`${CELL_BASE} flex-1 py-5 px-4 transition disabled:opacity-60`}
            >
              <ShapeIcon shape={opt.shape} color={opt.color} size={36} />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
