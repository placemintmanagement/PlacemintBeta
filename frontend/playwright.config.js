// @ts-check
const { defineConfig, devices } = require("@playwright/test");
const path = require("path");

// TEST-ONLY secret shared between the throwaway backend (scripts/
// run_test_server.py) and throwaway frontend (e2e/start-test-frontend.js)
// this config starts. NOT a real secret worth protecting by obscurity --
// it only ever matters when the backend process ALSO has ENVIRONMENT=test
// set (never true in any real deployment; see server.py's
// _resolve_auth0_sub and .env.example's TEST-ONLY section for the full
// reasoning). Safe to hardcode and commit.
const TEST_AUTH_TOKEN = "e2e-playwright-fixed-test-secret-2026-do-not-use-elsewhere";
const BACKEND_PORT = 8899;
const FRONTEND_PORT = 3899;

process.env.TEST_AUTH_TOKEN = TEST_AUTH_TOKEN;

module.exports = defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    permissions: ["microphone"],
    launchOptions: {
      // Feeds a real (synthetic tone) audio file into getUserMedia instead
      // of rejecting it or using a real mic -- lets the E2E test drive the
      // ACTUAL record -> MediaRecorder -> POST /transcribe -> Whisper flow
      // in headless Chromium, not just check that a button exists.
      args: [
        "--use-fake-device-for-media-stream",
        "--use-fake-ui-for-media-stream",
        `--use-file-for-fake-audio-capture=${path.resolve(__dirname, "e2e/fake-mic-audio.wav")}`,
      ],
    },
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  // Starts BOTH throwaway servers before the test run and tears them down
  // after -- reuseExistingServer:false so a stray already-running process
  // on these test-only ports never gets silently reused with stale env.
  webServer: [
    {
      command: `python scripts/run_test_server.py --port ${BACKEND_PORT} --token ${TEST_AUTH_TOKEN} --frontend-port ${FRONTEND_PORT}`,
      cwd: path.resolve(__dirname, "../backend"),
      url: `http://localhost:${BACKEND_PORT}/api/companies`,
      // Was 90_000 -- too tight. server.py's own fail-fast import (every
      // bank re-executes its reference solutions at import time) has been
      // directly measured between ~40s and ~143s depending on machine
      // load/caching, and Python block-buffers stdout when piped (not a
      // TTY), so a slow boot can silently exceed the old timeout with ZERO
      // captured output before Playwright kills the process -- exactly
      // what happened running this suite for Round 4 (AI-Assisted Coding).
      // Raised with real margin above the worst measured case; a passing
      // run's wall-clock time is unaffected, this only stops a slow-but-
      // legitimate boot from being killed as a false failure.
      timeout: 180_000,
      reuseExistingServer: false,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: `node e2e/start-test-frontend.js`,
      cwd: __dirname,
      env: { TEST_AUTH_TOKEN, TEST_BACKEND_PORT: String(BACKEND_PORT), TEST_FRONTEND_PORT: String(FRONTEND_PORT) },
      url: `http://localhost:${FRONTEND_PORT}`,
      // Was 300_000 -- a standalone `yarn build` measured at ~129s, but
      // this build runs CONCURRENTLY with the backend webServer above
      // (heavy fail-fast Python import + a background worker), and
      // resource contention between the two has been directly observed to
      // roughly triple the build's wall-clock time on this machine (a
      // ~4.7min close call during Round 3's own click-through, then an
      // actual timeout here during Round 4's). Raised with real margin
      // above that observed worst case -- same "false failure on a slow
      // but legitimate boot" fix as the backend timeout above.
      timeout: 480_000,
      reuseExistingServer: false,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
