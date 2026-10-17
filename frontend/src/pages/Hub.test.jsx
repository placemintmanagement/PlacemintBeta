// Company hub tests (2026-10 rollout): OA card (none/in-progress/done),
// interview card (unavailable/designated/chooser/in-progress), every
// /interview/start error code, and the past-interviews list. Mocked API,
// no network. api.js's shared interceptor (which stringifies object-
// shaped `detail`) is not exercised here -- these tests mock axios
// directly and hand back the SAME {code, message, ...} shape
// parseErrorDetail (src/lib/apiError.js) recovers from that interceptor's
// stringified text in real production, so the component code path under
// test is identical either way.
import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import Hub from "./Hub";
import api from "../api";
import { toast } from "sonner";

jest.mock("../api", () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn() },
}));

jest.mock("sonner", () => ({
  toast: { error: jest.fn(), success: jest.fn() },
}));

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

const CAPGEMINI = { id: "capgemini", name: "Capgemini", time_minutes: 181, sections: [1, 2, 3] };
const TCS = { id: "tcs-nqt", name: "TCS NQT", time_minutes: 190, sections: [1, 2, 3, 4, 5] };

function mockLoad({ company = CAPGEMINI, interviews = [], companies = [] } = {}) {
  api.get.mockImplementation((url) => {
    if (url.startsWith("/companies/")) return Promise.resolve({ data: company });
    if (url === "/interview/list") return Promise.resolve({ data: { interviews, companies } });
    return Promise.reject(new Error(`unexpected GET ${url}`));
  });
}

