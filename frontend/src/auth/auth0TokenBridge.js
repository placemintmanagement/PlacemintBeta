// getAccessTokenSilently() only exists inside React, via the useAuth0() hook
// -- but api.js's axios interceptor is a plain module, not a component. This
// bridge is the standard way to connect the two: Auth0TokenSync (rendered
// once, inside Auth0Provider) writes the current token-getter into this
// module-level holder on every auth-state change; api.js reads it back.
let currentGetAccessTokenSilently = null;

/** @param {(() => Promise<string>) | null} getAccessTokenSilently */
export function setAuth0TokenGetter(getAccessTokenSilently) {
  currentGetAccessTokenSilently = getAccessTokenSilently;
}

/** @returns {Promise<string|null>} the current Auth0 access token, or null if not signed in / unavailable */
export async function getAuth0AccessToken() {
  if (!currentGetAccessTokenSilently) return null;
  try {
    return await currentGetAccessTokenSilently();
  } catch {
    // Not logged in via Auth0, consent required, etc. -- not an error api.js
    // callers need to see; they just proceed without an Auth0 bearer token.
    return null;
  }
}
