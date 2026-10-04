import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate, useLocation } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { CheckCircle2, XCircle, ArrowRight, ChevronDown, ChevronUp, MinusCircle, BookmarkPlus, BookmarkCheck } from "lucide-react";
import { PageShell, SectionLabel, PageTitle, CardTitle, Card, Chip, Button } from "../components/shared";

// Body-size meta text (never monospace).
const META = { fontSize: 13, color: "rgba(11,42,48,0.7)" };
const BODY = { fontSize: 15, color: "rgba(11,42,48,0.85)", lineHeight: 1.6 };

const TIER_NAMES = { spark: "Spark", dave: "Dave", commit: "Commit" };

// Shown once, right after the final section of a Capgemini attempt. The tier
// is computed by the server (services/capgemini_tiers.py) and passed here in
// the navigation state; nothing on this page can change it.
function TierUnlockCard({ tier, onDismiss }) {
  return (
    <Card padding="24px 28px" className="mt-6" style={{ borderRadius: 24 }}>
      {tier.tier ? (
        <>
          <SectionLabel>capgemini tier</SectionLabel>
          <CardTitle style={{ fontSize: 24 }}>Congratulations, you unlocked the {TIER_NAMES[tier.tier]} tier!</CardTitle>
          <div className="mt-2" style={{ fontSize: 16, color: "rgba(11,42,48,0.75)" }}>{tier.lpa.toFixed(2)} LPA</div>
        </>
      ) : (
        <>
          <SectionLabel>attempt complete</SectionLabel>
          <CardTitle style={{ fontSize: 22 }}>Your attempt is complete.</CardTitle>
          <div className="mt-2" style={{ fontSize: 15, color: "rgba(11,42,48,0.75)" }}>Your full review is below.</div>
        </>
      )}
      <Button variant="primary" className="mt-4" onClick={onDismiss}>View my review</Button>
    </Card>
  );
}

