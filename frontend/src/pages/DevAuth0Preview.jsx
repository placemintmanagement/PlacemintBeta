import React from "react";
import { useAuth0 } from "@auth0/auth0-react";
import Header from "../components/Header";
import Auth0AuthButtons from "../auth/Auth0AuthButtons";
import Auth0ProtectedRoute from "../auth/Auth0ProtectedRoute";

// Standing dev tool -- preview route at /dev/auth0-preview demonstrating the
// Auth0 integration (login/logout, ProtectedRoute, token retrieval) without
// wiring it into a live production route yet. See Auth0ProviderWithNavigate
// .jsx's comment block for why: the backend has no Auth0 JWT verification,
// so applying Auth0ProtectedRoute to /dashboard or /oa/:attemptId right now
// would lock out every current user (a different login system) with no
// working replacement in place. Once backend support ships, swap
// Auth0ProtectedRoute in for App.js's existing `Protected` on those routes.

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