function renderHub(companyId = "capgemini") {
  return render(
    <MemoryRouter initialEntries={[`/company/${companyId}/hub`]}>
      <Routes>
        <Route path="/company/:companyId/hub" element={<Hub />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
});

// ---- OA card ----------------------------------------------------------

test("OA: no attempt yet shows Start the OA, no result panel", async () => {
  mockLoad({ companies: [{ company_id: "capgemini", interview_available: true, designated_tier: null }] });
  renderHub();
  await waitFor(() => expect(screen.getByTestId("hub-oa-start-btn")).toBeInTheDocument());
  expect(screen.getByTestId("hub-oa-start-btn")).toHaveTextContent("Start the OA");
  expect(screen.queryByTestId("hub-oa-result")).not.toBeInTheDocument();
});

test("OA: clicking Start, discovering it's already in progress, shows Continue and navigates", async () => {
  mockLoad({ companies: [{ company_id: "capgemini", interview_available: true, designated_tier: null }] });
  api.post.mockRejectedValueOnce({
    response: { data: { detail: { code: "oa_already_in_progress", message: "already running", attempt_id: "att-existing" } } },
  });
  const user = userEvent.setup();
  renderHub();
  await waitFor(() => expect(screen.getByTestId("hub-oa-start-btn")).toBeInTheDocument());
  await user.click(screen.getByTestId("hub-oa-start-btn"));

  const continueBtn = await screen.findByTestId("hub-oa-continue-btn");
  expect(continueBtn).toHaveTextContent("Continue your OA");
  await user.click(continueBtn);
  expect(mockNavigate).toHaveBeenCalledWith("/oa/att-existing");
});

test("OA: a successful start navigates straight to the new attempt", async () => {
  mockLoad({ companies: [] });
  api.post.mockResolvedValueOnce({ data: { attempt_id: "att-new" } });
  const user = userEvent.setup();
  renderHub();
  await waitFor(() => expect(screen.getByTestId("hub-oa-start-btn")).toBeInTheDocument());
  await user.click(screen.getByTestId("hub-oa-start-btn"));
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/oa/att-new"));
});

test("OA: a cleared Capgemini tier shows the result panel and a Retake button", async () => {
  mockLoad({ companies: [{ company_id: "capgemini", interview_available: true, designated_tier: "dave" }] });
  renderHub();
  const panel = await screen.findByTestId("hub-oa-result");
  expect(within(panel).getByText("Dave tier")).toBeInTheDocument();
  expect(screen.getByTestId("hub-oa-start-btn")).toHaveTextContent("Retake the OA");
});

test("OA: a TCS result uses the existing 'does not publish cutoffs' wording", async () => {
  mockLoad({
    company: TCS,
    companies: [{ company_id: "tcs-nqt", interview_available: false, designated_tier: "digital" }],
  });
  renderHub("tcs-nqt");
  const panel = await screen.findByTestId("hub-oa-result");
  expect(within(panel).getByText(/TCS does not publish cutoffs/)).toBeInTheDocument();
  expect(within(panel).getByText("Digital")).toBeInTheDocument();
});

// ---- Interview card -----------------------------------------------------

test("Interview: unavailable company shows a disabled coming-soon card", async () => {
  mockLoad({
    company: TCS,
    companies: [{ company_id: "tcs-nqt", interview_available: false, designated_tier: "ninja" }],
  });
  renderHub("tcs-nqt");
  const card = await screen.findByTestId("hub-interview-unavailable");
  expect(card).toHaveTextContent("aren't available yet");
  expect(screen.queryByTestId("hub-interview-designated-btn")).not.toBeInTheDocument();
});

test("Interview: a designated tier shows the primary CTA naming the tier", async () => {
  mockLoad({ companies: [{ company_id: "capgemini", interview_available: true, designated_tier: "spark" }] });
  renderHub();
  const btn = await screen.findByTestId("hub-interview-designated-btn");
  expect(btn).toHaveTextContent("Start Spark interview (based on your OA)");
});

test("Interview: designated tier CTA posts use_designated=true", async () => {
  mockLoad({ companies: [{ company_id: "capgemini", interview_available: true, designated_tier: "spark" }] });
  api.post.mockResolvedValueOnce({ data: { interview_id: "intv-1" } });
  const user = userEvent.setup();
  renderHub();
  await user.click(await screen.findByTestId("hub-interview-designated-btn"));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/interview/start", { company_id: "capgemini", use_designated: true }));
  expect(mockNavigate).toHaveBeenCalledWith("/interview/intv-1");
});

test("Interview: 'Choose a different tier' reveals the chooser even with a designated tier", async () => {
  mockLoad({ companies: [{ company_id: "capgemini", interview_available: true, designated_tier: "spark" }] });
  const user = userEvent.setup();
  renderHub();
  await user.click(await screen.findByTestId("hub-interview-choose-different"));
  expect(screen.getByTestId("hub-interview-chooser")).toBeInTheDocument();
  expect(screen.getByTestId("hub-interview-tier-option-commit")).toBeInTheDocument();
});

test("Interview: no designated tier shows the chooser directly, and starting posts the chosen tier", async () => {
  mockLoad({ companies: [{ company_id: "capgemini", interview_available: true, designated_tier: null }] });
  api.post.mockResolvedValueOnce({ data: { interview_id: "intv-2" } });
  const user = userEvent.setup();
  renderHub();
  expect(await screen.findByTestId("hub-interview-chooser")).toBeInTheDocument();
  expect(screen.getByTestId("hub-interview-start-chosen-btn")).toBeDisabled();

  await user.click(screen.getByTestId("hub-interview-tier-option-commit"));
  expect(screen.getByTestId("hub-interview-start-chosen-btn")).toBeEnabled();
  await user.click(screen.getByTestId("hub-interview-start-chosen-btn"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/interview/start", { company_id: "capgemini", tier: "commit" }));
  expect(mockNavigate).toHaveBeenCalledWith("/interview/intv-2");
});

test("Interview: a non-tier-routed company with no catalog explains the limitation instead of an empty chooser", async () => {
  mockLoad({
    company: { id: "infosys", name: "Infosys", time_minutes: 90, sections: [] },
    companies: [{ company_id: "infosys", interview_available: true, designated_tier: null }],
  });
  renderHub("infosys");
  expect(await screen.findByTestId("hub-interview-no-chooser-available")).toBeInTheDocument();
});

test("Interview: an in-progress interview shows Continue and navigates on click", async () => {
  mockLoad({
    companies: [{ company_id: "capgemini", interview_available: true, designated_tier: null }],
    interviews: [{ interview_id: "intv-live", company_id: "capgemini", tier: "dave", tier_source: "chosen", status: "in_progress", created_at: "2026-01-01T00:00:00" }],
  });
  const user = userEvent.setup();
  renderHub();
  const btn = await screen.findByTestId("hub-interview-continue-btn");
  await user.click(btn);
  expect(mockNavigate).toHaveBeenCalledWith("/interview/intv-live");
});

// ---- /interview/start error codes --------------------------------------

test.each([
  ["resume_required", "resume on file first"],
  ["no_designated_tier", "No cleared OA tier yet"],
  ["unknown_tier", "isn't available for this company"],
  ["interview_not_available", "aren't available yet"],
  ["invalid_start_body", "Something went wrong"],
  ["some_future_code_we_do_not_know", "Something went wrong"],
])("Interview: the %s error shows a clear message, no crash", async (code, expectedText) => {
  mockLoad({ companies: [{ company_id: "capgemini", interview_available: true, designated_tier: "spark" }] });
  api.post.mockRejectedValueOnce({ response: { data: { detail: { code, message: "server message" } } } });
  const user = userEvent.setup();
  renderHub();
  await user.click(await screen.findByTestId("hub-interview-designated-btn"));
  await waitFor(() => expect(screen.getByTestId("hub-interview-error")).toBeInTheDocument());
  expect(screen.getByTestId("hub-interview-error").closest("[role]")).toHaveTextContent(new RegExp(expectedText));
});

test("Interview: interview_already_in_progress navigates straight there instead of showing an error", async () => {
  mockLoad({ companies: [{ company_id: "capgemini", interview_available: true, designated_tier: "spark" }] });
  api.post.mockRejectedValueOnce({
    response: { data: { detail: { code: "interview_already_in_progress", message: "already running", interview_id: "intv-race" } } },
  });
  const user = userEvent.setup();
  renderHub();
  await user.click(await screen.findByTestId("hub-interview-designated-btn"));
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/interview/intv-race"));
  expect(screen.queryByTestId("hub-interview-error")).not.toBeInTheDocument();
});

// ---- Past interviews -----------------------------------------------------

test("Past interviews: lists only this company's interviews, with tier source and a report link", async () => {
  mockLoad({
    companies: [{ company_id: "capgemini", interview_available: true, designated_tier: null }],
    interviews: [
      { interview_id: "intv-a", company_id: "capgemini", tier: "spark", tier_source: "chosen", status: "completed", created_at: "2026-01-01T00:00:00" },
      { interview_id: "intv-b", company_id: "capgemini", tier: "dave", tier_source: "oa_designated", status: "completed", created_at: "2026-01-02T00:00:00" },
      { interview_id: "intv-c", company_id: "other-company", tier: "x", tier_source: "chosen", status: "completed", created_at: "2026-01-03T00:00:00" },
    ],
  });
  renderHub();
  const list = await screen.findByTestId("hub-past-interviews-list");
  expect(within(list).getByTestId("hub-past-interview-row-intv-a")).toBeInTheDocument();
  expect(within(list).getByTestId("hub-past-interview-row-intv-b")).toBeInTheDocument();
  expect(within(list).queryByTestId("hub-past-interview-row-intv-c")).not.toBeInTheDocument();
  expect(within(list).getByText("chosen by you")).toBeInTheDocument();
  expect(within(list).getByText("based on OA")).toBeInTheDocument();
  const reportLinks = within(list).getAllByText("View report");
  expect(reportLinks[0]).toHaveAttribute("href", "/interview/intv-a/report");
});

test("Past interviews: empty state when there are none for this company", async () => {
  mockLoad({ companies: [{ company_id: "capgemini", interview_available: true, designated_tier: null }] });
  renderHub();
  expect(await screen.findByTestId("hub-past-interviews-empty")).toBeInTheDocument();
});

// ---- Load failure --------------------------------------------------------

test("A load failure shows a clear message instead of crashing", async () => {
  api.get.mockRejectedValue(new Error("network down"));
  renderHub();
  await waitFor(() => expect(screen.getByText(/Couldn't load this hub/)).toBeInTheDocument());
});
