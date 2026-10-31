import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck, Menu, X, ArrowRight,
} from "lucide-react";
import { TID } from "../testIds";
import { SHOW_PRICING } from "../featureFlags";
import { useAuth } from "../auth";
import Button from "./shared/Button";

/**
 * HeroV2 -- the default "/" hero (2026-10). Renders full-bleed: it has NO
 * background or border-radius of its own -- the teal comes from the page
 * background (html, index.css), so there are no side gutters at any width.
 * Only an INNER max-w-7xl wrapper centers the nav/copy/cards; the outer
 * <section> stays edge to edge. Layout/style only taken from the reference
 * screenshot -- no photo, copy, avatars, icons, brand name or numbers from
 * it are reused anywhere here. The previous hero lives on, unused, in
 * HeroClassic.jsx. The phase strip that used to overlap this hero's
 * bottom edge now lives in its own section as <PhaseStrip /> (Landing.jsx)
 * -- see components/PhaseStrip.jsx. The three floating glass stat cards
 * that used to sit around the image slot are gone too (2026-10) -- the
 * same three facts now live in <Tray /> below, a white "tray" of three
 * illustrated, clickable action cards straddling the hero/cream seam, so
 * they weren't shown twice.
 */

// Each card is a whole link that smooth-scrolls to an existing section.
// ids: "different" (added to the Contrarian/"What makes this different"
// section, Landing.jsx -- it had none before), "inside-your-report"
// (added to InsideYourReportSection.jsx, same reason), "pipeline" (The
// Flow section -- already had this id). footerText intentionally does
// NOT follow the literal "lime-dark arrow on the lime card" spec -- see
// the contrast comment in TrayCard below for the measured reason.
//
// Card top colours (2026-10 fix): the previous "Real cutoffs" card used
// #0F6F7A, identical to the hero's own background right behind it, so
// the card read as a borderless gap rather than a card where they met.
// Swapped to sky-deep (an already-approved light-section token used
// elsewhere on this page), footer swapped to keep its own internal
// contrast (white title on a dark footer), and
// card-real-cutoffs-on-teal.svg (the on-dark-background illustration
// variant, now unused) is deleted from public/illustrations/.
//
// "Full pipeline" DOES use a teal top again (2026-10, #2A9AA3 --pm-teal-
// light) -- deliberately a different, lighter teal than the hero's own
// background (never flatter than #0A4A53 at its right edge, see the
// comment on the outer <section>'s backgroundImage below): HSL lightness
// 40.2% vs 18.2%, a 22-point gap, so the two are clearly distinguishable
// rather than repeating the earlier blending bug.
const TRAY_CARDS = [
  {
    id: "different",
    top: "#D3E8F6",
    footer: "#073B43",
    footerText: "#FFFFFF",
    pillBg: "#FFFFFF",
    title: "Real cutoffs",
    pill: "Per company",
    illustration: "/illustrations/tray-cutoffs.svg",
  },
  {
    id: "inside-your-report",
    top: "var(--pm-lime)",
    footer: "#A5CC2E",
    footerText: "#0B2A30",
    pillBg: "rgba(255,255,255,0.88)",
    title: "Adaptive interview",
    pill: "Live",
    illustration: "/illustrations/tray-interview.svg",
  },
  {
    id: "pipeline",
    top: "#2A9AA3",
    footer: "#0F6F7A",
    footerText: "#FFFFFF",
    pillBg: "#FFFFFF",
    title: "Full pipeline",
    pill: "Resume to verdict",
    illustration: "/illustrations/tray-pipeline.svg",
  },
];

// Only routes/sections that actually exist in this app. Pricing is
// omitted while SHOW_PRICING is false (featureFlags.js) -- its target
// section doesn't render, so the link would be dead.
const NAV_LINKS = [
  { label: "Home", href: "/", active: true },
  { label: "How it works", href: "/#pipeline" },
  ...(SHOW_PRICING ? [{ label: "Pricing", href: "/#pricing" }] : []),
  { label: "Contact", href: "mailto:hello@placemint.app" },
];

function scrollToId(e, id) {
  e.preventDefault();
  const el = document.getElementById(id);
  if (!el) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
}

