import React, { useEffect, useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import { SendHorizontal, CheckCircle2, XCircle } from "lucide-react";

/**
 * Capgemini Round 4 (AI-Assisted Coding) -- live staged conversation UI.
 *
 * Chat transcript bubbles reuse Interview.jsx's exact convention (AI
 * message = left bubble, candidate = right bubble, "complete"/system-style
 * lines = italic center) -- this is the only existing multi-turn chat
 * component in the app, deliberately not reinvented. The right panel is a
 * dark Monaco editor pane (same "pm-editor-pane" look as CodingSection/
 * DebuggingSection) but READ-ONLY throughout -- the candidate here never
 * writes or edits code, only discusses it (per the confirmed real-evidence
 * flow this round is built against). Starts empty with the exact evidence
 * placeholder text, then shows flawed_code ("Generated Code") once consent
 * is given, then corrected_code ("Reference Solution (Fixed)") at
 * completion -- driven entirely by session.revealed_code, which the
 * backend sets (never guessed client-side).
 *
 * Purely presentational + a thin action layer: `session` is the full,
 * live server document (backend/server.py's dev_ai_assisted_* routes);
 * onSendMessage/onConsent/onSelfReview are async callbacks the parent
 * page wires to the real API calls. NOT wired into OARunner.jsx yet --
 * Round 4 isn't part of any real company's round list (see
 * DevAiAssistedPreview.jsx for the standalone dev-preview this backs).
 */
const FREE_TEXT_STAGES = ["understand", "approach", "complexity", "explain_bug"];

export default function AiAssistedSection({ session, onSendMessage, onConsent, onSelfReview, sending }) {
  const [draft, setDraft] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.transcript?.length]);

  if (!session) return <div className="pm-card p-6">No session yet.</div>;

  const problem = session.problem || {};
  const stage = session.current_stage;
  const inProgress = session.status === "in_progress";
  const revealed = session.revealed_code;
  const outcome = session.final_outcome;

  const send = async () => {
    if (!draft.trim()) return;
    const text = draft;
    setDraft("");
    await onSendMessage(text);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:h-[75vh]">
      {/* Left: problem + chat transcript + input */}
      <div className="pm-card p-6 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between mb-2">
          <div className="font-display text-xl font-bold">{problem.title}</div>
          <span className="pm-chip pm-chip-primary">{problem.difficulty}</span>
        </div>
        <div className="text-sm text-pm-text2 mb-4 whitespace-pre-wrap">{problem.statement}</div>

        <div data-testid="ai-assisted-transcript" className="flex-1 overflow-y-auto space-y-3 border-t border-pm-border pt-4">
          {(session.transcript || []).map((m, i) => {
            if (m.role === "ai") return (
              <div key={i} className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-pm-primary text-white grid place-items-center font-display tabular-nums font-bold text-xs shrink-0">AI</div>
                <div data-testid={`ai-assisted-msg-ai-${i}`} className="pm-card p-3 text-sm flex-1">{m.text}</div>
              </div>
            );
            if (m.role === "candidate") return (
              <div key={i} className="flex gap-3 justify-end">
                <div data-testid={`ai-assisted-msg-candidate-${i}`} className="max-w-[80%] bg-pm-primary text-white p-3 rounded-2xl rounded-tr-sm text-sm">{m.text}</div>
                <div className="w-8 h-8 rounded-full bg-[var(--pm-teal-night)] text-white grid place-items-center font-display tabular-nums font-bold text-xs shrink-0">You</div>
              </div>
            );
            return <div key={i} className="text-xs font-display tabular-nums text-pm-text2 italic text-center">{m.text}</div>;
          })}
          <div ref={bottomRef} />
        </div>

        {/* Free-text input -- only for understand/approach/complexity/explain_bug */}
        {inProgress && FREE_TEXT_STAGES.includes(stage) && (
          <div className="mt-4 flex gap-2 items-end">
            <textarea
              data-testid="ai-assisted-message-input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={2}
              placeholder="Type your answer..."
              className="pm-input font-sans flex-1"
            />
            <button
              data-testid="ai-assisted-send-btn"
              onClick={send}
              disabled={sending || !draft.trim()}
              className="pm-btn pm-btn-primary h-[54px] px-5"
            >
              {sending ? "…" : <><SendHorizontal size={16} /> Send</>}
            </button>
          </div>
        )}

        {/* Consent gate -- buttons only, no free text */}
        {inProgress && stage === "consent" && (
          <div className="mt-4 flex gap-3 justify-center">
            <button data-testid="ai-assisted-consent-yes" onClick={() => onConsent(true)} disabled={sending} className="pm-btn pm-btn-primary px-6">Yes</button>
            <button data-testid="ai-assisted-consent-no" onClick={() => onConsent(false)} disabled={sending} className="pm-btn pm-btn-ghost px-6">No</button>
          </div>
        )}

        {/* Self-review checkpoint -- buttons only, no free text */}
        {inProgress && stage === "self_review" && (
          <div className="mt-4 flex gap-3 justify-center">
            <button data-testid="ai-assisted-review-yes" onClick={() => onSelfReview(true)} disabled={sending} className="pm-btn pm-btn-ghost px-6">Yes</button>
            <button data-testid="ai-assisted-review-no" onClick={() => onSelfReview(false)} disabled={sending} className="pm-btn pm-btn-primary px-6">No</button>
          </div>
        )}

        {/* Final outcome summary */}
        {session.status === "completed" && outcome && (
          <div data-testid="ai-assisted-outcome" className="mt-4 pm-card p-4">
            <div className="flex items-center gap-2 font-display font-semibold">
              {outcome.passed ? <CheckCircle2 size={16} className="text-pm-primary" /> : <XCircle size={16} className="text-pm-secondary" />}
              Score: {(outcome.score * 100).toFixed(0)}% · {outcome.passed ? "Passed" : "Not passed"}
            </div>
            <div className="text-sm text-pm-text2 mt-1">{outcome.reason}</div>
          </div>
        )}
      </div>

      {/* Right: read-only Monaco editor -- empty -> flawed_code -> corrected_code */}
      <div className="pm-editor-pane rounded-2xl overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
          <span className="pm-chip pm-chip-coral">{revealed ? revealed.label : "Code will appear here when requested during AI interaction..."}</span>
        </div>
        <div className="flex-1 min-h-[400px]">
          <Editor
            height="100%"
            language={revealed?.language === "cpp" ? "cpp" : (revealed?.language || "cpp")}
            theme="vs-dark"
            value={revealed?.code || ""}
            options={{ fontSize: 14, minimap: { enabled: false }, fontFamily: "JetBrains Mono", padding: { top: 12 }, scrollBeyondLastLine: false, readOnly: true }}
          />
        </div>
        {/* Read-only mirror for testability -- Monaco has no plain DOM text a
            test can easily assert against; this is never edited (read-only
            throughout), so no onChange/setter is needed, unlike Debugging
            Section's hidden INPUT mirror. */}
        <pre data-testid="ai-assisted-code-content" className="sr-only">{revealed?.code || ""}</pre>
      </div>
    </div>
  );
}
