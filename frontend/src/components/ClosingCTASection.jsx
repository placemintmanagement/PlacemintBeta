import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ShieldCheck } from "lucide-react";
import useRevealOnView from "../hooks/useRevealOnView";

/**
 * Closing CTA (Landing.jsx, 2026-10). Back at the very end of the page,
 * just above the footer -- its original position, replacing the Pricing
 * section's slot (Pricing itself is hidden for now, see featureFlags.js).
 * Light grey now (--pm-grey, was white, was sky, was cream before that)
 * -- FAQ just above it became sky, so grey is what keeps this from
 * repeating its neighbour's background; Footer below is dark teal-night,
 * no conflict there either. Rounded on both top and bottom: top overlaps
 * up into FAQ (same rounded-shelf technique used elsewhere -- crisp
 * colour edge, soft geometry, no gradient blend); bottom is self-
 * contained since nothing overlaps up into this section's own bottom
 * edge -- Footer just follows with its own plain gap.
 */
export default function ClosingCTASection() {
  const [rootRef, revealed] = useRevealOnView({ threshold: 0.3, fallbackMs: 500 });

  return (
    <section
      className="relative"
      style={{
        background: "var(--pm-grey)",
        borderTopLeftRadius: 56,
        borderTopRightRadius: 56,
        borderBottomLeftRadius: 56,
        borderBottomRightRadius: 56,
        marginTop: -56,
        zIndex: 24,
      }}
    >
      <div
        ref={rootRef}
        className="max-w-3xl mx-auto px-6 lg:px-10 py-28 text-center"
        style={{
          opacity: revealed ? 1 : 0,
          transform: revealed ? "translateY(0)" : "translateY(20px)",
          transition: "opacity 600ms, transform 600ms",
        }}
      >
        {/* Panel is #E8F3FB on the grey section: different colour, no border needed. */}
        <div className="mx-auto mb-10 overflow-hidden" style={{ maxWidth: 360, borderRadius: 24, background: "#E8F3FB" }}>
          <img src="/illustrations/student-stairs.svg" alt="" width={2048} height={1509} className="block w-full h-auto" />
        </div>
        <div className="text-lg sm:text-xl font-normal" style={{ color: "rgba(11,42,48,0.70)" }}>
          Start practising for
        </div>
        {/* font-weight 300 base + letter-spacing -0.02em, matching the
            site-wide h1/h2 style (HeroV2.jsx's h1) -- fully overridden
            here since the whole heading sits inside the emphasis span
            (unlike the other headings, there's no separate light lead-in
            phrase; "Start practising for" above fills that role as its
            own element instead). Span: plain teal-deep text, 600 weight,
            no highlighter band (removed from all h1/h2 emphasis,
            2026-10). */}
        <h2
          className="mt-2 font-display font-light"
          style={{ color: "#0B2A30", fontSize: "clamp(2rem, 7vw, 3.5rem)", lineHeight: 1.15, letterSpacing: "-0.02em" }}
        >
          <span
            style={{
              color: "#0F6F7A",
              fontWeight: 600,
            }}
          >
            the test that&apos;s yours
          </span>
        </h2>
        <p className="mt-6 text-base sm:text-lg" style={{ color: "rgba(11,42,48,0.70)" }}>
          Pick your company. Practise its real order, cutoffs and gating.
        </p>

        <div className="mt-10 flex flex-col items-center">
          <Link
            to="/signup"
            className="group inline-flex items-center justify-center gap-2 rounded-full font-display font-bold transition-transform duration-200 hover:-translate-y-0.5 w-full sm:w-auto"
            style={{
              background: "var(--pm-lime)",
              color: "#0B2A30",
              padding: "18px 36px",
              boxShadow: "0 4px 0 #A5CC2E",
              maxWidth: 320,
            }}
          >
            Get Started Now
            <ArrowRight size={18} className="transition-transform duration-200 group-hover:translate-x-1" />
          </Link>
          {/* .55 measured ~3.6:1 against a light background in this same
              pattern elsewhere (SampleRoundBanner, now removed) -- fails
              AA for 14px text. .65 clears it. */}
          <div className="mt-4 flex items-center gap-1.5 text-sm" style={{ color: "rgba(11,42,48,0.65)" }}>
            <ShieldCheck size={14} />
            Built for Indian placement drives
          </div>
        </div>
      </div>
    </section>
  );
}
