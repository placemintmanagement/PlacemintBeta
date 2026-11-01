import React, { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { SendHorizontal } from "lucide-react";
import { PageShell, SectionLabel, PageTitle, Card, Button } from "../components/shared";
import { parseErrorDetail } from "../lib/apiError";

// Capgemini Spark interview (text, 35 minutes). Everything time-related comes
// from the server: the deadline and "server_now" arrive with every response, so
// the countdown survives a refresh and does not depend on this device's clock.
// The browser never receives flags, scores, weights, thresholds or rubrics.

const META = { fontSize: 14, color: "var(--gl-muted)" };
const BODY = { fontSize: 15, color: "var(--gl-text)", lineHeight: 1.6 };
const OUTFIT = { fontFamily: "Outfit, system-ui, sans-serif", fontWeight: 600 };

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
  // FEATURE A (humanize, cosmetic only): a brief "typing..." pause before the
  // next interviewer message appears, and an idle nudge after IDLE_SECONDS of
  // no input. Neither one changes the server deadline or turn timing -- both
  // are purely client-side and a no-op when the server has HUMANIZE_ENABLED off
  // (the server then never sets `ai_interviewer` on the view, so these paths
  // just never trigger).
  const [typing, setTyping] = useState(false);
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

  // FEATURE A idle prompt (STATED): after 90s with no input, ask the server
  // for its fixed idle line. Resets on every keystroke and whenever the
  // current question changes. A plain no-op call when the server has
  // HUMANIZE_ENABLED off (interview_idle then just returns the view
  // unchanged), so this is always safe to fire.
  useEffect(() => {
    if (!inProgress || !view?.current_question?.id || typing) return;
    const id = setTimeout(async () => {
      try {
        const { data } = await api.post(`/interview/${interviewId}/idle`);
        applyView(data);
      } catch {
        // a failed idle ping is not worth surfacing to the candidate
      }
    }, 90000);
    return () => clearTimeout(id);
  }, [answer, view?.current_question?.id, inProgress, typing, interviewId, applyView]);

  // Shared by the normal Send button and the DSA-stage "Ask for a hint"
  // button below -- both post through the exact same answer endpoint (no
  // new route), get the exact same soft-refetch handling for a 409
  // (turn_in_progress included -- the hint path shares the same atomic
  // turn claim as any other submission), and the exact same
  // submitting-disabled guard. `clearDraft` is false for a hint request so
  // the candidate's own in-progress typed answer is never touched by it.
  const submitAnswer = async (text, clearDraft) => {
    const q = view?.current_question;
    if (!q || !text.trim() || submitting) return;
    setSubmitting(true);
    try {
      const { data } = await api.post(`/interview/${interviewId}/answer`, { question_id: q.id, answer: text });
      if (clearDraft) setAnswer("");
      if (data.ai_interviewer) {
        // FEATURE A typing indicator (STATED, cosmetic only): 1-3s scaled to
        // the next message's length before it appears. The server's
        // deadline/turn timing is already settled by this point -- this
        // delay only affects when the browser RENDERS the response it
        // already has.
        const text2 = data.current_question?.prompt || data.closing_message || "";
        const delay = Math.min(3000, Math.max(1000, text2.length * 12));
        setTyping(true);
        setSubmitting(false);
        await new Promise((resolve) => setTimeout(resolve, delay));
        setTyping(false);
      }
      applyView(data);
      // A one-off answer-request/confirmation/exhausted-hint reply (STATED:
      // "may stay a one-off note") -- never persisted, so it is shown here
      // and only here, as a toast, exactly like the existing soft-refetch
      // messages below. It never touches the problem statement.
      if (data.notice?.text) toast.message(data.notice.text);
    } catch (err) {
      // parseErrorDetail, not a bare err.response?.data?.detail?.code read:
      // api.js's shared response interceptor stringifies any object-shaped
      // `detail` into JSON text (see src/lib/apiError.js's own docstring),
      // so `.code` was never actually readable here against the REAL
      // interceptor in production -- only in tests that mock api.js
      // directly, bypassing it. parseErrorDetail recovers the original
      // {code, message, ...} object either way.
      const detail = parseErrorDetail(err);
      if (detail.code === "interview_already_in_progress" && detail.interview_id) {
        // This interview was superseded by another one already in
        // progress (e.g. started from a second tab) -- go to the real one
        // instead of showing a stale/broken view of this one.
        navigate(`/interview/${detail.interview_id}`);
        return;
      }
      if (detail.code === "time_up" || detail.code === "stale_question" || detail.code === "stale_turn"
          || detail.code === "interview_closed" || detail.code === "turn_in_progress") {
        toast.message(detail.message || "Refreshing the interview");
        await refresh();
      } else {
        toast.error(detail.message || "Failed to submit");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const send = () => submitAnswer(answer, true);
  const askForHint = () => submitAnswer("Can I get a hint?", false);

  if (!view) return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Loading…</div></PageShell></div>;

  const stageIndex = Math.max(0, view.stages.findIndex(s => s.stage === view.stage));

  return (
    <div>
      <Header light />
      <PageShell>
        <div className="max-w-4xl mx-auto pm-in">
          <SectionLabel>{view.company_name} · interview</SectionLabel>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex items-center gap-2">
              <PageTitle as="h2" style={{ fontSize: "clamp(1.75rem, 3vw, 2.25rem)" }}>Interview</PageTitle>
              {view.ai_interviewer && (
                <span data-testid="spark-ai-tag" className="rounded-full px-3 py-1"
                      style={{ fontSize: 11, fontWeight: 600, background: "color-mix(in srgb, var(--gl-text) 8%, transparent)", color: "var(--gl-text)" }}>
                  {view.persona_label || "AI interviewer"}
                </span>
              )}
            </div>
            {inProgress && (
              <div data-testid="spark-countdown" style={{ ...OUTFIT, fontSize: 22, color: "var(--gl-text)" }}>
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
                      background: current ? "var(--gl-accent)" : done ? "color-mix(in srgb, var(--gl-text) 8%, transparent)" : "transparent",
                      color: current ? "#fff" : "var(--gl-text)",
                      border: "1px solid var(--gl-line)",
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
                <div className="rounded-[18px] p-4 whitespace-pre-wrap" style={{ ...BODY, background: "color-mix(in srgb, var(--gl-text) 6%, transparent)" }}>{asText(t.question)}</div>
                <div className="flex justify-end">
                  <div className="max-w-[80%] p-4 rounded-[18px] rounded-tr-[4px] whitespace-pre-wrap" style={{ fontSize: 15, lineHeight: 1.6, background: "var(--gl-accent)", color: "#fff" }}>{asText(t.answer)}</div>
                </div>
              </div>
            ))}
            {inProgress && view.current_question && !typing && (
              <div data-testid="spark-problem-statement" className="rounded-[18px] p-4 whitespace-pre-wrap" style={{ ...BODY, background: "color-mix(in srgb, var(--gl-text) 6%, transparent)", border: "1px solid var(--gl-line)" }}>
                <div className="mb-1" style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--gl-muted)" }}>{view.current_question.stage}</div>
                {asText(view.current_question.prompt)}
              </div>
            )}
            {/* Hints shown so far for the DSA problem above -- persisted, so
                these come back on a refresh, never replace the statement. */}
            {inProgress && (view.hints?.shown || []).map((h, i) => (
              <div key={i} data-testid="spark-hint-shown" className="rounded-[18px] p-4 whitespace-pre-wrap" style={{ ...BODY, background: "color-mix(in srgb, var(--gl-text) 4%, transparent)", border: "1px solid var(--gl-line)" }}>
                <div className="mb-1" style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--gl-muted)" }}>Hint {h.level}</div>
                <span className="italic" style={{ color: "var(--gl-muted)" }}>{asText(h.lead_in)}</span>{" "}
                {asText(h.text)}
              </div>
            ))}
            {inProgress && typing && (
              <div data-testid="spark-typing-indicator" className="rounded-[18px] p-4 italic" style={{ ...META, background: "color-mix(in srgb, var(--gl-text) 6%, transparent)" }}>
                {view.persona_label || "Interviewer"} is typing…
              </div>
            )}
            <div ref={bottomRef} />
          </Card>

          {/* Input */}
          {inProgress && view.current_question && !typing && (
            <div className="mt-4 flex gap-3 items-end">
              <textarea
                data-testid="spark-answer-input"
                value={answer}
                onChange={e => setAnswer(e.target.value)}
                rows={4}
                placeholder="Type your answer."
                className="gl-field-input flex-1"
                style={{ fontSize: 15 }}
              />
              {view.hints?.available && (
                <Button data-testid="spark-ask-hint" onClick={askForHint} disabled={submitting}
                        variant="secondary" className="h-[54px] !px-4">
                  Ask for a hint
                </Button>
              )}
              <Button data-testid="spark-submit-answer" onClick={send} disabled={submitting || !answer.trim()} className="h-[54px] !px-5">
                {submitting ? "…" : <><SendHorizontal size={16} aria-hidden="true" /> Send</>}
              </Button>
            </div>
          )}
          {inProgress && view.hints && (
            <div data-testid="spark-hints-used" className="mt-2" style={META}>
              Hints used: {view.hints.used}/{view.hints.limit}
            </div>
          )}

          {/* After the interview the only text is the closing message (plain text; React escapes it). */}
          {!inProgress && view.closing_message && (
            <Card className="mt-6" padding="24px" data-testid="spark-closing">
              <p style={{ ...OUTFIT, fontSize: 18, color: "var(--gl-text)" }}>
                {view.closing_message}
              </p>
              {(view.attempt_id || view.interview_id) && (
                <div className="mt-6">
                  <Button onClick={() => navigate(view.attempt_id ? `/attempt/${view.attempt_id}/report` : `/interview/${view.interview_id}/report`)}>Go to your report</Button>
                </div>
              )}
            </Card>
          )}
        </div>
      </PageShell>
    </div>
  );
}
