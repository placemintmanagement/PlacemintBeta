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
import { PageShell, SectionLabel, PageTitle, CardTitle, Card, Chip, Button } from "../components/shared";

// Shared presentation values for the runner (2026-10 rollout). Body font
// everywhere; monospace is kept only for code (test I/O, constraints, the
// editor itself). Eyebrows use .pm-eyebrow; inputs use .pm-input.
const META = { fontSize: 13, color: "rgba(11,42,48,0.7)" };
const BODY = { fontSize: 15, color: "rgba(11,42,48,0.85)", lineHeight: 1.6 };
const TIMER_OK = { background: "var(--pm-success-bg)", color: "var(--pm-ink)" };
const TIMER_LOW = { background: "var(--pm-error-bg)", color: "var(--pm-error-text)" };

// SafeMarkdown: falls back to plain text if react-markdown isn't present in the pipeline.
function MD({ children }) {
  const text = String(children || "");
  return <div className="prose prose-sm max-w-none whitespace-pre-wrap font-sans" style={{ color: "var(--pm-ink)" }}>
    {text.split("\n").map((line, i) => <p key={i} className="my-1">{line}</p>)}
  </div>;
}

// Empty-section notice, shared by the question-type sections below.
function EmptyNotice({ children }) {
  return <Card><div style={BODY}>{children}</div></Card>;
}

// Letter badge for option lists: selected = teal-deep, otherwise sky.
function LetterBadge({ letter, selected }) {
  return (
    <div className="w-7 h-7 rounded-full grid place-items-center shrink-0 font-display font-semibold"
         style={{ fontSize: 14, background: selected ? "var(--pm-teal-deep)" : "var(--pm-sky)", color: selected ? "var(--pm-white)" : "var(--pm-ink)" }}>
      {letter}
    </div>
  );
}