function TrayCard({ card, index, revealed }) {
  return (
    <a
      href={`#${card.id}`}
      onClick={(e) => scrollToId(e, card.id)}
      className={`group flex-1 min-w-0 flex flex-col rounded-[24px] overflow-hidden transition-transform duration-200 hover:-translate-y-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0B2A30] ${
        revealed ? "" : "pointer-events-none"
      }`}
      style={{
        opacity: revealed ? 1 : 0,
        // Only applied pre-reveal -- once true, `transform` is left unset
        // so the hover: class can actually move the card (an inline
        // style.transform always wins over a stylesheet :hover rule, a
        // bug hit and fixed on this exact pattern earlier this session).
        transform: revealed ? undefined : "translateY(16px)",
        transitionProperty: "opacity, transform",
        transitionDuration: revealed ? "200ms" : "500ms",
        transitionDelay: revealed ? "0ms" : `${index * 100}ms`,
      }}
    >
      <div
        className="relative h-[170px] lg:h-[210px] shrink-0 overflow-hidden"
        style={{ background: card.top }}
      >
        <img
          src={card.illustration}
          alt=""
          aria-hidden="true"
          width={1344}
          height={768}
          loading="eager"
          className="absolute inset-0 block w-full h-full object-cover transition-transform duration-200 group-hover:scale-[1.04]"
          style={{ objectPosition: "center bottom" }}
        />
        <span
          className="absolute left-3 top-3 z-10 whitespace-nowrap text-xs font-semibold px-3 py-1.5 rounded-full"
          style={{ color: "#0B2A30", background: card.pillBg }}
        >
          {card.pill}
        </span>
      </div>
      {/* .60/.65-opacity text has failed AA on this page's lighter
          backgrounds before (see Landing.jsx DifferentiatorCards and the
          previous round of seam cards) -- full-opacity colours here
          instead, verified below rather than assumed (2026-10, footers
          changed when the card tops moved off teal):
            - white on --pm-teal-night #073B43 ("Real cutoffs" footer) -> 12.2:1
            - ink #0B2A30 on #A5CC2E ("Adaptive interview" footer, unchanged) -> 8.1:1
            - white on --pm-teal-deep #0F6F7A ("Full pipeline" footer) -> 5.9:1
          all comfortably clear AA (4.5:1). The spec's literal
          "lime-dark text on the lime card" was tried first by hand-
          calculation: lime-dark #AEDB3A on this card's own #A5CC2E
          footer measures ~1.15:1 (both are similar-brightness
          lime/olive tones) -- a severe fail -- so the lime card's
          footer uses --pm-ink (already specified for that footer
          elsewhere in the same spec) for both the title AND the arrow,
          not just the title. */}
      <div
        className="flex items-center justify-between h-[72px] px-5 shrink-0"
        style={{ background: card.footer, color: card.footerText }}
      >
        <span className="font-display text-lg font-semibold">{card.title}</span>
        <ArrowRight size={18} className="transition-transform duration-200 group-hover:translate-x-1" />
      </div>
    </a>
  );
}

// Fades/slides in once the hero has had a moment to settle after mount
// (not scroll-triggered -- the tray is inside the hero, visible on load
// without scrolling). Reduced-motion skips straight to visible.
function useRevealOnMount(delayMs = 300) {
  const [revealed, setRevealed] = useState(false);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setRevealed(true);
      return;
    }
    const t = setTimeout(() => setRevealed(true), delayMs);
    return () => clearTimeout(t);
  }, [delayMs]);
  return revealed;
}

