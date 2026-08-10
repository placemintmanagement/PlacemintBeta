import React, { useState } from "react";
import Header from "../components/Header";
import ChartQuestion from "../components/charts/ChartQuestion";

// Standing dev tool (not temporary) -- unauthenticated preview route at
// /dev/chart-preview for visually confirming DI chart questions against the
// `chart` schema before they go live. Useful for checking future chart
// questions render correctly, not just the one-time initial component check.
const SAMPLE_QUESTIONS = [
  {
    id: "di-preview-bar",
    prompt: "By what percentage did the company's revenue grow from 2021 to 2023?",
    options: ["25%", "40%", "50%", "60%"],
    correct_index: 1,
    chart: {
      type: "bar",
      title: "Annual Revenue (2019–2023)",
      labels: ["2019", "2020", "2021", "2022", "2023"],
      values: [40, 35, 50, 58, 70],
      unit: "₹ lakhs",
    },
  },
  {
    id: "di-preview-pie",
    prompt: "What is the ratio of students who chose Engineering to those who chose Commerce?",
    options: ["3 : 2", "5 : 3", "2 : 1", "5 : 4"],
    correct_index: 1,
    chart: {
      type: "pie",
      title: "Stream Chosen by 600 Class XII Students",
      labels: ["Engineering", "Medical", "Commerce", "Arts", "Other"],
      values: [225, 90, 135, 105, 45],
      unit: "students",
    },
  },
  {
    id: "di-preview-histogram",
    prompt: "How many students scored less than 60 marks?",
    options: ["18", "24", "32", "40"],
    correct_index: 2,
    chart: {
      type: "histogram",
      title: "Marks Distribution — Class X Mathematics (120 students)",
      labels: ["0–20", "20–40", "40–60", "60–80", "80–100"],
      values: [4, 10, 18, 52, 36],
      unit: "students",
    },
  },
];

export default function DevChartPreview() {
  const [answers, setAnswers] = useState({});
  const setAnswer = (qid, ix) => setAnswers(a => ({ ...a, [qid]: ix }));

  return (
    <div>
      <Header />
      <div className="max-w-3xl mx-auto px-6 py-10">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-1">dev preview · not a real route</div>
        <h1 className="font-display text-2xl font-bold mb-6">DI Chart Question — component preview</h1>
        <div className="space-y-6">
          {SAMPLE_QUESTIONS.map((q, i) => (
            <ChartQuestion
              key={q.id}
              question={q}
              index={i}
              total={SAMPLE_QUESTIONS.length}
              selected={answers[q.id]}
              onSelect={setAnswer}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
