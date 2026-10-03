import React, { useState } from "react";
import Editor from "@monaco-editor/react";
import { Play, CheckCircle2, XCircle } from "lucide-react";

function MD({ children }) {
  const text = String(children || "");
  return (
    <div className="prose prose-sm max-w-none whitespace-pre-wrap font-sans text-pm-text">
      {text.split("\n").map((line, i) => <p key={i} className="my-1">{line}</p>)}
    </div>
  );
}

const DEBUG_LANGUAGES = [
  { value: "python", label: "Python 3" },
  { value: "c", label: "C" },
  { value: "cpp", label: "C++" },
  { value: "java", label: "Java" },
];

/**
 * Debugging Assessment (Round 3) interface. Deliberately mirrors
 * CodingSection's (OARunner.jsx) editor/layout conventions -- problem
 * statement on the left, a dark Monaco editor on the right, a language
 * selector, sample tests, run results -- rather than inventing a new
 * layout, per the existing coding round already being the reference UI.
 *
 * Differences from CodingSection: the editor is ALWAYS pre-loaded with
 * the debugging_variant's buggy_code for whichever language is
 * selected (not just for an "automata_fix" flag), a task_description
 * block explains what's wrong, and the language choices are the 4
 * confirmed ones (Python/C/C++/Java) rather than CodingSection's 5
 * (which also includes JavaScript).
 *
 * NOT wired into OARunner's live section-type switch yet -- see
 * /dev/debugging-preview for a standalone render of this component.
 * `answers` / `setAnswer` follow the exact same controlled-prop shape
 * CodingSection uses, so wiring this in later is a drop-in.
 */
