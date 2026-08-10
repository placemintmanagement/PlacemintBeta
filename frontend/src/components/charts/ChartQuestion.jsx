import React from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
  PieChart, Pie, Legend,
} from "recharts";
import { TID } from "../../testIds";

// Categorical palette derived from the pm design tokens (mint/coral pair +
// their darker variants + the neutral text-2 slate) rather than generic
// chart-library defaults, so DI charts read as part of the same product.
const CHART_PALETTE = ["#0FAE73", "#FF6F4D", "#0C8B5C", "#4B5563", "#E8A33D", "#B23E23"];
const AXIS_TICK = { fontFamily: "'JetBrains Mono', ui-monospace, monospace", fontSize: 11, fill: "#4B5563" };

function ChartTooltip({ active, payload, unit }) {
  if (!active || !payload?.length) return null;
  const { name, value, payload: row } = payload[0];
  return (
    <div className="pm-card px-3 py-2 shadow-lg">
      <div className="text-[11px] text-pm-text2">{row?.label ?? name}</div>
      <div className="font-mono text-sm font-semibold text-pm-text">
        {value}{unit ? ` ${unit}` : ""}
      </div>
    </div>
  );
}

function BarOrHistogram({ chart, histogram }) {
  const data = chart.labels.map((label, i) => ({ label, value: chart.values[i] }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }} barCategoryGap={histogram ? 0 : "24%"}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(10,10,10,0.06)" vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} axisLine={{ stroke: "rgba(10,10,10,0.10)" }} tickLine={false} />
        <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={40} />
        <Tooltip content={<ChartTooltip unit={chart.unit} />} cursor={{ fill: "rgba(15,174,115,0.06)" }} />
        <Bar dataKey="value" radius={histogram ? [0, 0, 0, 0] : [6, 6, 0, 0]} maxBarSize={histogram ? undefined : 64}>
          {data.map((_, i) => (
            <Cell key={i} fill={histogram ? "#0FAE73" : CHART_PALETTE[i % CHART_PALETTE.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function PieChartView({ chart }) {
  const data = chart.labels.map((label, i) => ({ name: label, label, value: chart.values[i] }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={56} outerRadius={96} paddingAngle={2} strokeWidth={0}>
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_PALETTE[i % CHART_PALETTE.length]} stroke="#fff" strokeWidth={2} />
          ))}
        </Pie>
        <Tooltip content={<ChartTooltip unit={chart.unit} />} />
        <Legend
          layout="vertical" verticalAlign="middle" align="right"
          formatter={(value) => <span className="text-xs font-sans text-pm-text2">{value}</span>}
          iconType="circle" iconSize={8}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

// Pure chart renderer -- takes just the `chart` payload described in the DI
// question schema. Reusable anywhere a chart needs to render standalone
// (e.g. the review page), independent of question/option chrome.
export function DataChart({ chart }) {
  if (!chart) return null;
  return (
    <div>
      {chart.title && <div className="font-display text-sm font-semibold text-pm-text mb-3">{chart.title}</div>}
      {chart.type === "pie" ? <PieChartView chart={chart} />
        : chart.type === "histogram" ? <BarOrHistogram chart={chart} histogram />
        : <BarOrHistogram chart={chart} />}
      {chart.unit && <div className="text-[11px] font-mono text-pm-text-muted mt-1">values in {chart.unit}</div>}
    </div>
  );
}

// Full DI question: chart + prompt + options, matching MCQSection's existing
// .pm-card / A-B-C-D button visual pattern so it drops into the same section
// flow without looking like a different product.
export default function ChartQuestion({ question, index, total, selected, onSelect }) {
  const q = question;
  return (
    <div className="pm-card p-6">
      <div className="text-xs font-mono uppercase text-pm-text2 mb-2">
        Q{index + 1} of {total} · Data Interpretation
      </div>
      <div className="mb-5 pb-5 border-b border-pm-border">
        <DataChart chart={q.chart} />
      </div>
      <div className="font-display text-lg font-semibold mb-4">{q.prompt}</div>
      <div className="grid grid-cols-1 gap-2">
        {(q.options || []).map((opt, ix) => {
          const isSelected = selected === ix;
          return (
            <button
              key={ix}
              data-testid={TID.oaQuestionOption(q.id, ix)}
              onClick={() => onSelect(q.id, ix)}
              className={`text-left border rounded-lg p-3 flex items-start gap-3 transition ${
                isSelected ? "border-pm-primary bg-pm-primary/5" : "border-pm-border hover:bg-[rgba(0,0,0,0.02)]"
              }`}
            >
              <div className={`w-6 h-6 rounded-full grid place-items-center font-mono font-bold text-xs ${
                isSelected ? "bg-pm-primary text-white" : "bg-pm-muted"
              }`}>
                {String.fromCharCode(65 + ix)}
              </div>
              <div className="flex-1 text-sm">{opt}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
