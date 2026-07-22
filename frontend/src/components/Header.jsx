import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { TID } from "../testIds";
import { Sparkles, Crown } from "lucide-react";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "./ui/alert-dialog";

// Human-readable label + accent color per plan.
const PLAN_META = {
  free:     { label: "Free",     chipClass: "pm-chip",         icon: null },
  basic:    { label: "Basic",    chipClass: "pm-chip pm-chip-primary", icon: <Sparkles size={11} /> },
  pro:      { label: "Pro",      chipClass: "pm-chip pm-chip-primary", icon: <Sparkles size={11} /> },
  max:      { label: "MAX",      chipClass: "pm-chip pm-chip-primary", icon: <Sparkles size={11} /> },
  supermax: { label: "SuperMAX", chipClass: "pm-chip pm-chip-primary", icon: <Sparkles size={11} /> },
  founder:  { label: "Founder",  chipClass: "pm-chip pm-chip-coral",   icon: <Crown size={11} /> },
};

export default function Header() {
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

  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#FAF8F3]/80 border-b border-[rgba(10,10,10,0.06)]">
      <div className="max-w-7xl mx-auto flex items-center justify-between px-6 lg:px-10 py-4">
        <Link to="/" data-testid={TID.navLogo} className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-pm-primary grid place-items-center text-white font-display font-extrabold">P</div>
          <span className="font-display text-xl font-bold tracking-tight">Placemint</span>
          <span className="pm-chip pm-chip-primary hidden sm:inline-flex ml-2">Beta</span>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm text-pm-text2">
          <a href="/#companies" className="hover:text-pm-text">Companies</a>
          <a href="/#pipeline" className="hover:text-pm-text">How it works</a>
          <a href="/#pricing" className="hover:text-pm-text">Pricing</a>
          <a href="/#faq" className="hover:text-pm-text">FAQ</a>
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
                    <span className="text-[11px] font-mono text-pm-text2" title="Runs remaining">
                      {runsLeft}/{user.runs_quota} runs
                    </span>
                  )}
                </div>
              )}
              <Link to="/dashboard" data-testid={TID.navDashboard} className="pm-btn pm-btn-ghost text-sm py-2 px-4">Dashboard</Link>
              <Link to="/deck" data-testid="nav-deck" className="pm-btn pm-btn-ghost text-sm py-2 px-4 hidden sm:inline-flex">Review deck</Link>
              <button
                data-testid={TID.navLogout}
                onClick={() => setConfirmOpen(true)}
                className="pm-btn pm-btn-ghost text-sm py-2 px-4"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" data-testid={TID.navLogin} className="pm-btn pm-btn-ghost text-sm py-2 px-4">Sign in</Link>
              <Link to="/signup" data-testid={TID.navSignup} className="pm-btn pm-btn-primary text-sm py-2 px-4">Start free</Link>
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
              className="bg-pm-secondary text-white hover:bg-[#E64B29]"
            >
              {signingOut ? "Signing out…" : "Yes, sign me out"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </header>
  );
}
