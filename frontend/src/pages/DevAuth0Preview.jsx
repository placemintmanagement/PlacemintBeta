import React from "react";
import { useAuth0 } from "@auth0/auth0-react";
import Header from "../components/Header";
import Auth0AuthButtons from "../auth/Auth0AuthButtons";
import Auth0ProtectedRoute from "../auth/Auth0ProtectedRoute";

// Standing dev tool -- preview route at /dev/auth0-preview demonstrating the
// raw Auth0 SDK primitives (login/logout, Auth0ProtectedRoute, token
// retrieval) in isolation. UPDATE (2026-10): the real app IS wired to Auth0
// now -- Login.jsx/Signup.jsx call loginWithRedirect(), App.js's `Protected`
// gates on Auth0's isAuthenticated (alongside the app's own useAuth(),
// which Auth0TokenSync keeps synced -- see that file's own comment), and
// server.py's require_user is Auth0-only. This page's own
// Auth0ProtectedRoute/ProtectedContent below are NOT what gates /dashboard
// etc. in production (App.js's `Protected` is) -- this route just stays a
// standalone sanity check of the bare SDK primitives.

function ProtectedContent() {
  const { user } = useAuth0();
  return (
    <div className="pm-card p-6 max-w-xl mx-auto mt-6">
      <div className="font-display text-lg font-semibold mb-2">You're in: Auth0ProtectedRoute passed</div>
      <div className="text-sm text-pm-text2">Signed in as {user?.email || user?.name}</div>
    </div>
  );
}

export default function DevAuth0Preview() {
  return (
    <div>
      <Header />
      <div className="max-w-3xl mx-auto px-6 py-10">
        <div className="font-display text-2xl font-bold mb-2">Auth0 integration preview</div>
        <div className="text-sm text-pm-text2 mb-6">
          Not wired into the live app yet. This route exists to demonstrate login/logout and
          route protection working end-to-end on the frontend.
        </div>
        <Auth0AuthButtons />
        <Auth0ProtectedRoute>
          <ProtectedContent />
        </Auth0ProtectedRoute>
      </div>
    </div>
  );
}
