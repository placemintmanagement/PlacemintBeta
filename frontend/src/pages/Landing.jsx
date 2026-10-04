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
import FaqSection from "../components/FaqSection";
import DepartmentCard from "../components/DepartmentCard";
import IDEMockup from "../components/IDEMockup";
import Reveal from "../components/Reveal";
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
          // Soft shadow along the rounded top: the grey section above is close
          // in tone to this cream, so without it the curve reads as flat.
          boxShadow: "0 -10px 24px -14px rgba(7,59,67,0.18)",
          marginTop: -56,
          zIndex: 17,
        }}
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-28">
          <Reveal>
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
          </Reveal>
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
        <div className="relative max-w-[1240px] mx-auto px-6 lg:px-10 py-28">
          <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-x-10 lg:gap-y-0">
            {/* Row 1: eyebrow, heading, sentence. Row 2: step card and image
                share a row, so the image lines up with the four phases. */}
            <Reveal className="text-center lg:col-span-2 lg:row-start-1 lg:-mt-6">
              <div className="pm-eyebrow mb-2" style={{ color: "#0F6F7A" }}>the flow</div>
              <h2 className="font-display font-light text-4xl lg:text-6xl leading-[1.15]" style={{ color: "#0B2A30", letterSpacing: "-0.02em" }}>
                Four phases.{" "}
                <span style={{ color: "#0F6F7A", fontWeight: 600 }}>
                  One story.
                </span>
              </h2>
              <p className="mt-3 mx-auto" style={{ fontSize: 17, lineHeight: 1.6, color: "rgba(11,42,48,0.75)", maxWidth: "52ch" }}>Every phase feeds the next, so you get one story of how you performed, not four separate scores.</p>
            </Reveal>
            <div className="lg:col-start-1 lg:row-start-2">
              <PhaseStrip />
            </div>
            {/* Student illustration: background baked in at #E8F3FB, same as
                this section, so the image edge is invisible. Below 1024px it
                drops under the step list, centred. */}
            <div className="lg:col-start-2 lg:row-start-2 lg:self-stretch lg:relative">
              <img
                src="/illustrations/flow-hero.svg"
                alt=""
                width={1162}
                height={1128}
                loading="lazy"
                className="mx-auto mt-8 block h-auto w-auto max-w-[420px] lg:absolute lg:top-[calc(52px+(100%-52px)/2)] lg:left-full lg:-translate-x-full lg:-translate-y-1/2 lg:h-[calc((100%-52px)*1.12)] lg:mt-0 lg:max-w-none"

              />
            </div>
          </div>
        </div>
      </section>

      <WhatYouGetSection />

      <StartPractisingSection />

      {/* Feature bento (2026-10 redesign). Both neighbours (StartPractising
          above, InsideYourReport below) are cream, so this section is white
          and the 56px shelf radius marks its edge. The IDE mock sits on a
          sky-deep stage as the visual centre; cards keep the standard border
          and shadow. */}
      <section
        className="relative"
        style={{
          background: "#FFFFFF",
          borderTopLeftRadius: 56,
          borderTopRightRadius: 56,
          marginTop: -56,
          zIndex: 21,
        }}
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-28">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 flex flex-col gap-6">
              <Reveal>
                <div className="pm-eyebrow mb-3" style={{ color: "#0F6F7A" }}>what the OA actually looks like</div>
                <h3 className="font-display font-light" style={{ color: "#0B2A30", fontSize: "clamp(1.75rem, 3vw, 2.5rem)", lineHeight: 1.15, letterSpacing: "-0.02em" }}>
                  A real split-panel coding IDE, <span style={{ fontWeight: 600, color: "#0F6F7A" }}>not a textarea.</span>
                </h3>
                <p className="mt-3" style={{ fontSize: 17, lineHeight: 1.6, color: "rgba(11,42,48,0.75)", maxWidth: "62ch" }}>Same split-panel layout used by HackerRank &amp; LeetCode: problem on the left, dark editor on the right.</p>
              </Reveal>
              <Reveal delay={150}>
                <IDEMockup />
              </Reveal>
            </div>

            {/* Tall card: text on top, illustration anchored to its bottom edge. */}
            <div className="pm-card-lift relative overflow-hidden flex flex-col gap-6 lg:gap-0 h-full rounded-[24px] p-7" style={{ background: "#E8F3FB", border: "1px solid rgba(7,59,67,0.08)", boxShadow: "0 14px 28px -18px rgba(7,59,67,0.28)" }}>
              <div className="relative z-10 flex flex-col gap-4">
                <div className="w-11 h-11 rounded-[14px] grid place-items-center shrink-0" style={{ background: "var(--pm-teal-deep)", color: "#FFFFFF" }}><Code2 size={22} aria-hidden="true" /></div>
                <h4 className="font-display font-semibold" style={{ fontSize: 22, lineHeight: 1.2, color: "#0B2A30" }}>LeetCode-style coding rounds</h4>
                <p style={{ fontSize: 15, lineHeight: 1.6, color: "rgba(11,42,48,0.75)" }}>Split-panel IDE, dark editor on a light page. 2 visible tests. 3 hidden tests unlocked on Submit. Write in Python, JS, C, C++, Java.</p>
              </div>
              <img src="/illustrations/student-laptop.svg" alt="" width={1024} height={768} loading="lazy" className="relative mt-auto mx-auto block w-auto max-h-[220px] lg:absolute lg:bottom-0 lg:left-0 lg:mt-0 lg:mx-0 lg:max-h-none lg:w-full lg:h-auto" />
            </div>

            <div className="pm-card-lift relative flex flex-col gap-4 h-full rounded-[24px] p-7" style={{ background: "#FFFFFF", border: "1px solid rgba(7,59,67,0.08)", boxShadow: "0 14px 28px -18px rgba(7,59,67,0.28)" }}>
              <div className="w-11 h-11 rounded-[14px] grid place-items-center shrink-0" style={{ background: "var(--pm-teal-deep)", color: "#FFFFFF" }}><FileCheck2 size={22} aria-hidden="true" /></div>
              <h4 className="font-display font-semibold" style={{ fontSize: 22, lineHeight: 1.2, color: "#0B2A30" }}>Resume checker, free forever</h4>
              <p style={{ fontSize: 15, lineHeight: 1.6, color: "rgba(11,42,48,0.75)" }}>Uploads once, gets analysed against <em>this</em> company &amp; <em>this</em> role. Strengths, weaknesses, fit score, projects extracted. No credit card needed.</p>
            </div>

            <div className="pm-card-lift relative flex flex-col gap-4 h-full rounded-[24px] p-7" style={{ background: "#FFFFFF", border: "1px solid rgba(7,59,67,0.08)", boxShadow: "0 14px 28px -18px rgba(7,59,67,0.28)" }}>
              <div className="w-11 h-11 rounded-[14px] grid place-items-center shrink-0" style={{ background: "var(--pm-lime)", color: "var(--pm-ink)" }}><MessageSquareText size={22} aria-hidden="true" /></div>
              <h4 className="font-display font-semibold" style={{ fontSize: 22, lineHeight: 1.2, color: "#0B2A30" }}>Adaptive interview</h4>
              <p style={{ fontSize: 15, lineHeight: 1.6, color: "rgba(11,42,48,0.75)" }}>2 DSA + 2 project questions from your actual resume + 3 CS fundamentals. Follows up on vague answers like a real interviewer.</p>
            </div>

            <div className="pm-card-lift relative flex flex-col gap-4 h-full rounded-[24px] p-7" style={{ background: "#FFFFFF", border: "1px solid rgba(7,59,67,0.08)", boxShadow: "0 14px 28px -18px rgba(7,59,67,0.28)" }}>
              <div className="w-11 h-11 rounded-[14px] grid place-items-center shrink-0" style={{ background: "var(--pm-teal-deep)", color: "#FFFFFF" }}><ShieldCheck size={22} aria-hidden="true" /></div>
              <h4 className="font-display font-semibold" style={{ fontSize: 22, lineHeight: 1.2, color: "#0B2A30" }}>Sectional cutoffs, honest verdicts</h4>
              <p style={{ fontSize: 15, lineHeight: 1.6, color: "rgba(11,42,48,0.75)" }}>If Infosys wants 65% in pseudocode, you&apos;ll get eliminated at 64%. If it&apos;s blended, we tell you which section dragged you down.</p>
            </div>

            <div className="pm-card-lift relative flex flex-col gap-4 h-full rounded-[24px] p-7" style={{ background: "#FFFFFF", border: "1px solid rgba(7,59,67,0.08)", boxShadow: "0 14px 28px -18px rgba(7,59,67,0.28)" }}>
              <div className="w-11 h-11 rounded-[14px] grid place-items-center shrink-0" style={{ background: "var(--pm-teal-deep)", color: "#FFFFFF" }}><Zap size={22} aria-hidden="true" /></div>
              <h4 className="font-display font-semibold" style={{ fontSize: 22, lineHeight: 1.2, color: "#0B2A30" }}>One report, not four</h4>
              <p style={{ fontSize: 15, lineHeight: 1.6, color: "rgba(11,42,48,0.75)" }}>The final report ties resume, OA, and interview into a single narrative, written by our premium AI tier, the one place we don&apos;t downgrade.</p>
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
      {/* Departments (2026-10 redesign). Sky, not cream: the section above
          (InsideYourReport) is cream. Live department on the left, Coming Soon
          cards in a 2x2 grid on the right. Keeps id="companies" (in-page links). */}
      <section
        id="companies"
        className="relative"
        style={{
          background: "#FFFFFF",
          borderTopLeftRadius: 56,
          borderTopRightRadius: 56,
          marginTop: -56,
          zIndex: 22,
        }}
      >
        <div className="max-w-[1200px] mx-auto px-6 lg:px-10 py-14 lg:py-20">
          <Reveal>
            <div className="pm-eyebrow mb-3" style={{ color: "#0F6F7A" }}>5 engineering departments</div>
            <h2 className="font-display font-light" style={{ color: "#0B2A30", fontSize: "clamp(32px, 4vw, 48px)", lineHeight: 1.15, letterSpacing: "-0.02em" }}>
              Pick your <span style={{ fontWeight: 600, color: "#0F6F7A" }}>branch</span>, then your track.
            </h2>
            <p className="mt-3" style={{ fontSize: 17, lineHeight: 1.6, color: "rgba(11,42,48,0.75)" }}>Start your prep now.</p>
          </Reveal>
          <Reveal delay={150} data-testid={TID.departmentGrid} className="mt-10 grid grid-cols-1 gap-6 lg:grid-cols-[5fr_7fr]">
            <div className="flex flex-col gap-6">
              {departments.filter(d => d.active).map(d => <DepartmentCard key={d.id} department={d} />)}
            </div>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 sm:auto-rows-fr">
              {departments.filter(d => !d.active).map(d => <DepartmentCard key={d.id} department={d} />)}
            </div>
          </Reveal>
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
      <FaqSection />

      {/* Closing CTA -- back at the very end, just above the footer
          (2026-10, was briefly mid-page after Inside your report). Sky
          background, same rounded-shelf overlap into FAQ's teal (page
          gradient) that it always used, just now overlapping a different
          predecessor. */}
      <ClosingCTASection />

      <Reveal>
        <Footer />
      </Reveal>
    </div>
  );
}


