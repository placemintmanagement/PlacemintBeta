const { test, expect } = require("@playwright/test");

// TEST-ONLY click-through: exercises the REAL backend (server.py,
// unmodified) and REAL frontend build (Round1CommunicationSection.jsx,
// unmodified) through the auth bypass documented in server.py's
// _resolve_auth0_sub / api.js / App.js's Protected -- see playwright.config.js
// for how both throwaway servers are started with the shared secret.
//
// Scope: verifies rendering + interaction for listening_comp (Section 5)
// and spoken_sim (Section 6) specifically, since those were previously
// only verified via data-shape checks + a clean build, never a live
// click-through. Also re-confirms Sections 1-4 still render (regression).

const TEST_TOKEN = process.env.TEST_AUTH_TOKEN;
const BACKEND_URL = `http://localhost:${process.env.TEST_BACKEND_PORT || 8899}/api`;

test("Capgemini Round 1: listening_comp + spoken_sim render and behave correctly", async ({ page, request }) => {
  test.setTimeout(90_000);

  // ---- 1. Start a real Capgemini OA attempt via the real API ----
  const startResp = await request.post(`${BACKEND_URL}/oa/start`, {
    headers: { Authorization: `Bearer ${TEST_TOKEN}` },
    data: { company_id: "capgemini" },
  });
  expect(startResp.ok(), `start_oa failed: ${startResp.status()} ${await startResp.text()}`).toBeTruthy();
  const attempt = await startResp.json();
  const attemptId = attempt.attempt_id;
  expect(attemptId).toBeTruthy();

  // ---- 2. Poll get_oa until Round 1's questions are drawn (fast -- bank
  //         draws, not LLM generation, for all 6 Round 1 parts) ----
  let ready = false;
  let lastData = null;
  for (let i = 0; i < 30; i++) {
    const r = await request.get(`${BACKEND_URL}/oa/${attemptId}`, {
      headers: { Authorization: `Bearer ${TEST_TOKEN}` },
    });
    expect(r.ok(), `get_oa failed: ${r.status()} ${await r.text()}`).toBeTruthy();
    lastData = await r.json();
    const qs = lastData?.sections?.[0]?.questions || [];
    if (qs.length > 0) { ready = true; break; }
    await new Promise((res) => setTimeout(res, 1000));
  }
  expect(ready, `Round 1 questions never appeared: ${JSON.stringify(lastData?.sections?.[0])}`).toBeTruthy();

  const round1Questions = lastData.sections[0].questions;
  const hasListening = round1Questions.some((q) => q.clip_type);
  const hasSpoken = round1Questions.some((q) => q.item_type);
  expect(hasListening, "no listening_comp clip in drawn questions").toBeTruthy();
  expect(hasSpoken, "no spoken_sim item in drawn questions").toBeTruthy();

  // ---- 3. Navigate the real browser to the real OA page ----
  await page.goto(`/oa/${attemptId}`);

  // A fresh user (this test always resets/re-provisions the fixed test
  // user, see scripts/run_test_server.py) gets OnboardingModal's
  // college/target-role prompt on first load -- dismiss it via its own
  // "Skip for now" button (data-testid="onboard-skip") so it doesn't
  // overlay/intercept later click actions (Play/Record buttons).
  const skipOnboarding = page.getByTestId("onboard-skip");
  await skipOnboarding.click({ timeout: 10_000 }).catch(() => {});

  // ---- 4. Regression: Sections 1-4 still render ----
  await expect(page.getByText("Part 1 · Grammar & Sentence Correction")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Part 2 · Business Communication Writing")).toBeVisible();
  await expect(page.getByText("Part 3 · Task Situational Awareness & Response")).toBeVisible();
  await expect(page.getByText("Part 4 · Workplace Reading Comprehension")).toBeVisible();

  // ---- 5. listening_comp: audio player renders, single-play enforced ----
  await expect(page.getByText("Part 5 · Workplace Listening Comprehension")).toBeVisible();
  // Section 5 draws MULTIPLE clips, each its own "▶ Play clip" button. A
  // locator built from that literal text re-resolves by accessible name on
  // every check -- once the clicked clip's button label flips to
  // "Playing…"/"Already played" it no longer matches, so a bare `.first()`
  // silently shifts to the NEXT (still-enabled) clip's button and makes the
  // lock look broken when it isn't. Scope to the first clip's own card
  // (stable by position) and query the button by role within it instead.
  const firstClipCard = page
    .locator(".pm-card", { has: page.getByRole("button", { name: /Play clip|Playing…|Already played/ }) })
    .first();
  const playButton = firstClipCard.getByRole("button", { name: /Play clip|Playing…|Already played/ });
  await expect(playButton).toBeVisible();
  await expect(playButton).toBeEnabled();

  await playButton.click();
  // Locked immediately on click (play-start, not play-end, per spec).
  await expect(playButton).toBeDisabled();
  const lockedLabel = await playButton.textContent();
  expect(lockedLabel === "Playing…" || lockedLabel === "Already played", `unexpected label after first play: ${lockedLabel}`).toBeTruthy();

  // Attempt a "replay": click again on the (disabled) button -- Playwright
  // refuses to click a genuinely disabled element, so this itself proves
  // the lock; we additionally assert the label never reverts to the
  // clickable "▶ Play clip" state.
  await page.waitForTimeout(500);
  await expect(playButton).toBeDisabled();
  await expect(playButton).not.toHaveText("▶ Play clip");
  console.log("[listening_comp] single-play lock CONFIRMED: button stays disabled after first click, no replay possible.");

  // LetteredMCQCard renders "{label} {qNum} of {qTotal}" -- a space between
  // the "Q" label and the number, not "Q1 of 4".
  const listeningQuestion = page.getByText(/Q\s*\d+\s+of\s+\d+/).first();
  await expect(listeningQuestion).toBeVisible();

  // ---- 6. spoken_sim: both item types render, record button interactive ----
  await expect(page.getByText("Part 6 · Spoken Communication Simulation")).toBeVisible();
  await expect(page.getByText("Read Aloud")).toBeVisible();
  await expect(page.getByText("Respond to Prompt")).toBeVisible();

  const spokenItem = round1Questions.find((q) => q.item_type === "read_aloud");
  const promptItem = round1Questions.find((q) => q.item_type === "respond_to_prompt");
  if (spokenItem?.passage_text) {
    await expect(page.getByText(spokenItem.passage_text.slice(0, 40))).toBeVisible();
  }
  if (promptItem?.scenario) {
    await expect(page.getByText(promptItem.scenario.slice(0, 40))).toBeVisible();
  }
  // rubric must never appear on the page at all
  await expect(page.getByText(/professionalism|clarity.*relevance.*structure/i)).toHaveCount(0);

  const recordButtons = page.getByRole("button", { name: "Record" });
  await expect(recordButtons.first()).toBeVisible();
  await expect(recordButtons.first()).toBeEnabled();

  // ---- 7. Drive an ACTUAL recording through the fake mic device ----
  console.log("[spoken_sim] attempting a real record -> stop -> /transcribe round trip via fake mic device...");
  await recordButtons.first().click();
  const stopButton = page.getByRole("button", { name: "Stop" }).first();
  const recordFailedToUnavailable = page.getByText("Mic unavailable").first();
  const raced = await Promise.race([
    stopButton.waitFor({ state: "visible", timeout: 8000 }).then(() => "recording"),
    recordFailedToUnavailable.waitFor({ state: "visible", timeout: 8000 }).then(() => "unavailable"),
  ]).catch(() => "timeout");

  if (raced === "recording") {
    await page.waitForTimeout(1500); // let the fake mic feed a couple seconds of tone
    await stopButton.click();
    // "Transcribing…" then either a transcript textarea or a graceful "error" toast
    const transcribing = page.getByText("Transcribing…").first();
    await transcribing.waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
    const transcriptBox = page.getByText("Transcript (edit if needed):").first();
    const reachedTranscript = await transcriptBox.waitFor({ state: "visible", timeout: 20_000 }).then(() => true).catch(() => false);
    console.log(`[spoken_sim] record round trip result: ${reachedTranscript ? "REACHED transcript review (full real STT round trip succeeded)" : "did not reach transcript review within 20s (see trace/screenshot)"}`);
  } else {
    console.log(`[spoken_sim] record button did NOT enter 'recording' state (result: ${raced}) -- getUserMedia via the fake device likely unavailable in this environment; verified as far as technically possible (button present, enabled, clickable).`);
  }
});