// Straddles the hero/cream seam. Positioning is on this OUTER wrapper
// (absolute, full width, no visual styling of its own) rather than on
// the visible white tray div one level in -- the wrapper's own rendered
// height always equals the tray's (its only child), so transforms
// applied here read off the tray's true height with no separate
// measurement needed, same technique proven exact in the previous round
// of these cards (measured desktop card-centre == hero-bottom-edge to
// the pixel).
//
// Desktop (lg+): bottom: 0 (hero's true bottom edge) + translateY(50%),
// which resolves against this wrapper's own rendered height (the
// ~298px tray) -- centres the tray on the seam exactly, regardless of
// the tray's exact rendered height.
//
// Mobile: spec asks to anchor the tray's TOP edge 48px above the seam
// instead of centring it (the mobile tray, with all 3 cards stacked
// full width, is much taller -- centring it would push more than half
// of it up into the hero copy). top: 100% (= hero's own bottom edge,
// same reference point bottom:0 uses) + a fixed translateY(-48px) does
// this directly and exactly, with no dependency on the tray's actual
// stacked height at all.
//
// z-index: the spec asked for 5, but whichever section is this hero's
// immediate next sibling in Landing.jsx (CrackInterviewsSection as of
// 2026-10, formerly Contrarian/"What makes this different" before it was
// moved -- see Landing.jsx) has its own explicit z-index, and this
// hero's outer <section> carries no z-index of its own (nor any
// animation/transform that would create a stacking context for it --
// see the comment on the outer <section> below, about a real bug from
// an earlier round caused by exactly that). A child's z-index can only
// out-rank a sibling SECTION's z-index if it's numerically higher than
// that sibling's -- 5 would paint the tray BEHIND whatever section
// follows the hero, wherever they overlap (reproducing, by numbers
// alone, the exact invisible-cards bug already diagnosed and fixed in
// an earlier round). Used 25 instead -- comfortably above every
// section-level z-index used on this page so far (currently topping out
// at 18), below the sticky nav's 30, and distinct from the hero image
// slot's 20 -- confirmed visually that the tray renders on top, not
// behind, regardless of which section is next. If a future reorder ever
// pushes a section's own z-index past 25, bump this too.
function Tray() {
  const revealed = useRevealOnMount();
  return (
    <div className="absolute inset-x-0 z-[25] px-6 top-full lg:top-auto lg:bottom-0 [transform:translateY(-48px)] lg:[transform:translateY(50%)]">
      <div
        className="max-w-[1200px] mx-auto flex flex-col lg:flex-row gap-3 justify-center bg-white rounded-[32px] p-2"
        style={{
          // 2026-10 fix: the old shadow (0 24px 60px rgba(7,59,67,.28))
          // had a 60px blur -- well past the 40px ceiling -- which read
          // as a soft grey smear bleeding onto the cream section below
          // rather than a crisp edge. The white ring (0 0 0 4px) gives
          // the tray its own visible boundary against both the teal
          // above and the cream below; the second shadow has a negative
          // spread (-14px) specifically so it stays tucked under the
          // tray instead of blurring outward onto either neighbour.
          border: "1px solid rgba(7,59,67,0.12)",
          boxShadow: "0 0 0 4px rgba(255,255,255,0.35), 0 14px 28px -14px rgba(7,59,67,0.45)",
        }}
      >
        {TRAY_CARDS.map((card, i) => (
          <TrayCard key={card.id} card={card} index={i} revealed={revealed} />
        ))}
      </div>
    </div>
  );
}

function NavBar({ mobileOpen, setMobileOpen }) {
  const { user } = useAuth();
  const signedIn = Boolean(user);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className="sticky top-0 z-30 py-4 flex items-center justify-between transition-colors duration-200"
      style={scrolled ? { background: "rgba(10,60,66,0.82)", backdropFilter: "blur(14px)" } : undefined}
    >
      <Link to="/" data-testid={TID.navLogo} className="flex items-center gap-2 text-white">
        <div className="w-8 h-8 rounded-lg grid place-items-center font-display font-extrabold text-sm text-[#0A0A0A]" style={{ background: "var(--pm-lime)" }}>
          P
        </div>
        <span className="font-display text-lg font-bold tracking-tight">Placemint</span>
      </Link>

      <div className="hidden lg:flex items-center gap-8 text-sm font-medium">
        {NAV_LINKS.map((l) => (
          <a
            key={l.label}
            href={l.href}
            className={`pb-1 transition-colors ${l.active ? "text-white font-semibold" : "text-white/75 hover:text-white"}`}
          >
            {l.label}
            {l.active && <span className="block h-0.5 w-4 rounded-full mt-1" style={{ background: "var(--pm-lime)" }} />}
          </a>
        ))}
      </div>

      {/* Desktop: Log In, then Sign up (signed out only). Signed in, Log In
          stays as the account control and no Sign up is shown. */}
      <div className="hidden lg:flex items-center gap-3">
        <Button as={Link} to="/login" variant="outline-dark" data-testid={TID.navLogin} style={{ height: 44, padding: "0 20px", fontSize: 15 }}>
          Log In
        </Button>
        {!signedIn && (
          <Button as={Link} to="/signup" variant="lime-dark" data-testid={TID.navSignup} style={{ height: 44, padding: "0 22px", fontSize: 15 }}>
            Sign up
          </Button>
        )}
      </div>

      {/* Below lg: compact Sign up beside the menu button (signed out only);
          Log In moves inside the menu. */}
      <div className="lg:hidden flex items-center gap-2">
        {!signedIn && (
          <Button as={Link} to="/signup" variant="lime-dark" data-testid="nav-signup-mobile" style={{ height: 40, padding: "0 16px", fontSize: 15 }}>
            Sign up
          </Button>
        )}
        <button
          type="button"
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((v) => !v)}
          className="text-white p-2 -mr-2"
          style={{ minWidth: 44, minHeight: 44 }}
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {mobileOpen && (
        <div className="absolute top-full left-6 right-6 sm:left-10 sm:right-10 mt-3 lg:hidden rounded-2xl border border-white/15 bg-[#0A3A40]/95 backdrop-blur-md p-4 flex flex-col gap-3 shadow-xl">
          <Button as={Link} to="/login" variant="outline-dark" data-testid="nav-login-mobile" className="w-full" style={{ minHeight: 44, fontSize: 15 }}>
            Log In
          </Button>
          {NAV_LINKS.map((l) => (
            <a key={l.label} href={l.href} className={`flex items-center text-sm ${l.active ? "text-white font-semibold" : "text-white/80"}`} style={{ minHeight: 44 }}>
              {l.label}
            </a>
          ))}
        </div>
      )}
    </nav>
  );
}

