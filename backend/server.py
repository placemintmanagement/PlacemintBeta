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
from typing import Any, Dict, List, Optional, Tuple

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
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, Field
import pdfplumber

from companies import COMPANIES, get_company
from code_runner import run_code as _lang_run_code, run_tests as _lang_run_tests, SUPPORTED_LANGUAGES
from problem_bank import sample_problems as _sample_problems
from ai_service import (
    call_json,
    call_json_gpt,
    call_text,
    SONNET,
    resume_prompt,
    mcq_prompt,
    coding_prompt,
    pseudocode_prompt,
    comm_prompt,
    grammar_prompt,
    comprehension_prompt,
    cognitive_game_prompt,
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
)
import mcq_pool
import mcq_static_bank
import capgemini_challenges
import cognizant_games
import accenture_games
import challenge_repetition
import entitlements

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


def decode_jwt(token: str) -> Optional[str]:
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return data.get("sub")
    except Exception:
        return None


# ---- Auth dependency --------------------------------------------------------

async def get_current_user(
    session_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
) -> Optional[Dict[str, Any]]:
    """Returns the current user document (with _id excluded) or None."""
    token: Optional[str] = None
    if session_token:
        token = session_token
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None

    # 1) Emergent OAuth session token \u2192 stored in user_sessions
    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if sess:
        expires_at = sess.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < now_utc():
                return None
        user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0, "password_hash": 0})
        return user

    # 2) JWT (email/password login)
    user_id = decode_jwt(token)
    if user_id:
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
        return user
    return None


async def require_user(user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Dict[str, Any]:
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


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
) -> Dict[str, Any]:
    existing = await db.users.find_one({"email": email}, {"_id": 0})
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

    system = "You are a senior tech recruiter. Return only strict JSON."
    prompt = resume_prompt(company["name"], role, resume_text)
    result = await call_json(system, prompt, model=SONNET)
    if not isinstance(result, dict):
        result = {"strengths": [], "weaknesses": [], "extracted_projects": [], "fit_score": 50, "verdict": "Analysis unavailable."}

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


async def _generate_extra_topics(company_name: str, extra_topics: List[dict], diff: Optional[str], user_id: str) -> List[dict]:
    """Shared per-topic pool-or-live-verify loop — pulled out of the
    pseudocode branch's extra_topics handling (Capgemini's OOPS/DBMS/OS/CN
    fix) so a plain topic-only MCQ section (e.g. LTIMindtree's Computer
    Science: DBMS/OOPS/OS, no pseudocode content at all) can reuse the exact
    same mechanism without going through the pseudocode stype.

    90/10 static-bank/live split for the 8 canonical topics (mcq_static_bank.py,
    changed 2026-07-21 from the original 50/50): each topic pulls ceil(tcount*0.9)
    from the static bank (excluding this candidate's already-seen questions) and
    backfills the rest — including any static shortfall — from the existing
    pool-or-live-verify path, shuffled together before being tagged and returned."""
    data: List[dict] = []
    for t in extra_topics:
        tkey = t.get("key")
        tname = t.get("name", tkey)
        tcount = t.get("count", 5)
        if not tkey:
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


