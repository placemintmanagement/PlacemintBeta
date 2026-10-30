import React from "react";
import { Link } from "react-router-dom";
import { Sun, Moon } from "lucide-react";
import CompanyFinder from "./CompanyFinder";
import GlassLogoMark from "./GlassLogoMark";
import { useAuth } from "../../auth";
import { TID } from "../../testIds";

export default function GlassNav({ theme, onToggleTheme, onPreviewCompany, onStartPractice }) {
  const { user } = useAuth();
  const signedIn = Boolean(user);

  return (
    <nav className="gl-nav">
      <div>
        <Link className="gl-logo" to="/" data-testid={TID.navLogo}>
          <GlassLogoMark size={28} />
          HireTric
        </Link>
        <div className="gl-links">
          <a href="#top">Starting points</a>
          <a href="#get">What you get</a>
          <a href="#companies">Companies</a>
          <a href="#faq">FAQ</a>
        </div>
        <CompanyFinder onPreview={onPreviewCompany} className="gl-nav-finder" />
        <button
          type="button"
          className="gl-theme-btn"
          onClick={onToggleTheme}
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        {/* Replaces the hero's own "Start practice" button (removed
            2026-10 -- it was sitting over the photo's face). Drives the
            SAME demo state machine via GlassHero's exposed startDemo()
            ref method (Landing.jsx wires the two together), which also
            scrolls the hero into view first since this nav is sticky and
            reachable from anywhere on the page. Black solid (.gl-btn k),
            same treatment as the signed-in Dashboard button below --
            Sign up already owns the yellow accent, so this stays
            visually distinct from it rather than competing for the same
            attention. Hidden below 980px (glass.css) -- same breakpoint
            that already hides .gl-links/.gl-finder to keep the mobile nav
            from overflowing: a third action button alongside Log in/Sign
            up pushed the nav 100px+ past the 390px viewport, clipping
            Sign up off-screen entirely (caught live via a scrollWidth
            check, not assumed). Sign up stays the primary mobile CTA;
            Start practice shows once there's room for it. */}
        <button type="button" className="gl-btn k gl-nav-start" data-testid={TID.heroCta} onClick={onStartPractice}>
          Start practice
        </button>
        {signedIn ? (
          <Link className="gl-btn k" to="/dashboard" data-testid={TID.navDashboard}>Dashboard</Link>
        ) : (
          <Link className="gl-btn" to="/login" data-testid={TID.navLogin}>Log in</Link>
        )}
        {!signedIn && (
          <Link className="gl-btn y" to="/signup" data-testid={TID.navSignup}>Sign up</Link>
        )}
      </div>
    </nav>
  );
}
