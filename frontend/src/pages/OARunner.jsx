import React, { useEffect, useState, useMemo, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import ChartQuestion from "../components/charts/ChartQuestion";
import DeductiveGridSection from "../components/games/DeductiveGridSection";
import SwitchChallengeSection from "../components/games/SwitchChallengeSection";
import GridChallengeSection from "../components/games/GridChallengeSection";
import InductiveChallengeSection from "../components/games/InductiveChallengeSection";
import MotionChallengeSection from "../components/games/MotionChallengeSection";
import Round1CommunicationSection from "../components/capgemini/Round1CommunicationSection";
import DebuggingSection from "../components/DebuggingSection";
import AiAssistedSection from "../components/AiAssistedSection";
import { useMicRecorder } from "../hooks/useMicRecorder";
import { TID } from "../testIds";
import { Clock, Play, ChevronRight, CheckCircle2, XCircle } from "lucide-react";

// SafeMarkdown: falls back to plain text if react-markdown isn't present in the pipeline.
function MD({ children }) {
  const text = String(children || "");
  return <div className="prose prose-sm max-w-none whitespace-pre-wrap font-sans text-pm-text">
    {text.split("\n").map((line, i) => <p key={i} className="my-1">{line}</p>)}
  </div>;
}

export default function OARunner() {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState(null);
  const [answers, setAnswers] = useState({}); // {section_key: {qid: value}}
  const [submitting, setSubmitting] = useState(false);
  const [tick, setTick] = useState(0); // rerender for timer
  const startTimeRef = useRef({}); // per-section start times

  // Initial load
  useEffect(() => {
    let cancelled = false;
    api.get(`/oa/${attemptId}`).then(r => { if (!cancelled) setAttempt(r.data); })
       .catch(() => { if (!cancelled) toast.error("Attempt not found"); });
    return () => { cancelled = true; };
  }, [attemptId]);

  // Keep polling while ANY section is still generating in the background.
  // Runs alongside the rest of the runner — the user can start solving section 1
  // even while sections 2..N are still being built.
  useEffect(() => {
    if (!attempt) return;
    if (attempt.generation_status !== "generating") return;
    const t = setTimeout(async () => {
      try {
        const { data } = await api.get(`/oa/${attemptId}`);
        setAttempt(prev => ({
          ...data,
          // Preserve current_section_index in case user has advanced locally
          current_section_index: prev?.current_section_index ?? data.current_section_index ?? 0,
        }));
      } catch { /* ignore — next poll will retry */ }
    }, 3000);
    return () => clearTimeout(t);
  }, [attempt, attemptId]);

  useEffect(() => {
    const t = setInterval(() => setTick(x => x + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const currentSection = useMemo(() => {
    if (!attempt) return null;
    return attempt.sections[attempt.current_section_index] || null;
  }, [attempt]);

  useEffect(() => {
    if (currentSection && !startTimeRef.current[currentSection.key]) {
      startTimeRef.current[currentSection.key] = Date.now();
    }
  }, [currentSection]);

  if (!attempt) return <div><Header /><div className="p-10 text-center">Loading…</div></div>;

  if (attempt.generation_status === "failed") {
    return (
      <div>
        <Header />
        <div className="max-w-md mx-auto px-6 py-24 text-center">
          <h1 className="font-display text-3xl font-bold text-pm-text">Generation failed.</h1>
          <p className="text-pm-text2 mt-3">Please try starting a new run. Your run quota was not consumed.</p>
        </div>
      </div>
    );
  }

  if (attempt.status === "completed") {
    setTimeout(() => navigate(`/attempt/${attemptId}/review`, { replace: true }), 200);
    return <div><Header /><div className="p-10 text-center">Redirecting to review…</div></div>;
  }

  // The CURRENT section has no questions yet — show a targeted waiting screen
  // (this happens if the user submits section N and section N+1 hasn't finished
  // generating). Sections that ARE ready remain playable.
  const currentReady = currentSection && (currentSection.questions?.length ?? 0) > 0;
  if (!currentReady) {
    const total = attempt.sections?.length ?? 0;
    const ready = (attempt.sections || []).filter(s => (s.questions?.length ?? 0) > 0).length;
    return (
      <div>
        <Header />
        <div className="max-w-2xl mx-auto px-6 py-24 text-center pm-in">
          <div className="w-14 h-14 mx-auto rounded-full bg-pm-primary/10 grid place-items-center mb-6">
            <div className="w-6 h-6 border-2 border-pm-primary border-t-transparent rounded-full animate-spin" />
          </div>
          <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-2">preparing your OA</div>
          <h1 className="font-display text-3xl font-bold">
            {ready === 0
              ? <>Building {attempt.company_name}'s real OA for you.</>
              : <>Loading section {(attempt.current_section_index ?? 0) + 1}: {currentSection?.name}…</>}
          </h1>
          <p className="text-pm-text2 mt-3">
            {ready === 0
              ? "Sections generate in parallel. The first one usually lands in under 20 seconds."
              : "Almost there. You can start this section the moment it's ready."}
          </p>
          <div className="mt-8 pm-card p-5 text-left">
            <div className="text-xs font-mono uppercase text-pm-text2 mb-3">progress</div>
            <div className="space-y-2">
              {(attempt.sections || []).map((s, i) => {
                const done = (s.questions?.length ?? 0) > 0;
                const isCurrent = i === (attempt.current_section_index ?? 0);
                return (
                  <div key={s.key} className={`flex items-center gap-3 text-sm ${isCurrent ? "font-semibold" : ""}`}>
                    <span className={`w-2 h-2 rounded-full ${done ? "bg-pm-primary" : "bg-pm-text-muted animate-pulse"}`}></span>
                    <span className={done ? "text-pm-text" : "text-pm-text2"}>{s.name}</span>
                    {done && <span className="ml-auto text-xs font-mono text-pm-primary-dark">{s.questions.length} q ready</span>}
                    {!done && isCurrent && <span className="ml-auto text-xs font-mono text-pm-secondary">generating…</span>}
                  </div>
                );
              })}
            </div>
            <div className="mt-4 text-xs font-mono text-pm-text2">{ready} / {total} sections ready</div>
          </div>
        </div>
      </div>
    );
  }

  const sectionKey = currentSection.key;
  const sectionAnswers = answers[sectionKey] || {};

  const setAnswer = (qid, value) => {
    setAnswers(a => ({ ...a, [sectionKey]: { ...(a[sectionKey] || {}), [qid]: value } }));
  };

  const elapsed = Math.floor((Date.now() - (startTimeRef.current[sectionKey] || Date.now())) / 1000);
  const remaining = Math.max(0, currentSection.minutes * 60 - elapsed);
  const mm = String(Math.floor(remaining / 60)).padStart(2, "0");
  const ss = String(remaining % 60).padStart(2, "0");

  const submitSection = async () => {
    setSubmitting(true);
    try {
      const { data } = await api.post(`/oa/${attemptId}/section`, {
        section_key: sectionKey,
        answers: sectionAnswers,
      });
      toast.success(`Section done. Score ${(data.section_result.score * 100).toFixed(0)}%`);
      // Refresh attempt to move forward
      const { data: fresh } = await api.get(`/oa/${attemptId}`);
      setAttempt(fresh);
      if (data.status === "completed") {
        navigate(`/attempt/${attemptId}/review`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Submit failed");
    } finally { setSubmitting(false); }
  };

  // gamified_round has no manual "Submit section" step -- DeductiveGridSection
  // auto-advances through every sub-puzzle on its own and fires onComplete
  // exactly once with the full answers map. Posts that map directly instead
  // of going through sectionAnswers state (setAnswer/setAnswers batching
  // wouldn't be reflected yet if we read state back synchronously here).
  const submitGamifiedRoundAnswers = async (answersMap) => {
    if (submitting) return;
    setSubmitting(true);
    setAnswers(a => ({ ...a, [sectionKey]: answersMap }));
    try {
      const { data } = await api.post(`/oa/${attemptId}/section`, {
        section_key: sectionKey,
        answers: answersMap,
      });
      toast.success(`Section done. Score ${(data.section_result.score * 100).toFixed(0)}%`);
      const { data: fresh } = await api.get(`/oa/${attemptId}`);
      setAttempt(fresh);
      if (data.status === "completed") {
        navigate(`/attempt/${attemptId}/review`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Submit failed");
    } finally { setSubmitting(false); }
  };

  return (
    <div>
      <Header />
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-8 pm-in">
        {/* Section header */}
        <div className="flex items-center justify-between flex-wrap gap-4 mb-4">
          <div>
            <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark">
              {attempt.company_name} · section {attempt.current_section_index + 1}/{attempt.sections.length}
            </div>
            <h1 className="font-display text-3xl font-bold mt-1">{currentSection.name}</h1>
          </div>
          <div className="flex items-center gap-3">
            <div data-testid={TID.oaTimer} className={`pm-chip ${remaining < 60 ? "pm-chip-coral" : "pm-chip-primary"} text-base py-2 px-4`}>
              <Clock size={14} /> <span className="font-mono">{mm}:{ss}</span>
            </div>
            {currentSection.type !== "gamified_round" && (
              <button data-testid={TID.oaFinishSection} onClick={submitSection} disabled={submitting}
                      className="pm-btn pm-btn-primary text-sm py-2 px-4">
                {submitting ? "Grading…" : <>Submit section <ChevronRight size={14}/></>}
              </button>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-1 bg-[rgba(10,10,10,0.06)] rounded-full mb-8 overflow-hidden">
          <div className="h-full bg-pm-primary" style={{ width: `${((attempt.current_section_index) / attempt.sections.length) * 100}%` }}></div>
        </div>

        {/* Section body */}
        {(currentSection.type === "coding") ? (
          <CodingSection
            attemptId={attemptId}
            section={currentSection}
            answers={sectionAnswers}
            setAnswer={setAnswer}
          />
        ) : currentSection.type === "essay" ? (
          <EssaySection section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} />
        ) : currentSection.type === "speaking" ? (
          <SpeakingSection attemptId={attemptId} section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} />
        ) : currentSection.type === "reading_listening" ? (
          <ReadingListeningSection attemptId={attemptId} section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} />
        ) : currentSection.type === "comm_mixed" ? (
          <CommMixedSection attemptId={attemptId} section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} />
        ) : currentSection.type === "voice_mixed" ? (
          <VoiceMixedSection attemptId={attemptId} section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} />
        ) : currentSection.type === "gamified_round" ? (
          <GamifiedRoundSection attemptId={attemptId} section={currentSection} onComplete={submitGamifiedRoundAnswers} />
        ) : currentSection.type === "capgemini_round1" ? (
          <Round1CommunicationSection attemptId={attemptId} section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} />
        ) : currentSection.type === "debugging" ? (
          <DebuggingRoundSection attemptId={attemptId} section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} />
        ) : currentSection.type === "ai_assisted" ? (
          <AiAssistedRoundSection attemptId={attemptId} section={currentSection} />
        ) : (
          <MCQSection section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} />
        )}
      </div>
    </div>
  );
}

// -------- gamified_round -----------------------------------------------------
// A gamified_round section now runs EVERY game type the company's config
// lists, back to back within one section -- not one randomly-picked type
// (that was the old model). section.questions is a FLAT list spanning all
// present types (each item still carries its own gameType, unstripped --
// only correctAnswer/explanation are removed), grouped here by type
// (preserving first-seen order, which matches the server's generation
// order) and rendered ONE type's flow-wrapper at a time. Each wrapper owns
// its own instructions -> sub-puzzle 1..N -> done flow; when one finishes,
// this component advances to the next type's wrapper, merging
// deductive_grid/switch_challenge/inductive_challenge's per-puzzle answers
// into one combined map (all three use answer_check and the same {selected,
// timedOut, timeTakenMs} shape -- inductive_challenge's `selected` is just a
// 2-element index list instead of a single index, which the merge below
// doesn't need to know or care about). grid_challenge and motion_challenge
// contribute nothing to that map -- both already live server-side via their
// own live round trips (/grid-challenge/answer, /motion-challenge/move and
// /undo) -- each calls handleSubComplete({}), and spreading an empty object
// into the merge is a proven no-op (verified against grid_challenge's
// existing identical call before wiring motion_challenge the same way): it
// can never overwrite or drop keys the other types already contributed.
// onComplete fires exactly once, after the LAST type finishes, with the
// full merged map -- submitGamifiedRoundAnswers + the server's combined
// _grade_gamified_round_section remain the sole source of truth for score.
// perTypeConfig comes down on the section doc itself (server.py's
// gamified_round branch persists it to sections.$.perTypeConfig at
// generation time, via the SAME GET /oa/{attempt_id} fetch OARunner
// already makes -- no separate config fetch needed). Maps each type's DB
// field names onto the prop names its own component already expects
// (each one already has a `config?.X ?? default` fallback -- this was
// simply never being passed a real config before, so every timer was
// silently hardcoded regardless of what gamified_round_config held).
function buildGameConfig(perTypeConfig, gameType) {
  const cfg = (perTypeConfig || {})[gameType] || {};
  return {
    timerPerPuzzle: cfg.timerPerPuzzle,
    poolSeconds: cfg.poolTimerSeconds,
    blinkMs: cfg.blinkMs,
    judgmentSeconds: cfg.judgmentSeconds,
  };
}

function GamifiedRoundSection({ attemptId, section, onComplete }) {
  const puzzles = section.questions || [];
  const [subIndex, setSubIndex] = useState(0);
  const [combinedAnswers, setCombinedAnswers] = useState({});

  if (puzzles.length === 0) {
    return <div className="pm-card p-6 text-pm-text2">Question generation returned empty. Try re-starting this run.</div>;
  }

  const groups = [];
  for (const p of puzzles) {
    let group = groups.find((g) => g.gameType === p.gameType);
    if (!group) {
      group = { gameType: p.gameType, items: [] };
      groups.push(group);
    }
    group.items.push(p);
  }

  const onCheckAnswer = async (puzzleId, result) => {
    const { data } = await api.post(`/oa/${attemptId}/section/check`, {
      section_key: section.key,
      puzzle_id: puzzleId,
      selected: result.selected,
      timedOut: result.timedOut,
      timeTakenMs: result.timeTakenMs,
    });
    return data; // {correct, pointsAwarded, runningScore}
  };

  const handleSubComplete = (answersForThisType) => {
    const merged = { ...combinedAnswers, ...(answersForThisType || {}) };
    setCombinedAnswers(merged);
    if (subIndex + 1 < groups.length) {
      setSubIndex(subIndex + 1);
    } else {
      onComplete?.(merged);
    }
  };

  const current = groups[subIndex];
  if (!current) return null;
  const gameConfig = buildGameConfig(section.perTypeConfig, current.gameType);

  if (current.gameType === "switch_challenge") {
    return <SwitchChallengeSection puzzles={current.items} config={gameConfig} onComplete={handleSubComplete} onCheckAnswer={onCheckAnswer} />;
  }
  if (current.gameType === "inductive_challenge") {
    return <InductiveChallengeSection puzzles={current.items} config={gameConfig} onComplete={handleSubComplete} onCheckAnswer={onCheckAnswer} />;
  }
  if (current.gameType === "grid_challenge") {
    const puzzleId = current.items[0]?.id ?? current.items[0]?.puzzle_id;
    return (
      <GridChallengeSection
        attemptId={attemptId}
        sectionKey={section.key}
        puzzleId={puzzleId}
        config={gameConfig}
        onComplete={() => handleSubComplete({})}
      />
    );
  }
  if (current.gameType === "motion_challenge") {
    return (
      <MotionChallengeSection
        puzzles={current.items}
        attemptId={attemptId}
        sectionKey={section.key}
        config={gameConfig}
        onComplete={() => handleSubComplete({})}
      />
    );
  }
  return <DeductiveGridSection puzzles={current.items} config={gameConfig} onComplete={handleSubComplete} onCheckAnswer={onCheckAnswer} />;
}

// -------- MCQ / pseudocode / comm / game ------------------------------------
function MCQSection({ section, answers, setAnswer }) {
  const qs = section.questions || [];
  return (
    <div className="space-y-4">
      {qs.length === 0 && <div className="pm-card p-6 text-pm-text2">Question generation returned empty. Try re-starting this run.</div>}
      {qs.map((q, i) => (
        q.chart ? (
          <ChartQuestion
            key={q.id}
            question={q}
            index={i}
            total={qs.length}
            selected={answers[q.id]}
            onSelect={setAnswer}
          />
        ) : (
        <div key={q.id} className="pm-card p-6">
          <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Q{i+1} of {qs.length}</div>
          <div className="font-display text-lg font-semibold mb-4"><MD>{q.prompt}</MD></div>
          {q.svg_diagram && (
            <div
              className="mb-4 rounded-lg border border-pm-border overflow-x-auto flex justify-center bg-white p-2"
              dangerouslySetInnerHTML={{ __html: q.svg_diagram }}
            />
          )}
          <div className="grid grid-cols-1 gap-2">
            {(q.options || []).map((opt, ix) => {
              const selected = answers[q.id] === ix;
              return (
                <button
                  key={ix}
                  data-testid={TID.oaQuestionOption(q.id, ix)}
                  onClick={() => setAnswer(q.id, ix)}
                  className={`text-left border rounded-lg p-3 flex items-start gap-3 transition ${selected ? "border-pm-primary bg-pm-primary/5" : "border-pm-border hover:bg-[rgba(0,0,0,0.02)]"}`}
                >
                  <div className={`w-6 h-6 rounded-full grid place-items-center font-mono font-bold text-xs ${selected ? "bg-pm-primary text-white" : "bg-pm-muted"}`}>
                    {String.fromCharCode(65 + ix)}
                  </div>
                  <div className="flex-1 text-sm">{opt}</div>
                </button>
              );
            })}
          </div>
        </div>
        )
      ))}
    </div>
  );
}

// -------- Essay -------------------------------------------------------------
function EssaySection({ section, answers, setAnswer }) {
  const qs = section.questions || [];
  return (
    <div className="space-y-4">
      {qs.map((q) => (
        <div key={q.id} className="pm-card p-6">
          <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Essay</div>
          <div className="font-display text-xl font-bold mb-2">{q.topic}</div>
          <div className="text-sm text-pm-text2 mb-4">{q.instructions}</div>
          <textarea
            data-testid={TID.oaEssayInput(q.id)}
            className="pm-input min-h-[240px] font-sans"
            placeholder={`Write ${q.min_words || 150}-${q.max_words || 300} words…`}
            value={answers[q.id] || ""}
            onChange={e => setAnswer(q.id, e.target.value)}
          />
          <div className="mt-2 text-xs font-mono text-pm-text2">
            {(answers[q.id] || "").trim().split(/\s+/).filter(Boolean).length} words
          </div>
        </div>
      ))}
    </div>
  );
}

// -------- Voice recording (Cognizant Speaking / Reading & Listening) -------
// useMicRecorder moved to hooks/useMicRecorder.js (2026-08, Capgemini Round 1
// Section 6 frontend pass) so Round1CommunicationSection.jsx can reuse it
// too, without a circular import back into this page file. Same hook,
// same behavior -- every call site below is unchanged.

// -------- Speaking (30s prep -> 60s record -> transcript review) -----------
function SpeakingSection({ attemptId, section, answers, setAnswer }) {
  const q = (section.questions || [])[0];
  const [phase, setPhase] = useState("intro"); // intro | prep | recording | reviewing
  const [prepLeft, setPrepLeft] = useState(30);
  const [recordLeft, setRecordLeft] = useState(60);
  const [typedMode, setTypedMode] = useState(false);
  const mic = useMicRecorder(attemptId, section.key, q?.id, (t) => setAnswer(q.id, t));

  useEffect(() => { if (mic.status === "unavailable") setTypedMode(true); }, [mic.status]);
  useEffect(() => { if (mic.status === "done") setPhase("reviewing"); }, [mic.status]);

  useEffect(() => {
    if (phase !== "prep") return;
    if (prepLeft <= 0) { setPhase("recording"); mic.start(); return; }
    const t = setTimeout(() => setPrepLeft(s => s - 1), 1000);
    return () => clearTimeout(t);
  }, [phase, prepLeft]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (phase !== "recording") return;
    if (recordLeft <= 0) { mic.stop(); return; }
    const t = setTimeout(() => setRecordLeft(s => s - 1), 1000);
    return () => clearTimeout(t);
  }, [phase, recordLeft]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!q) return <div className="pm-card p-6">No speaking prompt generated.</div>;

  const restart = () => { mic.reset(); setPrepLeft(30); setRecordLeft(60); setPhase("intro"); };

  return (
    <div className="pm-card p-6 space-y-4">
      <div className="text-xs font-mono uppercase text-pm-text2">Speaking</div>
      <div className="font-display text-xl font-bold">{q.topic}</div>
      <div className="text-sm text-pm-text2">{q.instructions}</div>

      {typedMode ? (
        <>
          <div className="text-xs text-pm-text2">Mic unavailable. Type your response instead.</div>
          <textarea
            data-testid={TID.oaMicFallbackInput(q.id)}
            className="pm-input min-h-[160px] font-sans"
            placeholder={`Write ${q.min_words || 70}-${q.max_words || 170} words…`}
            value={answers[q.id] || ""}
            onChange={e => setAnswer(q.id, e.target.value)}
          />
        </>
      ) : phase === "intro" ? (
        <button data-testid={TID.oaMicRecordBtn(q.id)} onClick={() => setPhase("prep")} className="pm-btn pm-btn-primary text-sm py-2 px-4">
          Start (30s prep, then 60s to speak)
        </button>
      ) : phase === "prep" ? (
        <div className="text-center py-8">
          <div className="font-mono text-4xl font-bold">{prepLeft}s</div>
          <div className="text-sm text-pm-text2 mt-2">Get ready to speak…</div>
        </div>
      ) : phase === "recording" ? (
        <div className="text-center py-8">
          <div className="font-mono text-4xl font-bold text-pm-secondary">{recordLeft}s</div>
          <div className="text-sm text-pm-text2 mt-2">Recording… speak now</div>
          <button data-testid={TID.oaMicStopBtn(q.id)} onClick={mic.stop} className="pm-btn pm-btn-secondary text-sm py-2 px-4 mt-4">Stop early</button>
        </div>
      ) : mic.status === "uploading" ? (
        <div className="text-center py-8 text-pm-text2">Transcribing…</div>
      ) : (
        <>
          <div className="text-xs text-pm-text2">Transcript (edit if needed):</div>
          <textarea
            data-testid={TID.oaTranscriptInput(q.id)}
            className="pm-input min-h-[160px] font-sans"
            value={answers[q.id] || ""}
            onChange={e => setAnswer(q.id, e.target.value)}
          />
          <div className="flex gap-4">
            <button onClick={restart} className="text-xs text-pm-text2 underline">Re-record</button>
            <button onClick={() => setTypedMode(true)} className="text-xs text-pm-text2 underline">Type instead</button>
          </div>
        </>
      )}
    </div>
  );
}

// -------- Reading & Listening (repeat statements, one card per sentence) ---
function ReadingListeningSection({ attemptId, section, answers, setAnswer }) {
  const qs = section.questions || [];
  return (
    <div className="space-y-4">
      {qs.length === 0 && <div className="pm-card p-6 text-pm-text2">Question generation returned empty. Try re-starting this run.</div>}
      {qs.map((q, i) => (
        <ReadAloudCard
          key={q.id}
          attemptId={attemptId}
          sectionKey={section.key}
          q={q}
          idx={i}
          total={qs.length}
          value={answers[q.id] || ""}
          onChange={(v) => setAnswer(q.id, v)}
        />
      ))}
    </div>
  );
}

function ReadAloudCard({ attemptId, sectionKey, q, idx, total, value, onChange }) {
  const [typedMode, setTypedMode] = useState(false);
  const mic = useMicRecorder(attemptId, sectionKey, q.id, onChange);

  useEffect(() => { if (mic.status === "unavailable") setTypedMode(true); }, [mic.status]);

  return (
    <div className="pm-card p-6">
      <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Sentence {idx + 1} of {total}: read aloud</div>
      <div className="font-display text-lg font-semibold mb-4">{q.text}</div>
      {typedMode ? (
        <input
          data-testid={TID.oaMicFallbackInput(q.id)}
          className="pm-input"
          placeholder="Type what you would say…"
          value={value}
          onChange={e => onChange(e.target.value)}
        />
      ) : mic.status === "recording" ? (
        <button data-testid={TID.oaMicStopBtn(q.id)} onClick={mic.stop} className="pm-btn pm-btn-secondary text-sm py-2 px-4">Stop</button>
      ) : mic.status === "uploading" ? (
        <div className="text-sm text-pm-text2">Transcribing…</div>
      ) : (
        <div className="flex items-center gap-3">
          <button data-testid={TID.oaMicRecordBtn(q.id)} onClick={mic.start} className="pm-btn pm-btn-primary text-sm py-2 px-4">
            {value ? "Re-record" : "Record"}
          </button>
          <button onClick={() => setTypedMode(true)} className="text-xs text-pm-text2 underline">Type instead</button>
        </div>
      )}
      {value && !typedMode && (
        <div className="mt-3">
          <div className="text-xs text-pm-text2 mb-1">Transcript (edit if needed):</div>
          <input
            data-testid={TID.oaTranscriptInput(q.id)}
            className="pm-input"
            value={value}
            onChange={e => onChange(e.target.value)}
          />
        </div>
      )}
    </div>
  );
}

// -------- Accenture Communication Assessment: mixed MCQ + spoken items -----
// Each question carries its own `mode` ("mcq" | "speaking") from
// server.py's comm_mixed branch. Speaking items reuse the exact same
// useMicRecorder hook / POST /oa/{attemptId}/transcribe endpoint as
// Cognizant's voice sections — no second transcription implementation.
function SpeakingAnswerCard({ attemptId, sectionKey, q, idx, total, value, onChange }) {
  const [typedMode, setTypedMode] = useState(false);
  const mic = useMicRecorder(attemptId, sectionKey, q.id, onChange);

  useEffect(() => { if (mic.status === "unavailable") setTypedMode(true); }, [mic.status]);

  return (
    <div className="pm-card p-6">
      <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Q{idx + 1} of {total}: spoken response</div>
      <div className="font-display text-lg font-semibold mb-1">{q.topic}</div>
      <div className="text-sm text-pm-text2 mb-4">{q.instructions}</div>
      {typedMode ? (
        <>
          <div className="text-xs text-pm-text2 mb-2">Mic unavailable. Type your response instead.</div>
          <textarea
            data-testid={TID.oaMicFallbackInput(q.id)}
            className="pm-input min-h-[120px] font-sans"
            placeholder={`Write ${q.min_words || 70}-${q.max_words || 170} words…`}
            value={value}
            onChange={e => onChange(e.target.value)}
          />
        </>
      ) : mic.status === "recording" ? (
        <button data-testid={TID.oaMicStopBtn(q.id)} onClick={mic.stop} className="pm-btn pm-btn-secondary text-sm py-2 px-4">Stop</button>
      ) : mic.status === "uploading" ? (
        <div className="text-sm text-pm-text2">Transcribing…</div>
      ) : (
        <div className="flex items-center gap-3">
          <button data-testid={TID.oaMicRecordBtn(q.id)} onClick={mic.start} className="pm-btn pm-btn-primary text-sm py-2 px-4">
            {value ? "Re-record" : "Record"}
          </button>
          <button onClick={() => setTypedMode(true)} className="text-xs text-pm-text2 underline">Type instead</button>
        </div>
      )}
      {value && !typedMode && (
        <div className="mt-3">
          <div className="text-xs text-pm-text2 mb-1">Transcript (edit if needed):</div>
          <textarea
            data-testid={TID.oaTranscriptInput(q.id)}
            className="pm-input min-h-[100px] font-sans"
            value={value}
            onChange={e => onChange(e.target.value)}
          />
        </div>
      )}
    </div>
  );
}

function CommMixedSection({ attemptId, section, answers, setAnswer }) {
  const qs = section.questions || [];
  return (
    <div className="space-y-4">
      {qs.length === 0 && <div className="pm-card p-6 text-pm-text2">Question generation returned empty. Try re-starting this run.</div>}
      {qs.map((q, i) => q.mode === "speaking" ? (
        <SpeakingAnswerCard
          key={q.id}
          attemptId={attemptId}
          sectionKey={section.key}
          q={q}
          idx={i}
          total={qs.length}
          value={answers[q.id] || ""}
          onChange={(v) => setAnswer(q.id, v)}
        />
      ) : (
        <div key={q.id} className="pm-card p-6">
          <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Q{i + 1} of {qs.length}</div>
          <div className="font-display text-lg font-semibold mb-4"><MD>{q.prompt}</MD></div>
          <div className="grid grid-cols-1 gap-2">
            {(q.options || []).map((opt, ix) => {
              const selected = answers[q.id] === ix;
              return (
                <button
                  key={ix}
                  data-testid={TID.oaQuestionOption(q.id, ix)}
                  onClick={() => setAnswer(q.id, ix)}
                  className={`text-left border rounded-lg p-3 flex items-start gap-3 transition ${selected ? "border-pm-primary bg-pm-primary/5" : "border-pm-border hover:bg-[rgba(0,0,0,0.02)]"}`}
                >
                  <div className={`w-6 h-6 rounded-full grid place-items-center font-mono font-bold text-xs ${selected ? "bg-pm-primary text-white" : "bg-pm-muted"}`}>
                    {String.fromCharCode(65 + ix)}
                  </div>
                  <div className="flex-1 text-sm">{opt}</div>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// -------- LTIMindtree Spoken English / Communication: listening + speaking -
// Reverses the earlier text-only conversion for THIS company specifically
// (Tech Mahindra's separate Written Communication stays untouched). Every
// item is voice — reuses ReadAloudCard (listening, Cognizant) and
// SpeakingAnswerCard (speaking, Accenture) VERBATIM, no new interactive UI,
// same useMicRecorder/transcribe endpoint underneath.
function VoiceMixedSection({ attemptId, section, answers, setAnswer }) {
  const qs = section.questions || [];
  return (
    <div className="space-y-4">
      {qs.length === 0 && <div className="pm-card p-6 text-pm-text2">Question generation returned empty. Try re-starting this run.</div>}
      {qs.map((q, i) => q.mode === "speaking" ? (
        <SpeakingAnswerCard
          key={q.id}
          attemptId={attemptId}
          sectionKey={section.key}
          q={q}
          idx={i}
          total={qs.length}
          value={answers[q.id] || ""}
          onChange={(v) => setAnswer(q.id, v)}
        />
      ) : (
        <ReadAloudCard
          key={q.id}
          attemptId={attemptId}
          sectionKey={section.key}
          q={q}
          idx={i}
          total={qs.length}
          value={answers[q.id] || ""}
          onChange={(v) => setAnswer(q.id, v)}
        />
      ))}
    </div>
  );
}

// -------- Coding (LeetCode-style split panel) -------------------------------
function CodingSection({ attemptId, section, answers, setAnswer }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [running, setRunning] = useState(false);
  const [runResults, setRunResults] = useState(null);
  const qs = section.questions || [];
  const problem = qs[activeIdx];
  const penPaper = !!section.pen_paper;         // Zoho: no run button, textarea only
  const automataFix = !!section.automata_fix;   // Tech Mahindra: pre-fill buggy code
  if (!problem) return <div className="pm-card p-6">No problems generated.</div>;

  // Initial state: pre-fill buggy_code for Automata Fix problems.
  const initialCode = problem.buggy_code || "";
  const current = answers[problem.id] || { language: "python", code: initialCode };
  // If Automata Fix and user hasn't touched the field yet, seed it once.
  if (automataFix && !answers[problem.id] && initialCode) {
    setAnswer(problem.id, { language: "python", code: initialCode });
  }
  const setForProblem = (patch) => setAnswer(problem.id, { ...current, ...patch });

  const runCode = async () => {
    setRunning(true);
    try {
      const { data } = await api.post("/oa/run", {
        attempt_id: attemptId,
        section_key: section.key,
        problem_id: problem.id,
        language: current.language,
        code: current.code,
      });
      setRunResults(data.results);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Run failed");
    } finally { setRunning(false); }
  };

  return (
    <div>
      {qs.length > 1 && (
        <div className="flex gap-2 mb-4">
          {qs.map((q, i) => (
            <button key={q.id} onClick={() => { setActiveIdx(i); setRunResults(null); }}
              className={`px-3 py-1.5 rounded-lg text-sm font-mono ${i === activeIdx ? "bg-pm-primary text-white" : "bg-pm-muted"}`}>
              Problem {i+1}
            </button>
          ))}
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:h-[70vh]">
        {/* Left: problem */}
        <div className="pm-card p-6 overflow-y-auto">
          <div className="flex items-center justify-between mb-2">
            <div className="font-display text-xl font-bold">{problem.title}</div>
            <span className="pm-chip pm-chip-primary">{problem.difficulty}</span>
          </div>
          <div className="text-sm text-pm-text2"><MD>{problem.statement}</MD></div>
          {problem.input_format && <div className="mt-4"><div className="text-xs font-mono uppercase text-pm-text2 mb-1">Input</div><div className="text-sm">{problem.input_format}</div></div>}
          {problem.output_format && <div className="mt-3"><div className="text-xs font-mono uppercase text-pm-text2 mb-1">Output</div><div className="text-sm">{problem.output_format}</div></div>}
          {problem.constraints && <div className="mt-3"><div className="text-xs font-mono uppercase text-pm-text2 mb-1">Constraints</div><div className="text-sm font-mono">{problem.constraints}</div></div>}

          <div className="mt-6">
            <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Visible tests</div>
            <div className="space-y-2">
              {(problem.visible_tests || []).map((t, i) => (
                <div key={i} className="border rounded-lg p-3 text-xs font-mono bg-pm-muted/50">
                  <div><span className="text-pm-text2">input:</span> {t.input}</div>
                  <div><span className="text-pm-text2">expected:</span> {t.expected_output}</div>
                </div>
              ))}
            </div>
          </div>

          {runResults && (
            <div className="mt-6">
              <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Run results</div>
              <div className="space-y-2">
                {runResults.map((r, i) => (
                  <div key={i} className={`border rounded-lg p-3 text-xs font-mono ${r.passed ? "border-pm-primary/40 bg-pm-primary/5" : "border-pm-secondary/40 bg-pm-secondary/5"}`}>
                    <div className="flex items-center gap-2">
                      {r.passed ? <CheckCircle2 size={14} className="text-pm-primary"/> : <XCircle size={14} className="text-pm-secondary"/>}
                      Test {i+1} · {r.passed ? "passed" : "failed"}
                    </div>
                    <div className="mt-1 text-pm-text2">expected: {r.expected}</div>
                    <div className="text-pm-text2">got: {r.got || (r.error ? `(error) ${r.error}` : "")}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: editor — dark Monaco for regular coding, plain textarea for pen-paper mode. */}
        {penPaper ? (
          <div className="pm-card p-4 flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <div className="pm-chip pm-chip-coral">pen-paper mode · no run button</div>
              <div className="text-xs font-mono text-pm-text2">Zoho style</div>
            </div>
            <textarea
              data-testid={TID.oaCodeArea}
              value={current.code}
              onChange={e => setForProblem({ code: e.target.value })}
              placeholder="Write your full program here. No autocomplete. No test runner. Just like paper."
              autoComplete="off" autoCorrect="off" spellCheck={false}
              className="pm-input flex-1 min-h-[400px] font-mono text-sm"
              style={{ background: "#E3EFEF", color: "#0B2A30", lineHeight: 1.6, tabSize: 4 }}
            />
            <div className="mt-2 text-xs font-mono text-pm-text2">{(current.code || "").split("\n").length} lines · {(current.code || "").length} chars</div>
          </div>
        ) : (
        <div className="pm-editor-pane rounded-2xl overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
            <div className="flex items-center gap-2">
              <select
                data-testid={TID.oaLangSelect}
                value={current.language}
                onChange={e => setForProblem({ language: e.target.value })}
                className="bg-transparent border border-white/10 rounded-md text-xs px-2 py-1 font-mono"
              >
                <option value="python">Python 3</option>
                <option value="javascript">JavaScript</option>
                <option value="c">C</option>
                <option value="cpp">C++</option>
                <option value="java">Java</option>
              </select>
              {automataFix && <span className="pm-chip pm-chip-coral">automata fix · code pre-filled</span>}
            </div>
            <button data-testid={TID.oaRunBtn} onClick={runCode} disabled={running}
              className="pm-btn text-xs py-1.5 px-3" style={{ background: "#0F6F7A", color: "#fff" }}>
              <Play size={12}/> {running ? "running…" : "Run visible tests"}
            </button>
          </div>
          <div className="flex-1 min-h-[400px]">
            <Editor
              height="100%"
              language={current.language === "python" ? "python" : current.language}
              theme="vs-dark"
              value={current.code}
              onChange={(v) => setForProblem({ code: v || "" })}
              options={{ fontSize: 14, minimap: { enabled: false }, fontFamily: "JetBrains Mono", padding: { top: 12 }, scrollBeyondLastLine: false }}
            />
          </div>
          <textarea data-testid={TID.oaCodeArea} value={current.code} onChange={e => setForProblem({ code: e.target.value })} className="sr-only" aria-hidden />
        </div>
        )}
      </div>
    </div>
  );
}

// -------- Debugging Assessment (Round 3) ------------------------------------
// Thin wrapper around DebuggingSection (the same presentational component
// /dev/debugging-preview uses, already click-through verified there) --
// this wrapper owns only the Run button's running/runResults state and
// posts to the existing, generic /oa/run route above (unchanged: it looks
// up the problem by id inside the section's server-stored questions and
// runs visible_tests, exactly like CodingSection's own runCode does, with
// no section-type check of its own). "Submit section" needs nothing
// debugging-specific here -- the top-level submitSection() already posts
// sectionAnswers generically to /oa/{attemptId}/section, which server.py's
// submit_section now dispatches to _grade_debugging_section() for this
// section's type.
function DebuggingRoundSection({ attemptId, section, answers, setAnswer }) {
  const [running, setRunning] = useState(false);
  const [runResults, setRunResults] = useState(null);

  const onRun = async (problem, current) => {
    setRunning(true);
    try {
      const { data } = await api.post("/oa/run", {
        attempt_id: attemptId,
        section_key: section.key,
        problem_id: problem.id,
        language: current.language,
        code: current.code,
      });
      setRunResults(data.results);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Run failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <DebuggingSection
      problems={section.questions || []}
      answers={answers}
      setAnswer={setAnswer}
      onRun={onRun}
      running={running}
      runResults={runResults}
    />
  );
}

// -------- AI-Assisted Coding (Round 4) ---------------------------------
// Thin wrapper around AiAssistedSection (the same presentational
// component /dev/ai-assisted-preview uses, already click-through
// verified there). UNLIKE every other section, Round 4's live state
// lives entirely server-side in db.ai_assisted_sessions (created at
// generation time, see server.py's "ai_assisted" _generate_section_
// questions branch) -- section.questions here holds only an opaque
// {session_id, problem_id} pointer, not the conversation itself, so this
// wrapper fetches the live session on mount and re-fetches it (via each
// action's response body) after every turn, rather than deriving
// anything from `section` the way CodingSection/DebuggingRoundSection
// do. Talks to the LIVE, attempt-scoped
// /oa/{attemptId}/ai-assisted/{section.key}/... routes -- a separate
// code path from /dev/ai-assisted/*, not a wrapper around it (see
// server.py's own comment on that same separation). "Submit section"
// needs nothing special here either: the top-level submitSection()
// posts sectionAnswers (whatever they are, even {}) to
// /oa/{attemptId}/section, and server.py's submit_section dispatches to
// _finalize_ai_assisted_section() for this type, which ignores the
// answers payload entirely and re-derives the score from the stored
// session -- covering both natural completion AND "candidate clicked
// Submit / timer expired mid-conversation" the same way.
function AiAssistedRoundSection({ attemptId, section }) {
  const [session, setSession] = useState(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.get(`/oa/${attemptId}/ai-assisted/${section.key}`).then(r => {
      if (!cancelled) setSession(r.data);
    }).catch(err => {
      if (!cancelled) toast.error(err.response?.data?.detail || "Failed to load session");
    });
    return () => { cancelled = true; };
  }, [attemptId, section.key]);

  const onSendMessage = async (text) => {
    setSending(true);
    try {
      const { data } = await api.post(`/oa/${attemptId}/ai-assisted/${section.key}/message`, { text });
      setSession(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send message");
    } finally {
      setSending(false);
    }
  };

  const onConsent = async (value) => {
    setSending(true);
    try {
      const { data } = await api.post(`/oa/${attemptId}/ai-assisted/${section.key}/consent`, { value });
      setSession(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to submit consent");
    } finally {
      setSending(false);
    }
  };

  const onSelfReview = async (value) => {
    setSending(true);
    try {
      const { data } = await api.post(`/oa/${attemptId}/ai-assisted/${section.key}/self_review`, { value });
      setSession(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to submit self-review");
    } finally {
      setSending(false);
    }
  };

  if (!session) return <div className="pm-card p-6 text-pm-text2">Loading your problem…</div>;

  return (
    <AiAssistedSection
      session={session}
      onSendMessage={onSendMessage}
      onConsent={onConsent}
      onSelfReview={onSelfReview}
      sending={sending}
    />
  );
}
