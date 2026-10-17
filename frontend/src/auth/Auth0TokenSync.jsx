import { useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { setAuth0TokenGetter } from "./auth0TokenBridge";
import { useAuth } from "../auth";

// Renders nothing -- just keeps auth0TokenBridge's holder pointed at the
// current getAccessTokenSilently, so api.js's interceptor always has an
// up-to-date reference. Mount once, inside Auth0Provider (see App.js).
//
// ALSO re-runs the app's own useAuth()'s refresh() (GET /auth/me) whenever
// Auth0's isAuthenticated flips true (2026-10, "wire /login to Auth0" pass):
// the app's own AuthProvider calls refresh() once on its own mount, which
// races Auth0Provider's own async cache check -- that first refresh()
// almost always fires BEFORE Auth0 has resolved a token, so it 401s and
// leaves `user` null even for a genuinely-authenticated visitor. Re-running
// refresh() here, right after setAuth0TokenGetter so the interceptor
// already has a working token getter, is what makes useAuth()'s `user`
// (college/plan/runs_used/etc. -- fields Auth0's own user object doesn't
// have) actually populate. Clears `user` on the reverse transition too, so
// an Auth0 sign-out (Auth0AuthButtons / Header's doSignOut) doesn't leave a
// stale, now-unauthenticated `user` behind.
export default function Auth0TokenSync() {
  const { isAuthenticated, getAccessTokenSilently } = useAuth0();
  const { refresh, setUser } = useAuth();

  useEffect(() => {
    setAuth0TokenGetter(isAuthenticated ? getAccessTokenSilently : null);
    if (isAuthenticated) {
      refresh();
    } else {
      setUser(null);
    }
    return () => setAuth0TokenGetter(null);
  }, [isAuthenticated, getAccessTokenSilently, refresh, setUser]);

  return null;
}
