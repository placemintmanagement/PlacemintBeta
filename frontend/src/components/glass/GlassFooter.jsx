import React from "react";
import { Link } from "react-router-dom";

/**
 * Minimal, centered footer -- matches the reference's one-line footer in
 * spirit, plus this app's real legal links and the trademark/honesty
 * disclaimer line that already exists elsewhere in this codebase
 * (CrackInterviewsSection.jsx / FaqSection.jsx), carried over verbatim
 * since it's a real legal requirement, not decorative. Landing-page-only
 * -- the shared components/Footer.jsx used by other pages is untouched.
 */
export default function GlassFooter() {
  return (
    <footer className="gl-footer">
      <div className="gl-footer-links">
        <a href="#top">Starting points</a>
        <a href="#get">What you get</a>
        <a href="#companies">Companies</a>
        <a href="#faq">FAQ</a>
        <a href="mailto:hello@placemint.app">Contact</a>
      </div>
      <div className="gl-footer-legal">
        <Link to="/legal/privacy">Privacy</Link>
        <Link to="/legal/terms">Terms</Link>
        <Link to="/legal/refund">Refund</Link>
        <Link to="/legal/cookies">Cookies</Link>
        <Link to="/legal/about">About</Link>
      </div>
      <div>&copy; {new Date().getFullYear()} Placemint. Illustrative layout, not real results.</div>
      <small>
        Company names are trademarks of their respective owners. Placemint is not affiliated with or endorsed by them.
      </small>
    </footer>
  );
}
