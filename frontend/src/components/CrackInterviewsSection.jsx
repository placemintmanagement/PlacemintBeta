import React from "react";
import useRevealOnView from "../hooks/useRevealOnView";

/**
 * "Crack interviews at" -- a text-only wall of company names, directly
 * under the hero and above the cream "What makes this different"
 * section (Landing.jsx). No logos, no brand colours/fonts, no results
 * claims (2026-10 spec) -- see the CHECKS section of the task this was
 * built from: a grep for forbidden wording and for any logo <img> is
 * part of verifying this file, not just writing it.
 *
 * Sitting directly under the hero means this section owns the hero's
 * own straddling <Tray /> seam (HeroV2.jsx) -- its top padding has to
 * clear the Tray cards, not just look nice. That clearance math (and
 * its exact pt values) moved over wholesale from the Contrarian section
 * when this was repositioned ahead of it (2026-10) -- see the padding
 * comment below for the full derivation.
 *
 * Edit these two to move a company from "coming next" to "live", or to
 * add/remove one. COMING_NEXT = [] (every company live) must still look
 * balanced -- centred + flex-wrap handles that with no separate empty
 * state needed, verified by temporarily emptying it during this round's
 * verification pass.
 */
const LIVE_COMPANIES = ["Capgemini"];
const COMING_NEXT = [
  "TCS", "Infosys", "Wipro", "Cognizant", "Accenture", "IBM",
  "HCLTech", "LTIMindtree", "Tech Mahindra", "Zoho", "Deloitte",
];

function LiveDot({ size = 8 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 8 8" aria-hidden="true" className="shrink-0">
      <circle cx="4" cy="4" r="3" fill="#C6F24E" stroke="#073B43" strokeWidth="2" />
    </svg>
  );
}

