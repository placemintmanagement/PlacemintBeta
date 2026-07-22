import React from "react";

/**
 * The signature pipeline diagram — Resume → OA → Interview → Review.
 * Nodes are positioned along an SVG path; an animated dashed stroke flows through it.
 */
const NODES = [
  { key: "resume",    label: "Resume",    subtitle: "AI check",   color: "#0FAE73" },
  { key: "oa",        label: "Online Assessment", subtitle: "Real structure", color: "#0A0A0A" },
  { key: "interview", label: "Interview", subtitle: "Adaptive",   color: "#FF6F4D" },
  { key: "review",    label: "Cross-Phase Review", subtitle: "One narrative", color: "#0FAE73" },
];

export default function PipelineDiagram() {
  return (
    <div id="pipeline" className="w-full">
      <div className="relative">
        {/* SVG connector */}
        <svg viewBox="0 0 1000 160" className="w-full h-32 lg:h-40" preserveAspectRatio="none" aria-hidden>
          <defs>
            <linearGradient id="pipe" x1="0" x2="1">
              <stop offset="0%" stopColor="#0FAE73" />
              <stop offset="50%" stopColor="#0A0A0A" />
              <stop offset="100%" stopColor="#FF6F4D" />
            </linearGradient>
          </defs>
          {/* Base guide */}
          <path d="M 40 80 C 250 20, 500 140, 750 40 S 960 100, 970 80"
                stroke="rgba(10,10,10,0.08)" strokeWidth="2" fill="none" />
          {/* Animated dash */}
          <path d="M 40 80 C 250 20, 500 140, 750 40 S 960 100, 970 80"
                stroke="url(#pipe)" strokeWidth="2.5" fill="none"
                strokeDasharray="6 12" className="pm-flow" />
        </svg>

        {/* Nodes overlay */}
        <div className="absolute inset-0 grid grid-cols-4">
          {NODES.map((n, i) => (
            <div key={n.key} className="flex flex-col items-center justify-end pb-4">
              <div className="pm-card px-4 py-3 flex items-center gap-3 min-w-[130px] max-w-[240px]"
                   style={{ borderColor: n.color + "40" }}>
                <div className="w-8 h-8 rounded-full grid place-items-center font-mono font-bold text-white text-xs"
                     style={{ background: n.color }}>
                  {i + 1}
                </div>
                <div className="text-left">
                  <div className="font-display font-bold leading-tight text-sm sm:text-base">{n.label}</div>
                  <div className="text-[11px] text-pm-text2 leading-tight">{n.subtitle}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
