# -*- coding: utf-8 -*-
"""Auth0 JWT verification.

Flow: the frontend gets an access token from Auth0 (loginWithRedirect +
getAccessTokenSilently) -> sends it as `Authorization: Bearer <token>` on
every API request -> get_current_user (this module) verifies the token's
signature against Auth0's JWKS, checks expiration/audience/issuer, and
returns the token's `sub` claim as a trusted, verified user identity ->
downstream route handlers get that identity via a FastAPI dependency.

This module is deliberately auth-source-agnostic about what happens AFTER
verification -- it only proves "this sub is a real, currently-valid Auth0
user," nothing about your own user records. server.py's require_user is
what turns a verified sub into an actual (auto-provisioned if needed) user
document.

Auth0-only (2026-08): this used to be tried as a fallback AFTER the app's
own session/JWT auth (require_user_any); that dual-path logic was removed
once an independent audit confirmed zero real user accounts existed yet,
so there was no live-migration risk in going Auth0-only directly. See
server.py's require_user docstring for the real, deliberate consequence:
the app's own /login-issued sessions no longer grant access to any
Depends(require_user) route.

get_userinfo_email() below is called only on first-seen sub (new user
provisioning) -- Auth0 access tokens for a custom API audience carry no
email claim by default, so getting one requires a separate call to Auth0's
/userinfo endpoint with the same access token.
"""
from __future__ import annotations
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Header, HTTPException
from jose import jwt
from jose.exceptions import JOSEError

logger = logging.getLogger(__name__)

AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "")
AUTH0_AUDIENCE = os.environ.get("AUTH0_AUDIENCE", "")
AUTH0_ISSUER = f"https://{AUTH0_DOMAIN}/"
JWKS_URL = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
USERINFO_URL = f"https://{AUTH0_DOMAIN}/userinfo"
ALGORITHMS = ["RS256"]

# Simple TTL cache, not functools.lru_cache -- lru_cache has no time-based
# expiry on its own (it would cache the JWKS forever, across key rotations,
# until the process restarts). Auth0 keys rotate rarely, so an hour is
# plenty conservative without refetching on every request.
_JWKS_TTL_SECONDS = 3600
_jwks_cache: Dict[str, Any] = {"keys": None, "fetched_at": 0.0}

_AUTH_ERROR = HTTPException(status_code=401, detail="Not authenticated")


async def _get_jwks() -> List[Dict[str, Any]]:
    now = time.time()
    if _jwks_cache["keys"] is None or (now - _jwks_cache["fetched_at"]) > _JWKS_TTL_SECONDS:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(JWKS_URL)
            resp.raise_for_status()
        _jwks_cache["keys"] = resp.json()["keys"]
        _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]


async def _verify_token(token: str) -> Dict[str, Any]:
    """Verifies signature, expiration, audience, and issuer. Raises the
    same generic 401 (_AUTH_ERROR) on ANY failure -- bad signature,
    expired, wrong audience/issuer, malformed token, no matching key,
    unreachable JWKS -- callers must never learn WHY verification failed,
    only that it did."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JOSEError:
        raise _AUTH_ERROR

    try:
        jwks = await _get_jwks()
    except (httpx.HTTPError, KeyError, ValueError):
        raise _AUTH_ERROR

    rsa_key: Dict[str, Any] = {}
    for key in jwks:
        if key.get("kid") == unverified_header.get("kid"):
            rsa_key = {"kty": key["kty"], "kid": key["kid"], "use": key["use"], "n": key["n"], "e": key["e"]}
            break
    if not rsa_key:
        raise _AUTH_ERROR

    try:
        return jwt.decode(
            token, rsa_key, algorithms=ALGORITHMS,
            audience=AUTH0_AUDIENCE, issuer=AUTH0_ISSUER,
        )
    except JOSEError:
        raise _AUTH_ERROR


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> str:
    """FastAPI dependency: verifies the Bearer token and returns the
    trusted `sub` claim (Auth0's unique, stable user identifier). Raises
    401 with a generic message on a missing/malformed header or any
    verification failure -- use this directly on a route that should ONLY
    ever accept an Auth0 token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _AUTH_ERROR
    token = authorization.split(" ", 1)[1].strip()
    payload = await _verify_token(token)
    sub = payload.get("sub")
    if not sub:
        raise _AUTH_ERROR
    return sub


async def get_current_user_optional(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    """Same verification as get_current_user, but returns None instead of
    raising on any failure. No longer wired to anything (2026-08 -- this
    backed require_user_any's try-existing-auth-first, fall-back-to-Auth0
    pattern, removed when the dual-path fallback was dropped). Left in
    place rather than deleted: a reasonable utility for a future
    optional-auth route, and unlike get_current_user/decode_jwt/require_user
    in server.py, this isn't legacy code being replaced -- it's Auth0-native
    and simply has no current caller."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        token = authorization.split(" ", 1)[1].strip()
        payload = await _verify_token(token)
        return payload.get("sub")
    except HTTPException:
        return None


async def get_userinfo_email(access_token: str) -> Optional[str]:
    """Calls Auth0's /userinfo endpoint with an already-verified access
    token to retrieve the user's email, for first-seen-sub provisioning
    only (existing users skip this entirely -- see server.py's
    require_user). Returns None on ANY failure (network error, non-200,
    malformed response, no email in the response) -- never raises, since a
    /userinfo hiccup must not block signup; callers should log this
    themselves if they want visibility (server.py's require_user doesn't
    currently distinguish "call failed" from "call succeeded but had no
    email claim" beyond this function's own warning log, since both
    resolve to the same "provision with empty email" outcome)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Auth0 /userinfo call failed, provisioning without email: %s", e)
        return None
    email = data.get("email")
    if not email:
        logger.warning("Auth0 /userinfo returned no email claim, provisioning without email")
        return None
    return email
