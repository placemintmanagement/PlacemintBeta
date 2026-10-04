import React, { useState } from "react";
import { ShieldCheck, MessageSquareText, FileCheck2, Code2 } from "lucide-react";
import useRevealOnView from "../hooks/useRevealOnView";

/**
 * PhaseStrip -- the four phases as a vertical step list in one white card,
 * used by the "4 phases. One story." section on Landing.jsx.
 *
 * The lime highlight starts on Cross-Phase Review and can be moved to any
 * phase: hover, keyboard focus or a click selects that row, and it stays
 * there until another row is picked. Every row keeps the same padding and
 * margin whether highlighted or not, so the connector line stays aligned.
 */
export const PHASES = [
  { key: "resume", icon: FileCheck2, title: "Resume", desc: "AI check against the exact company and role you picked.", color: "#0F6F7A" },
  { key: "oa", icon: Code2, title: "Online Assessment", desc: "Real structure: sectional cutoffs, real timing, real gating.", color: "#0B2A30" },
  { key: "interview", icon: MessageSquareText, title: "Interview", desc: "Adaptive, follows up on vague answers like a real interviewer.", color: "#2A9AA3" },
  { key: "review", icon: ShieldCheck, title: "Cross-Phase Review", desc: "One narrative tying resume, OA and interview together.", color: "#0F6F7A" },
];

const DEFAULT_KEY = "review";
const STEP_DELAY_MS = 120;

export default function PhaseStrip() {
  // Scroll-driven in both directions -- see useRevealOnView.
  const [rootRef, entered] = useRevealOnView({ threshold: 0.3, fallbackMs: 500 });
  const [activeKey, setActiveKey] = useState(DEFAULT_KEY);

  return (
    <div
      ref={rootRef}
      className="pm-flow-card mt-7 lg:mt-[52px] bg-white p-4 lg:p-6"
      style={{
        borderRadius: 24,
        border: "1px solid rgba(7,59,67,0.08)",
        boxShadow: "var(--pm-card-shadow)",
      }}
    >
      <ol className="pm-flow-list list-none m-0 p-0">
        {PHASES.map((p, i) => {
          const active = activeKey === p.key;
          return (
            <li key={p.key} data-testid={`phase-strip-${p.key}`}>
              <button
                type="button"
                aria-pressed={active}
                onMouseEnter={() => setActiveKey(p.key)}
                onFocus={() => setActiveKey(p.key)}
                onClick={() => setActiveKey(p.key)}
                className="relative w-full flex items-start gap-4 text-left transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pm-teal-night)] focus-visible:ring-offset-2"
                style={{
                  padding: "14px 16px",
                  margin: "0 -8px",
                  width: "calc(100% + 16px)",
                  borderRadius: 18,
                  background: active ? "#C6F24E" : "transparent",
                  opacity: entered ? 1 : 0,
                  transform: entered ? "translateY(0)" : "translateY(10px)",
                  transitionProperty: "opacity, transform, background-color",
                  transitionDuration: "400ms, 400ms, 200ms",
                  transitionDelay: entered ? `${i * STEP_DELAY_MS}ms, ${i * STEP_DELAY_MS}ms, 0ms` : "0ms, 0ms, 0ms",
                }}
              >
                <div
                  className="relative flex-none grid place-items-center w-10 h-10 lg:w-11 lg:h-11"
                  style={{ borderRadius: 14, background: active ? "rgba(11,42,48,0.10)" : p.color + "14" }}
                >
                  <p.icon size={20} style={{ color: active ? "#0B2A30" : p.color }} aria-hidden="true" />
                  <span
                    className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full grid place-items-center font-display font-semibold"
                    style={{ fontSize: 11, background: active ? "#0B2A30" : "var(--pm-teal-deep)", color: "#FFFFFF" }}
                  >
                    {i + 1}
                  </span>
                </div>
                <div className="min-w-0 pt-0.5">
                  <div className="font-display font-semibold" style={{ fontSize: 18, lineHeight: 1.3, color: "#0B2A30" }}>{p.title}</div>
                  <div className="mt-1" style={{ fontSize: 15, lineHeight: 1.5, color: active ? "#0B2A30" : "rgba(11,42,48,0.75)" }}>{p.desc}</div>
                </div>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