// Option button style: unselected uses the control border (it is an
// interactive boundary); selected uses teal-deep and a sky wash.
function optionStyle(selected) {
  return selected
    ? { border: "1.5px solid var(--pm-teal-deep)", background: "var(--pm-sky)", color: "var(--pm-ink)" }
    : { border: "1.5px solid var(--pm-border-control)", background: "var(--pm-white)", color: "var(--pm-ink)" };
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

  if (!attempt) return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Loading…</div></PageShell></div>;

  if (attempt.generation_status === "failed") {
    return (
      <div>
        <Header light />
        <PageShell>
          <div className="max-w-md mx-auto py-24 text-center">
            <PageTitle>Generation failed.</PageTitle>
            <p className="mt-3" style={BODY}>Please try starting a new run. Your run quota was not consumed.</p>
          </div>
        </PageShell>
      </div>
    );
  }

  if (attempt.status === "completed") {
    setTimeout(() => navigate(`/attempt/${attemptId}/review`, { replace: true }), 200);
    return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Redirecting to review…</div></PageShell></div>;
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
        <Header light />
        <PageShell>
          <div className="max-w-2xl mx-auto py-24 text-center pm-in">
            <div className="w-14 h-14 mx-auto rounded-full grid place-items-center mb-6" style={{ background: "var(--pm-sky)" }}>
              <div className="w-6 h-6 rounded-full animate-spin" style={{ border: "2px solid var(--pm-teal-deep)", borderTopColor: "transparent" }} />
            </div>
            <SectionLabel>preparing your OA</SectionLabel>
            <PageTitle>
              {ready === 0
                ? <>Building {attempt.company_name}'s real OA for you.</>
                : <>Loading section {(attempt.current_section_index ?? 0) + 1}: {currentSection?.name}…</>}
            </PageTitle>
            <p className="mt-3" style={BODY}>
              {ready === 0
                ? "Sections generate in parallel. The first one usually lands in under 20 seconds."
                : "Almost there. You can start this section the moment it's ready."}
            </p>
            <Card className="mt-8 text-left" padding="20px 24px">
              <div className="pm-eyebrow mb-3" style={{ color: "rgba(11,42,48,0.7)" }}>progress</div>
              <div className="space-y-2">
                {(attempt.sections || []).map((s, i) => {
                  const done = (s.questions?.length ?? 0) > 0;
                  const isCurrent = i === (attempt.current_section_index ?? 0);
                  return (
                    <div key={s.key} className={`flex items-center gap-3 ${isCurrent ? "font-semibold" : ""}`} style={{ fontSize: 15, color: done ? "var(--pm-ink)" : "rgba(11,42,48,0.7)" }}>
                      <span className={`w-2.5 h-2.5 rounded-full ${done ? "" : "animate-pulse"}`} style={{ background: done ? "var(--pm-teal-deep)" : "rgba(11,42,48,0.35)" }}></span>
                      <span>{s.name}</span>
                      {done && <span className="ml-auto" style={{ ...META, color: "var(--pm-teal-deep)", fontWeight: 600 }}>{s.questions.length} q ready</span>}
                      {!done && isCurrent && <span className="ml-auto" style={{ ...META, color: "var(--pm-teal-deep)", fontWeight: 600 }}>generating…</span>}
                    </div>
                  );
                })}
              </div>
              <div className="mt-4" style={META}>{ready} / {total} sections ready</div>
            </Card>
          </div>
        </PageShell>
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
      if (data.status === "completed") {
        // Navigate with the tier before refreshing the attempt. The refreshed
        // attempt is completed, so the render-time redirect below would
        // otherwise replace this entry and drop the tier from its state.
        navigate(`/attempt/${attemptId}/review`, { state: data.capgemini_tier ? { capgemini_tier: data.capgemini_tier } : null });
        return;
      }
      // Refresh attempt to move forward
      const { data: fresh } = await api.get(`/oa/${attemptId}`);
      setAttempt(fresh);
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
      if (data.status === "completed") {
        // Same ordering as submitSection: navigate before the attempt refresh.
        navigate(`/attempt/${attemptId}/review`, { state: data.capgemini_tier ? { capgemini_tier: data.capgemini_tier } : null });
        return;
      }
      const { data: fresh } = await api.get(`/oa/${attemptId}`);
      setAttempt(fresh);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Submit failed");
    } finally { setSubmitting(false); }
  };

  const progressPct = (attempt.current_section_index / attempt.sections.length) * 100;

  return (
    <div>
      <Header light />
      <PageShell section={false}>
        <div className="py-8 pm-in">
          {/* Section header */}
          <div className="flex items-end justify-between flex-wrap gap-4 mb-5">
            <div>
              <SectionLabel className="!mb-1">
                {attempt.company_name} · section {attempt.current_section_index + 1}/{attempt.sections.length}
              </SectionLabel>
              <PageTitle style={{ fontSize: "clamp(1.75rem, 3vw, 2.25rem)" }}>{currentSection.name}</PageTitle>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <div data-testid={TID.oaTimer} className="inline-flex items-center gap-2 rounded-full font-display font-semibold"
                   style={{ fontSize: 18, padding: "8px 16px", fontVariantNumeric: "tabular-nums", ...(remaining < 60 ? TIMER_LOW : TIMER_OK) }}>
                <Clock size={16} aria-hidden="true" /> <span>{mm}:{ss}</span>
              </div>
              {currentSection.type !== "gamified_round" && (
                <Button data-testid={TID.oaFinishSection} onClick={submitSection} disabled={submitting} className="!py-2 !px-4" style={{ fontSize: 14 }}>
                  {submitting ? "Grading…" : <>Submit section <ChevronRight size={14} aria-hidden="true"/></>}
                </Button>
              )}
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full rounded-full overflow-hidden mb-8" style={{ height: 6, background: "var(--pm-sky-deep)" }} role="progressbar" aria-valuenow={Math.round(progressPct)} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-full rounded-full" style={{ width: `${progressPct}%`, background: "var(--pm-teal-deep)" }}></div>
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
      </PageShell>
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
    return <EmptyNotice>Question generation returned empty. Try re-starting this run.</EmptyNotice>;
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
      {qs.length === 0 && <EmptyNotice>Question generation returned empty. Try re-starting this run.</EmptyNotice>}
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
        <Card key={q.id}>
          <div className="pm-eyebrow mb-2" style={{ color: "rgba(11,42,48,0.7)" }}>Q{i+1} of {qs.length}</div>
          <div className="font-display font-semibold mb-4" style={{ fontSize: 19, color: "var(--pm-ink)", lineHeight: 1.4 }}><MD>{q.prompt}</MD></div>
          {q.svg_diagram && (
            <div
              className="mb-4 rounded-[14px] overflow-x-auto flex justify-center p-2"
              style={{ border: "1px solid rgba(7,59,67,0.08)", background: "var(--pm-white)" }}
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
                  aria-pressed={selected}
                  onClick={() => setAnswer(q.id, ix)}
                  className="text-left rounded-[14px] px-4 py-3 flex items-start gap-3 transition-colors hover:bg-[rgba(15,111,122,0.06)] focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[var(--pm-teal-night)]"
                  style={optionStyle(selected)}
                >
                  <LetterBadge letter={String.fromCharCode(65 + ix)} selected={selected} />
                  <div className="flex-1" style={{ fontSize: 15, lineHeight: 1.5, paddingTop: 2 }}>{opt}</div>
                </button>
              );
            })}
          </div>
        </Card>
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
        <Card key={q.id}>
          <div className="pm-eyebrow mb-2" style={{ color: "rgba(11,42,48,0.7)" }}>Essay</div>
          <div className="font-display font-semibold mb-2" style={{ fontSize: 22, color: "var(--pm-ink)" }}>{q.topic}</div>
          <div className="mb-4" style={BODY}>{q.instructions}</div>
          <textarea
            data-testid={TID.oaEssayInput(q.id)}
            className="pm-input min-h-[240px]"
            placeholder={`Write ${q.min_words || 150}-${q.max_words || 300} words…`}
            value={answers[q.id] || ""}
            onChange={e => setAnswer(q.id, e.target.value)}
          />
          <div className="mt-2" style={META}>
            {(answers[q.id] || "").trim().split(/\s+/).filter(Boolean).length} words
          </div>
        </Card>
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

  if (!q) return <EmptyNotice>No speaking prompt generated.</EmptyNotice>;

  const restart = () => { mic.reset(); setPrepLeft(30); setRecordLeft(60); setPhase("intro"); };

  return (
    <Card>
      <div className="space-y-4">
        <div className="pm-eyebrow" style={{ color: "rgba(11,42,48,0.7)" }}>Speaking</div>
        <div className="font-display font-semibold" style={{ fontSize: 22, color: "var(--pm-ink)" }}>{q.topic}</div>
        <div style={BODY}>{q.instructions}</div>

        {typedMode ? (
          <>
            <div style={META}>Mic unavailable. Type your response instead.</div>
            <textarea
              data-testid={TID.oaMicFallbackInput(q.id)}
              className="pm-input min-h-[160px]"
              placeholder={`Write ${q.min_words || 70}-${q.max_words || 170} words…`}
              value={answers[q.id] || ""}
              onChange={e => setAnswer(q.id, e.target.value)}
            />
          </>
        ) : phase === "intro" ? (
          <Button data-testid={TID.oaMicRecordBtn(q.id)} onClick={() => setPhase("prep")} className="!py-2 !px-4" style={{ fontSize: 14 }}>
            Start (30s prep, then 60s to speak)
          </Button>
        ) : phase === "prep" ? (
          <div className="text-center py-8">
            <div className="font-display font-semibold" style={{ fontSize: 48, color: "var(--pm-ink)", fontVariantNumeric: "tabular-nums" }}>{prepLeft}s</div>
            <div className="mt-2" style={BODY}>Get ready to speak…</div>
          </div>
        ) : phase === "recording" ? (
          <div className="text-center py-8">
            <div className="font-display font-semibold" style={{ fontSize: 48, color: "var(--pm-teal-deep)", fontVariantNumeric: "tabular-nums" }}>{recordLeft}s</div>
            <div className="mt-2" style={BODY}>Recording… speak now</div>
            <Button variant="secondary" data-testid={TID.oaMicStopBtn(q.id)} onClick={mic.stop} className="mt-4 !py-2 !px-4" style={{ fontSize: 14 }}>Stop early</Button>
          </div>
        ) : mic.status === "uploading" ? (
          <div className="text-center py-8" style={BODY}>Transcribing…</div>
        ) : (
          <>
            <div style={META}>Transcript (edit if needed):</div>
            <textarea
              data-testid={TID.oaTranscriptInput(q.id)}
              className="pm-input min-h-[160px]"
              value={answers[q.id] || ""}
              onChange={e => setAnswer(q.id, e.target.value)}
            />
            <div className="flex gap-4" style={{ fontSize: 14 }}>
              <button onClick={restart} className="underline underline-offset-2" style={{ color: "var(--pm-teal-deep)", fontWeight: 600 }}>Re-record</button>
              <button onClick={() => setTypedMode(true)} className="underline underline-offset-2" style={{ color: "var(--pm-teal-deep)", fontWeight: 600 }}>Type instead</button>
            </div>
          </>
        )}
      </div>
    </Card>
  );
}

