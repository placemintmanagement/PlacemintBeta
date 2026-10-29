import React, { useEffect, useRef, useState } from "react";

// Same Two Sum problem/code/test cases as components/IDEMockup.jsx (teal
// design) -- a generic, reasonable placeholder problem with no existing
// real equivalent to preserve, so it's kept as-is per the task brief.
const CODE_LINES = [
  [{ t: "def", k: true }, { t: " " }, { t: "two_sum", f: true }, { t: "(nums, target):" }],
  [{ t: "    seen = {}" }],
  [{ t: "    " }, { t: "for", k: true }, { t: " i, n " }, { t: "in", k: true }, { t: " " }, { t: "enumerate", f: true }, { t: "(nums):" }],
  [{ t: "        diff = target - n" }],
  [{ t: "        " }, { t: "if", k: true }, { t: " diff " }, { t: "in", k: true }, { t: " seen:" }],
  [{ t: "            " }, { t: "return", k: true }, { t: " [seen[diff], i]" }],
  [{ t: "        seen[n] = i" }],
  [{ t: "    " }, { t: "return", k: true }, { t: " []" }],
];

export default function GlassIdeSection() {
  const [left, setLeft] = useState(624); // 10:24, same starting countdown as the reference
  const [running, setRunning] = useState(false);
  const [ran, setRan] = useState(false);
  const runTimeout = useRef(null);

  useEffect(() => {
    const id = setInterval(() => setLeft((s) => (s > 0 ? s - 1 : 0)), 1000);
    return () => clearInterval(id);
  }, []);
  useEffect(() => () => clearTimeout(runTimeout.current), []);

  function run() {
    setRunning(true);
    runTimeout.current = setTimeout(() => {
      setRunning(false);
      setRan(true);
    }, 600);
  }

  const mm = Math.floor(left / 60);
  const ss = String(left % 60).padStart(2, "0");

  return (
    <section className="gl-sec">
      <h2 className="gl-h2">A real split-panel coding IDE, <b>not a textarea.</b></h2>
      <p className="gl-sub">The same layout as HackerRank and LeetCode: problem on the left, dark editor on the right.</p>
      <div className="gl-ide">
        <div className="gl-ide-in">
          <div className="gl-pl">
            <h3>Two Sum <span className="gl-tag">Easy</span></h3>
            <p>
              Given an integer array <code>nums</code> and a target <code>target</code>, return the indices of the two
              numbers that add up to target.
            </p>
            <b style={{ fontWeight: 500, fontSize: 14 }}>Visible tests</b>
            <div>
              <div className="gl-tc">input: nums=[2,7,11,15], target=9<br />expected: [0,1]</div>
              <div className="gl-tc">input: nums=[3,3], target=6<br />expected: [0,1]</div>
            </div>
            <div className="gl-pl-ft">
              <span className="gl-tag">3 hidden tests</span>
              <span className="gl-tag">{mm}:{ss} left</span>
            </div>
          </div>
          <div className="gl-ed">
            <div className="gl-bar">
              <span>two_sum.py</span>
              <span className="gl-bar-r">
                <em>Python 3</em>
                <button type="button" className="gl-run" disabled={running} onClick={run}>
                  {running ? "Running…" : "Run"}
                </button>
              </span>
            </div>
            <pre className="gl-code">
              {CODE_LINES.map((line, i) => (
                <div key={i}>
                  <span className="ln">{i + 1}</span>
                  <span>
                    {line.map((tok, j) => (
                      <span key={j} className={tok.k ? "gl-k" : tok.f ? "gl-f" : undefined}>{tok.t}</span>
                    ))}
                  </span>
                </div>
              ))}
            </pre>
            {ran && (
              <div className="gl-out">
                <i aria-hidden="true" />2 / 2 visible tests passed. 3 hidden tests unlock on Submit.
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
