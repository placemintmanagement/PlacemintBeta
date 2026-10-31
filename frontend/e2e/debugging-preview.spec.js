const { test, expect } = require("@playwright/test");

// TEST-ONLY click-through: exercises the REAL frontend build
// (DebuggingSection.jsx / DevDebuggingPreview.jsx, unmodified by this test)
// AND the REAL backend (server.py's new POST /api/dev/debugging/run route,
// which calls debugging_bank.grade_debugging_submission() -> the real
// code_runner pipeline) through the same auth bypass documented in
// server.py's _resolve_auth0_sub / api.js -- see playwright.config.js for
// how both throwaway servers are started with the shared secret.
//
// Scope: Round 3 (Debugging Assessment) is NOT wired into companies.py or
// any real company's round list, so this drives the standalone
// /dev/debugging-preview route instead of a real OA attempt. That's the
// one deliberate gap vs. a full company-round click-through -- noted here,
// not glossed over.
//
// Critical check this test exists to make: a clean webpack compile and a
// working grade_debugging_submission() in isolation (already verified
// separately) do NOT prove the Run/Submit buttons in the actual rendered
// page are wired to real grading. This drives the actual buttons and reads
// the actual rendered pass/fail text.

const TEST_TOKEN = process.env.TEST_AUTH_TOKEN;

