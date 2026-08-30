import axios from "axios";
import { getAuth0AccessToken } from "./auth/auth0TokenBridge";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  timeout: 300000, // 5 minutes — AI question generation for a full OA can legitimately take this long
});

// Attach bearer if we saved one at signup/login. Cookie is primary.
api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("pm_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

// Auth0 bearer token (frontend-only integration, 2026-08 -- see
// src/auth/Auth0ProviderWithNavigate.jsx). Only attaches if the app-auth
// interceptor above didn't already set one, so this never overrides the
// existing, currently-working auth mechanism real users depend on.
// server.py's require_user is Auth0-only now (see backend/server.py's own
// require_user docstring) -- this IS the mechanism actual requests
// authenticate through today.
api.interceptors.request.use(async (cfg) => {
  if (!cfg.headers.Authorization) {
    const auth0Token = await getAuth0AccessToken();
    if (auth0Token) cfg.headers.Authorization = `Bearer ${auth0Token}`;
  }
  return cfg;
});

// TEST-ONLY (2026-08, Playwright E2E click-through testing). Mirrors
// server.py's own _resolve_auth0_sub bypass exactly: REACT_APP_TEST_AUTH_TOKEN
// is a CRA build-time env var, inlined by webpack at build time -- a real
// production build (built without this var set in the build environment,
// which it never is; it's not part of any committed .env) has this
// literal as `undefined` everywhere, so this whole branch is provably dead
// in any real deployment, not just "off by default". Only ever set by the
// E2E test launcher's own shell environment when starting a throwaway
// `craco start` dev server for testing -- never written to any .env file.
// Runs LAST (lowest priority): only fires if NEITHER the legacy pm_token
// NOR a real Auth0 token was already attached above, so it can never
// override a real user's actual credentials even if this var were somehow
// present in a real user's browser.
api.interceptors.request.use((cfg) => {
  const testToken = process.env.REACT_APP_TEST_AUTH_TOKEN;
  if (testToken && !cfg.headers.Authorization) {
    cfg.headers.Authorization = `Bearer ${testToken}`;
  }
  return cfg;
});

// Normalize FastAPI/Pydantic validation errors so callers can always render
// `err.response.data.detail` as a plain string. Without this, a 422 returns
// `detail: [{type, loc, msg, input, url}, ...]` which crashes React when
// passed to <div>{detail}</div> or toast.error(detail).
api.interceptors.response.use(
  (r) => r,
  (err) => {
    const detail = err?.response?.data?.detail;
    if (Array.isArray(detail)) {
      err.response.data.detail = detail
        .map((e) => {
          if (e && typeof e === "object") {
            const field = Array.isArray(e.loc) ? e.loc.filter(x => x !== "body").join(".") : "";
            return field ? `${field}: ${e.msg || "invalid"}` : (e.msg || JSON.stringify(e));
          }
          return String(e);
        })
        .join("; ");
    } else if (detail && typeof detail === "object") {
      err.response.data.detail = detail.msg || JSON.stringify(detail);
    }
    return Promise.reject(err);
  },
);

export default api;
