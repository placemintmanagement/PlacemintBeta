import React, { useEffect, useState, useMemo, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import Editor from "@monaco-editor/react";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import ChartQuestion from "../components/charts/ChartQuestion";
import { TID } from "../testIds";
import { Clock, Play, ChevronRight, CheckCircle2, XCircle, Star, RotateCcw, Circle, Square, Triangle, ArrowUp } from "lucide-react";

// Deductive Challenge (mini-sudoku) symbol names (from capgemini_challenges.py's
// _SUDOKU_SYMBOLS) mapped to their lucide-react icon components.
const SUDOKU_ICONS = { circle: Circle, square: Square, triangle: Triangle, star: Star };

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
          <h1 className="font-display text-3xl font-bold text-red-600">Generation failed.</h1>
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
              ? "Sections generate in parallel — the first one usually lands in under 20 seconds."
              : "Almost there — you can start this section the moment it's ready."}
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
      toast.success(`Section done — score ${(data.section_result.score * 100).toFixed(0)}%`);
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
            <button data-testid={TID.oaFinishSection} onClick={submitSection} disabled={submitting}
                    className="pm-btn pm-btn-primary text-sm py-2 px-4">
              {submitting ? "Grading…" : <>Submit section <ChevronRight size={14}/></>}
            </button>
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
        ) : (currentSection.type === "cognitive_game" || currentSection.type === "game") ? (
          <CognitiveGameSection section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} onAutoAdvanceEnd={submitSection} />
        ) : currentSection.type === "capgemini_challenges" ? (
          <CapgeminiChallengesSection section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} onAutoAdvanceEnd={submitSection} />
        ) : currentSection.type === "cognizant_games" ? (
          <CognizantGamesSection section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} onAutoAdvanceEnd={submitSection} />
        ) : currentSection.type === "accenture_games" ? (
          <AccentureGamesSection section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} onAutoAdvanceEnd={submitSection} />
        ) : (
          <MCQSection section={currentSection} answers={sectionAnswers} setAnswer={setAnswer} />
        )}
      </div>
    </div>
  );
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
// Shared MediaRecorder -> POST /oa/{attemptId}/transcribe flow. Falls back to
// `status === "unavailable"` (caller renders a typed textarea instead) if
// getUserMedia is missing, denied, or errors — there is no mic requirement
// anywhere else in this app, so this has to degrade gracefully.
function useMicRecorder(attemptId, sectionKey, questionId, onTranscript) {
  const [status, setStatus] = useState("idle"); // idle | recording | uploading | done | unavailable | error
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  const start = async () => {
    if (!navigator.mediaDevices?.getUserMedia) { setStatus("unavailable"); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const mr = new MediaRecorder(stream);
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = async () => {
        streamRef.current?.getTracks().forEach(t => t.stop());
        setStatus("uploading");
        try {
          const blob = new Blob(chunksRef.current, { type: "audio/webm" });
          const fd = new FormData();
          fd.append("section_key", sectionKey);
          fd.append("question_id", questionId);
          fd.append("file", blob, "recording.webm");
          const { data } = await api.post(`/oa/${attemptId}/transcribe`, fd, { headers: { "Content-Type": "multipart/form-data" } });
          onTranscript(data.transcript || "");
          setStatus("done");
        } catch (err) {
          toast.error("Transcription failed — you can type your answer instead.");
          setStatus("error");
        }
      };
      mediaRecorderRef.current = mr;
      mr.start();
      setStatus("recording");
    } catch (err) {
      setStatus("unavailable");
    }
  };

  const stop = () => { mediaRecorderRef.current?.stop(); };
  const reset = () => setStatus("idle");

  return { status, start, stop, reset };
}

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
          <div className="text-xs text-pm-text2">Mic unavailable — type your response instead.</div>
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
      <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Sentence {idx + 1} of {total} — read aloud</div>
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
      <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Q{idx + 1} of {total} — spoken response</div>
      <div className="font-display text-lg font-semibold mb-1">{q.topic}</div>
      <div className="text-sm text-pm-text2 mb-4">{q.instructions}</div>
      {typedMode ? (
        <>
          <div className="text-xs text-pm-text2 mb-2">Mic unavailable — type your response instead.</div>
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
              style={{ background: "#F3F0E6", color: "#0A0A0A", lineHeight: 1.6, tabSize: 4 }}
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
              className="pm-btn text-xs py-1.5 px-3" style={{ background: "#0FAE73", color: "#fff" }}>
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

// -------- Cognitive Game (Accenture "cognitive_game", IBM/Capgemini "game") --
// Per-question timer. When the timer expires we auto-record the current selection
// (or -1 if none), advance to the next question, and when done auto-submit.
function CognitiveGameSection({ section, answers, setAnswer, onAutoAdvanceEnd }) {
  const qs = section.questions || [];
  const perQ = section.per_question_seconds || 15;
  const [idx, setIdx] = useState(0);
  const [remaining, setRemaining] = useState(perQ);
  const timerRef = useRef(null);

  const currentQ = qs[idx];

  useEffect(() => {
    setRemaining(perQ);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          clearInterval(timerRef.current);
          // Lock in whatever the user has selected; -1 means skipped.
          setAnswer(currentQ.id, answers[currentQ.id] ?? -1);
          if (idx + 1 < qs.length) {
            setIdx(idx + 1);
          } else if (onAutoAdvanceEnd) {
            setTimeout(onAutoAdvanceEnd, 200);
          }
          return perQ;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx]);

  if (!currentQ) return <div className="pm-card p-6">No questions generated.</div>;

  const chooseAndAdvance = (i) => {
    setAnswer(currentQ.id, i);
    // Small delay so user sees selection highlight
    setTimeout(() => {
      if (idx + 1 < qs.length) setIdx(idx + 1);
      else if (onAutoAdvanceEnd) onAutoAdvanceEnd();
    }, 250);
  };

  const styleChip = {
    // Accenture/IBM (cognitive_game_prompt)
    pattern: "pattern",
    sequence: "odd-one-out",
    spatial: "spatial",
    speed_math: "speed math",
    // Capgemini's own distinct categories (capgemini_challenges.py) — same
    // component, same visual treatment, just its own real category names.
    deductive_challenge: "Deductive Challenge",
    inductive_challenge: "Inductive Challenge",
    grid_challenge: "Grid Challenge",
    switch_challenge: "Switch Challenge",
    motion_challenge: "Motion Challenge",
    digit_challenge: "Digit Challenge",
  }[currentQ.style] || "cognitive";

  return (
    <div className="pm-card p-8 max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="pm-chip pm-chip-primary">Q{idx + 1} / {qs.length}</span>
          <span className="pm-chip">{styleChip}</span>
        </div>
        {/* Per-question countdown — turns coral in the last 5 seconds */}
        <div className={`pm-chip text-lg py-2 px-4 font-mono ${remaining <= 5 ? "pm-chip-coral" : "pm-chip-primary"}`}>
          {String(remaining).padStart(2, "0")}s
        </div>
      </div>
      <div className="font-display text-2xl font-bold my-6 text-center leading-snug"><MD>{currentQ.prompt}</MD></div>
      <div className="grid grid-cols-2 gap-3">
        {(currentQ.options || []).map((opt, ix) => {
          const selected = answers[currentQ.id] === ix;
          return (
            <button
              key={ix}
              data-testid={TID.oaQuestionOption(currentQ.id, ix)}
              onClick={() => chooseAndAdvance(ix)}
              className={`text-center border-2 rounded-xl p-4 font-mono text-lg transition ${selected ? "border-pm-primary bg-pm-primary/10" : "border-pm-border hover:border-pm-primary/40 hover:bg-pm-primary/5"}`}
            >
              <span className="text-xs font-bold text-pm-text2 mr-2">{String.fromCharCode(65 + ix)}</span> {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// -------- Capgemini's own Cognitive Challenges (bespoke rebuild) -----------
// Full rebuild (2026-07-19) of Capgemini's 6 challenge categories as genuine
// bespoke interactive puzzles — NOT the shared CognitiveGameSection MCQ-button
// UI. Batch 1: Deductive + Grid Challenge. Inductive/Switch/Motion/Digit are
// still old-shape (rendered via the CognitiveGameSection-style single-MCQ
// fallback below) pending their own batches — capgemini_challenges.py's
// generate_capgemini_challenges() returns a MIX of both shapes during this
// transition, and CapgeminiChallengesSection below dispatches on which shape
// each item actually is.

// Shared sub-puzzle-sequencing state, reused by every rebuilt challenge type.
function useSubPuzzleFlow(subPuzzles, onChallengeComplete) {
  const [subIdx, setSubIdx] = useState(0);
  const [collected, setCollected] = useState([]);
  const total = subPuzzles.length;
  const current = subPuzzles[subIdx];

  const submitSub = (answer) => {
    const next = [...collected, answer];
    if (subIdx + 1 < total) {
      setCollected(next);
      setSubIdx(subIdx + 1);
    } else {
      onChallengeComplete(next);
    }
  };

  return { subIdx, total, current, submitSub };
}

function DeductiveChallengeGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const [grid, setGrid] = useState(() => current.grid.map((row) => [...row]));
  const [selectedCell, setSelectedCell] = useState(null);

  useEffect(() => {
    setGrid(current.grid.map((row) => [...row]));
    setSelectedCell(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subIdx]);

  const isGiven = (r, c) => current.grid[r][c] !== null;
  const clickCell = (r, c) => { if (!isGiven(r, c)) setSelectedCell([r, c]); };
  const placeSymbol = (sym) => {
    if (!selectedCell) return;
    const [r, c] = selectedCell;
    const next = grid.map((row) => [...row]);
    next[r][c] = sym;
    setGrid(next);
  };

  const isComplete = grid.every((row) => row.every((cell) => cell !== null));
  const isValid = (() => {
    if (!isComplete) return false;
    const { size, region_size: regionSize, symbols } = current;
    const expected = new Set(symbols);
    const sameSet = (arr) => arr.length === expected.size && new Set(arr).size === expected.size && arr.every((v) => expected.has(v));
    for (let r = 0; r < size; r++) if (!sameSet(grid[r])) return false;
    for (let c = 0; c < size; c++) if (!sameSet(grid.map((row) => row[c]))) return false;
    for (let br = 0; br < size; br += regionSize) {
      for (let bc = 0; bc < size; bc += regionSize) {
        const block = [];
        for (let r = br; r < br + regionSize; r++) for (let c = bc; c < bc + regionSize; c++) block.push(grid[r][c]);
        if (!sameSet(block)) return false;
      }
    }
    return true;
  })();

  return (
    <div className="max-w-md mx-auto">
      <div className="flex items-center justify-between mb-4">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
        {isComplete && (
          <span className={`pm-chip font-mono ${isValid ? "pm-chip-primary" : "pm-chip-coral"}`}>
            {isValid ? "Valid!" : "Not valid yet"}
          </span>
        )}
      </div>
      <div
        className="grid gap-1 mx-auto mb-4"
        style={{ gridTemplateColumns: `repeat(${current.size}, minmax(0,1fr))`, maxWidth: 280 }}
      >
        {grid.map((row, r) => row.map((cell, c) => {
          const given = isGiven(r, c);
          const isSel = selectedCell && selectedCell[0] === r && selectedCell[1] === c;
          const Icon = cell ? SUDOKU_ICONS[cell] : null;
          return (
            <button
              key={`${r}-${c}`}
              data-testid={TID.oaCardTile(current.id || `deductive-${subIdx}`, `${r}-${c}`)}
              onClick={() => clickCell(r, c)}
              disabled={given}
              className={`aspect-square rounded-lg border-2 flex items-center justify-center transition ${
                given ? "border-pm-border bg-pm-surface-muted" : isSel ? "border-pm-primary bg-pm-primary/10" : "border-pm-border bg-white hover:border-pm-primary/40"
              }`}
            >
              {Icon && <Icon size={22} className={given ? "text-pm-text2" : "text-pm-primary-dark"} />}
            </button>
          );
        }))}
      </div>
      <div className="flex items-center justify-center gap-3 mb-6">
        {current.symbols.map((sym) => {
          const Icon = SUDOKU_ICONS[sym];
          return (
            <button
              key={sym}
              onClick={() => placeSymbol(sym)}
              disabled={!selectedCell}
              className="w-12 h-12 rounded-xl border-2 border-pm-border bg-white hover:border-pm-primary/40 disabled:opacity-40 flex items-center justify-center transition"
            >
              <Icon size={22} className="text-pm-primary-dark" />
            </button>
          );
        })}
      </div>
      <div className="text-center">
        <button
          onClick={() => submitSub({ grid })}
          disabled={!isValid}
          className="pm-btn pm-btn-primary text-sm disabled:opacity-40"
        >
          {subIdx + 1 < total ? "Continue" : "Finish challenge"} <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

function GridChallengeGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const [selected, setSelected] = useState(null);

  useEffect(() => { setSelected(null); }, [subIdx]);

  const [blankR, blankC] = current.blank_position;

  return (
    <div className="max-w-md mx-auto">
      <div className="flex items-center justify-between mb-4">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
      </div>
      <div className="grid grid-cols-3 gap-2 mx-auto mb-6" style={{ maxWidth: 240 }}>
        {current.grid.map((row, r) => row.map((cell, c) => {
          const isBlank = r === blankR && c === blankC;
          return (
            <div
              key={`${r}-${c}`}
              className={`aspect-square rounded-lg border-2 flex items-center justify-center font-mono text-lg ${
                isBlank ? (selected !== null ? "border-pm-primary bg-pm-primary/10 text-pm-primary-dark font-bold" : "border-dashed border-pm-secondary bg-pm-surface-muted") : "border-pm-border bg-white text-pm-text"
              }`}
            >
              {isBlank ? (selected !== null ? selected : "?") : cell}
            </div>
          );
        }))}
      </div>
      <div className="grid grid-cols-2 gap-3 mb-6">
        {current.options.map((opt, ix) => (
          <button
            key={ix}
            data-testid={TID.oaQuestionOption(current.id || `grid-${subIdx}`, ix)}
            onClick={() => setSelected(opt)}
            className={`text-center border-2 rounded-xl p-3 font-mono text-lg transition ${selected === opt ? "border-pm-primary bg-pm-primary/10" : "border-pm-border hover:border-pm-primary/40 hover:bg-pm-primary/5"}`}
          >
            {opt}
          </button>
        ))}
      </div>
      <div className="text-center">
        <button
          onClick={() => submitSub({ selected_value: selected })}
          disabled={selected === null}
          className="pm-btn pm-btn-primary text-sm disabled:opacity-40"
        >
          {subIdx + 1 < total ? "Continue" : "Finish challenge"} <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

// Shared shape renderer for Switch Challenge — reuses the same 4 icons as
// Deductive Challenge's sudoku symbols, just with color/rotation/scale
// animated via Framer Motion instead of placed in a grid cell.
const SWITCH_COLOR_CLASS = { primary: "text-pm-primary", secondary: "text-pm-secondary", dark: "text-pm-text" };

function VisualShape({ shape, color, rotation = 0, scale = 1, size = 48 }) {
  const Icon = SUDOKU_ICONS[shape] || Circle;
  return (
    <motion.div
      animate={{ rotate: rotation, scale }}
      transition={{ duration: 0.5, ease: "easeInOut" }}
      className="flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <Icon size={size * 0.6} className={SWITCH_COLOR_CLASS[color] || "text-pm-text"} strokeWidth={2.5} />
    </motion.div>
  );
}

function SwitchChallengeGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const [demoKey, setDemoKey] = useState(0);
  const [selected, setSelected] = useState(null);

  useEffect(() => { setSelected(null); setDemoKey((n) => n + 1); }, [subIdx]);

  return (
    <div className="max-w-lg mx-auto">
      <div className="flex items-center justify-between mb-4">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
        <button onClick={() => setDemoKey((n) => n + 1)} className="pm-chip hover:bg-pm-surface-muted transition">
          <RotateCcw size={12} /> Replay
        </button>
      </div>

      <div className="pm-card p-6 mb-6 bg-pm-surface-muted/50">
        <div className="text-xs font-mono uppercase tracking-widest text-pm-text2 mb-3 text-center">Watch the rule</div>
        <div className="flex items-center justify-center gap-6">
          <div className="text-center">
            <VisualShape {...current.example_before} />
            <div className="text-xs text-pm-text2 mt-1">Before</div>
          </div>
          <ChevronRight className="text-pm-text-muted" />
          <div className="text-center">
            <motion.div
              key={demoKey}
              initial={{ rotate: current.example_before.rotation, scale: current.example_before.scale }}
              animate={{ rotate: current.example_after.rotation, scale: current.example_after.scale }}
              transition={{ duration: 0.8, ease: "easeInOut" }}
              className="flex items-center justify-center"
              style={{ width: 48, height: 48 }}
            >
              {(() => {
                const Icon = SUDOKU_ICONS[current.example_after.shape] || Circle;
                return <Icon size={30} className={SWITCH_COLOR_CLASS[current.example_after.color] || "text-pm-text"} strokeWidth={2.5} />;
              })()}
            </motion.div>
            <div className="text-xs text-pm-text2 mt-1">After</div>
          </div>
        </div>
      </div>

      <div className="text-center mb-4">
        <div className="text-xs font-mono uppercase tracking-widest text-pm-text2 mb-3">Now apply the SAME rule to:</div>
        <VisualShape {...current.new_before} />
      </div>
      <div className="grid grid-cols-4 gap-3 mb-6">
        {current.options.map((opt, ix) => (
          <button
            key={ix}
            data-testid={TID.oaQuestionOption(current.id || `switch-${subIdx}`, ix)}
            onClick={() => setSelected(ix)}
            className={`pm-card p-3 flex items-center justify-center transition ${selected === ix ? "border-pm-primary bg-pm-primary/10" : "hover:border-pm-primary/40"}`}
          >
            <VisualShape {...opt} size={40} />
          </button>
        ))}
      </div>
      <div className="text-center">
        <button
          onClick={() => submitSub({ selected_index: selected })}
          disabled={selected === null}
          className="pm-btn pm-btn-primary text-sm disabled:opacity-40"
        >
          {subIdx + 1 < total ? "Continue" : "Finish challenge"} <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

function MotionChallengeGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const [frameIx, setFrameIx] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    setFrameIx(0);
    setPlaying(true);
    setSelected(null);
  }, [subIdx]);

  useEffect(() => {
    if (!playing) return undefined;
    if (frameIx >= current.frames.length - 1) {
      const t = setTimeout(() => setPlaying(false), 500);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setFrameIx((i) => i + 1), 700);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, frameIx]);

  const replay = () => { setFrameIx(0); setPlaying(true); setSelected(null); };

  return (
    <div className="max-w-md mx-auto text-center">
      <div className="flex items-center justify-between mb-4">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
        <button onClick={replay} className="pm-chip hover:bg-pm-surface-muted transition">
          <RotateCcw size={12} /> Replay
        </button>
      </div>
      <div className="pm-card p-8 mb-6 bg-pm-surface-muted/50">
        <div className="text-xs font-mono uppercase tracking-widest text-pm-text2 mb-4">
          {playing ? `Frame ${frameIx + 1} of ${current.frames.length}` : "What comes next?"}
        </div>
        <div className="flex items-center justify-center" style={{ height: 80 }}>
          {playing ? (
            <motion.div animate={{ rotate: current.frames[frameIx] }} transition={{ duration: 0.5, ease: "easeInOut" }}>
              <ArrowUp size={48} className="text-pm-primary-dark" strokeWidth={2.5} />
            </motion.div>
          ) : (
            <span className="text-3xl font-display font-bold text-pm-text-muted">?</span>
          )}
        </div>
      </div>
      {!playing && (
        <>
          <div className="grid grid-cols-4 gap-3 mb-6">
            {current.options.map((rot, ix) => (
              <button
                key={ix}
                data-testid={TID.oaQuestionOption(current.id || `motion-${subIdx}`, ix)}
                onClick={() => setSelected(ix)}
                className={`pm-card p-3 flex items-center justify-center transition ${selected === ix ? "border-pm-primary bg-pm-primary/10" : "hover:border-pm-primary/40"}`}
              >
                <motion.div animate={{ rotate: rot }} transition={{ duration: 0.3 }}>
                  <ArrowUp size={28} className="text-pm-text" strokeWidth={2.5} />
                </motion.div>
              </button>
            ))}
          </div>
          <button
            onClick={() => submitSub({ selected_index: selected })}
            disabled={selected === null}
            className="pm-btn pm-btn-primary text-sm disabled:opacity-40"
          >
            {subIdx + 1 < total ? "Continue" : "Finish challenge"} <ChevronRight size={14} />
          </button>
        </>
      )}
    </div>
  );
}

function InductiveChallengeGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const [typed, setTyped] = useState("");

  useEffect(() => { setTyped(""); }, [subIdx]);

  const submit = () => { if (typed.trim() !== "") submitSub({ typed_value: typed.trim() }); };

  return (
    <div className="max-w-md mx-auto">
      <div className="flex items-center justify-between mb-4">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
      </div>
      <div className="pm-card p-6 mb-6 bg-pm-surface-muted/50">
        <div className="text-xs font-mono uppercase tracking-widest text-pm-text2 mb-3 text-center">These follow a hidden rule</div>
        <div className="space-y-2">
          {current.examples.map((ex, i) => (
            <div key={i} className="flex items-center justify-center gap-3 font-mono text-lg">
              <span className="pm-chip">{ex.input}</span>
              <ChevronRight size={16} className="text-pm-text-muted" />
              <span className="pm-chip pm-chip-primary">{ex.output}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="text-center mb-6">
        <div className="text-xs font-mono uppercase tracking-widest text-pm-text2 mb-3">Apply the same rule</div>
        <div className="flex items-center justify-center gap-3">
          <span className="pm-chip text-lg py-2 px-4 font-mono">{current.new_input}</span>
          <ChevronRight size={18} className="text-pm-text-muted" />
          <input
            type="number"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            data-testid={TID.oaTypedInput(current.id || `inductive-${subIdx}`)}
            className="pm-input w-28 text-center font-mono text-lg"
            placeholder="?"
          />
        </div>
      </div>
      <div className="text-center">
        <button onClick={submit} disabled={typed.trim() === ""} className="pm-btn pm-btn-primary text-sm disabled:opacity-40">
          {subIdx + 1 < total ? "Continue" : "Finish challenge"} <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

function DigitChallengeGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const [typed, setTyped] = useState("");
  const [placedTileIx, setPlacedTileIx] = useState({}); // {position: tileIndex}
  const [selectedTileIx, setSelectedTileIx] = useState(null);

  useEffect(() => {
    setTyped("");
    setPlacedTileIx({});
    setSelectedTileIx(null);
  }, [subIdx]);

  if (current.variant === "type_in") {
    const submit = () => { if (typed.trim() !== "") submitSub({ typed_value: typed.trim() }); };
    return (
      <div className="max-w-md mx-auto text-center">
        <div className="flex items-center justify-between mb-4">
          <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
        </div>
        <div className="text-xs font-mono uppercase tracking-widest text-pm-text2 mb-4">What comes next?</div>
        <div className="flex items-center justify-center gap-2 mb-6 flex-wrap">
          {current.sequence.map((v, i) => (
            <span key={i} className="pm-chip text-lg py-2 px-4 font-mono">{v}</span>
          ))}
          <input
            type="number"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            data-testid={TID.oaTypedInput(current.id || `digit-${subIdx}`)}
            className="pm-input w-24 text-center font-mono text-lg"
            placeholder="?"
          />
        </div>
        <button onClick={submit} disabled={typed.trim() === ""} className="pm-btn pm-btn-primary text-sm disabled:opacity-40">
          {subIdx + 1 < total ? "Continue" : "Finish challenge"} <ChevronRight size={14} />
        </button>
      </div>
    );
  }

  // arrange_tiles variant — click a tile, then click a blank slot to place
  // it (click a filled slot again to clear it); same click-to-place
  // interaction as Deductive/Grid Challenge, not drag-and-drop.
  const usedTileIndices = new Set(Object.values(placedTileIx));

  const clickTile = (tileIx) => { if (!usedTileIndices.has(tileIx)) setSelectedTileIx(tileIx); };
  const clickSlot = (position) => {
    if (placedTileIx[position] !== undefined) {
      const next = { ...placedTileIx };
      delete next[position];
      setPlacedTileIx(next);
      return;
    }
    if (selectedTileIx === null) return;
    setPlacedTileIx({ ...placedTileIx, [position]: selectedTileIx });
    setSelectedTileIx(null);
  };

  const allSlotsFilled = current.blank_positions.every((p) => placedTileIx[p] !== undefined);
  const submitArrange = () => {
    const placedValues = {};
    for (const pos of current.blank_positions) placedValues[pos] = current.tiles[placedTileIx[pos]];
    submitSub({ placed: placedValues });
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="flex items-center justify-between mb-4">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
      </div>
      <div className="text-xs font-mono uppercase tracking-widest text-pm-text2 mb-4 text-center">Place the tiles to complete the sequence</div>
      <div className="flex items-center justify-center gap-2 mb-6 flex-wrap">
        {current.sequence.map((v, i) => {
          if (v !== null) return <span key={i} className="pm-chip text-lg py-2 px-4 font-mono">{v}</span>;
          const tileIx = placedTileIx[i];
          const filled = tileIx !== undefined;
          return (
            <button
              key={i}
              data-testid={TID.oaDigitSlot(current.id || `digit-${subIdx}`, i)}
              onClick={() => clickSlot(i)}
              className={`w-16 h-11 rounded-lg border-2 flex items-center justify-center font-mono text-lg transition ${
                filled ? "border-pm-primary bg-pm-primary/10 text-pm-primary-dark font-bold" : "border-dashed border-pm-secondary bg-pm-surface-muted"
              }`}
            >
              {filled ? current.tiles[tileIx] : "?"}
            </button>
          );
        })}
      </div>
      <div className="flex items-center justify-center gap-3 mb-6">
        {current.tiles.map((t, ix) => (
          <button
            key={ix}
            data-testid={TID.oaDigitTile(current.id || `digit-${subIdx}`, ix)}
            onClick={() => clickTile(ix)}
            disabled={usedTileIndices.has(ix)}
            className={`w-14 h-14 rounded-xl border-2 font-mono text-lg transition ${
              usedTileIndices.has(ix) ? "opacity-30 border-pm-border" : selectedTileIx === ix ? "border-pm-primary bg-pm-primary/10" : "border-pm-border bg-white hover:border-pm-primary/40"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="text-center">
        <button onClick={submitArrange} disabled={!allSlotsFilled} className="pm-btn pm-btn-primary text-sm disabled:opacity-40">
          {subIdx + 1 < total ? "Continue" : "Finish challenge"} <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

const CAPGEMINI_CHALLENGE_INTROS = {
  deductive_challenge: { title: "Deductive Challenge", body: "A mini logic grid. Place each shape so every row, column, and 2×2 block contains all 4 shapes exactly once." },
  grid_challenge: { title: "Grid Challenge", body: "Each grid follows a consistent row/column pattern. Work out the rule and pick the value that completes it." },
  inductive_challenge: { title: "Inductive Challenge", body: "Study the example pairs, infer the hidden rule, then apply it." },
  switch_challenge: { title: "Switch Challenge", body: "Watch the transformation, then apply the same rule to a new item." },
  motion_challenge: { title: "Motion Challenge", body: "Watch the motion sequence, then predict what comes next." },
  digit_challenge: { title: "Digit Challenge", body: "Complete the numeric pattern." },
};

const COGNIZANT_GAME_INTROS = {
  connect_pairs: { title: "Connect the Pairs", body: "Connect every point to exactly one other point so that no two connecting lines cross." },
  pattern_break: { title: "Pattern Break", body: "A hidden rule generates this sequence. Click the one number that breaks it." },
  speed_math_chain: { title: "Speed Math Chain", body: "Follow the chain of operations from the starting number and enter the final result." },
  shape_rotation: { title: "Shape Rotation", body: "One option is a true rotation of the base shape. The others are mirror images. Click the true rotation." },
};

const ACCENTURE_GAME_INTROS = {
  number_sort: { title: "Number Sorting", body: "Click the tiles in order from smallest value to largest." },
  path_finding: { title: "Path-Finding", body: "Starting at the marked cell, follow each arrow to the next cell until you exit the grid. Click where you exit." },
  key_door_maze: { title: "Key-Door Maze", body: "Click the one key that's both reachable from the start and matches the door's color." },
};

const _DIR_ROTATE = { up: 0, right: 90, down: 180, left: 270 };
const _KEY_COLOR_HEX = { red: "#DC2626", blue: "#2563EB", green: "#16A34A", yellow: "#CA8A04", purple: "#7C3AED" };

function CapgeminiChallengesSection({ section, answers, setAnswer, onAutoAdvanceEnd }) {
  const challenges = section.questions || [];
  const [challengeIdx, setChallengeIdx] = useState(0);
  const [phase, setPhase] = useState("intro"); // intro -> playing

  const challenge = challenges[challengeIdx];
  if (!challenge) return <div className="pm-card p-6">No challenges generated.</div>;

  const advanceChallenge = () => {
    if (challengeIdx + 1 < challenges.length) {
      setChallengeIdx(challengeIdx + 1);
      setPhase("intro");
    } else if (onAutoAdvanceEnd) {
      onAutoAdvanceEnd();
    }
  };

  const handleSubPuzzleChallengeComplete = (perSubAnswers) => {
    perSubAnswers.forEach((ans, i) => setAnswer(`${challenge.id}_${i}`, ans));
    advanceChallenge();
  };

  const type = challenge.type || challenge.style;
  const intro = CAPGEMINI_CHALLENGE_INTROS[type] || { title: "Cognitive Challenge", body: "" };

  return (
    <div className="pm-card p-8">
      <div className="flex items-center gap-2 mb-6">
        <span className="pm-chip pm-chip-primary">Challenge {challengeIdx + 1} / {challenges.length}</span>
        <span className="pm-chip">{intro.title}</span>
      </div>

      {phase === "intro" ? (
        <div className="text-center py-8">
          <h3 className="font-display text-2xl font-bold mb-3">{intro.title}</h3>
          <p className="text-pm-text2 max-w-md mx-auto mb-6">{intro.body}</p>
          <button onClick={() => setPhase("playing")} className="pm-btn pm-btn-primary">
            <Play size={14} /> Start
          </button>
        </div>
      ) : "sub_puzzles" in challenge ? (
        type === "deductive_challenge" ? (
          <DeductiveChallengeGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
        ) : type === "grid_challenge" ? (
          <GridChallengeGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
        ) : type === "switch_challenge" ? (
          <SwitchChallengeGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
        ) : type === "motion_challenge" ? (
          <MotionChallengeGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
        ) : type === "inductive_challenge" ? (
          <InductiveChallengeGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
        ) : (
          <DigitChallengeGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
        )
      ) : (
        // Backward compatibility only — rebuild is complete as of 2026-07-19,
        // so no NEW attempt generates old-shape items anymore. This renders
        // any old-shape item still persisted in an OA attempt created before
        // this deploy (e.g. a candidate resuming an in-progress session).
        <div>
          <div className="font-display text-xl font-bold mb-6 text-center"><MD>{challenge.prompt}</MD></div>
          <div className="grid grid-cols-2 gap-3">
            {(challenge.options || []).map((opt, ix) => {
              const selected = answers[challenge.id] === ix;
              return (
                <button
                  key={ix}
                  data-testid={TID.oaQuestionOption(challenge.id, ix)}
                  onClick={() => { setAnswer(challenge.id, ix); setTimeout(advanceChallenge, 250); }}
                  className={`text-center border-2 rounded-xl p-4 font-mono text-lg transition ${selected ? "border-pm-primary bg-pm-primary/10" : "border-pm-border hover:border-pm-primary/40 hover:bg-pm-primary/5"}`}
                >
                  <span className="text-xs font-bold text-pm-text2 mr-2">{String.fromCharCode(65 + ix)}</span> {opt}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// -------- Cognizant gamified round (tile matching / memory / puzzle) -------
// NOT based on real Cognizant OA research — a deliberate new addition (see
// cognizant_games.py). Three genuinely new interaction patterns, cycled one
// at a time like CognitiveGameSection, but untimed per-item (the outer
// section-level countdown chip already provides overall time pressure —
// these are about accuracy, not per-question speed).

function ConnectPairsGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const [selected, setSelected] = useState(null);
  const [pairs, setPairs] = useState([]); // [{a, b}]

  useEffect(() => {
    setSelected(null);
    setPairs([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subIdx]);

  const points = current.points || [];
  const usedIds = new Set(pairs.flatMap((p) => [p.a, p.b]));

  const clickPoint = (pointId) => {
    if (usedIds.has(pointId)) return;
    if (selected === null) {
      setSelected(pointId);
    } else if (selected === pointId) {
      setSelected(null);
    } else {
      setPairs([...pairs, { a: selected, b: pointId }]);
      setSelected(null);
    }
  };

  const undo = () => setPairs(pairs.slice(0, -1));
  const submit = () => submitSub({ pairs: pairs.map((p) => [p.a, p.b]) });

  const byId = Object.fromEntries(points.map((p) => [p.point_id, p]));
  const done = pairs.length === current.n_pairs;

  return (
    <div className="max-w-lg mx-auto">
      <div className="flex items-center justify-between mb-4">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
      </div>
      <div className="pm-card p-4 mb-4">
        <svg
          viewBox={`0 0 ${current.canvas_width} ${current.canvas_height}`}
          width="100%"
          height={current.canvas_height}
        >
          {pairs.map((p, i) => (
            <line
              key={i}
              x1={byId[p.a].x} y1={byId[p.a].y} x2={byId[p.b].x} y2={byId[p.b].y}
              stroke="#0FAE73" strokeWidth="3" strokeLinecap="round"
            />
          ))}
          {points.map((p) => {
            const isUsed = usedIds.has(p.point_id);
            const isSelected = selected === p.point_id;
            return (
              <circle
                key={p.point_id}
                data-testid={TID.oaConnectPoint(`connect-${subIdx}`, p.point_id)}
                cx={p.x} cy={p.y} r={isSelected ? 10 : 8}
                fill={isUsed ? "#0FAE73" : isSelected ? "#FF6F4D" : "#0A0A0A"}
                style={{ cursor: isUsed ? "default" : "pointer" }}
                onClick={() => clickPoint(p.point_id)}
              />
            );
          })}
        </svg>
      </div>
      <div className="flex items-center justify-between">
        <span className="pm-chip font-mono">{pairs.length} / {current.n_pairs} connected</span>
        <div className="flex gap-2">
          <button
            data-testid={TID.oaConnectUndo(`connect-${subIdx}`)}
            onClick={undo}
            disabled={pairs.length === 0}
            className="pm-btn pm-btn-ghost text-sm"
          >
            <RotateCcw size={14} /> Undo
          </button>
          <button
            data-testid={TID.oaConnectSubmit(`connect-${subIdx}`)}
            onClick={submit}
            disabled={!done}
            className="pm-btn pm-btn-primary text-sm"
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
}

// -------- Pattern Break: click the number that breaks the sequence --------
function PatternBreakGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const sequence = current.sequence || [];

  return (
    <div className="max-w-lg mx-auto text-center">
      <div className="flex items-center justify-center mb-6">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
      </div>
      <div className="flex items-center justify-center gap-3 flex-wrap">
        {sequence.map((n, ix) => (
          <button
            key={ix}
            data-testid={TID.oaPatternTile(`pattern-${subIdx}`, ix)}
            onClick={() => submitSub({ selected_index: ix })}
            className="w-16 h-16 rounded-xl border-2 border-pm-border bg-white hover:border-pm-primary font-display font-bold text-xl transition"
          >
            {n}
          </button>
        ))}
      </div>
      <div className="text-xs text-pm-text2 mt-4">Click the number that breaks the pattern.</div>
    </div>
  );
}

// -------- Speed Math Chain: mental-math operation chain -------------------
const _OP_SYMBOL = { add: "+", subtract: "−", multiply: "×" };

function SpeedMathChainGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const [value, setValue] = useState("");

  useEffect(() => { setValue(""); }, [subIdx]);

  const submit = () => {
    if (value.trim() === "") return;
    submitSub({ value: Number(value) });
  };

  return (
    <div className="max-w-lg mx-auto text-center">
      <div className="flex items-center justify-center mb-6">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
      </div>
      <div className="flex items-center justify-center gap-2 flex-wrap font-mono text-lg mb-6">
        <span className="pm-chip">{current.start}</span>
        {(current.operations || []).map((op, ix) => (
          <React.Fragment key={ix}>
            <ArrowUp size={16} className="rotate-90 text-pm-text2" />
            <span className="pm-chip">{_OP_SYMBOL[op.op] || op.op} {op.value}</span>
          </React.Fragment>
        ))}
        <ArrowUp size={16} className="rotate-90 text-pm-text2" />
        <span className="pm-chip pm-chip-primary">?</span>
      </div>
      <div className="flex items-center justify-center gap-3">
        <input
          data-testid={TID.oaMathInput(`math-${subIdx}`)}
          type="number"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
          className="pm-input w-32 text-center font-mono text-lg"
          placeholder="?"
        />
        <button
          data-testid={TID.oaMathSubmit(`math-${subIdx}`)}
          onClick={submit}
          disabled={value.trim() === ""}
          className="pm-btn pm-btn-primary text-sm"
        >
          Submit
        </button>
      </div>
    </div>
  );
}

// -------- Shape Rotation: click the true rotation, not the mirror ---------
function ShapeMini({ grid, testId }) {
  const size = grid.length;
  return (
    <div data-testid={testId} className="grid gap-0.5 mx-auto" style={{ gridTemplateColumns: `repeat(${size}, minmax(0,1fr))`, width: 84 }}>
      {grid.map((row, r) => row.map((cell, c) => (
        <div
          key={`${r}-${c}`}
          className={`aspect-square rounded-sm ${cell ? "bg-pm-primary" : "bg-pm-surface-muted"}`}
        />
      )))}
    </div>
  );
}

function ShapeRotationGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);

  return (
    <div className="max-w-lg mx-auto text-center">
      <div className="flex items-center justify-center mb-4">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
      </div>
      <div className="text-xs text-pm-text2 mb-2">Base shape</div>
      <ShapeMini grid={current.base_grid} testId={TID.oaShapeBase(`shape-${subIdx}`)} />
      <div className="text-xs text-pm-text2 mt-6 mb-3">Which option is a true rotation of the base shape?</div>
      <div className="grid grid-cols-4 gap-3">
        {(current.options || []).map((opt, ix) => (
          <button
            key={ix}
            data-testid={TID.oaShapeOption(`shape-${subIdx}`, ix)}
            onClick={() => submitSub({ selected_index: ix })}
            className="pm-card p-3 hover:border-pm-primary transition"
          >
            <ShapeMini grid={opt} />
          </button>
        ))}
      </div>
    </div>
  );
}

function CognizantGamesSection({ section, answers, setAnswer, onAutoAdvanceEnd }) {
  const challenges = section.questions || [];
  const [challengeIdx, setChallengeIdx] = useState(0);
  const [phase, setPhase] = useState("intro"); // intro -> playing

  const challenge = challenges[challengeIdx];
  if (!challenge) return <div className="pm-card p-6">No games generated.</div>;

  const advanceChallenge = () => {
    if (challengeIdx + 1 < challenges.length) {
      setChallengeIdx(challengeIdx + 1);
      setPhase("intro");
    } else if (onAutoAdvanceEnd) {
      onAutoAdvanceEnd();
    }
  };

  const handleSubPuzzleChallengeComplete = (perSubAnswers) => {
    perSubAnswers.forEach((ans, i) => setAnswer(`${challenge.id}_${i}`, ans));
    advanceChallenge();
  };

  const type = challenge.type;
  const intro = COGNIZANT_GAME_INTROS[type] || { title: "Puzzle", body: "" };

  return (
    <div className="pm-card p-8">
      <div className="flex items-center gap-2 mb-6">
        <span className="pm-chip pm-chip-primary">Challenge {challengeIdx + 1} / {challenges.length}</span>
        <span className="pm-chip">{intro.title}</span>
      </div>

      {phase === "intro" ? (
        <div className="text-center py-8">
          <h3 className="font-display text-2xl font-bold mb-3">{intro.title}</h3>
          <p className="text-pm-text2 max-w-md mx-auto mb-6">{intro.body}</p>
          <button onClick={() => setPhase("playing")} className="pm-btn pm-btn-primary">
            <Play size={14} /> Start
          </button>
        </div>
      ) : type === "connect_pairs" ? (
        <ConnectPairsGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
      ) : type === "pattern_break" ? (
        <PatternBreakGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
      ) : type === "speed_math_chain" ? (
        <SpeedMathChainGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
      ) : type === "shape_rotation" ? (
        <ShapeRotationGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
      ) : (
        <div className="text-pm-text2">Unknown challenge type.</div>
      )}
    </div>
  );
}

// -------- Number Sorting: click tiles smallest-to-largest ------------------
function NumberSortGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const [order, setOrder] = useState([]);

  useEffect(() => { setOrder([]); }, [subIdx]);

  const items = current.items || [];
  const clickItem = (id) => {
    if (order.includes(id)) return;
    const next = [...order, id];
    setOrder(next);
    if (next.length === items.length) {
      submitSub({ order: next });
    }
  };
  const undo = () => setOrder(order.slice(0, -1));

  return (
    <div className="max-w-lg mx-auto text-center">
      <div className="flex items-center justify-between mb-6">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
        <span className="pm-chip font-mono">{order.length} / {items.length} placed</span>
      </div>
      <div className="flex items-center justify-center gap-3 flex-wrap mb-4">
        {items.map((it) => {
          const pos = order.indexOf(it.id);
          return (
            <button
              key={it.id}
              data-testid={TID.oaSortTile(`sort-${subIdx}`, it.id)}
              onClick={() => clickItem(it.id)}
              disabled={pos !== -1}
              className={`relative w-20 h-20 rounded-xl border-2 flex items-center justify-center font-mono font-bold transition ${
                pos !== -1 ? "border-pm-primary bg-pm-primary/10 text-pm-text2" : "border-pm-border bg-white hover:border-pm-primary"
              }`}
            >
              {it.display}
              {pos !== -1 && (
                <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-pm-primary text-white text-xs grid place-items-center">{pos + 1}</span>
              )}
            </button>
          );
        })}
      </div>
      <button onClick={undo} disabled={order.length === 0} className="pm-btn pm-btn-ghost text-sm">
        <RotateCcw size={14} /> Undo
      </button>
    </div>
  );
}

// -------- Path-Finding: trace arrows to the true exit -----------------------
function PathFindingGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const grid = current.grid || [];
  const start = current.start || { row: 0, col: 0 };

  return (
    <div className="max-w-lg mx-auto text-center">
      <div className="flex items-center justify-center mb-4">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
      </div>
      <div
        className="grid gap-1 mx-auto mb-6"
        style={{ gridTemplateColumns: `repeat(${grid.length}, minmax(0,1fr))`, maxWidth: 260 }}
      >
        {grid.map((row, r) => row.map((dir, c) => {
          const isStart = start.row === r && start.col === c;
          return (
            <div
              key={`${r}-${c}`}
              data-testid={TID.oaPathCell(`path-${subIdx}`, `${r}-${c}`)}
              className={`aspect-square rounded-lg border-2 flex items-center justify-center ${isStart ? "border-pm-primary bg-pm-primary/10" : "border-pm-border bg-white"}`}
            >
              <ArrowUp size={18} style={{ transform: `rotate(${_DIR_ROTATE[dir]}deg)` }} className={isStart ? "text-pm-primary-dark" : "text-pm-text2"} />
            </div>
          );
        }))}
      </div>
      <div className="text-xs text-pm-text2 mb-3">Where do you exit the grid?</div>
      <div className="flex items-center justify-center gap-3 flex-wrap">
        {(current.exit_options || []).map((opt, ix) => (
          <button
            key={ix}
            data-testid={TID.oaPathExitOption(`path-${subIdx}`, ix)}
            onClick={() => submitSub({ selected_index: ix })}
            className="pm-btn pm-btn-secondary text-sm py-2 px-4 font-mono"
          >
            ({opt.row}, {opt.col})
          </button>
        ))}
      </div>
    </div>
  );
}

// -------- Key-Door Maze: click the reachable, color-matching key ----------
function KeyDoorMazeGame({ subPuzzles, onChallengeComplete }) {
  const { subIdx, total, current, submitSub } = useSubPuzzleFlow(subPuzzles, onChallengeComplete);
  const size = current.size || 5;
  const start = current.start || { row: 0, col: 0 };
  const wallSet = new Set((current.walls || []).map((w) => `${w.row}-${w.col}`));
  const door = current.door || {};
  const keys = current.keys || [];
  const keyByCell = Object.fromEntries(keys.map((k) => [`${k.row}-${k.col}`, k]));

  return (
    <div className="max-w-lg mx-auto text-center">
      <div className="flex items-center justify-between mb-4">
        <span className="pm-chip pm-chip-primary font-mono">Puzzle {subIdx + 1} of {total}</span>
        <span className="pm-chip font-mono" style={{ background: `${_KEY_COLOR_HEX[door.color]}22`, color: _KEY_COLOR_HEX[door.color] }}>
          Door: {door.color}
        </span>
      </div>
      <div
        className="grid gap-1 mx-auto mb-4"
        style={{ gridTemplateColumns: `repeat(${size}, minmax(0,1fr))`, maxWidth: 300 }}
      >
        {Array.from({ length: size }).map((_, r) => Array.from({ length: size }).map((_, c) => {
          const cellKey = `${r}-${c}`;
          const isWall = wallSet.has(cellKey);
          const isStart = start.row === r && start.col === c;
          const isDoor = door.row === r && door.col === c;
          const key = keyByCell[cellKey];
          return (
            <div
              key={cellKey}
              data-testid={TID.oaMazeCell(`maze-${subIdx}`, cellKey)}
              className={`aspect-square rounded flex items-center justify-center text-[9px] font-mono ${
                isWall ? "bg-pm-text-muted/40" : "bg-pm-surface-muted"
              }`}
            >
              {isStart && <span className="pm-chip pm-chip-primary" style={{ padding: "2px 4px", fontSize: 9 }}>S</span>}
              {isDoor && !isStart && <span style={{ color: _KEY_COLOR_HEX[door.color] }}>▢</span>}
              {key && (
                <button
                  data-testid={TID.oaMazeKey(`maze-${subIdx}`, key.id)}
                  onClick={() => submitSub({ selected_key_id: key.id })}
                  className="w-4 h-4 rounded-full hover:ring-2 hover:ring-pm-primary"
                  style={{ background: _KEY_COLOR_HEX[key.color] }}
                  title={`Key: ${key.color}`}
                />
              )}
            </div>
          );
        }))}
      </div>
      <div className="text-xs text-pm-text2">Click the key that's reachable and matches the door's color.</div>
    </div>
  );
}

function AccentureGamesSection({ section, answers, setAnswer, onAutoAdvanceEnd }) {
  const challenges = section.questions || [];
  const [challengeIdx, setChallengeIdx] = useState(0);
  const [phase, setPhase] = useState("intro"); // intro -> playing

  const challenge = challenges[challengeIdx];
  if (!challenge) return <div className="pm-card p-6">No games generated.</div>;

  const advanceChallenge = () => {
    if (challengeIdx + 1 < challenges.length) {
      setChallengeIdx(challengeIdx + 1);
      setPhase("intro");
    } else if (onAutoAdvanceEnd) {
      onAutoAdvanceEnd();
    }
  };

  const handleSubPuzzleChallengeComplete = (perSubAnswers) => {
    perSubAnswers.forEach((ans, i) => setAnswer(`${challenge.id}_${i}`, ans));
    advanceChallenge();
  };

  const type = challenge.type;
  const intro = ACCENTURE_GAME_INTROS[type] || { title: "Puzzle", body: "" };

  return (
    <div className="pm-card p-8">
      <div className="flex items-center gap-2 mb-6">
        <span className="pm-chip pm-chip-primary">Challenge {challengeIdx + 1} / {challenges.length}</span>
        <span className="pm-chip">{intro.title}</span>
      </div>

      {phase === "intro" ? (
        <div className="text-center py-8">
          <h3 className="font-display text-2xl font-bold mb-3">{intro.title}</h3>
          <p className="text-pm-text2 max-w-md mx-auto mb-6">{intro.body}</p>
          <button onClick={() => setPhase("playing")} className="pm-btn pm-btn-primary">
            <Play size={14} /> Start
          </button>
        </div>
      ) : type === "number_sort" ? (
        <NumberSortGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
      ) : type === "path_finding" ? (
        <PathFindingGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
      ) : type === "key_door_maze" ? (
        <KeyDoorMazeGame subPuzzles={challenge.sub_puzzles} onChallengeComplete={handleSubPuzzleChallengeComplete} />
      ) : (
        <div className="text-pm-text2">Unknown challenge type.</div>
      )}
    </div>
  );
}
