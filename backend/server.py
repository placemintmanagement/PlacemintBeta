"""Placemint backend \u2014 FastAPI.

Single-file layout intentionally: keeps the router surface easy to inspect. Auth,
resume checker, OA runner, interview, final report, payments (Razorpay) all live
here. AI calls are delegated to ai_service.py.
"""
from __future__ import annotations

import os
import io
import re
import random
import difflib
import asyncio
import uuid
import hmac
import hashlib
import logging
import json
import subprocess
import tempfile
import bcrypt
import jwt
import requests
import razorpay
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import (
    FastAPI,
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    UploadFile,
    File,
    Form,
    Cookie,
    Header,
)
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, Field
import pdfplumber

from companies import COMPANIES, DEPARTMENTS, get_company, get_department
from services import capgemini_tiers
from services.code_runner import run_code as _lang_run_code, run_tests as _lang_run_tests, SUPPORTED_LANGUAGES
from banks.problem_bank import sample_problems as _sample_problems
from banks import problem_bank
from banks import debugging_bank
from banks import ai_assisted_bank
from services.ai_service import (
    call_json,
    call_json_gpt,
    call_text,
    SONNET,
    stage_sufficiency_prompt,
    bug_explanation_grading_prompt,
    resume_prompt,
    mcq_prompt,
    coding_prompt,
    pseudocode_prompt,
    comm_prompt,
    grammar_prompt,
    comprehension_prompt,
    automata_fix_prompt,
    essay_prompt,
    grade_essay_prompt,
    speaking_prompt,
    communication_speaking_prompts,
    grade_spoken_response_prompt,
    reading_listening_prompt,
    transcribe_audio,
    grade_coding_prompt,
    interview_plan_prompt,
    grade_answer_prompt,
    final_report_prompt,
    INTERVIEW_SYSTEM,
    GRADING_INJECTION_DEFENSE,
    flag_suspicious_grading,
)
from banks import mcq_pool
from banks import mcq_static_bank
from games import gamified_round
from core import entitlements
from core import auth0_middleware
# Merged (2026-08 restructure) from capgemini_round1_section1..4.py into one
# per-company module -- see that file's own docstring for the symbol-rename
# collision list. Call sites below (capgemini_round1_section1.draw_section1_
# questions(...) etc.) were updated to capgemini_recruitment_process.<name>
# accordingly; the function names themselves are unchanged.
from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini import (
    capgemini_recruitment_process,
)
from collections import Counter

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---- Database ---------------------------------------------------------------

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

# ---- Config -----------------------------------------------------------------

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_ALGO = "HS256"
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

# Emails that bypass all payment gates and quota limits. Comma-separated env var
# `PAYMENT_BYPASS_EMAILS` can extend this list at runtime.
PAYMENT_BYPASS_EMAILS = {
    "prashati02@gmail.com",
    "deanushkaforwork@gmail.com",
}
_env_bypass = os.environ.get("PAYMENT_BYPASS_EMAILS", "")
for _e in _env_bypass.split(","):
    _e = _e.strip().lower()
    if _e:
        PAYMENT_BYPASS_EMAILS.add(_e)


def is_bypass_email(email: str) -> bool:
    return (email or "").strip().lower() in PAYMENT_BYPASS_EMAILS

_razorpay_client: Optional[razorpay.Client] = None
if RAZORPAY_KEY_ID and not RAZORPAY_KEY_ID.endswith("XXXXXXXXXXXX"):
    try:
        _razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except Exception as e:  # pragma: no cover
        logger.warning("Razorpay client init failed: %s", e)

# ---- App --------------------------------------------------------------------

