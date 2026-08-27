import React, { useEffect, useRef, useState, useCallback } from "react";
import { Play, Clock, Zap, Eye } from "lucide-react";
import api from "../../api";

// Genuinely new flow-wrapper -- NOT a variant of DeductiveGridSection/
// SwitchChallengeSection. Reuses only their outer container language
// (#FAF8F3 page background inherited from the app shell, rounded-xl white
// cards with a soft shadow, the instructions-screen-with-Play-button
// convention) since grid_challenge's actual content (circle cluster,
// pattern grids, ordered recall) has nothing in common with either of the
// other two types' visuals.
//
// Unlike DeductiveGridSection/SwitchChallengeSection (which receive a
// pre-fetched `puzzles` array -- their entire content is safe to reveal
// upfront), this component owns real network calls to the phase-gated
// endpoints, because part of THIS game's content (block 2/3's highlighted
// position, every judgment's correct answer, the recall order) is the
// secret being tested, not just a "correctAnswer" field stripped off an
// otherwise-public document. See grid_challenge.py's module docstring.
//
// Client-side phase-order enforcement here is structural, not a separate
// checked condition: the state machine only ever calls startBlock(N+1)
// after finishing block N's LAST judgment, and only fetches recall_board
// after block 2 is done -- there is no UI path that could request a phase
// out of order. That's a UX nicety; the real security boundary is the
// server's 403 gating (see gamified_round.get_grid_challenge_phase),
// which rejects an out-of-order request even if this component had a bug.
//
// Props: attemptId, sectionKey, puzzleId, config, onComplete(result).

const DEFAULT_BLINK_MS = 2000;
const DEFAULT_JUDGMENT_SECONDS = 6;
const NUM_BLOCKS = 3;
const BLOCK_PHASE_NAMES = ["block1", "block2", "block3"];

// Same base tokens as deductive_grid/switch_challenge: white rounded card,
// soft shadow, no border.
const CELL_BASE = "bg-white rounded-xl shadow-[0_6px_20px_-8px_rgba(0,0,0,0.12)]";

function CircleCluster({ circles, highlightId, clickable, clickedIds, onClickCircle }) {
  return (
    <div className="relative w-full aspect-square bg-[#EFEBDD] rounded-2xl overflow-hidden">
      {(circles || []).map((c) => {
        const isHighlighted = c.id === highlightId;
        const clickedIndex = (clickedIds || []).indexOf(c.id);
        const isClicked = clickedIndex !== -1;
        return (
          <button
            key={c.id}
            type="button"
            data-testid={`grid-circle-${c.id}`}
            disabled={!clickable || isClicked}
            onClick={() => onClickCircle?.(c.id)}
            className={[
              "absolute rounded-full -translate-x-1/2 -translate-y-1/2 flex items-center justify-center transition-transform",
              isHighlighted ? "bg-[#0FAE73]" : isClicked ? "bg-[#0C8B5C]" : "bg-[#B9B3A2]",
              clickable && !isClicked ? "hover:scale-110 cursor-pointer" : "cursor-default",
            ].join(" ")}
            style={{ left: `${c.x * 100}%`, top: `${c.y * 100}%`, width: "7%", height: "7%" }}
          >
            {isClicked && <span className="text-white text-[10px] font-bold font-mono">{clickedIndex + 1}</span>}
          </button>
        );
      })}
    </div>
  );
}

// "Dark squares + small dots" per the reference: filled cells render as a
// solid dark square, empty cells render as a small muted dot rather than
// nothing, so the grid reads as a deliberate dot-grid, not a broken/empty one.
function PatternGrid({ pattern }) {
  return (
    <div className={`grid grid-cols-5 gap-1 p-3 ${CELL_BASE}`}>
      {pattern.map((row, r) =>
        row.map((cell, c) => (
          <div key={`${r}-${c}`} className="w-6 h-6 flex items-center justify-center">
            {cell === 1 ? (
              <div className="w-full h-full rounded-[3px] bg-[#2C3E56]" />
            ) : (
              <div className="w-1.5 h-1.5 rounded-full bg-[#D8D3C4]" />
            )}
          </div>
        ))
      )}
    </div>
  );
}

