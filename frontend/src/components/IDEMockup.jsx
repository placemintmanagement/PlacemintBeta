import React from "react";
import { Clock } from "lucide-react";

/**
 * A miniature, non-interactive replica of the OA coding round. Renders exactly
 * the same split layout the user will see inside the app:
 *   - Left: light problem panel (title, difficulty chip, statement, tests).
 *   - Right: dark editor with syntax-highlighted-ish sample code.
 * The point is to sell what the product looks like, not to be interactive.
 *
 * 2026-10 redesign: the whole mock sits on a sky-deep "stage" so it reads as
 * the visual centre of the section. Monospace appears only inside code:
 * inline code pills, test cases, and the editor itself.
 */
const CODE_LINES = [
  { t: [{ txt: "def", c: "kw" }, { txt: " " }, { txt: "two_sum", c: "fn" }, { txt: "(nums, target):" }] },
  { t: [{ txt: "    seen = {}" }] },
  { t: [{ txt: "    " }, { txt: "for", c: "kw" }, { txt: " i, n " }, { txt: "in", c: "kw" }, { txt: " " }, { txt: "enumerate", c: "fn" }, { txt: "(nums):" }] },
  { t: [{ txt: "        diff = target - n" }] },
  { t: [{ txt: "        " }, { txt: "if", c: "kw" }, { txt: " diff " }, { txt: "in", c: "kw" }, { txt: " seen:" }] },
  { t: [{ txt: "            " }, { txt: "return", c: "kw" }, { txt: " [seen[diff], i]" }] },
  { t: [{ txt: "        seen[n] = i" }] },
  { t: [{ txt: "    " }, { txt: "return", c: "kw" }, { txt: " []" }] },
];

// Syntax colours on #0B2A30. Each is checked to be at least 4.5:1 there.
const TOKEN_COLOR = {
  kw: "#FF9A93",   // keywords (was #FF7B72, raised for contrast)
  fn: "#DDBDFF",   // functions (was #D2A8FF, raised for contrast)
  str: "#A5D6FF",  // strings
};

const CODE_PILL = { background: "#E8F3FB", borderRadius: 8, padding: "1px 6px", fontFamily: "ui-monospace, monospace", fontSize: "0.92em", color: "#0B2A30" };
const TESTCASE = { background: "#E8F3FB", borderRadius: 14, padding: "12px 14px", fontFamily: "ui-monospace, monospace", fontSize: 13, color: "rgba(11,42,48,0.85)", lineHeight: 1.6 };
const LABEL = { fontFamily: "var(--pm-font-label)", fontWeight: 600, fontSize: 11, letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(11,42,48,0.7)" };

export default function IDEMockup() {
  return (
    <div className="rounded-[32px] p-3.5 sm:p-7" style={{ background: "var(--pm-sky-deep)" }}>
      <div
        className="grid grid-cols-1 lg:grid-cols-2 overflow-hidden"
        style={{
          borderRadius: 20,
          border: "1px solid rgba(7,59,67,0.12)",
          boxShadow: "0 30px 50px -28px rgba(7,59,67,0.5)",
        }}
      >
        {/* LEFT: problem panel */}
        <div className="p-6 md:p-7 min-h-[360px]" style={{ background: "#FFFFFF" }}>
          <div className="flex items-center justify-between gap-3 mb-3">
            <div className="font-display font-semibold" style={{ fontSize: 22, color: "#0B2A30" }}>Two Sum</div>
            <span className="rounded-full whitespace-nowrap" style={{ background: "#EAF9C4", color: "#0B2A30", fontSize: 13, padding: "4px 10px" }}>Easy</span>
          </div>
          <div style={{ fontSize: 15, lineHeight: 1.6, color: "rgba(11,42,48,0.8)" }}>
            Given an integer array <code style={CODE_PILL}>nums</code> and a target <code style={CODE_PILL}>target</code>, return the indices of the two numbers that add up to target.
          </div>
          <div className="mt-5" style={LABEL}>Visible tests</div>
          <div className="mt-2 space-y-2">
            <div style={TESTCASE}>
              <div><span style={{ color: "rgba(11,42,48,0.7)" }}>input:</span> nums=[2,7,11,15], target=9</div>
              <div><span style={{ color: "rgba(11,42,48,0.7)" }}>expected:</span> [0,1]</div>
            </div>
            <div style={TESTCASE}>
              <div><span style={{ color: "rgba(11,42,48,0.7)" }}>input:</span> nums=[3,3], target=6</div>
              <div><span style={{ color: "rgba(11,42,48,0.7)" }}>expected:</span> [0,1]</div>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-3" style={{ fontSize: 13 }}>
            <span className="rounded-full" style={{ background: "#E8F3FB", color: "#0B2A30", padding: "4px 10px" }}>3 hidden tests</span>
            <span className="inline-flex items-center gap-1.5 rounded-full" style={{ background: "#EAF9C4", color: "#0B2A30", padding: "4px 10px" }}>
              <Clock size={13} style={{ color: "#0F6F7A" }} aria-hidden="true" />
              10:24 left
            </span>
          </div>
        </div>

        {/* RIGHT: dark editor (the allowed dark surface) */}
        <div className="flex flex-col min-h-[260px] lg:min-h-[360px]" style={{ background: "#0B2A30", color: "#FFFFFF" }}>
          <div className="flex items-center justify-between gap-3 px-4 py-3" style={{ background: "#0F3A42", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <div style={{ fontSize: 12, fontFamily: "ui-monospace, monospace", color: "rgba(255,255,255,0.7)" }}>two_sum.py</div>
            <div className="flex items-center gap-2">
              <span className="rounded-md px-2 py-0.5" style={{ fontSize: 12, fontFamily: "ui-monospace, monospace", border: "1px solid rgba(255,255,255,0.2)", color: "#FFFFFF" }}>Python 3</span>
              <span className="rounded-full px-3 py-1 font-display font-semibold" style={{ fontSize: 13, background: "#C6F24E", color: "#0B2A30" }}>Run</span>
            </div>
          </div>
          <div className="p-4 flex-1 overflow-x-auto" style={{ fontFamily: "ui-monospace, monospace", fontSize: 13, lineHeight: 1.65 }}>
            {CODE_LINES.map((ln, i) => (
              <div key={i} className="flex min-w-max">
                <span className="w-6 select-none text-right pr-3" style={{ color: "rgba(255,255,255,0.55)" }}>{i + 1}</span>
                <span className="whitespace-pre">
                  {ln.t.map((tok, j) => (
                    <span key={j} style={{ color: tok.c ? TOKEN_COLOR[tok.c] : "#E4E7EE" }}>{tok.txt}</span>
                  ))}
                </span>
              </div>
            ))}
            <div className="mt-3 flex items-center gap-2" style={{ fontSize: 12, fontFamily: "var(--pm-font-display)" }}>
              <span className="w-2 h-2 rounded-full" style={{ background: "#C6F24E" }} aria-hidden="true"></span>
              <span style={{ color: "rgba(255,255,255,0.85)" }}>2 / 2 visible tests passed</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
