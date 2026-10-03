import React from "react";
import { Link } from "react-router-dom";
import { Check, FileCheck2, Code2, MessageSquareText, ShieldCheck, ArrowRight } from "lucide-react";
import useRevealOnView from "../hooks/useRevealOnView";

/**
 * "Inside your report" (Landing.jsx, 2026-10) -- replaces "Choose your
 * company" (components/ChooseCompanySection.jsx, now gated off by
 * SHOW_COMPANY_GRID in featureFlags.js, not deleted) in the same slot:
 * between What you get (white) and the closing CTA (sky). Structure only
 * -- no artwork, copy or colours copied from any reference. The report
 * card is built entirely from HTML/CSS/SVG, no images, no third-party
 * assets, no real scores/percentages/rankings/company names -- every bar
 * length below is decorative only.
 */
const CHECK_LINES = [
  "Every section scored against the company's cutoff logic",
  "Interview feedback on the answers you actually gave",
  "One verdict that ties resume, OA and interview together",
];

// Decorative only -- no real scores. OA's three sub-bars represent
// "sections" in the abstract; the cutoff marker is a fixed illustrative
// position, not a real company's threshold.
const OA_SUBBARS = [
  { pct: 82, above: true },
  { pct: 48, above: false },
  { pct: 68, above: true },
];
const OA_CUTOFF_PCT = 58;

function CheckRow({ text }) {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-0.5 w-5 h-5 rounded-full grid place-items-center shrink-0" style={{ background: "rgba(15,111,122,0.12)" }}>
        <Check size={12} style={{ color: "#0F6F7A" }} strokeWidth={3} />
      </span>
      <span className="text-sm leading-relaxed" style={{ color: "rgba(11,42,48,0.80)" }}>{text}</span>
    </li>
  );
}

function Bar({ pct, revealed, delayMs, color = "#0F6F7A", trackColor = "var(--pm-sky-deep)", height = 8 }) {
  return (
    <div className="w-full rounded-full overflow-hidden" style={{ background: trackColor, height }}>
      <div
        className="h-full rounded-full"
        style={{
          width: revealed ? `${pct}%` : "0%",
          background: color,
          transition: "width 700ms ease-out",
          transitionDelay: revealed ? delayMs : "0ms",
        }}
      />
    </div>
  );
}