export default function DebuggingSection({ problems, answers, setAnswer, onRun, running, runResults }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const qs = problems || [];
  const problem = qs[activeIdx];
  if (!problem) return <div className="pm-card p-6">No problems drawn for this session.</div>;

  const variant = problem.debugging_variant || {};
  const buggyByLang = variant.buggy_code || {};
  const current = answers[problem.id] || { language: "python", code: buggyByLang.python || "" };
  if (!answers[problem.id]) {
    // Seed once, mirrors CodingSection's automataFix pre-fill-on-first-render pattern.
    setAnswer(problem.id, current);
  }
  const setForProblem = (patch) => setAnswer(problem.id, { ...current, ...patch });

  // Per (problem, language) draft memory, so switching languages to peek
  // at another one doesn't lose an in-progress fix, but still starts
  // fresh from the buggy code the first time a language is opened.
  const draftKey = (lang) => `${problem.id}:${lang}`;

  const changeLanguage = (language) => {
    const draft = answers[draftKey(language)];
    setForProblem({ language, code: draft !== undefined ? draft : (buggyByLang[language] || "") });
  };

  const changeCode = (code) => {
    setForProblem({ code });
    setAnswer(draftKey(current.language), code);
  };

  return (
    <div>
      {qs.length > 1 && (
        <div className="flex gap-2 mb-4">
          {qs.map((p, i) => (
            <button
              key={p.id}
              data-testid={`debug-problem-tab-${i}`}
              onClick={() => setActiveIdx(i)}
              className={`px-3 py-1.5 rounded-full text-sm font-display font-semibold ${i === activeIdx ? "bg-[var(--pm-teal-deep)] text-white" : "bg-[var(--pm-sky)] text-[var(--pm-ink)]"}`}
            >
              Problem {i + 1} · {p.topic}
            </button>
          ))}
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:h-[70vh]">
        {/* Left: problem statement + what's wrong + sample tests */}
        <div className="pm-card p-6 overflow-y-auto">
          <div className="flex items-center justify-between mb-2">
            <div className="font-display text-xl font-bold">{problem.title}</div>
            <span className="pm-chip pm-chip-primary">{problem.difficulty}</span>
          </div>
          <div className="text-sm text-pm-text2"><MD>{problem.statement}</MD></div>

          <div className="mt-4 rounded-xl p-4" style={{ background: "rgba(255, 138, 76, 0.08)", border: "1px solid rgba(255, 138, 76, 0.25)" }}>
            <div className="text-xs pm-eyebrow text-pm-text2 mb-1">What's wrong with this code</div>
            <div className="text-sm">{variant.task_description}</div>
          </div>

          {problem.input_format && (
            <div className="mt-4">
              <div className="text-xs pm-eyebrow text-pm-text2 mb-1">Input</div>
              <div className="text-sm">{problem.input_format}</div>
            </div>
          )}
          {problem.output_format && (
            <div className="mt-3">
              <div className="text-xs pm-eyebrow text-pm-text2 mb-1">Output</div>
              <div className="text-sm">{problem.output_format}</div>
            </div>
          )}
          {problem.constraints && (
            <div className="mt-3">
              <div className="text-xs pm-eyebrow text-pm-text2 mb-1">Constraints</div>
              <div className="text-sm font-mono">{problem.constraints}</div>
            </div>
          )}

          <div className="mt-6">
            <div className="text-xs pm-eyebrow text-pm-text2 mb-2">Sample tests</div>
            <div className="space-y-2">
              {(problem.visible_tests || []).map((t, i) => (
                <div key={i} className="border rounded-[14px] p-3 text-xs font-mono bg-[var(--pm-grey)]">
                  <div><span className="text-pm-text2">input:</span> {t.input}</div>
                  <div><span className="text-pm-text2">expected:</span> {t.expected_output}</div>
                </div>
              ))}
            </div>
          </div>

          {runResults && (
            <div className="mt-6" data-testid="debug-run-results">
              <div className="text-xs pm-eyebrow text-pm-text2 mb-2">Run results</div>
              <div className="space-y-2">
                {runResults.map((r, i) => (
                  <div key={i} data-testid={`debug-run-result-${i}`} className={`border rounded-[14px] p-3 text-xs font-mono ${r.passed ? "border-[rgba(15,111,122,0.4)] bg-[var(--pm-success-bg)]" : "border-[rgba(180,35,24,0.4)] bg-[var(--pm-error-bg)]"}`}>
                    <div className="flex items-center gap-2">
                      {r.passed ? <CheckCircle2 size={14} className="text-pm-primary" /> : <XCircle size={14} className="text-[var(--pm-error-text)]" />}
                      Test {i + 1} · {r.passed ? "passed" : "failed"}
                    </div>
                    <div className="mt-1 text-pm-text2">expected: {r.expected}</div>
                    <div className="text-pm-text2">got: {r.got || (r.error ? `(error) ${r.error}` : "")}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: dark Monaco editor, pre-loaded with the buggy code */}
        <div className="pm-editor-pane rounded-2xl overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
            <div className="flex items-center gap-2">
              <select
                data-testid="debug-lang-select"
                value={current.language}
                onChange={(e) => changeLanguage(e.target.value)}
                className="bg-transparent border border-white/10 rounded-md text-xs px-2 py-1 font-mono"
              >
                {DEBUG_LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
              <span className="pm-chip pm-chip-coral">buggy code pre-filled · fix it</span>
            </div>
            <button
              data-testid="debug-run-btn"
              onClick={() => onRun(problem, current)}
              disabled={running}
              className="pm-btn text-xs py-1.5 px-3"
              style={{ background: "var(--pm-teal-deep)", color: "var(--pm-white)" }}
            >
              <Play size={12} /> {running ? "running…" : "Run sample tests"}
            </button>
          </div>
          <div className="flex-1 min-h-[400px]">
            <Editor
              height="100%"
              language={current.language === "cpp" ? "cpp" : current.language}
              theme="vs-dark"
              value={current.code}
              onChange={(v) => changeCode(v || "")}
              options={{ fontSize: 14, minimap: { enabled: false }, fontFamily: "JetBrains Mono", padding: { top: 12 }, scrollBeyondLastLine: false }}
            />
          </div>
          {/* Hidden mirror of the editor's value -- same pattern CodingSection
              (OARunner.jsx) uses: Monaco has no plain DOM input a test can
              `.fill()`, so this controlled, screen-reader-only textarea gives
              Playwright (or any test) a normal element to type into; onChange
              routes through the exact same setter Monaco's own onChange uses,
              so Monaco re-renders with the new value via its controlled `value` prop. */}
          <textarea
            data-testid="debug-code-area"
            value={current.code}
            onChange={(e) => changeCode(e.target.value)}
            className="sr-only"
            aria-hidden
          />
        </div>
      </div>
    </div>
  );
}
