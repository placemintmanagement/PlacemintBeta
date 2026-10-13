// Dev/test spend-cutting follow-up (2026-10): verifies that a 409 for
// turn_in_progress (the new atomic turn-claim guard in server.py) is
// handled exactly like the pre-existing stale_turn/stale_question/
// time_up/interview_closed codes -- a silent refetch of current state,
// no error banner, and the candidate's typed (but not yet sent) answer
// is never cleared. Before this fix, turn_in_progress fell through to
// the generic toast.error branch instead.
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import SparkInterview from "./SparkInterview";
import api from "../api";
import { toast } from "sonner";

jest.mock("../api", () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn() },
}));

jest.mock("sonner", () => ({
  toast: { error: jest.fn(), message: jest.fn(), success: jest.fn() },
}));

const BASE_VIEW = {
  interview_id: "intv1",
  mode: "commit",
  status: "in_progress",
  stage: "project1",
  stage_label: "Project 1",
  stages: [{ stage: "project1", label: "Project 1" }],
  deadline_epoch: Date.now() / 1000 + 3600,
  server_now_epoch: Date.now() / 1000,
  turns: [],
  current_question: { id: "commit-project1", stage: "project1", prompt: "Tell me about a project." },
  closing_message: null,
};

function renderSpark() {
  return render(
    <MemoryRouter>
      <SparkInterview interviewId="intv1" initial={BASE_VIEW} />
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  // Safe defaults so any call beyond the single one each test explicitly
  // sets up with mockRejectedValueOnce/mockResolvedValueOnce (e.g. the
  // idle-ping effect, or an incidental extra render) resolves harmlessly
  // instead of hitting a bare, un-configured jest.fn() -- which resolves
  // to undefined, and destructuring `{ data }` from that throws, landing
  // on the generic "Failed to submit" toast and making the assertions
  // below flaky/order-dependent.
  api.get.mockResolvedValue({ data: BASE_VIEW });
  api.post.mockResolvedValue({ data: BASE_VIEW });
});

test.each(["turn_in_progress", "stale_turn", "stale_question", "time_up", "interview_closed"])(
  "a %s 409 refetches silently: no error toast, answer text preserved",
  async (code) => {
    const typed = "A clear, specific answer about my own part and the trade-off I handled.";
    api.post.mockRejectedValueOnce({
      response: { data: { detail: { code, message: "Refreshing the interview" } } },
    });
    api.get.mockResolvedValueOnce({ data: { ...BASE_VIEW, turns: [{ stage: "project1" }] } });

    const user = userEvent.setup();
    renderSpark();
    const textarea = screen.getByTestId("spark-answer-input");
    await user.type(textarea, typed);
    await user.click(screen.getByTestId("spark-submit-answer"));

    await waitFor(() => expect(api.get).toHaveBeenCalledWith("/interview/intv1"));
    expect(toast.error).not.toHaveBeenCalled();
    expect(toast.message).toHaveBeenCalled();
    expect(textarea.value).toBe(typed); // never cleared on this path
  }
);

test("an unrelated error (not one of the race/timeout codes) still shows an error toast", async () => {
  api.post.mockRejectedValueOnce({ response: { data: { detail: "Answer is empty" } } });

  const user = userEvent.setup();
  renderSpark();
  const textarea = screen.getByTestId("spark-answer-input");
  await user.type(textarea, "short");
  await user.click(screen.getByTestId("spark-submit-answer"));

  await waitFor(() => expect(toast.error).toHaveBeenCalled());
  expect(api.get).not.toHaveBeenCalled();
});

test("a successful submit clears the answer box and does not toast", async () => {
  api.post.mockResolvedValueOnce({
    data: { ...BASE_VIEW, current_question: { id: "commit-p1f1", stage: "project1", prompt: "Next question?" } },
  });

  const user = userEvent.setup();
  renderSpark();
  const textarea = screen.getByTestId("spark-answer-input");
  await user.type(textarea, "A real answer.");
  await user.click(screen.getByTestId("spark-submit-answer"));

  await waitFor(() => expect(textarea.value).toBe(""));
  expect(toast.error).not.toHaveBeenCalled();
});
