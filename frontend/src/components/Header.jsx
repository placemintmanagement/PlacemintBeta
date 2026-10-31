import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { useAuth } from "../auth";
import { TID } from "../testIds";
import { SHOW_PRICING } from "../featureFlags";
import { Sparkles, Crown } from "lucide-react";
import GlassLogoMark from "./glass/GlassLogoMark";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "./ui/alert-dialog";

// Human-readable label + accent color per plan. `.gl-tag` (glass.css) is
// a plain pastel-yellow pill by default; founder/paid plans get a vivid
// accent color via inline style, same "pastel token reads dull as an
// icon/badge foreground, use a dedicated vivid hex" pattern used
// throughout the rest of the glass system.
const PLAN_META = {
  free:     { label: "Free",     accent: null,      icon: null },
  basic:    { label: "Basic",    accent: "#ca8a04",  icon: <Sparkles size={11} /> },
  pro:      { label: "Pro",      accent: "#ca8a04",  icon: <Sparkles size={11} /> },
  max:      { label: "MAX",      accent: "#ca8a04",  icon: <Sparkles size={11} /> },
  supermax: { label: "SuperMAX", accent: "#ca8a04",  icon: <Sparkles size={11} /> },
  founder:  { label: "Founder",  accent: "#7c3aed",  icon: <Crown size={11} /> },
};

// `light` is accepted but no longer changes anything visually -- every
// real page already passed `light` (confirmed: only the /dev/* preview
// routes, out of scope for the glass rollout, ever used the old default
// translucent-teal variant), and the glass nav is a single light/white
// design regardless. Kept as a no-op prop rather than removed so no
// caller needs a code change for this component alone.
export default function Header({ light = false } = {}) {
  const { user, logout } = useAuth();
  const { isAuthenticated: auth0Authenticated, logout: auth0Logout } = useAuth0();
  const navigate = useNavigate();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  const plan = user ? PLAN_META[user.plan] || PLAN_META.free : null;
  const runsLeft = user ? Math.max(0, (user.runs_quota ?? 0) - (user.runs_used ?? 0)) : 0;

  // Real sign-in is now Auth0 (2026-10) -- the legacy logout() alone only
  // clears this app's own session state, leaving Auth0's own hosted
  // session (and its SDK cache) still authenticated, so the very next
  // page load would silently sign the candidate back in via
  // Auth0TokenSync. auth0Logout() redirects away, so nothing after it runs.
  const doSignOut = async () => {
    setSigningOut(true);
    await logout();
    if (auth0Authenticated) {
      auth0Logout({ logoutParams: { returnTo: window.location.origin } });
      return;
    }
    setSigningOut(false);
    setConfirmOpen(false);
    navigate("/");
  };

  return (
    // `glass-landing` reused here as the general "this subtree uses the
    // glass design system" scope marker, not landing-specific -- it's
    // just a CSS class name, and all its token/reset rules are written
    // as `.glass-landing`/`.glass-landing <descendant>`, so applying it
    // directly to this component's own root scopes everything to just
    // the header, without touching the rest of a still-teal page below
    // it (verified live: broadening these rules to the app-wide
    // `.glass-app` wrapper instead painted white over every teal page).
    // `data-theme="light"` pins it away from auto OS-dark-mode reactivity
    // for now, since no other page supports dark mode yet.
    <header className="glass-landing gl-nav" data-theme="light">
      <div>
        <Link to="/" data-testid={TID.navLogo} className="gl-logo">
          <GlassLogoMark size={28} />
          HireTric
          <span className="gl-tag" style={{ fontSize: 12, marginLeft: 4 }}>Beta</span>
        </Link>

        <div className="gl-links">
          <a href="/#companies">Companies</a>
          <a href="/#pipeline">How it works</a>
          {SHOW_PRICING && <a href="/#pricing">Pricing</a>}
          <a href="/#faq">FAQ</a>
        </div>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
          {user ? (
            <>
              {plan && (
                <div className="hidden sm:flex items-center gap-2" data-testid="header-plan-badge">
                  <span className="gl-tag" style={plan.accent ? { background: "none", border: `1px solid ${plan.accent}`, color: plan.accent } : undefined} title={`Plan: ${plan.label}`}>
                    {plan.icon}{plan.label}
                  </span>
                  {user.plan !== "founder" && (
                    <span style={{ fontSize: 11, color: "var(--gl-muted)" }} title="Runs remaining">
                      {runsLeft}/{user.runs_quota} runs
                    </span>
                  )}
                </div>
              )}
              <Link to="/dashboard" data-testid={TID.navDashboard} className="gl-btn">Dashboard</Link>
              <div className="hidden sm:flex">
                <Link to="/deck" data-testid="nav-deck" className="gl-btn">Review deck</Link>
              </div>
              <button data-testid={TID.navLogout} onClick={() => setConfirmOpen(true)} className="gl-btn">
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" data-testid={TID.navLogin} className="gl-btn">Sign in</Link>
              <Link to="/signup" data-testid={TID.navSignup} className="gl-btn y">Start free</Link>
            </>
          )}
        </div>
      </div>

      {/* Sign-out confirmation */}
      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent data-testid="signout-confirm-modal">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-2xl" style={{ fontFamily: "Outfit, system-ui, sans-serif" }}>Sign out of HireTric?</AlertDialogTitle>
            <AlertDialogDescription>
              Your progress is saved. You can sign back in any time and pick up where you left off.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="signout-cancel">Stay signed in</AlertDialogCancel>
            <AlertDialogAction
              data-testid="signout-confirm"
              onClick={doSignOut}
              disabled={signingOut}
            >
              {signingOut ? "Signing out…" : "Yes, sign me out"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </header>
  );
}
