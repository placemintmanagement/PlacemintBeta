import React, { useState } from "react";
import { Play, Clock, Target } from "lucide-react";
import DeductiveGridQuestion from "./DeductiveGridQuestion";

// deductive_grid's own known scoring ratio (+1/-1, confirmed) -- not a
// secret, it's already shown verbatim in the instructions screen text
// below. Used only to size the progress bar's 100% mark (puzzles.length *
// POINTS_CORRECT); the actual per-answer point values always come from the
// server via onCheckAnswer, never computed client-side.
const POINTS_CORRECT = 1;

// Standalone flow wrapper, wired into OARunner.jsx's gamified_round dispatch
// (see GamifiedRoundSection). Owns the instructions -> sub-puzzle-1..N ->
// done flow for one gamified_round section: instructions screen with a
// "Play" button, then one sub-puzzle per screen with no manual "next"/
// "back" -- each DeductiveGridQuestion auto-fires onAnswer (on selection OR
// its own 15s timeout) and this wrapper immediately advances.
//
// Props:
//   puzzles: array of public-safe (post strip_answer()) puzzle docs, e.g.
//     gamified_round.sample_puzzles()'s return value.
//   config: the company's gamified_round_config doc (for instructions text
//     + timerPerPuzzle).
//   onComplete(answers): fired once with the full { [puzzle_id]: {selected,
//     timedOut, timeTakenMs} } map after the last sub-puzzle -- caller is
//     expected to submit this to the grade_session endpoint (the real,
//     authoritative score).
//   onCheckAnswer(puzzleId, result) -> Promise<{correct, pointsAwarded,
//     runningScore}>: optional, called once per answer purely for LIVE
//     running-score feedback (the orange bar). If omitted, the bar falls
//     back to a plain answered/total display. Failures here are swallowed
//     and never block advancing -- the final grade is what actually counts.
export default function DeductiveGridSection({ puzzles, config, onComplete, onCheckAnswer }) {
  const [phase, setPhase] = useState("instructions"); // "instructions" | "playing" | "done"
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [runningScore, setRunningScore] = useState(null); // null until the first live check resolves

  const instructions = config?.instructions || {
    title: "Deductive Grid",
    rule: "Neither a row nor a column should have similar symbols.",
    scoringNote: "+1 for a correct answer, -1 for an incorrect answer or a time out.",
    timerNote: `You have ${config?.timerPerPuzzle ?? 15} seconds per puzzle.`,
  };
  const secondsPerPuzzle = config?.timerPerPuzzle ?? 15;

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
            <Target size={16} className="text-pm-primary shrink-0" />
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
        <DeductiveGridQuestion
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

  // phase === "done" -- caller (OARunner) owns what renders next; this
  // wrapper doesn't assume a review UI.
  return null;
}
