// Recovers the structured {code, message, ...} shape server.py's
// HTTPException(status, {"code": ..., "message": ...}) convention sends
// (e.g. resume_required, no_designated_tier, unknown_tier,
// interview_not_available, invalid_start_body, oa_already_in_progress,
// interview_already_in_progress) -- even though api.js's shared response
// interceptor stringifies any object-shaped `detail` into JSON text, so
// every OTHER existing caller that treats `detail` as a plain string
// (there are many: toast.error(err.response?.data?.detail || "...")
// across the app) keeps working completely unchanged. This helper is
// local to the new company-hub code, not a change to that shared
// interceptor.
export function parseErrorDetail(err) {
  const raw = err?.response?.data?.detail;
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
    } catch {
      // Not JSON -- a plain string error message (e.g. "Company not found").
    }
    return { code: null, message: raw };
  }
  if (raw && typeof raw === "object" && !Array.isArray(raw)) return raw;
  return { code: null, message: err?.message || "Something went wrong." };
}