export default function CrackInterviewsSection() {
  const [rootRef, revealed] = useRevealOnView({ threshold: 0.2, fallbackMs: 500 });
  const allNames = [
    ...LIVE_COMPANIES.map((name) => ({ name, live: true })),
    ...COMING_NEXT.map((name) => ({ name, live: false })),
  ];

  return (
    <section
      // NOT id="companies" (spec's literal ask) -- that id already belongs
      // to the Departments grid further down (Landing.jsx) and is live
      // navigation: Header's "Companies" nav link, Footer's "14
      // Companies" link, Dashboard's "start new" link, and
      // StartPractisingSection's first card all point at /#companies
      // expecting the real department/company browser. A second element
      // with the same id would make getElementById (and every one of
      // those links) resolve to whichever is first in the DOM -- this
      // section -- silently redirecting all of them away from Departments.
      id="crack-interviews"
      ref={rootRef}
      className="relative"
      style={{
        background: "var(--pm-grey)",
        // Same rounded-shelf mechanism as every other section seam on
        // this page (see HeroV2.jsx's comment on why a direct colour
        // blend goes muddy) -- 56px radius pulled up -56px into the
        // hero's own bottom padding. z-index 16: clears the hero itself
        // (effectively z:auto/0) trivially, but more importantly stays
        // BELOW the hero's own <Tray /> (z-index 25, HeroV2.jsx) so the
        // Tray cards keep painting on top of this section's shelf where
        // they straddle the seam, not behind it. Contrarian (below) was
        // bumped from zIndex 15 to 17 so ITS shelf, which now overlaps
        // into THIS section instead of the hero directly, still paints
        // on top the same way.
        borderTopLeftRadius: 56,
        borderTopRightRadius: 56,
        marginTop: -56,
        zIndex: 16,
      }}
    >
      {/* pt-[840px] lg:pt-[262px] -- moved over from the Contrarian
          section when this was repositioned directly under the hero
          (2026-10); the underlying seam geometry is identical regardless
          of which section sits here, so the same numbers apply unchanged.
          Both account for this section's own -56px shelf offset
          (marginTop, above): its rendered top sits 56px ABOVE its
          in-flow position, i.e. 56px closer to the Tray than a naive
          "half tray height + 56" would assume.
          Desktop/lg (Tray centred on the seam, ~298px tall, measured):
          tray bottom sits 149 - 56 = 93px into this section before any
          padding; spec wants >=56px clear below that, so
          pt >= 93 + 56 = 149 -- measured empirically at pt-[260px] the
          real clearance was 55px (1px under spec), so this is 262px,
          independently verified via Playwright at 1440x900 and 1024x768.
          Mobile (Tray's TOP anchored 48px above the seam, not centred --
          see HeroV2.jsx <Tray />; measured tray height 766px at 390px
          width): tray bottom sits (766-48) - 56 = 662px into this
          section before padding; pt >= 662 + 56 = 718 minimum -- 840px
          leaves a verified margin instead of sitting right at it. Both
          values confirmed via direct DOM measurement
          (getBoundingClientRect), not just this arithmetic. */}
      <div className="max-w-5xl mx-auto px-6 lg:px-10 pt-[840px] lg:pt-[262px] pb-24 lg:pb-28 text-center">
        {/* Weight 300/600 split (2026-10, was 400/700) -- matches the
            site-wide h1/h2 "display heading" style (HeroV2.jsx's h1 is
            the reference). "Crack" moved from muted (ink 70%) to full
            ink too, per the same system's "ink everywhere except hero/
            footer" base heading colour rule. */}
        <h2
          className="font-display font-light leading-[1.15]"
          style={{
            fontSize: "clamp(1.75rem, 3.2vw, 2.5rem)",
            letterSpacing: "-0.02em",
            opacity: revealed ? 1 : 0,
            transform: revealed ? "none" : "translateY(12px)",
            transition: "opacity 500ms ease-out, transform 500ms ease-out",
          }}
        >
          <span style={{ fontWeight: 300, color: "#0B2A30" }}>Crack </span>
          <span style={{ fontWeight: 600, color: "#0F6F7A" }}>interviews at</span>
        </h2>

        <div
          className="mt-12 flex flex-wrap justify-center max-w-[1100px] mx-auto"
          style={{ rowGap: 20, columnGap: 44 }}
        >
          {allNames.map((c, i) => (
            <span
              key={c.name}
              className={`inline-flex items-center gap-2 font-display font-bold transition-colors duration-200 ${
                c.live ? "" : "cursor-default hover:text-[rgba(11,42,48,0.70)] focus-visible:text-[rgba(11,42,48,0.70)]"
              }`}
              style={{
                fontSize: "clamp(1.15rem, 2vw, 1.7rem)",
                letterSpacing: "-0.01em",
                // Live: full-strength ink. Coming next: spec asked for
                // ink at 40%, measured at 2.39:1 on white -- fails AA
                // even against the relaxed 3:1 "large text" threshold
                // (and this text is borderline large-text size to begin
                // with: clamp()'s floor, 18.4px, sits just under the
                // 18.66px/14pt-bold cutoff). .65 clears normal-text AA
                // outright: 4.88:1.
                color: c.live ? "#0B2A30" : "rgba(11,42,48,0.65)",
                opacity: revealed ? 1 : 0,
                transform: revealed ? "none" : "translateY(8px)",
                transitionProperty: "opacity, transform",
                transitionDuration: "400ms",
                // Names start after the heading's own 500ms fade (spec:
                // heading first, THEN names), then stagger 40ms apart.
                transitionDelay: revealed ? `${400 + i * 40}ms` : "0ms",
              }}
            >
              {c.live && <LiveDot />}
              {c.name}
            </span>
          ))}
        </div>

        {/* .60 (spec) measured 4.18:1 on white -- fails AA for 13px/12px
            text, same issue hit and fixed the same way earlier this
            session (the seam cards' label text). .70 clears it: 5.73:1. */}
        <div
          className="mt-8 flex items-center justify-center flex-wrap gap-x-6 gap-y-2"
          style={{ fontSize: 13, color: "rgba(11,42,48,0.70)" }}
        >
          <span className="inline-flex items-center gap-1.5">
            <LiveDot /> Live now
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="font-display font-bold" style={{ color: "rgba(11,42,48,0.65)" }}>Company</span>
            Rolling out next
          </span>
        </div>

        <p className="mt-4" style={{ fontSize: 12, color: "rgba(11,42,48,0.70)" }}>
          Company names are trademarks of their respective owners. Placemint is not
          affiliated with or endorsed by them.
        </p>
      </div>
    </section>
  );
}
