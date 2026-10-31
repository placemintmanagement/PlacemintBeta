// Canary rework frontend follow-up (2026-10): a 503 grading_infra_error
// from POST /oa/:id/section (coding sections specifically -- see
// server.py's _grade_coding_section) must show a clear, specific message
// and must NEVER clear whatever the candidate had typed into the code
// editor. The backend guarantees the attempt's own state is untouched by
// this 503 (see backend/tests/test_grading_infra_resubmission.py); this
// test covers the matching frontend contract.
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import OARunner from "./OARunner";
import api from "../api";
import { toast } from "sonner";
import { TID } from "../testIds";

jest.mock("../api", () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn() },
}));

jest.mock("sonner", () => ({
  toast: { error: jest.fn(), success: jest.fn() },
}));

// Monaco needs real browser APIs (ResizeObserver, workers, ...) jsdom
// doesn't provide. OARunner already mirrors the editor's value into a
// plain, hidden <textarea data-testid={TID.oaCodeArea}> specifically so
// tests can drive code content without touching Monaco at all -- stub
// the Editor component out entirely rather than fighting jsdom for it.
jest.mock("@monaco-editor/react", () => ({
  __esModule: true,
  default: () => null,
}));

const ATTEMPT = {
  attempt_id: "att1",
  company_name: "TCS",
  status: "in_progress",
  generation_status: "ready",
  current_section_index: 0,
  sections: [{
    key: "coding",
    type: "coding",
    name: "Coding",
    minutes: 60,
    optional: false,
    questions: [{
      id: "p1",
      title: "Two Sum",
      difficulty: "Easy",
      statement: "Find two numbers that add up to target.",
      visible_tests: [{ input: "1", expected_output: "1" }],
    }],
  }],
};

function renderRunner() {
  return render(
    <MemoryRouter initialEntries={["/oa/att1"]}>
      <Routes>
        <Route path="/oa/:attemptId" element={<OARunner />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  api.get.mockResolvedValue({ data: ATTEMPT });
});

test("a 503 grading_infra_error shows a clear message and keeps the typed code", async () => {
  const typedCode = "print('this took me 40 minutes, do not lose it')";
  api.post.mockRejectedValueOnce({
    response: {
      status: 503,
      data: {
        detail: {
          code: "grading_infra_error",
          // Deliberately different from the frontend's own message, to
          // prove the frontend shows ITS OWN clear wording for this
          // code rather than just forwarding whatever the backend sent.
          message: "backend's own wording -- should NOT be what's shown",
        },
      },
    },
  });

  const user = userEvent.setup();
  renderRunner();

  const codeArea = await screen.findByTestId(TID.oaCodeArea);
  await user.clear(codeArea);
  await user.type(codeArea, typedCode);
  expect(codeArea.value).toBe(typedCode);

  await user.click(screen.getByTestId(TID.oaFinishSection));

  await waitFor(() =>
    expect(toast.error).toHaveBeenCalledWith(
      "We couldn't grade your code just now. Nothing was lost. Please submit again."
    )
  );
  // The editor's content is completely untouched by the error path.
  expect(codeArea.value).toBe(typedCode);
});
