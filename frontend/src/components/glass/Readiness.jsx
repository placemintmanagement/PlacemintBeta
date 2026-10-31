import React from "react";

// Generic, illustrative interview-competency dimensions -- same REGISTER
// as a real adaptive-interview evaluation (communication, depth of
// technical answers, clarity, etc.), not a specific claimed scoring
// rubric this app runs today. Six labels to match the hexagon's six
// points, same spirit as the reference's own vertex set (Research /
// Communication / Teamwork / ...) without copying it.
const DIMENSIONS = ["Communication", "Problem Solving", "Technical Depth", "Clarity", "Ownership", "Follow-through"];

// Fixed, hand-picked radii (as a fraction of the outer grid ring) for the
// filled polygon's six vertices -- NOT derived from any formula, random
// seed, company, topic or any other state. The reference's equivalent
// shape is driven by six numeric scores (4.7/4.2/3.6/...); this app has
// no real per-dimension interview signal to show honestly, so rather than
// invent one, this shape is a plain static illustration -- the exact same
// irregular-hexagon silhouette every time, for every visitor, regardless
// of anything they do. It never changes, which is what keeps it in the
// "shape only" register the caption below states rather than reading as
// a result.
const SHAPE = [0.78, 0.62, 0.88, 0.7, 0.58, 0.82];
const GRID_RINGS = [0.33, 0.66, 1];

/**
 * "Interview results" card -- deliberately qualitative, not a chart.
 *
 * Reframed (2026-10) from a general "sectional readiness" meter (mixed OA
 * topics + phases) to specifically an interview-results card, matching
 * the reference's own "Interview Results" framing, including its
 * concentric radar-grid rings and a filled irregular polygon -- see
 * docs/glass-restyle-progress.md for the full reasoning.
 *
 * Honesty-rule call, unchanged in spirit from the original version: the
 * reference's own vertices carry fabricated numeric scores
 * (4.7/4.2/3.6/...) -- exactly the kind of real-result-shaped visual this
 * app's standing honesty rule forbids. This version matches the
 * reference's visual STRUCTURE (grid rings, filled polygon, vertex dots)
 * but the polygon's shape is a fixed constant (see SHAPE above), not
 * computed from anything -- no magnitude is ever encoded, per-dimension
 * or otherwise, and the shape can't be read as "your" result because it
 * literally never changes. The only thing that DOES change is a single
 * binary "active" state (brighter fill + glow) while a live interview is
 * actually in progress (`interviewActive`).
 */
export default function Readiness({ interviewActive = false }) {
  const cx = 110, cy = 86, r = 56;

  const pt = (i, radius) => {
    const a = -Math.PI / 2 + (i * Math.PI) / 3;
    return [cx + Math.cos(a) * radius, cy + Math.sin(a) * radius];
  };

  const shapePoints = SHAPE.map((f, i) => pt(i, r * f).join(",")).join(" ");

  return (
    <div>
      <svg viewBox="0 0 220 170" className="gl-ready-shape" role="img" aria-label="Dimensions an adaptive interview looks at">
        {GRID_RINGS.map((f) => (
          <polygon key={f} fill="none" stroke="rgba(255,255,255,.22)" strokeWidth="1" points={DIMENSIONS.map((_, i) => pt(i, r * f).join(",")).join(" ")} />
        ))}
        <polygon
          fill={interviewActive ? "rgba(255,196,40,.38)" : "rgba(255,196,40,.22)"}
          stroke={interviewActive ? "#FFC428" : "rgba(255,196,40,.6)"}
          strokeWidth="1.6"
          points={shapePoints}
          style={{ transition: "fill 300ms, stroke 300ms" }}
        />
        {DIMENSIONS.map((label, i) => {
          const [lx, ly] = pt(i, r * 1.34);
          const [dx, dy] = pt(i, r * SHAPE[i]);
          return (
            <g key={label}>
              <text x={lx} y={ly + 3} textAnchor="middle" fontSize="11" fill="#fff" opacity={interviewActive ? 1 : 0.8}>
                {label}
              </text>
              <circle cx={dx} cy={dy} r={interviewActive ? 3.2 : 2.4} fill={interviewActive ? "#FFC428" : "rgba(255,196,40,.85)"} />
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export { DIMENSIONS };