async def _generate_section_questions(company_name: str, section: dict, user_id: str, attempt_id: str) -> List[dict]:
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
        if difficulty_targets:
            # Per-problem difficulty (e.g. Wipro: Problem 1 easy-medium,
            # Problem 2 hard) — sample each individually rather than one
            # blended difficulty_target across the whole count, excluding
            # already-picked ids so an overlapping tier (Medium appears in
            # both easy_medium and hard's top-up) can't draw the same
            # problem twice across separate calls.
            picks = []
            excluded: set = set()
            for t in difficulty_targets:
                got = _sample_problems(1, difficulty_target=t, needs_buggy=needs_buggy, exclude_ids=excluded)
                picks.extend(got)
                excluded.update(p.get("id") for p in got if p.get("id"))
            if len(picks) < count:
                extra = _sample_problems(count - len(picks), difficulty_target=diff, needs_buggy=needs_buggy, exclude_ids=excluded)
                picks.extend(extra)
        else:
            picks = _sample_problems(count, difficulty_target=diff, needs_buggy=needs_buggy)
        # Normalize ids to strings (bank ids are already strings but be safe)
        for i, p in enumerate(picks):
            p.setdefault("id", f"q{i+1}")
            p["id"] = str(p["id"])
        return picks
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
        data = await mcq_pool.fallback_live_verify(
            company_name, section_name, section.get("key") or "pseudocode", pseudo_count, diff,
        )
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
    elif stype in ("cognitive_game", "game"):
        # "game" (IBM) gets the exact same treatment as Accenture's
        # cognitive_game: the real per-question-timer UI needs style-tagged,
        # tightly length-limited stems, which only cognitive_game_prompt
        # produces — game_prompt's plain MCQ shape can't back that UI.
        # (Capgemini used to share this branch too, before it got its own
        # capgemini_challenges type below.)
        data = await call_json(system, cognitive_game_prompt(company_name, count))
    elif stype == "capgemini_challenges":
        # Capgemini's own distinct round — fully procedural, zero AI (see
        # capgemini_challenges.py docstring for why). Non-repetition is
        # tracked per candidate/category since procedural generation lets us
        # actually GUARANTEE a fresh variant, unlike LLM content.
        #
        # Mid-rebuild: items come back in one of two shapes (see
        # capgemini_challenges.py's module docstring). Old-shape items mark
        # one hash under the item's own `style`. New-shape (rebuilt) items
        # carry a `sub_puzzles` list — each sub-puzzle gets its own
        # repetition hash (tracked at sub-puzzle granularity, not just
        # challenge-type granularity, per the rebuild's non-repetition
        # requirement) AND, where a secret exists (e.g. Grid Challenge's
        # correct value), gets it persisted via _store_hidden_answer_key
        # under a composite id ("<challenge_id>_<sub_index>") — never
        # included in the public payload served to the frontend.
        section_key = section.get("key") or "cognitive"
        seen = await challenge_repetition.get_seen_hashes(user_id, section_key)
        data = capgemini_challenges.generate_capgemini_challenges(count, seen)
        for item in data:
            if "sub_puzzles" in item:
                secrets = item.pop("_secrets", [])
                hashes = item.pop("_content_hashes", [])
                for i, h in enumerate(hashes):
                    if h:
                        await challenge_repetition.mark_seen(user_id, section_key, item["type"], h)
                    secret = secrets[i] if i < len(secrets) else None
                    if secret is not None:
                        sub_qid = f"{item['id']}_{i}"
                        await _store_hidden_answer_key(attempt_id, section_key, sub_qid, secret)
            else:
                h = item.pop("_content_hash", None)
                if h:
                    await challenge_repetition.mark_seen(user_id, section_key, item["style"], h)
    elif stype == "cognizant_games":
        # Cognizant's gamified round — bespoke design, fully procedural, zero
        # AI, built to the same sub-puzzle-set + hidden-secret standard as
        # capgemini_challenges.py (see cognizant_games.py's module docstring).
        # Every item is new-shape (sub_puzzles) — no old-shape branching
        # needed here, unlike Capgemini's mid-rebuild dual-shape handling.
        section_key = section.get("key") or "gamified"
        seen = await challenge_repetition.get_seen_hashes(user_id, section_key)
        data = cognizant_games.generate_cognizant_games(seen)
        for item in data:
            secrets = item.pop("_secrets", [])
            hashes = item.pop("_content_hashes", [])
            for i, h in enumerate(hashes):
                if h:
                    await challenge_repetition.mark_seen(user_id, section_key, item["type"], h)
                secret = secrets[i] if i < len(secrets) else None
                if secret is not None:
                    sub_qid = f"{item['id']}_{i}"
                    await _store_hidden_answer_key(attempt_id, section_key, sub_qid, secret)
    elif stype == "accenture_games":
        # Accenture's gamified round — same bespoke sub-puzzle-set + hidden-
        # secret architecture as cognizant_games, scoped to 3 always-shown
        # categories (see accenture_games.py's module docstring).
        section_key = section.get("key") or "cognitive"
        seen = await challenge_repetition.get_seen_hashes(user_id, section_key)
        data = accenture_games.generate_accenture_games(seen)
        for item in data:
            secrets = item.pop("_secrets", [])
            hashes = item.pop("_content_hashes", [])
            for i, h in enumerate(hashes):
                if h:
                    await challenge_repetition.mark_seen(user_id, section_key, item["type"], h)
                secret = secrets[i] if i < len(secrets) else None
                if secret is not None:
                    sub_qid = f"{item['id']}_{i}"
                    await _store_hidden_answer_key(attempt_id, section_key, sub_qid, secret)
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


