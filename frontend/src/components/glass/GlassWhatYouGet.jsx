import React, { useState } from "react";
import { FileCheck2, MessageSquareText, ShieldCheck, Layers, Code2, RefreshCw } from "lucide-react";

/**
 * "What you get" interactive picker (reference section #get). Copy for all
 * six options is carried over verbatim from the site's existing bento
 * section + WhatYouGetSection.jsx (Landing.jsx, teal design) -- not the
 * mockup's placeholder text. Picking an option just highlights it and
 * advances the "Feature X of 6" counter -- no preview card below (removed
 * per feedback: a per-option illustration/title/desc card was tried here,
 * but the ask is for the grid to be self-explanatory, nothing changes
 * below it on click).
 */
// Vivid, saturated colors (not the shared --gl-* pastel tokens, which
// read as washed-out/grey at icon scale even with a saturate() filter
// boost) -- matches a provided reference screenshot's bright per-icon
// colors, one distinct hue per option.
const FEATURES = [
  { key: "resume", name: "Resume checker", icon: FileCheck2, ic: "#16a34a" },
  { key: "interview", name: "Adaptive interview", icon: MessageSquareText, ic: "#2563eb" },
  { key: "cutoffs", name: "Sectional cutoffs", icon: ShieldCheck, ic: "#dc2626" },
  { key: "report", name: "One report", icon: Layers, ic: "#ca8a04" },
  { key: "coding", name: "Coding rounds", icon: Code2, ic: "#0d9488" },
  { key: "fresh", name: "Fresh questions", icon: RefreshCw, ic: "#ea580c" },
];

export default function GlassWhatYouGet() {
  const [k, setK] = useState(0);

  return (
    <section className="gl-sec" id="get">
      <div className="gl-wg">
        <div>
          <span className="gl-bdg"><i>&#10022;</i>What you get</span>
          <h2 className="gl-h2">Everything a real placement drive <b>throws at you.</b></h2>
          <p className="gl-sub">Pick one to see how it works. Every part mirrors how the company actually screens.</p>
        </div>

        <div className="gl-wc">
          <div className="gl-wc-in">
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
                    <b style={{ "--oc": o.ic }}><OIcon size={19} /></b>
                    {o.name}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
