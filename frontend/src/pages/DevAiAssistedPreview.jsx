import React, { useState } from "react";
import api from "../api";
import Header from "../components/Header";
import AiAssistedSection from "../components/AiAssistedSection";

// Standing dev tool (not temporary) -- preview route at
// /dev/ai-assisted-preview for confirming the Round 4 (AI-Assisted Coding)
// live conversation before it's wired into any real company round. Every
// action here hits the REAL backend (POST /api/dev/ai-assisted/start,
// /message, /consent, /self_review -- server.py) which makes GENUINE,
// live LLM calls (Groq via services.ai_service.call_json_groq -- a
// flagged deviation from this codebase's usual Haiku/Anthropic routing,
// since this environment's ANTHROPIC_API_KEY is empty; see that
// function's docstring) -- nothing here is mocked or simulated, unlike
// most other /dev/* previews (see DevGamePreview.jsx's mockCheckAnswer
// for the pattern this deliberately deviates from, same reasoning as
// /dev/debugging-preview: the whole point of this round is real grading,
// so faking it client-side would make verification meaningless).
//
// Round 4 is NOT wired into companies.py or any real company's round list
// yet. This page authenticates like any other API caller -- itself isn't
// auth-gated (matching every other /dev/* preview), but the calls
// underneath need a real user or the Playwright test-auth bypass.
//
// Supports an optional ?problem_id=<id> query param -- passed straight
// through to /start's body. Purely a testability affordance (lets a
// script/test use a KNOWN problem and write answers tailored to its
// specific bug, rather than needing generic-enough answers to pass real
// LLM sufficiency judgment regardless of which of the 15 problems gets
// drawn). With no query param, a real random problem is drawn via
// ai_assisted_bank.sample_one(), same as before.
export default function DevAiAssistedPreview() {
  const [session, setSession] = useState(null);
  const [sending, setSending] = useState(false);
  const [starting, setStarting] = useState(false);

  const start = async () => {
    setStarting(true);
    try {
      const problemId = new URLSearchParams(window.location.search).get("problem_id");
      const { data } = await api.post("/dev/ai-assisted/start", problemId ? { problem_id: problemId } : {});
      setSession(data);
    } catch (err) {
      console.error("start failed", err);
    } finally {
      setStarting(false);
    }
  };

  const onSendMessage = async (text) => {
    setSending(true);
    try {
      const { data } = await api.post(`/dev/ai-assisted/${session.session_id}/message`, { text });
      setSession(data);
    } catch (err) {
      console.error("message failed", err);
    } finally {
      setSending(false);
    }
  };

  const onConsent = async (value) => {
    setSending(true);
    try {
      const { data } = await api.post(`/dev/ai-assisted/${session.session_id}/consent`, { value });
      setSession(data);
    } catch (err) {
      console.error("consent failed", err);
    } finally {
      setSending(false);
    }
  };

  const onSelfReview = async (value) => {
    setSending(true);
    try {
      const { data } = await api.post(`/dev/ai-assisted/${session.session_id}/self_review`, { value });
      setSession(data);
    } catch (err) {
      console.error("self_review failed", err);
    } finally {
      setSending(false);
    }
  };

  return (
    <div>
      <Header />
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-8">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-1">dev preview · not a real route</div>
        <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
          <h1 className="font-display text-3xl font-bold">AI-Assisted Coding: interface preview</h1>
          <button
            data-testid="ai-assisted-start-btn"
            className="pm-btn pm-btn-primary text-sm py-2 px-4"
            onClick={start}
            disabled={starting}
          >
            {starting ? "Starting…" : session ? "Restart session" : "Start Discussion"}
          </button>
        </div>

        {!session ? (
          <div className="pm-card p-10 text-center text-pm-text2">
            Click "Start Discussion" to draw a real problem and begin a live, LLM-driven session.
          </div>
        ) : (
          <AiAssistedSection
            session={session}
            onSendMessage={onSendMessage}
            onConsent={onConsent}
            onSelfReview={onSelfReview}
            sending={sending}
          />
        )}
      </div>
    </div>
  );
}
