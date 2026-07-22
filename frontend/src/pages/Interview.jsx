import React, { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { TID } from "../testIds";
import { SendHorizontal } from "lucide-react";

// Defensive: never trust a prompt/text field is a string. Legacy interview
// documents in the DB may have object prompts from earlier LLM outputs.
const asText = (v) => {
  if (v == null) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  try { return JSON.stringify(v, null, 2); } catch { return String(v); }
};

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

  if (!interview) return <div><Header /><div className="p-10 text-center">Loading…</div></div>;

  return (
    <div>
      <Header />
      <div className="max-w-4xl mx-auto px-6 py-8 pm-in">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-2">{interview.company_name} · interview</div>
        <h1 className="font-display text-3xl font-bold">Adaptive interview</h1>
        <div className="mt-1 text-sm text-pm-text2">Question {Math.min((interview.current_index ?? 0) + 1, interview.questions.length)} of {interview.questions.length}</div>

        {/* Chat */}
        <div className="mt-6 pm-card p-6 space-y-4 max-h-[60vh] overflow-y-auto">
          {transcript.map((m, i) => {
            if (m.role === "interviewer") return (
              <div key={i} className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-pm-primary text-white grid place-items-center font-mono font-bold text-xs shrink-0">I</div>
                <div className="flex-1">
                  {m.kind && <div className="text-[10px] font-mono uppercase text-pm-text2 mb-1">{m.kind}</div>}
                  <div className="pm-card p-4 !hover:transform-none">{m.text}</div>
                </div>
              </div>
            );
            if (m.role === "you") return (
              <div key={i} className="flex gap-3 justify-end">
                <div className="max-w-[80%] bg-pm-primary text-white p-4 rounded-2xl rounded-tr-sm">{m.text}</div>
                <div className="w-8 h-8 rounded-full bg-[#0A0A0A] text-white grid place-items-center font-mono font-bold text-xs shrink-0">You</div>
              </div>
            );
            return (
              <div key={i} className="flex gap-3">
                <div className="w-8 h-8"></div>
                <div className="text-xs font-mono text-pm-text2 italic">{m.text}</div>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        {currentQ && (
          <div className="mt-4 flex gap-2 items-end">
            <textarea
              data-testid={TID.intvAnswerInput}
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              rows={3}
              placeholder="Type your answer. Be specific. Real interviewers dislike vague answers."
              className="pm-input font-sans flex-1"
            />
            <button
              data-testid={TID.intvSubmitAnswer}
              onClick={send} disabled={submitting || !answer.trim()}
              className="pm-btn pm-btn-primary h-[54px] px-5">
              {submitting ? "…" : <><SendHorizontal size={16}/> Send</>}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
