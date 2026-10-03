import React from "react";
import useRevealOnView from "../hooks/useRevealOnView";

/**
 * The three cards under "Every company tests differently." (Landing.jsx).
 * That section is a cream background (2026-10, was solid white), so "Real
 * order"/"Real cutoffs" are solid white cards with a cream-deep border --
 * plain cream-on-cream would have no visible edge. "Real pressure" stays
 * the section's one lime highlight. Frosted glass is kept only for the
 * small floating stat cards in the hero (HeroV2's GlassCard), never
 * reused here. Fade + slide up in sequence on first scroll into view,
 * reduced-motion safe -- see useRevealOnView for why the trigger has a
 * fast fallback rather than depending solely on IntersectionObserver.
 *
 * Icon tiles replaced with illustrations (2026-10) -- each SVG already
 * bakes in its own 480x180 background colour, matching the card it sits
 * on (sky-ish white for order, cream for cutoffs, lime for pressure), so
 * no separate background styling is needed for the image itself.
 */
const ITEMS = [
  { key: "order", illustration: "/illustrations/card-real-order.svg", title: "Real order", desc: "Sections appear in the same order as the company's actual test." },
  { key: "cutoffs", illustration: "/illustrations/card-real-cutoffs-scorecard.svg", title: "Real cutoffs", desc: "Sectional and overall cutoffs mirror how each company screens." },
  { key: "pressure", illustration: "/illustrations/card-real-pressure.svg", title: "Real pressure", desc: "Timed rounds and gating, so you practise under real conditions.", highlight: true },
];

const STAGGER_MS = 120;

// box-shadow as a class, not inline style, so hover: can actually override
// the resting one -- inline `style.boxShadow` always wins over a
// stylesheet rule regardless of :hover, so a hover className alone would
// have had no visible effect.
const WHITE_CARD_CLASS =
  "bg-white border border-[#F2EDDF] shadow-[0_10px_30px_rgba(11,42,48,0.08)] hover:shadow-[0_16px_40px_rgba(11,42,48,0.14)]";

export default function DifferentiatorCards() {
  const [rootRef, revealed] = useRevealOnView({ threshold: 0.3, fallbackMs: 500 });

  return (
    <div ref={rootRef} className="grid grid-cols-1 sm:grid-cols-3 gap-5 mt-10 items-stretch">
      {ITEMS.map((item, i) => (
        <div
          key={item.key}
          className={`pm-card-lift rounded-[26px] p-8 flex flex-col h-full ${item.highlight ? "" : WHITE_CARD_CLASS}`}
          style={{
            background: item.highlight ? "var(--pm-lime)" : undefined,
            opacity: revealed ? 1 : 0,
            // Only set pre-reveal -- once true, left unset so the
            // .pm-card-lift hover/focus-within rule can actually move the
            // card. An inline style.transform always wins over a
            // stylesheet rule regardless of :hover, so keeping it
            // explicitly at translateY(0) post-reveal (as before) made
            // the hover lift silently do nothing -- same bug class
            // caught and fixed elsewhere this session.
            transform: revealed ? undefined : "translateY(16px)",
            transitionProperty: "opacity, transform",
            transitionDuration: revealed ? "200ms" : "500ms",
            transitionDelay: revealed ? `${i * STAGGER_MS}ms` : "0ms",
          }}
        >
          <img
            src={item.illustration}
            alt=""
            loading="lazy"
            className="block w-full rounded-[20px] object-cover"
            style={{ aspectRatio: "8 / 3" }}
          />
          <div className="font-display font-bold text-lg mt-5" style={{ color: "#0B2A30" }}>{item.title}</div>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: item.highlight ? "rgba(11,42,48,0.75)" : "rgba(11,42,48,0.70)" }}>
            {item.desc}
          </p>
        </div>
      ))}
    </div>
  );
}
