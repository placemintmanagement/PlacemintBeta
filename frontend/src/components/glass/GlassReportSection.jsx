import React from "react";
import { Link } from "react-router-dom";

/**
 * Report section (reference: dark gradient `.rep` + glass `.rc` report
 * card). This one was already explicitly called out in the task brief as
 * fine as-is: the reference itself labels it "Illustrative example", and
 * this codebase's own InsideYourReportSection.jsx (teal design) already
 * carries the identical content, decorative bar values and "Illustrative
 * layout, not real results." disclaimer -- reused verbatim here, just
 * restyled into the glass dark-gradient treatment.
 */
const CHECK_LINES = [
  "Every section scored against the company's cutoff logic",
  "Interview feedback on the answers you actually gave",
  "One verdict that ties resume, OA and interview together",
];

export default function GlassReportSection() {
  return (
    <section className="gl-sec">
      <div className="gl-rep">
        <div>
          <h2 className="gl-h2" style={{ color: "#fff" }}>See exactly <b>where you stand.</b></h2>
          <ul>
            {CHECK_LINES.map((t) => <li key={t}><i aria-hidden="true">&#10003;</i>{t}</li>)}
          </ul>
          <Link className="gl-btn y" to="/signup">Get started now</Link>
        </div>

        <div className="gl-rc">
          <header>
            <b style={{ fontWeight: 500 }}>Your Placemint report</b>
            <small>Illustrative example</small>
          </header>

          <div className="gl-ri" style={{ "--bc": "var(--gl-pink)" }}>
            <b>Resume</b>
            <div className="gl-tr"><i style={{ width: "74%" }} /></div>
          </div>

          <div className="gl-ri" style={{ "--bc": "var(--gl-blue)" }}>
            <b>Online assessment</b>
            <div className="gl-tr"><i style={{ width: "82%" }} /><u style={{ left: "62%" }} /></div>
            <span className="gl-pill-sm a">Above cutoff</span>
            <div className="gl-tr"><i style={{ width: "48%" }} /><u style={{ left: "62%" }} /></div>
            <span className="gl-pill-sm b">Below cutoff</span>
            <div className="gl-tr"><i style={{ width: "68%" }} /><u style={{ left: "62%" }} /></div>
            <span className="gl-pill-sm a">Above cutoff</span>
          </div>

          <div className="gl-ri" style={{ "--bc": "var(--gl-y)" }}>
            <b>Interview</b>
            <div className="gl-tr"><i style={{ width: "62%" }} /></div>
            <q>&quot;You mentioned the project but not how you measured the improvement.&quot;</q>
          </div>

          <div className="gl-ri" style={{ border: 0, "--bc": "var(--gl-mint)" }}>
            <b>Cross-phase review</b>
            <div className="gl-tr"><i style={{ width: "78%" }} /></div>
          </div>

          <div className="gl-vd">
            <span className="gl-vd-n">&#10003;</span>
            <div><b style={{ fontWeight: 500 }}>Verdict</b>One narrative of how you performed.</div>
          </div>

          <p style={{ margin: "10px 0 0", textAlign: "center", fontSize: 12, color: "#555" }}>
            Illustrative layout, not real results.
          </p>
        </div>
      </div>
    </section>
  );
}
