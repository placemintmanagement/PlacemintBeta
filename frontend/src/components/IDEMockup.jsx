import React from "react";

/**
 * A miniature, non-interactive replica of the OA coding round. Renders exactly
 * the same split layout the user will see inside the app:
 *   - Left: light problem panel (title, difficulty chip, statement, tests).
 *   - Right: dark editor with syntax-highlighted-ish sample code.
 * The point is to sell what the product looks like, not to be interactive.
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

const TOKEN_COLOR = {
  kw: "#FF7B72",   // pink for keywords
  fn: "#D2A8FF",   // purple for functions
  str: "#A5D6FF",  // blue-ish for strings
};

export default function IDEMockup() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 rounded-2xl overflow-hidden border border-white/5 shadow-2xl">
      {/* LEFT: problem panel */}
      <div className="bg-[#FAF8F3] p-6 md:p-7 min-h-[360px]">
        <div className="flex items-center justify-between mb-3">
          <div className="font-display text-xl font-bold">Two Sum</div>
          <span className="pm-chip pm-chip-primary">Easy</span>
        </div>
        <div className="text-sm text-pm-text leading-relaxed">
          Given an integer array <code className="font-mono bg-pm-muted px-1 rounded">nums</code> and a target <code className="font-mono bg-pm-muted px-1 rounded">target</code>, return the indices of the two numbers that add up to target.
        </div>
        <div className="mt-4 text-xs font-mono uppercase text-pm-text2 mb-2">Visible tests</div>
        <div className="space-y-2">
          <div className="border rounded-lg p-3 text-xs font-mono bg-pm-muted/60">
            <div><span className="text-pm-text2">input:</span> nums=[2,7,11,15], target=9</div>
            <div><span className="text-pm-text2">expected:</span> [0,1]</div>
          </div>
          <div className="border rounded-lg p-3 text-xs font-mono bg-pm-muted/60">
            <div><span className="text-pm-text2">input:</span> nums=[3,3], target=6</div>
            <div><span className="text-pm-text2">expected:</span> [0,1]</div>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3 text-xs font-mono text-pm-text2">
          <span className="pm-chip">3 hidden tests</span>
          <span className="pm-chip">10:24 left</span>
        </div>
      </div>

      {/* RIGHT: dark editor */}
      <div className="bg-[#0F111A] text-white flex flex-col min-h-[360px]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
          <div className="text-[11px] font-mono text-white/50">two_sum.py</div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono border border-white/10 rounded-md px-2 py-0.5">Python 3</span>
            <span className="text-[11px] font-mono rounded-md px-2 py-0.5 bg-pm-primary text-white">Run</span>
          </div>
        </div>
        <div className="p-4 font-mono text-[13px] leading-[1.65] flex-1 overflow-hidden">
          {CODE_LINES.map((ln, i) => (
            <div key={i} className="flex">
              <span className="text-white/25 w-6 select-none text-right pr-3">{i + 1}</span>
              <span className="whitespace-pre">
                {ln.t.map((tok, j) => (
                  <span key={j} style={{ color: tok.c ? TOKEN_COLOR[tok.c] : "#E4E7EE" }}>{tok.txt}</span>
                ))}
              </span>
            </div>
          ))}
          <div className="mt-3 flex items-center gap-2 text-[11px]">
            <span className="w-2 h-2 rounded-full bg-pm-primary animate-pulse"></span>
            <span className="text-white/60 font-mono">2 / 2 visible tests passed</span>
          </div>
        </div>
      </div>
    </div>
  );
}
