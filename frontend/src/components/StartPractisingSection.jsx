import React from "react";
import { Link } from "react-router-dom";
import useRevealOnView from "../hooks/useRevealOnView";

/**
 * "Pick your starting point." (Landing.jsx, 2026-10). Structure only, taken
 * from a reference three-card action row (illustrated top area + darker
 * footer CTA bar) -- no artwork, icons, copy or colours copied from it.
 * Every illustration below is hand-built from basic SVG shapes (rects,
 * circles), nothing imported from an icon set or any third party.
 */
const CARDS = [
  {
    key: "company",
    title: "Practice by company",
    desc: "Browse every company and pick the one you're prepping for.",
    to: "/#companies",
    topBg: "var(--pm-teal-deep)",
    footerBg: "#0A4A53",
    footerText: "#FFFFFF",
    Illustration: () => (
      <svg viewBox="0 0 120 80" width="64" height="44" aria-hidden="true">
        {[0, 1, 2].map((col) =>
          [0, 1].map((row) => (
            <rect
              key={`${col}-${row}`}
              x={10 + col * 38}
              y={10 + row * 34}
              width="28"
              height="24"
              rx="6"
              fill={col === 1 && row === 0 ? "var(--pm-lime)" : "rgba(255,255,255,0.22)"}
            />
          ))
        )}
      </svg>
    ),
  },
  {
    key: "oa",
    title: "Mock Online Assessment",
    desc: "Real sectional structure, cutoffs and timing, not a generic quiz.",
    to: "/signup",
    topBg: "var(--pm-lime)",
    footerBg: "#B5E03F",
    footerText: "#0B2A30",
    Illustration: () => (
      <svg viewBox="0 0 120 80" width="64" height="44" aria-hidden="true">
        <rect x="14" y="16" width="92" height="12" rx="6" fill="rgba(11,42,48,0.75)" />
        <rect x="14" y="34" width="68" height="12" rx="6" fill="rgba(11,42,48,0.5)" />
        <rect x="14" y="52" width="46" height="12" rx="6" fill="rgba(11,42,48,0.28)" />
      </svg>
    ),
  },
  {
    key: "interview",
    title: "Adaptive Interview",
    desc: "Follows up on vague answers, just like a real interviewer.",
    to: "/signup",
    topBg: "#073B43",
    footerBg: "#052B31",
    footerText: "#FFFFFF",
    Illustration: () => (
      <svg viewBox="0 0 120 80" width="64" height="44" aria-hidden="true">
        <rect x="10" y="14" width="64" height="30" rx="14" fill="rgba(255,255,255,0.18)" />
        <path d="M20 44 L20 54 L32 44 Z" fill="rgba(255,255,255,0.18)" />
        <rect x="46" y="40" width="64" height="30" rx="14" fill="var(--pm-lime)" />
        <path d="M100 70 L100 60 L88 70 Z" fill="var(--pm-lime)" />
      </svg>
    ),
  },
];

const COMPANIES = [
  "TCS NQT", "Infosys", "Wipro Elite NTH", "Cognizant GenC", "Accenture",
  "IBM", "Zoho", "Capgemini", "HCLTech", "LTIMindtree", "Tech Mahindra", "Deloitte USI",
];

function ActionCard({ card }) {
  const Illustration = card.Illustration;
  return (
    <Link
      to={card.to}
      data-testid={`start-card-${card.key}`}
      className="group flex-1 rounded-[24px] overflow-hidden flex flex-col transition-transform duration-200 hover:-translate-y-1"
    >
      <div className="flex-1 min-h-[140px] flex items-center justify-center" style={{ background: card.topBg }}>
        <Illustration />
      </div>
      <div className="px-5 pt-4 pb-3 bg-white">
        <div className="font-display font-bold text-base" style={{ color: "#0B2A30" }}>{card.title}</div>
        <p className="mt-1 text-sm leading-snug" style={{ color: "rgba(11,42,48,0.70)" }}>{card.desc}</p>
      </div>
      <div
        className="px-5 py-3 flex items-center justify-between font-display font-semibold text-sm"
        style={{ background: card.footerBg, color: card.footerText }}
      >
        <span>{card.title}</span>
        <span className="inline-block transition-transform duration-200 group-hover:translate-x-1">&rarr;</span>
      </div>
    </Link>
  );
}

export default function StartPractisingSection() {
  const [rootRef, revealed] = useRevealOnView({ threshold: 0.2, fallbackMs: 500 });

  return (
    <section
      className="relative"
      style={{
        background: "var(--pm-cream)",
        // Same rounded-shelf transition as the other cream/teal boundaries
        // on this page -- crisp colour edge, soft geometry, no gradient
        // blend (a direct cream/teal colour blend produces a desaturated
        // grey "mud" band at the midpoint; see HeroV2.jsx's comment).
        borderTopLeftRadius: 56,
        borderTopRightRadius: 56,
        marginTop: -56,
        // 20, not 19 (2026-10) -- WhatYouGetSection (the section this
        // overlaps) was itself bumped 17->19 to fix a stacking bug (it
        // had fallen behind Flow's rising zIndex across two later
        // rounds), so this needs to clear 19, one higher again.
        zIndex: 20,
      }}
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-28">
        <div className="text-center max-w-2xl mx-auto mb-12">
          {/* font-weight 300 + letter-spacing -0.02em + line-height 1.15,
              matching the site-wide h1/h2 style (HeroV2.jsx's h1). Plain
              teal-deep emphasis text, no highlighter band (same rule as
              every other main heading on this page). */}
          <h2 className="font-display font-light text-4xl lg:text-6xl leading-[1.15]" style={{ color: "#0B2A30", letterSpacing: "-0.02em" }}>
            Pick your{" "}
            <span style={{ color: "#0F6F7A", fontWeight: 600 }}>starting point.</span>
          </h2>
          <p className="mt-3 text-base" style={{ color: "rgba(11,42,48,0.70)" }}>
            Every path runs on the real structure of the company you choose.
          </p>
        </div>

        <div
          ref={rootRef}
          className="pm-awe-tray rounded-[28px] p-3 flex flex-col sm:flex-row gap-3"
          style={{ background: "#FFFFFF", boxShadow: "var(--pm-card-shadow)" }}
        >
          {CARDS.map((card, i) => (
            <div
              key={card.key}
              style={{
                opacity: revealed ? 1 : 0,
                transform: revealed ? "translateY(0)" : "translateY(16px)",
                transition: "opacity 500ms, transform 500ms",
                transitionDelay: revealed ? `${i * 120}ms` : "0ms",
                display: "flex",
                flex: 1,
              }}
            >
              <ActionCard card={card} />
            </div>
          ))}
          {/* Decorative only: rests on the tray's top edge above the third
              (Adaptive Interview) card. Hidden below 1100px via .pm-awe-figure. */}
          <img
            src="/illustrations/student-awe.svg"
            alt=""
            aria-hidden="true"
            width={1190}
            height={849}
            loading="lazy"
            className="pm-awe-figure"
          />
        </div>

        <div className="mt-14 text-center">
          <div className="font-display font-semibold text-lg mb-5" style={{ color: "#0B2A30" }}>
            Practise the real tests of
          </div>
          <div className="flex flex-wrap justify-center gap-2.5">
            {COMPANIES.map((name) => (
              <span
                key={name}
                className="px-4 py-1.5 rounded-full text-sm bg-white"
                style={{ border: "1px solid #F2EDDF", color: "#0B2A30" }}
              >
                {name}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
