import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { TID } from "../testIds";
import { SHOW_PRICING } from "../featureFlags";
import { Sparkles, Crown } from "lucide-react";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "./ui/alert-dialog";

// Human-readable label + accent color per plan. Chip classes are the
// "on teal" variants (index.css) since the header sits directly on the
// page's teal background now, not a white card.
const PLAN_META = {
  free:     { label: "Free",     chipClass: "pm-chip pm-chip-light", icon: null },
  basic:    { label: "Basic",    chipClass: "pm-chip pm-chip-lime",  icon: <Sparkles size={11} /> },
  pro:      { label: "Pro",      chipClass: "pm-chip pm-chip-lime",  icon: <Sparkles size={11} /> },
  max:      { label: "MAX",      chipClass: "pm-chip pm-chip-lime",  icon: <Sparkles size={11} /> },
  supermax: { label: "SuperMAX", chipClass: "pm-chip pm-chip-lime",  icon: <Sparkles size={11} /> },
  founder:  { label: "Founder",  chipClass: "pm-chip pm-chip-light", icon: <Crown size={11} /> },
};

// light: renders the header for a light-background page (2026-10,
// DepartmentCompanies.jsx) -- white/ink instead of the default
// translucent-teal/white chrome every other app page still uses.
// Defaults to false so every existing <Header /> call keeps its current
// look untouched.
export default function Header({ light = false } = {}) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  const plan = user ? PLAN_META[user.plan] || PLAN_META.free : null;
  const runsLeft = user ? Math.max(0, (user.runs_quota ?? 0) - (user.runs_used ?? 0)) : 0;

  const doSignOut = async () => {
    setSigningOut(true);
    await logout();
    setSigningOut(false);
    setConfirmOpen(false);
    navigate("/");
  };

  const navLinkClass = light
    ? "transition-colors hover:text-[#0B2A30]"
    : "hover:text-white transition-colors";
  const ghostBtnClass = light ? "pm-btn pm-btn-ghost" : "pm-btn pm-btn-ghost-light";

  return (
    <header
      className={`sticky top-0 z-40 backdrop-blur-xl ${light ? "" : "border-b border-white/10"}`}
      style={light
        ? { background: "#FFFFFF", borderBottom: "1px solid rgba(7,59,67,0.08)" }
        : { background: "rgba(10,60,66,0.82)" }
      }
    >
      <div className={`max-w-7xl mx-auto flex items-center justify-between ${light ? "px-4 sm:px-6 lg:px-10" : "px-6 lg:px-10"} py-4`}>
        <Link to="/" data-testid={TID.navLogo} className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg grid place-items-center font-display font-extrabold" style={{ background: "var(--pm-lime)", color: "var(--pm-ink)" }}>P</div>
          <span className={`font-display ${light ? "text-lg sm:text-xl" : "text-xl"} font-bold tracking-tight`} style={{ color: light ? "#0B2A30" : "#FFFFFF" }}>Placemint</span>
          {light ? (
            <span className="hidden sm:inline-flex ml-2 rounded-full" style={{ background: "var(--pm-sky)", color: "var(--pm-ink)", fontSize: 13, padding: "4px 10px" }}>Beta</span>
          ) : (
            <span className="pm-chip pm-chip-light hidden sm:inline-flex ml-2">Beta</span>
          )}
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm" style={{ color: light ? "rgba(11,42,48,0.70)" : "rgba(255,255,255,0.75)" }}>
          <a href="/#companies" className={navLinkClass}>Companies</a>
          <a href="/#pipeline" className={navLinkClass}>How it works</a>
          {SHOW_PRICING && <a href="/#pricing" className={navLinkClass}>Pricing</a>}
          <a href="/#faq" className={navLinkClass}>FAQ</a>
        </nav>

        <div className="flex items-center gap-3">
          {user ? (
            <>
              {plan && (
                <div className="hidden sm:flex items-center gap-2" data-testid="header-plan-badge">
                  <span className={plan.chipClass} title={`Plan: ${plan.label}`}>
                    {plan.icon}{plan.label}
                  </span>
                  {user.plan !== "founder" && (
                    <span className={`text-[11px] ${light ? "" : "font-mono"}`} style={{ color: light ? "rgba(11,42,48,0.60)" : "rgba(255,255,255,0.70)" }} title="Runs remaining">
                      {runsLeft}/{user.runs_quota} runs
                    </span>
                  )}
                </div>
              )}
              <Link to="/dashboard" data-testid={TID.navDashboard} className={light ? `${ghostBtnClass} text-sm pm-hdr-btn` : `${ghostBtnClass} text-sm py-2 px-4`}>Dashboard</Link>
              {/* Wrapper, not the link: .pm-btn sets display itself and would win over a hidden class. */}
              <div className="hidden sm:flex">
                <Link to="/deck" data-testid="nav-deck" className={`${ghostBtnClass} text-sm py-2 px-4`}>Review deck</Link>
              </div>
              <button
                data-testid={TID.navLogout}
                onClick={() => setConfirmOpen(true)}
                className={light ? `${ghostBtnClass} text-sm pm-hdr-btn` : `${ghostBtnClass} text-sm py-2 px-4`}
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" data-testid={TID.navLogin} className={light ? `${ghostBtnClass} text-sm pm-hdr-btn whitespace-nowrap` : `${ghostBtnClass} text-sm py-2 px-3 sm:px-4 whitespace-nowrap`}>Sign in</Link>
              <Link to="/signup" data-testid={TID.navSignup} className={light ? "pm-btn pm-btn-primary text-sm pm-hdr-btn whitespace-nowrap" : "pm-btn pm-btn-primary text-sm py-2 px-3 sm:px-4 whitespace-nowrap"}>Start free</Link>
            </>
          )}
        </div>
      </div>

      {/* Sign-out confirmation */}
      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent data-testid="signout-confirm-modal" className="bg-pm-surface">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display text-2xl">Sign out of Placemint?</AlertDialogTitle>
            <AlertDialogDescription className="text-pm-text2">
              Your progress is saved. You can sign back in any time and pick up where you left off.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="signout-cancel">Stay signed in</AlertDialogCancel>
            <AlertDialogAction
              data-testid="signout-confirm"
              onClick={doSignOut}
              disabled={signingOut}
              className="bg-pm-secondary text-white hover:bg-[#123A42]"
            >
              {signingOut ? "Signing out…" : "Yes, sign me out"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </header>
  );
}
