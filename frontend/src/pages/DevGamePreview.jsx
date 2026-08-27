import React, { useState, useRef } from "react";
import Header from "../components/Header";
import DeductiveGridSection from "../components/games/DeductiveGridSection";

// Standing dev tool (not temporary) -- unauthenticated preview route at
// /dev/game-preview for visually confirming gamified-round components
// against their public-safe (post strip_answer()) schema. These 3 puzzles
// are real output from deductive_grid.generate_puzzle() (one per grid
// size, seed="shape-fix-preview-seed", each independently re-verified via
// verify_puzzle() before being hardcoded here), not hand-drawn mockups --
// generated AFTER the shape-only symbol fix (5 shapes: circle/square/
// triangle/cross/diamond, each with exactly one fixed color; color is no
// longer a second, independently-varying axis of meaning). Rendered
// through the full flow wrapper (instructions -> sub-puzzle 1..3 -> done).
const SAMPLE_PUZZLES = [
  {
    id: "preview-3x3",
    gridSize: 3,
    grid: [
      [null, null, null],
      [null, { shape: "square", color: "olive" }, null],
      [{ shape: "square", color: "olive" }, null, { shape: "diamond", color: "amber" }],
    ],
    targetCell: { row: 2, col: 1 },
    options: [{ shape: "diamond", color: "amber" }, { shape: "square", color: "olive" }, { shape: "triangle", color: "brick" }],
  },
  {
    id: "preview-4x4",
    gridSize: 4,
    grid: [
      [null, null, { shape: "cross", color: "plum" }, null],
      [null, null, { shape: "diamond", color: "amber" }, null],
      [null, null, null, null],
      [null, { shape: "cross", color: "plum" }, null, { shape: "diamond", color: "amber" }],
    ],
    targetCell: { row: 3, col: 2 },
    options: [{ shape: "cross", color: "plum" }, { shape: "square", color: "olive" }, { shape: "diamond", color: "amber" }],
  },
  {
    id: "preview-5x5",
    gridSize: 5,
    grid: [
      [null, null, null, null, null],
      [null, null, null, null, null],
      [{ shape: "circle", color: "navy" }, null, null, null, null],
      [null, { shape: "diamond", color: "amber" }, null, { shape: "cross", color: "plum" }, { shape: "circle", color: "navy" }],
      [{ shape: "diamond", color: "amber" }, null, null, null, null],
    ],
    targetCell: { row: 3, col: 0 },
    options: [{ shape: "triangle", color: "brick" }, { shape: "circle", color: "navy" }, { shape: "diamond", color: "amber" }],
  },
];

const SAMPLE_CONFIG = {
  timerPerPuzzle: 15,
  instructions: {
    title: "Deductive Grid",
    rule: "Neither a row nor a column should have similar symbols.",
    scoringNote: "+1 for a correct answer, -1 for an incorrect answer or a time out.",
    timerNote: "You have 15 seconds per puzzle.",
  },
};

export default function DevGamePreview() {
  const [completedAnswers, setCompletedAnswers] = useState(null);
  const [runKey, setRunKey] = useState(0);
  const scoreRef = useRef(0);

  // Dev-only mock -- the real onCheckAnswer hits POST /oa/{attemptId}/section/check,
  // which knows the puzzle's real correctAnswer server-side. This preview has
  // no attemptId/backend session, and SAMPLE_PUZZLES intentionally carries no
  // correctAnswer (matches the real strip_answer() shape), so there's nothing
  // genuine to check against -- this just SIMULATES a plausible correct/wrong
  // split so the running-score bar can be previewed visually. Not real grading.
  const mockCheckAnswer = async (_puzzleId, result) => {
    const isCorrect = !result.timedOut && Math.random() > 0.4;
    scoreRef.current += isCorrect ? 1 : -1;
    return { correct: isCorrect, pointsAwarded: isCorrect ? 1 : -1, runningScore: scoreRef.current };
  };

  return (
    <div>
      <Header />
      <div className="max-w-3xl mx-auto px-6 py-10">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-1">dev preview · not a real route</div>
        <h1 className="font-display text-2xl font-bold mb-6">Deductive Grid — full flow preview (instructions → 3x3 → 4x4 → 5x5)</h1>

        {completedAnswers ? (
          <div className="pm-card p-6">
            <div className="font-display text-lg font-semibold mb-3">Session complete</div>
            <pre className="text-xs font-mono bg-pm-muted rounded-lg p-4 overflow-auto">
              {JSON.stringify(completedAnswers, null, 2)}
            </pre>
            <button
              className="pm-btn pm-btn-ghost mt-4 text-sm py-2 px-4"
              onClick={() => { setCompletedAnswers(null); setRunKey((k) => k + 1); scoreRef.current = 0; }}
            >
              Restart preview
            </button>
          </div>
        ) : (
          <DeductiveGridSection
            key={runKey}
            puzzles={SAMPLE_PUZZLES}
            config={SAMPLE_CONFIG}
            onComplete={setCompletedAnswers}
            onCheckAnswer={mockCheckAnswer}
          />
        )}
      </div>
    </div>
  );
}