async def _gen_and_persist_section(attempt_id: str, company_name: str, index: int, section: dict, user_id: str):
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
            questions = await _generate_section_questions(company_name, section, user_id, attempt_id)
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
            *[_gen_and_persist_section(attempt_id, company["name"], i, s, user_id)
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
    return doc


class SubmitSectionIn(BaseModel):
    section_key: str
    answers: Dict[str, Any]  # {question_id: answer}


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


def _grade_capgemini_challenges_section(section: dict, answers: Dict[str, Any], attempt: dict) -> dict:
    """Capgemini's cognitive round mixes old-shape items (not yet rebuilt:
    inductive/switch/motion/digit — single question, graded like _grade_mcq_like)
    with new-shape items (rebuilt: deductive/grid — a set of sub-puzzles, each
    graded by its own type-specific function in capgemini_challenges.py).
    Score is per-CHALLENGE (e.g. "4 of 5 sub-puzzles solved" collapses to one
    0.0-1.0 score for that challenge), matching the design's "rolls up into
    the section's existing weight" requirement — a 5-sub-puzzle challenge
    counts the same as a 1-question challenge, not 5x as much.
    """
    section_key = section.get("key") or "cognitive"
    items = section.get("questions", [])
    total = len(items)
    per_item = []
    total_score = 0.0
    for item in items:
        qid = str(item.get("id"))
        if "sub_puzzles" in item:
            sub_puzzles = item["sub_puzzles"]
            n = len(sub_puzzles) or 1
            grader = capgemini_challenges.SUBPUZZLE_GRADERS.get(item.get("type"))
            correct = 0
            for i, pub in enumerate(sub_puzzles):
                if grader is None:
                    continue
                sub_qid = f"{qid}_{i}"
                sub_answer = answers.get(sub_qid)
                secret = _get_hidden_answer_key(attempt, section_key, sub_qid)
                if grader(pub, secret, sub_answer) >= 1.0:
                    correct += 1
            item_score = correct / n
            per_item.append({
                "question_id": qid, "type": item.get("type"),
                "sub_puzzles_correct": correct, "sub_puzzles_total": n,
                "score": round(item_score, 3),
            })
        else:
            correct_index = item.get("correct_index")
            raw_user = answers.get(qid)
            try:
                user_index = int(raw_user) if raw_user is not None and raw_user != "" else None
            except Exception:
                user_index = None
            item_score = 1.0 if (user_index is not None and user_index == correct_index) else 0.0
            per_item.append({"question_id": qid, "type": item.get("style"), "score": item_score})
        total_score += item_score
    score = (total_score / total) if total else 0
    passed = score >= section.get("cutoff", 0.5)
    return {"score": round(score, 3), "items": per_item, "total": total, "passed": passed}


def _grade_cognizant_games_section(section: dict, answers: Dict[str, Any], attempt: dict) -> dict:
    """Mirrors _grade_capgemini_challenges_section exactly (same sub-puzzle-set
    architecture): every item carries `sub_puzzles`, each graded by its own
    type-specific function in cognizant_games.py, reading the hidden secret
    (if any) back via _get_hidden_answer_key. Score is per-CHALLENGE (fraction
    of its sub-puzzles solved), not per-sub-puzzle, so a 4-sub-puzzle
    challenge counts the same as any other single item in the section."""
    section_key = section.get("key") or "gamified"
    items = section.get("questions", [])
    total = len(items)
    per_item = []
    total_score = 0.0
    for item in items:
        qid = str(item.get("id"))
        sub_puzzles = item.get("sub_puzzles", [])
        n = len(sub_puzzles) or 1
        grader = cognizant_games.SUBPUZZLE_GRADERS.get(item.get("type"))
        correct = 0
        for i, pub in enumerate(sub_puzzles):
            if grader is None:
                continue
            sub_qid = f"{qid}_{i}"
            sub_answer = answers.get(sub_qid)
            secret = _get_hidden_answer_key(attempt, section_key, sub_qid)
            if grader(pub, secret, sub_answer) >= 1.0:
                correct += 1
        item_score = correct / n
        per_item.append({
            "question_id": qid, "type": item.get("type"),
            "sub_puzzles_correct": correct, "sub_puzzles_total": n,
            "score": round(item_score, 3),
        })
        total_score += item_score
    score = (total_score / total) if total else 0
    passed = score >= section.get("cutoff", 0.5)
    return {"score": round(score, 3), "items": per_item, "total": total, "passed": passed}


def _grade_accenture_games_section(section: dict, answers: Dict[str, Any], attempt: dict) -> dict:
    """Mirrors _grade_cognizant_games_section exactly (same sub-puzzle-set
    architecture, scoped to accenture_games.py's 3 categories)."""
    section_key = section.get("key") or "cognitive"
    items = section.get("questions", [])
    total = len(items)
    per_item = []
    total_score = 0.0
    for item in items:
        qid = str(item.get("id"))
        sub_puzzles = item.get("sub_puzzles", [])
        n = len(sub_puzzles) or 1
        grader = accenture_games.SUBPUZZLE_GRADERS.get(item.get("type"))
        correct = 0
        for i, pub in enumerate(sub_puzzles):
            if grader is None:
                continue
            sub_qid = f"{qid}_{i}"
            sub_answer = answers.get(sub_qid)
            secret = _get_hidden_answer_key(attempt, section_key, sub_qid)
            if grader(pub, secret, sub_answer) >= 1.0:
                correct += 1
        item_score = correct / n
        per_item.append({
            "question_id": qid, "type": item.get("type"),
            "sub_puzzles_correct": correct, "sub_puzzles_total": n,
            "score": round(item_score, 3),
        })
        total_score += item_score
    score = (total_score / total) if total else 0
    passed = score >= section.get("cutoff", 0.5)
    return {"score": round(score, 3), "items": per_item, "total": total, "passed": passed}


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
            "You are a coding interviewer. Return only strict JSON.",
            grade_coding_prompt(p, code, language, vpass, vtotal, hpass, htotal),
        ) or {"score": int(pct * 100), "complexity_note": "", "correctness_note": "", "style_note": ""}
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
            "You are a strict essay evaluator. Return only strict JSON.",
            grade_essay_prompt(topic, answer_text, min_w, max_w),
        ) or {"score": 0, "strengths": [], "weaknesses": [], "rewrite_suggestion": ""}
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
            "You are a fair, encouraging spoken-English evaluator. Return only strict JSON.",
            grade_spoken_response_prompt(topic, transcript, min_w, max_w),
        ) or {"score": 0, "strengths": [], "weaknesses": [], "rewrite_suggestion": ""}
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
                "You are a fair, encouraging spoken-English evaluator. Return only strict JSON.",
                grade_spoken_response_prompt(topic, transcript, min_w, max_w),
            ) or {"score": 0}
            item_score = (result.get("score", 0) or 0) / 100.0
            per_item.append({"question_id": qid, "mode": mode, "score": round(item_score, 3)})
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
                "You are a fair, encouraging spoken-English evaluator. Return only strict JSON.",
                grade_spoken_response_prompt(topic, transcript, min_w, max_w),
            ) or {"score": 0}
            item_score = (result.get("score", 0) or 0) / 100.0
        else:
            reference = q.get("text", "") or ""
            transcript = answers.get(qid, "") or ""
            item_score = difflib.SequenceMatcher(
                None, _normalize_for_similarity(reference), _normalize_for_similarity(transcript),
            ).ratio()
        per_item.append({"question_id": qid, "mode": mode, "score": round(item_score, 3)})
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
    elif stype == "cognizant_games":
        result = _grade_cognizant_games_section(section, body.answers, attempt)
    elif stype == "accenture_games":
        result = _grade_accenture_games_section(section, body.answers, attempt)
    elif stype == "capgemini_challenges":
        result = _grade_capgemini_challenges_section(section, body.answers, attempt)
    else:  # mcq / topic_mcq / pseudocode / comm / game / cognitive_game / grammar / comprehension
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
    await db.oa_attempts.update_one(
        {"attempt_id": attempt_id},
        {"$set": {
            "section_results": section_results,
            "answers": answers,
            "current_section_index": current_idx,
            "status": status,
            "completed_at": iso(now_utc()) if status == "completed" else None,
        }},
    )
    return {"section_result": result, "next_index": current_idx, "status": status}