// -------- Reading & Listening (repeat statements, one card per sentence) ---
function ReadingListeningSection({ attemptId, section, answers, setAnswer }) {
  const qs = section.questions || [];
  return (
    <div className="space-y-4">
      {qs.length === 0 && <EmptyNotice>Question generation returned empty. Try re-starting this run.</EmptyNotice>}
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
    <Card>
      <div className="pm-eyebrow mb-2" style={{ color: "rgba(11,42,48,0.7)" }}>Sentence {idx + 1} of {total}: read aloud</div>
      <div className="font-display font-semibold mb-4" style={{ fontSize: 19, color: "var(--pm-ink)", lineHeight: 1.4 }}>{q.text}</div>
      {typedMode ? (
        <input
          data-testid={TID.oaMicFallbackInput(q.id)}
          className="pm-input"
          placeholder="Type what you would say…"
          value={value}
          onChange={e => onChange(e.target.value)}
        />
      ) : mic.status === "recording" ? (
        <Button variant="secondary" data-testid={TID.oaMicStopBtn(q.id)} onClick={mic.stop} className="!py-2 !px-4" style={{ fontSize: 14 }}>Stop</Button>
      ) : mic.status === "uploading" ? (
        <div style={BODY}>Transcribing…</div>
      ) : (
        <div className="flex items-center gap-3 flex-wrap">
          <Button data-testid={TID.oaMicRecordBtn(q.id)} onClick={mic.start} className="!py-2 !px-4" style={{ fontSize: 14 }}>
            {value ? "Re-record" : "Record"}
          </Button>
          <button onClick={() => setTypedMode(true)} className="underline underline-offset-2" style={{ fontSize: 14, color: "var(--pm-teal-deep)", fontWeight: 600 }}>Type instead</button>
        </div>
      )}
      {value && !typedMode && (
        <div className="mt-3">
          <div className="mb-1" style={META}>Transcript (edit if needed):</div>
          <input
            data-testid={TID.oaTranscriptInput(q.id)}
            className="pm-input"
            value={value}
            onChange={e => onChange(e.target.value)}
          />
        </div>
      )}
    </Card>
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
    <Card>
      <div className="pm-eyebrow mb-2" style={{ color: "rgba(11,42,48,0.7)" }}>Q{idx + 1} of {total}: spoken response</div>
      <div className="font-display font-semibold mb-1" style={{ fontSize: 20, color: "var(--pm-ink)" }}>{q.topic}</div>
      <div className="mb-4" style={BODY}>{q.instructions}</div>
      {typedMode ? (
        <>
          <div className="mb-2" style={META}>Mic unavailable. Type your response instead.</div>
          <textarea
            data-testid={TID.oaMicFallbackInput(q.id)}
            className="pm-input min-h-[120px]"
            placeholder={`Write ${q.min_words || 70}-${q.max_words || 170} words…`}
            value={value}
            onChange={e => onChange(e.target.value)}
          />
        </>
      ) : mic.status === "recording" ? (
        <Button variant="secondary" data-testid={TID.oaMicStopBtn(q.id)} onClick={mic.stop} className="!py-2 !px-4" style={{ fontSize: 14 }}>Stop</Button>
      ) : mic.status === "uploading" ? (
        <div style={BODY}>Transcribing…</div>
      ) : (
        <div className="flex items-center gap-3 flex-wrap">
          <Button data-testid={TID.oaMicRecordBtn(q.id)} onClick={mic.start} className="!py-2 !px-4" style={{ fontSize: 14 }}>
            {value ? "Re-record" : "Record"}
          </Button>
          <button onClick={() => setTypedMode(true)} className="underline underline-offset-2" style={{ fontSize: 14, color: "var(--pm-teal-deep)", fontWeight: 600 }}>Type instead</button>
        </div>
      )}
      {value && !typedMode && (
        <div className="mt-3">
          <div className="mb-1" style={META}>Transcript (edit if needed):</div>
          <textarea
            data-testid={TID.oaTranscriptInput(q.id)}
            className="pm-input min-h-[100px]"
            value={value}
            onChange={e => onChange(e.target.value)}
          />
        </div>
      )}
    </Card>
  );
}

