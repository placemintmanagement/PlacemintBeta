import React, { useState } from "react";
import { PHASES } from "../PhaseStrip";

const PX = [60, 180, 290, 400];
const PY = [190, 138, 98, 60];
const PW = [86, 56, 92, 78];
const CURVE = "M60 190C110 190 130 140 180 138C230 136 250 100 290 98C340 96 360 64 400 60";
const SHORT = { resume: "Resume", oa: "OA", interview: "Interview", review: "Review" };

/**
 * "Four phases. One story." (reference: dark split panel + animated SVG
 * step-path). Copy for all four phases is PhaseStrip.jsx's existing,
 * real PHASES array (title + desc), not the mockup's placeholder text.
 */
export default function GlassFourPhases() {
  const [ph, setPh] = useState(0);
  const phase = PHASES[ph];

  return (
    <section className="gl-sec gl-sec-wide">
      <div className="gl-dk">
        <div className="gl-dl">
          <h2>Four phases. <b>One story.</b></h2>
          <p>Every phase feeds the next, so you get one story of how you performed, not four separate scores.</p>
          <div className="gl-ibox">
            <div>
              <small>Phase {ph + 1} of 4: {phase.title}</small>
              <span>{phase.desc}</span>
            </div>
            <button type="button" className="gl-nxt" onClick={() => setPh((p) => (p + 1) % 4)}>
              Next<i aria-hidden="true">&rarr;</i>
            </button>
          </div>
        </div>
        <div className="gl-dr">
          <div className="gl-dc">
            <div className="gl-dct">Your readiness story</div>
            <svg viewBox="0 0 460 240" role="img" aria-label="Four phases rising to one verdict">
              <defs>
                <clipPath id="gl-fcp">
                  <rect x="0" y="0" width={PX[ph] + 4} height="240" />
                </clipPath>
              </defs>
              <path d={`${CURVE}L400 240L60 240Z`} fill="rgba(255,196,40,.18)" clipPath="url(#gl-fcp)" />
              <path d={CURVE} fill="none" stroke="rgba(255,255,255,.45)" strokeWidth="2" />
              <path d={CURVE} fill="none" stroke="#FFC428" strokeWidth="3" clipPath="url(#gl-fcp)" />
              {PHASES.map((p, i) => {
                const on = i === ph;
                const x = PX[i], y = PY[i], w = PW[i];
                return (
                  <g key={p.key} style={{ cursor: "pointer" }} onClick={() => setPh(i)}>
                    <circle cx={x} cy={y} r={on ? 9 : 6} fill={on ? "#FFC428" : "#777"} />
                    <rect
                      x={x - w / 2}
                      y={y - 46}
                      width={w}
                      height={28}
                      rx={14}
                      fill="#000"
                      strokeWidth={on ? 2 : 1}
                      stroke={on ? "#FFC428" : "rgba(255,255,255,.3)"}
                    />
                    <text x={x} y={y - 27} textAnchor="middle" fontSize="12" fill={on ? "#fff" : "#aaa"}>
                      {SHORT[p.key]}
                    </text>
                  </g>
                );
              })}
              <text x="12" y="234" fontSize="12" fill="#777">Start</text>
              <text x="448" y="234" fontSize="12" textAnchor="end" fill="#777">One verdict</text>
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}
