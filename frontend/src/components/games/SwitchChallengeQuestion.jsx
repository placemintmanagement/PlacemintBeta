import React, { useEffect, useRef, useState } from "react";
import { Clock } from "lucide-react";
import { TID } from "../../testIds";

// ALL shapes share ONE single fixed color -- unlike deductive_grid, shape
// type alone carries meaning here, matching the reference exactly. Reuses
// deductive_grid's navy token (per confirmed decision) but this file is
// deliberately self-contained (no cross-import from DeductiveGridQuestion)
// so the two game types stay independent, matching the registry pattern
// where each game type owns its own frontend component.
const SHAPE_COLOR = "#2C3E56"; // navy

const DEFAULT_SECONDS_PER_PUZZLE = 20;

function ShapeIcon({ shape, size = 30 }) {
  if (shape === "circle") {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <circle cx="16" cy="16" r="12" fill={SHAPE_COLOR} />
      </svg>
    );
  }
  if (shape === "square") {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <rect x="5" y="5" width="22" height="22" rx="4" fill={SHAPE_COLOR} />
      </svg>
    );
  }
  if (shape === "triangle") {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <polygon points="16,4 28,27 4,27" fill={SHAPE_COLOR} />
      </svg>
    );
  }
  if (shape === "cross") {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <polygon points="12,4 20,4 20,12 28,12 28,20 20,20 20,28 12,28 12,20 4,20 4,12 12,12" fill={SHAPE_COLOR} />
      </svg>
    );
  }
  return null;
}

// White rounded card, soft shadow, no border -- same base tokens as
// deductive_grid (confirmed to carry over), sitting on top of THIS game's
// own blue-gradient canvas rather than the plain #FAF8F3 page background.
const CELL_BASE = "bg-white rounded-xl shadow-[0_6px_20px_-8px_rgba(0,0,0,0.12)] flex items-center justify-center";

// question shape (public-safe, post strip_answer()): { id|puzzle_id,
// topRow: [shape x4], bottomRow: [shape x4], options: [digitString x4] } --
// never includes correctAnswer; grading happens server-side.
//
// Single-subpart view: owns its own 20s countdown and fires onAnswer
// exactly once (on selection or timeout), then locks. Level badge / running
// progress bar live in the flow wrapper (SwitchChallengeSection), since
// those are session-level, not per-puzzle.
export default function SwitchChallengeQuestion({
  question, index, total, onAnswer, secondsPerPuzzle = DEFAULT_SECONDS_PER_PUZZLE,
}) {
  const q = question;
  const qid = q.id ?? q.puzzle_id;
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
    <div
      className="rounded-2xl p-6"
      style={{ background: "linear-gradient(135deg, #DCEBFA 0%, #B9D9F2 100%)" }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs font-mono uppercase text-[#2C3E56]/70">
          Q{index + 1} of {total} · Switch Challenge
        </div>
        <div className={`flex items-center gap-1.5 font-mono text-xs font-semibold ${remaining <= 5 ? "text-pm-secondary" : "text-[#2C3E56]"}`}>
          <Clock size={14} />
          00:{String(remaining).padStart(2, "0")}
        </div>
      </div>

      <div className="pm-card p-6">
        <div className="font-display text-base font-semibold mb-5 text-center">
          Which digit sequence maps the input to the output?
        </div>

        <div className="text-[11px] font-mono uppercase text-pm-text2 mb-2 text-center">Input</div>
        <div className="flex justify-center gap-4 mb-6">
          {q.topRow.map((shape, i) => (
            <ShapeCellLight key={i} shape={shape} positionLabel={i + 1} />
          ))}
        </div>

        <div className="text-[11px] font-mono uppercase text-pm-text2 mb-2 text-center">Output</div>
        <div className="flex justify-center gap-4 mb-6">
          {q.bottomRow.map((shape, i) => (
            <ShapeCellLight key={i} shape={shape} />
          ))}
        </div>

        <div className="border-t border-pm-border pt-5">
          <div className="text-xs font-mono uppercase text-pm-text2 mb-3 text-center">Pick the matching sequence</div>
          <div className="flex justify-center gap-3">
            {(q.options || []).map((opt, ix) => (
              <button
                key={ix}
                data-testid={TID.oaQuestionOption(qid, ix)}
                onClick={() => handleSelect(ix)}
                disabled={locked}
                className={`${CELL_BASE} px-5 py-4 font-mono text-lg font-bold tracking-widest transition disabled:opacity-60`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Position-label variant used on the light pm-card body (dark navy label
// text reads fine on white, unlike the white-on-gradient variant above).
function ShapeCellLight({ shape, positionLabel }) {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className={`${CELL_BASE} w-16 h-16`}>
        <ShapeIcon shape={shape} />
      </div>
      {positionLabel != null && (
        <div className="font-mono text-xs font-semibold text-pm-text2">{positionLabel}</div>
      )}
    </div>
  );
}
