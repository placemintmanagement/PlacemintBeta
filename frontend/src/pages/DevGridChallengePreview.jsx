import React, { useState } from "react";
import Header from "../components/Header";
import GridChallengeSection from "../components/games/GridChallengeSection";

// Standing dev tool (not temporary) -- unauthenticated-looking preview
// route at /dev/grid-challenge-preview, BUT unlike the other two dev
// previews this one is NOT self-contained/mocked: grid_challenge's whole
// premise is progressive server-side reveal, so there's nothing honest to
// preview without hitting the real phase-gated endpoints. This page
// expects a real attemptId/sectionKey/puzzleId pointing at an actual
// oa_attempts + game_session fixture already set up server-side (see the
// scratchpad round-trip test script for how one is constructed), and a
// real pm_token in localStorage. Query params let that fixture be swapped
// without editing this file: ?attemptId=...&sectionKey=...&puzzleId=...
export default function DevGridChallengePreview() {
  const [completed, setCompleted] = useState(null);
  const params = new URLSearchParams(window.location.search);
  const attemptId = params.get("attemptId");
  const sectionKey = params.get("sectionKey") || "grid_test";
  const puzzleId = params.get("puzzleId");

  return (
    <div>
      <Header />
      <div className="max-w-3xl mx-auto px-6 py-10">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-1">dev preview · not a real route</div>
        <h1 className="font-display text-2xl font-bold mb-2">Grid Challenge — live preview</h1>
        <p className="text-sm text-pm-text2 mb-6">
          Requires real query params pointing at a live test fixture: <code>?attemptId=...&amp;sectionKey=...&amp;puzzleId=...</code>
        </p>

        {!attemptId || !puzzleId ? (
          <div className="pm-card p-6 text-pm-text2">
            Missing attemptId/puzzleId query params -- this page has nothing mocked to fall back to.
          </div>
        ) : completed ? (
          <div className="pm-card p-6">
            <div className="font-display text-lg font-semibold mb-3">Session complete</div>
            <pre className="text-xs font-mono bg-pm-muted rounded-lg p-4 overflow-auto">
              {JSON.stringify(completed, null, 2)}
            </pre>
          </div>
        ) : (
          <GridChallengeSection
            attemptId={attemptId}
            sectionKey={sectionKey}
            puzzleId={puzzleId}
            onComplete={setCompleted}
          />
        )}
      </div>
    </div>
  );
}
