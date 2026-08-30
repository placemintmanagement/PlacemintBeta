import React from "react";
import { useAuth0 } from "@auth0/auth0-react";

// Auth0 login/logout controls -- separate from Header's existing sign-in/
// sign-out UI (the app's own auth system) so the two aren't confused with
// each other. See Auth0ProviderWithNavigate.jsx for why this isn't wired
// into the live app-wide auth yet.
export default function Auth0AuthButtons() {
  const { isAuthenticated, isLoading, user, loginWithRedirect, logout } = useAuth0();

  if (isLoading) {
    return <span className="text-sm text-pm-text2">Loading…</span>;
  }

  if (isAuthenticated) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-sm text-pm-text2">Signed in via Auth0 as {user?.email || user?.name}</span>
        <button
          type="button"
          onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
          className="pm-btn pm-btn-ghost text-sm py-2 px-4"
        >
          Sign out (Auth0)
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => loginWithRedirect()}
      className="pm-btn pm-btn-primary text-sm py-2 px-4"
    >
      Sign in with Auth0
    </button>
  );
}
