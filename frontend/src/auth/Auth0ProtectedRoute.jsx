import React, { useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";

/**
 * Gates its children behind Auth0 authentication -- redirects to Auth0's
 * hosted login page (loginWithRedirect) if the user isn't signed in, and
 * shows a loading state while Auth0 checks auth status on app load.
 * Mirrors App.js's existing `Protected` component's loading/redirect
 * pattern, adapted to useAuth0() instead of the app's own useAuth().
 *
 * @param {{ children: React.ReactNode }} props
 */
export default function Auth0ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      loginWithRedirect({ appState: { returnTo: window.location.pathname } });
    }
  }, [isLoading, isAuthenticated, loginWithRedirect]);

  if (isLoading || !isAuthenticated) {
    return <div className="min-h-screen grid place-items-center text-sm text-pm-text2">Loading…</div>;
  }

  return children;
}
