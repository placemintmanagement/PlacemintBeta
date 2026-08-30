import { useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { setAuth0TokenGetter } from "./auth0TokenBridge";

// Renders nothing -- just keeps auth0TokenBridge's holder pointed at the
// current getAccessTokenSilently, so api.js's interceptor always has an
// up-to-date reference. Mount once, inside Auth0Provider (see App.js).
export default function Auth0TokenSync() {
  const { isAuthenticated, getAccessTokenSilently } = useAuth0();

  useEffect(() => {
    setAuth0TokenGetter(isAuthenticated ? getAccessTokenSilently : null);
    return () => setAuth0TokenGetter(null);
  }, [isAuthenticated, getAccessTokenSilently]);

  return null;
}
