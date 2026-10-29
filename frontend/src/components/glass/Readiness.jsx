import React from "react";

const TOPICS = ["Aptitude", "Verbal", "Reasoning", "Coding", "Interview", "Resume"];

/**
 * "Sectional readiness" card -- deliberately qualitative, not a chart.
 *
 * Honesty-rule call (see docs/glass-restyle-progress.md): the reference
 * mockup's radar here is a formula-generated numeric scale
 * (`.45+(((ci+1)*(i+3))%6)*.08`) with no in-hero disclaimer -- exactly the
 * kind of "real-result-shaped" visual this app's standing honesty rule
 * forbids. This version keeps the hexagon SHAPE (same register as the
 * reference) but every vertex sits at the SAME radius -- no magnitude is
 * ever encoded. The only thing that changes is which vertex is marked
 * "in focus" right now (a filled dot + highlight ring), driven by the
 * topic tile / phase the visitor is currently looking at. No numbers, no
 * percentages, no implied score -- same "no numbers" rule already applied
 * to every icon-only mock elsewhere in this app.
 */
export default function Readiness({ activeTopic }) {
  const cx = 110, cy = 86, r = 56;
  const activeIndex = TOPICS.indexOf(activeTopic);

  const pt = (i, radius) => {
    const a = -Math.PI / 2 + (i * Math.PI) / 3;
    return [cx + Math.cos(a) * radius, cy + Math.sin(a) * radius];
  };

  const ring1 = TOPICS.map((_, i) => pt(i, r * 0.5).join(",")).join(" ");
  const ring2 = TOPICS.map((_, i) => pt(i, r).join(",")).join(" ");

  return (
    <div>
      <svg viewBox="0 0 220 170" className="gl-ready-shape" role="img" aria-label="Topics covered in your prep plan">
        <polygon fill="none" stroke="rgba(255,255,255,.28)" points={ring1} />
        <polygon fill="rgba(255,255,255,.12)" stroke="rgba(255,255,255,.45)" strokeWidth="1.4" points={ring2} />
        {TOPICS.map((topic, i) => {
          const [lx, ly] = pt(i, r * 1.34);
          const [dx, dy] = pt(i, r);
          const active = i === activeIndex;
          return (
            <g key={topic}>
              <text x={lx} y={ly + 3} textAnchor="middle" fontSize="9" fill="#fff" opacity={active ? 1 : 0.75}>
                {topic}
              </text>
              <circle
                cx={dx}
                cy={dy}
                r={active ? 4.5 : 2.6}
                fill={active ? "#FFC428" : "rgba(255,255,255,.8)"}
              />
              {active && (
                <circle cx={dx} cy={dy} r={8} fill="none" stroke="#FFC428" strokeWidth="1.4" />
              )}
            </g>
          );
        })}
      </svg>
      <p style={{ margin: "6px 0 0", fontSize: 11, opacity: 0.75 }}>
        Shape only — not a score. Highlights what you're currently practising.
      </p>
    </div>
  );
}

export { TOPICS };