export default function HeroV2({ imageSrc = "/hero-student.png" } = {}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [imgError, setImgError] = useState(false);
  const showImage = Boolean(imageSrc) && !imgError;

  return (
    // Full-bleed: width 100%, no outer max-width, no rounding. The hero
    // paints ONLY a scrim here (never a competing opaque gradient) -- the
    // teal itself is the one continuous page gradient (html, index.css).
    // An earlier version gave the hero its own 135deg teal-deep/teal-light
    // background, which produced a visible seam where it met the page
    // gradient at the hero's bottom edge (two different gradients, exit
    // color never matched the page gradient's color at that scroll
    // position). The scrim is edge to edge on the outer <section> itself,
    // not the padded inner wrapper -- putting it on the inner div left a
    // seam of flat, unscrimmed teal between the viewport edge and wherever
    // that div's own padding started.
    // pm-in (the mount fade/slide animation) moved OFF this outer section
    // and onto the inner content wrapper below (2026-10) -- a CSS
    // `animation` touching opacity/transform makes the animated element
    // establish its own stacking context (spec, not a bug in just this
    // codebase), which was silently trapping a descendant's z-index
    // inside the hero: no matter how high it was set, it could never
    // out-rank the next section's own z-index, because the comparison
    // happened at the whole-hero-vs-next-section level, not card-vs-shelf.
    // Keeping the outer section free of any such property lets <Tray />
    // below compare its own z-index directly against whatever follows --
    // see the comment on <Tray /> itself for why it needs 25, not 5.
    <section
      className="relative pt-0 pb-24 lg:pb-[198px] min-h-[100svh] flex flex-col"
      style={{
        // End stop changed from `transparent` to #0A4A53 (2026-10) -- past
        // 70% this scrim used to fade to nothing, which simply revealed
        // the page's own html-level gradient underneath (index.css),
        // itself ≈#0F6F7A (--pm-teal-deep) near the top of the page where
        // the hero sits -- 0 percentage points of HSL lightness away from
        // #0F6F7A, nowhere near the 12% safety margin a card or any other
        // light element would need against it. #0A4A53 is ~8.6 points
        // darker (HSL L 18.2% vs 26.9%), so the hero's right edge never
        // reads as the same flat teal as whatever sits behind/around it.
        // Grid lines are listed FIRST so they paint above the scrim -- the
        // scrim is now opaque at its right edge (#0A4A53), which would
        // otherwise hide the page-level grid (index.css body::before) that
        // sits underneath the hero's content.
        backgroundImage:
          "linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(90deg, #031A1D 0%, rgba(7,66,74,0.9) 35%, #0A4A53 70%)",
        backgroundSize: "40px 40px, 40px 40px, 100% 100%",
      }}
    >
      {/* Uniform scrim below lg, where the layout stacks (text centered,
          full width, image below) instead of the left-text/right-image
          split the directional scrim above assumes. Also edge to edge. */}
      <div className="absolute inset-0 block lg:hidden pointer-events-none" style={{ background: "rgba(0,0,0,0.38)" }} aria-hidden="true" />

      {/* No linear-gradient fade into cream here (removed, 2026-10) -- any
          direct colour blend between a warm, light cream and a cool, dark
          teal passes through a desaturated grey "mud" band at the
          midpoint (they're ~140 degrees apart on the hue wheel), no
          matter how the gradient stops are written -- not a `transparent`-
          keyword bug, an inherent property of blending near-complementary
          hues. The cream section's own rounded "shelf" (Landing.jsx,
          border-radius + negative margin, overlapping up into this
          section's bottom padding) gives the soft/curved transition
          instead, with a crisp colour edge and only the GEOMETRY doing
          the softening. */}

      <div className="relative flex-1 flex flex-col max-w-7xl w-full mx-auto px-6 sm:px-10 lg:px-16 pm-in">
        {/* Hero copy + image share this wrapper so the image's bleed below
            it doesn't affect this wrapper's own flow height. */}
        <div className="relative flex-1 flex flex-col">
          <div className="relative">
            <NavBar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />

            <div className="flex flex-col lg:grid lg:grid-cols-[58fr_42fr] lg:items-center items-center text-center lg:text-left pt-8 pb-14 lg:pt-10 lg:pb-16">
              <div className="w-full">
                <div
                  className="uppercase text-white/80 mb-4"
                  style={{ fontFamily: "var(--pm-font-label)", fontWeight: 600, fontSize: 13, letterSpacing: "0.06em" }}
                >
                  Company-specific placement prep
                </div>
                {/* Weight 300 (font-light) + letter-spacing -0.02em +
                    line-height 1.08 is the site-wide h1/h2 "display
                    heading" style (2026-10) -- this hero is its origin
                    reference, so every other heading this applies to
                    matches it exactly rather than approximating it. */}
                <h1
                  className="font-display font-light text-white"
                  style={{ fontSize: "clamp(40px, 5.2vw, 72px)", lineHeight: 1.08, letterSpacing: "-0.02em", textWrap: "balance" }}
                >
                  <span className="block">Don&apos;t practice for a test.</span>
                  <span className="block">
                    Practice for <span style={{ color: "var(--pm-lime)", fontWeight: 600 }}>the</span> test.
                  </span>
                </h1>
                <p className="mt-6 text-base sm:text-lg text-white/85 max-w-md mx-auto lg:mx-0 leading-relaxed">
                  One engine per company, built on its real order, cutoffs and gating.
                </p>
                <Link
                  to="/signup"
                  data-testid={TID.heroCta}
                  className="inline-flex items-center mt-8 px-7 py-3.5 rounded-full font-semibold text-[#0A0A0A] transition-transform hover:scale-[1.03] active:scale-[0.97]"
                  style={{ background: "var(--pm-lime)" }}
                >
                  Get Started Now
                </Link>
                <div className="mt-7 flex items-center justify-center lg:justify-start gap-2 text-white/70 text-sm">
                  <ShieldCheck size={16} style={{ color: "var(--pm-lime)" }} />
                  Built for Indian placement drives
                </div>
              </div>

              {/* Desktop: illustration in the right column, vertically centred
                  against the copy. Decorative, so alt is empty. Hidden below
                  1024px (the hero stays single column). The float animation
                  is in index.css (.pm-hero-float). */}
              <img
                src="/illustrations/hero-illustration.svg"
                alt=""
                aria-hidden="true"
                width={1636}
                height={1191}
                loading="eager"
                fetchPriority="high"
                className="hidden lg:block w-full max-w-[640px] h-auto justify-self-end pm-hero-float"
              />

              {/* Mobile/tablet: image inline below text, centred (only if available) */}
              {showImage && (
                <div className="lg:hidden mt-8 w-full flex justify-center">
                  <img
                    src={imageSrc}
                    alt=""
                    onError={() => setImgError(true)}
                    className="max-h-[360px] w-auto object-contain"
                    style={{ filter: "drop-shadow(0 16px 28px rgba(0,0,0,0.35))" }}
                  />
                </div>
              )}

            </div>
          </div>

        </div>
      </div>

      <Tray />

      {/* The phase strip used to overlap this edge (-mt-14 trick) -- it now
          lives in its own section as <PhaseStrip />, so the hero just ends
          here with its own bottom padding above instead of relying on
          something below it to close the gap. */}
    </section>
  );
}
