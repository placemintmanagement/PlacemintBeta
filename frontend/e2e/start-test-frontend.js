// TEST-ONLY launcher for the Playwright E2E click-through test.
//
// Builds a PRODUCTION bundle (`craco build`, completely unmodified) with
// three env vars overridden IN THIS PROCESS'S OWN ENVIRONMENT ONLY -- never
// written to frontend/.env -- then serves it statically. See
// scripts/run_test_server.py for the matching backend-side reasoning.
//
//   REACT_APP_BACKEND_URL     -> the throwaway test backend, not :8000.
//   REACT_APP_TEST_AUTH_TOKEN -> must match the backend's TEST_AUTH_TOKEN.
//   PORT                      -> only used by `serve` below; a dedicated
//                                test port so this never collides with a
//                                real dev server on :3000.
//
// DELIBERATELY builds + serves a PRODUCTION bundle (`craco build`), NOT
// `craco start` (the dev server) -- found empirically, not assumed: `craco
// start` unconditionally wraps the app with @emergentbase/visual-edits
// (craco.config.js's `isDevServer` gate, true whenever NODE_ENV !==
// "production", which `craco start` always sets internally). That tool
// instruments every element for its own click-to-edit UI and was observed
// to swallow/interfere with a real button's onClick (the Section 5 audio
// player's single-play lock never engaged when driven by Playwright against
// the dev server, despite the component's own logic being correct --
// confirmed by testing the identical component against a production build,
// where it worked immediately). A production build never loads
// visual-edits at all (isDevServer is false), which also makes this a MORE
// representative test of what a real candidate's browser actually runs.
const { spawnSync } = require("child_process");
const http = require("http");
const fs = require("fs");
const path = require("path");

const TEST_TOKEN = process.env.TEST_AUTH_TOKEN;
const BACKEND_PORT = process.env.TEST_BACKEND_PORT || "8899";
const FRONTEND_PORT = process.env.TEST_FRONTEND_PORT || "3899";
const ROOT = path.resolve(__dirname, "..");

if (!TEST_TOKEN) {
  console.error("start-test-frontend.js: TEST_AUTH_TOKEN env var is required (must match the backend's).");
  process.exit(1);
}

const buildEnv = {
  ...process.env,
  REACT_APP_BACKEND_URL: `http://localhost:${BACKEND_PORT}`,
  REACT_APP_TEST_AUTH_TOKEN: TEST_TOKEN,
  CI: "false", // don't treat this project's pre-existing unrelated eslint warnings as build-breaking errors
};

const yarnCmd = process.platform === "win32" ? "yarn.cmd" : "yarn";

console.log("[start-test-frontend] building production bundle with test env vars baked in...");
const build = spawnSync(yarnCmd, ["build"], { cwd: ROOT, env: buildEnv, stdio: "inherit", shell: true });
if (build.status !== 0) {
  console.error("[start-test-frontend] build failed");
  process.exit(build.status ?? 1);
}

// A minimal, dependency-free static file server with SPA fallback (serve
// index.html for any GET that doesn't match a real file under build/) --
// NOT the `serve` npm package: this repo's own top-level `resolutions`
// block (package.json) forcibly pins path-to-regexp@0.1.13 repo-wide for
// unrelated reasons, which broke `serve`'s bundled serve-handler at runtime
// (`pathToRegExp.compile is not a function` -- that API only exists on
// path-to-regexp v6+). Writing ~20 lines here avoids fighting that
// resolution rather than trying to override it for one throwaway test
// server.
const BUILD_DIR = path.join(ROOT, "build");
const MIME = {
  ".html": "text/html", ".js": "application/javascript", ".css": "text/css",
  ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg",
  ".svg": "image/svg+xml", ".ico": "image/x-icon", ".woff": "font/woff",
  ".woff2": "font/woff2", ".wav": "audio/wav", ".map": "application/json",
};

console.log(`[start-test-frontend] serving build/ on port ${FRONTEND_PORT}...`);
const server = http.createServer((req, res) => {
  let urlPath = decodeURIComponent(req.url.split("?")[0]);
  let filePath = path.join(BUILD_DIR, urlPath);
  if (!filePath.startsWith(BUILD_DIR)) { res.writeHead(400); res.end(); return; } // path traversal guard
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(BUILD_DIR, "index.html"); // SPA fallback for client-side routes
  }
  const ext = path.extname(filePath);
  fs.readFile(filePath, (err, data) => {
    if (err) { res.writeHead(404); res.end("Not found"); return; }
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    res.end(data);
  });
});
server.listen(Number(FRONTEND_PORT), () => {
  console.log(`[start-test-frontend] listening on http://localhost:${FRONTEND_PORT}`);
});