@api.get("/oa/{attempt_id}/review")
async def oa_review(attempt_id: str, user: Dict[str, Any] = Depends(require_user)):
    attempt = await db.oa_attempts.find_one({"attempt_id": attempt_id, "user_id": user["user_id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(404, "Not found")

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
        "attempt_id": attempt_id,
        "company_name": attempt["company_name"],
        "scoring_mode": scoring_mode,
        "section_results": section_results,
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
        "You grade interview answers as an experienced engineer. Return only strict JSON.",
        grade_answer_prompt(question, body.answer),
    ) or {"score": 0, "signals_hit": [], "missed": [], "follow_up": None, "one_line_verdict": ""}

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


@app.on_event("startup")
async def _startup():
    # Wire mcq_pool with our db handle and kick off the singleton background
    # worker that keeps the pre-verified MCQ pool topped up.
    mcq_pool.init(db)
    challenge_repetition.init(db)
    mcq_static_bank.init(db)
    try:
        await db.mcq_pool.create_index([("company_name", 1), ("section_key", 1), ("verified", 1)])
        await db.mcq_pool_stats.create_index([("company_name", 1), ("section_key", 1)], unique=True)
        await db.review_deck.create_index([("user_id", 1), ("added_at", -1)])
        await db.review_deck.create_index([("user_id", 1), ("source_attempt_id", 1), ("section_key", 1), ("question_id", 1)], unique=True)
        await db.seen_challenges.create_index(
            [("user_id", 1), ("section_key", 1), ("category", 1), ("content_hash", 1)], unique=True,
        )
        await db.mcq_static_bank.create_index([("topic", 1), ("question_id", 1)], unique=True)
        await db.mcq_static_bank_seen.create_index([("user_id", 1), ("topic", 1)], unique=True)
    except Exception as e:  # pragma: no cover
        logger.warning("mcq_pool index create failed: %s", e)
    mcq_pool.start_worker(COMPANIES)


@app.on_event("shutdown")
async def _shutdown():
    mcq_pool.stop_worker()
    client.close()
