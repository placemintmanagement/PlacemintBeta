import React, { useState } from "react";
import { Play, Clock, Zap } from "lucide-react";
import SwitchChallengeQuestion from "./SwitchChallengeQuestion";

// switch_challenge's own known scoring ratio (+3/-1, confirmed) -- not a
// secret, it's already shown verbatim in the instructions screen text
// below. Used only to size the progress bar's 100% mark (puzzles.length *
// POINTS_CORRECT); the actual per-answer point values always come from the
// server via onCheckAnswer, never computed client-side.
const POINTS_CORRECT = 3;

// Standalone flow wrapper, same shape as DeductiveGridSection but with its
// own fresh header (level badge + running-score bar + timer) per spec --
// not a reuse of deductive_grid's header.
//
// Props: puzzles, config, onComplete(answers) -- same as before.
// onCheckAnswer(puzzleId, {selected,timedOut,timeTakenMs}) -> Promise<{correct,
//   pointsAwarded, runningScore}>, called once per answer for LIVE feedback
//   only. If omitted, the bar falls back to a plain answered/total display.
// The final onComplete(answers) call (and the server's grade_session it
// leads to) remain the sole source of truth for the actual score --
// onCheckAnswer failures are swallowed and never block advancing.
export default function SwitchChallengeSection({ puzzles, config, onComplete, onCheckAnswer }) {
  const [phase, setPhase] = useState("instructions"); // "instructions" | "playing" | "done"
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [runningScore, setRunningScore] = useState(null); // null until the first live check resolves

  const instructions = config?.instructions || {
    title: "Switch Challenge",
    rule: "Figure out which input position each output symbol came from, and pick the matching 4-digit sequence.",
    scoringNote: "+3 for a correct answer, -1 for an incorrect answer or a time out.",
    timerNote: `You have ${config?.timerPerPuzzle ?? 20} seconds per puzzle.`,
  };
  const secondsPerPuzzle = config?.timerPerPuzzle ?? 20;

  const handleAnswer = async (puzzleId, result) => {
    const next = { ...answers, [puzzleId]: result };
    setAnswers(next);
    try {
      const check = await onCheckAnswer?.(puzzleId, result);
      if (check && typeof check.runningScore === "number") {
        setRunningScore(check.runningScore);
      }
    } catch {
      // live-check is UI feedback only -- never blocks the real flow below.
    }
    if (currentIndex + 1 < puzzles.length) {
      setCurrentIndex(currentIndex + 1);
    } else {
      setPhase("done");
      onComplete?.(next);
    }
  };

  if (phase === "instructions") {
    return (
      <div className="pm-card p-8 max-w-lg mx-auto text-center">
        <div className="text-xs pm-eyebrow tracking-widest text-pm-primary-dark mb-2">
          Gamified Round
        </div>
        <h2 className="font-display text-2xl font-bold mb-4">{instructions.title}</h2>
        <p className="text-pm-text2 mb-6">{instructions.rule}</p>
        <div className="flex flex-col gap-3 text-left mb-8">
          <div className="flex items-center gap-3 text-sm text-pm-text2">
            <Zap size={16} className="text-pm-primary shrink-0" />
            {instructions.scoringNote}
          </div>
          <div className="flex items-center gap-3 text-sm text-pm-text2">
            <Clock size={16} className="text-pm-primary shrink-0" />
            {instructions.timerNote}
          </div>
        </div>
        <button
          onClick={() => setPhase("playing")}
          className="pm-btn pm-btn-primary inline-flex items-center gap-2 px-6 py-3"
        >
          <Play size={16} /> Play
        </button>
      </div>
    );
  }

  if (phase === "playing") {
    const current = puzzles[currentIndex];
    const answeredCount = Object.keys(answers).length;
    const maxPossible = puzzles.length * POINTS_CORRECT;
    const hasLiveScore = runningScore !== null;
    const fillPct = hasLiveScore
      ? Math.max(0, Math.min(100, (runningScore / maxPossible) * 100))
      : (answeredCount / puzzles.length) * 100;
    return (
      <div>
        <div className="flex items-center justify-between mb-3 px-1">
          <div className="pm-chip text-xs">LEVEL {currentIndex + 1}</div>
          <div className="flex-1 mx-4 h-2 bg-[rgba(10,10,10,0.06)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--pm-teal-deep)] transition-all"
              style={{ width: `${fillPct}%` }}
            />
          </div>
          <div className="text-xs font-display tabular-nums text-pm-text2">
            {hasLiveScore ? `${runningScore} pts` : `${answeredCount}/${puzzles.length}`}
          </div>
        </div>
        <SwitchChallengeQuestion
          key={current.id ?? current.puzzle_id}
          question={current}
          index={currentIndex}
          total={puzzles.length}
          secondsPerPuzzle={secondsPerPuzzle}
          onAnswer={handleAnswer}
        />
      </div>
    );
  }

  return null;
}
