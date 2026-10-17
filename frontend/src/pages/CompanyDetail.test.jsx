// CompanyDetail.jsx (2026-10 fix): this page used to call POST /oa/start
// directly from its own "Start OA" button, bypassing the hub entirely --
// so Interview was unreachable from here, and a candidate who clicked
// "Start OA" never saw the independent OA/Interview choice. Both the
// primary CTA and "skip resume for this run" now navigate to the hub
// instead; starting the OA (and picking a skill cluster) lives there now.
import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import CompanyDetail from "./CompanyDetail";
import api from "../api";
import { TID } from "../testIds";

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
  useParams: () => ({ companyId: "capgemini" }),
}));

const COMPANY = {
  id: "capgemini", name: "Capgemini", tagline: "test", time_minutes: 181,
  scoring_mode: "sectional", sections: [{ key: "s1", name: "Section 1", type: "mcq", count: 5, minutes: 10, cutoff: 0.5 }],
};

beforeEach(() => {
  jest.clearAllMocks();
  api.get.mockResolvedValue({ data: COMPANY });
});

function renderPage() {
  return render(
    <MemoryRouter>
      <CompanyDetail />
    </MemoryRouter>
  );
}

test("the primary CTA navigates to the hub, never calls POST /oa/start directly", async () => {
  const user = userEvent.setup();
  renderPage();
  await screen.findByTestId(TID.startOaBtn);

  await user.click(screen.getByTestId(TID.startOaBtn));

  expect(mockNavigate).toHaveBeenCalledWith("/company/capgemini/hub");
  expect(api.post).not.toHaveBeenCalled();
});

test("'skip resume for this run' also navigates to the hub", async () => {
  const user = userEvent.setup();
  renderPage();
  await screen.findByTestId(TID.resumeSkip);

  await user.click(screen.getByTestId(TID.resumeSkip));

  expect(mockNavigate).toHaveBeenCalledWith("/company/capgemini/hub");
  expect(api.post).not.toHaveBeenCalled();
});

test("a successful resume upload also navigates to the hub", async () => {
  api.post.mockResolvedValueOnce({ data: { resume_id: "res1", analysis: { fit_score: 80 } } });
  const user = userEvent.setup();
  renderPage();
  await screen.findByTestId(TID.resumeUploadInput);

  const file = new File(["dummy"], "resume.pdf", { type: "application/pdf" });
  await user.upload(screen.getByTestId(TID.resumeUploadInput), file);
  await user.click(screen.getByTestId(TID.resumeSubmit));

  expect(mockNavigate).toHaveBeenCalledWith("/company/capgemini/hub");
});

test("no cluster picker is rendered on this page anymore -- it moved to the hub", async () => {
  renderPage();
  await screen.findByTestId(TID.startOaBtn);
  expect(screen.queryByText(/Pick your skill cluster/i)).not.toBeInTheDocument();
});
