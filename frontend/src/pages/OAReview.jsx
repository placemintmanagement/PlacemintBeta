import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { CheckCircle2, XCircle, ArrowRight, ChevronDown, ChevronUp, Circle, MinusCircle, BookmarkPlus, BookmarkCheck } from "lucide-react";

export default function OAReview() {
  const { attemptId } = useParams();
  const [review, setReview] = useState(null);
  const [starting, setStarting] = useState(false);
  const [openKeys, setOpenKeys] = useState({});
  const [savingBulk, setSavingBulk] = useState(false);
  const [savedIds, setSavedIds] = useState({}); // "sectionKey:qid" -> true
  const navigate = useNavigate();

  useEffect(() => {
    api.get(`/oa/${attemptId}/review`).then(r => setReview(r.data));
  }, [attemptId]);

  if (!review) return <div><Header /><div className="p-10 text-center">Loading review…</div></div>;

  if (review.available === false) {
    return (
      <div>
        <Header />
        <div className="p-10 text-center">
          <div className="font-display text-xl font-bold mb-2">Review isn't ready yet</div>
          <div className="text-pm-text2 mb-6">Finish every section of the OA to unlock your full review and answer key.</div>
          <Link to={`/oa/${attemptId}`} className="pm-btn pm-btn-primary">Back to OA</Link>
        </div>
      </div>
    );
  }

  const verdictColor = review.verdict === "clear" ? "text-pm-primary-dark" : review.verdict === "borderline" ? "text-pm-secondary" : "text-red-600";
  const verdictText = review.verdict === "clear" ? "You'd likely clear this."
    : review.verdict === "borderline" ? "You're borderline — fixable."
    : "Not ready yet — keep grinding.";

  const startInterview = async () => {
    setStarting(true);
    try {
      const { data } = await api.post("/interview/start", { attempt_id: attemptId });
      navigate(`/interview/${data.interview_id}`);
    } catch (e) {
      setStarting(false);
    }
  };

  const nameByKey = Object.fromEntries((review.sections_meta || []).map(s => [s.key, s.name]));

  // Count how many wrong / skipped MCQs are in this attempt (drives the CTA copy).
  const wrongPlusSkipped = (review.answer_key || []).reduce(
    (sum, s) => sum + s.questions.filter(q => !q.answered || !q.is_correct).length, 0,
  );

  const saveOneToDeck = async (sectionKey, questionId) => {
    const marker = `${sectionKey}:${questionId}`;
    try {
      const { data } = await api.post("/deck/add", {
        attempt_id: attemptId,
        question_ids: [{ section_key: sectionKey, question_id: questionId }],
      });
      setSavedIds(m => ({ ...m, [marker]: true }));
      if (data.added > 0) toast.success("Added to your review deck");
      else toast.info("Already in your review deck");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't save to deck");
    }
  };

  const saveAllWrongToDeck = async () => {
    setSavingBulk(true);
    try {
      const { data } = await api.post("/deck/add", { attempt_id: attemptId });
      // Optimistically mark every wrong/skipped as saved
      const marks = {};
      for (const s of review.answer_key || []) {
        for (const q of s.questions) {
          if (!q.answered || !q.is_correct) marks[`${s.section_key}:${q.id}`] = true;
        }
      }
      setSavedIds(m => ({ ...m, ...marks }));
      toast.success(`${data.added} added to review deck${data.skipped_duplicates ? ` · ${data.skipped_duplicates} already saved` : ""}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't save to deck");
    } finally {
      setSavingBulk(false);
    }
  };

  return (
    <div>
      <Header />
      <div className="max-w-5xl mx-auto px-6 lg:px-10 py-10 pm-in">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-2">OA review · {review.company_name}</div>
        <h1 className={`font-display text-4xl lg:text-5xl font-bold ${verdictColor}`}>{verdictText}</h1>
        <div className="mt-4 flex flex-wrap items-center gap-4">
          <div className="pm-card px-5 py-3">
            <div className="text-xs font-mono uppercase text-pm-text2">Composite</div>
            <div className="font-display text-2xl font-bold font-mono">{Math.round(review.composite_score * 100)}%</div>
          </div>
          <div className="pm-card px-5 py-3">
            <div className="text-xs font-mono uppercase text-pm-text2">Weakest section</div>
            <div className="font-display text-lg font-bold">{nameByKey[review.weakest_section] || review.weakest_section || "—"}</div>
          </div>
          <div className="pm-card px-5 py-3">
            <div className="text-xs font-mono uppercase text-pm-text2">Scoring mode</div>
            <div className="font-display text-lg font-bold capitalize">{review.scoring_mode}</div>
          </div>
        </div>

        <h2 className="mt-10 font-display text-2xl font-bold">Section breakdown</h2>
        <div className="mt-4 space-y-3">
          {Object.entries(review.section_results).map(([key, res]) => (
            <div key={key} className="pm-card p-5 flex items-center justify-between">
              <div>
                <div className="font-display font-bold">{nameByKey[key] || key}</div>
                <div className="text-xs font-mono text-pm-text2">score {(res.score * 100).toFixed(0)}%</div>
              </div>
              <div className="flex items-center gap-2">
                {res.passed
                  ? <span className="pm-chip pm-chip-primary"><CheckCircle2 size={12}/> passed</span>
                  : <span className="pm-chip pm-chip-coral"><XCircle size={12}/> below cutoff</span>}
              </div>
            </div>
          ))}
        </div>

        {/* Answer key — MCQ-style sections only */}
        {(review.answer_key || []).length > 0 && (
          <>
            <div className="mt-10 flex flex-wrap items-end justify-between gap-4">
              <div>
                <h2 className="font-display text-2xl font-bold">Answer key</h2>
                <p className="mt-1 text-sm text-pm-text2">Every MCQ you saw, your answer, and the correct one — with explanations.</p>
              </div>
              {wrongPlusSkipped > 0 && (
                <button
                  onClick={saveAllWrongToDeck}
                  disabled={savingBulk}
                  data-testid="deck-save-all-wrong"
                  className="pm-btn pm-btn-secondary text-sm"
                >
                  <BookmarkPlus size={14}/>
                  {savingBulk ? "Saving…" : `Save all ${wrongPlusSkipped} wrong to review deck`}
                </button>
              )}
            </div>
            <div className="mt-4 space-y-3" data-testid="answer-key-list">
              {review.answer_key.map((sec) => {
                const isOpen = !!openKeys[sec.section_key];
                const totalQ = sec.questions.length;
                const correctQ = sec.questions.filter(q => q.is_correct).length;
                const wrongQ = sec.questions.filter(q => q.answered && !q.is_correct).length;
                const skippedQ = sec.questions.filter(q => !q.answered).length;
                return (
                  <div key={sec.section_key} className="pm-card overflow-hidden">
                    <button
                      onClick={() => setOpenKeys(o => ({ ...o, [sec.section_key]: !o[sec.section_key] }))}
                      data-testid={`answer-key-toggle-${sec.section_key}`}
                      className="w-full flex items-center justify-between p-5 text-left hover:bg-black/[0.02] transition-colors"
                    >
                      <div>
                        <div className="font-display font-bold">{sec.section_name}</div>
                        <div className="text-xs font-mono text-pm-text2 mt-1 flex flex-wrap gap-3">
                          <span className="text-pm-primary-dark">✓ {correctQ} correct</span>
                          <span className="text-red-600">✗ {wrongQ} wrong</span>
                          {skippedQ > 0 && <span className="text-pm-text2">– {skippedQ} skipped</span>}
                          <span>· {totalQ} total</span>
                        </div>
                      </div>
                      <div className="text-pm-text2">
                        {isOpen ? <ChevronUp size={18}/> : <ChevronDown size={18}/>}
                      </div>
                    </button>
                    {isOpen && (
                      <div className="border-t border-pm-line divide-y divide-pm-line">
                        {sec.questions.map((q, i) => (
                          <QuestionRow
                            key={q.id || i}
                            q={q}
                            index={i}
                            saved={!!savedIds[`${sec.section_key}:${q.id}`]}
                            onSave={() => saveOneToDeck(sec.section_key, q.id)}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}

        <div className="mt-10 pm-card p-6 bg-[#0A0A0A] text-white hover:!transform-none flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="pm-chip" style={{ background: "rgba(255,255,255,0.08)", color: "#fff" }}>next up</div>
            <div className="font-display text-2xl font-bold mt-2">Take the interview round.</div>
            <div className="text-sm text-white/70 mt-1">2 DSA · 2 project questions · 3 CS fundamentals.</div>
          </div>
          <div className="flex gap-3">
            <Link to="/dashboard" className="pm-btn pm-btn-ghost text-sm bg-white/5 border-white/10 text-white hover:bg-white/10">Back to dashboard</Link>
            <button onClick={startInterview} disabled={starting} className="pm-btn pm-btn-primary text-sm">
              {starting ? "Preparing…" : <>Start interview <ArrowRight size={14}/></>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function QuestionRow({ q, index, saved, onSave }) {
  // Multiline prompt preserved as-is; options rendered as a list with the
  // correct answer highlighted mint and the user's wrong pick highlighted coral.
  const correctIdx = q.correct_index;
  const userIdx = q.user_index;
  const state = q.answered ? (q.is_correct ? "correct" : "wrong") : "skipped";
  const badge = state === "correct"
    ? <span className="pm-chip pm-chip-primary" data-testid={`ak-badge-correct-${index}`}><CheckCircle2 size={12}/> correct</span>
    : state === "wrong"
    ? <span className="pm-chip pm-chip-coral" data-testid={`ak-badge-wrong-${index}`}><XCircle size={12}/> wrong</span>
    : <span className="pm-chip" style={{background:"rgba(0,0,0,0.06)"}} data-testid={`ak-badge-skipped-${index}`}><MinusCircle size={12}/> skipped</span>;
  const savable = state !== "correct";

  return (
    <div className="p-5" data-testid={`ak-row-${index}`}>
      <div className="flex items-start gap-3">
        <div className="font-mono text-xs text-pm-text2 shrink-0 mt-1">Q{index + 1}</div>
        <div className="flex-1 min-w-0">
          <div className="whitespace-pre-wrap text-sm">{q.prompt}</div>
          <div className="mt-3 space-y-1.5">
            {(q.options || []).map((opt, i) => {
              const isCorrect = i === correctIdx;
              const isUser = i === userIdx;
              let cls = "border border-pm-line bg-white";
              if (isCorrect) cls = "border border-pm-primary bg-pm-primary/10";
              else if (isUser && !isCorrect) cls = "border border-red-400 bg-red-50";
              return (
                <div key={i} className={`text-sm px-3 py-2 rounded-md flex items-start gap-2 ${cls}`}>
                  <span className="font-mono text-[11px] text-pm-text2 shrink-0 mt-0.5">{String.fromCharCode(65 + i)}</span>
                  <span className="flex-1 min-w-0 whitespace-pre-wrap">{opt}</span>
                  <span className="shrink-0 flex items-center gap-1 text-[11px] font-mono">
                    {isCorrect && <span className="text-pm-primary-dark">correct</span>}
                    {isUser && !isCorrect && <span className="text-red-600">your answer</span>}
                    {isUser && isCorrect && <span className="text-pm-primary-dark">✓ you</span>}
                  </span>
                </div>
              );
            })}
          </div>
          {q.explanation && (
            <div className="mt-3 text-xs text-pm-text2 border-l-2 border-pm-primary/40 pl-3">
              <span className="font-mono uppercase tracking-widest text-[10px] text-pm-primary-dark">Why</span>
              <div className="mt-0.5 whitespace-pre-wrap">{q.explanation}</div>
            </div>
          )}
          {savable && (
            <div className="mt-3">
              <button
                onClick={onSave}
                disabled={saved}
                data-testid={`deck-save-q-${index}`}
                className={`inline-flex items-center gap-1.5 text-xs font-mono px-2.5 py-1.5 rounded-md border transition-colors ${
                  saved
                    ? "border-pm-primary/40 bg-pm-primary/10 text-pm-primary-dark cursor-default"
                    : "border-pm-line bg-white hover:bg-black/[0.03] text-pm-text"
                }`}
              >
                {saved ? <><BookmarkCheck size={13}/> Saved to deck</> : <><BookmarkPlus size={13}/> Save to review deck</>}
              </button>
            </div>
          )}
        </div>
        <div className="shrink-0">{badge}</div>
      </div>
    </div>
  );
}
