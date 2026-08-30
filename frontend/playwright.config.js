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
      timeout: 90_000,
      reuseExistingServer: false,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: `node e2e/start-test-frontend.js`,
      cwd: __dirname,
      env: { TEST_AUTH_TOKEN, TEST_BACKEND_PORT: String(BACKEND_PORT), TEST_FRONTEND_PORT: String(FRONTEND_PORT) },
      url: `http://localhost:${FRONTEND_PORT}`,
      timeout: 300_000,
      reuseExistingServer: false,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
