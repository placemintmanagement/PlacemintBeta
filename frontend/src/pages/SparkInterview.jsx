import React, { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { SendHorizontal } from "lucide-react";
import { PageShell, SectionLabel, PageTitle, Card, Button } from "../components/shared";

// Capgemini Spark interview (text, 35 minutes). Everything time-related comes
// from the server: the deadline and "server_now" arrive with every response, so
// the countdown survives a refresh and does not depend on this device's clock.
// The browser never receives flags, scores, weights, thresholds or rubrics.

const META = { fontSize: 14, color: "rgba(11,42,48,0.7)" };
const BODY = { fontSize: 15, color: "var(--pm-ink)", lineHeight: 1.6 };

const asText = (v) => (v == null ? "" : typeof v === "string" ? v : String(v));

function formatRemaining(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}

export default function SparkInterview({ interviewId, initial }) {
  const navigate = useNavigate();
  const [view, setView] = useState(initial);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  // Offset between the server clock and this device's clock, taken at receipt.
  const offsetRef = useRef(0);
  const [now, setNow] = useState(() => Date.now() / 1000);
  const bottomRef = useRef(null);

  const applyView = useCallback((data) => {
    if (typeof data.server_now_epoch === "number") {
      offsetRef.current = data.server_now_epoch - Date.now() / 1000;
    }
    setView(data);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get(`/interview/${interviewId}`);
      applyView(data);
    } catch {
      toast.error("Could not load the interview");
    }
  }, [interviewId, applyView]);

  useEffect(() => {
    if (typeof initial?.server_now_epoch === "number") {
      offsetRef.current = initial.server_now_epoch - Date.now() / 1000;
    }
  }, [initial]);

  // Tick once a second against the server-derived clock.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now() / 1000 + offsetRef.current), 1000);
    return () => clearInterval(id);
  }, []);

  const inProgress = view?.status === "in_progress";
  const remaining = view ? view.deadline_epoch - now : 0;

  // When the countdown reaches zero, ask the server to close the interview.
  useEffect(() => {
    if (inProgress && view && remaining <= 0) refresh();
  }, [inProgress, view, remaining, refresh]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [view?.turns?.length, view?.current_question?.id]);

  const send = async () => {
    const q = view?.current_question;
    if (!q || !answer.trim() || submitting) return;
    setSubmitting(true);
    try {
      const { data } = await api.post(`/interview/${interviewId}/answer`, { question_id: q.id, answer });
      setAnswer("");
      applyView(data);
    } catch (err) {
      const code = err.response?.data?.detail?.code;
      if (code === "time_up" || code === "stale_question" || code === "stale_turn" || code === "interview_closed") {
        toast.message(err.response?.data?.detail?.message || "Refreshing the interview");
        await refresh();
      } else {
        toast.error(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Failed to submit");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (!view) return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Loading…</div></PageShell></div>;

  const stageIndex = Math.max(0, view.stages.findIndex(s => s.stage === view.stage));

  return (
    <div>
      <Header light />
      <PageShell>
        <div className="max-w-4xl mx-auto pm-in">
          <SectionLabel>{view.company_name} · interview</SectionLabel>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <PageTitle as="h2" style={{ fontSize: "clamp(1.75rem, 3vw, 2.25rem)" }}>Interview</PageTitle>
            {inProgress && (
              <div data-testid="spark-countdown" className="font-display font-semibold" style={{ fontSize: 22, color: "var(--pm-ink)" }}>
                {formatRemaining(remaining)} left
              </div>
            )}
          </div>

          {/* Stage progress */}
          <ol className="mt-4 flex flex-wrap gap-2" aria-label="Interview stages" data-testid="spark-stages">
            {view.stages.map((s, i) => {
              const done = !inProgress || i < stageIndex;
              const current = inProgress && i === stageIndex;
              return (
                <li key={s.stage} aria-current={current ? "step" : undefined}
                    className="rounded-full px-3 py-1"
                    style={{
                      fontSize: 13, fontWeight: 600,
                      background: current ? "var(--pm-teal-deep)" : done ? "rgba(7,59,67,0.08)" : "transparent",
                      color: current ? "var(--pm-white)" : "var(--pm-ink)",
                      border: "1px solid rgba(7,59,67,0.12)",
                    }}>
                  {s.label}
                </li>
              );
            })}
          </ol>

          {/* Transcript */}
          <Card className="mt-6 space-y-5 max-h-[60vh] overflow-y-auto" padding="24px">
            {view.turns.map((t, i) => (
              <div key={i} className="space-y-3">
                <div className="rounded-[18px] p-4 whitespace-pre-wrap" style={{ ...BODY, background: "var(--pm-grey)" }}>{asText(t.question)}</div>
                <div className="flex justify-end">
                  <div className="max-w-[80%] p-4 rounded-[18px] rounded-tr-[4px] whitespace-pre-wrap" style={{ fontSize: 15, lineHeight: 1.6, background: "var(--pm-teal-deep)", color: "var(--pm-white)" }}>{asText(t.answer)}</div>
                </div>
              </div>
            ))}
            {inProgress && view.current_question && (
              <div className="rounded-[18px] p-4 whitespace-pre-wrap" style={{ ...BODY, background: "var(--pm-grey)", border: "1px solid rgba(7,59,67,0.08)" }}>
                <div className="pm-eyebrow mb-1" style={{ fontSize: 11, color: "rgba(11,42,48,0.7)" }}>{view.current_question.stage}</div>
                {asText(view.current_question.prompt)}
              </div>
            )}
            <div ref={bottomRef} />
          </Card>

          {/* Input */}
          {inProgress && view.current_question && (
            <div className="mt-4 flex gap-3 items-end">
              <textarea
                data-testid="spark-answer-input"
                value={answer}
                onChange={e => setAnswer(e.target.value)}
                rows={4}
                placeholder="Type your answer."
                className="pm-input flex-1"
                style={{ fontSize: 15 }}
              />
              <Button data-testid="spark-submit-answer" onClick={send} disabled={submitting || !answer.trim()} className="h-[54px] !px-5">
                {submitting ? "…" : <><SendHorizontal size={16} aria-hidden="true" /> Send</>}
              </Button>
            </div>
          )}

          {/* After the interview the only text is the closing message (plain text; React escapes it). */}
          {!inProgress && view.closing_message && (
            <Card className="mt-6" padding="24px" data-testid="spark-closing">
              <p className="font-display font-semibold" style={{ fontSize: 18, color: "var(--pm-ink)" }}>
                {view.closing_message}
              </p>
              {view.attempt_id && (
                <div className="mt-6">
                  <Button onClick={() => navigate(`/attempt/${view.attempt_id}/report`)}>Go to your report</Button>
                </div>
              )}
            </Card>
          )}
        </div>
      </PageShell>
    </div>
  );
}
