import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import PhaseStrip from "../components/PhaseStrip";
import CrackInterviewsSection from "../components/CrackInterviewsSection";
import DifferentiatorCards from "../components/DifferentiatorCards";
import WhatYouGetSection from "../components/WhatYouGetSection";
import ChooseCompanySection from "../components/ChooseCompanySection";
import InsideYourReportSection from "../components/InsideYourReportSection";
import StartPractisingSection from "../components/StartPractisingSection";
import ClosingCTASection from "../components/ClosingCTASection";
import DepartmentCard from "../components/DepartmentCard";
import IDEMockup from "../components/IDEMockup";
import Footer from "../components/Footer";
import HeroV2 from "../components/HeroV2";
import { TID } from "../testIds";
import { SHOW_PRICING, SHOW_COMPANY_GRID } from "../featureFlags";
import { ShieldCheck, Zap, MessageSquareText, FileCheck2, Code2 } from "lucide-react";

export default function Landing() {
  const [departments, setDepartments] = useState([]);
  const [plans, setPlans] = useState([]);

  useEffect(() => {
    api.get("/departments").then(r => setDepartments(r.data.departments)).catch(() => {});
    if (SHOW_PRICING) {
      api.get("/pricing").then(r => setPlans(r.data.plans)).catch(() => {});
    }
  }, []);

  return (
    <div className="min-h-screen">
      <HeroV2 />

      {/* "Crack interviews at" -- directly under the hero now (2026-10,
          moved ahead of Contrarian/"What makes this different" per
          explicit instruction). Because this is now HeroV2's immediate
          next sibling, it owns the hero's own straddling <Tray /> seam:
          its own top padding/shelf/z-index are sized to clear the Tray
          cards instead of Contrarian's -- see CrackInterviewsSection.jsx
          for that geometry (same numbers Contrarian used to carry, moved
          over wholesale since the underlying seam math is identical
          regardless of which section sits here). */}
      <CrackInterviewsSection />

      {/* What makes this different -- cream section (2026-10, was solid
          white). Cream is an allowed token now, but only for light
          sections like this one, never the page background or text. Part
          of the alternating rhythm so no two adjacent sections share a
          background: hero(teal) -> CrackInterviews(white) -> this(cream)
          -> Flow(sky) -> bento(white) -> departments(white) -> pricing
          (white) -> FAQ(cream) -> footer(dark). No longer directly under
          the hero (2026-10) -- CrackInterviewsSection is -- so this no
          longer needs the oversized top padding that used to clear the
          hero's straddling Tray cards; back to a plain py-28. Lime text
          is unreadable on a light background, so "real pressure" is a
          lime HIGHLIGHTER strip behind dark text instead of lime text.
          The trailing period is INSIDE the highlight span -- the span's
          own right padding was creating a visible gap between
          "pressure" and the period, reading as detached. */}
      <section
        id="different"
        className="relative"
        style={{
          background: "var(--pm-cream)",
          // Rounded "shelf" overlapping up into CrackInterviewsSection's
          // own bottom padding (56px radius, 56px overlap). zIndex 17
          // (was 15, when this sat directly under the hero): now
          // overlaps CrackInterviewsSection (white, zIndex 16) instead
          // of the hero directly, so needs to clear ITS zIndex, one
          // higher.
          borderTopLeftRadius: 56,
          borderTopRightRadius: 56,
          marginTop: -56,
          zIndex: 17,
        }}
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-28">
          <div className="pm-eyebrow mb-3" style={{ color: "#0F6F7A" }}>what makes this different</div>
          {/* font-weight 300 + letter-spacing -0.02em + line-height 1.15
              is the shared h1/h2 "display heading" style (2026-10) --
              see HeroV2.jsx's h1 for the reference definition. Emphasis
              phrase: 600 weight, --pm-teal-deep text, no background --
              the lime highlighter band was removed from all h1/h2
              emphasis (2026-10); it stays on the paragraph's "real
              pressure." pill below (not a heading, out of scope). */}
          <h2
            className="font-display font-light text-4xl lg:text-6xl leading-[1.15] max-w-4xl"
            style={{ color: "#0B2A30", letterSpacing: "-0.02em" }}
          >
            Every company tests{" "}
            <span style={{ color: "#0F6F7A", fontWeight: 600 }}>
              differently.
            </span>
          </h2>
          <p className="mt-4 max-w-2xl text-lg font-normal leading-relaxed" style={{ color: "rgba(11,42,48,0.70)" }}>
            Real order, real cutoffs, <span style={{ background: "var(--pm-lime)", color: "#0B2A30", borderRadius: 6, padding: "0 6px", fontWeight: 600 }}>real pressure.</span>
          </p>
          <DifferentiatorCards />
        </div>
      </section>

      {/* The Flow -- the phase strip (components/PhaseStrip.jsx) replaces
          the old dashed-line carousel entirely. Light sky-blue background
          (2026-10, was solid dark teal #0A4A53) -- both neighbours
          (Contrarian/cream above, StartPractising/cream below) are light
          now too, so a 1px --pm-sky-deep edge on top/bottom gives a
          little definition where two pale tones meet, on top of the
          existing rounded-shelf geometry (56px top radius, pulled up
          -56px into the cream section above, stacked via z-index --
          crisp colour edge, no linear-gradient blend: see HeroV2.jsx's
          comment on why a direct cream/teal-style blend goes muddy).
          Heading left / subline right. 112px vertical padding (py-28),
          mb-20 before the strip keeps ~80-120px of breathing room above
          it too. zIndex 18 (was 17): overlaps Contrarian, now zIndex 17
          (was 15, before CrackInterviewsSection was inserted ahead of
          it) -- needs to clear that, one higher. */}
      <section
        id="pipeline"
        className="relative"
        style={{
          background: "var(--pm-sky)",
          borderTopLeftRadius: 56,
          borderTopRightRadius: 56,
          borderTop: "1px solid var(--pm-sky-deep)",
          borderBottom: "1px solid var(--pm-sky-deep)",
          marginTop: -56,
          zIndex: 18,
        }}
      >
        <div className="relative max-w-7xl mx-auto px-6 lg:px-10 py-28">
          <div className="mb-20 flex items-end justify-between flex-wrap gap-4">
            <div>
              <div className="pm-eyebrow mb-2" style={{ color: "#0F6F7A" }}>the flow</div>
              <h2 className="font-display font-light text-4xl lg:text-5xl leading-[1.15]" style={{ color: "#0B2A30", letterSpacing: "-0.02em" }}>
                4 phases.{" "}
                <span style={{ color: "#0F6F7A", fontWeight: 600 }}>
                  One story.
                </span>
              </h2>
            </div>
            <p className="max-w-sm" style={{ color: "rgba(11,42,48,0.70)" }}>Every phase feeds the next, so you get one story of how you performed, not four separate scores.</p>
            {/* Side panel, hidden below 1024px. Same colour as this section,
                so the 1px control-edge border keeps the panel readable. */}
            <div className="hidden lg:block shrink-0 overflow-hidden" style={{ width: 240, borderRadius: 24, background: "#E8F3FB", border: "1px solid rgba(7,59,67,0.08)" }}>
              <img src="/illustrations/student-laptop.svg" alt="" width={2048} height={1509} className="block w-full h-auto" />
            </div>
          </div>
          <PhaseStrip />
        </div>
      </section>

      <WhatYouGetSection />

      <StartPractisingSection />

      {/* Feature bento -- white. Order (2026-10): WhatYouGet -> this pair
          (StartPractising + bento, unchanged relative to each other) ->
          InsideYourReport -> ClosingCTA -> departments. */}
      <section style={{ background: "#FFFFFF" }}>
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-28">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 flex flex-col gap-4">
              <div className="flex items-end justify-between flex-wrap gap-3">
                <div>
                  <div className="pm-eyebrow mb-2" style={{ color: "#0F6F7A" }}>what the OA actually looks like</div>
                  <h3 className="font-display text-2xl lg:text-3xl font-bold" style={{ color: "#0B2A30" }}>A real split-panel coding IDE, not a textarea.</h3>
                </div>
                <div className="text-sm max-w-xs" style={{ color: "rgba(11,42,48,0.70)" }}>Same split-panel layout used by HackerRank &amp; LeetCode: problem on the left, dark editor on the right.</div>
              </div>
              <IDEMockup />
            </div>

            <div className="pm-card p-8 flex flex-col gap-4">
              <div className="w-10 h-10 rounded-lg bg-pm-primary/10 text-pm-primary-dark grid place-items-center"><Code2 /></div>
              <h4 className="font-display text-xl font-bold">LeetCode-style coding rounds</h4>
              <p className="text-pm-text2 text-sm">Split-panel IDE, dark editor on a light page. 2 visible tests. 3 hidden tests unlocked on Submit. Write in Python, JS, C, C++, Java.</p>
            </div>

            <div className="pm-card p-8 flex flex-col gap-4">
              <div className="w-10 h-10 rounded-lg bg-pm-primary/10 text-pm-primary-dark grid place-items-center"><FileCheck2 /></div>
              <h4 className="font-display text-xl font-bold">Resume checker, free forever</h4>
              <p className="text-pm-text2 text-sm">Uploads once, gets analysed against <em>this</em> company &amp; <em>this</em> role. Strengths, weaknesses, fit score, projects extracted. No credit card needed.</p>
            </div>

            <div className="pm-card p-8 flex flex-col gap-4">
              <div className="w-10 h-10 rounded-lg grid place-items-center" style={{ background: "var(--pm-lime)", color: "var(--pm-ink)" }}><MessageSquareText /></div>
              <h4 className="font-display text-xl font-bold">Adaptive interview</h4>
              <p className="text-pm-text2 text-sm">2 DSA + 2 project questions from your actual resume + 3 CS fundamentals. Follows up on vague answers like a real interviewer.</p>
            </div>

            <div className="pm-card p-8 flex flex-col gap-4">
              <div className="w-10 h-10 rounded-lg bg-pm-primary/10 text-pm-primary-dark grid place-items-center"><ShieldCheck /></div>
              <h4 className="font-display text-xl font-bold">Sectional cutoffs, honest verdicts</h4>
              <p className="text-pm-text2 text-sm">If Infosys wants 65% in pseudocode, you'll get eliminated at 64%. If it's blended, we tell you which section dragged you down.</p>
            </div>

            <div className="pm-card p-8 flex flex-col gap-4">
              <div className="w-10 h-10 rounded-lg grid place-items-center" style={{ background: "rgba(42,154,163,0.14)", color: "#2A9AA3" }}><Zap /></div>
              <h4 className="font-display text-xl font-bold">One report, not four</h4>
              <p className="text-pm-text2 text-sm">The final report ties resume, OA, and interview into a single narrative, written by our premium AI tier, the one place we don't downgrade.</p>
            </div>
          </div>
        </div>
      </section>

      {/* "Choose your company" is hidden for now (2026-10, see
          featureFlags.js) -- "Inside your report" takes its slot instead.
          The component itself is untouched, not deleted, so flipping
          SHOW_COMPANY_GRID back to true brings it straight back. It has
          no id/anchor and nothing else in the app links to it. */}
      {SHOW_COMPANY_GRID && <ChooseCompanySection />}
      <InsideYourReportSection />

      {/* Departments grid -- white (2026-10, back from cream): the closing
          CTA no longer sits between this and InsideYourReportSection (it
          moved to the very end of the page, just above the footer -- see
          below), so this and InsideYourReportSection became directly
          adjacent. Both were cream, which would have broken the "no two
          adjacent sections share a background" rule, so this reverted to
          white (a flat edge against cream is fine, same reasoning as
          bento above). */}
      <section id="companies" style={{ background: "#FFFFFF" }}>
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-28">
          <div className="mb-8 flex items-end justify-between flex-wrap gap-4">
            <div>
              <div className="pm-eyebrow mb-2" style={{ color: "#0F6F7A" }}>5 engineering departments</div>
              <h2 className="font-display font-bold text-3xl lg:text-4xl" style={{ color: "#0B2A30" }}>Pick your <em>branch</em>, then your track.</h2>
            </div>
            <p className="max-w-md text-sm" style={{ color: "rgba(11,42,48,0.70)" }}>Start your prep now.</p>
          </div>
          <div data-testid={TID.departmentGrid} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {departments.map(d => <DepartmentCard key={d.id} department={d} />)}
          </div>
        </div>
      </section>

      {/* Pricing -- hidden for now (2026-10, see featureFlags.js). Kept
          in place, not deleted, so SHOW_PRICING = true brings it straight
          back; the /pricing route/page are untouched either way. */}
      {SHOW_PRICING && (
      <section id="pricing" style={{ background: "#FFFFFF" }}>
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-28">
          <div className="mb-6">
            <div className="pm-eyebrow mb-2" style={{ color: "#0F6F7A" }}>pricing</div>
            <h2 className="font-display font-bold text-3xl lg:text-4xl" style={{ color: "#0B2A30" }}>Pay for reps, not marketing fluff.</h2>
          </div>

          {/* Explainer strip — removes any ambiguity about what "1 run" means. */}
          <div className="pm-card p-5 mb-8 flex flex-wrap items-center gap-x-8 gap-y-3">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-widest text-pm-primary-dark">what counts as 1 run</div>
              <div className="font-display font-bold text-lg">1 company · OA + Interview + Report</div>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="pm-chip">✓ Full OA (all sections)</span>
              <span className="pm-chip">✓ Adaptive interview</span>
              <span className="pm-chip">✓ Final cross-phase report</span>
              <span className="pm-chip pm-chip-primary">Resume Checker is always free</span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {plans.map(p => (
              <div key={p.id} data-testid={TID.pricingPlan(p.id)}
                   className={`pm-card p-6 flex flex-col ${p.highlight ? "shadow-[0_20px_60px_-30px_rgba(198,242,78,0.6)] scale-[1.02]" : ""}`}
                   style={p.highlight ? { borderColor: "var(--pm-lime)" } : undefined}>
                {p.highlight && <span className="pm-chip pm-chip-lime self-start mb-3">Most picked</span>}
                <div className="font-display text-xl font-bold">{p.name}</div>
                <div className="mt-2 font-mono text-3xl font-bold">
                  {p.price === 0 ? "₹0" : <>₹{p.price}</>}
                  <span className="text-sm font-normal text-pm-text2 ml-1">{p.id === "basic" || p.id === "pro" ? "/mo" : (p.id === "free" ? "" : " one-time")}</span>
                </div>
                <div className="mt-1 font-mono text-xs text-pm-text2">{p.companies} co • {p.runs} runs</div>
                <ul className="mt-4 space-y-1.5 text-sm text-pm-text2">
                  {p.features.map((f, i) => <li key={i} className="flex gap-2"><span className="text-pm-primary">✓</span>{f}</li>)}
                </ul>
                <Link to="/pricing" data-testid={TID.pricingSelect(p.id)} className={`mt-6 pm-btn ${p.highlight ? "pm-btn-primary" : "pm-btn-ghost"} text-sm py-2`}>{p.cta}</Link>
              </div>
            ))}
          </div>
        </div>
      </section>
      )}

      {/* FAQ -- sky blue (2026-10, was cream, was teal via the page
          gradient before that). White on both sides (departments above,
          ClosingCTASection below) -- a flat edge against white is fine,
          same reasoning used elsewhere for white/light pairings. Heading
          flipped from white to ink since it's no longer on a dark
          background. */}
      <section id="faq" style={{ background: "var(--pm-sky)" }}>
        <div className="max-w-4xl mx-auto px-6 lg:px-10 py-28">
          <h2 className="font-display font-bold text-3xl lg:text-4xl mb-6" style={{ color: "#0B2A30" }}>Questions people actually ask</h2>
          <div className="space-y-3">
            {FAQ.map((f, i) => (
              <details key={i} className="pm-card p-5 group open:shadow-md">
                <summary className="cursor-pointer font-display font-semibold text-lg list-none flex justify-between items-center">
                  {f.q}
                  <span className="text-pm-primary group-open:rotate-45 transition-transform text-xl leading-none">+</span>
                </summary>
                <div className="mt-3 text-pm-text2 leading-relaxed text-sm">{f.a}</div>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* Closing CTA -- back at the very end, just above the footer
          (2026-10, was briefly mid-page after Inside your report). Sky
          background, same rounded-shelf overlap into FAQ's teal (page
          gradient) that it always used, just now overlapping a different
          predecessor. */}
      <ClosingCTASection />

      <Footer />
    </div>
  );
}

const FAQ = [
  { q: "How is this different from any other mock-test website?", a: "Each of the 14 tracks runs its own real section order, timing, and cutoff logic. Infosys' pseudocode round has a 65% cutoff. Wipro's essay is a real elimination gate. Zoho runs a 3-round marathon: pen-paper aptitude, then 5 basic programs, then advanced DSA. Not a shared template." },
  { q: "Why is the resume checker free?", a: "Because it's the least AI-heavy part and it's how we earn trust. You upload once, an AI reads it against the company/role you picked, you get honest strengths/weaknesses. No credit card, ever." },
  { q: "Do I need to pay to try?", a: "No. Free tier gives you 3 full runs during our launch window. That's enough to get through 3 companies end-to-end: resume, OA, interview, and final report." },
  { q: "Which languages do the coding rounds support?", a: "Python, JavaScript, C, C++, and Java all run live in the browser, same as HackerRank's model. Every submission is executed against 2 visible + 3 hidden test cases." },
  { q: "Is the AI grading actually good?", a: "For OA sections we use structured JSON outputs, so grading is deterministic, not \"vibes\" grading. The final cross-phase report uses our premium AI tier because that's the one part where the extra reasoning is worth it." },
];