function CommMixedSection({ attemptId, section, answers, setAnswer }) {
  const qs = section.questions || [];
  return (
    <div className="space-y-4">
      {qs.length === 0 && <EmptyNotice>Question generation returned empty. Try re-starting this run.</EmptyNotice>}
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
        <Card key={q.id}>
          <div className="pm-eyebrow mb-2" style={{ color: "rgba(11,42,48,0.7)" }}>Q{i + 1} of {qs.length}</div>
          <div className="font-display font-semibold mb-4" style={{ fontSize: 19, color: "var(--pm-ink)", lineHeight: 1.4 }}><MD>{q.prompt}</MD></div>
          <div className="grid grid-cols-1 gap-2">
            {(q.options || []).map((opt, ix) => {
              const selected = answers[q.id] === ix;
              return (
                <button
                  key={ix}
                  data-testid={TID.oaQuestionOption(q.id, ix)}
                  aria-pressed={selected}
                  onClick={() => setAnswer(q.id, ix)}
                  className="text-left rounded-[14px] px-4 py-3 flex items-start gap-3 transition-colors hover:bg-[rgba(15,111,122,0.06)] focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[var(--pm-teal-night)]"
                  style={optionStyle(selected)}
                >
                  <LetterBadge letter={String.fromCharCode(65 + ix)} selected={selected} />
                  <div className="flex-1" style={{ fontSize: 15, lineHeight: 1.5, paddingTop: 2 }}>{opt}</div>
                </button>
              );
            })}
          </div>
        </Card>
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
      {qs.length === 0 && <EmptyNotice>Question generation returned empty. Try re-starting this run.</EmptyNotice>}
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
  if (!problem) return <EmptyNotice>No problems generated.</EmptyNotice>;

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
        <div className="flex gap-2 mb-4 flex-wrap">
          {qs.map((q, i) => (
            <button key={q.id} onClick={() => { setActiveIdx(i); setRunResults(null); }}
              aria-pressed={i === activeIdx}
              className="px-4 py-2 rounded-full font-display font-semibold transition-colors focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[var(--pm-teal-night)]"
              style={i === activeIdx
                ? { fontSize: 14, background: "var(--pm-teal-deep)", color: "var(--pm-white)", border: "1.5px solid var(--pm-teal-deep)" }
                : { fontSize: 14, background: "var(--pm-sky)", color: "var(--pm-ink)", border: "1.5px solid transparent" }}>
              Problem {i+1}
            </button>
          ))}
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:h-[70vh]">
        {/* Left: problem */}
        <Card className="overflow-y-auto" style={{ minHeight: 0 }}>
          <div className="flex items-start justify-between gap-3 mb-2">
            <CardTitle style={{ fontSize: 22 }}>{problem.title}</CardTitle>
            <Chip tone="status">{problem.difficulty}</Chip>
          </div>
          <div style={BODY}><MD>{problem.statement}</MD></div>
          {problem.input_format && <div className="mt-4"><div className="pm-eyebrow mb-1" style={{ color: "rgba(11,42,48,0.7)" }}>Input</div><div style={BODY}>{problem.input_format}</div></div>}
          {problem.output_format && <div className="mt-3"><div className="pm-eyebrow mb-1" style={{ color: "rgba(11,42,48,0.7)" }}>Output</div><div style={BODY}>{problem.output_format}</div></div>}
          {problem.constraints && <div className="mt-3"><div className="pm-eyebrow mb-1" style={{ color: "rgba(11,42,48,0.7)" }}>Constraints</div><div className="font-mono" style={{ fontSize: 14, color: "var(--pm-ink)" }}>{problem.constraints}</div></div>}

          <div className="mt-6">
            <div className="pm-eyebrow mb-2" style={{ color: "rgba(11,42,48,0.7)" }}>Visible tests</div>
            <div className="space-y-2">
              {(problem.visible_tests || []).map((t, i) => (
                <div key={i} className="rounded-[14px] p-3 font-mono" style={{ fontSize: 13, border: "1px solid rgba(7,59,67,0.12)", background: "var(--pm-grey)", color: "var(--pm-ink)" }}>
                  <div><span style={{ color: "rgba(11,42,48,0.7)" }}>input:</span> {t.input}</div>
                  <div><span style={{ color: "rgba(11,42,48,0.7)" }}>expected:</span> {t.expected_output}</div>
                </div>
              ))}
            </div>
          </div>

          {runResults && (
            <div className="mt-6">
              <div className="pm-eyebrow mb-2" style={{ color: "rgba(11,42,48,0.7)" }}>Run results</div>
              <div className="space-y-2">
                {runResults.map((r, i) => (
                  <div key={i} className="rounded-[14px] p-3" style={{ fontSize: 13, background: r.passed ? "var(--pm-success-bg)" : "var(--pm-error-bg)", color: "var(--pm-ink)", border: `1px solid ${r.passed ? "rgba(15,111,122,0.35)" : "rgba(180,35,24,0.35)"}` }}>
                    <div className="flex items-center gap-2 font-semibold">
                      {r.passed ? <CheckCircle2 size={14} style={{ color: "var(--pm-teal-deep)" }}/> : <XCircle size={14} style={{ color: "var(--pm-error-text)" }}/>}
                      Test {i+1} · {r.passed ? "passed" : "failed"}
                    </div>
                    <div className="mt-1 font-mono" style={{ color: "rgba(11,42,48,0.85)" }}>expected: {r.expected}</div>
                    <div className="font-mono" style={{ color: "rgba(11,42,48,0.85)" }}>got: {r.got || (r.error ? `(error) ${r.error}` : "")}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        {/* Right: editor — dark Monaco for regular coding, plain textarea for pen-paper mode. */}
        {penPaper ? (
          <Card padding="16px" className="flex flex-col">
            <div className="flex items-center justify-between gap-2 mb-2">
              <Chip>pen-paper mode · no run button</Chip>
              <div style={META}>Zoho style</div>
            </div>
            <textarea
              data-testid={TID.oaCodeArea}
              value={current.code}
              onChange={e => setForProblem({ code: e.target.value })}
              placeholder="Write your full program here. No autocomplete. No test runner. Just like paper."
              autoComplete="off" autoCorrect="off" spellCheck={false}
              className="pm-input flex-1 min-h-[400px] font-mono"
              style={{ background: "var(--pm-sky)", color: "var(--pm-ink)", fontSize: 14, lineHeight: 1.6, tabSize: 4 }}
            />
            <div className="mt-2" style={META}>{(current.code || "").split("\n").length} lines · {(current.code || "").length} chars</div>
          </Card>
        ) : (
        <div className="pm-editor-pane rounded-[24px] overflow-hidden flex flex-col">
          <div className="flex items-center justify-between gap-3 flex-wrap px-4 py-3 border-b border-white/5">
            <div className="flex items-center gap-2 flex-wrap">
              <select
                data-testid={TID.oaLangSelect}
                value={current.language}
                onChange={e => setForProblem({ language: e.target.value })}
                className="bg-transparent rounded-[10px] px-2 py-1 font-mono"
                style={{ fontSize: 13, border: "1px solid rgba(255,255,255,0.35)", color: "var(--pm-white)" }}
              >
                <option value="python">Python 3</option>
                <option value="javascript">JavaScript</option>
                <option value="c">C</option>
                <option value="cpp">C++</option>
                <option value="java">Java</option>
              </select>
              {automataFix && <Chip>automata fix · code pre-filled</Chip>}
            </div>
            <Button data-testid={TID.oaRunBtn} onClick={runCode} disabled={running} className="!py-1.5 !px-3" style={{ fontSize: 13 }}>
              <Play size={12} aria-hidden="true"/> {running ? "running…" : "Run visible tests"}
            </Button>
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

  if (!session) return <EmptyNotice>Loading your problem…</EmptyNotice>;

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