export default function GridChallengeSection({ attemptId, sectionKey, puzzleId, config, onComplete }) {
  // Config-driven (gamified_round_config.perType.grid_challenge.blinkMs/
  // judgmentSeconds via OARunner -> section.perTypeConfig), falling back
  // to the confirmed reference values -- unlike the other 4 types this
  // has no single timerPerPuzzle, but it's no less config-driven now.
  const blinkMs = config?.blinkMs ?? DEFAULT_BLINK_MS;
  const judgmentSeconds = config?.judgmentSeconds ?? DEFAULT_JUDGMENT_SECONDS;

  const [screen, setScreen] = useState("instructions"); // instructions | blink | judgment | recall | done
  const [blockIndex, setBlockIndex] = useState(0);
  const [judgmentIndex, setJudgmentIndex] = useState(0);
  const [circles, setCircles] = useState([]);
  const [highlightId, setHighlightId] = useState(null);
  const [judgments, setJudgments] = useState([]);
  const [recallLayout, setRecallLayout] = useState([]);
  const [clickedIds, setClickedIds] = useState([]);
  const [runningScore, setRunningScore] = useState(0);
  const [remaining, setRemaining] = useState(judgmentSeconds);
  const [locked, setLocked] = useState(false);
  const [error, setError] = useState(null);
  const startRef = useRef(Date.now());

  const instructions = config?.instructions || {
    title: "Grid Challenge",
    rule: "Memorize each highlighted position, judge whether the pattern pairs are rotated but identical, then recall the 3 positions in the order they were shown.",
    scoringNote: "+3 for a correct answer, -1 for an incorrect answer or a time out.",
    timerNote: `Each highlight shows for ${blinkMs / 1000} seconds; each pattern judgment gives you ${judgmentSeconds} seconds.`,
  };

  const fetchPhase = useCallback(async (phaseName, blockIdx) => {
    const { data } = await api.post(`/oa/${attemptId}/section/grid-challenge/phase`, {
      section_key: sectionKey, puzzle_id: puzzleId, phase: phaseName, blockIndex: blockIdx,
    });
    return data;
  }, [attemptId, sectionKey, puzzleId]);

  const submitJudgment = useCallback(async (blockIdx, judgmentIdx, ans, timedOut, timeTakenMs) => {
    const { data } = await api.post(`/oa/${attemptId}/section/grid-challenge/answer`, {
      section_key: sectionKey, puzzle_id: puzzleId, phase: "judgment",
      blockIndex: blockIdx, judgmentIndex: judgmentIdx, answer: ans, timedOut, timeTakenMs,
    });
    return data;
  }, [attemptId, sectionKey, puzzleId]);

  const submitRecall = useCallback(async (orderedIds) => {
    const { data } = await api.post(`/oa/${attemptId}/section/grid-challenge/answer`, {
      section_key: sectionKey, puzzle_id: puzzleId, phase: "recall", answer: orderedIds,
    });
    return data;
  }, [attemptId, sectionKey, puzzleId]);

  const startBlock = useCallback(async (idx) => {
    try {
      const data = await fetchPhase(`${BLOCK_PHASE_NAMES[idx]}_blink`, idx);
      setCircles(data.circleLayout);
      setHighlightId(data.targetCircleId);
      setBlockIndex(idx);
      setScreen("blink");
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load this round.");
    }
  }, [fetchPhase]);

  const handlePlay = () => startBlock(0);

  // blink -> pure timed reveal, no user action -- auto-fetches judgments
  // for this block once blinkMs elapses.
  useEffect(() => {
    if (screen !== "blink") return;
    const t = setTimeout(async () => {
      try {
        const data = await fetchPhase(`${BLOCK_PHASE_NAMES[blockIndex]}_judgments`, blockIndex);
        setJudgments(data.judgments);
        setJudgmentIndex(0);
        setScreen("judgment");
      } catch (e) {
        setError(e?.response?.data?.detail || "Failed to load this round's patterns.");
      }
    }, blinkMs);
    return () => clearTimeout(t);
  }, [screen, blockIndex, fetchPhase, blinkMs]);

  // per-judgment countdown (config-driven length)
  useEffect(() => {
    if (screen !== "judgment") return;
    setRemaining(judgmentSeconds);
    setLocked(false);
    startRef.current = Date.now();
    const interval = setInterval(() => setRemaining((r) => (r > 0 ? r - 1 : 0)), 1000);
    return () => clearInterval(interval);
  }, [screen, blockIndex, judgmentIndex, judgmentSeconds]);

  const advanceAfterJudgment = useCallback(async (result) => {
    setRunningScore(result.runningScore);
    const nextJudgmentIndex = judgmentIndex + 1;
    if (nextJudgmentIndex < judgments.length) {
      setJudgmentIndex(nextJudgmentIndex);
      return;
    }
    if (blockIndex + 1 < NUM_BLOCKS) {
      await startBlock(blockIndex + 1);
      return;
    }
    try {
      const data = await fetchPhase("recall_board", null);
      setRecallLayout(data.circleLayout);
      setClickedIds([]);
      setScreen("recall");
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load the recall step.");
    }
  }, [judgmentIndex, judgments.length, blockIndex, startBlock, fetchPhase]);

  const handleJudgmentAnswer = async (ans) => {
    if (locked) return;
    setLocked(true);
    const timeTakenMs = Date.now() - startRef.current;
    const result = await submitJudgment(blockIndex, judgmentIndex, ans, false, timeTakenMs);
    await advanceAfterJudgment(result);
  };

  // timeout = scored as incorrect via the same answer endpoint, same
  // convention as deductive_grid/switch_challenge's timeout handling.
  useEffect(() => {
    if (screen !== "judgment" || locked) return;
    if (remaining !== 0) return;
    setLocked(true);
    (async () => {
      const timeTakenMs = Date.now() - startRef.current;
      const result = await submitJudgment(blockIndex, judgmentIndex, null, true, timeTakenMs);
      await advanceAfterJudgment(result);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remaining, screen, locked]);

  // Recall has no timer per the reference (flagging this explicitly, not
  // silently assuming) -- candidate clicks 3 circles in order, already-
  // clicked ones are disabled via CircleCluster's clickedIds check.
  const handleClickCircle = (id) => {
    if (clickedIds.includes(id) || clickedIds.length >= 3) return;
    const next = [...clickedIds, id];
    setClickedIds(next);
    if (next.length === 3) {
      (async () => {
        const result = await submitRecall(next);
        setRunningScore(result.runningScore);
        setScreen("done");
        onComplete?.(result);
      })();
    }
  };

  if (error) {
    return <div className="pm-card p-6 text-pm-text2">{error}</div>;
  }

  if (screen === "instructions") {
    return (
      <div className="pm-card p-8 max-w-lg mx-auto text-center">
        <div className="text-xs font-mono uppercase tracking-widest text-pm-primary-dark mb-2">Gamified Round</div>
        <h2 className="font-display text-2xl font-bold mb-4">{instructions.title}</h2>
        <p className="text-pm-text2 mb-6">{instructions.rule}</p>
        <div className="flex flex-col gap-3 text-left mb-8">
          <div className="flex items-center gap-3 text-sm text-pm-text2">
            <Zap size={16} className="text-pm-primary shrink-0" /> {instructions.scoringNote}
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

  const headerBar = (
    <div className="flex items-center justify-between mb-3 px-1">
      <div className="pm-chip text-xs">BLOCK {blockIndex + 1} OF {NUM_BLOCKS}</div>
      <div className="text-xs font-mono text-pm-text2">{runningScore} pts</div>
    </div>
  );

  if (screen === "blink") {
    return (
      <div>
        {headerBar}
        <div className="pm-card p-6">
          <div className="flex items-center gap-2 text-sm font-semibold mb-4 justify-center">
            <Eye size={16} className="text-pm-primary" /> Memorize this position
          </div>
          <div className="max-w-sm mx-auto">
            <CircleCluster circles={circles} highlightId={highlightId} clickable={false} />
          </div>
        </div>
      </div>
    );
  }

  if (screen === "judgment") {
    const current = judgments[judgmentIndex];
    return (
      <div>
        {headerBar}
        <div className="pm-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="text-xs font-mono uppercase text-pm-text2">
              Judgment {judgmentIndex + 1} of {judgments.length}
            </div>
            <div className={`flex items-center gap-1.5 font-mono text-xs font-semibold ${remaining <= 2 ? "text-pm-secondary" : "text-pm-text2"}`}>
              <Clock size={14} /> 00:{String(remaining).padStart(2, "0")}
            </div>
          </div>
          <div className="font-display text-base font-semibold mb-5 text-center">Rotated but identical?</div>
          {current && (
            <div className="flex justify-center gap-6 mb-6">
              <PatternGrid pattern={current.patternA} />
              <PatternGrid pattern={current.patternB} />
            </div>
          )}
          <div className="flex justify-center gap-3">
            <button
              data-testid="grid-judgment-yes"
              onClick={() => handleJudgmentAnswer(true)}
              disabled={locked}
              className={`${CELL_BASE} px-8 py-4 font-semibold text-sm disabled:opacity-60`}
            >
              Yes
            </button>
            <button
              data-testid="grid-judgment-no"
              onClick={() => handleJudgmentAnswer(false)}
              disabled={locked}
              className={`${CELL_BASE} px-8 py-4 font-semibold text-sm disabled:opacity-60`}
            >
              No
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (screen === "recall") {
    return (
      <div>
        <div className="flex items-center justify-between mb-3 px-1">
          <div className="pm-chip text-xs">RECALL</div>
          <div className="text-xs font-mono text-pm-text2">{runningScore} pts</div>
        </div>
        <div className="pm-card p-6">
          <div className="font-display text-base font-semibold mb-1 text-center">
            Click the 3 positions you memorized, in order
          </div>
          <div className="text-xs text-pm-text2 text-center mb-5">{clickedIds.length} of 3 selected</div>
          <div className="max-w-sm mx-auto">
            <CircleCluster
              circles={recallLayout}
              clickable={clickedIds.length < 3}
              clickedIds={clickedIds}
              onClickCircle={handleClickCircle}
            />
          </div>
        </div>
      </div>
    );
  }

  // "done" -- caller (OARunner, once wired in step 6) owns what renders next.
  return null;
}
