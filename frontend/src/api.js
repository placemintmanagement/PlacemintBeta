import axios from "axios";

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
