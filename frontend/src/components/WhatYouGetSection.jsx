import React from "react";
import useRevealOnView from "../hooks/useRevealOnView";

/**
 * "What you get" (Landing.jsx, 2026-10). White section, right after Flow.
 * Structure only, taken from a reference four-card row -- no artwork,
 * copy, logos or text copied from it.
 *
 * Each card's hand-drawn SVG icon was replaced with a full illustration
 * (2026-10) -- the illustration fills the card's top edge-to-edge (the
 * card's own rounded-[24px] + overflow-hidden clips it into the top
 * corners) and supplies its own background colour, so `tint` here is
 * only a same-colour fallback behind the <img> while it loads (avoids a
 * flash of mismatched colour), not a separate decorative box -- matches
 * the colour baked into each SVG exactly, so there's no seam either way.
 */
const ITEMS = [
  {
    key: "engines",
    title: "Company-specific engines",
    desc: "Each company's real section order, timing and gating.",
    tint: "#E3EEF0",
    illustration: "/illustrations/illustration-engines.svg",
  },
  {
    key: "fresh",
    title: "Fresh questions every run",
    desc: "Generated and execution-verified, so no memorised answer sheets.",
    tint: "#EAF9C4",
    illustration: "/illustrations/illustration-fresh-questions.svg",
  },
  {
    key: "interview",
    title: "Adaptive interview",
    desc: "Follows up on vague answers like a real interviewer.",
    tint: "#E8F3FB",
    illustration: "/illustrations/illustration-adaptive-interview.svg",
  },
  {
    key: "report",
    title: "One cross-phase report",
    desc: "Resume, OA and interview tied into a single narrative.",
    tint: "#F2EDDF",
    illustration: "/illustrations/illustration-cross-phase-report.svg",
  },
];

// .pm-card-lift (index.css) -- same hover/focus-within lift as
// DifferentiatorCards.jsx's three cards, shared rather than redefined,
// already reduced-motion safe. Shadow depth is a className (not inline
// style) for the same reason noted there: inline style.boxShadow always
// wins over a stylesheet :hover rule, so a hover className alone
// wouldn't have had any visible effect -- this replaces the old
// onMouseEnter/onMouseLeave JS (imperative, and didn't respect
// prefers-reduced-motion) with the same declarative, shared approach.
function Card({ item }) {
  return (
    <div
      className="pm-card-lift h-full flex flex-col rounded-[24px] overflow-hidden bg-white border border-[rgba(11,42,48,0.08)] pm-card-depth"
    >
      <img
        src={item.illustration}
        alt=""
        loading="lazy"
        className="block w-full object-cover"
        style={{ aspectRatio: "16 / 9", background: item.tint }}
      />
      <div className="px-5 py-6 text-center">
        <div className="font-display font-bold text-base" style={{ color: "#0B2A30" }}>{item.title}</div>
        <p className="mt-2 text-sm leading-relaxed" style={{ color: "rgba(11,42,48,0.70)" }}>{item.desc}</p>
      </div>
    </div>
  );
}

export default function WhatYouGetSection() {
  const [rootRef, revealed] = useRevealOnView({ threshold: 0.2, fallbackMs: 500 });

  return (
    <section
      className="relative"
      style={{
        background: "#FFFFFF",
        borderTopLeftRadius: 56,
        borderTopRightRadius: 56,
        marginTop: -56,
        // 19, not 17 (2026-10 fix) -- this overlaps Flow (Landing.jsx),
        // whose own zIndex was bumped 16->17->18 across two later rounds
        // (Crack Interviews inserted, then moved ahead of Contrarian)
        // without this section being updated to match, leaving it BELOW
        // its own predecessor -- a real stacking bug (Flow's flat edge
        // would've painted over this section's rounded top corners
        // instead of the reverse). 19 clears Flow's 18; StartPractisingSection
        // (next, below) already expected this slot to be taken and sits
        // at 20 now (was 19) to stay ahead of it in turn.
        zIndex: 19,
      }}
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-24">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <div className="pm-eyebrow mb-3" style={{ color: "#0F6F7A" }}>what you get</div>
          {/* font-weight 300 + letter-spacing -0.02em + line-height 1.15,
              matching the site-wide h1/h2 style (HeroV2.jsx's h1). Plain
              teal-deep emphasis text, no highlighter band (removed from
              all h1/h2 emphasis, 2026-10). */}
          <h2
            className="font-display font-light text-4xl lg:text-5xl leading-[1.15]"
            style={{ color: "#0B2A30", letterSpacing: "-0.02em" }}
          >
            Everything a real placement drive{" "}
            <span style={{ color: "#0F6F7A", fontWeight: 600 }}>
              throws at you.
            </span>
          </h2>
        </div>

        {/* grid-cols-1 -> md:grid-cols-2 -> lg:grid-cols-4 (2026-10, was a
            horizontal scroll-snap carousel below sm:640px) -- items-stretch
            (CSS Grid's own default, set explicitly for clarity) plus each
            Card's own h-full keeps all four the same height at every
            width. */}
        <div
          ref={rootRef}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 items-stretch"
        >
          {ITEMS.map((item, i) => (
            <div
              key={item.key}
              className="h-full"
              style={{
                opacity: revealed ? 1 : 0,
                transform: revealed ? "translateY(0)" : "translateY(16px)",
                transition: "opacity 500ms, transform 500ms",
                transitionDelay: revealed ? `${i * 100}ms` : "0ms",
              }}
            >
              <Card item={item} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
