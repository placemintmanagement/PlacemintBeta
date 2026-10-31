// Proves parseErrorDetail against the REAL axios instance and its REAL
// response interceptor (src/api.js), not a mocked api module. A custom
// axios adapter stands in for the network transport only -- every
// interceptor (request and response) still runs for real, exactly as in
// production. This is the thing Hub.jsx and SparkInterview.jsx actually
// depend on: that parseErrorDetail can recover {code, message, ...} from
// whatever api.js's interceptor really does to an object-shaped `detail`,
// not from a guess about what it does.
import axios from "axios";
import api from "../api";
import { parseErrorDetail } from "./apiError";

// A bare custom adapter that just resolves with {status, data, ...} does
// NOT reproduce a real error: axios's own dispatchRequest.js never checks
// response.status itself -- that check (settle(), comparing against
// validateStatus) lives INSIDE each real transport adapter (http.js/
// xhr.js/fetch.js), not in the dispatch layer. A custom adapter has to do
// that check itself to be a faithful stand-in, exactly as confirmed by
// first running this against a bare resolve-only adapter and finding the
// promise resolved instead of rejecting for a 409 (see this file's own
// commit message for the full finding).
function withJsonAdapter(status, data) {
  return async (config) => {
    const response = { data, status, statusText: "", headers: {}, config };
    if (status >= 200 && status < 300) return response;
    throw new axios.AxiosError(
      `Request failed with status code ${status}`,
      status >= 400 && status < 500 ? axios.AxiosError.ERR_BAD_REQUEST : axios.AxiosError.ERR_BAD_RESPONSE,
      config,
      null,
      response,
    );
  };
}

function withNetworkErrorAdapter() {
  return async () => {
    const err = new Error("Network Error");
    err.code = "ERR_NETWORK";
    throw err; // no .response at all -- a real transport-level failure
  };
}

describe("parseErrorDetail against the real api.js interceptor", () => {
  const originalAdapter = api.defaults.adapter;
  afterEach(() => {
    api.defaults.adapter = originalAdapter;
  });

  test("oa_already_in_progress 409: code, message and attempt_id all survive", async () => {
    const sent = { code: "oa_already_in_progress", message: "An OA attempt for this company is already in progress.", attempt_id: "abc" };
    api.defaults.adapter = withJsonAdapter(409, { detail: sent });

    let caught;
    try { await api.post("/oa/start", { company_id: "capgemini" }); } catch (err) { caught = err; }
    expect(caught).toBeDefined();

    // Report what the real interceptor actually produced, for the record.
    // eslint-disable-next-line no-console
    console.log("[interceptor output] oa_already_in_progress -> typeof detail =", typeof caught.response.data.detail, "value =", caught.response.data.detail);

    const detail = parseErrorDetail(caught);
    expect(detail.code).toBe("oa_already_in_progress");
    expect(detail.attempt_id).toBe("abc");
    expect(detail.message).toBe(sent.message);
  });

  test("interview_already_in_progress 409: code, message and interview_id all survive", async () => {
    const sent = { code: "interview_already_in_progress", message: "An interview for this company is already in progress.", interview_id: "intv-live" };
    api.defaults.adapter = withJsonAdapter(409, { detail: sent });

    let caught;
    try { await api.post("/interview/start", { company_id: "capgemini", tier: "spark" }); } catch (err) { caught = err; }

    const detail = parseErrorDetail(caught);
    expect(detail.code).toBe("interview_already_in_progress");
    expect(detail.interview_id).toBe("intv-live");
    expect(detail.message).toBe(sent.message);
  });

  test("resume_required 400: code and message survive", async () => {
    const sent = { code: "resume_required", message: "Analyze a resume for this company before starting an interview." };
    api.defaults.adapter = withJsonAdapter(400, { detail: sent });

    let caught;
    try { await api.post("/interview/start", { company_id: "capgemini", tier: "spark" }); } catch (err) { caught = err; }

    const detail = parseErrorDetail(caught);
    expect(detail.code).toBe("resume_required");
    expect(detail.message).toBe(sent.message);
  });

  test("interview_not_available 400: code and message survive", async () => {
    const sent = { code: "interview_not_available", message: "This company does not have an interview phase yet." };
    api.defaults.adapter = withJsonAdapter(400, { detail: sent });

    let caught;
    try { await api.post("/interview/start", { company_id: "tcs-nqt", use_designated: true }); } catch (err) { caught = err; }

    const detail = parseErrorDetail(caught);
    expect(detail.code).toBe("interview_not_available");
    expect(detail.message).toBe(sent.message);
  });

  test("a plain string detail (e.g. a 404) comes out unchanged, code is null", async () => {
    api.defaults.adapter = withJsonAdapter(404, { detail: "Company not found" });

    let caught;
    try { await api.get("/companies/does-not-exist"); } catch (err) { caught = err; }

    expect(typeof caught.response.data.detail).toBe("string"); // interceptor left it alone
    const detail = parseErrorDetail(caught);
    expect(detail.code).toBeNull();
    expect(detail.message).toBe("Company not found");
  });

  test("a network error with no response at all: generic fallback, no throw", async () => {
    api.defaults.adapter = withNetworkErrorAdapter();

    let caught;
    try { await api.get("/interview/list"); } catch (err) { caught = err; }
    expect(caught.response).toBeUndefined();

    const detail = parseErrorDetail(caught);
    expect(detail.code).toBeNull();
    expect(typeof detail.message).toBe("string");
    expect(detail.message.length).toBeGreaterThan(0);
  });
});
