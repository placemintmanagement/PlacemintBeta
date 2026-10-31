import React from "react";
import { Link } from "react-router-dom";
import { Twitter, Linkedin, Github, Mail } from "lucide-react";
import { SHOW_PRICING } from "../featureFlags";
import GlassLogoMark from "./glass/GlassLogoMark";

/**
 * Dark, multi-column marketing footer. Rendered on DepartmentCompanies and
 * the legal pages (via LegalPage.jsx). Keeps its own richer multi-column
 * content -- GlassFooter.jsx (landing-only) is a minimal one-line footer
 * with landing-specific copy (an "illustrative layout" disclaimer, a
 * trademark notice for the company logos shown there) that doesn't apply
 * to this component's actual pages, so this reuses glass's dark-footer
 * color palette rather than that component's copy/structure. Keep this
 * static — don't add live status widgets or newsletter signups without
 * asking, this is the "trust anchor" of the site.
 */
// className: the landing page keeps the default top margin; pages that sit
// on a cream background pass mt-0 so no teal body gradient shows in the gap.
export default function Footer({ className = "mt-24" } = {}) {
  // color set via inline style, not a Tailwind text-white/* class --
  // `.glass-landing`'s base reset sets `color: var(--gl-text)` (near-
  // black) on this same element with equal Tailwind-utility specificity,
  // so a plain class loses that tie unpredictably by source order;
  // inline style always wins regardless, and every
  // `.glass-landing a { color: inherit }` link below correctly inherits
  // this corrected value. Caught live: links were rendering nearly
  // invisible against the dark background before this fix.
  return (
    <footer className={`glass-landing ${className} relative z-10`} style={{ background: "#0c0c0c", color: "rgba(255,255,255,0.8)" }}>
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-16 grid grid-cols-1 md:grid-cols-6 gap-10">
        {/* Brand + tagline */}
        <div className="md:col-span-2">
          <Link to="/" className="flex items-center gap-2">
            <GlassLogoMark size={32} />
            <span className="text-2xl font-bold text-white" style={{ fontFamily: "Outfit, system-ui, sans-serif" }}>HireTric</span>
          </Link>
          <p className="text-sm text-white/60 leading-relaxed mt-5 max-w-xs">
            Placement prep the way companies actually test you. Real OA structure, real cutoffs, real interview rounds, across 14 top Indian tech recruiters.
          </p>
          <div className="mt-6 flex items-center gap-3">
            <a href="https://twitter.com" target="_blank" rel="noreferrer" aria-label="Twitter"
               className="w-9 h-9 rounded-lg border border-white/10 grid place-items-center hover:bg-white/5 transition">
              <Twitter size={16} />
            </a>
            <a href="https://linkedin.com" target="_blank" rel="noreferrer" aria-label="LinkedIn"
               className="w-9 h-9 rounded-lg border border-white/10 grid place-items-center hover:bg-white/5 transition">
              <Linkedin size={16} />
            </a>
            <a href="https://github.com" target="_blank" rel="noreferrer" aria-label="GitHub"
               className="w-9 h-9 rounded-lg border border-white/10 grid place-items-center hover:bg-white/5 transition">
              <Github size={16} />
            </a>
          </div>
        </div>

        {/* Column: Product */}
        <FooterColumn title="Product">
          <FooterLink href="/#companies">14 Companies</FooterLink>
          <FooterLink href="/#pipeline">How it works</FooterLink>
          {SHOW_PRICING && <FooterLink to="/pricing">Pricing</FooterLink>}
          <FooterLink to="/signup">Resume Checker</FooterLink>
          <FooterLink to="/dashboard">Dashboard</FooterLink>
        </FooterColumn>

        {/* Column: Resources */}
        <FooterColumn title="Resources">
          <FooterLink href="/#faq">FAQ</FooterLink>
          <FooterLink to="/pricing">What is a run?</FooterLink>
          <FooterLink href="mailto:hello@placemint.app">Help &amp; Support</FooterLink>
          {/* Was href="/#pricing" -- that anchor's section no longer
              renders while SHOW_PRICING is false, so it would be dead.
              Gated behind the same flag rather than repointed, since
              "Founder pricing" is itself a pricing-tier claim. */}
          {SHOW_PRICING && <FooterLink href="/#pricing">Founder pricing</FooterLink>}
        </FooterColumn>

        {/* Column: Legal */}
        <FooterColumn title="Legal">
          <FooterLink to="/legal/privacy">Privacy Policy</FooterLink>
          <FooterLink to="/legal/terms">Terms of Service</FooterLink>
          <FooterLink to="/legal/refund">Refund Policy</FooterLink>
          <FooterLink to="/legal/cookies">Cookie Policy</FooterLink>
        </FooterColumn>

        {/* Column: Company */}
        <FooterColumn title="Company">
          <FooterLink to="/legal/about">About</FooterLink>
          <FooterLink href="mailto:hello@placemint.app">Contact</FooterLink>
          <span className="text-sm text-white/70 py-1">Made in India</span>
          <a href="mailto:hello@hiretric.app" className="text-sm text-white/60 hover:text-white transition inline-flex items-center gap-1.5 py-1">
            <Mail size={12} /> hello@hiretric.app
          </a>
        </FooterColumn>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-white/10">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-6 flex flex-wrap items-center justify-between gap-3 text-xs text-white/70">
          <div>&copy; {new Date().getFullYear()} HireTric. Built for the fresher who’s tired of “one mock test fits all”.</div>
          <div className="flex items-center gap-4">
            <Link to="/legal/privacy" className="hover:text-[var(--gl-y)] transition">Privacy</Link>
            <Link to="/legal/terms" className="hover:text-[var(--gl-y)] transition">Terms</Link>
            <span className="inline-flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "var(--gl-y)" }}></span>
              beta
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({ title, children }) {
  return (
    <div>
      <div className="mb-4" style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "rgba(255,255,255,0.7)" }}>{title}</div>
      <div className="flex flex-col gap-2">{children}</div>
    </div>
  );
}

function FooterLink({ to, href, children }) {
  const cls = "text-sm text-white/70 transition py-1 hover:text-[var(--gl-y)]";
  if (to) return <Link to={to} className={cls}>{children}</Link>;
  return <a href={href} className={cls}>{children}</a>;
}
