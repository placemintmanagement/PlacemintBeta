// DSA-hints Stage 2 frontend component test: the "Ask for a hint" button is
// shown only when the server's view carries hints.available (i.e.
// HINTS_ENABLED is on AND the candidate is on a DSA solving question with
// hints remaining), posts the fixed text "Can I get a hint?" through the
// SAME /answer endpoint as a normal submission (no new route), and never
// clears the candidate's own in-progress typed answer.
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
  mode: "spark",
  status: "in_progress",
  stage: "dsa",
  stage_label: "DSA",
  stages: [{ stage: "dsa", label: "DSA" }],
  deadline_epoch: Date.now() / 1000 + 3600,
  server_now_epoch: Date.now() / 1000,
  turns: [],
  current_question: { id: "spark-dsa", stage: "dsa", prompt: "Find a repeated value in the array." },
  closing_message: null,
};

function renderSpark(initial) {
  return render(
    <MemoryRouter>
      <SparkInterview interviewId="intv1" initial={initial} />
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  api.get.mockResolvedValue({ data: BASE_VIEW });
  api.post.mockResolvedValue({ data: BASE_VIEW });
});

test("no hints field (flag off) -- no hint button, no hints-used line", () => {
  renderSpark(BASE_VIEW);
  expect(screen.queryByTestId("spark-ask-hint")).toBeNull();
  expect(screen.queryByTestId("spark-hints-used")).toBeNull();
});

test("hints available -- button shown, shows the used/limit count", () => {
  renderSpark({ ...BASE_VIEW, hints: { used: 0, limit: 3, available: true } });
  expect(screen.getByTestId("spark-ask-hint")).toBeInTheDocument();
  expect(screen.getByTestId("spark-hints-used")).toHaveTextContent("Hints used: 0/3");
});

test("hints used up -- button hidden, count still shown", () => {
  renderSpark({ ...BASE_VIEW, hints: { used: 3, limit: 3, available: false } });
  expect(screen.queryByTestId("spark-ask-hint")).toBeNull();
  expect(screen.getByTestId("spark-hints-used")).toHaveTextContent("Hints used: 3/3");
});

test("clicking the hint button posts the fixed hint phrase, never clears the draft, and NEVER overwrites the problem statement", async () => {
  api.post.mockResolvedValueOnce({
    data: {
      ...BASE_VIEW,
      hints: {
        used: 1, limit: 3, available: true,
        shown: [{ level: 1, lead_in: "Sure, think about this:", text: "What's the fastest way to check if you've seen a value before?" }],
      },
      // current_question is UNCHANGED -- a hint is never shown by replacing the statement.
      current_question: { id: "spark-dsa", stage: "dsa", prompt: "Find a repeated value in the array." },
    },
  });

  const user = userEvent.setup();
  renderSpark({ ...BASE_VIEW, hints: { used: 0, limit: 3, available: true, shown: [] } });
  const textarea = screen.getByTestId("spark-answer-input");
  await user.type(textarea, "my draft answer in progress");

  await user.click(screen.getByTestId("spark-ask-hint"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    "/interview/intv1/answer", { question_id: "spark-dsa", answer: "Can I get a hint?" }
  ));
  expect(textarea.value).toBe("my draft answer in progress"); // never cleared by a hint request
  expect(toast.error).not.toHaveBeenCalled();
  await waitFor(() => expect(screen.getByTestId("spark-hints-used")).toHaveTextContent("Hints used: 1/3"));
  // the statement AND the editor are both still visible, together with the new hint
  expect(screen.getByTestId("spark-problem-statement")).toHaveTextContent("Find a repeated value in the array.");
  expect(screen.getByTestId("spark-answer-input")).toBeInTheDocument();
  const shown = screen.getAllByTestId("spark-hint-shown");
  expect(shown).toHaveLength(1);
  expect(shown[0]).toHaveTextContent("Sure, think about this:");
  expect(shown[0]).toHaveTextContent("What's the fastest way to check if you've seen a value before?");
});

test("renders the problem statement together with multiple hints already shown (e.g. after a refresh)", () => {
  renderSpark({
    ...BASE_VIEW,
    hints: {
      used: 2, limit: 3, available: true,
      shown: [
        { level: 1, lead_in: "Sure, think about this:", text: "L1 text here." },
        { level: 2, lead_in: "Here's something to consider:", text: "L2 text here." },
      ],
    },
  });
  expect(screen.getByTestId("spark-problem-statement")).toHaveTextContent("Find a repeated value in the array.");
  const shown = screen.getAllByTestId("spark-hint-shown");
  expect(shown).toHaveLength(2);
  expect(shown[0]).toHaveTextContent("L1 text here.");
  expect(shown[1]).toHaveTextContent("L2 text here.");
  // both the statement and the answer editor remain visible alongside the hints
  expect(screen.getByTestId("spark-answer-input")).toBeInTheDocument();
});

test("an answer-request/confirmation notice is shown as a one-off toast, never replaces the statement", async () => {
  api.post.mockResolvedValueOnce({
    data: {
      ...BASE_VIEW,
      hints: { used: 0, limit: 3, available: true, shown: [] },
      notice: { kind: "answer_request", text: "I can't give you the answer, but I can nudge you. Want a hint?" },
    },
  });

  const user = userEvent.setup();
  renderSpark({ ...BASE_VIEW, hints: { used: 0, limit: 3, available: true, shown: [] } });
  await user.click(screen.getByTestId("spark-ask-hint"));
  // (any submission works the same way; the hint button is just convenient here)

  await waitFor(() => expect(toast.message).toHaveBeenCalledWith(
    "I can't give you the answer, but I can nudge you. Want a hint?"
  ));
  expect(screen.getByTestId("spark-problem-statement")).toHaveTextContent("Find a repeated value in the array.");
});

test("a 409 turn_in_progress on a hint request refetches silently, same as a normal submit", async () => {
  api.post.mockRejectedValueOnce({
    response: { data: { detail: { code: "turn_in_progress", message: "Refreshing the interview" } } },
  });
  api.get.mockResolvedValueOnce({ data: { ...BASE_VIEW, hints: { used: 0, limit: 3, available: true, shown: [] } } });

  const user = userEvent.setup();
  renderSpark({ ...BASE_VIEW, hints: { used: 0, limit: 3, available: true, shown: [] } });
  await user.click(screen.getByTestId("spark-ask-hint"));

  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/interview/intv1"));
  expect(toast.error).not.toHaveBeenCalled();
  expect(toast.message).toHaveBeenCalled();
});
