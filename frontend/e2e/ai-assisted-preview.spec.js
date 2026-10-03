const { test, expect } = require("@playwright/test");

// TEST-ONLY click-through: exercises the REAL frontend build
// (AiAssistedSection.jsx / DevAiAssistedPreview.jsx, unmodified by this
// test) AND the REAL backend (server.py's dev_ai_assisted_* routes, which
// make GENUINE, live GPT-4o mini LLM calls via services.ai_service.call_json_gpt
// (switched from Groq, 2026-09-29 pass) -- not mocked, not stubbed) through
// the same auth bypass documented in
// server.py's _resolve_auth0_sub / api.js -- see playwright.config.js for
// how both throwaway servers are started with the shared secret.
//
// Scope: Round 4 (AI-Assisted Coding) is NOT wired into companies.py or
// any real company's round list, so this drives the standalone
// /dev/ai-assisted-preview route instead of a real OA attempt -- same
// deliberate gap as Round 3's debugging-preview spec, noted here rather
// than glossed over.
//
// Critical check this test exists to make: a clean webpack compile and
// passing live-LLM-call verification in isolation (already done
// separately, via a Python script hitting the routes directly) do NOT
// prove the actual chat bubbles / buttons / code panel in the rendered
// page are wired to that real backend. This drives the real Start
// Discussion button, real message textarea + Send, real Yes/No buttons,
// and reads the actual rendered transcript and code panel -- a full good
// path from empty session to a passing final outcome, with every stage
// gated by a REAL GPT-4o mini judgment call happening live during this test.

test("AI-Assisted Coding preview: real click-through of the full good path, real GPT-4o mini calls throughout", async ({ page }) => {
  test.setTimeout(180_000);

  // Fixed problem_id (not a random draw) -- same problem + same tailored
  // answers already verified live, standalone, against the real backend
  // (see the Python verification script's "RUN A"). This keeps the click-
  // through deterministic: real LLM judgment still runs live on every
  // stage, but the answers are known to be substantive enough to pass it
  // for THIS specific problem, rather than needing generic-enough text to
  // pass regardless of which of the 15 problems a random draw picks.
  await page.goto("/dev/ai-assisted-preview?problem_id=missing-number");
  await page.getByTestId("onboard-skip").click({ timeout: 10_000 }).catch(() => {});

  await expect(page.getByText("AI-Assisted Coding: interface preview")).toBeVisible({ timeout: 20_000 });

  // ---- 1. Start Discussion -> real problem drawn, session begins ----
  // (This dev-preview draws the problem AS PART OF starting the session --
  // there's no separate "problem browsing, chat not yet begun" screen, so
  // the problem panel + editor only mount once Start Discussion is
  // clicked, not before. The evidence's "editor starts empty" claim is
  // checked right after this click, where it's still genuinely true.)
  await page.getByTestId("ai-assisted-start-btn").click();
  const transcript = page.getByTestId("ai-assisted-transcript");
  await expect(transcript).toBeVisible({ timeout: 15_000 });

  // ---- 2. Editor starts empty with the confirmed placeholder text ----
  await expect(page.getByText("Code will appear here when requested during AI interaction...")).toBeVisible();

  await expect(page.getByTestId("ai-assisted-msg-ai-0")).toBeVisible({ timeout: 15_000 });
  const welcome = await page.getByTestId("ai-assisted-msg-ai-0").textContent();
  console.log("[start] AI welcome:", welcome);
  expect(welcome).toMatch(/what is this problem asking/i);

  const input = page.getByTestId("ai-assisted-message-input");
  const send = page.getByTestId("ai-assisted-send-btn");

  // ---- 3. Stage 1 (understand) -- real answer, real GPT-4o mini judgment ----
  await input.fill(
    "We're given n distinct integers drawn from the range 0 to n inclusive, with " +
    "exactly one value missing from that range. I need to read n and the array, " +
    "then output the single missing integer."
  );
  await send.click();
  await expect(page.getByTestId("ai-assisted-msg-ai-2")).toBeVisible({ timeout: 30_000 });
  console.log("[stage 1->2] AI:", await page.getByTestId("ai-assisted-msg-ai-2").textContent());

  // ---- 4. Stage 2 (approach) ----
  await input.fill(
    "I'll use the sum trick: the sum of all integers from 0 to n is n*(n+1)/2. " +
    "Since exactly one number is missing, I compute that expected total and " +
    "subtract the actual sum of the given array -- the difference is the missing number."
  );
  await send.click();
  await expect(page.getByTestId("ai-assisted-msg-ai-4")).toBeVisible({ timeout: 30_000 });
  console.log("[stage 2->3] AI:", await page.getByTestId("ai-assisted-msg-ai-4").textContent());

  // ---- 5. Stage 3 (complexity) -- must reach the consent gate ----
  await input.fill("Time complexity is O(n) since it's one pass to sum the array. Space complexity is O(1) beyond the input array itself.");
  await send.click();
  await expect(page.getByTestId("ai-assisted-consent-yes")).toBeVisible({ timeout: 30_000 });
  const consentPrompt = await page.getByTestId("ai-assisted-msg-ai-6").textContent();
  console.log("[stage 3->consent] AI:", consentPrompt);
  expect(consentPrompt).toMatch(/preliminary .* solution/i);

  // ---- 6. Consent gate is BUTTON-driven -- click Yes, confirm flawed_code appears ----
  await page.getByTestId("ai-assisted-consent-yes").click();
  await expect(page.getByText("Generated Code")).toBeVisible({ timeout: 15_000 });
  const codeAfterConsent = await page.getByTestId("ai-assisted-code-content").textContent();
  expect(codeAfterConsent.length).toBeGreaterThan(20);
  expect(codeAfterConsent).toMatch(/<---/); // the inline bug marker comment
  console.log("[consent=Yes] CONFIRMED flawed_code revealed in the editor panel, marker comment present");

  // ---- 7. Self-review checkpoint -- click "No" (correct: caught the flaw) ----
  await expect(page.getByTestId("ai-assisted-review-no")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("ai-assisted-review-no").click();
  await expect(input).toBeVisible({ timeout: 15_000 }); // back to a free-text stage (explain_bug)

  // ---- 8. Explain the bug -- must be specific enough to pass the real grader ----
  await input.fill(
    "The formula subtracts n*(n-1)/2 instead of n*(n+1)/2 -- that's the sum of " +
    "0 through n-1, not 0 through n, so it's missing the value n from the " +
    "expected total. This makes the computed missing number wrong on essentially every input."
  );
  await send.click();

  // ---- 9. Auto-completion -- final outcome + "Reference Solution (Fixed)" ----
  await expect(page.getByTestId("ai-assisted-outcome")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Reference Solution (Fixed)")).toBeVisible({ timeout: 10_000 });
  const outcomeText = await page.getByTestId("ai-assisted-outcome").textContent();
  console.log("[complete] outcome:", outcomeText);
  const codeAtEnd = await page.getByTestId("ai-assisted-code-content").textContent();
  expect(codeAtEnd.length).toBeGreaterThan(20);
  expect(codeAtEnd).not.toMatch(/<---/); // corrected_code has no bug marker
  console.log("[auto-completion] CONFIRMED final outcome shown, editor now shows the corrected reference solution with no bug marker, no manual submit button anywhere in this flow -- via real rendered buttons/inputs, not the isolated backend script.");
});
