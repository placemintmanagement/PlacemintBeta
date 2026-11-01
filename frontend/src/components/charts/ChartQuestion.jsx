import React from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
  PieChart, Pie, Legend,
} from "recharts";
import { TID } from "../../testIds";

// Categorical palette derived from the glass brand hexes (accent teal,
// logo pink, amber, mint/blue + two neutral fill-ins) rather than generic
// chart-library defaults, so DI charts read as part of the same product
// (glass restyle, 2026-11 -- was the old pm teal/lime pair).
const CHART_PALETTE = ["#0d9488", "#ec4899", "#f2a900", "#2dd4da", "#b45309", "#64748b"];
const AXIS_TICK = { fontFamily: "Outfit, system-ui, sans-serif", fontSize: 12, fill: "#5d5d5d" };

function ChartTooltip({ active, payload, unit }) {
  if (!active || !payload?.length) return null;
  const { name, value, payload: row } = payload[0];
  return (
    <div className="gl-card px-3 py-2 shadow-lg">
      <div className="text-[11px]" style={{ color: "var(--gl-muted)" }}>{row?.label ?? name}</div>
      <div className="font-display tabular-nums text-sm font-semibold" style={{ color: "var(--gl-text)" }}>
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
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(11,11,11,0.06)" vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} axisLine={{ stroke: "rgba(11,11,11,0.10)" }} tickLine={false} />
        <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={40} />
        <Tooltip content={<ChartTooltip unit={chart.unit} />} cursor={{ fill: "rgba(13,148,136,0.06)" }} />
        <Bar dataKey="value" radius={histogram ? [0, 0, 0, 0] : [6, 6, 0, 0]} maxBarSize={histogram ? undefined : 64}>
          {data.map((_, i) => (
            <Cell key={i} fill={histogram ? "#0d9488" : CHART_PALETTE[i % CHART_PALETTE.length]} />
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
          formatter={(value) => <span className="text-xs font-sans" style={{ color: "var(--gl-muted)" }}>{value}</span>}
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
      {chart.title && <div className="font-display text-sm font-semibold mb-3" style={{ color: "var(--gl-text)" }}>{chart.title}</div>}
      {chart.type === "pie" ? <PieChartView chart={chart} />
        : chart.type === "histogram" ? <BarOrHistogram chart={chart} histogram />
        : <BarOrHistogram chart={chart} />}
      {chart.unit && <div className="text-[11px] font-display tabular-nums mt-1" style={{ color: "var(--gl-muted)" }}>values in {chart.unit}</div>}
    </div>
  );
}

// Full DI question: chart + prompt + options, matching MCQSection's existing
// .pm-card / A-B-C-D button visual pattern so it drops into the same section
// flow without looking like a different product.
export default function ChartQuestion({ question, index, total, selected, onSelect }) {
  const q = question;
  return (
    <div className="gl-card p-6">
      <div className="text-xs pm-eyebrow mb-2" style={{ color: "var(--gl-muted)" }}>
        Q{index + 1} of {total} · Data Interpretation
      </div>
      <div className="mb-5 pb-5" style={{ borderBottom: "1px solid var(--gl-line)" }}>
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
              className={`text-left border rounded-lg p-3 flex items-start gap-3 transition ${isSelected ? "" : "hover:bg-[rgba(0,0,0,0.02)]"}`}
              style={isSelected
                ? { borderColor: "var(--gl-accent)", background: "color-mix(in srgb, var(--gl-accent) 5%, transparent)" }
                : { borderColor: "var(--gl-line)" }}
            >
              <div className="w-6 h-6 rounded-full grid place-items-center font-display tabular-nums font-bold text-xs"
                   style={isSelected ? { background: "var(--gl-accent)", color: "#fff" } : { background: "var(--gl-blue)" }}>
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