app = FastAPI(title="Placemint API")
api = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static media (2026-08) -- no asset-storage convention existed anywhere in
# this codebase before Capgemini Round 1 Section 5 (listening_comprehension)
# needed to serve real audio files; this is that new pattern, flagged
# explicitly per the audio-generation task's own instructions. Plain local
# disk under backend/media/, served directly by FastAPI's StaticFiles --
# deliberately the simplest thing that works today, not a CDN/object-store
# integration (no credentials for one exist in this codebase, and inventing
# a new external dependency wasn't asked for). Mounted at app-level "/media"
# (NOT under the "/api" prefix "api" uses below) -- matches the audio_url
# values already written onto capgemini_round1_bank docs
# (e.g. "/media/capgemini_round1_audio/<clip_id>.wav") exactly as stored.
MEDIA_DIR = os.path.join(ROOT_DIR, "media")
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# ---- Utilities --------------------------------------------------------------

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat()


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def make_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": int(now_utc().timestamp()),
        "exp": int((now_utc() + timedelta(days=7)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


# ---- Auth dependency --------------------------------------------------------
# Auth0-only (2026-08, replacing the old dual-path require_user_any). The
# app's own session-cookie/JWT auth check (get_current_user/decode_jwt/the
# old require_user) was REMOVED here -- confirmed via a repo-wide search
# that nothing else calls them (only require_user_any depended on them, and
# require_user_any itself had no other callers either). An independent
# audit confirmed zero real user accounts exist in db.users yet (all 23
# were test/seed data), so there was no live-migration risk in dropping the
# fallback rather than carrying it as dead weight.
#
# NOTE -- real consequence, not just an internal cleanup: /auth/signup,
# /auth/login, /auth/google/session, and /auth/logout are UNTOUCHED (they're
# a separate concern -- account creation / session issuance, not route
# gating) and still create accounts and set session cookies exactly as
# before. But since NOTHING reads that cookie/JWT anymore, those flows are
# now functionally dead ends for reaching any Depends(require_user) route --
# including /auth/me, which the frontend's OWN AuthProvider polls to
# determine login state. The frontend's Protected/useAuth() (App.js) was
# NOT updated to use Auth0 in this pass (out of scope here) -- so a user who
# logs in via the app's own /login page will still see protected pages
# render client-side, but every API call they make will now 401.
# ---- Test-only auth bypass (2026-08, E2E click-through testing) -----------
# Exists so a scripted Playwright run can authenticate as a designated
# synthetic user WITHOUT a real Auth0 login (no test Auth0 tenant/user
# credentials exist in this repo, and minting a token that would pass real
# Auth0 JWT verification is not possible from our backend at all -- Auth0
# signs with a private key only Auth0 holds; RS256 is asymmetric). This is
# NOT a weakening of auth0_middleware's real verification -- that module is
# completely unmodified. It's ONE extra early-exit branch here, in
# server.py's own require_user, that:
#   1. Only runs its check at all when os.environ.get("ENVIRONMENT") == "test"
#      -- re-read fresh on every request, never cached -- which is never set
#      by any real deployment (this repo has no ENVIRONMENT var today at
#      all; introduced solely for this gate). A production .env/deployment
#      config that never sets this is safe by simple omission, not by
#      remembering to disable something.
#   2. EVEN THEN, requires the caller to also present TEST_AUTH_TOKEN (a
#      second, separate, random secret -- generated locally, gitignored,
#      never a JWT, never known to or issued by Auth0) as the literal Bearer
#      value, compared via hmac.compare_digest (constant-time, avoids a
#      timing side-channel on the comparison itself).
#   3. Falls through to the REAL, unmodified auth0_middleware.get_current_user
#      check in EVERY other case -- including when ENVIRONMENT=="test" but
#      the token isn't the exact test secret, so a genuine Auth0 token still
#      authenticates normally even inside a test-mode process.
# Net effect: a real user's Auth0 token takes the identical code path, with
# identical verification, in every environment. Only a caller who both (a)
# is talking to a process explicitly started with ENVIRONMENT=test AND
# (b) knows TEST_AUTH_TOKEN can ever reach this branch's success case.
_TEST_BYPASS_USER_SUB = "test-bypass|e2e-runner"


def _test_bypass_active() -> bool:
    return os.environ.get("ENVIRONMENT") == "test"


if _test_bypass_active():
    logger.warning("=" * 70)
    logger.warning("AUTH0 TEST BYPASS IS ACTIVE (ENVIRONMENT=test).")
    logger.warning("This must NEVER be set in a production deployment.")
    logger.warning("=" * 70)


async def _resolve_auth0_sub(authorization: Optional[str]) -> str:
    if _test_bypass_active():
        test_token = os.environ.get("TEST_AUTH_TOKEN", "")
        if (
            test_token
            and authorization
            and authorization.lower().startswith("bearer ")
            and hmac.compare_digest(authorization.split(" ", 1)[1].strip(), test_token)
        ):
            return _TEST_BYPASS_USER_SUB
    # Real, unmodified Auth0 verification -- same function, same behavior,
    # called directly instead of via Depends() so this can conditionally
    # short-circuit above it; auth0_middleware.get_current_user itself is
    # untouched and raises its own 401 on any failure, exactly as before.
    return await auth0_middleware.get_current_user(authorization)


async def require_user(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Verifies the Auth0 access token (via _resolve_auth0_sub above, which
    is real Auth0 verification in every case except the explicit,
    doubly-gated test bypass -- see that function's docstring), then looks
    up or auto-provisions the corresponding user document.

    /userinfo is only ever called on first-seen sub (existing users skip
    it entirely -- no extra network call on every request). A /userinfo
    failure never blocks provisioning: logs a warning and proceeds with an
    empty email, per spec.

    Email collision handling: if /userinfo DOES return an email, and that
    email already belongs to a different (pre-Auth0) user record, this
    does NOT merge or overwrite -- _create_user_record's auth0_sub lookup
    means a genuinely new document gets created for this sub regardless
    (there's no unique index on users.email, so this can't fail at the DB
    level either) -- but the collision is logged explicitly as a WARNING so
    it's visible rather than silently creating two accounts for one real
    person. Deliberately not resolved automatically -- flagged for an
    explicit decision, per spec."""
    auth0_sub = await _resolve_auth0_sub(authorization)
    existing = await db.users.find_one({"auth0_sub": auth0_sub}, {"_id": 0})
    if existing:
        return existing

    email = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        email = await auth0_middleware.get_userinfo_email(token) or ""

    if email:
        collision = await db.users.find_one({"email": email}, {"_id": 0})
        if collision:
            logger.warning(
                "Auth0 email collision on first-seen provisioning: sub=%s email=%s "
                "already belongs to user_id=%s (auth_provider=%s) -- creating a "
                "SEPARATE Auth0-keyed record, NOT merging.",
                auth0_sub, email, collision.get("user_id"), collision.get("auth_provider"),
            )

    return await _create_user_record(email=email, name="Auth0 User", auth_provider="auth0", auth0_sub=auth0_sub)


# =============================================================================
#  Auth
# =============================================================================

class SignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


async def _create_user_record(
    email: str,
    name: str,
    picture: str = "",
    password_hash: Optional[str] = None,
    auth_provider: str = "password",
    auth0_sub: Optional[str] = None,
) -> Dict[str, Any]:
    """auth0_sub (2026-08, Auth0 JWT verification middleware): Auth0 access
    tokens for a custom API audience carry `sub` but typically no email
    claim, so Auth0-provisioned users can't be deduped by email like every
    other auth_provider here. When auth0_sub is given, lookup/dedup happens
    on that field instead — email may legitimately be empty for these
    users. The internal `user_id` stays a normal new_id("user") either way
    (not the raw sub), so every existing foreign-key relationship
    (oa_attempts.user_id, etc.) keeps its established id shape."""
    existing = await db.users.find_one(
        {"auth0_sub": auth0_sub} if auth0_sub else {"email": email}, {"_id": 0},
    )
    if existing:
        # Owner-bypass emails always run on the unlimited "founder" plan even if
        # they signed up before being whitelisted.
        if is_bypass_email(email) and existing.get("plan") != "founder":
            await db.users.update_one(
                {"user_id": existing["user_id"]},
                {"$set": {"plan": "founder", "runs_quota": 999999, "runs_used": 0}},
            )
            existing["plan"] = "founder"
            existing["runs_quota"] = 999999
            existing["runs_used"] = 0
        return existing
    user_id = new_id("user")
    bypass = is_bypass_email(email)
    doc = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "auth_provider": auth_provider,
        "created_at": iso(now_utc()),
        "plan": "founder" if bypass else "free",
        "runs_used": 0,
        # runs_quota retained for legacy read-paths that haven't been migrated
        # yet; runs_remaining_on_plan() is the source of truth going forward.
        "runs_quota": 999999 if bypass else entitlements.FREE_RUN_LIMIT_DURING_CONTEST,
        "credits": 0,
        "company_selections": [],
        "plan_started_at": iso(now_utc()) if bypass else None,
        "plan_expires_at": None,
        "runs_period_start": None,
        "college": "",
        "branch": "",
        "graduation_year": "",
        "target_role": "",
        "email_verified": auth_provider == "google" or bypass,
    }
    if password_hash:
        doc["password_hash"] = password_hash
    if auth0_sub:
        doc["auth0_sub"] = auth0_sub
    await db.users.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.post("/auth/signup")
async def signup(body: SignupIn, response: Response):
    existing = await db.users.find_one({"email": body.email}, {"_id": 0})
    if existing:
        raise HTTPException(400, "Email already registered")
    user = await _create_user_record(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        auth_provider="password",
    )
    token = make_jwt(user["user_id"])
    response.set_cookie(
        "session_token", token, httponly=True, secure=True, samesite="none",
        max_age=7 * 24 * 3600, path="/",
    )
    user.pop("password_hash", None)
    return {"user": user, "token": token}


@api.post("/auth/login")
async def login(body: LoginIn, response: Response):
    user = await db.users.find_one({"email": body.email})
    if not user or not user.get("password_hash"):
        raise HTTPException(401, "Invalid credentials")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    # Auto-upgrade bypass emails on login (in case they signed up before whitelisting).
    if is_bypass_email(user["email"]) and user.get("plan") != "founder":
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"plan": "founder", "runs_quota": 999999, "runs_used": 0}},
        )
        user["plan"] = "founder"
        user["runs_quota"] = 999999
        user["runs_used"] = 0
    token = make_jwt(user["user_id"])
    response.set_cookie(
        "session_token", token, httponly=True, secure=True, samesite="none",
        max_age=7 * 24 * 3600, path="/",
    )
    user.pop("_id", None)
    user.pop("password_hash", None)
    return {"user": user, "token": token}


@api.post("/auth/google/session")
async def google_session(request: Request, response: Response):
    """Exchange Emergent OAuth session_id for our session token."""
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id required")
    try:
        r = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
            timeout=10,
        )
        if r.status_code != 200:
            raise HTTPException(401, f"OAuth exchange failed: {r.text[:200]}")
        data = r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"OAuth exchange error: {e}")

    email = data["email"]
    name = data.get("name") or email.split("@")[0]
    picture = data.get("picture") or ""
    session_token = data["session_token"]

    user = await _create_user_record(email=email, name=name, picture=picture, auth_provider="google")
    # Update name/picture if changed
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"name": name, "picture": picture}})

    await db.user_sessions.insert_one({
        "user_id": user["user_id"],
        "session_token": session_token,
        "expires_at": iso(now_utc() + timedelta(days=7)),
        "created_at": iso(now_utc()),
    })

    response.set_cookie(
        "session_token", session_token, httponly=True, secure=True, samesite="none",
        max_age=7 * 24 * 3600, path="/",
    )
    user.pop("password_hash", None)
    return {"user": user}


@api.get("/auth/me")
async def me(user: Dict[str, Any] = Depends(require_user)):
    # Roll the 30-day window forward before returning state, so the dashboard
    # never shows stale runs_used for Basic/Pro users past their reset date.
    reset_op = entitlements.maybe_reset_period(user)
    if reset_op:
        await db.users.update_one({"user_id": user["user_id"]}, reset_op)
        user["runs_used"] = 0
        user["runs_period_start"] = entitlements._now().isoformat()
    return {**user, "entitlements": entitlements.build_state(user)}


class CompanySelectionIn(BaseModel):
    add: Optional[str] = None      # company_id to add
    remove: Optional[str] = None   # company_id to swap out


@api.post("/user/company-selection")
async def update_company_selection(body: CompanySelectionIn, user: Dict[str, Any] = Depends(require_user)):
    """Free/Basic/Pro users need this to swap a company slot once they've hit
    the cap. MAX/SuperMAX/founder don't need it (cap=None) but the endpoint
    still returns the current state."""
    plan = user.get("plan", "free")
    limits = entitlements.PLAN_LIMITS.get(plan, {})
    cap = limits.get("company_cap")
    selections: List[str] = list(user.get("company_selections", []) or [])

    if body.remove and body.remove in selections:
        selections = [c for c in selections if c != body.remove]
    if body.add:
        if not get_company(body.add):
            raise HTTPException(404, "Company not found")
        if body.add in selections:
            pass  # already selected — idempotent
        elif cap is None or len(selections) < cap:
            selections.append(body.add)
        else:
            raise HTTPException(400, {
                "code": "company_cap_reached",
                "message": "Remove a company first to add a new one.",
                "cap": cap,
                "current_selections": selections,
            })

    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"company_selections": selections}},
    )
    user["company_selections"] = selections
    return {"company_selections": selections, "cap": cap, "entitlements": entitlements.build_state(user)}


@api.post("/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(default=None)):
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


class ProfileIn(BaseModel):
    college: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[str] = None
    target_role: Optional[str] = None
    name: Optional[str] = None


@api.patch("/auth/profile")
async def update_profile(body: ProfileIn, user: Dict[str, Any] = Depends(require_user)):
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if updates:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": updates})
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return fresh


# =============================================================================
#  Email verification + password reset (dev-mode: no real email sender).
#
#  All tokens are stored server-side with a 30-minute expiry. The "link"
#  is (a) printed to backend logs, (b) surfaced in the JSON response as
#  ``dev_link`` while we're in dev mode. When a real email transport is added
#  later, we simply stop returning ``dev_link`` and call send_email() instead.
# =============================================================================

def _new_token(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


async def _create_token(kind: str, user_id: str, ttl_minutes: int = 30) -> str:
    token = _new_token(kind)
    await db.auth_tokens.insert_one({
        "token": token,
        "kind": kind,  # "verify_email" | "reset_password"
        "user_id": user_id,
        "expires_at": iso(now_utc() + timedelta(minutes=ttl_minutes)),
        "used": False,
        "created_at": iso(now_utc()),
    })
    return token


async def _consume_token(token: str, kind: str) -> Optional[str]:
    doc = await db.auth_tokens.find_one({"token": token, "kind": kind, "used": False})
    if not doc:
        return None
    exp = doc.get("expires_at")
    if isinstance(exp, str):
        exp = datetime.fromisoformat(exp)
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp and exp < now_utc():
        return None
    await db.auth_tokens.update_one({"_id": doc["_id"]}, {"$set": {"used": True, "used_at": iso(now_utc())}})
    return doc["user_id"]


def _dev_link(request: Request, path: str, token: str) -> str:
    """Return a relative path with the token as a query param. Frontend prepends
    its own origin so the link works regardless of the ingress hostname.
    """
    return f"{path}?token={token}"


@api.post("/auth/email/send-verification")
async def send_verification(request: Request, user: Dict[str, Any] = Depends(require_user)):
    if user.get("email_verified"):
        return {"ok": True, "already_verified": True}
    token = await _create_token("verify_email", user["user_id"])
    link = _dev_link(request, "/verify-email", token)
    logger.info("EMAIL VERIFICATION link for %s -> %s", user["email"], link)
    return {"ok": True, "dev_link": link, "token": token, "expires_in_minutes": 30}


class VerifyEmailIn(BaseModel):
    token: str


@api.post("/auth/email/verify")
async def verify_email(body: VerifyEmailIn):
    user_id = await _consume_token(body.token, "verify_email")
    if not user_id:
        raise HTTPException(400, "Invalid or expired verification link")
    await db.users.update_one({"user_id": user_id}, {"$set": {"email_verified": True}})
    return {"ok": True}


class ForgotPasswordIn(BaseModel):
    email: EmailStr


@api.post("/auth/password/forgot")
async def forgot_password(body: ForgotPasswordIn, request: Request):
    """Returns 200 whether or not the email exists (prevents user enumeration).
    In dev mode we still surface the dev_link so testing is possible."""
    user = await db.users.find_one({"email": body.email}, {"_id": 0})
    resp = {"ok": True, "message": "If that email exists, a reset link was sent."}
    if not user or user.get("auth_provider") != "password":
        return resp
    token = await _create_token("reset_password", user["user_id"], ttl_minutes=30)
    link = _dev_link(request, "/reset-password", token)
    logger.info("PASSWORD RESET link for %s -> %s", body.email, link)
    resp["dev_link"] = link
    resp["token"] = token
    resp["expires_in_minutes"] = 30
    return resp


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=6)


@api.post("/auth/password/reset")
async def reset_password(body: ResetPasswordIn):
    user_id = await _consume_token(body.token, "reset_password")
    if not user_id:
        raise HTTPException(400, "Invalid or expired reset link")
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"password_hash": hash_password(body.new_password)}},
    )
    # Invalidate all other active reset tokens for this user.
    await db.auth_tokens.update_many(
        {"user_id": user_id, "kind": "reset_password", "used": False},
        {"$set": {"used": True}},
    )
    return {"ok": True}


# =============================================================================
#  Companies
# =============================================================================

@api.get("/companies")
async def list_companies():
    return {"companies": COMPANIES}


@api.get("/companies/{company_id}")
async def get_company_detail(company_id: str):
    c = get_company(company_id)
    if not c:
        raise HTTPException(404, "Company not found")
    return c


# =============================================================================
#  Departments
# =============================================================================

@api.get("/departments")
async def list_departments():
    return {"departments": DEPARTMENTS}


@api.get("/departments/{department_id}/companies")
async def get_department_companies(department_id: str):
    dept = get_department(department_id)
    if not dept:
        raise HTTPException(404, "Department not found")
    companies = [c for c in COMPANIES if c.get("department") == department_id]
    return {"department": dept, "companies": companies}


# =============================================================================
#  Resume checker
# =============================================================================

@api.post("/resume/analyze")
async def analyze_resume(
    company_id: str = Form(...),
    role: str = Form("Software Engineer"),
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(require_user),
):
    company = get_company(company_id)
    if not company:
        raise HTTPException(404, "Company not found")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(400, "PDF too large (max 5MB)")

    # Extract text from PDF
    resume_text = ""
    try:
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages[:8]:
                resume_text += (page.extract_text() or "") + "\n"
    except Exception as e:
        raise HTTPException(400, f"Could not read PDF: {e}")

    if not resume_text.strip():
        raise HTTPException(400, "PDF appears to be empty or is a scanned image (no text layer).")

    system = "You are a senior tech recruiter. Return only strict JSON.\n\n" + GRADING_INJECTION_DEFENSE
    prompt = resume_prompt(company["name"], role, resume_text)
    result = await call_json(system, prompt, model=SONNET)
    if not isinstance(result, dict):
        result = {"strengths": [], "weaknesses": [], "extracted_projects": [], "fit_score": 50, "verdict": "Analysis unavailable."}
    result = _attach_grading_flag(result, score_key="fit_score")

    resume_id = new_id("resume")
    doc = {
        "resume_id": resume_id,
        "user_id": user["user_id"],
        "company_id": company_id,
        "role": role,
        "analysis": result,
        "resume_text_sample": resume_text[:2000],
        "created_at": iso(now_utc()),
    }
    await db.resumes.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/resume/{resume_id}")
async def get_resume(resume_id: str, user: Dict[str, Any] = Depends(require_user)):
    doc = await db.resumes.find_one({"resume_id": resume_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Not found")
    return doc


@api.get("/resume")
async def list_my_resumes(user: Dict[str, Any] = Depends(require_user)):
    docs = await db.resumes.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"resumes": docs}


# =============================================================================
#  OA runner
# =============================================================================

class StartOAIn(BaseModel):
    company_id: str
    resume_id: Optional[str] = None
    cluster: Optional[str] = None


async def _validate_coding_problem(problem: Dict[str, Any]) -> Dict[str, Any]:
    """Run the AI's reference solution against every test case and OVERWRITE
    the AI-claimed expected_output with the actual stdout. This eliminates the
    common failure mode where the LLM hallucinates an incorrect expected value
    for its own problem \u2013 which then marks correct submissions as wrong.

    If the reference solution errors or times out on a test, we DROP that test.
    If NONE of the visible tests survive, the problem is unusable and we mark
    it with ``_reference_broken: True`` so the frontend can hide it.
    """
    ref = problem.get("reference_solution") or ""
    if not ref.strip():
        problem["_reference_broken"] = True
        return problem

    async def _fix(tests_key: str):
        tests = problem.get(tests_key) or []
        fixed = []
        for t in tests:
            stdin = str(t.get("input", ""))
            # Off-load the sync subprocess call so we don't block the event loop.
            result = await asyncio.to_thread(_lang_run_code, "python", ref, stdin, 3)
            if result.get("timed_out") or result.get("exit_code") != 0:
                logger.warning(
                    "ref-sol failed for problem %s (%s): %s",
                    problem.get("id"), tests_key, (result.get("stderr") or result.get("error") or "")[:120],
                )
                continue
            actual = (result.get("stdout") or "").strip()
            fixed.append({"input": stdin, "expected_output": actual})
        return fixed

    v = await _fix("visible_tests")
    h = await _fix("hidden_tests")
    problem["visible_tests"] = v
    problem["hidden_tests"] = h
    if not v:
        # No usable visible tests \u2013 problem is broken. Mark it; the frontend
        # will treat these problems as skipped so users never lose marks on them.
        problem["_reference_broken"] = True
    return problem


async def _validate_coding_batch(problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not problems:
        return problems
    validated = await asyncio.gather(*[_validate_coding_problem(p) for p in problems], return_exceptions=True)
    out = []
    for orig, res in zip(problems, validated):
        if isinstance(res, Exception):
            logger.warning("validation crashed for %s: %s", orig.get("id"), res)
            continue  # drop crashed problems entirely
        if not res.get("_reference_broken"):
            # Strip reference_solution before returning so the frontend never sees the answer.
            res.pop("reference_solution", None)
            out.append(res)
        else:
            logger.warning("dropping broken coding problem %s", res.get("id"))
    # If EVERY problem was broken (very rare), fall back to the originals so the
    # user isn't left with a zero-question section. They'll still be marked
    # skipped by the grader.
    if not out:
        for p in problems:
            p["_reference_broken"] = True
            p.pop("reference_solution", None)
        return problems
    return out


async def _store_hidden_answer_key(attempt_id: str, section_key: str, question_id: str, key_data: Any) -> None:
    """Persists an answer key that must never reach the client (e.g. Grid
    Challenge's correct value) — a field on the SAME oa_attempts document,
    excluded from the GET /oa/{attempt_id} projection but freely readable by
    server-side grading code via its own (unfiltered) find_one call."""
    await db.oa_attempts.update_one(
        {"attempt_id": attempt_id},
        {"$set": {f"_hidden_answer_keys.{section_key}.{question_id}": key_data}},
    )


def _get_hidden_answer_key(attempt: dict, section_key: str, question_id: str) -> Any:
    return (attempt.get("_hidden_answer_keys") or {}).get(section_key, {}).get(str(question_id))


async def _generate_extra_topics(company_name: str, extra_topics: List[dict], diff: Optional[str], user_id: str, static_only: bool = False) -> List[dict]:
    """Shared per-topic pool-or-live-verify loop — pulled out of the
    pseudocode branch's extra_topics handling (Capgemini's OOPS/DBMS/OS/CN
    fix) so a plain topic-only MCQ section (e.g. LTIMindtree's Computer
    Science: DBMS/OOPS/OS, no pseudocode content at all) can reuse the exact
    same mechanism without going through the pseudocode stype.

    90/10 static-bank/live split for the 8 canonical topics (mcq_static_bank.py,
    changed 2026-07-21 from the original 50/50): each topic pulls ceil(tcount*0.9)
    from the static bank (excluding this candidate's already-seen questions) and
    backfills the rest — including any static shortfall — from the existing
    pool-or-live-verify path, shuffled together before being tagged and returned.

    static_only=True (Capgemini Round 2 technical): no LLM call at all. Each
    topic is served from the static bank; any shortfall is filled with the
    candidate's least-recently-seen static questions, with a warning logged."""
    data: List[dict] = []
    for t in extra_topics:
        tkey = t.get("key")
        tname = t.get("name", tkey)
        tcount = t.get("count", 5)
        if not tkey:
            continue
        if static_only:
            if tkey not in mcq_static_bank.CANONICAL_TOPICS:
                logger.warning("static-only draw: topic %r has no static bank; %d questions unfilled", tkey, tcount)
                continue
            got, reused, unfilled = await mcq_static_bank.sample_static_with_reuse(user_id, tkey, tcount)
            if reused or unfilled:
                logger.warning(
                    "static bank shortfall for topic %r: requested %d, reused %d, unfilled %d (company %s)",
                    tkey, tcount, reused, unfilled, company_name,
                )
            random.shuffle(got)
            for q in got:
                q["topic"] = tname
            data = data + got
            continue
        static_items: List[dict] = []
        live_n = tcount
        if tkey in mcq_static_bank.CANONICAL_TOPICS:
            static_items, live_n = await mcq_static_bank.sample_mixed_static_part(user_id, tkey, tcount)
        got = list(static_items)
        if live_n > 0:
            pool_key = f"core-{tkey}"
            live_got = await mcq_pool.pop_from_pool(company_name, pool_key, tname, live_n)
            if len(live_got) < live_n:
                needed = live_n - len(live_got)
                extra = await mcq_pool.fallback_live_verify_topic(company_name, tkey, tname, needed, diff)
                live_got = live_got + extra
            got.extend(live_got)
        random.shuffle(got)
        for q in got:
            q["topic"] = tname
        data = data + got
    return data


async def _generate_topic_mix(company_name: str, count: int, topic_groups: List[dict], diff: Optional[str], section_key: str, user_id: str) -> List[dict]:
    """Wipro's blended Quant+Logical+Verbal Aptitude Test — 90/10 static-bank/live
    split PER SUB-GROUP (added 2026-07-22; previously always 100% live via one
    combined mcq_pool.fallback_live_verify_topic_mix call for the whole section).

    Each topic_group needs its own canonical `key` (mcq_static_bank.CANONICAL_TOPICS)
    to participate; a group without one stays 100% live for its own share only.
    The live shortfall per group is generated via the SAME per-group topic-mix
    prompt as before (fallback_live_verify_topic_mix, called with topic_groups=
    [just this group]) -- preserving Wipro's specific sub-topics list (Time &
    Work/TSD/etc.) for the live portion, instead of falling back to the generic
    topic hint text every plain aptitude/reasoning/verbal section's live
    fallback uses. Count/timing are unchanged -- same 15/15/15 split as before,
    only the SOURCE of each group's questions changes."""
    n_groups = max(1, len(topic_groups))
    per_group, remainder = divmod(count, n_groups)
    all_items: List[dict] = []
    for i, g in enumerate(topic_groups):
        gcount = per_group + (1 if i < remainder else 0)
        if gcount <= 0:
            continue
        gkey = g.get("key")
        static_items: List[dict] = []
        live_n = gcount
        if gkey in mcq_static_bank.CANONICAL_TOPICS:
            static_items, live_n = await mcq_static_bank.sample_mixed_static_part(user_id, gkey, gcount)
        got = list(static_items)
        if live_n > 0:
            got.extend(await mcq_pool.fallback_live_verify_topic_mix(company_name, live_n, [g], diff, section_key))
        for q in got:
            q["topic"] = g.get("name", gkey)
        all_items.extend(got)
    random.shuffle(all_items)
    return all_items[:count]


async def _generate_section_questions(company_name: str, section: dict, user_id: str, attempt_id: str, company_id: Optional[str] = None) -> List[dict]:
    system = "You are an expert Indian tech OA question setter. Return only strict JSON."
    stype = section["type"]
    count = section.get("count", 5)
    section_name = section["name"]
    diff = section.get("difficulty_target")  # 'easy_medium' | 'hard' | None
    if stype == "coding":
        # Use the curated LeetCode-style problem bank rather than asking the LLM
        # to invent problems from scratch. Bank problems have verified reference
        # solutions and byte-exact tests, eliminating the "AI hallucinated the
        # expected_output" bug class entirely.
        needs_buggy = bool(section.get("automata_fix"))
        difficulty_targets = section.get("difficulty_targets")
        # Cross-attempt repetition fix (2026-09, Phase 0 migration): merge
        # this candidate's already-seen problem ids into the exclusion set
        # from the start, so a retaken assessment doesn't repeat a coding
        # problem. `exclude_ids` previously only prevented duplicates WITHIN
        # one draw (the per-difficulty-target loop below).
        seen_ids = await problem_bank.get_seen_ids(user_id)
        if difficulty_targets:
            # Per-problem difficulty (e.g. Wipro: Problem 1 easy-medium,
            # Problem 2 hard) — sample each individually rather than one
            # blended difficulty_target across the whole count, excluding
            # already-picked ids so an overlapping tier (Medium appears in
            # both easy_medium and hard's top-up) can't draw the same
            # problem twice across separate calls.
            picks = []
            excluded: set = set(seen_ids)
            for t in difficulty_targets:
                got = _sample_problems(1, difficulty_target=t, needs_buggy=needs_buggy, exclude_ids=excluded)
                picks.extend(got)
                excluded.update(p.get("id") for p in got if p.get("id"))
            if len(picks) < count:
                extra = _sample_problems(count - len(picks), difficulty_target=diff, needs_buggy=needs_buggy, exclude_ids=excluded)
                picks.extend(extra)
        else:
            picks = _sample_problems(count, difficulty_target=diff, needs_buggy=needs_buggy, exclude_ids=seen_ids)
        if len(picks) < count:
            # Graceful shortfall: seen-exclusion left too few UNSEEN problems
            # to satisfy `count` (small 29-problem bank, long candidate
            # history) -- backfill by allowing repeats rather than
            # under-serving the section, same "never a hard failure"
            # philosophy mcq_static_bank's shortfall handling already uses.
            picked_ids = {p.get("id") for p in picks if p.get("id")}
            extra = _sample_problems(count - len(picks), difficulty_target=diff, needs_buggy=needs_buggy, exclude_ids=picked_ids)
            picks.extend(extra)
        # Normalize ids to strings (bank ids are already strings but be safe)
        for i, p in enumerate(picks):
            p.setdefault("id", f"q{i+1}")
            p["id"] = str(p["id"])
        await problem_bank.mark_seen(user_id, [p["id"] for p in picks])
        return picks
    elif stype == "debugging":
        # Round 3: Debugging Assessment. Draws exactly 1 problem via
        # debugging_bank.sample_debug_session() (2026-09, R3/R4-config-
        # correction pass: was 2 problems from 2 different topics --
        # reversed per explicit instruction; see that function's own
        # docstring). NOT the same code path as /dev/debugging-preview,
        # which uses its own hardcoded 2-problem sample array and never
        # calls sample_debug_session() at all -- confirmed via audit
        # before this change, so this change has zero effect on it.
        # Cross-attempt repetition uses debugging_bank's OWN seen tracker
        # (debugging_bank_seen collection), kept deliberately separate from
        # problem_bank's tracker -- this is its own ~25-item pool, not a
        # sub-split of the 104-item coding bank (see debugging_bank.py's
        # own comment on this).
        seen_ids = await debugging_bank.get_seen_ids(user_id)
        picks = debugging_bank.sample_debug_session(exclude_ids=seen_ids)
        await debugging_bank.mark_seen(user_id, [p["id"] for p in picks])
        return picks
    elif stype == "ai_assisted":
        # Round 4: AI-Assisted Coding. Draws exactly 1 problem via
        # ai_assisted_bank.sample_one() -- its own seen tracker
        # (ai_assisted_bank_seen collection), same "own pool, own
        # tracker" convention as Round 3's debugging_bank. UNLIKE every
        # other branch here, this ALSO creates the live conversation's
        # session doc right now (not lazily on first message) in its own
        # db.ai_assisted_sessions collection, attempt+section_key+user
        # scoped -- so the conversation is ready the instant the
        # candidate reaches this section. This section's `questions`
        # deliberately holds only an OPAQUE {session_id, problem_id}
        # pointer, never problem/answer content -- see companies.py's
        # round4_ai_assisted comment and _strip_ai_assisted_problem's
        # docstring for why (flawed_code/corrected_code/bug_explanation_
        # key_points must never reach get_oa's response; they only ever
        # travel through session["revealed_code"], server-controlled).
        #
        # Deliberately NOT calling into /dev/ai-assisted/start's route
        # body (which builds an equivalent but NOT attempt-scoped session
        # doc for the standalone dev-preview) -- kept as two independent
        # code paths, same "dev route stays untouched, real flow is its
        # own thing" separation Round 3 used for /api/dev/debugging/run
        # vs. the real coding/debugging dispatch.
        seen_ids = await ai_assisted_bank.get_seen_ids(user_id)
        problem = ai_assisted_bank.sample_one(exclude_ids=seen_ids)
        await ai_assisted_bank.mark_seen(user_id, [problem["id"]])
        session_id = new_id("aas")
        welcome = f"Let's talk through \"{problem['title']}\". " + _AI_ASSISTED_STAGE_OPENERS["understand"]
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "attempt_id": attempt_id,
            "section_key": section["key"],
            "company_name": company_name,
            "problem_id": problem["id"],
            "problem": _strip_ai_assisted_problem(problem),
            "current_stage": "understand",
            "transcript": [{"role": "ai", "stage": "understand", "text": welcome, "at": iso(now_utc())}],
            "stage_attempts": {"understand": 0, "approach": 0, "complexity": 0, "explain_bug": 0},
            "consent_given": None,
            "self_review_result": None,
            "bug_explanation_text": None,
            "bug_explanation_score": None,
            "revealed_code": None,
            "final_outcome": None,
            "status": "in_progress",
            "created_at": iso(now_utc()),
            "completed_at": None,
        }
        await db.ai_assisted_sessions.insert_one(session)
        return [{"session_id": session_id, "problem_id": problem["id"]}]
    elif stype == "pseudocode":
        # Pseudocode sections go through the 3-stage ground-truth pipeline
        # (transpile-execute preferred; solver-agreement fallback). Ground
        # truth for these questions comes from actually running the code
        # under a Python interpreter, not from any LLM's belief.
        #
        # `extra_topics` (e.g. Capgemini's OOPS/DBMS/OS/CN) is an OPTIONAL,
        # additive layer on top of this — sections without it (Zoho's
        # r1-technical, etc.) behave exactly as before: pseudo_count falls
        # back to `count` and the loop below is a no-op. When present,
        # `pseudocode_count` controls how many pseudocode questions get
        # generated (this untouched call is never resized by the section's
        # top-level `count`, which instead reflects the section's TOTAL
        # across pseudocode + all extra topics).
        extra_topics = section.get("extra_topics") or []
        pseudo_count = section.get("pseudocode_count", count) if extra_topics else count
        # 90/10 static-bank/live split (2026-09 Phase 0 migration), same
        # pattern as every other canonical topic (mcq_static_bank.py) --
        # "pseudocode" has 130 once-verified seeded questions instead of
        # always calling the live 3-stage ground-truth pipeline. Live
        # fallback (transpile-execute/solver-agreement) stays as the safety
        # net for the 10% + any shortfall, kept deliberately rather than
        # removed now, since 130 questions isn't yet proven enough depth to
        # guarantee zero shortfalls across every company's pseudocode_count.
        static_items, live_n = await mcq_static_bank.sample_mixed_static_part(user_id, "pseudocode", pseudo_count)
        data = list(static_items)
        if live_n > 0:
            live_data = await mcq_pool.fallback_live_verify(
                company_name, section_name, section.get("key") or "pseudocode", live_n, diff,
            )
            data.extend(live_data)
        random.shuffle(data)
        for q in data:
            if isinstance(q, dict):
                q["topic"] = "Pseudocode"
        # Reuses the EXACT same topic_mcq machinery already proven for Core
        # Assessment's topic_mcq sections (topic_mcq_prompt + TOPIC_INSTRUCTIONS
        # + per-topic pool-or-live-verify) via the shared _generate_extra_topics
        # helper (also reused standalone by LTIMindtree's CS Fundamentals,
        # which has no pseudocode content at all) — invoked directly here
        # instead of through a dedicated topic_mcq-typed section, since this
        # section's signature content (pseudocode) needs to coexist alongside
        # topic coverage, not be replaced by it.
        data = data + await _generate_extra_topics(company_name, extra_topics, diff, user_id)
    elif stype == "comm":
        data = await call_json(system, comm_prompt(company_name, count, diff))
    elif stype == "grammar":
        data = await call_json(system, grammar_prompt(company_name, count, diff))
    elif stype == "comprehension":
        data = await call_json(system, comprehension_prompt(company_name, count, diff))
    elif stype == "essay":
        e = essay_prompt(company_name, section_name, target_words=section.get("target_words"))
        data = await call_json(e["system"], e["prompt"])
        if isinstance(data, dict):
            data = [data]
    elif stype == "speaking":
        sp = speaking_prompt(company_name)
        data = await call_json(sp["system"], sp["prompt"])
        if isinstance(data, dict):
            data = [data]
    elif stype == "reading_listening":
        data = await call_json(system, reading_listening_prompt(company_name, count))
    elif stype == "comm_mixed":
        # Accenture's Communication Assessment: ~half MCQ/written, ~half
        # spoken-response — a DELIBERATE deviation from Accenture's real
        # researched (all-MCQ+written) format, added by explicit choice
        # (2026-07-20), same category as Cognizant's voice sections. Each
        # generated item is tagged `mode` ("mcq" | "speaking") so a single
        # section can mix both — reuses comm_prompt (MCQ half) and the new
        # batched communication_speaking_prompts (speaking half) unchanged;
        # no new prompt machinery for the MCQ side.
        n_speaking = section.get("speaking_count", count // 2)
        n_mcq = max(0, count - n_speaking)
        mcq_items = await call_json(system, comm_prompt(company_name, n_mcq, diff)) if n_mcq else []
        if not isinstance(mcq_items, list):
            mcq_items = []
        for q in mcq_items:
            if isinstance(q, dict):
                q["mode"] = "mcq"
        speaking_items = []
        if n_speaking:
            sp = communication_speaking_prompts(company_name, n_speaking)
            speaking_items = await call_json(sp["system"], sp["prompt"])
            if not isinstance(speaking_items, list):
                speaking_items = []
        for q in speaking_items:
            if isinstance(q, dict):
                q["mode"] = "speaking"
        data = mcq_items + speaking_items
    elif stype == "voice_mixed":
        # LTIMindtree's Spoken English / Communication — reverses the earlier
        # text-only conversion for THIS company specifically (2026-07-20).
        # ALL items are voice, split into two modes: "listening" (repeat-
        # statement, reuses reading_listening_prompt, graded by deterministic
        # string similarity — see _grade_voice_mixed_section) and "speaking"
        # (open response, reuses communication_speaking_prompts, graded via
        # the essay pipeline on the transcript). Both prompt functions and the
        # underlying Groq transcription infra are the exact same ones built
        # for Cognizant/Accenture — no second implementation.
        n_listening = section.get("listening_count", count // 2)
        n_speaking = max(0, count - n_listening)
        listening_items = []
        if n_listening:
            listening_items = await call_json(system, reading_listening_prompt(company_name, n_listening))
            if not isinstance(listening_items, list):
                listening_items = []
        for q in listening_items:
            if isinstance(q, dict):
                q["mode"] = "listening"
        speaking_items = []
        if n_speaking:
            sp = communication_speaking_prompts(company_name, n_speaking)
            speaking_items = await call_json(sp["system"], sp["prompt"])
            if not isinstance(speaking_items, list):
                speaking_items = []
        for q in speaking_items:
            if isinstance(q, dict):
                q["mode"] = "speaking"
        data = listening_items + speaking_items
    elif stype == "gamified_round":
        # Registry-driven gamified round (see game_types.py / gamified_round.py).
        # Unlike every other branch here, content isn't generated by an LLM at
        # all -- it's sampled from the pre-verified puzzle_bank, already
        # stripped of correctAnswer server-side (gamified_round.strip_answer).
        # Real grading happens later against puzzle_bank via
        # gamified_round.grade_session, keyed by session_id =
        # f"{attempt_id}_{section_key}" (same convention create_session uses
        # right below) -- the answer key never touches the attempt doc.
        # gamified_round_config/puzzle_bank are keyed by the lowercase company
        # id ("capgemini"), NOT the display name ("Capgemini") that
        # `company_name` holds everywhere else in this function (used for LLM
        # prompt text) -- company_id is threaded in separately for this.
        cid = company_id or company_name
        config = await gamified_round.get_config(cid)
        game_types_list = (config.get("gameTypes") if config else None) or ["deductive_grid"]
        # EVERY game type listed in gameTypes runs in EVERY session -- not a
        # random pick-1-of-N (that was the old model, replaced 2026-08).
        #
        # drawCount (2026-10, R5-random-draw pass): OPTIONAL per-company
        # override -- when a company's gamified_round_config doc sets this
        # (currently only Capgemini, drawCount=4), that many game TYPES are
        # drawn at random from gameTypes for THIS session (no repeats within
        # the draw, since random.sample draws without replacement), instead
        # of running the full list. Every other company's config doc has no
        # drawCount field, so `config.get("drawCount")` is None for them and
        # this is a complete no-op -- game_types_list stays the full list,
        # identical to pre-2026-10 behavior. Nothing downstream (grading's
        # types_present, OARunner.jsx's groups) needs to know this happened:
        # both already derive which types are "present" from the actual
        # served puzzles, not from gameTypes' length, which is exactly what
        # makes this safe to add here alone.
        draw_count = (config.get("drawCount") if config else None)
        if draw_count and 0 < draw_count < len(game_types_list):
            game_types_list = random.sample(game_types_list, draw_count)
        # perType holds per-type tunables: subPuzzlesPerGame for the flat-list
        # types (deductive_grid/switch_challenge), instancesPerGame for
        # grid_challenge (always 1 -- it's one instance with internal blocks,
        # not N independent sub-puzzles).
        per_type_config = (config.get("perType") if config else None) or {}

        # Persist perType tunables (timerPerPuzzle, poolTimerSeconds,
        # blinkMs/judgmentSeconds, etc.) onto the section itself, so the
        # SAME GET /oa/{attempt_id} fetch the frontend already makes
        # carries them down -- no separate config fetch needed. Targeted
        # update by section key (not the numeric index this function
        # doesn't have) so it composes safely alongside the caller's own
        # `sections.{index}.questions` $set on the same array element.
        # Previously this was fetched here ONLY to size sample_puzzles()
        # calls and never reached the client at all -- every type's timer
        # was silently hardcoded client-side regardless of what this
        # config actually said.
        await db.oa_attempts.update_one(
            {"attempt_id": attempt_id, "sections.key": section.get("key")},
            {"$set": {"sections.$.perTypeConfig": per_type_config}},
        )

        all_puzzles: List[dict] = []
        puzzle_ids_by_type: Dict[str, List[str]] = {}
        for gtype in game_types_list:
            type_cfg = per_type_config.get(gtype, {})
            n = type_cfg.get("instancesPerGame") if gtype == "grid_challenge" else type_cfg.get("subPuzzlesPerGame")
            n = n or count
            type_puzzles = await gamified_round.sample_puzzles(cid, gtype, user_id, n)
            # Force id == puzzle_id before the generic id-normalization below
            # runs (it only fills in q["id"] when missing/non-string) --
            # otherwise every puzzle would get a synthetic "q1"/"q2" id that
            # no longer matches the puzzle_id the answers dict (and
            # grade_session) key on.
            for p in type_puzzles:
                p["id"] = p.get("puzzle_id")
            puzzle_ids_by_type[gtype] = [p["puzzle_id"] for p in type_puzzles if p.get("puzzle_id")]
            all_puzzles.extend(type_puzzles)

        await gamified_round.create_session(
            user_id, attempt_id, cid, section.get("key"), puzzle_ids_by_type,
        )
        data = all_puzzles
    elif stype == "capgemini_round1":
        # Capgemini Round 1: Communication Assessment -- ONE section
        # covering 6 heterogeneous sub-parts sharing a single 60-minute
        # timer (see companies.py's section-entry comment for why this is
        # one section, not six). Content is DRAWN from capgemini_round1_
        # bank, not LLM-generated -- each draw_sectionN_questions call is
        # called with strip=False so the FULL doc (including correct_option/
        # rubric) gets persisted into oa_attempts; stripping for the client
        # happens once, at get_oa response time
        # (_strip_answer_fields_for_response's "capgemini_round1" branch
        # below), matching the "store full, strip at response" pattern the
        # rest of this codebase already uses. Each item is tagged `part` so
        # the frontend can switch rendering, same convention as comm_mixed's
        # `mode`. `id` is force-set to each item's natural id field BEFORE
        # the generic id-normalization at the bottom of this function runs
        # (same reason gamified_round does `p["id"] = p.get("puzzle_id")`
        # above) -- otherwise reading_comp's passage-level items especially
        # would get overwritten with synthetic q1/q2 ids that don't match
        # anything downstream.
        grammar_pool = await db.capgemini_round1_bank.find(
            {"section": "grammar_correction"}, {"_id": 0},
        ).to_list(None)
        business_pool = await db.capgemini_round1_bank.find(
            {"section": "business_writing"}, {"_id": 0},
        ).to_list(None)
        situational_pool = await db.capgemini_round1_bank.find(
            {"section": "situational_response"}, {"_id": 0},
        ).to_list(None)
        reading_pool = await db.capgemini_round1_bank.find(
            {"section": "reading_comprehension"}, {"_id": 0},
        ).to_list(None)
        # Section 5 (listening_comprehension) -- wired 2026-08, after Groq
        # TTS generation. ONLY clips with tts_status == "generated" are ever
        # fetched here -- a clip with no real audio yet must never reach a
        # candidate, regardless of how complete its script/question content
        # is (draw_section5_questions also independently re-filters on this,
        # so this is belt-and-suspenders, not the only guard). As of this
        # wiring, 5/22 clips are generated (Groq's free-tier daily token
        # quota was exhausted mid-batch on the rest); draw_section5_questions
        # still reliably reaches its fixed 4-question target from those 5 --
        # confirmed via 300 real draws against this exact pool before wiring,
        # 0 failures -- so this is safe to ship now rather than waiting for
        # every clip to finish generating.
        listening_pool = await db.capgemini_round1_bank.find(
            {"section": "listening_comprehension", "tts_status": "generated"}, {"_id": 0},
        ).to_list(None)
        # Section 6 (spoken_simulation) -- wired 2026-08. Single query for
        # both item_types (draw_section6_questions splits by item_type
        # itself, same "hand it the whole pool" contract every other
        # draw_sectionN_questions here uses). No tts_status-style readiness
        # gate needed here -- unlike Section 5's audio CLIPS, these items are
        # TEXT the candidate reads/responds to; the candidate's own spoken
        # response is what gets recorded, not something pre-generated that
        # could be "not ready yet".
        spoken_pool = await db.capgemini_round1_bank.find(
            {"section": "spoken_simulation"}, {"_id": 0},
        ).to_list(None)

        # Cross-attempt repetition fix (2026-09, Phase 0 migration): each
        # draw call now gets this candidate's already-seen ids for that
        # specific section, keyed by the same `section` value used in the
        # queries above -- see capgemini_recruitment_process.get_seen_ids.
        grammar_seen = await capgemini_recruitment_process.get_seen_ids(user_id, "grammar_correction")
        business_seen = await capgemini_recruitment_process.get_seen_ids(user_id, "business_writing")
        situational_seen = await capgemini_recruitment_process.get_seen_ids(user_id, "situational_response")
        reading_seen = await capgemini_recruitment_process.get_seen_ids(user_id, "reading_comprehension")
        listening_seen = await capgemini_recruitment_process.get_seen_ids(user_id, "listening_comprehension")
        spoken_seen = await capgemini_recruitment_process.get_seen_ids(user_id, "spoken_simulation")

        grammar_items = capgemini_recruitment_process.draw_section1_questions(grammar_pool, strip=False, exclude_ids=grammar_seen)
        business_items = capgemini_recruitment_process.draw_section2_questions(business_pool, strip=False, exclude_ids=business_seen)
        situational_items = capgemini_recruitment_process.draw_section3_questions(situational_pool, strip=False, exclude_ids=situational_seen)
        reading_items = capgemini_recruitment_process.draw_section4_questions(reading_pool, exclude_ids=reading_seen)
        listening_items = capgemini_recruitment_process.draw_section5_questions(listening_pool, strip=False, exclude_ids=listening_seen)
        spoken_items = capgemini_recruitment_process.draw_section6_questions(spoken_pool, strip=False, exclude_ids=spoken_seen)

        for q in grammar_items:
            q["part"] = "grammar"
            q["id"] = q["question_id"]
        for q in business_items:
            q["part"] = "business_writing"
            q["id"] = q["scenario_id"]
        for q in situational_items:
            q["part"] = "situational"
            q["id"] = q["question_id"]
        for p in reading_items:
            p["part"] = "reading_comp"
            p["id"] = p["passage_id"]
        for c in listening_items:
            c["part"] = "listening_comp"
            c["id"] = c["clip_id"]
        for it in spoken_items:
            it["part"] = "spoken_sim"
            it["id"] = it["item_id"]

        await capgemini_recruitment_process.mark_seen(user_id, "grammar_correction", [q["question_id"] for q in grammar_items])
        await capgemini_recruitment_process.mark_seen(user_id, "business_writing", [q["scenario_id"] for q in business_items])
        await capgemini_recruitment_process.mark_seen(user_id, "situational_response", [q["question_id"] for q in situational_items])
        await capgemini_recruitment_process.mark_seen(user_id, "reading_comprehension", [p["passage_id"] for p in reading_items])
        await capgemini_recruitment_process.mark_seen(user_id, "listening_comprehension", [c["clip_id"] for c in listening_items])
        await capgemini_recruitment_process.mark_seen(user_id, "spoken_simulation", [it["item_id"] for it in spoken_items])

        data = grammar_items + business_items + situational_items + reading_items + listening_items + spoken_items
    elif stype == "capgemini_round2_ai_literacy":
        # Round 2 -- AI Literacy (2026-09, Phase 0 migration, Task 2). Content
        # is DRAWN from capgemini_round2_bank (separate collection from
        # Round 1's capgemini_round1_bank), not LLM-generated -- same "store
        # full, strip at response" pattern as capgemini_round1 above.
        # NOT YET reachable in practice: companies.py's Capgemini Round 2
        # config doesn't have a section with this `type` yet (see this
        # module's top docstring) -- this branch exists, tested, so that
        # decision (where in Round 2, what count/weight) can be made
        # separately without ever having shipped un-wired dispatch code in
        # between, same precedent as Section 5 before its own wiring pass.
        ai_literacy_pool = await db.capgemini_round2_bank.find({}, {"_id": 0}).to_list(None)
        ai_literacy_seen = await capgemini_recruitment_process.get_seen_ids(user_id, "ai_literacy")
        ai_literacy_items = capgemini_recruitment_process.draw_section7_questions(
            ai_literacy_pool, strip=False, exclude_ids=ai_literacy_seen,
        )
        for s in ai_literacy_items:
            s["part"] = "ai_literacy"
            s["id"] = s["scenario_id"]
        await capgemini_recruitment_process.mark_seen(user_id, "ai_literacy", [s["scenario_id"] for s in ai_literacy_items])
        data = ai_literacy_items
    elif stype == "capgemini_round2_technical":
        # Round 2 -- Technical Assessment (2026-09/10, Round 2 wiring pass).
        # Fixed 20-question, 4-way split: 5 from "programming_logic", 5 from
        # "dsa", 5 mixed across oops/dbms/swe_fundamentals (balanced,
        # randomized per draw -- not a fixed per-topic count, unlike a plain
        # extra_topics section), and 5 mixed across cn/modern_engineering
        # (weighted 3:2 toward cn). All four source topics are now in
        # mcq_static_bank.CANONICAL_TOPICS (see that module), so this
        # delegates the actual draw -- static/live 90/10 split, seen-
        # tracking, shuffling -- to the SAME shared _generate_extra_topics
        # helper OOPS/DBMS/OS/CN already go through elsewhere in this file;
        # the only new logic here is picking each mixed pool's per-topic
        # counts fresh on every call, via weighted random.choices over 5
        # slots (so the split varies draw to draw around its target ratio
        # rather than being identical every time -- verified via a 500-draw
        # simulation before wiring: swe-mix lands close to an even 3-way
        # split with no source systematically favored, modern-mix lands
        # close to 3:2 cn:modern_engineering on average).
        swe_mix_counts = Counter(random.choices(["oops", "dbms", "swe_fundamentals"], k=5))
        modern_mix_counts = Counter(random.choices(["cn", "modern_engineering"], weights=[3, 2], k=5))
        _TOPIC_DISPLAY_NAMES = {
            "programming_logic": "Programming Logic", "dsa": "DSA", "oops": "OOPS", "dbms": "DBMS",
            "swe_fundamentals": "SWE Fundamentals", "cn": "Computer Networks", "modern_engineering": "Modern Engineering",
        }
        extra_topics = [
            {"key": "programming_logic", "name": _TOPIC_DISPLAY_NAMES["programming_logic"], "count": 5},
            {"key": "dsa", "name": _TOPIC_DISPLAY_NAMES["dsa"], "count": 5},
        ] + [
            {"key": k, "name": _TOPIC_DISPLAY_NAMES[k], "count": c}
            for k, c in swe_mix_counts.items() if c > 0
        ] + [
            {"key": k, "name": _TOPIC_DISPLAY_NAMES[k], "count": c}
            for k, c in modern_mix_counts.items() if c > 0
        ]
        data = await _generate_extra_topics(company_name, extra_topics, diff, user_id, static_only=True)
    else:  # mcq / topic_mcq
        skey = section.get("key")
        stype = section.get("type")
        if stype == "topic_mcq":
            # Compound MCQ round: pull ONE verified question per topic from the
            # pool. Falls back to live-verify per topic if a bucket is empty.
            # Topics are resolved in parallel so 7 topics don't take 7× the
            # time of one.
            topics = section.get("topics", []) or []

            async def _one_topic(t: dict) -> List[dict]:
                tkey = t.get("key")
                tname = t.get("name", tkey)
                if not tkey:
                    return []
                # 90/10 static-bank/live split for the 8 canonical topics
                # (see mcq_static_bank.py, changed 2026-07-21 from 50/50) —
                # at count=1, static_n=ceil(1*0.9)=1 so this prefers the
                # static bank whenever it has an unseen question for this
                # candidate, falling back to the existing pool-or-live-verify
                # path only when it doesn't (shortfall or topic not covered
                # by the static bank).
                static_items: List[dict] = []
                live_n = 1
                if tkey in mcq_static_bank.CANONICAL_TOPICS:
                    static_items, live_n = await mcq_static_bank.sample_mixed_static_part(user_id, tkey, 1)
                got = list(static_items)
                if live_n > 0:
                    pool_key = f"core-{tkey}"
                    live_got = await mcq_pool.pop_from_pool(company_name, pool_key, tname, live_n)
                    if not live_got:
                        live_got = await mcq_pool.fallback_live_verify_topic(
                            company_name, tkey, tname, live_n, diff,
                        )
                    got.extend(live_got)
                random.shuffle(got)
                # Belt-and-suspenders: never allow more than 1 per topic here.
                got = got[:1]
                for q in got:
                    q["topic"] = tname
                return got

            results = await asyncio.gather(*[_one_topic(t) for t in topics], return_exceptions=True)
            items: List[dict] = []
            for r in results:
                if isinstance(r, list):
                    items.extend(r)
            data = items
        elif section.get("topic_groups"):
            # 90/10 static-bank/live split PER SUB-GROUP (added 2026-07-22 --
            # see _generate_topic_mix). Previously always 100% live for the
            # whole section via one combined fallback_live_verify_topic_mix
            # call; still bypasses the shared cross-company pool below (even
            # though "aptitude" IS a pooled key) — pool entries for that key
            # are generic, generated without any awareness of topic_groups,
            # and would silently serve untagged content that ignores the split.
            data = await _generate_topic_mix(
                company_name, count, section["topic_groups"], diff, skey, user_id,
            )
        elif section.get("extra_topics"):
            # LTIMindtree's Computer Science section (DBMS/OOPs/OS) — a
            # topic-only MCQ section with no pseudocode content at all, reusing
            # the same per-topic pool-or-live-verify mechanism as Capgemini's
            # fundamentals fix via the shared _generate_extra_topics helper.
            # Deliberately bypasses the generic pool below (even though
            # "cs-fundamentals" IS a pooled key) for the same reason
            # topic_groups does: pool entries there are untagged and don't
            # know about this company's specific topic split.
            data = await _generate_extra_topics(company_name, section["extra_topics"], diff, user_id)
        elif skey and await mcq_pool.is_pooled_key(skey):
            # 90/10 static-bank/live split (changed 2026-07-21 from 50/50) for
            # section keys that map cleanly to one of the 8 canonical topics
            # (mcq_static_bank.SECTION_KEY_TO_TOPIC) — verbal/english/reasoning/
            # logical/analytical/numerical/aptitude/quant. cs-fundamentals/
            # technical/puzzles/advanced aren't in that map and fall through
            # unchanged (live pool only, as today).
            static_items: List[dict] = []
            live_n = count
            topic = mcq_static_bank.SECTION_KEY_TO_TOPIC.get(skey)
            if topic:
                static_items, live_n = await mcq_static_bank.sample_mixed_static_part(user_id, topic, count)
            data = list(static_items)
            if live_n > 0:
                live_data = await mcq_pool.pop_from_pool(company_name, skey, section_name, live_n)
                if len(live_data) < live_n:
                    needed = live_n - len(live_data)
                    extra = await mcq_pool.fallback_live_verify(company_name, section_name, skey, needed, diff)
                    live_data = live_data + extra
                data.extend(live_data)
            random.shuffle(data)
        else:
            data = await call_json(system, mcq_prompt(company_name, section_name, count, diff))
    if not isinstance(data, list):
        data = []
    # Normalize ids to strings (models sometimes emit integers)
    for i, q in enumerate(data):
        if isinstance(q, dict):
            qid = q.get("id")
            if qid is None or not isinstance(qid, str):
                q["id"] = f"q{i+1}"
            else:
                q["id"] = str(qid)
    return data


# Section types where `count` independent items are generated and each one
# goes through its own multi-stage verification \u2014 the types actually worth
# splitting into small chunks delivered progressively. Excludes:
# essay/coding/*_games/*_challenges/speaking/reading_listening/comm_mixed/
# voice_mixed (small counts or non-uniform shapes that don't split cleanly),
# and anything with `extra_topics` (its per-topic counts are configured
# independently of the section's own `count`, so scaling that down wouldn't
# actually shrink a chunk \u2014 see _generate_extra_topics).
#
# BATCH_SIZE = 5 isn't just about perceived speed: single-shot generation for
# a large `count` (e.g. Cognizant's 34-question Grammar, or 16-question
# Comprehension whose items embed full reading passages) can genuinely
# TRUNCATE against ANTHROPIC_MAX_TOKENS (4096) \u2014 confirmed live: a 29-item
# grammar call came back with stop_reason="max_tokens", cut off mid-question,
# parsed as zero usable questions. That's a real pre-existing bug this
# chunking also fixes, not just a latency nice-to-have \u2014 6-7 comprehension
# items (the heaviest content type) already uses 51-70% of the token budget,
# so batches of 5 keep every single call comfortably inside the limit
# regardless of section size.
_BATCHABLE_TYPES = {"mcq", "topic_mcq", "pseudocode", "comm", "grammar", "comprehension"}
BATCH_SIZE = 5


async def _gen_and_persist_section(attempt_id: str, company_name: str, index: int, section: dict, user_id: str, company_id: Optional[str] = None):
    """Generate one section's questions and write them back atomically. This
    lets the frontend unlock a section as soon as it's ready \u2014 without waiting
    for the slowest sibling.

    For large batchable sections, generates in BATCH_SIZE-sized chunks,
    persisting each as it completes (the frontend already treats a section as
    playable the moment it has ANY questions \u2014 see OARunner's `currentReady`
    check) \u2014 so a candidate can start on question 1 without waiting for
    question 45's full ground-truth pipeline to finish, and without any
    single generation call risking a token-limit truncation."""
    total_count = section.get("count", 5)
    stype = section.get("type")
    extra_topics = section.get("extra_topics") or []

    if extra_topics:
        # Capgemini's Technical (pseudocode base + OOPS/DBMS/OS/CN) and
        # LTIMindtree's CS Fundamentals (DBMS/OOPS/OS, no base at all) both
        # used to wait for EVERYTHING — pseudocode base plus every topic —
        # before persisting a single question, even though each individual
        # piece (a topic's 6-7 questions, or a chunk of the pseudocode base)
        # is already small/fast on its own. Persist each piece as it
        # completes instead: the pseudocode base (if any) chunked at
        # BATCH_SIZE for the same truncation-safety reason as _BATCHABLE_TYPES,
        # then each extra_topic's own call, appended one at a time.
        diff = section.get("difficulty_target")
        section_key = section.get("key") or "pseudocode"
        section_name = section["name"]
        pseudo_count = section.get("pseudocode_count", total_count) if stype == "pseudocode" else 0

        questions: List[dict] = []
        chunk_idx = 0

        async def _persist_piece(new_items: List[dict]):
            nonlocal chunk_idx
            if not new_items:
                return
            offset = len(questions)
            for i, q in enumerate(new_items):
                if isinstance(q, dict):
                    q["id"] = f"q{offset + i + 1}"
            if chunk_idx == 0:
                await db.oa_attempts.update_one(
                    {"attempt_id": attempt_id},
                    {"$set": {f"sections.{index}.questions": new_items}},
                )
            else:
                await db.oa_attempts.update_one(
                    {"attempt_id": attempt_id},
                    {"$push": {f"sections.{index}.questions": {"$each": new_items}}},
                )
            questions.extend(new_items)
            chunk_idx += 1

        remaining_pseudo = pseudo_count
        while remaining_pseudo > 0:
            chunk_size = min(BATCH_SIZE, remaining_pseudo)
            try:
                chunk = await mcq_pool.fallback_live_verify(company_name, section_name, section_key, chunk_size, diff)
            except Exception as e:  # pragma: no cover
                logger.warning("section '%s' pseudocode chunk failed: %s", section_key, e)
                chunk = []
            for q in chunk:
                if isinstance(q, dict):
                    q["topic"] = "Pseudocode"
            await _persist_piece(chunk)
            if not chunk:
                break
            remaining_pseudo -= len(chunk)

        for t in extra_topics:
            try:
                topic_items = await _generate_extra_topics(company_name, [t], diff, user_id)
            except Exception as e:  # pragma: no cover
                logger.warning("section '%s' topic '%s' failed: %s", section_key, t.get("key"), e)
                topic_items = []
            await _persist_piece(topic_items)
        return

    batchable = stype in _BATCHABLE_TYPES and total_count > BATCH_SIZE

    if not batchable:
        try:
            questions = await _generate_section_questions(company_name, section, user_id, attempt_id, company_id=company_id)
        except Exception as e:  # pragma: no cover
            logger.warning("section '%s' failed: %s", section["key"], e)
            questions = []
        await db.oa_attempts.update_one(
            {"attempt_id": attempt_id},
            {"$set": {f"sections.{index}.questions": questions}},
        )
        return

    questions: List[dict] = []
    chunk_idx = 0
    while len(questions) < total_count:
        chunk_size = min(BATCH_SIZE, total_count - len(questions))
        chunk_section = {**section, "count": chunk_size}
        try:
            chunk = await _generate_section_questions(company_name, chunk_section, user_id, attempt_id)
        except Exception as e:  # pragma: no cover
            logger.warning("section '%s' chunk %d failed: %s", section["key"], chunk_idx, e)
            chunk = []
        if not chunk:
            break  # stop on failure; keep whatever's already persisted rather than retry forever
        # Each chunk independently id-normalizes to q1..qN based on its own
        # array position \u2014 re-number so ids continue the running sequence
        # instead of colliding across chunks.
        offset = len(questions)
        for i, q in enumerate(chunk):
            if isinstance(q, dict):
                q["id"] = f"q{offset + i + 1}"
        if chunk_idx == 0:
            await db.oa_attempts.update_one(
                {"attempt_id": attempt_id},
                {"$set": {f"sections.{index}.questions": chunk}},
            )
        else:
            await db.oa_attempts.update_one(
                {"attempt_id": attempt_id},
                {"$push": {f"sections.{index}.questions": {"$each": chunk}}},
            )
        questions.extend(chunk)
        chunk_idx += 1


async def _generate_all_sections_bg(attempt_id: str, company: dict, user_id: str):
    """Background task: generate each section concurrently. Every finished
    section is written back to Mongo AS SOON as it's ready (not batched at the
    end), so the frontend can unlock it immediately."""
    import asyncio
    try:
        await asyncio.gather(
            *[_gen_and_persist_section(attempt_id, company["name"], i, s, user_id, company_id=company["id"])
              for i, s in enumerate(company["sections"])],
            return_exceptions=True,
        )
        await db.oa_attempts.update_one(
            {"attempt_id": attempt_id},
            {"$set": {"generation_status": "ready"}},
        )
        logger.info("bg gen: attempt %s ready (incremental)", attempt_id)
    except Exception as e:  # pragma: no cover
        logger.exception("bg gen crashed for %s: %s", attempt_id, e)
        await db.oa_attempts.update_one(
            {"attempt_id": attempt_id},
            {"$set": {"generation_status": "failed", "generation_error": str(e)[:400]}},
        )


@api.post("/oa/start")
async def start_oa(body: StartOAIn, user: Dict[str, Any] = Depends(require_user)):
    import asyncio
    company = get_company(body.company_id)
    if not company:
        raise HTTPException(404, "Company not found")

    cluster_options = company.get("cluster_options")
    if cluster_options and body.cluster not in cluster_options:
        raise HTTPException(400, f"cluster must be one of {cluster_options}")

    # -- Entitlements gate ---------------------------------------------------
    # 1) Roll the 30-day window forward for Basic/Pro if needed.
    reset_op = entitlements.maybe_reset_period(user)
    if reset_op:
        await db.users.update_one({"user_id": user["user_id"]}, reset_op)
        # Reflect in the local user snapshot so subsequent checks see the reset.
        user["runs_used"] = 0
        user["runs_period_start"] = entitlements._now().isoformat()

    # 2) Company selection cap (Free 1 / Basic 4 / Pro 6). MAX/SuperMAX + founder unlimited.
    ok_c, why_c = entitlements.assert_company_allowed(user, company["id"])
    if not ok_c:
        raise HTTPException(402, {
            "code": why_c,
            "message": "Your plan's company slots are full. Swap a selection or upgrade.",
            "current_selections": list(user.get("company_selections", []) or []),
        })

    # 3) Free OA-only enforcement (only applies AFTER the contest window ends).
    #    Free users can't start on companies that lack an OA phase — n/a for now
    #    since every company has an OA phase; the Interview/Review lock is
    #    enforced at those endpoints.

    # 4) Run cap → credit fallback.
    ok_r, why_r, source = entitlements.can_start_run(user)
    if not ok_r:
        raise HTTPException(402, {
            "code": why_r,
            "message": "Run quota exhausted. Buy credits or upgrade your plan.",
            "credit_packs": CREDIT_PACKS,
        })

    # Create attempt with PLACEHOLDER sections (no questions yet).
    placeholder_sections = [{**s, "questions": []} for s in company["sections"]]
    attempt_id = new_id("oa")
    attempt = {
        "attempt_id": attempt_id,
        "user_id": user["user_id"],
        "company_id": company["id"],
        "company_name": company["name"],
        "resume_id": body.resume_id,
        "cluster": body.cluster,
        "scoring_mode": company["scoring_mode"],
        "sections": placeholder_sections,
        "answers": {},
        "section_results": {},
        "status": "in_progress",
        "generation_status": "generating",  # "generating" | "ready" | "failed"
        "created_at": iso(now_utc()),
        "current_section_index": 0,
        "charged_source": source,  # "plan" | "credit" | "bypass"
    }
    await db.oa_attempts.insert_one(attempt)
    mcq_pool.record_activity()  # a new OA session counts as real demand -- see mcq_pool's demand-aware worker

    # 5) Deduct the run: plan first, credits second. Founder = no-op.
    if source == "plan":
        upd: Dict[str, Any] = {"$inc": {"runs_used": 1}}
        # For Basic/Pro, ensure runs_period_start is set on first-ever run.
        if not user.get("runs_period_start"):
            upd["$set"] = {"runs_period_start": entitlements._now().isoformat()}
        await db.users.update_one({"user_id": user["user_id"]}, upd)
    elif source == "credit":
        await db.users.update_one({"user_id": user["user_id"]}, {"$inc": {"credits": -1}})

    # 6) Record company selection (only if we're inside a cap-bearing plan and this is new).
    plan_limits = entitlements.PLAN_LIMITS.get(user.get("plan", "free"), {})
    if plan_limits.get("company_cap") is not None:
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$addToSet": {"company_selections": company["id"]}},
        )

    # Kick off background generation. asyncio.create_task returns immediately.
    asyncio.create_task(_generate_all_sections_bg(attempt_id, company, user["user_id"]))
    attempt.pop("_id", None)
    return attempt


# Response-shape fix (2026-08, security audit): get_oa's Mongo projection
# previously excluded ONLY `_id` and `_hidden_answer_keys`, so every plain
# MCQ-shaped question's correct_index/explanation passed straight through
# into the live, in-progress HTTP response — unlike gamified_round content,
# which is pre-stripped via puzzle_bank sampling (gamified_round.
# strip_answer) before it's ever persisted. Confirmed via audit that
# mcq/topic_mcq/pseudocode/comm/grammar/comprehension sections, plus
# comm_mixed/voice_mixed's "mcq"-mode items, all carried this exposure;
# submit_section (re-derives from its own separate unfiltered find_one) and
# gamified_round were already clean.
#
# WHITELIST, not gamified_round.strip_answer()'s blacklist: these MCQ docs
# carry internal-only fields (correct_index, explanation, topic, difficulty,
# ground_truth_source, verified_by, source_batch, date_added) that have no
# reason to reach the live client at all. The kept fields were verified
# against OARunner.jsx's actual reads (MCQSection, ChartQuestion,
# CommMixedSection/SpeakingAnswerCard) — not guessed — so this can't
# silently drop something the frontend needs to render the question.
#
# Deliberately response-only: the stored oa_attempts document is untouched,
# so submit_section's server-side re-derivation keeps reading
# q.get("correct_index") from its own full find_one exactly as before.
# oa_review and the review-deck endpoints are POST-completion study
# features that intentionally reveal answers — not touched here. (Separate,
# pre-existing gap noted but NOT fixed in this pass, per its
# response-shape-only scope: oa_review's answer_key is built from every
# section's stored questions regardless of whether that section has
# actually been submitted yet, since it never checks section_results/
# attempt["status"] before building each section's entry — so a candidate
# could in principle call GET /oa/{id}/review early and see correct_index
# for sections they haven't answered. That's a gating/flow issue, not a
# response-shape one, so it's flagged for separate follow-up rather than
# folded into this fix.)
_MCQ_ANSWER_BEARING_TYPES = {"mcq", "topic_mcq", "pseudocode", "comm", "grammar", "comprehension", "capgemini_round2_technical"}
_MIXED_MODE_TYPES = {"comm_mixed", "voice_mixed"}
_MCQ_CLIENT_SAFE_FIELDS = ("id", "prompt", "options", "chart", "svg_diagram")
_MCQ_MODE_CLIENT_SAFE_FIELDS = ("id", "mode", "prompt", "options")
_SPEAKING_MODE_CLIENT_SAFE_FIELDS = ("id", "mode", "topic", "instructions", "min_words", "max_words")
# Round 3 (Debugging Assessment) -- deliberately excludes hidden_tests and
# reference_solution (the two fields debugging_bank.grade_debugging_
# submission() needs server-side, that must never reach the client).
# debugging_variant is already client-safe as stored (buggy_code/
# bug_category/task_description only, no answer).
_DEBUGGING_CLIENT_SAFE_FIELDS = (
    "id", "title", "difficulty", "topic", "statement",
    "input_format", "output_format", "constraints",
    "visible_tests", "debugging_variant",
)

# Capgemini Round 1's six sub-parts, keyed by the `part` tag set in
# _generate_section_questions's "capgemini_round1" branch -- each part has
# its own field shape (grammar/situational are plain MCQ, business_writing
# is free-text with no answer field at all, reading_comp nests sub-questions
# under a passage). Deliberately NOT reusing capgemini_recruitment_process's
# own _strip_grammar_for_client/_strip_business_writing_for_client/
# _strip_situational_for_client helpers here: those return question_id/
# scenario_id as the id field (their own module's contract), but this
# app's response shape needs `id` uniformly (matching every other section
# type's answers[q.id] convention on the frontend) -- the persisted docs
# keep BOTH the original id field and a copied `id` field (see the
# generation branch), so this whitelists straight to `id`.
# "part" is included in every one of these whitelists (2026-08 fix, found by
# a real Playwright click-through, not caught by earlier data-shape-only
# verification): Round1CommunicationSection.jsx routes ALL SIX parts by
# checking `q.part` client-side (`qs.filter(q => q.part === "grammar")`
# etc.) -- omitting it here meant the client never received the one field
# it needed to render ANY part at all, so the whole section silently
# rendered empty (no error, no "empty" message, since section.questions
# itself wasn't empty -- only every per-part filter was). Not
# answer-revealing: it's a category tag, same class of field as the
# already-whitelisted passage_type/clip_type.
_R1_GRAMMAR_FIELDS = ("id", "part", "prompt", "options")
_R1_SITUATIONAL_FIELDS = ("id", "part", "scenario_prompt", "options")
_R1_BUSINESS_WRITING_FIELDS = ("id", "part", "context", "recipient_type", "tone_expected")
_R1_READING_COMP_PASSAGE_FIELDS = ("id", "part", "passage_text", "passage_type")
_R1_READING_COMP_SUBQ_FIELDS = ("question_id", "prompt", "question_focus", "options")
# Section 5 (listening_comprehension) -- added 2026-08, code-wiring pass.
# `id` (not `clip_id`) matches every other part's own id-field convention
# above; `script` is deliberately excluded from the top-level whitelist --
# same reasoning as correct_option/rubric elsewhere: showing the transcript
# would let a candidate read instead of listen, defeating the section's
# purpose. Nested SUBQ fields mirror _R1_READING_COMP_SUBQ_FIELDS exactly
# (question_id is required so the frontend has a key to submit each
# sub-question's answer under -- omitting it, as an earlier draft of this
# whitelist did, would silently break answer submission for every listening
# item). NOT yet reachable in practice: server.py's capgemini_round1
# generation branch does not fetch a listening pool or tag any item
# part="listening_comp" yet (see that section of this file) -- this case
# exists so the whitelist is ready the moment that wiring lands, without
# ever having shipped an un-whitelisted "unknown part" gap in between.
_R1_LISTENING_CLIP_FIELDS = ("id", "part", "clip_type", "speaker_count", "audio_url", "estimated_duration_seconds")
_R1_LISTENING_SUBQ_FIELDS = ("question_id", "prompt", "question_focus", "options")
# Section 6 (spoken_simulation) -- added 2026-08, code-wiring pass. `id`
# (not `item_id`) matches every other part's own id-field convention above.
# read_aloud shows passage_text (not answer-revealing -- the candidate must
# read it aloud to be graded, unlike an MCQ answer key); respond_to_prompt
# excludes `rubric` (grading-internal, same no-rubric-shown precedent as
# business_writing). Both parts share one whitelist tuple since neither
# field set is ever answer-revealing for spoken_sim's own item_type -- the
# unused key (passage_text for a respond_to_prompt doc, scenario for a
# read_aloud doc) is simply absent from that item's stored fields, so the
# `if k in q` guard drops it naturally rather than needing a per-type branch
# the way the module-internal _strip_spoken_sim_for_client does.
_R1_SPOKEN_SIM_FIELDS = ("id", "part", "item_type", "passage_text", "scenario", "estimated_duration_seconds")

# Round 2 -- AI Literacy (added 2026-09, Phase 0 migration, Task 2). `id`
# (not `scenario_id`) matches every Round 1 part's own id-field convention
# above. Nested question fields exclude correct_option/explanation, same
# answer-revealing exclusion as every other section -- `options` itself (the
# letter-keyed dict of answer text) is not answer-revealing on its own.
_R2_AI_LITERACY_SCENARIO_FIELDS = ("id", "part", "domain")
_R2_AI_LITERACY_QUESTION_FIELDS = ("question_id", "prompt", "topic_tag", "options")


def _strip_capgemini_round2_ai_literacy_question(q: Dict[str, Any]) -> Dict[str, Any]:
    item = {k: q[k] for k in _R2_AI_LITERACY_SCENARIO_FIELDS if k in q}
    item["questions"] = [
        {k: sub[k] for k in _R2_AI_LITERACY_QUESTION_FIELDS if k in sub}
        for sub in (q.get("questions") or [])
    ]
    return item


def _strip_capgemini_round1_question(q: Dict[str, Any]) -> Dict[str, Any]:
    part = q.get("part")
    if part == "grammar":
        return {k: q[k] for k in _R1_GRAMMAR_FIELDS if k in q}
    if part == "situational":
        return {k: q[k] for k in _R1_SITUATIONAL_FIELDS if k in q}
    if part == "business_writing":
        return {k: q[k] for k in _R1_BUSINESS_WRITING_FIELDS if k in q}
    if part == "reading_comp":
        item = {k: q[k] for k in _R1_READING_COMP_PASSAGE_FIELDS if k in q}
        item["questions"] = [
            {k: sub[k] for k in _R1_READING_COMP_SUBQ_FIELDS if k in sub}
            for sub in (q.get("questions") or [])
        ]
        return item
    if part == "listening_comp":
        item = {k: q[k] for k in _R1_LISTENING_CLIP_FIELDS if k in q}
        item["questions"] = [
            {k: sub[k] for k in _R1_LISTENING_SUBQ_FIELDS if k in sub}
            for sub in (q.get("questions") or [])
        ]
        return item
    if part == "spoken_sim":
        return {k: q[k] for k in _R1_SPOKEN_SIM_FIELDS if k in q}
    # Unknown/missing part tag -- fail closed (empty dict) rather than risk
    # passing an un-whitelisted question through with its answer intact.
    return {}


def _strip_answer_fields_for_response(sections: List[dict]) -> List[dict]:
    out = []
    for s in sections:
        stype = s.get("type")
        questions = s.get("questions") or []
        if stype in _MCQ_ANSWER_BEARING_TYPES:
            new_questions = [{k: q[k] for k in _MCQ_CLIENT_SAFE_FIELDS if k in q} for q in questions]
            out.append({**s, "questions": new_questions})
        elif stype in _MIXED_MODE_TYPES:
            new_questions = []
            for q in questions:
                fields = _SPEAKING_MODE_CLIENT_SAFE_FIELDS if q.get("mode") == "speaking" else _MCQ_MODE_CLIENT_SAFE_FIELDS
                new_questions.append({k: q[k] for k in fields if k in q})
            out.append({**s, "questions": new_questions})
        elif stype == "capgemini_round1":
            new_questions = [_strip_capgemini_round1_question(q) for q in questions]
            out.append({**s, "questions": new_questions})
        elif stype == "capgemini_round2_ai_literacy":
            new_questions = [_strip_capgemini_round2_ai_literacy_question(q) for q in questions]
            out.append({**s, "questions": new_questions})
        elif stype == "debugging":
            new_questions = [{k: q[k] for k in _DEBUGGING_CLIENT_SAFE_FIELDS if k in q} for q in questions]
            out.append({**s, "questions": new_questions})
        elif stype == "ai_assisted":
            # Whitelist is really a no-op in practice -- the generation
            # branch already only ever stores {session_id, problem_id} in
            # `questions` (see _generate_section_questions's "ai_assisted"
            # branch), never problem/answer content. Kept explicit anyway,
            # matching this function's whitelist-everywhere convention,
            # rather than relying on "nothing sensitive is in there by
            # construction" alone.
            new_questions = [{k: q[k] for k in ("session_id", "problem_id") if k in q} for q in questions]
            out.append({**s, "questions": new_questions})
        else:
            out.append(s)
    return out


def _client_section_results(section_results: Dict[str, Any]) -> Dict[str, Any]:
    """Section results as the candidate may see them. Round 4's per-component
    breakdown (self_review_correct, bug_explanation_quality, stage_efficiency)
    is stored server-side and read only by the grading and tier code, so it is
    removed here. Each section keeps its score and passed fields."""
    return {
        key: ({k: v for k, v in result.items() if k != "components"} if isinstance(result, dict) else result)
        for key, result in section_results.items()
    }


@api.get("/oa/{attempt_id}")
async def get_oa(attempt_id: str, user: Dict[str, Any] = Depends(require_user)):
    # _hidden_answer_keys never goes to the client — it's where puzzle types
    # with a genuine secret (e.g. Grid/Inductive/Digit Challenge's correct
    # value) keep their answer key server-side only. Internal code (grading)
    # reads it via its own separate find_one call without this exclusion.
    doc = await db.oa_attempts.find_one(
        {"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0, "_hidden_answer_keys": 0},
    )
    if not doc:
        raise HTTPException(404, "Not found")
    doc["sections"] = _strip_answer_fields_for_response(doc.get("sections", []))
    if doc.get("section_results"):
        doc["section_results"] = _client_section_results(doc["section_results"])
    # The stored capgemini_tier carries the per-criterion breakdown for admin use.
    # The candidate gets only the whitelisted {tier, lpa} view.
    if doc.get("capgemini_tier"):
        doc["capgemini_tier"] = capgemini_tiers.client_view(doc["capgemini_tier"])
    return doc


class SubmitSectionIn(BaseModel):
    section_key: str
    answers: Dict[str, Any]  # {question_id: answer}


class CheckPuzzleIn(BaseModel):
    section_key: str
    puzzle_id: str
    # int for deductive_grid/switch_challenge's single-index answers; a
    # 2-element list for inductive_challenge's unordered pair-of-indices
    # answer (see game_types._pair_answer_check) -- both are passed through
    # untouched to gamified_round.check_answer, which looks up the right
    # checker per puzzle's gameType rather than assuming a shape here.
    selected: Optional[Union[int, List[int]]] = None
    timedOut: bool = False
    timeTakenMs: Optional[int] = None


class GridChallengePhaseIn(BaseModel):
    section_key: str
    puzzle_id: str
    phase: str  # "block{1,2,3}_blink" | "block{1,2,3}_judgments" | "recall_board"
    blockIndex: Optional[int] = None


class GridChallengeAnswerIn(BaseModel):
    section_key: str
    puzzle_id: str
    phase: str  # "judgment" | "recall"
    blockIndex: Optional[int] = None
    judgmentIndex: Optional[int] = None
    answer: Any = None
    timedOut: bool = False
    timeTakenMs: Optional[int] = None


class MotionChallengeMoveIn(BaseModel):
    section_key: str
    puzzle_id: str
    blockId: Optional[str] = None  # None means "move the ball"
    direction: str  # "up" | "down" | "left" | "right"


class MotionChallengeUndoIn(BaseModel):
    section_key: str
    puzzle_id: str


class MotionChallengeStateIn(BaseModel):
    section_key: str
    puzzle_id: str


def _grade_mcq_like(section: dict, answers: Dict[str, Any]) -> dict:
    total = len(section.get("questions", []))
    correct = 0
    negative = section.get("negative", False)
    for q in section.get("questions", []):
        qid = str(q.get("id"))
        if qid not in answers:
            continue
        chosen = answers[qid]
        try:
            chosen_int = int(chosen)
        except Exception:
            chosen_int = -1
        if chosen_int == q.get("correct_index"):
            correct += 1
        elif negative and chosen_int != -1:
            correct -= 0.25
    correct = max(0, correct)
    score = (correct / total) if total else 0
    passed = score >= section.get("cutoff", 0.5)
    return {"score": round(score, 3), "correct": correct, "total": total, "passed": passed}


async def _grade_gamified_round_section(section: dict, answers: Dict[str, Any], attempt_id: str) -> dict:
    """Grades EVERY game type present in this section (a gamified_round
    section now runs all of a company's configured game types together,
    not one at a time) and combines them into one section-level result.

    Grades against puzzle_bank's stored correctAnswer via
    gamified_round.grade_session -- never against anything stored on the
    attempt doc itself (the served questions had correctAnswer stripped).
    session_id is recomputed rather than stored, matching create_session's
    own f"{attempt_id}_{section_key}" convention. `answers` here is keyed by
    puzzle_id -> {selected, timedOut, timeTakenMs}, produced by
    DeductiveGridSection/SwitchChallengeSection's onComplete, merged across
    both by GamifiedRoundSection before this is called.

    grid_challenge and motion_challenge are each dispatched to their own
    grade_*_session instead -- their whole interaction already happened
    via live round-trips (/grid-challenge/answer, /motion-challenge/move
    and /undo) rather than one "answers dict submitted once at the end"
    the flat-list types use, so both independently re-derive the final
    score from what's already stored server-side rather than from this
    function's `answers` param.

    Combined raw_score sums across types even though they use different
    point ratios (+1/-1, +3/-1, +3/-1, +4/-1) -- it's an informational total, not
    what decides pass/fail; score/passed use plain correct/total across
    every sub-answer from every type, same convention every other section
    type in this app already uses."""
    session_id = f"{attempt_id}_{section['key']}"
    questions = section.get("questions") or []
    types_present = sorted({q.get("gameType") for q in questions if q.get("gameType")})

    combined_raw_score = 0
    combined_correct = 0
    combined_incorrect = 0
    combined_total = 0
    combined_items = []

    for gtype in types_present:
        if gtype == "grid_challenge":
            result = await gamified_round.grade_grid_challenge_session(session_id)
        elif gtype == "motion_challenge":
            result = await gamified_round.grade_motion_challenge_session(session_id)
        else:
            result = await gamified_round.grade_session(session_id, gtype, answers)
        combined_raw_score += result.get("raw_score") or 0
        combined_correct += result.get("correct") or 0
        combined_incorrect += result.get("incorrect") or 0
        combined_total += result.get("total") or 0
        for item in result.get("items", []):
            combined_items.append({**item, "gameType": gtype})

    score = (combined_correct / combined_total) if combined_total else 0
    result_out = {
        "score": round(score, 3),
        "correct": combined_correct,
        "incorrect": combined_incorrect,
        "total": combined_total,
        "raw_score": combined_raw_score,
        "passed": score >= section.get("cutoff", 0.5),
        "items": combined_items,
    }
    await db.game_session.update_one(
        {"session_id": session_id},
        {"$set": {
            "raw_score": combined_raw_score, "correct": combined_correct,
            "incorrect": combined_incorrect, "total": combined_total,
            "graded_at": iso(now_utc()),
        }},
    )
    return result_out


async def _grade_coding_section(section: dict, answers: Dict[str, Any]) -> dict:
    problems = section.get("questions", [])
    per_problem = []
    total_score = 0.0
    graded_count = 0
    for p in problems:
        # Skip problems whose AI-generated tests couldn't be validated \u2013 we
        # can't fairly grade against untrusted expected outputs.
        if p.get("_reference_broken"):
            per_problem.append({
                "problem_id": str(p.get("id")),
                "title": p.get("title"),
                "skipped": True,
                "reason": "Test cases could not be validated; this problem doesn't count.",
            })
            continue
        pid = str(p.get("id"))
        sub = answers.get(pid) or {}
        code = sub.get("code", "")
        language = sub.get("language", "python")
        visible = p.get("visible_tests", []) or []
        hidden = p.get("hidden_tests", []) or []
        vpass, _vdetails = await asyncio.to_thread(_lang_run_tests, language, code, visible)
        hpass, _hdetails = await asyncio.to_thread(_lang_run_tests, language, code, hidden)
        vtotal, htotal = len(visible), len(hidden)
        tests_pass = vpass + hpass
        tests_total = vtotal + htotal
        pct = (tests_pass / tests_total) if tests_total else 0
        # AI grade for note
        note = await call_json_gpt(
            "You are a coding interviewer. Return only strict JSON.\n\n" + GRADING_INJECTION_DEFENSE,
            grade_coding_prompt(p, code, language, vpass, vtotal, hpass, htotal),
        ) or {"score": int(pct * 100), "complexity_note": "", "correctness_note": "", "style_note": ""}
        note = _attach_grading_flag(note)
        per_problem.append({
            "problem_id": pid,
            "title": p.get("title"),
            "visible": {"passed": vpass, "total": vtotal},
            "hidden": {"passed": hpass, "total": htotal},
            "ai": note,
        })
        total_score += pct
        graded_count += 1
    n = max(1, graded_count)
    score = total_score / n
    return {
        "score": round(score, 3),
        "problems": per_problem,
        "passed": score >= section.get("cutoff", 0.5),
    }


async def _grade_debugging_section(section: dict, answers: Dict[str, Any]) -> dict:
    """Grades Round 3 (Debugging Assessment) by reusing debugging_bank.
    grade_debugging_submission() per problem -- the exact same code_runner.
    run_tests() pipeline _grade_coding_section (above) already uses for the
    existing "coding" round, and the same grading primitive
    /api/dev/debugging/run calls for the standalone dev-preview. No AI note
    here (unlike coding) -- a debugging problem's correctness is fully
    determined by test pass/fail, there's nothing subjective to comment on.

    grade_debugging_submission() itself returns full per-test detail
    (including hidden test input/expected/got) -- fine for the dev-only
    route, which has no live attempt to protect, but this response is
    persisted into section_results and handed straight back to the client
    in submit_section's HTTP response. Strip to aggregate counts only here,
    matching _grade_coding_section's own convention above (which never
    exposes hidden test detail either) -- otherwise a candidate could read
    off the hidden tests' exact inputs/expected outputs from their own
    submit response.
    """
    problems = section.get("questions", [])
    per_problem = []
    total_score = 0.0
    for p in problems:
        pid = str(p.get("id"))
        sub = answers.get(pid) or {}
        code = sub.get("code", "")
        language = sub.get("language", "python")
        result = await asyncio.to_thread(debugging_bank.grade_debugging_submission, p, code, language)
        per_problem.append({
            "problem_id": result["problem_id"],
            "language": result["language"],
            "title": p.get("title"),
            "visible": {"passed": result["visible"]["passed"], "total": result["visible"]["total"]},
            "hidden": {"passed": result["hidden"]["passed"], "total": result["hidden"]["total"]},
            "score": result["score"],
            "passed": result["passed"],
        })
        total_score += result["score"]
    n = max(1, len(problems))
    score = total_score / n
    return {
        "score": round(score, 3),
        "problems": per_problem,
        "passed": score >= section.get("cutoff", 0.5),
    }


async def _grade_capgemini_round1_section(section: dict, answers: Dict[str, Any]) -> dict:
    """Grades all 6 sub-parts of Capgemini's Round 1 Communication
    Assessment together (one section, see companies.py's single-timer
    reasoning). Reads correct_option/rubric straight off `section` -- the
    FULL, unstripped document submit_section already fetched via its own
    plain find_one (never the get_oa-stripped shape) -- so this is
    server-side re-derivation, same principle as every other grader here;
    the client-submitted `answers` dict is only ever compared against, never
    trusted as the source of truth.

    business_writing grading is a genuine async LLM call
    (grade_business_writing_submission), AWAITED HERE SYNCHRONOUSLY within
    this same request -- mirroring _grade_essay_section/_grade_speaking_
    section's existing pattern exactly (no background job queue anywhere in
    this codebase; essay/speaking already block the HTTP response on their
    LLM grading call, so this doesn't introduce a new async model). This
    matters for /review's completion gate: because grading fully resolves
    (to "graded" or "grading_failed") before this function returns, and
    submit_section persists section_results / advances current_section_index
    only AFTER this returns, there's no window where attempt["status"] can
    flip to "completed" while a business_writing scenario is still
    "grading_pending" -- confirmed by test, not assumed (see
    test_capgemini_round1_e2e.py).

    Each of the 28 drawn items (10 grammar + 6 situational + 4 reading_comp
    sub-questions + 2 business_writing + 4 listening_comp sub-questions + 2
    spoken_sim) contributes one 0.0-1.0 score to the section average: binary
    correct/incorrect for the MCQ-shaped parts, scaled_score/100 for
    business_writing/spoken_sim (continuous, same convention
    _grade_essay_section/_grade_speaking_section already use for LLM-scored
    0-100 items -- spoken_sim's read_aloud items are scaled_score/100 too,
    even though that score comes from deterministic WER banding rather than
    an LLM call).

    "listening_comp" re-derives correctness for each clip's nested
    sub-questions the exact same way "reading_comp" does (question_focus/
    subquestion nesting is structurally identical between the two banks).

    "spoken_sim" (added 2026-08, follow-up wiring pass) grades the
    candidate's Whisper transcript (submitted via the existing generic
    POST /oa/{attempt_id}/transcribe endpoint, then passed through
    submit_section's normal answers dict exactly like an essay/speaking
    answer) against the FULL stored item -- read_aloud via deterministic WER
    (grade_read_aloud_response, no LLM call), respond_to_prompt via the
    rubric-LLM pipeline reused from business_writing
    (grade_respond_to_prompt_submission)."""
    per_item_scores: List[float] = []
    breakdown: Dict[str, Any] = {
        "grammar": [], "situational": [], "reading_comp": [], "business_writing": [], "listening_comp": [],
        "spoken_sim": [],
    }

    for q in section.get("questions", []):
        part = q.get("part")
        qid = str(q.get("id"))

        if part == "grammar" or part == "situational":
            submitted = answers.get(qid)
            correct = submitted is not None and str(submitted) == q.get("correct_option")
            per_item_scores.append(1.0 if correct else 0.0)
            breakdown[part].append({"id": qid, "submitted": submitted, "correct": correct})

        elif part == "reading_comp" or part == "listening_comp":
            for subq in q.get("questions", []) or []:
                sub_qid = str(subq.get("question_id"))
                submitted = answers.get(sub_qid)
                correct = submitted is not None and str(submitted) == subq.get("correct_option")
                per_item_scores.append(1.0 if correct else 0.0)
                breakdown[part].append({"id": sub_qid, "submitted": submitted, "correct": correct})

        elif part == "business_writing":
            email_text = answers.get(qid, "") or ""
            grading = await capgemini_recruitment_process.grade_business_writing_submission(q, email_text)
            per_item_scores.append((grading.get("scaled_score", 0) or 0) / 100.0)
            breakdown["business_writing"].append({"id": qid, **grading})

        elif part == "spoken_sim":
            # `answers[qid]` is the transcript text the frontend already
            # produced via POST /oa/{attempt_id}/transcribe (the existing
            # generic Groq-Whisper endpoint -- see its own docstring; it
            # never branches by section type, so nothing there needed to
            # change for this section) and submitted exactly like an essay/
            # speaking answer, keyed by question id. The transcript is never
            # trusted as ground truth beyond being the thing to grade --
            # read_aloud compares it against `q["passage_text"]` (the FULL,
            # unstripped doc this function already has, same re-derivation
            # principle as every other part here), respond_to_prompt grades
            # it against `q["rubric"]`.
            transcript = answers.get(qid, "") or ""
            item_type = q.get("item_type")
            if item_type == "read_aloud":
                grading = capgemini_recruitment_process.grade_read_aloud_response(q, transcript)
            else:
                grading = await capgemini_recruitment_process.grade_respond_to_prompt_submission(q, transcript)
            per_item_scores.append((grading.get("scaled_score", 0) or 0) / 100.0)
            breakdown["spoken_sim"].append({"id": qid, "item_type": item_type, **grading})

    total = len(per_item_scores)
    score = (sum(per_item_scores) / total) if total else 0.0
    return {
        "score": round(score, 3),
        "total": total,
        "breakdown": breakdown,
        "passed": score >= section.get("cutoff", 0.5),
    }


async def _grade_capgemini_round2_ai_literacy_section(section: dict, answers: Dict[str, Any]) -> dict:
    """Grades Round 2's AI Literacy section (2026-09/10, Round 2 wiring
    pass). Doesn't fit the generic _grade_mcq_like: items here are
    scenario-nested (scenario -> questions: [...]), same nesting shape as
    capgemini_round1's reading_comp/listening_comp sub-questions, but each
    leaf question uses a LETTER-KEYED correct_option ("A".."D", matching
    how this bank was authored -- see draw_section7_questions' docstring)
    instead of reading_comp/listening_comp's own correct_option convention
    or the flat MCQ types' int correct_index. Re-derives correctness from
    `section` -- the FULL, unstripped doc submit_section already fetched --
    never the client-submitted answer, same principle as every grader
    here."""
    per_item_scores: List[float] = []
    breakdown: List[Dict[str, Any]] = []
    for scenario in section.get("questions", []):
        for subq in scenario.get("questions") or []:
            sub_qid = str(subq.get("question_id"))
            submitted = answers.get(sub_qid)
            correct = submitted is not None and str(submitted).strip().upper() == subq.get("correct_option")
            per_item_scores.append(1.0 if correct else 0.0)
            breakdown.append({"id": sub_qid, "submitted": submitted, "correct": correct})
    total = len(per_item_scores)
    score = (sum(per_item_scores) / total) if total else 0.0
    return {
        "score": round(score, 3),
        "correct": int(sum(per_item_scores)),
        "total": total,
        "breakdown": breakdown,
        "passed": score >= section.get("cutoff", 0.5),
    }


def _attach_grading_flag(result: Dict[str, Any], max_score: float = 100, score_key: str = "score") -> Dict[str, Any]:
    """Adds `flagged_for_review`/`flag_reason` (advisory only -- never
    alters `result[score_key]`) to any LLM grading result shaped like
    {score, ...free-text fields...} -- essay/speaking's {strengths,
    weaknesses, rewrite_suggestion}, coding's {complexity_note,
    correctness_note, style_note}, interview's {signals_hit, missed,
    one_line_verdict}, or resume analysis's {strengths, weaknesses,
    verdict} (pass score_key="fit_score" there). See
    ai_service.flag_suspicious_grading for the heuristic itself."""
    text_fields: List[str] = []
    for k, v in result.items():
        if k == score_key:
            continue
        if isinstance(v, str):
            text_fields.append(v)
        elif isinstance(v, list):
            text_fields.extend(x for x in v if isinstance(x, str))
    reason = flag_suspicious_grading([(result.get(score_key, 0) or 0, max_score)], text_fields)
    result["flagged_for_review"] = reason is not None
    result["flag_reason"] = reason
    return result


async def _grade_essay_section(section: dict, answers: Dict[str, Any]) -> dict:
    prompts = section.get("questions", [])
    graded = []
    total = 0.0
    for p in prompts:
        qid = str(p.get("id"))
        answer_text = answers.get(qid, "") or ""
        min_w = int(p.get("min_words", 100))
        max_w = int(p.get("max_words", 300))
        topic = p.get("topic", "Essay")
        result = await call_json_gpt(
            "You are a strict essay evaluator. Return only strict JSON.\n\n" + GRADING_INJECTION_DEFENSE,
            grade_essay_prompt(topic, answer_text, min_w, max_w),
        ) or {"score": 0, "strengths": [], "weaknesses": [], "rewrite_suggestion": ""}
        result = _attach_grading_flag(result)
        graded.append({"prompt_id": qid, "topic": topic, **result})
        total += (result.get("score", 0) or 0) / 100.0
    n = max(1, len(prompts))
    score = total / n
    return {"score": round(score, 3), "essays": graded, "passed": score >= section.get("cutoff", 0.5)}


async def _grade_speaking_section(section: dict, answers: Dict[str, Any]) -> dict:
    """Mirrors _grade_essay_section exactly (same generic scoring machinery —
    see ai_service.grade_spoken_response_prompt's docstring for why the prompt
    wording differs from essay grading). `answers[qid]` is the transcript text
    the frontend already produced via POST /oa/{attempt_id}/transcribe."""
    prompts = section.get("questions", [])
    graded = []
    total = 0.0
    for p in prompts:
        qid = str(p.get("id"))
        transcript = answers.get(qid, "") or ""
        min_w = int(p.get("min_words", 70))
        max_w = int(p.get("max_words", 170))
        topic = p.get("topic", "Speaking")
        result = await call_json_gpt(
            "You are a fair, encouraging spoken-English evaluator. Return only strict JSON.\n\n" + GRADING_INJECTION_DEFENSE,
            grade_spoken_response_prompt(topic, transcript, min_w, max_w),
        ) or {"score": 0, "strengths": [], "weaknesses": [], "rewrite_suggestion": ""}
        result = _attach_grading_flag(result)
        graded.append({"prompt_id": qid, "topic": topic, **result})
        total += (result.get("score", 0) or 0) / 100.0
    n = max(1, len(prompts))
    score = total / n
    return {"score": round(score, 3), "responses": graded, "passed": score >= section.get("cutoff", 0.5)}


async def _grade_comm_mixed_section(section: dict, answers: Dict[str, Any]) -> dict:
    """Accenture's mixed Communication Assessment: each question carries its
    own `mode` ("mcq" | "speaking"), graded accordingly — mcq items via the
    same correct_index check as _grade_mcq_like, speaking items via the same
    transcript-grading call as _grade_speaking_section. Both halves collapse
    into one 0.0-1.0 per-item score and average together, same as every
    other section here."""
    items = section.get("questions", [])
    total = len(items)
    per_item = []
    total_score = 0.0
    for q in items:
        qid = str(q.get("id"))
        mode = q.get("mode", "mcq")
        if mode == "speaking":
            transcript = answers.get(qid, "") or ""
            min_w = int(q.get("min_words", 70))
            max_w = int(q.get("max_words", 170))
            topic = q.get("topic", "Speaking")
            result = await call_json_gpt(
                "You are a fair, encouraging spoken-English evaluator. Return only strict JSON.\n\n" + GRADING_INJECTION_DEFENSE,
                grade_spoken_response_prompt(topic, transcript, min_w, max_w),
            ) or {"score": 0}
            result = _attach_grading_flag(result)
            item_score = (result.get("score", 0) or 0) / 100.0
            per_item.append({
                "question_id": qid, "mode": mode, "score": round(item_score, 3),
                "flagged_for_review": result["flagged_for_review"], "flag_reason": result["flag_reason"],
            })
        else:
            raw_user = answers.get(qid)
            try:
                user_index = int(raw_user) if raw_user is not None and raw_user != "" else None
            except Exception:
                user_index = None
            item_score = 1.0 if (user_index is not None and user_index == q.get("correct_index")) else 0.0
            per_item.append({"question_id": qid, "mode": mode, "score": item_score})
        total_score += item_score
    score = (total_score / total) if total else 0
    passed = score >= section.get("cutoff", 0.5)
    return {"score": round(score, 3), "items": per_item, "total": total, "passed": passed}


_PUNCT_RE = re.compile(r"[^\w\s]")


def _normalize_for_similarity(text: str) -> str:
    return _PUNCT_RE.sub("", (text or "").lower()).split()


def _grade_reading_listening_section(section: dict, answers: Dict[str, Any]) -> dict:
    """Deterministic string-similarity grading — NOT an LLM call. Compares the
    Whisper transcript against the reference sentence the candidate was shown
    (not secret; it's what they read/repeat aloud)."""
    items = section.get("questions", [])
    per_item = []
    total_score = 0.0
    for q in items:
        qid = str(q.get("id"))
        reference = q.get("text", "") or ""
        transcript = answers.get(qid, "") or ""
        ratio = difflib.SequenceMatcher(
            None, _normalize_for_similarity(reference), _normalize_for_similarity(transcript),
        ).ratio()
        per_item.append({"question_id": qid, "score": round(ratio, 3)})
        total_score += ratio
    n = max(1, len(items))
    score = total_score / n
    return {"score": round(score, 3), "items": per_item, "total": len(items), "passed": score >= section.get("cutoff", 0.5)}


async def _grade_voice_mixed_section(section: dict, answers: Dict[str, Any]) -> dict:
    """LTIMindtree's Spoken English / Communication — combines
    _grade_reading_listening_section's deterministic string-similarity
    (mode="listening") with _grade_comm_mixed_section's essay-pipeline
    transcript grading (mode="speaking") in one section, per-item mode tag."""
    items = section.get("questions", [])
    total = len(items)
    per_item = []
    total_score = 0.0
    for q in items:
        qid = str(q.get("id"))
        mode = q.get("mode", "listening")
        if mode == "speaking":
            transcript = answers.get(qid, "") or ""
            min_w = int(q.get("min_words", 70))
            max_w = int(q.get("max_words", 170))
            topic = q.get("topic", "Speaking")
            result = await call_json_gpt(
                "You are a fair, encouraging spoken-English evaluator. Return only strict JSON.\n\n" + GRADING_INJECTION_DEFENSE,
                grade_spoken_response_prompt(topic, transcript, min_w, max_w),
            ) or {"score": 0}
            result = _attach_grading_flag(result)
            item_score = (result.get("score", 0) or 0) / 100.0
            flag_info = {"flagged_for_review": result["flagged_for_review"], "flag_reason": result["flag_reason"]}
        else:
            reference = q.get("text", "") or ""
            transcript = answers.get(qid, "") or ""
            item_score = difflib.SequenceMatcher(
                None, _normalize_for_similarity(reference), _normalize_for_similarity(transcript),
            ).ratio()
            flag_info = {}
        per_item.append({"question_id": qid, "mode": mode, "score": round(item_score, 3), **flag_info})
        total_score += item_score
    score = (total_score / total) if total else 0
    passed = score >= section.get("cutoff", 0.5)
    return {"score": round(score, 3), "items": per_item, "total": total, "passed": passed}


def _run_tests_legacy_placeholder():
    """No longer used \u2013 replaced by code_runner.run_tests()."""
    pass


class RunCodeIn(BaseModel):
    attempt_id: str
    section_key: str
    problem_id: str
    language: str
    code: str


@api.post("/oa/run")
async def run_code(body: RunCodeIn, user: Dict[str, Any] = Depends(require_user)):
    attempt = await db.oa_attempts.find_one(
        {"attempt_id": body.attempt_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not attempt:
        raise HTTPException(404, "Attempt not found")
    section = next((s for s in attempt["sections"] if s["key"] == body.section_key), None)
    if not section:
        raise HTTPException(404, "Section not found")
    problem = next((q for q in section.get("questions", []) if str(q.get("id")) == str(body.problem_id)), None)
    if not problem:
        raise HTTPException(404, "Problem not found")
    visible = problem.get("visible_tests", []) or []
    _passed, details = await asyncio.to_thread(_lang_run_tests, body.language, body.code, visible)
    # Reshape details to the API contract expected by the frontend.
    results = [{
        "input": d["input"], "expected": d["expected"], "got": d["got"],
        "passed": d["passed"],
        "error": d.get("error") or (d.get("stderr") if not d["passed"] else None),
    } for d in details]
    return {"results": results, "language": body.language, "supported_languages": SUPPORTED_LANGUAGES}


class DevDebuggingRunIn(BaseModel):
    problem_id: str
    language: str
    code: str


@api.post("/dev/debugging/run")
async def dev_debugging_run(body: DevDebuggingRunIn, user: Dict[str, Any] = Depends(require_user)):
    """DEV/TEST-ONLY: backs /dev/debugging-preview's run+submit actions on
    the frontend (see DevDebuggingPreview.jsx). Exercises
    debugging_bank.grade_debugging_submission() -- which itself reuses
    code_runner.run_tests(), the exact same pipeline _grade_coding_section
    already uses for the real "coding" round -- through a genuine HTTP round
    trip, so the dev-preview's click-through tests real grading wired to a
    real UI action, not a client-side simulation.

    Reads no oa_attempts document and writes nothing -- NOT part of any OA
    attempt/section flow. Round 3 (Debugging Assessment) is still not wired
    into companies.py or any real company's round list; this route exists
    solely so the standalone dev-preview can be verified end-to-end.
    """
    problem = debugging_bank.get_problem(body.problem_id)
    if not problem:
        raise HTTPException(404, "Unknown debugging problem id")
    result = await asyncio.to_thread(debugging_bank.grade_debugging_submission, problem, body.code, body.language)
    return result


@api.post("/oa/{attempt_id}/transcribe")
async def oa_transcribe(
    attempt_id: str,
    section_key: str = Form(...),
    question_id: str = Form(...),
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(require_user),
):
    """Stateless voice-to-text utility for Cognizant's Speaking / Reading &
    Listening sections. Doesn't persist anything itself — the frontend takes
    the returned transcript and submits it through the normal
    setAnswer/POST /oa/{attempt_id}/section flow, exactly like an essay
    answer (plain text keyed by question id)."""
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Not found")
    audio_bytes = await file.read()
    if len(audio_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "Audio too large (max 10MB)")
    transcript = await transcribe_audio(audio_bytes, file.filename or "audio.webm")
    logger.info(f"transcribe: attempt={attempt_id} section={section_key} q={question_id} chars={len(transcript)}")
    return {"transcript": transcript}


@api.post("/oa/{attempt_id}/section/check")
async def check_puzzle_answer(attempt_id: str, body: CheckPuzzleIn, user: Dict[str, Any] = Depends(require_user)):
    """Live, per-puzzle feedback for gamified_round sections DURING play
    (the running-score bar) -- NOT the final grade. Ownership-checked the
    same way submit_section is; the actual grading/scoring lookup lives in
    gamified_round.check_answer, which never returns correctAnswer, only
    {correct, pointsAwarded, runningScore}. submit_section's grade_session
    call remains the sole source of truth for pass/fail -- this endpoint
    never writes anything grade_session reads."""
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Not found")
    section = next((s for s in attempt["sections"] if s["key"] == body.section_key), None)
    if not section or section["type"] != "gamified_round":
        raise HTTPException(404, "Section not found")
    return await gamified_round.check_answer(
        attempt_id, body.section_key, body.puzzle_id, body.selected, body.timedOut, body.timeTakenMs,
    )


@api.post("/oa/{attempt_id}/section/grid-challenge/phase")
async def grid_challenge_phase(attempt_id: str, body: GridChallengePhaseIn, user: Dict[str, Any] = Depends(require_user)):
    """Phase-gated content reveal for grid_challenge -- ownership-checked
    the same way check_puzzle_answer is, but the actual sequencing
    enforcement (block N unreachable until block N-1 is fully answered)
    lives in gamified_round.get_grid_challenge_phase, checked against
    game_session state server-side. A PermissionError there means the
    gate genuinely rejected the request (mapped to HTTP 403) -- not a
    convention the frontend is trusted to honor on its own."""
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Not found")
    section = next((s for s in attempt["sections"] if s["key"] == body.section_key), None)
    if not section or section["type"] != "gamified_round":
        raise HTTPException(404, "Section not found")
    try:
        return await gamified_round.get_grid_challenge_phase(
            attempt_id, body.section_key, body.puzzle_id, body.phase, body.blockIndex,
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@api.post("/oa/{attempt_id}/section/grid-challenge/answer")
async def grid_challenge_answer(attempt_id: str, body: GridChallengeAnswerIn, user: Dict[str, Any] = Depends(require_user)):
    """Live per-sub-answer feedback for grid_challenge (7 judgments + a
    3-position recall) -- same never-leak-the-answer discipline as
    check_puzzle_answer, dispatched through phase_check (not answer_check)
    since one grid_challenge puzzle has multiple gradable sub-answers.
    Final pass/fail still comes from submit_section ->
    _grade_gamified_round_section -> grade_grid_challenge_session, which
    independently re-derives everything and never trusts this endpoint's
    own running tally."""
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Not found")
    section = next((s for s in attempt["sections"] if s["key"] == body.section_key), None)
    if not section or section["type"] != "gamified_round":
        raise HTTPException(404, "Section not found")
    return await gamified_round.check_grid_challenge_answer(
        attempt_id, body.section_key, body.puzzle_id, body.phase,
        body.blockIndex, body.judgmentIndex, body.answer, body.timeTakenMs, body.timedOut,
    )


@api.post("/oa/{attempt_id}/section/motion-challenge/move")
async def motion_challenge_move_route(attempt_id: str, body: MotionChallengeMoveIn, user: Dict[str, Any] = Depends(require_user)):
    """Server-authoritative per-move validation for motion_challenge --
    ownership-checked the same way check_puzzle_answer/grid_challenge_phase
    are. Unlike grid_challenge's progressive reveal, nothing here is
    secret; the whole board is visible from move one. What's enforced
    server-side is state mutation: gamified_round.motion_challenge_move
    replays the FULL stored move history from the puzzle's own initial
    board on every call, never trusting a client-claimed "current board",
    and rejects moves against a level that's already won or already lost
    (budget exhausted) rather than letting the client re-trigger them. A
    PermissionError there means this puzzle_id was never served to this
    session (mapped to HTTP 403) -- a real ownership rejection, not a
    normal "wrong move" response (those come back as a normal 200 with
    valid=False)."""
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Not found")
    section = next((s for s in attempt["sections"] if s["key"] == body.section_key), None)
    if not section or section["type"] != "gamified_round":
        raise HTTPException(404, "Section not found")
    try:
        return await gamified_round.motion_challenge_move(
            attempt_id, body.section_key, body.puzzle_id, body.blockId, body.direction,
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))


@api.post("/oa/{attempt_id}/section/motion-challenge/undo")
async def motion_challenge_undo_route(attempt_id: str, body: MotionChallengeUndoIn, user: Dict[str, Any] = Depends(require_user)):
    """Pops the last move from server-held history -- free to perform,
    doesn't refund a budget move (see gamified_round.motion_challenge_undo
    for why that requires no special bookkeeping). Same ownership check as
    the move route above; rejected the same way (403) if this puzzle_id
    was never served to this session."""
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Not found")
    section = next((s for s in attempt["sections"] if s["key"] == body.section_key), None)
    if not section or section["type"] != "gamified_round":
        raise HTTPException(404, "Section not found")
    try:
        return await gamified_round.motion_challenge_undo(attempt_id, body.section_key, body.puzzle_id)
    except PermissionError as e:
        raise HTTPException(403, str(e))


@api.post("/oa/{attempt_id}/section/motion-challenge/state")
async def motion_challenge_state_route(attempt_id: str, body: MotionChallengeStateIn, user: Dict[str, Any] = Depends(require_user)):
    """Read-only current-state fetch -- never mutates anything, safe to
    call any number of times. Lets the frontend sync to the real
    server-held state whenever a level is (re-)entered, instead of
    assuming it always starts fresh -- added after Step 4/5 verification
    surfaced a real bug: the frontend was unconditionally resetting to
    the puzzle's pristine starting board on every mount, silently
    diverging from whatever move history the server already had."""
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Not found")
    section = next((s for s in attempt["sections"] if s["key"] == body.section_key), None)
    if not section or section["type"] != "gamified_round":
        raise HTTPException(404, "Section not found")
    try:
        return await gamified_round.motion_challenge_state(attempt_id, body.section_key, body.puzzle_id)
    except PermissionError as e:
        raise HTTPException(403, str(e))


@api.post("/oa/{attempt_id}/section")
async def submit_section(attempt_id: str, body: SubmitSectionIn, user: Dict[str, Any] = Depends(require_user)):
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Not found")
    section = next((s for s in attempt["sections"] if s["key"] == body.section_key), None)
    if not section:
        raise HTTPException(404, "Section not found")

    stype = section["type"]
    if stype == "coding":
        result = await _grade_coding_section(section, body.answers)
    elif stype == "debugging":
        result = await _grade_debugging_section(section, body.answers)
    elif stype == "ai_assisted":
        # body.answers is deliberately IGNORED here -- see
        # _finalize_ai_assisted_section's docstring for why (Round 4's
        # true state lives in db.ai_assisted_sessions, not an answers
        # payload; a client-supplied score/stage claim has no effect).
        result = await _finalize_ai_assisted_section(section, attempt_id, user["user_id"])
    elif stype == "essay":
        result = await _grade_essay_section(section, body.answers)
    elif stype == "speaking":
        result = await _grade_speaking_section(section, body.answers)
    elif stype == "reading_listening":
        result = _grade_reading_listening_section(section, body.answers)
    elif stype == "comm_mixed":
        result = await _grade_comm_mixed_section(section, body.answers)
    elif stype == "voice_mixed":
        result = await _grade_voice_mixed_section(section, body.answers)
    elif stype == "gamified_round":
        result = await _grade_gamified_round_section(section, body.answers, attempt_id)
    elif stype == "capgemini_round1":
        result = await _grade_capgemini_round1_section(section, body.answers)
    elif stype == "capgemini_round2_ai_literacy":
        result = await _grade_capgemini_round2_ai_literacy_section(section, body.answers)
    else:  # mcq / topic_mcq / pseudocode / comm / grammar / comprehension / capgemini_round2_technical
        result = _grade_mcq_like(section, body.answers)

    # Persist
    section_results = attempt.get("section_results", {})
    section_results[body.section_key] = result
    answers = attempt.get("answers", {})
    answers[body.section_key] = body.answers
    current_idx = attempt.get("current_section_index", 0) + 1
    total_sections = len(attempt["sections"])
    status = "in_progress"
    if current_idx >= total_sections:
        status = "completed"
    # Capgemini tier: computed here, server-side, only once the attempt is
    # completed. Reads stored section_results alone, so nothing the client sends
    # in this request can change the outcome.
    tier_eval = None
    if status == "completed" and attempt.get("company_id") == "capgemini":
        tier_eval = capgemini_tiers.evaluate(section_results)
    update = {
        "section_results": section_results,
        "answers": answers,
        "current_section_index": current_idx,
        "status": status,
        "completed_at": iso(now_utc()) if status == "completed" else None,
    }
    if tier_eval is not None:
        update["capgemini_tier"] = {**tier_eval, "computed_at": iso(now_utc())}
    await db.oa_attempts.update_one({"attempt_id": attempt_id}, {"$set": update})
    response = {"section_result": result, "next_index": current_idx, "status": status}
    if tier_eval is not None:
        response["capgemini_tier"] = {"tier": tier_eval["tier"], "lpa": tier_eval["lpa"]}
    return response


@api.get("/oa/{attempt_id}/review")
async def oa_review(attempt_id: str, user: Dict[str, Any] = Depends(require_user)):
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Not found")

    # Gating fix (2026-08, security audit follow-up): review used to build
    # and return the full answer_key regardless of completion — a candidate
    # could call this mid-attempt and see correct_index for sections not yet
    # submitted. Reuses submit_section's EXACT completion signal
    # (attempt["status"] == "completed", flipped there once
    # current_section_index >= total sections) rather than inventing a new
    # per-section check — this is a whole-attempt gate, not a rolling
    # per-section reveal: some-but-not-all sections submitted is treated
    # identically to none submitted. Short-circuits before any
    # composite/verdict/answer_key computation, so no question, answer, or
    # score content of any kind is included in the "not yet" response.
    if attempt.get("status") != "completed":
        return {"available": False, "reason": "oa_incomplete", "attempt_id": attempt_id}

    section_results = attempt.get("section_results", {})
    scoring_mode = attempt.get("scoring_mode", "composite")
    # Weighted composite: sections can carry a `weight` (0 → unscored, like
    # Accenture Behavioral and the new Core Assessment behavioral). If no
    # section defines a weight, we fall back to equal weighting.
    section_by_key = {s["key"]: s for s in attempt["sections"]}
    weighted_parts: List[Tuple[float, float]] = []
    for k, v in section_results.items():
        sec_cfg = section_by_key.get(k, {})
        w = sec_cfg.get("weight")
        if w is None:
            w = 1.0
        try:
            w = float(w)
        except Exception:
            w = 1.0
        if w <= 0:
            continue
        weighted_parts.append((w, float(v.get("score", 0))))

    if weighted_parts:
        total_w = sum(w for w, _ in weighted_parts)
        composite = sum(w * s for w, s in weighted_parts) / total_w if total_w else 0
    else:
        # No section carried a positive weight (all unscored) — degenerate case.
        composite = 0.0

    # Weakest = lowest-scoring scored section
    weakest = None
    weakest_score = 2.0
    for k, v in section_results.items():
        w_val = section_by_key.get(k, {}).get("weight", 1.0)
        try:
            w_f = float(w_val)
        except Exception:
            w_f = 1.0
        if w_f <= 0:
            continue
        s = v.get("score", 0)
        if s < weakest_score:
            weakest = k
            weakest_score = s

    if scoring_mode == "sectional":
        any_failed = any(not v.get("passed", False) for v in section_results.values())
        if any_failed:
            verdict = "not_ready"
        elif composite >= 0.7:
            verdict = "clear"
        else:
            verdict = "borderline"
    else:
        if composite >= 0.65:
            verdict = "clear"
        elif composite >= 0.45:
            verdict = "borderline"
        else:
            verdict = "not_ready"

    # Build answer key for MCQ-like sections (mcq / pseudocode / comm / game).
    # Coding + essay sections don't have a single "correct answer", so we skip
    # those to keep the UI honest.
    stored_answers = attempt.get("answers", {}) or {}
    answer_key: List[Dict[str, Any]] = []
    _MCQ_TYPES = {"mcq", "topic_mcq", "pseudocode", "comm", "game", "grammar", "comprehension"}
    for s in attempt["sections"]:
        stype = s.get("type")
        if stype not in _MCQ_TYPES:
            continue
        skey = s.get("key")
        section_answers = stored_answers.get(skey, {}) or {}
        items = []
        for q in s.get("questions", []) or []:
            qid = str(q.get("id"))
            correct_index = q.get("correct_index")
            raw_user = section_answers.get(qid)
            try:
                user_index = int(raw_user) if raw_user is not None and raw_user != "" else None
            except Exception:
                user_index = None
            is_correct = (user_index is not None and user_index == correct_index)
            items.append({
                "id": qid,
                "prompt": q.get("prompt", ""),
                "options": q.get("options", []),
                "correct_index": correct_index,
                "user_index": user_index,
                "is_correct": is_correct,
                "answered": user_index is not None,
                "explanation": q.get("explanation", ""),
                "difficulty": q.get("difficulty"),
                "topic": q.get("topic"),
            })
        if items:
            answer_key.append({
                "section_key": skey,
                "section_name": s.get("name", skey),
                "section_type": stype,
                "questions": items,
            })

    return {
        "available": True,
        "attempt_id": attempt_id,
        "company_name": attempt["company_name"],
        "scoring_mode": scoring_mode,
        "section_results": _client_section_results(section_results),
        "composite_score": round(composite, 3),
        "weakest_section": weakest,
        "verdict": verdict,
        "sections_meta": [{"key": s["key"], "name": s["name"], "type": s["type"]} for s in attempt["sections"]],
        "answer_key": answer_key,
    }


# =============================================================================
#  Review Deck — per-user private drill collection of missed / saved MCQs
# =============================================================================

_MCQ_TYPES_FOR_DECK = {"mcq", "topic_mcq", "pseudocode", "comm", "game", "grammar", "comprehension"}


class DeckAddIn(BaseModel):
    attempt_id: str
    # If provided → only those specific questions are saved. If empty →
    # server saves every WRONG or SKIPPED MCQ from the attempt.
    question_ids: Optional[List[Dict[str, str]]] = None  # [{section_key, question_id}]


@api.post("/deck/add")
async def deck_add(body: DeckAddIn, user: Dict[str, Any] = Depends(require_user)):
    attempt = await db.oa_attempts.find_one(
        {"attempt_id": body.attempt_id, "user_id": user["user_id"]}, {"_id": 0},
    )
    if not attempt:
        raise HTTPException(404, "Attempt not found")

    stored_answers = attempt.get("answers", {}) or {}
    picks: List[dict] = []
    section_by_key = {s["key"]: s for s in attempt["sections"]}

    if body.question_ids:
        wanted = {(p["section_key"], p["question_id"]) for p in body.question_ids if p.get("section_key") and p.get("question_id")}
        for (skey, qid) in wanted:
            s = section_by_key.get(skey)
            if not s or s.get("type") not in _MCQ_TYPES_FOR_DECK:
                continue
            q = next((x for x in s.get("questions", []) if str(x.get("id")) == str(qid)), None)
            if q:
                picks.append((s, q))
    else:
        # Auto: every wrong or skipped MCQ from this attempt
        for s in attempt["sections"]:
            if s.get("type") not in _MCQ_TYPES_FOR_DECK:
                continue
            skey = s["key"]
            sect_answers = stored_answers.get(skey, {}) or {}
            for q in s.get("questions", []) or []:
                qid = str(q.get("id"))
                raw = sect_answers.get(qid)
                try:
                    ui = int(raw) if raw not in (None, "") else None
                except Exception:
                    ui = None
                if ui is None or ui != q.get("correct_index"):
                    picks.append((s, q))

    added, skipped = 0, 0
    for s, q in picks:
        qid = str(q.get("id"))
        skey = s["key"]
        existing = await db.review_deck.find_one({
            "user_id": user["user_id"],
            "source_attempt_id": body.attempt_id,
            "section_key": skey,
            "question_id": qid,
        })
        if existing:
            skipped += 1
            continue
        await db.review_deck.insert_one({
            "card_id": new_id("card"),
            "user_id": user["user_id"],
            "source_attempt_id": body.attempt_id,
            "company_name": attempt.get("company_name"),
            "section_name": s.get("name"),
            "section_key": skey,
            "question_id": qid,
            "prompt": q.get("prompt", ""),
            "options": q.get("options", []),
            "correct_index": q.get("correct_index"),
            "explanation": q.get("explanation", ""),
            "difficulty": q.get("difficulty"),
            "added_at": iso(now_utc()),
            "attempts": [],
            "mastered": False,
        })
        added += 1
    return {"added": added, "skipped_duplicates": skipped}


@api.get("/deck")
async def deck_list(user: Dict[str, Any] = Depends(require_user), unmastered: int = 0):
    q: Dict[str, Any] = {"user_id": user["user_id"]}
    if unmastered:
        q["mastered"] = False
    cards = []
    async for c in db.review_deck.find(q, {"_id": 0}).sort("added_at", -1):
        cards.append(c)
    total = len(cards)
    unmastered_count = sum(1 for c in cards if not c.get("mastered"))
    return {"cards": cards, "total": total, "unmastered": unmastered_count}


class DeckAttemptIn(BaseModel):
    chosen_index: int


@api.post("/deck/{card_id}/attempt")
async def deck_attempt(card_id: str, body: DeckAttemptIn, user: Dict[str, Any] = Depends(require_user)):
    card = await db.review_deck.find_one({"card_id": card_id, "user_id": user["user_id"]}, {"_id": 0})
    if not card:
        raise HTTPException(404, "Card not found")
    correct = int(body.chosen_index) == card.get("correct_index")
    entry = {"answered_at": iso(now_utc()), "chosen_index": int(body.chosen_index), "correct": correct}
    # A card is "mastered" after 2 consecutive correct attempts. Streak resets on wrong.
    attempts = card.get("attempts", []) or []
    attempts.append(entry)
    streak = 0
    for a in reversed(attempts):
        if a.get("correct"):
            streak += 1
        else:
            break
    mastered = streak >= 2
    await db.review_deck.update_one(
        {"card_id": card_id, "user_id": user["user_id"]},
        {"$set": {"attempts": attempts, "mastered": mastered}},
    )
    return {"correct": correct, "mastered": mastered, "correct_index": card.get("correct_index"), "explanation": card.get("explanation", "")}


@api.delete("/deck/{card_id}")
async def deck_delete(card_id: str, user: Dict[str, Any] = Depends(require_user)):
    r = await db.review_deck.delete_one({"card_id": card_id, "user_id": user["user_id"]})
    if not r.deleted_count:
        raise HTTPException(404, "Card not found")
    return {"deleted": True}


# =============================================================================
#  Interview
# =============================================================================

class StartInterviewIn(BaseModel):
    attempt_id: str


@api.post("/interview/start")
async def start_interview(body: StartInterviewIn, user: Dict[str, Any] = Depends(require_user)):
    attempt = await db.oa_attempts.find_one({"attempt_id": body.attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Attempt not found")

    # Free-tier lock: after the contest window ends, Free plan gets OA-only.
    if entitlements.free_is_oa_only(user):
        raise HTTPException(402, {
            "code": "interview_locked_free_tier",
            "message": "The Interview + Report phases are unlocked on paid plans. Upgrade to continue.",
        })

    resume_projects: List[dict] = []
    if attempt.get("resume_id"):
        resume = await db.resumes.find_one({"resume_id": attempt["resume_id"]}, {"_id": 0})
        if resume:
            resume_projects = resume.get("analysis", {}).get("extracted_projects", []) or []

    # If the source company defines an interview_difficulty (e.g. "Core
    # Assessment (Default)" wants medium-skew DSA), pass that hint through
    # so the interviewer LLM raises the DSA bar for this company.
    interview_difficulty = None
    company_cfg = get_company(attempt.get("company_id"))
    if company_cfg:
        interview_difficulty = company_cfg.get("interview_difficulty")

    plan = await call_json(
        "You plan realistic technical interviews. Return only strict JSON.",
        interview_plan_prompt(attempt["company_name"], resume_projects, interview_difficulty),
    ) or {"questions": []}

    # Harden: guarantee each question has string id + string prompt so the
    # frontend can always render it and submit answers without 422s.
    raw_questions = plan.get("questions", []) or []
    questions: List[dict] = []
    for i, q in enumerate(raw_questions):
        if not isinstance(q, dict):
            continue
        qid = q.get("id")
        if not isinstance(qid, str) or not qid.strip():
            qid = f"q{i+1}"
        prompt_val = q.get("prompt")
        if isinstance(prompt_val, dict) or isinstance(prompt_val, list):
            prompt_val = json.dumps(prompt_val)
        elif prompt_val is None:
            prompt_val = ""
        else:
            prompt_val = str(prompt_val)
        kind = q.get("kind") or "fundamentals"
        if not isinstance(kind, str):
            kind = "fundamentals"
        signals = q.get("expected_signals") or []
        if not isinstance(signals, list):
            signals = []
        questions.append({
            "id": qid,
            "kind": kind,
            "prompt": prompt_val,
            "expected_signals": [str(s) for s in signals],
        })

    interview_id = new_id("intv")
    interview = {
        "interview_id": interview_id,
        "user_id": user["user_id"],
        "attempt_id": body.attempt_id,
        "company_name": attempt["company_name"],
        "resume_id": attempt.get("resume_id"),
        "questions": questions,
        "answers": [],  # [{qid, answer, grade}]
        "current_index": 0,
        "status": "in_progress",
        "created_at": iso(now_utc()),
    }
    await db.interviews.insert_one(interview)
    interview.pop("_id", None)
    return interview


@api.get("/interview/{interview_id}")
async def get_interview(interview_id: str, user: Dict[str, Any] = Depends(require_user)):
    doc = await db.interviews.find_one({"interview_id": interview_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Not found")
    return doc


class AnswerIn(BaseModel):
    question_id: str
    answer: str


@api.post("/interview/{interview_id}/answer")
async def submit_interview_answer(interview_id: str, body: AnswerIn, user: Dict[str, Any] = Depends(require_user)):
    interview = await db.interviews.find_one({"interview_id": interview_id, "user_id": user["user_id"]}, {"_id": 0})
    if not interview:
        raise HTTPException(404, "Not found")
    question = next((q for q in interview["questions"] if str(q.get("id")) == str(body.question_id)), None)
    if not question:
        raise HTTPException(404, "Question not found")

    grade = await call_json(
        "You grade interview answers as an experienced engineer. Return only strict JSON.\n\n" + GRADING_INJECTION_DEFENSE,
        grade_answer_prompt(question, body.answer),
    ) or {"score": 0, "signals_hit": [], "missed": [], "follow_up": None, "one_line_verdict": ""}
    grade = _attach_grading_flag(grade)

    entry = {"question_id": body.question_id, "answer": body.answer, "grade": grade}
    answers = interview.get("answers", [])
    answers.append(entry)
    current_index = interview.get("current_index", 0) + 1
    status = "in_progress"
    if current_index >= len(interview["questions"]):
        status = "completed"

    await db.interviews.update_one(
        {"interview_id": interview_id},
        {"$set": {"answers": answers, "current_index": current_index, "status": status,
                  "completed_at": iso(now_utc()) if status == "completed" else None}},
    )
    return {"grade": grade, "next_index": current_index, "status": status}


# =============================================================================
#  DEV/TEST-ONLY: Capgemini Round 4 (AI-Assisted Coding) -- live staged
#  conversation backend. Modeled directly on the /interview/* trio above
#  (own dedicated Mongo collection, own *_id, user_id-scoped ownership,
#  grow-a-transcript-in-place per turn) -- the closest existing analog for
#  genuine multi-turn stateful LLM interaction in this codebase (see the
#  audit that preceded this pass). Schema/content/design this is built
#  against lives in banks/ai_assisted_bank.py (STAGE_ORDER, STAGE_CONFIG,
#  CONSENT_GATE, SELF_REVIEW, FINAL_SUMMARY_TEMPLATE).
#
#  NOT wired into companies.py or any real company's round list yet --
#  same sequencing discipline as Round 3 (debugging_bank): dev-preview
#  first, verified end-to-end, before any live-flow wiring. Backs
#  /dev/ai-assisted-preview (DevAiAssistedPreview.jsx / AiAssistedSection.jsx).
#
#  current_stage/progression is derived SERVER-SIDE from actual LLM
#  sufficiency judgments (stage_sufficiency_prompt/bug_explanation_grading_
#  prompt, both wrap_untrusted + GRADING_INJECTION_DEFENSE hardened, same
#  pairing as grade_answer_prompt above) or from the two deterministic
#  button gates below -- never from a client-submitted claim of what stage
#  it should be on.
# =============================================================================

_AI_ASSISTED_FREE_TEXT_STAGES = ("understand", "approach", "complexity", "explain_bug")

# Fixed, natural candidate-facing opener per free-text stage. STAGE_CONFIG's
# own `prompt_intro` (ai_assisted_bank.py) is written as an INSTRUCTION FOR
# THE GRADER ("Ask the candidate...") -- reused as-is for the LLM's judging
# context in stage_sufficiency_prompt, but not natural as literal chat text,
# so this is the actual shown phrasing (a deliberate, small implementation
# choice, not data-driven, since it's always the same ~3 openers).
_AI_ASSISTED_STAGE_OPENERS = {
    "understand": "First, in your own words -- what is this problem asking you to do? Talk me through the inputs, outputs, and any constraints that matter.",
    "approach": "Good. Now, what's your strategy? Walk me through the algorithmic approach you'd use to solve this.",
    "complexity": "And what's the time and space complexity of that approach?",
}

_AI_ASSISTED_CLIENT_SAFE_FIELDS = ("id", "title", "difficulty", "topic", "statement", "input_format", "output_format", "constraints")


def _strip_ai_assisted_problem(problem: Dict[str, Any]) -> Dict[str, Any]:
    """Client-safe projection -- deliberately excludes the ENTIRE
    ai_assisted_variant (flawed_code, corrected_code, bug_category,
    bug_explanation_key_points). The editor starts empty; flawed_code is
    revealed only via the consent="yes" action, corrected_code only at
    completion -- both delivered through session["revealed_code"], never
    through this problem projection."""
    return {k: problem[k] for k in _AI_ASSISTED_CLIENT_SAFE_FIELDS if k in problem}


def _ai_assisted_lang_display(lang: str) -> str:
    return {"cpp": "C++", "c": "C", "python": "Python", "java": "Java"}.get(lang, lang)


def _score_ai_assisted_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """PROPOSED SCORING DEFAULT -- NOT CONFIRMED. Flagged exactly like
    Section 2's rubric weighting was flagged earlier as an assumption
    pending sign-off; implemented as the working default, not a locked
    decision.

    Weights: self-review correctness 0.5 (the core test per the confirmed
    evidence -- did they correctly say "No" to the flawed code) +
    bug-explanation quality 0.35 (graded against that problem's
    bug_explanation_key_points) + stage-completion efficiency 0.15 across
    understand/approach/complexity (fewer re-prompts needed = higher
    signal of genuine understanding, min(1.0, 1/attempts) per stage,
    averaged).

    If self_review_result == "yes" (candidate blindly accepted the flawed
    code -- the UNCONFIRMED/assumed-default path, see ai_assisted_bank.
    SELF_REVIEW["on_yes"]), self_review_correct AND bug_explanation_quality
    are BOTH 0 by construction (that path never reaches explain_bug), so
    this formula alone caps the score at 0.15 * stage_efficiency <= 0.15 --
    well under any reasonable passing cutoff (0.5), with no special-cased
    override needed. That's the intentional "missing the actual point of
    the round should dominate the outcome" behavior, achieved by the
    weighting itself rather than an if-branch.
    """
    attempts = session.get("stage_attempts", {})
    effs = [min(1.0, 1.0 / max(1, attempts.get(st, 1))) for st in ("understand", "approach", "complexity")]
    stage_efficiency = sum(effs) / len(effs) if effs else 0.0

    self_review_correct = 1.0 if session.get("self_review_result") == "no" else 0.0
    bug_explanation_quality = (session.get("bug_explanation_score") or 0) / 100.0

    score = 0.5 * self_review_correct + 0.35 * bug_explanation_quality + 0.15 * stage_efficiency
    passed = score >= 0.5
    if not self_review_correct:
        reason = "candidate accepted the flawed code as correct -- missed the core test of this round"
    elif bug_explanation_quality >= 0.5:
        reason = "candidate correctly caught the flawed code and explained the real bug"
    else:
        reason = "candidate caught the flaw but the bug explanation was weak or generic"
    return {
        "score": round(score, 3),
        "passed": passed,
        "reason": reason,
        "components": {
            "self_review_correct": self_review_correct,
            "bug_explanation_quality": round(bug_explanation_quality, 3),
            "stage_efficiency": round(stage_efficiency, 3),
        },
    }


async def _finalize_ai_assisted_section(section: dict, attempt_id: str, user_id: str) -> dict:
    """submit_section's "ai_assisted" dispatch target. UNLIKE every other
    section's grading function, this deliberately does NOT take
    body.answers at all -- Round 4 is a stateful, multi-turn conversation
    whose true state lives in db.ai_assisted_sessions (created at
    generation time), not in an answers payload the client submits. A
    client-supplied score or stage claim has NO code path into this
    function to have any effect; everything is re-derived from the
    stored session server-side, via the exact same _score_ai_assisted_
    session() formula the live self_review="Yes"/explain_bug-sufficient
    paths already use.

    Also covers "the candidate ran out the timer or left mid-
    conversation" -- _score_ai_assisted_session is already null-safe
    against an in-progress session (self_review_result/
    bug_explanation_score simply score as 0 in the formula when unset),
    so scoring an abandoned session needs no special-casing here. Marks
    the session "completed" if it wasn't already, so it can't keep
    mutating after being scored."""
    session = await db.ai_assisted_sessions.find_one(
        {"attempt_id": attempt_id, "section_key": section["key"], "user_id": user_id}, {"_id": 0},
    )
    if not session:
        # No session was ever created (generation failed/crashed) -- score
        # as a complete miss rather than 500, same "never leave the
        # attempt hanging" philosophy as coding's _reference_broken skip.
        return {"score": 0.0, "passed": False, "reason": "no session found for this section", "problem_id": None}

    outcome = _score_ai_assisted_session(session)
    if session.get("status") != "completed":
        await db.ai_assisted_sessions.update_one(
            {"session_id": session["session_id"]},
            {"$set": {"status": "completed", "completed_at": iso(now_utc()), "final_outcome": outcome}},
        )
    return {
        "score": outcome["score"],
        "passed": outcome["passed"],
        "reason": outcome["reason"],
        "problem_id": session.get("problem_id"),
        "self_review_result": session.get("self_review_result"),
        "components": outcome["components"],
    }


class StartAiAssistedIn(BaseModel):
    problem_id: Optional[str] = None


@api.post("/dev/ai-assisted/start")
async def dev_ai_assisted_start(body: StartAiAssistedIn, user: Dict[str, Any] = Depends(require_user)):
    """DEV/TEST-ONLY: starts a new Round 4 (AI-Assisted Coding) session.
    Draws a REAL problem via ai_assisted_bank.sample_one() (the same
    verified draw function a future live wiring would use) unless a
    specific problem_id is passed (for reproducible manual/automated
    testing)."""
    if body.problem_id:
        problem = ai_assisted_bank.get_problem(body.problem_id)
        if not problem:
            raise HTTPException(404, "Unknown ai-assisted problem id")
    else:
        seen = await ai_assisted_bank.get_seen_ids(user["user_id"])
        problem = ai_assisted_bank.sample_one(exclude_ids=seen)
    await ai_assisted_bank.mark_seen(user["user_id"], [problem["id"]])

    session_id = new_id("aas")
    welcome = f"Let's talk through \"{problem['title']}\". " + _AI_ASSISTED_STAGE_OPENERS["understand"]
    session = {
        "session_id": session_id,
        "user_id": user["user_id"],
        "problem_id": problem["id"],
        "problem": _strip_ai_assisted_problem(problem),
        "current_stage": "understand",
        "transcript": [{"role": "ai", "stage": "understand", "text": welcome, "at": iso(now_utc())}],
        "stage_attempts": {"understand": 0, "approach": 0, "complexity": 0, "explain_bug": 0},
        "consent_given": None,
        "self_review_result": None,
        "bug_explanation_text": None,
        "bug_explanation_score": None,
        "revealed_code": None,
        "final_outcome": None,
        "status": "in_progress",
        "created_at": iso(now_utc()),
        "completed_at": None,
    }
    await db.ai_assisted_sessions.insert_one(session)
    session.pop("_id", None)
    return session


@api.get("/dev/ai-assisted/{session_id}")
async def dev_ai_assisted_get(session_id: str, user: Dict[str, Any] = Depends(require_user)):
    doc = await db.ai_assisted_sessions.find_one({"session_id": session_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Not found")
    return doc


class AiAssistedMessageIn(BaseModel):
    text: str


@api.post("/dev/ai-assisted/{session_id}/message")
async def dev_ai_assisted_message(session_id: str, body: AiAssistedMessageIn, user: Dict[str, Any] = Depends(require_user)):
    """Free-text stages only (understand/approach/complexity/explain_bug).
    The consent and self_review gates are button-driven -- see the two
    routes below, never this one."""
    session = await db.ai_assisted_sessions.find_one({"session_id": session_id, "user_id": user["user_id"]}, {"_id": 0})
    if not session:
        raise HTTPException(404, "Not found")
    stage = session["current_stage"]
    if stage not in _AI_ASSISTED_FREE_TEXT_STAGES:
        raise HTTPException(409, f"Current stage '{stage}' does not accept free-text messages")
    if session["status"] != "in_progress":
        raise HTTPException(409, "Session already completed")

    problem = ai_assisted_bank.get_problem(session["problem_id"])
    variant = problem["ai_assisted_variant"]
    transcript = session["transcript"]
    transcript.append({"role": "candidate", "stage": stage, "text": body.text, "at": iso(now_utc())})
    attempts = session["stage_attempts"]

    update: Dict[str, Any] = {}

    if stage == "explain_bug":
        # call_json_gpt (GPT_MINI = gpt-5.4-mini, temperature 0) -- Round 4's
        # staged-conversation grading.
        grade = await call_json_gpt(
            "You grade a candidate's bug-explanation for an AI-assisted coding "
            "assessment. Return only strict JSON.\n\n" + GRADING_INJECTION_DEFENSE,
            bug_explanation_grading_prompt(
                problem["title"], variant["bug_category"], variant["bug_explanation_key_points"], body.text,
            ),
            temperature=0,
        ) or {"sufficient": False, "reprompt": "Could you point to the specific line or condition that's wrong, and why?", "score": 0, "one_line_verdict": ""}
        grade = _attach_grading_flag(grade)
        sufficient = bool(grade.get("sufficient"))
        attempts["explain_bug"] = attempts.get("explain_bug", 0) + 1

        if sufficient:
            session["bug_explanation_text"] = body.text
            session["bug_explanation_score"] = grade.get("score", 0)
            session["current_stage"] = "complete"
            session["status"] = "completed"
            session["completed_at"] = iso(now_utc())
            session["revealed_code"] = {
                "label": "Reference Solution (Fixed)",
                "language": variant["display_language"],
                "code": variant["corrected_code"],
            }
            final_outcome = _score_ai_assisted_session(session)
            session["final_outcome"] = final_outcome
            transcript.append({"role": "ai", "stage": "explain_bug", "text": grade.get("one_line_verdict") or "Correct -- that's the actual bug.", "at": iso(now_utc())})
            transcript.append({"role": "ai", "stage": "complete", "text": ai_assisted_bank.FINAL_SUMMARY_TEMPLATE["heading"], "at": iso(now_utc())})
            update.update({
                "bug_explanation_text": session["bug_explanation_text"],
                "bug_explanation_score": session["bug_explanation_score"],
                "current_stage": "complete", "status": "completed", "completed_at": session["completed_at"],
                "revealed_code": session["revealed_code"], "final_outcome": final_outcome,
            })
        else:
            reprompt = grade.get("reprompt") or "Could you point to the specific line or condition that's wrong, and why?"
            transcript.append({"role": "ai", "stage": "explain_bug", "text": reprompt, "at": iso(now_utc())})
    else:
        stage_cfg = ai_assisted_bank.STAGE_CONFIG[stage]
        # Verdict comes from the element flags in _grade_stage_free_text, not from the model.
        grade = await _grade_stage_free_text(stage, stage_cfg, body.text)
        sufficient = grade["sufficient"]
        attempts[stage] = attempts.get(stage, 0) + 1

        if sufficient:
            next_stage = ai_assisted_bank.STAGE_ORDER[ai_assisted_bank.STAGE_ORDER.index(stage) + 1]
            session["current_stage"] = next_stage
            if next_stage == "consent":
                ai_msg = ai_assisted_bank.CONSENT_GATE["prompt_template"].format(
                    language=_ai_assisted_lang_display(variant["display_language"])
                )
            else:
                ai_msg = _AI_ASSISTED_STAGE_OPENERS[next_stage]
            transcript.append({"role": "ai", "stage": next_stage, "text": ai_msg, "at": iso(now_utc())})
            update["current_stage"] = next_stage
        else:
            reprompt = grade.get("reprompt") or (stage_cfg["reprompt_examples"] or ["Could you say a bit more?"])[0]
            transcript.append({"role": "ai", "stage": stage, "text": reprompt, "at": iso(now_utc())})

    update["transcript"] = transcript
    update["stage_attempts"] = attempts
    await db.ai_assisted_sessions.update_one({"session_id": session_id}, {"$set": update})
    session.update(update)
    return session


async def _grade_stage_free_text(stage: str, stage_cfg: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Round 4 free-text stage gate (understand / approach / complexity). The
    model marks each required element present or absent (temperature 0). The
    pass/fail verdict is computed here: the stage passes when the fraction of
    present elements is at least ai_assisted_bank.STAGE_SUFFICIENCY_THRESHOLD.
    A missing or malformed model reply counts every element as absent."""
    required = stage_cfg["required_elements"]
    examples = stage_cfg["reprompt_examples"]
    grade = await call_json_gpt(
        "You check a candidate's answer for an AI-assisted coding assessment. "
        "Return only strict JSON.\n\n" + GRADING_INJECTION_DEFENSE,
        stage_sufficiency_prompt(
            stage, stage_cfg["prompt_intro"], stage_cfg["sufficiency_rubric"],
            examples, text, required,
        ),
        temperature=0,
    ) or {}
    raw_elements = grade.get("elements") if isinstance(grade.get("elements"), dict) else {}
    flags = {key: raw_elements.get(key) is True for key in required}
    present = sum(flags.values())
    sufficient = bool(required) and present / len(required) >= ai_assisted_bank.STAGE_SUFFICIENCY_THRESHOLD
    reprompt = grade.get("reprompt") or (examples[0] if examples else "Could you say a bit more?")
    return {"sufficient": sufficient, "elements": flags, "reprompt": reprompt}


class AiAssistedButtonIn(BaseModel):
    value: bool


@api.post("/dev/ai-assisted/{session_id}/consent")
async def dev_ai_assisted_consent(session_id: str, body: AiAssistedButtonIn, user: Dict[str, Any] = Depends(require_user)):
    """Deterministic, button-driven -- NO LLM call. 'No' holds at the same
    gate and re-prompts patiently (no penalty, genuine candidate pacing
    control, per the confirmed evidence). 'Yes' reveals flawed_code into
    the editor and advances to self_review."""
    session = await db.ai_assisted_sessions.find_one({"session_id": session_id, "user_id": user["user_id"]}, {"_id": 0})
    if not session:
        raise HTTPException(404, "Not found")
    if session["current_stage"] != "consent":
        raise HTTPException(409, f"Current stage is '{session['current_stage']}', not 'consent'")
    if session["status"] != "in_progress":
        raise HTTPException(409, "Session already completed")

    transcript = session["transcript"]
    transcript.append({"role": "candidate", "stage": "consent", "text": "Yes" if body.value else "No", "at": iso(now_utc())})
    update: Dict[str, Any] = {}

    if not body.value:
        transcript.append({"role": "ai", "stage": "consent", "text": ai_assisted_bank.CONSENT_GATE["on_no"]["message"], "at": iso(now_utc())})
    else:
        problem = ai_assisted_bank.get_problem(session["problem_id"])
        variant = problem["ai_assisted_variant"]
        rng = ai_assisted_bank.bug_marker_line_range(variant["flawed_code"])
        session["consent_given"] = True
        session["current_stage"] = "self_review"
        session["revealed_code"] = {"label": "Generated Code", "language": variant["display_language"], "code": variant["flawed_code"]}
        review_msg = ai_assisted_bank.SELF_REVIEW["prompt_template"].format(start=rng["start"], end=rng["end"])
        transcript.append({"role": "ai", "stage": "self_review", "text": review_msg, "at": iso(now_utc())})
        update.update({"consent_given": True, "current_stage": "self_review", "revealed_code": session["revealed_code"]})

    update["transcript"] = transcript
    await db.ai_assisted_sessions.update_one({"session_id": session_id}, {"$set": update})
    session.update(update)
    return session


@api.post("/dev/ai-assisted/{session_id}/self_review")
async def dev_ai_assisted_self_review(session_id: str, body: AiAssistedButtonIn, user: Dict[str, Any] = Depends(require_user)):
    """Deterministic, button-driven -- NO LLM call. 'No' (correct: caught
    the flaw) advances to explain_bug. 'Yes' (accepted flawed code as
    correct) applies the UNCONFIRMED/assumed-default path documented in
    ai_assisted_bank.SELF_REVIEW["on_yes"] -- ends the round immediately,
    scores as a miss, still shows corrected_code as the reference summary."""
    session = await db.ai_assisted_sessions.find_one({"session_id": session_id, "user_id": user["user_id"]}, {"_id": 0})
    if not session:
        raise HTTPException(404, "Not found")
    if session["current_stage"] != "self_review":
        raise HTTPException(409, f"Current stage is '{session['current_stage']}', not 'self_review'")
    if session["status"] != "in_progress":
        raise HTTPException(409, "Session already completed")

    problem = ai_assisted_bank.get_problem(session["problem_id"])
    variant = problem["ai_assisted_variant"]
    transcript = session["transcript"]
    transcript.append({"role": "candidate", "stage": "self_review", "text": "Yes" if body.value else "No", "at": iso(now_utc())})
    update: Dict[str, Any] = {}

    if not body.value:
        session["self_review_result"] = "no"
        session["current_stage"] = "explain_bug"
        transcript.append({"role": "ai", "stage": "explain_bug", "text": ai_assisted_bank.SELF_REVIEW["on_no"]["message"], "at": iso(now_utc())})
        update.update({"self_review_result": "no", "current_stage": "explain_bug"})
    else:
        session["self_review_result"] = "yes"
        session["current_stage"] = "complete"
        session["status"] = "completed"
        session["completed_at"] = iso(now_utc())
        session["revealed_code"] = {"label": "Reference Solution (Fixed)", "language": variant["display_language"], "code": variant["corrected_code"]}
        final_outcome = _score_ai_assisted_session(session)
        session["final_outcome"] = final_outcome
        transcript.append({"role": "ai", "stage": "complete", "text": ai_assisted_bank.FINAL_SUMMARY_TEMPLATE["heading"], "at": iso(now_utc())})
        update.update({
            "self_review_result": "yes", "current_stage": "complete", "status": "completed",
            "completed_at": session["completed_at"], "revealed_code": session["revealed_code"],
            "final_outcome": final_outcome,
        })

    update["transcript"] = transcript
    await db.ai_assisted_sessions.update_one({"session_id": session_id}, {"$set": update})
    session.update(update)
    return session


# =============================================================================
#  Capgemini Round 4 (AI-Assisted Coding) -- LIVE, attempt-scoped routes.
#  Deliberately SEPARATE from the /dev/ai-assisted/* routes above (not
#  wrappers around them, no shared route-body code) -- same "dev route
#  stays untouched, real flow is its own code path" separation Round 3
#  used for /api/dev/debugging/run vs. the real coding/debugging
#  dispatch. Reuses only the shared, non-route-specific helpers those dev
#  routes ALSO happen to use (_score_ai_assisted_session, STAGE_CONFIG,
#  the prompt builders, etc.) -- never the dev routes' own function
#  bodies, so the dev-preview's behavior is unaffected by this section.
#
#  Looked up via {attempt_id, section_key, user_id} (ownership-checked
#  against the attempt first, then confirms the section is actually type
#  "ai_assisted") rather than a bare session_id the client would have to
#  separately track -- the frontend already knows attempt_id (from the
#  URL) and section_key (from currentSection.key), matching how /oa/run
#  is already scoped for the "coding" round above.
# =============================================================================

async def _load_ai_assisted_session_for_attempt(attempt_id: str, section_key: str, user_id: str) -> Dict[str, Any]:
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user_id}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Attempt not found")
    section = next((s for s in attempt["sections"] if s["key"] == section_key), None)
    if not section or section["type"] != "ai_assisted":
        raise HTTPException(404, "Not an AI-Assisted Coding section")
    session = await db.ai_assisted_sessions.find_one(
        {"attempt_id": attempt_id, "section_key": section_key, "user_id": user_id}, {"_id": 0},
    )
    if not session:
        raise HTTPException(404, "Session not found -- section may still be generating")
    return session


def _client_ai_assisted_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """The session as the candidate may see it. final_outcome keeps score, passed
    and reason, which the completion screen reads. Its per-component breakdown is
    left out. The stored session is not modified."""
    outcome = session.get("final_outcome")
    if not isinstance(outcome, dict) or "components" not in outcome:
        return session
    return {**session, "final_outcome": {k: v for k, v in outcome.items() if k != "components"}}


@api.get("/oa/{attempt_id}/ai-assisted/{section_key}")
async def oa_ai_assisted_get(attempt_id: str, section_key: str, user: Dict[str, Any] = Depends(require_user)):
    session = await _load_ai_assisted_session_for_attempt(attempt_id, section_key, user["user_id"])
    return _client_ai_assisted_session(session)


@api.post("/oa/{attempt_id}/ai-assisted/{section_key}/message")
async def oa_ai_assisted_message(attempt_id: str, section_key: str, body: AiAssistedMessageIn, user: Dict[str, Any] = Depends(require_user)):
    """Live-flow counterpart of dev_ai_assisted_message -- same logic,
    attempt+section_key scoped instead of bare session_id. Free-text
    stages only (understand/approach/complexity/explain_bug); consent and
    self_review are button-driven, see the two routes below."""
    session = await _load_ai_assisted_session_for_attempt(attempt_id, section_key, user["user_id"])
    session_id = session["session_id"]
    stage = session["current_stage"]
    if stage not in _AI_ASSISTED_FREE_TEXT_STAGES:
        raise HTTPException(409, f"Current stage '{stage}' does not accept free-text messages")
    if session["status"] != "in_progress":
        raise HTTPException(409, "Session already completed")

    problem = ai_assisted_bank.get_problem(session["problem_id"])
    variant = problem["ai_assisted_variant"]
    transcript = session["transcript"]
    transcript.append({"role": "candidate", "stage": stage, "text": body.text, "at": iso(now_utc())})
    attempts = session["stage_attempts"]

    update: Dict[str, Any] = {}

    if stage == "explain_bug":
        # call_json_gpt (GPT_MINI = gpt-5.4-mini, temperature 0) -- Round 4's
        # staged-conversation grading.
        grade = await call_json_gpt(
            "You grade a candidate's bug-explanation for an AI-assisted coding "
            "assessment. Return only strict JSON.\n\n" + GRADING_INJECTION_DEFENSE,
            bug_explanation_grading_prompt(
                problem["title"], variant["bug_category"], variant["bug_explanation_key_points"], body.text,
            ),
            temperature=0,
        ) or {"sufficient": False, "reprompt": "Could you point to the specific line or condition that's wrong, and why?", "score": 0, "one_line_verdict": ""}
        grade = _attach_grading_flag(grade)
        sufficient = bool(grade.get("sufficient"))
        attempts["explain_bug"] = attempts.get("explain_bug", 0) + 1

        if sufficient:
            session["bug_explanation_text"] = body.text
            session["bug_explanation_score"] = grade.get("score", 0)
            session["current_stage"] = "complete"
            session["status"] = "completed"
            session["completed_at"] = iso(now_utc())
            session["revealed_code"] = {
                "label": "Reference Solution (Fixed)",
                "language": variant["display_language"],
                "code": variant["corrected_code"],
            }
            final_outcome = _score_ai_assisted_session(session)
            session["final_outcome"] = final_outcome
            transcript.append({"role": "ai", "stage": "explain_bug", "text": grade.get("one_line_verdict") or "Correct -- that's the actual bug.", "at": iso(now_utc())})
            transcript.append({"role": "ai", "stage": "complete", "text": ai_assisted_bank.FINAL_SUMMARY_TEMPLATE["heading"], "at": iso(now_utc())})
            update.update({
                "bug_explanation_text": session["bug_explanation_text"],
                "bug_explanation_score": session["bug_explanation_score"],
                "current_stage": "complete", "status": "completed", "completed_at": session["completed_at"],
                "revealed_code": session["revealed_code"], "final_outcome": final_outcome,
            })
        else:
            reprompt = grade.get("reprompt") or "Could you point to the specific line or condition that's wrong, and why?"
            transcript.append({"role": "ai", "stage": "explain_bug", "text": reprompt, "at": iso(now_utc())})
    else:
        stage_cfg = ai_assisted_bank.STAGE_CONFIG[stage]
        # Verdict comes from the element flags in _grade_stage_free_text, not from the model.
        grade = await _grade_stage_free_text(stage, stage_cfg, body.text)
        sufficient = grade["sufficient"]
        attempts[stage] = attempts.get(stage, 0) + 1

        if sufficient:
            next_stage = ai_assisted_bank.STAGE_ORDER[ai_assisted_bank.STAGE_ORDER.index(stage) + 1]
            session["current_stage"] = next_stage
            if next_stage == "consent":
                ai_msg = ai_assisted_bank.CONSENT_GATE["prompt_template"].format(
                    language=_ai_assisted_lang_display(variant["display_language"])
                )
            else:
                ai_msg = _AI_ASSISTED_STAGE_OPENERS[next_stage]
            transcript.append({"role": "ai", "stage": next_stage, "text": ai_msg, "at": iso(now_utc())})
            update["current_stage"] = next_stage
        else:
            reprompt = grade.get("reprompt") or (stage_cfg["reprompt_examples"] or ["Could you say a bit more?"])[0]
            transcript.append({"role": "ai", "stage": stage, "text": reprompt, "at": iso(now_utc())})

    update["transcript"] = transcript
    update["stage_attempts"] = attempts
    await db.ai_assisted_sessions.update_one({"session_id": session_id}, {"$set": update})
    session.update(update)
    return session


@api.post("/oa/{attempt_id}/ai-assisted/{section_key}/consent")
async def oa_ai_assisted_consent(attempt_id: str, section_key: str, body: AiAssistedButtonIn, user: Dict[str, Any] = Depends(require_user)):
    """Live-flow counterpart of dev_ai_assisted_consent -- deterministic,
    button-driven, NO LLM call. Same logic, attempt+section_key scoped."""
    session = await _load_ai_assisted_session_for_attempt(attempt_id, section_key, user["user_id"])
    session_id = session["session_id"]
    if session["current_stage"] != "consent":
        raise HTTPException(409, f"Current stage is '{session['current_stage']}', not 'consent'")
    if session["status"] != "in_progress":
        raise HTTPException(409, "Session already completed")

    transcript = session["transcript"]
    transcript.append({"role": "candidate", "stage": "consent", "text": "Yes" if body.value else "No", "at": iso(now_utc())})
    update: Dict[str, Any] = {}

    if not body.value:
        transcript.append({"role": "ai", "stage": "consent", "text": ai_assisted_bank.CONSENT_GATE["on_no"]["message"], "at": iso(now_utc())})
    else:
        problem = ai_assisted_bank.get_problem(session["problem_id"])
        variant = problem["ai_assisted_variant"]
        rng = ai_assisted_bank.bug_marker_line_range(variant["flawed_code"])
        session["consent_given"] = True
        session["current_stage"] = "self_review"
        session["revealed_code"] = {"label": "Generated Code", "language": variant["display_language"], "code": variant["flawed_code"]}
        review_msg = ai_assisted_bank.SELF_REVIEW["prompt_template"].format(start=rng["start"], end=rng["end"])
        transcript.append({"role": "ai", "stage": "self_review", "text": review_msg, "at": iso(now_utc())})
        update.update({"consent_given": True, "current_stage": "self_review", "revealed_code": session["revealed_code"]})

    update["transcript"] = transcript
    await db.ai_assisted_sessions.update_one({"session_id": session_id}, {"$set": update})
    session.update(update)
    return session


@api.post("/oa/{attempt_id}/ai-assisted/{section_key}/self_review")
async def oa_ai_assisted_self_review(attempt_id: str, section_key: str, body: AiAssistedButtonIn, user: Dict[str, Any] = Depends(require_user)):
    """Live-flow counterpart of dev_ai_assisted_self_review -- deterministic,
    button-driven, NO LLM call. Same logic, attempt+section_key scoped.
    'Yes' (accepts flawed code) applies the UNCONFIRMED/assumed-default
    path documented in ai_assisted_bank.SELF_REVIEW["on_yes"]."""
    session = await _load_ai_assisted_session_for_attempt(attempt_id, section_key, user["user_id"])
    session_id = session["session_id"]
    if session["current_stage"] != "self_review":
        raise HTTPException(409, f"Current stage is '{session['current_stage']}', not 'self_review'")
    if session["status"] != "in_progress":
        raise HTTPException(409, "Session already completed")

    problem = ai_assisted_bank.get_problem(session["problem_id"])
    variant = problem["ai_assisted_variant"]
    transcript = session["transcript"]
    transcript.append({"role": "candidate", "stage": "self_review", "text": "Yes" if body.value else "No", "at": iso(now_utc())})
    update: Dict[str, Any] = {}

    if not body.value:
        session["self_review_result"] = "no"
        session["current_stage"] = "explain_bug"
        transcript.append({"role": "ai", "stage": "explain_bug", "text": ai_assisted_bank.SELF_REVIEW["on_no"]["message"], "at": iso(now_utc())})
        update.update({"self_review_result": "no", "current_stage": "explain_bug"})
    else:
        session["self_review_result"] = "yes"
        session["current_stage"] = "complete"
        session["status"] = "completed"
        session["completed_at"] = iso(now_utc())
        session["revealed_code"] = {"label": "Reference Solution (Fixed)", "language": variant["display_language"], "code": variant["corrected_code"]}
        final_outcome = _score_ai_assisted_session(session)
        session["final_outcome"] = final_outcome
        transcript.append({"role": "ai", "stage": "complete", "text": ai_assisted_bank.FINAL_SUMMARY_TEMPLATE["heading"], "at": iso(now_utc())})
        update.update({
            "self_review_result": "yes", "current_stage": "complete", "status": "completed",
            "completed_at": session["completed_at"], "revealed_code": session["revealed_code"],
            "final_outcome": final_outcome,
        })

    update["transcript"] = transcript
    await db.ai_assisted_sessions.update_one({"session_id": session_id}, {"$set": update})
    session.update(update)
    return session


# =============================================================================
#  Final cross-phase report
# =============================================================================

@api.get("/report/{attempt_id}")
async def final_report(attempt_id: str, user: Dict[str, Any] = Depends(require_user)):
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Attempt not found")

    resume_analysis = {}
    if attempt.get("resume_id"):
        r = await db.resumes.find_one({"resume_id": attempt["resume_id"]}, {"_id": 0})
        if r:
            resume_analysis = r.get("analysis", {})

    review = await oa_review(attempt_id, user)  # reuse
    oa_summary = {
        "verdict": review["verdict"],
        "composite_score": review["composite_score"],
        "weakest_section": review["weakest_section"],
        "section_results": {k: {"score": v.get("score"), "passed": v.get("passed")} for k, v in review["section_results"].items()},
    }

    interview_doc = await db.interviews.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    interview_summary = {"skipped": True}
    if interview_doc:
        answered = interview_doc.get("answers", [])
        scores = [a["grade"].get("score", 0) for a in answered]
        interview_summary = {
            "skipped": False,
            "avg_score": round(sum(scores) / max(1, len(scores)), 1) if scores else 0,
            "verdicts": [a["grade"].get("one_line_verdict", "") for a in answered],
            "completed": interview_doc.get("status") == "completed",
        }

    cached = await db.reports.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if cached:
        return cached

    report = await call_json(
        "You are a senior career coach. Write ONE cohesive report. Return only strict JSON.",
        final_report_prompt(attempt["company_name"], resume_analysis, oa_summary, interview_summary),
        model=SONNET,
        max_tokens=8000,  # longest, most synthesis-heavy output in the app; extra
                          # headroom above the 4096 default costs nothing if unused
    ) or {
        "overall_verdict": oa_summary["verdict"],
        "overall_score": int(oa_summary["composite_score"] * 100),
        "narrative": "Report generation failed; showing raw OA verdict.",
        "weakest_dimension": review["weakest_section"] or "",
        "strongest_dimension": "",
        "next_steps": [],
    }

    doc = {
        "report_id": new_id("rep"),
        "attempt_id": attempt_id,
        "user_id": user["user_id"],
        "company_name": attempt["company_name"],
        "resume_analysis": resume_analysis,
        "oa_summary": oa_summary,
        "interview_summary": interview_summary,
        "report": report,
        "created_at": iso(now_utc()),
    }
    await db.reports.insert_one(doc)
    doc.pop("_id", None)
    return doc


# =============================================================================
#  Dashboard
# =============================================================================

@api.get("/dashboard")
async def dashboard(user: Dict[str, Any] = Depends(require_user)):
    attempts = await db.oa_attempts.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    resumes = await db.resumes.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    # Compact attempts view for the dashboard
    compact = [{
        "attempt_id": a["attempt_id"],
        "company_id": a["company_id"],
        "company_name": a["company_name"],
        "status": a.get("status"),
        "created_at": a.get("created_at"),
        "sections_done": len(a.get("section_results", {})),
        "sections_total": len(a.get("sections", [])),
    } for a in attempts]
    return {
        "user": user,
        "attempts": compact,
        "resumes": [{"resume_id": r["resume_id"], "company_id": r["company_id"], "role": r.get("role"), "fit_score": r["analysis"].get("fit_score"), "created_at": r.get("created_at")} for r in resumes],
    }


# =============================================================================
#  Pricing / Razorpay
# =============================================================================

PLANS = entitlements.PLANS_CATALOG
CREDIT_PACKS = entitlements.CREDIT_PACKS


@api.get("/pricing")
async def pricing():
    return {
        "plans": PLANS,
        "credit_packs": CREDIT_PACKS,
        "contest_end": entitlements.CONTEST_END.isoformat(),
        "razorpay_enabled": _razorpay_client is not None,
        "razorpay_key_id": RAZORPAY_KEY_ID if _razorpay_client else None,
    }


class CreateOrderIn(BaseModel):
    plan_id: Optional[str] = None
    credit_pack_id: Optional[str] = None


def _find_plan_or_pack(plan_id: Optional[str], pack_id: Optional[str]) -> Tuple[Optional[dict], Optional[dict]]:
    if plan_id:
        return next((p for p in PLANS if p["id"] == plan_id), None), None
    if pack_id:
        return None, next((c for c in CREDIT_PACKS if c["id"] == pack_id), None)
    return None, None


@api.post("/payments/order")
async def create_order(body: CreateOrderIn, user: Dict[str, Any] = Depends(require_user)):
    if is_bypass_email(user.get("email", "")):
        raise HTTPException(400, "Your account already has unlimited access. No payment required.")
    plan, pack = _find_plan_or_pack(body.plan_id, body.credit_pack_id)
    if plan is None and pack is None:
        raise HTTPException(400, "Provide either plan_id or credit_pack_id")
    if plan and plan["price"] <= 0:
        raise HTTPException(400, "Invalid plan")

    amount_paise = (plan["price"] if plan else pack["price"]) * 100
    order_id = new_id("order")

    if _razorpay_client:
        try:
            razor_order = _razorpay_client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": order_id[:40],
                "payment_capture": 1,
                "notes": {
                    "plan_id": plan["id"] if plan else "",
                    "credit_pack_id": pack["id"] if pack else "",
                    "user_id": user["user_id"],
                },
            })
        except Exception as e:
            raise HTTPException(500, f"Razorpay error: {e}")
        rzp_id = razor_order["id"]
    else:
        rzp_id = f"order_mock_{uuid.uuid4().hex[:10]}"

    doc = {
        "order_id": order_id,
        "razorpay_order_id": rzp_id,
        "kind": "plan" if plan else "credits",
        "plan_id": plan["id"] if plan else None,
        "credit_pack_id": pack["id"] if pack else None,
        "user_id": user["user_id"],
        "amount": amount_paise,
        "currency": "INR",
        "status": "created",
        "mock": _razorpay_client is None,
        "created_at": iso(now_utc()),
    }
    await db.orders.insert_one(doc)
    doc.pop("_id", None)
    return {
        "order": doc,
        "razorpay_key_id": RAZORPAY_KEY_ID if _razorpay_client else None,
        "mock": _razorpay_client is None,
    }


class VerifyPaymentIn(BaseModel):
    order_id: str
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None


@api.post("/payments/verify")
async def verify_payment(body: VerifyPaymentIn, user: Dict[str, Any] = Depends(require_user)):
    order = await db.orders.find_one({"order_id": body.order_id, "user_id": user["user_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")

    verified = False
    if _razorpay_client and body.razorpay_order_id and body.razorpay_payment_id and body.razorpay_signature:
        try:
            _razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": body.razorpay_order_id,
                "razorpay_payment_id": body.razorpay_payment_id,
                "razorpay_signature": body.razorpay_signature,
            })
            verified = True
        except Exception as e:
            logger.warning("Signature verify failed: %s", e)
            verified = False
    else:
        # Mock mode: accept as paid.
        verified = True

    if not verified:
        raise HTTPException(400, "Signature verification failed")

    # Route by order kind ------------------------------------------------------
    kind = order.get("kind") or ("plan" if order.get("plan_id") else "credits")
    if kind == "plan":
        plan = next((p for p in PLANS if p["id"] == order["plan_id"]), None)
        if plan:
            limits = entitlements.PLAN_LIMITS.get(plan["id"], {})
            days = limits.get("validity_days")
            expires_at = (entitlements._now() + timedelta(days=days)).isoformat() if days else None
            # Reset runs_used=0 and roll a fresh period window on plan purchase.
            update_set: Dict[str, Any] = {
                "plan": plan["id"],
                "runs_used": 0,
                "plan_started_at": iso(now_utc()),
                "runs_period_start": iso(now_utc()),
            }
            if expires_at:
                update_set["plan_expires_at"] = expires_at
            else:
                update_set["plan_expires_at"] = None
            await db.users.update_one({"user_id": user["user_id"]}, {"$set": update_set})
    elif kind == "credits":
        pack = next((c for c in CREDIT_PACKS if c["id"] == order.get("credit_pack_id")), None)
        if pack:
            await db.users.update_one(
                {"user_id": user["user_id"]},
                {"$inc": {"credits": int(pack["credits"])}},
            )

    await db.orders.update_one(
        {"order_id": order["order_id"]},
        {"$set": {"status": "paid", "razorpay_payment_id": body.razorpay_payment_id, "paid_at": iso(now_utc())}},
    )
    return {"ok": True, "mock": order.get("mock", False), "kind": kind}


# ---- Root & health ----------------------------------------------------------

@api.get("/")
async def root():
    return {"service": "placemint", "ok": True}


@api.get("/admin/mcq-stats")
async def admin_mcq_stats(user: Dict[str, Any] = Depends(require_user)):
    """Founder-only readout of MCQ pool health + verifier disagreement rates."""
    email = (user.get("email") or "").lower()
    if email not in PAYMENT_BYPASS_EMAILS:
        raise HTTPException(403, "Founder-only")
    return await mcq_pool.pool_stats()


app.include_router(api)


_MCQ_POOL_WORKER_OFF_VALUES = {"0", "false", "no", "off"}


def mcq_pool_worker_enabled(env_value: Optional[str] = None) -> bool:
    """MCQ_POOL_WORKER_ENABLED: unset or any value other than 0/false/no/off keeps the worker on."""
    raw = os.environ.get("MCQ_POOL_WORKER_ENABLED") if env_value is None else env_value
    if raw is None:
        return True
    return raw.strip().lower() not in _MCQ_POOL_WORKER_OFF_VALUES


@app.on_event("startup")
async def _startup():
    # Wire mcq_pool with our db handle and kick off the singleton background
    # worker that keeps the pre-verified MCQ pool topped up.
    mcq_pool.init(db)
    mcq_static_bank.init(db)
    gamified_round.init(db)
    problem_bank.init(db)
    debugging_bank.init(db)
    ai_assisted_bank.init(db)
    capgemini_recruitment_process.init(db)
    try:
        await db.mcq_pool.create_index([("company_name", 1), ("section_key", 1), ("verified", 1)])
        await db.mcq_pool_stats.create_index([("company_name", 1), ("section_key", 1)], unique=True)
        await db.review_deck.create_index([("user_id", 1), ("added_at", -1)])
        await db.review_deck.create_index([("user_id", 1), ("source_attempt_id", 1), ("section_key", 1), ("question_id", 1)], unique=True)
        await db.mcq_static_bank.create_index([("topic", 1), ("question_id", 1)], unique=True)
        await db.mcq_static_bank_seen.create_index([("user_id", 1), ("topic", 1)], unique=True)
        await db.gamified_round_config.create_index([("company", 1)], unique=True)
        await db.puzzle_bank.create_index([("gameType", 1), ("puzzle_id", 1)], unique=True)
        await db.puzzle_bank.create_index([("gameType", 1), ("companyTags", 1)])
        await db.game_session.create_index([("session_id", 1)], unique=True)
        await db.game_session.create_index([("user_id", 1), ("gameType", 1)])
    except Exception as e:  # pragma: no cover
        logger.warning("mcq_pool index create failed: %s", e)
    # The pool worker pre-generates MCQs with the LLM. It is on by default
    # (existing behaviour). Set MCQ_POOL_WORKER_ENABLED=0 (or false/no/off) to disable it.
    if mcq_pool_worker_enabled():
        mcq_pool.start_worker(COMPANIES)
    else:
        logger.info("mcq_pool background worker disabled (MCQ_POOL_WORKER_ENABLED is off)")


@app.on_event("shutdown")
async def _shutdown():
    mcq_pool.stop_worker()
    client.close()
