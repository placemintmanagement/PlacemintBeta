import React, { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { TID } from "../testIds";
import { SendHorizontal } from "lucide-react";
import { PageShell, SectionLabel, PageTitle, Card, Button } from "../components/shared";

// Defensive: never trust a prompt/text field is a string. Legacy interview
// documents in the DB may have object prompts from earlier LLM outputs.
const asText = (v) => {
  if (v == null) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  try { return JSON.stringify(v, null, 2); } catch { return String(v); }
};

// Body-size meta text (never monospace).
const META = { fontSize: 14, color: "rgba(11,42,48,0.7)" };
const BODY = { fontSize: 15, color: "var(--pm-ink)", lineHeight: 1.6 };

// Avatar disc: teal-deep for the interviewer, teal-night for the candidate.
function Avatar({ tone, children }) {
  return (
    <div className="w-9 h-9 rounded-full grid place-items-center font-display font-semibold shrink-0"
         style={{ fontSize: 14, background: tone === "you" ? "var(--pm-teal-night)" : "var(--pm-teal-deep)", color: "var(--pm-white)" }}>
      {children}
    </div>
  );
}

export default function Interview() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const [interview, setInterview] = useState(null);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [transcript, setTranscript] = useState([]);
  const bottomRef = useRef(null);

  useEffect(() => {
    api.get(`/interview/${interviewId}`).then(r => {
      setInterview(r.data);
      // Reconstruct transcript from stored answers
      const t = [];
      (r.data.questions || []).forEach((q, i) => {
        const ans = r.data.answers?.[i];
        if (ans) {
          t.push({ role: "interviewer", text: asText(q.prompt), kind: q.kind });
          t.push({ role: "you", text: asText(ans.answer) });
          if (ans.grade?.one_line_verdict) t.push({ role: "verdict", text: asText(ans.grade.one_line_verdict) });
        }
      });
      // Add current pending question
      const idx = r.data.current_index || 0;
      if (idx < (r.data.questions || []).length) {
        const cur = r.data.questions[idx];
        t.push({ role: "interviewer", text: asText(cur.prompt), kind: cur.kind });
      }
      setTranscript(t);
    }).catch(() => toast.error("Interview not found"));
  }, [interviewId]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [transcript]);

  const currentQ = interview?.questions?.[interview.current_index];

  const send = async () => {
    if (!answer.trim() || !currentQ) return;
    setSubmitting(true);
    try {
      const you = { role: "you", text: answer };
      setTranscript(t => [...t, you]);
      const { data } = await api.post(`/interview/${interviewId}/answer`, {
        question_id: currentQ.id,
        answer,
      });
      setAnswer("");
      const verdict = { role: "verdict", text: asText(data.grade?.one_line_verdict) || "Got it." };
      setTranscript(t => [...t, verdict]);

      const fresh = await api.get(`/interview/${interviewId}`);
      setInterview(fresh.data);
      if (data.status === "completed") {
        toast.success("Interview complete! Building final report…");
        setTimeout(() => navigate(`/attempt/${fresh.data.attempt_id}/report`), 400);
      } else {
        const nq = fresh.data.questions[fresh.data.current_index];
        if (nq) setTranscript(t => [...t, { role: "interviewer", text: asText(nq.prompt), kind: nq.kind }]);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to submit");
    } finally { setSubmitting(false); }
  };

  if (!interview) return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Loading…</div></PageShell></div>;

  return (
    <div>
      <Header light />
      <PageShell>
        <div className="max-w-4xl mx-auto pm-in">
          <SectionLabel>{interview.company_name} · interview</SectionLabel>
          <PageTitle as="h2" style={{ fontSize: "clamp(1.75rem, 3vw, 2.25rem)" }}>Adaptive interview</PageTitle>
          <div className="mt-2" style={META}>Question {Math.min((interview.current_index ?? 0) + 1, interview.questions.length)} of {interview.questions.length}</div>

          {/* Chat */}
          <Card className="mt-6 space-y-5 max-h-[60vh] overflow-y-auto" padding="24px">
            {transcript.map((m, i) => {
              if (m.role === "interviewer") return (
                <div key={i} className="flex gap-3">
                  <Avatar tone="interviewer">I</Avatar>
                  <div className="flex-1 min-w-0">
                    {m.kind && <div className="pm-eyebrow mb-1" style={{ fontSize: 11, color: "rgba(11,42,48,0.7)" }}>{m.kind}</div>}
                    <div className="rounded-[18px] p-4 whitespace-pre-wrap" style={{ ...BODY, background: "var(--pm-grey)", border: "1px solid rgba(7,59,67,0.08)" }}>{m.text}</div>
                  </div>
                </div>
              );
              if (m.role === "you") return (
                <div key={i} className="flex gap-3 justify-end">
                  <div className="max-w-[80%] p-4 rounded-[18px] rounded-tr-[4px] whitespace-pre-wrap" style={{ fontSize: 15, lineHeight: 1.6, background: "var(--pm-teal-deep)", color: "var(--pm-white)" }}>{m.text}</div>
                  <Avatar tone="you">You</Avatar>
                </div>
              );
              return (
                <div key={i} className="flex gap-3">
                  <div className="w-9 h-9 shrink-0" aria-hidden="true"></div>
                  <div style={{ ...META, fontStyle: "italic" }}>{m.text}</div>
                </div>
              );
            })}
            <div ref={bottomRef} />
          </Card>

          {/* Input */}
          {currentQ && (
            <div className="mt-4 flex gap-3 items-end">
              <textarea
                data-testid={TID.intvAnswerInput}
                value={answer}
                onChange={e => setAnswer(e.target.value)}
                rows={3}
                placeholder="Type your answer. Be specific. Real interviewers dislike vague answers."
                className="pm-input flex-1"
                style={{ fontSize: 15 }}
              />
              <Button
                data-testid={TID.intvSubmitAnswer}
                onClick={send} disabled={submitting || !answer.trim()}
                className="h-[54px] !px-5"
              >
                {submitting ? "…" : <><SendHorizontal size={16} aria-hidden="true"/> Send</>}
              </Button>
            </div>
          )}
        </div>
      </PageShell>
    </div>
  );
}
