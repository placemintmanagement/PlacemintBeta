import React, { useEffect, useState } from "react";
import { ShieldCheck, MessageSquareText, FileCheck2, Code2 } from "lucide-react";
import useRevealOnView from "../hooks/useRevealOnView";

/**
 * PhaseStrip -- the white four-column "Resume / Online Assessment /
 * Interview / Cross-Phase Review" card. Extracted from HeroV2 (2026-10,
 * where it used to overlap the hero's bottom edge) into a shared
 * component so the "4 phases. One story." section on Landing.jsx can
 * reuse the exact same white-card/icon-tile/title/description language,
 * not a redesign -- the base visuals (28-32px radius, soft icon tiles,
 * bold title, two-line description, lime highlighted card) are unchanged.
 * The hero no longer renders this at all.
 */
export const PHASES = [
  { key: "resume", icon: FileCheck2, title: "Resume", desc: "AI check against the exact company and role you picked.", color: "#0F6F7A" },
  { key: "oa", icon: Code2, title: "Online Assessment", desc: "Real structure: sectional cutoffs, real timing, real gating.", color: "#0B2A30" },
  { key: "interview", icon: MessageSquareText, title: "Interview", desc: "Adaptive, follows up on vague answers like a real interviewer.", color: "#2A9AA3" },
  { key: "review", icon: ShieldCheck, title: "Cross-Phase Review", desc: "One narrative tying resume, OA and interview together.", color: "#0F6F7A" },
];

const DEFAULT_ACTIVE = "oa";
const STEP_DELAY_MS = 150;

// Column centers for an even 4-col grid (12.5%, 37.5%, 62.5%, 87.5%), and
// the 3 gap midpoints between them (25%, 50%, 75%) for the arrow tips.
const ARROW_POSITIONS = [25, 50, 75];

export default function PhaseStrip() {
  const [activeKey, setActiveKey] = useState(DEFAULT_ACTIVE);
  const [stepKey, setStepKey] = useState(null); // drives the 1->2->3->4 intro sweep
  // threshold:0.3 + a 500ms fallback -- see useRevealOnView's own comment
  // for why a reveal animation must never depend on a single trigger path.
  const [rootRef, entered] = useRevealOnView({ threshold: 0.3, fallbackMs: 500 });

  useEffect(() => {
    if (!entered) return;
    // Step the lime highlight through each phase in turn, then settle on
    // the default (Online Assessment).
    let i = 0;
    let timer = null;
    const step = () => {
      if (i >= PHASES.length) {
        setStepKey(null);
        setActiveKey(DEFAULT_ACTIVE);
        return;
      }
      setStepKey(PHASES[i].key);
      i += 1;
      timer = setTimeout(step, STEP_DELAY_MS);
    };
    timer = setTimeout(step, STEP_DELAY_MS);
    return () => { if (timer) clearTimeout(timer); };
  }, [entered]);

  const highlightKey = stepKey ?? activeKey;

  return (
    <div
      ref={rootRef}
      className="bg-white px-4 sm:px-8 py-8"
      style={{
        borderRadius: 28,
        border: "1px solid rgba(15,111,122,0.14)",
        boxShadow: "0 16px 40px rgba(15,111,122,0.12)",
      }}
    >
      <div className="relative">
        {/* Connecting line + arrow tips, desktop only (4-across layout) */}
        <div className="hidden lg:block absolute left-0 right-0 top-[18px] h-px pointer-events-none" style={{ background: "rgba(15,111,122,0.35)" }} aria-hidden="true">
          {ARROW_POSITIONS.map((pct) => (
            <span
              key={pct}
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 text-[10px] leading-none"
              style={{ left: `${pct}%`, color: "rgba(15,111,122,0.35)" }}
            >
              ▶
            </span>
          ))}
        </div>

        <div className="relative grid grid-cols-2 lg:grid-cols-4 gap-5 sm:gap-6">
          {PHASES.map((p, i) => {
            const isActive = highlightKey === p.key;
            return (
              <button
                key={p.key}
                type="button"
                onMouseEnter={() => setActiveKey(p.key)}
                onFocus={() => setActiveKey(p.key)}
                onMouseLeave={() => setActiveKey(DEFAULT_ACTIVE)}
                onBlur={() => setActiveKey(DEFAULT_ACTIVE)}
                data-testid={`phase-strip-${p.key}`}
                className="text-left rounded-2xl p-4 transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pm-primary focus-visible:ring-offset-2"
                style={{
                  background: isActive ? "var(--pm-lime)" : "transparent",
                  opacity: entered ? 1 : 0,
                  transform: entered ? "translateY(0)" : "translateY(12px)",
                  transitionProperty: "opacity, transform, background-color",
                  transitionDuration: "400ms, 400ms, 200ms",
                  transitionDelay: entered ? `${i * STEP_DELAY_MS}ms` : "0ms",
                }}
              >
                <div
                  className="relative w-9 h-9 rounded-lg grid place-items-center mb-3"
                  style={{ background: p.color + "14" }}
                >
                  <p.icon size={18} style={{ color: p.color }} />
                  <span
                    className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full grid place-items-center text-[9px] font-mono font-bold"
                    style={{
                      background: isActive ? "var(--pm-lime)" : "var(--pm-teal-deep)",
                      color: isActive ? "#0B2A30" : "#FFFFFF",
                    }}
                  >
                    {i + 1}
                  </span>
                </div>
                <div className="font-display font-bold text-sm sm:text-base">{p.title}</div>
                <div className={`mt-1 text-xs sm:text-sm leading-snug ${isActive ? "text-[#0B2A30]/75" : "text-pm-text2"}`}>
                  {p.desc}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