test("Debugging Assessment preview: renders 2 problems across languages and grades real Run/Submit actions", async ({ page }) => {
  test.setTimeout(90_000);

  await page.goto("/dev/debugging-preview");

  // Fresh test user (see run_test_server.py's reset) gets OnboardingModal on
  // first load -- dismiss it defensively, same as round1-listening-spoken.spec.js.
  await page.getByTestId("onboard-skip").click({ timeout: 10_000 }).catch(() => {});

  await expect(page.getByText("Debugging Assessment: interface preview")).toBeVisible({ timeout: 20_000 });

  // ---- 1. Problem 1 (two-sum, arrays) renders: title, task description, sample tests ----
  await expect(page.getByText("Two Sum", { exact: true })).toBeVisible();
  await expect(page.getByText(/returning nothing on some inputs/)).toBeVisible();
  await expect(page.getByText(/2 7 11 15/)).toBeVisible(); // sample test input

  const codeArea = page.getByTestId("debug-code-area");
  const langSelect = page.getByTestId("debug-lang-select");

  // Defaults to Python; the buggy starter code should already be pre-loaded
  // (its own off-by-one loop bound, not the reference's).
  await expect(langSelect).toHaveValue("python");
  await expect(codeArea).toHaveValue(/for i in range\(1, n\)/);

  // ---- 2. Switch problem 1 to Java -- editor content must actually change ----
  await langSelect.selectOption("java");
  await expect(codeArea).toHaveValue(/public class Main/);
  await expect(codeArea).toHaveValue(/for \(int i = 1; i < n; i\+\+\)/); // same off-by-one bug, Java translation

  // ---- 3. Switch to problem 2 (tree-invert, trees) -- different topic ----
  await page.getByTestId("debug-problem-tab-1").click();
  await expect(page.getByText("Invert Binary Tree", { exact: true })).toBeVisible();
  await expect(page.getByText(/recurses into the LEFT child twice/)).toBeVisible();
  await expect(page.getByText(/4 2 7 1 3 6 9/)).toBeVisible();

  // Problem 2's own language state is independent of problem 1's -- should
  // still default to Python with ITS buggy code (the doubled invert(n.l) call).
  await expect(langSelect).toHaveValue("python");
  await expect(codeArea).toHaveValue(/invert\(n\.l\); invert\(n\.l\)/);

  // Switch problem 2 to C -- a THIRD language exercised across the 2 problems.
  await langSelect.selectOption("c");
  await expect(codeArea).toHaveValue(/typedef struct Node/);
  await expect(codeArea).toHaveValue(/invert\(n->l\); invert\(n->l\);/);

  console.log("[render checks] PASSED: both problems' statement/task/sample-tests render, buggy code correctly reflects the selected language across 3 languages (python/java/c).");

  // ================================================================
  // CRITICAL CHECK: Run/Submit are wired to REAL grading, not a mock.
  // ================================================================

  // ---- 4. Back to problem 1 (Python, unchanged buggy code) -- Run must show a MIXED result ----
  // two-sum's buggy code (loop starts at i=1) is verified to pass visible
  // test 0 and fail visible test 1 -- NOT uniformly pass or fail. Seeing
  // that exact mixed pattern in the real UI is strong evidence this is
  // really executing the code, not a client-side "changed vs unchanged" mock.
  await page.getByTestId("debug-problem-tab-0").click();
  await expect(langSelect).toHaveValue("java"); // problem 1's own language state persisted from step 2
  await page.getByTestId("debug-run-btn").click();
  const runResults = page.getByTestId("debug-run-results");
  await expect(runResults).toBeVisible({ timeout: 15_000 });
  await expect(runResults.getByText("passed", { exact: false })).toHaveCount(1);
  await expect(runResults.getByText("failed", { exact: false })).toHaveCount(1);
  console.log("[unchanged buggy code] CONFIRMED mixed pass/fail on real Run -- matches the verified buggy-code behavior, not a mock.");

  // ---- 5. Paste the KNOWN-CORRECT Java reference solution -- Run must show ALL PASS ----
  const JAVA_REFERENCE = `import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt();
        long[] a = new long[n];
        for (int i = 0; i < n; i++) a[i] = sc.nextLong();
        long t = sc.nextLong();
        Map<Long, Integer> seen = new HashMap<>();
        for (int i = 0; i < n; i++) {
            long need = t - a[i];
            if (seen.containsKey(need)) { System.out.println(seen.get(need) + " " + i); return; }
            seen.put(a[i], i);
        }
    }
}
`;
  await codeArea.fill(JAVA_REFERENCE, { force: true });
  await page.getByTestId("debug-run-btn").click();
  await expect(runResults.getByText("failed", { exact: false })).toHaveCount(0, { timeout: 15_000 });
  await expect(runResults.getByText("passed", { exact: false })).toHaveCount(2);
  console.log("[correct fix] CONFIRMED both sample tests pass on real Run after pasting the reference solution.");

  // ---- 6. Submit session -- problem 1 fixed (Java), problem 2 left on its buggy C default ----
  await page.getByTestId("debug-problem-tab-1").click();
  await expect(langSelect).toHaveValue("c"); // seeded once already in step 3; confirm it persisted
  await page.getByTestId("debug-problem-tab-0").click(); // back to the fixed problem before submitting

  await page.getByRole("button", { name: "Submit session" }).click();
  await expect(page.getByText("Session complete")).toBeVisible({ timeout: 15_000 });
  const summary = page.locator("pre");
  await expect(summary).toBeVisible({ timeout: 15_000 });
  const submittedJson = JSON.parse(await summary.textContent());
  console.log("[submit session] real grading response:", JSON.stringify(submittedJson));

  const p1 = submittedJson.find((r) => r.problem_id === "two-sum");
  const p2 = submittedJson.find((r) => r.problem_id === "tree-invert");
  expect(p1, "two-sum missing from submit response").toBeTruthy();
  expect(p2, "tree-invert missing from submit response").toBeTruthy();
  expect(p1.passed, `two-sum (fixed Java) should have passed: ${JSON.stringify(p1)}`).toBe(true);
  expect(p2.passed, `tree-invert (unchanged buggy C default) should NOT have passed: ${JSON.stringify(p2)}`).toBe(false);
  console.log("[submit session] CONFIRMED: fixed problem passed, untouched-buggy problem failed -- via the real Submit action, second independent code path to the same backend endpoint.");
});
