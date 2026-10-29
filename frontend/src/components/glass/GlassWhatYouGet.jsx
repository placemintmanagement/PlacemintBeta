import React, { useState } from "react";
import { FileCheck2, MessageSquareText, ShieldCheck, Layers, Code2, RefreshCw } from "lucide-react";

/**
 * "What you get" interactive picker (reference section #get). Copy for all
 * six options is carried over verbatim from the site's existing bento
 * section + WhatYouGetSection.jsx (Landing.jsx, teal design) -- not the
 * mockup's placeholder text. The reference's own FT array defines a
 * title/description/illustration per option but its script never actually
 * renders them anywhere (only the option buttons' own highlight state and
 * the "Feature X of 6" counter update) -- a clear gap in the reference, not
 * a deliberate behavior, so this implementation wires the preview card the
 * data obviously intends: picking an option swaps the big card's title,
 * description and background tint below the grid.
 */
const FEATURES = [
  {
    key: "resume",
    name: "Resume checker",
    title: "Resume checker, free forever",
    desc: "Uploads once, gets analysed against this company & this role. Strengths, weaknesses, fit score, projects extracted. No credit card needed.",
    icon: FileCheck2,
    tc: "--gl-pink",
  },
  {
    key: "interview",
    name: "Adaptive interview",
    title: "Adaptive interview",
    desc: "One question at a time, planned for the company you chose and drawing on your resume when one is attached. A short verdict follows each answer.",
    icon: MessageSquareText,
    tc: "--gl-blue",
  },
  {
    key: "cutoffs",
    name: "Sectional cutoffs",
    title: "Sectional cutoffs, honest verdicts",
    desc: "Where a company sets a cutoff for each section, missing one means not ready. Where it uses a blended score, we show your weakest section.",
    icon: ShieldCheck,
    tc: "--gl-sand",
  },
  {
    key: "report",
    name: "One report",
    title: "One report, not four",
    desc: "The final report ties resume, OA, and interview into a single narrative, written by our premium AI tier, the one place we don't downgrade.",
    icon: Layers,
    tc: "--gl-mint",
  },
  {
    key: "coding",
    name: "Coding rounds",
    title: "LeetCode-style coding rounds",
    desc: "Split-panel IDE, dark editor on a light page. 2 visible tests. 3 hidden tests unlocked on Submit. Write in Python, JS, C, C++, Java.",
    icon: Code2,
    tc: "--gl-blue",
  },
  {
    key: "fresh",
    name: "Fresh questions",
    title: "Fresh questions every run",
    desc: "Generated and execution-verified, so there are no memorised answer sheets.",
    icon: RefreshCw,
    tc: "--gl-y",
  },
];

export default function GlassWhatYouGet() {
  const [k, setK] = useState(0);
  const f = FEATURES[k];
  const Icon = f.icon;

  return (
    <section className="gl-sec" id="get">
      <div className="gl-wg">
        <div>
          <span className="gl-bdg"><i>&#10022;</i>What you get</span>
          <h2 className="gl-h2">Everything a real placement drive <b>throws at you.</b></h2>
          <p className="gl-sub">Pick one to see how it works. Every part mirrors how the company actually screens.</p>
        </div>

        <div className="gl-wc">
          <div className="gl-wh">
            <h3>Where do you want to start?</h3>
            <div className="gl-pg">
              <small>Feature {k + 1} of {FEATURES.length}</small>
              <span className="gl-pgp">
                {FEATURES.map((_, i) => <i key={i} className={i === k ? "on" : ""} />)}
              </span>
            </div>
          </div>

          <div className="gl-opts" role="tablist" aria-label="Feature picker">
            {FEATURES.map((o, i) => {
              const OIcon = o.icon;
              return (
                <button
                  key={o.key}
                  type="button"
                  role="tab"
                  aria-selected={i === k}
                  className={`gl-opt${i === k ? " on" : ""}`}
                  onClick={() => setK(i)}
                >
                  <b style={{ color: `var(${o.tc})` }}><OIcon size={22} /></b>
                  {o.name}
                </button>
              );
            })}
          </div>

          <div
            className="gl-fc"
            style={{ background: `linear-gradient(150deg, color-mix(in srgb, var(${f.tc}) 55%, transparent), transparent 70%), color-mix(in srgb, var(${f.tc}) 70%, var(--gl-card))` }}
          >
            <span className="gl-fc-g"><Icon size={20} /></span>
            <div className="gl-fc-tx">
              <h4>{f.title}</h4>
              <p>{f.desc}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
