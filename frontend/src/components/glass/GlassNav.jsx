import React from "react";
import { Link } from "react-router-dom";
import { Sun, Moon } from "lucide-react";
import CompanyFinder from "./CompanyFinder";
import { useAuth } from "../../auth";
import { TID } from "../../testIds";

export default function GlassNav({ theme, onToggleTheme, onPreviewCompany }) {
  const { user } = useAuth();
  const signedIn = Boolean(user);

  return (
    <nav className="gl-nav">
      <div>
        <Link className="gl-logo" to="/" data-testid={TID.navLogo}>
          placemint<i aria-hidden="true" />
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
