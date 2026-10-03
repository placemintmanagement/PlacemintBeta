import React, { useState, useRef } from "react";
import Header from "../components/Header";
import SwitchChallengeSection from "../components/games/SwitchChallengeSection";

// Standing dev tool (not temporary) -- unauthenticated preview route at
// /dev/switch-preview for visually confirming switch_challenge before it's
// wired into the real OA flow. These 5 puzzles are real output from
// switch_challenge.generate_puzzle() (seed="switch-devpreview-seed"), each
// independently re-verified via verify_puzzle() before being hardcoded
// here -- not hand-drawn mockups. Not yet inserted into puzzle_bank.
const SAMPLE_PUZZLES = [
  { id: "preview-sc-1", topRow: ["triangle", "square", "circle", "cross"], bottomRow: ["triangle", "circle", "square", "cross"], options: ["2314", "3124", "1432", "1324"] },
  { id: "preview-sc-2", topRow: ["circle", "square", "cross", "triangle"], bottomRow: ["circle", "triangle", "cross", "square"], options: ["2431", "1432", "4213", "2341"] },
  { id: "preview-sc-3", topRow: ["cross", "square", "triangle", "circle"], bottomRow: ["square", "cross", "circle", "triangle"], options: ["1342", "2143", "2314", "3124"] },
  { id: "preview-sc-4", topRow: ["triangle", "circle", "square", "cross"], bottomRow: ["square", "cross", "triangle", "circle"], options: ["1243", "1423", "3412", "4231"] },
  { id: "preview-sc-5", topRow: ["triangle", "square", "cross", "circle"], bottomRow: ["circle", "square", "cross", "triangle"], options: ["3214", "4213", "4231", "1342"] },
];

const SAMPLE_CONFIG = {
  timerPerPuzzle: 20,
  instructions: {
    title: "Switch Challenge",
    rule: "Figure out which input position each output symbol came from, and pick the matching 4-digit sequence.",
    scoringNote: "+3 for a correct answer, -1 for an incorrect answer or a time out.",
    timerNote: "You have 20 seconds per puzzle.",
  },
};

// Unlike deductive_grid, nothing is hidden in switch_challenge -- the
// correct answer is a pure function of topRow/bottomRow, so this preview
// can compute REAL correctness locally (this mirrors switch_challenge.py's
// solve_puzzle logic, kept deliberately simple/standalone here since it's
// preview-only, not a security boundary -- the real app never does this
// client-side, it always asks the server).
function realCorrectAnswer(topRow, bottomRow) {
  const position = {};
  topRow.forEach((shape, i) => { position[shape] = i + 1; });
  return bottomRow.map((shape) => position[shape]).join("");
}

export default function DevSwitchChallengePreview() {
  const [completedAnswers, setCompletedAnswers] = useState(null);
  const [runKey, setRunKey] = useState(0);
  const scoreRef = useRef(0);

  const mockCheckAnswer = async (puzzleId, result) => {
    const puzzle = SAMPLE_PUZZLES.find((p) => p.id === puzzleId);
    const trueAnswer = realCorrectAnswer(puzzle.topRow, puzzle.bottomRow);
    const chosenValue = result.selected != null ? puzzle.options[result.selected] : null;
    const isCorrect = !result.timedOut && chosenValue === trueAnswer;
    const points = isCorrect ? 3 : -1;
    scoreRef.current += points;
    return { correct: isCorrect, pointsAwarded: points, runningScore: scoreRef.current };
  };

  return (
    <div>
      <Header />
      <div className="max-w-3xl mx-auto px-6 py-10">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-1">dev preview · not a real route</div>
        <h1 className="font-display text-2xl font-bold mb-6">Switch Challenge: full flow preview</h1>

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
          <SwitchChallengeSection
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