export default function OAReview() {
  const { attemptId } = useParams();
  const location = useLocation();
  const tierUnlock = location.state?.capgemini_tier || null;
  const [unlockDismissed, setUnlockDismissed] = useState(false);
  const [review, setReview] = useState(null);
  const [starting, setStarting] = useState(false);
  const [openKeys, setOpenKeys] = useState({});
  const [savingBulk, setSavingBulk] = useState(false);
  const [savedIds, setSavedIds] = useState({}); // "sectionKey:qid" -> true
  const navigate = useNavigate();

  useEffect(() => {
    api.get(`/oa/${attemptId}/review`).then(r => setReview(r.data));
  }, [attemptId]);

  if (!review) return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Loading review…</div></PageShell></div>;

  if (review.available === false) {
    return (
      <div>
        <Header light />
        <PageShell>
          <div className="p-10 text-center">
            <CardTitle style={{ fontSize: 22, marginBottom: 8 }}>Review isn't ready yet</CardTitle>
            <div className="mb-6" style={BODY}>Finish every section of the OA to unlock your full review and answer key.</div>
            <Button as={Link} to={`/oa/${attemptId}`}>Back to OA</Button>
          </div>
        </PageShell>
      </div>
    );
  }

  // Three-tier verdict colour: teal for clear, ink 70% for borderline, full
  // ink for not ready. No hue beyond the palette.
  const verdictColor = review.verdict === "clear" ? "var(--pm-teal-deep)" : review.verdict === "borderline" ? "rgba(11,42,48,0.7)" : "var(--pm-ink)";
  const verdictText = review.verdict === "clear" ? "You'd likely clear this."
    : review.verdict === "borderline" ? "You're borderline, fixable."
    : "Not ready yet. Keep grinding.";

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
      <Header light />
      <PageShell>
        <div className="max-w-5xl mx-auto pm-in">
          {tierUnlock && !unlockDismissed && <TierUnlockCard tier={tierUnlock} onDismiss={() => setUnlockDismissed(true)} />}
          <SectionLabel>OA review · {review.company_name}</SectionLabel>
          <PageTitle style={{ color: verdictColor }}>{verdictText}</PageTitle>
          <div className="mt-6 flex flex-wrap items-stretch gap-4">
            <Card padding="16px 20px" style={{ borderRadius: 20 }}>
              <div style={META}>Composite</div>
              <div className="font-display font-semibold" style={{ fontSize: 26, color: "var(--pm-ink)" }}>{Math.round(review.composite_score * 100)}%</div>
            </Card>
            <Card padding="16px 20px" style={{ borderRadius: 20 }}>
              <div style={META}>Weakest section</div>
              <div className="font-display font-semibold" style={{ fontSize: 18, color: "var(--pm-ink)" }}>{nameByKey[review.weakest_section] || review.weakest_section || "N/A"}</div>
            </Card>
            <Card padding="16px 20px" style={{ borderRadius: 20 }}>
              <div style={META}>Scoring mode</div>
              <div className="font-display font-semibold capitalize" style={{ fontSize: 18, color: "var(--pm-ink)" }}>{review.scoring_mode}</div>
            </Card>
          </div>

          <div className="mt-12 mb-5"><PageTitle as="h2">Section breakdown</PageTitle></div>
          <div className="space-y-3">
            {Object.entries(review.section_results).map(([key, res]) => (
              <Card key={key} padding="20px 24px">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div>
                    <div className="font-display font-semibold" style={{ fontSize: 18, color: "var(--pm-ink)" }}>{nameByKey[key] || key}</div>
                    <div className="mt-1" style={META}>score {(res.score * 100).toFixed(0)}%</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {res.passed
                      ? <Chip tone="status" icon={<CheckCircle2 size={12}/>}>passed</Chip>
                      : <Chip icon={<XCircle size={12}/>}>below cutoff</Chip>}
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {/* Answer key — MCQ-style sections only */}
          {(review.answer_key || []).length > 0 && (
            <>
              <div className="mt-12 flex flex-wrap items-end justify-between gap-4">
                <div>
                  <PageTitle as="h2">Answer key</PageTitle>
                  <p className="mt-2" style={BODY}>Every MCQ you saw, your answer, and the correct one, with explanations.</p>
                </div>
                {wrongPlusSkipped > 0 && (
                  <Button
                    variant="secondary"
                    onClick={saveAllWrongToDeck}
                    disabled={savingBulk}
                    data-testid="deck-save-all-wrong"
                    className="!py-2 !px-4"
                    style={{ fontSize: 14 }}
                  >
                    <BookmarkPlus size={14} aria-hidden="true"/>
                    {savingBulk ? "Saving…" : `Save all ${wrongPlusSkipped} wrong to review deck`}
                  </Button>
                )}
              </div>
              <div className="mt-5 space-y-3" data-testid="answer-key-list">
                {review.answer_key.map((sec) => {
                  const isOpen = !!openKeys[sec.section_key];
                  const totalQ = sec.questions.length;
                  const correctQ = sec.questions.filter(q => q.is_correct).length;
                  const wrongQ = sec.questions.filter(q => q.answered && !q.is_correct).length;
                  const skippedQ = sec.questions.filter(q => !q.answered).length;
                  return (
                    <Card key={sec.section_key} padding="0">
                      <button
                        onClick={() => setOpenKeys(o => ({ ...o, [sec.section_key]: !o[sec.section_key] }))}
                        data-testid={`answer-key-toggle-${sec.section_key}`}
                        aria-expanded={isOpen}
                        className="w-full flex items-center justify-between gap-4 p-5 text-left transition-colors hover:bg-[rgba(15,111,122,0.04)] focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-[-3px] focus-visible:outline-[var(--pm-teal-night)]"
                      >
                        <div>
                          <div className="font-display font-semibold" style={{ fontSize: 18, color: "var(--pm-ink)" }}>{sec.section_name}</div>
                          <div className="mt-1 flex flex-wrap gap-3" style={META}>
                            <span style={{ color: "var(--pm-teal-deep)", fontWeight: 600 }}>✓ {correctQ} correct</span>
                            <span style={{ color: "var(--pm-ink)", fontWeight: 600 }}>✗ {wrongQ} wrong</span>
                            {skippedQ > 0 && <span>– {skippedQ} skipped</span>}
                            <span>· {totalQ} total</span>
                          </div>
                        </div>
                        <div style={{ color: "rgba(11,42,48,0.7)" }}>
                          {isOpen ? <ChevronUp size={18}/> : <ChevronDown size={18}/>}
                        </div>
                      </button>
                      {isOpen && (
                        <div style={{ borderTop: "1px solid rgba(7,59,67,0.08)" }} className="divide-y" >
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
                    </Card>
                  );
                })}
              </div>
            </>
          )}

          <div className="mt-12 rounded-[24px] p-7 flex items-center justify-between flex-wrap gap-6" style={{ background: "var(--pm-teal-night)", color: "var(--pm-white)" }}>
            <div>
              <span className="inline-flex rounded-full" style={{ background: "rgba(255,255,255,0.12)", color: "var(--pm-white)", fontSize: 13, padding: "4px 10px" }}>next up</span>
              <div className="font-display font-semibold mt-3" style={{ fontSize: 26, color: "var(--pm-white)" }}>Take the interview round.</div>
              <div className="mt-1" style={{ fontSize: 15, color: "rgba(255,255,255,0.8)" }}>2 DSA · 2 project questions · 3 CS fundamentals.</div>
            </div>
            <div className="flex gap-3 flex-wrap">
              <Link to="/dashboard" className="pm-btn pm-btn-ghost-light !py-3 !px-5" style={{ fontSize: 15 }}>Back to dashboard</Link>
              <Button variant="lime" onClick={startInterview} disabled={starting}>
                {starting ? "Preparing…" : <>Start interview <ArrowRight size={14} aria-hidden="true"/></>}
              </Button>
            </div>
          </div>
        </div>
      </PageShell>
    </div>
  );
}

function QuestionRow({ q, index, saved, onSave }) {
  // Multiline prompt preserved as-is; options rendered as a list with the
  // correct answer highlighted in teal and the user's wrong pick outlined in ink.
  const correctIdx = q.correct_index;
  const userIdx = q.user_index;
  const state = q.answered ? (q.is_correct ? "correct" : "wrong") : "skipped";
  const badge = state === "correct"
    ? <Chip tone="status" icon={<CheckCircle2 size={12}/>}><span data-testid={`ak-badge-correct-${index}`}>correct</span></Chip>
    : state === "wrong"
    ? <Chip icon={<XCircle size={12}/>}><span data-testid={`ak-badge-wrong-${index}`}>wrong</span></Chip>
    : <Chip icon={<MinusCircle size={12}/>}><span data-testid={`ak-badge-skipped-${index}`}>skipped</span></Chip>;
  const savable = state !== "correct";

  return (
    <div className="p-5" data-testid={`ak-row-${index}`}>
      <div className="flex items-start gap-3">
        <div className="shrink-0 mt-0.5 pm-eyebrow" style={{ color: "rgba(11,42,48,0.7)" }}>Q{index + 1}</div>
        <div className="flex-1 min-w-0">
          <div className="whitespace-pre-wrap" style={BODY}>{q.prompt}</div>
          <div className="mt-3 space-y-1.5">
            {(q.options || []).map((opt, i) => {
              const isCorrect = i === correctIdx;
              const isUser = i === userIdx;
              let style = { border: "1px solid rgba(7,59,67,0.12)", background: "var(--pm-white)" };
              if (isCorrect) style = { border: "1.5px solid var(--pm-teal-deep)", background: "var(--pm-success-bg)" };
              else if (isUser && !isCorrect) style = { border: "1.5px solid rgba(11,42,48,0.55)", background: "var(--pm-grey)" };
              return (
                <div key={i} className="rounded-[12px] px-3 py-2 flex items-start gap-2" style={{ fontSize: 15, color: "var(--pm-ink)", ...style }}>
                  <span className="shrink-0 mt-0.5 font-semibold" style={{ fontSize: 13, color: "rgba(11,42,48,0.7)" }}>{String.fromCharCode(65 + i)}</span>
                  <span className="flex-1 min-w-0 whitespace-pre-wrap">{opt}</span>
                  <span className="shrink-0 flex items-center gap-1" style={{ fontSize: 13 }}>
                    {isCorrect && <span style={{ color: "var(--pm-teal-deep)", fontWeight: 600 }}>correct</span>}
                    {isUser && !isCorrect && <span style={{ color: "var(--pm-ink)", fontWeight: 600 }}>your answer</span>}
                    {isUser && isCorrect && <span style={{ color: "var(--pm-teal-deep)", fontWeight: 600 }}>✓ you</span>}
                  </span>
                </div>
              );
            })}
          </div>
          {q.explanation && (
            <div className="mt-3 pl-3" style={{ fontSize: 14, color: "rgba(11,42,48,0.85)", borderLeft: "2px solid var(--pm-teal-deep)" }}>
              <span className="pm-eyebrow" style={{ fontSize: 11, color: "var(--pm-teal-deep)" }}>Why</span>
              <div className="mt-0.5 whitespace-pre-wrap">{q.explanation}</div>
            </div>
          )}
          {savable && (
            <div className="mt-3">
              <button
                onClick={onSave}
                disabled={saved}
                data-testid={`deck-save-q-${index}`}
                className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 font-semibold transition-colors focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[var(--pm-teal-night)] disabled:cursor-default"
                style={saved
                  ? { fontSize: 13, background: "var(--pm-success-bg)", color: "var(--pm-teal-deep)", border: "1px solid rgba(15,111,122,0.35)" }
                  : { fontSize: 13, background: "var(--pm-white)", color: "var(--pm-teal-deep)", border: "1.5px solid var(--pm-border-control)" }}
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
