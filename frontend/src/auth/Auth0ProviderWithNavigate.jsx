import React from "react";
import { useNavigate } from "react-router-dom";
import { Auth0Provider } from "@auth0/auth0-react";

// ---------------------------------------------------------------------------
// Auth0 flow (frontend-only integration, 2026-08):
//
// 1. A component calls loginWithRedirect() (via useAuth0()) — the browser is
//    sent to Auth0's hosted login page.
// 2. After the user authenticates, Auth0 redirects back to this app with a
//    code in the URL. Auth0Provider exchanges it for tokens automatically
//    and calls onRedirectCallback below, which strips the code from the URL
//    and returns the user to wherever they were headed (appState.returnTo).
// 3. Once authenticated, useAuth0().getAccessTokenSilently() returns a fresh
//    access token (refreshed automatically, silently, in the background).
//    auth0TokenBridge.js exposes that function outside React so api.js's
//    axios interceptor can attach it as a Bearer token on every request.
//
// UPDATED (2026-08): server.py's require_user is now Auth0-only (verifies
// via auth0_middleware.py's JWKS-based check) -- the app's own legacy
// session-cookie/JWT auth path was removed after an independent audit
// confirmed zero real user accounts existed yet. scope includes "email" so
// first-seen-sub provisioning can fetch a real email via Auth0's /userinfo
// endpoint (see auth0_middleware.get_userinfo_email).
//
// UPDATED AGAIN (2026-10, "wire /login to Auth0" pass): the real /login and
// /signup pages now call loginWithRedirect() as their primary CTA (the old
// Google-session/email-password UI is still present, collapsed under an
// "Other sign-in options" disclosure -- untouched code, just no longer the
// default path, since it issues a session nothing on the backend accepts
// anymore). App.js's `Protected` was NOT swapped for Auth0ProtectedRoute
// wholesale -- it still gates on the app's own useAuth() context (so
// Header/Dashboard/OnboardingModal etc. keep working off the SAME user
// object they always have, with its college/plan/runs_used/... fields
// Auth0's own user object doesn't carry), but now ALSO reads Auth0's own
// isAuthenticated/isLoading directly to avoid bouncing a genuinely
// authenticated visitor to /login during the brief window before
// Auth0TokenSync's refresh() (see that file) resolves. Auth0ProtectedRoute
// itself remains demonstrated only on /dev/auth0-preview, unused by any
// real route.
// ---------------------------------------------------------------------------

const AUTH0_DOMAIN = process.env.REACT_APP_AUTH0_DOMAIN;
const AUTH0_CLIENT_ID = process.env.REACT_APP_AUTH0_CLIENT_ID;
const AUTH0_AUDIENCE = process.env.REACT_APP_AUTH0_AUDIENCE;

/**
 * @param {{ children: React.ReactNode }} props
 */
export default function Auth0ProviderWithNavigate({ children }) {
  const navigate = useNavigate();

  const onRedirectCallback = (appState) => {
    navigate(appState?.returnTo || window.location.pathname);
  };

  return (
    <Auth0Provider
      domain={AUTH0_DOMAIN}
      clientId={AUTH0_CLIENT_ID}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: AUTH0_AUDIENCE,
        scope: "openid profile email",
      }}
      onRedirectCallback={onRedirectCallback}
    >
      {children}
    </Auth0Provider>
  );
}