function OARow({ revealed }) {
  return (
    <div className="flex items-start gap-3 py-3 border-t border-[rgba(15,111,122,0.08)]">
      <div className="w-8 h-8 rounded-lg grid place-items-center shrink-0 mt-0.5" style={{ background: "rgba(15,111,122,0.10)" }}>
        <Code2 size={16} style={{ color: "#0F6F7A" }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-display font-semibold text-sm mb-2" style={{ color: "#0B2A30" }}>Online Assessment</div>
        <div className="space-y-2.5">
          {OA_SUBBARS.map((s, i) => (
            <div key={i} className="relative">
              <div className="relative">
                <Bar pct={s.pct} revealed={revealed} delayMs={`${300 + i * 150}ms`} height={6} />
                {/* Cutoff marker line */}
                <div
                  className="absolute top-[-2px] bottom-[-2px] w-px"
                  style={{ left: `${OA_CUTOFF_PCT}%`, background: "rgba(11,42,48,0.35)" }}
                  aria-hidden="true"
                />
              </div>
              <div
                className="mt-1 inline-flex"
                style={{
                  opacity: revealed ? 1 : 0,
                  transition: "opacity 400ms",
                  transitionDelay: revealed ? `${700 + i * 150}ms` : "0ms",
                }}
              >
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wide"
                  style={
                    s.above
                      ? { background: "var(--pm-lime)", color: "#0B2A30" }
                      : { background: "var(--pm-cream-deep)", color: "#0B2A30" }
                  }
                >
                  {s.above ? "Above cutoff" : "Below cutoff"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PhaseRow({ phase, revealed, delayMs }) {
  const Icon = phase.icon;
  return (
    <div className="flex items-start gap-3 py-3 border-t border-[rgba(15,111,122,0.08)]">
      <div className="w-8 h-8 rounded-lg grid place-items-center shrink-0 mt-0.5" style={{ background: "rgba(15,111,122,0.10)" }}>
        <Icon size={16} style={{ color: "#0F6F7A" }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-display font-semibold text-sm mb-2" style={{ color: "#0B2A30" }}>{phase.label}</div>
        <Bar pct={phase.barPct} revealed={revealed} delayMs={delayMs} />
        {phase.feedback && (
          <p
            className="mt-2 text-xs leading-relaxed"
            style={{
              color: "rgba(11,42,48,0.70)",
              opacity: revealed ? 1 : 0,
              transition: "opacity 500ms",
              transitionDelay: revealed ? "900ms" : "0ms",
            }}
          >
            "You mentioned the project but not how you measured the improvement.
            Walk through the before/after numbers next time."
          </p>
        )}
      </div>
    </div>
  );
}

function ReportCard({ rootRef, revealed }) {
  return (
    <div
      ref={rootRef}
      className="rounded-[28px] bg-white overflow-hidden"
      style={{
        border: "1px solid rgba(15,111,122,0.14)",
        boxShadow: "0 20px 50px rgba(15,111,122,0.14)",
      }}
    >
      {/* Top bar */}
      <div className="flex items-center justify-between px-5 py-3" style={{ background: "var(--pm-sky)" }}>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5" aria-hidden="true">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#0F6F7A" }} />
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: "var(--pm-lime)" }} />
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: "rgba(11,42,48,0.25)" }} />
          </div>
          <span className="font-display font-semibold text-sm" style={{ color: "#0B2A30" }}>Your Placemint report</span>
        </div>
        <span
          className="px-2.5 py-1 rounded-full text-[10px] font-mono uppercase tracking-wide shrink-0"
          style={{ background: "rgba(11,42,48,0.08)", color: "rgba(11,42,48,0.70)" }}
        >
          Illustrative example
        </span>
      </div>

      <div className="px-5 py-2">
        <PhaseRow phase={{ key: "resume", icon: FileCheck2, label: "Resume", barPct: 74 }} revealed={revealed} delayMs="0ms" />
        <OARow revealed={revealed} />
        <PhaseRow
          phase={{ key: "interview", icon: MessageSquareText, label: "Interview", barPct: 62, feedback: true }}
          revealed={revealed}
          delayMs="650ms"
        />
        <PhaseRow phase={{ key: "review", icon: ShieldCheck, label: "Cross-Phase Review", barPct: 78 }} revealed={revealed} delayMs="800ms" />

        {/* Verdict row */}
        <div
          className="mt-3 mb-1 rounded-2xl p-4"
          style={{
            background: "var(--pm-lime)",
            opacity: revealed ? 1 : 0,
            transform: revealed ? "translateY(0)" : "translateY(10px)",
            transition: "opacity 500ms, transform 500ms",
            transitionDelay: revealed ? "950ms" : "0ms",
          }}
        >
          <div className="flex items-center gap-2 font-display font-bold text-sm" style={{ color: "#0B2A30" }}>
            <ShieldCheck size={16} />
            Verdict
          </div>
          <p className="mt-1 text-sm" style={{ color: "rgba(11,42,48,0.80)" }}>
            One narrative of how you performed.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function InsideYourReportSection() {
  const [rootRef, revealed] = useRevealOnView({ threshold: 0.2, fallbackMs: 500 });

  return (
    <section id="inside-your-report" style={{ background: "var(--pm-cream)" }}>
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-24">
        <div className="grid grid-cols-1 lg:grid-cols-[40%_60%] gap-12 items-center">
          <div>
            <div className="pm-eyebrow mb-3" style={{ color: "#0F6F7A" }}>inside your report</div>
            {/* font-weight 300 + letter-spacing -0.02em + line-height
                1.15, matching the site-wide h1/h2 style (HeroV2.jsx's
                h1). Emphasis span: plain teal-deep text, no highlighter
                band (removed from all h1/h2 emphasis, 2026-10). */}
            <h2
              className="font-display font-light text-3xl lg:text-4xl leading-[1.15]"
              style={{ color: "#0B2A30", letterSpacing: "-0.02em" }}
            >
              See{" "}
              <span style={{ color: "#0F6F7A", fontWeight: 600 }}>
                exactly
              </span>{" "}
              where you stand.
            </h2>

            <ul className="mt-6 space-y-3">
              {CHECK_LINES.map((text) => (
                <CheckRow key={text} text={text} />
              ))}
            </ul>

            <Link
              to="/signup"
              className="group inline-flex items-center gap-2 mt-8 px-7 py-3.5 rounded-full font-display font-semibold text-sm text-white transition-transform duration-200 hover:-translate-y-0.5"
              style={{ background: "#0F6F7A" }}
            >
              Get Started Now
              <ArrowRight size={16} className="transition-transform duration-200 group-hover:translate-x-1" />
            </Link>
          </div>

          <div>
            <ReportCard rootRef={rootRef} revealed={revealed} />
            {/* .55 measured ~3.6:1 against a light background elsewhere in
                this same session (ClosingCTASection/SampleRoundBanner) --
                fails AA for small text. .65 clears it, used here from the
                start this time. */}
            <p className="mt-3 text-center text-xs" style={{ color: "rgba(11,42,48,0.65)" }}>
              Illustrative layout, not real results.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
