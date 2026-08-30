"""Entitlements — the single source of truth for plan caps, credit balance,
and company-selection enforcement.

Terminology:
  - "plan run" = a run that consumes the plan's monthly / total quota.
  - "credit" = a permanent 1-run token purchased separately; never expires.
  - "internal tester" = founder / bypass email → never blocked.

Design principles:
  1. Runs count at SESSION START (Phase 1 OA start), not on completion.
  2. Resuming an in-progress attempt is NEVER blocked — the gate only applies
     to fresh starts.
  3. Plan cap exhausted → check credits before hard-blocking.
  4. Grants only via webhook-confirmed payment path (verify_payment/webhook).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple, List


# ---------------------------------------------------------------------------
# Plan catalog — prices, caps, and duration semantics.
#
# resets_every_days: 30 → Basic/Pro monthly reset window
# validity_days:     e.g. 90 → MAX pass; None for subscription plans
# ---------------------------------------------------------------------------
PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
    "free": {
        "run_limit": 1,                # normal after contest window
        "company_cap": 1,
        "resets_every_days": None,     # free doesn't reset
        "validity_days": None,
        "extras": [],
    },
    "basic": {
        "run_limit": 10,
        "company_cap": 4,
        "resets_every_days": 30,
        "validity_days": 30,
        "extras": [],
    },
    "pro": {
        "run_limit": 20,
        "company_cap": 6,
        "resets_every_days": 30,
        "validity_days": 30,
        "extras": [],
    },
    "max": {
        "run_limit": 25,
        "company_cap": None,           # all 14 (+ generic core-default) unlocked
        "resets_every_days": None,     # one-time, no reset
        "validity_days": 90,
        "extras": ["pdf_export", "multi_resume"],
    },
    "supermax": {
        "run_limit": 35,
        "company_cap": None,
        "resets_every_days": None,
        "validity_days": 180,
        "extras": ["pdf_export", "multi_resume"],
    },
    "founder": {                       # internal / bypass emails
        "run_limit": 10**9,
        "company_cap": None,
        "resets_every_days": None,
        "validity_days": None,
        "extras": ["pdf_export", "multi_resume"],
    },
}


# TEMPORARY contest-window override (revert on 2026-07-21).
# Until this date, Free users get 3 full 4-phase runs on any company.
# After the date, Free reverts to 1 OA-only run.
# TODO(2026-07-21): remove `CONTEST_END` handling and drop this override.
CONTEST_END = datetime(2026, 7, 21, 23, 59, 59, tzinfo=timezone.utc)
FREE_RUN_LIMIT_DURING_CONTEST = 3
FREE_RUN_LIMIT_AFTER_CONTEST = 1


# ---- Helpers ---------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(s: Any) -> Optional[datetime]:
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    if isinstance(s, str):
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def is_internal_tester(user: Dict[str, Any]) -> bool:
    return user.get("plan") == "founder" or bool(user.get("is_internal_tester"))


def effective_run_limit(user: Dict[str, Any]) -> int:
    plan = user.get("plan", "free")
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    if plan == "free":
        return FREE_RUN_LIMIT_DURING_CONTEST if _now() <= CONTEST_END else FREE_RUN_LIMIT_AFTER_CONTEST
    return limits["run_limit"]


def free_is_oa_only(user: Dict[str, Any]) -> bool:
    """During the contest window Free unlocks full pipeline; after it reverts to
    OA-only (Interview + Review are locked)."""
    if user.get("plan") != "free":
        return False
    return _now() > CONTEST_END


def plan_expired(user: Dict[str, Any]) -> bool:
    """MAX/SuperMAX and Basic/Pro all carry an explicit expiry."""
    if is_internal_tester(user):
        return False
    exp = _parse_iso(user.get("plan_expires_at"))
    if not exp:
        return False
    return _now() > exp


def _in_current_window(user: Dict[str, Any]) -> bool:
    """For Basic/Pro: has the 30-day window elapsed since runs_period_start?
    If elapsed, caller should reset runs_used = 0 and roll period."""
    limits = PLAN_LIMITS.get(user.get("plan", "free"), {})
    days = limits.get("resets_every_days")
    if not days:
        return True
    start = _parse_iso(user.get("runs_period_start"))
    if not start:
        return False
    return (_now() - start) < timedelta(days=days)


def maybe_reset_period(user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a Mongo update-op if the user's Basic/Pro window has rolled over.
    Caller is responsible for applying it."""
    limits = PLAN_LIMITS.get(user.get("plan", "free"), {})
    if not limits.get("resets_every_days"):
        return None
    if _in_current_window(user):
        return None
    return {
        "$set": {
            "runs_used": 0,
            "runs_period_start": _now().isoformat(),
        }
    }


def runs_remaining_on_plan(user: Dict[str, Any]) -> int:
    if is_internal_tester(user):
        return 10**9
    if plan_expired(user):
        return 0
    used = int(user.get("runs_used", 0) or 0)
    limit = effective_run_limit(user)
    return max(0, limit - used)


def credits_balance(user: Dict[str, Any]) -> int:
    return int(user.get("credits", 0) or 0)


def can_start_run(user: Dict[str, Any]) -> Tuple[bool, str, str]:
    """Decide if this user can start a fresh run right now.

    Returns (allowed, reason_code, source):
      - source ∈ {"plan","credit","bypass"} indicates where the run is charged.
      - reason_code is a machine-readable string ("ok" if allowed, otherwise
        one of "plan_expired","limit_reached_no_credits").
    """
    if is_internal_tester(user):
        return True, "ok", "bypass"
    if plan_expired(user):
        # Expired plans fall back to free-tier limit for grace, but only if
        # there are still credits available.
        if credits_balance(user) > 0:
            return True, "ok", "credit"
        return False, "plan_expired", "none"
    if runs_remaining_on_plan(user) > 0:
        return True, "ok", "plan"
    if credits_balance(user) > 0:
        return True, "ok", "credit"
    return False, "limit_reached_no_credits", "none"


def assert_company_allowed(user: Dict[str, Any], company_id: str) -> Tuple[bool, str]:
    """Free/Basic/Pro have a company_cap. First N companies a user starts an OA
    against become their "selected" companies; further companies require the
    user to swap one out (POST /api/user/company-selection) or upgrade.
    """
    if is_internal_tester(user):
        return True, "ok"
    plan = user.get("plan", "free")
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    cap = limits.get("company_cap")
    if cap is None:
        return True, "ok"
    selections: List[str] = list(user.get("company_selections", []) or [])
    if company_id in selections:
        return True, "ok"
    if len(selections) < cap:
        return True, "ok"      # room to add on start
    return False, "company_cap_reached"


def build_state(user: Dict[str, Any]) -> Dict[str, Any]:
    """A dashboard-friendly snapshot: plan, runs left, credits, expiry etc.
    Callers can spread this into whatever /api/me / /api/pricing response."""
    plan = user.get("plan", "free")
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    exp = _parse_iso(user.get("plan_expires_at"))
    return {
        "plan": plan,
        "plan_expires_at": user.get("plan_expires_at"),
        "plan_expired": plan_expired(user),
        "run_limit": effective_run_limit(user),
        "runs_used": int(user.get("runs_used", 0) or 0),
        "runs_remaining_on_plan": runs_remaining_on_plan(user),
        "credits": credits_balance(user),
        "company_cap": limits.get("company_cap"),
        "company_selections": list(user.get("company_selections", []) or []),
        "free_is_oa_only": free_is_oa_only(user),
        "contest_window_active": _now() <= CONTEST_END,
        "extras": list(limits.get("extras", [])),
        "is_internal_tester": is_internal_tester(user),
    }


# ---- Credit packs & pricing publishing ------------------------------------

CREDIT_PACKS = [
    {"id": "credit-1",   "credits": 1,  "price": 49,  "currency": "INR", "label": "Single credit"},
    {"id": "credit-5",   "credits": 5,  "price": 199, "currency": "INR", "label": "5-pack"},
    {"id": "credit-10",  "credits": 10, "price": 349, "currency": "INR", "label": "10-pack"},
]


PLANS_CATALOG = [
    {
        "id": "free", "name": "Free", "price": 0, "currency": "INR",
        "companies": 1, "runs": FREE_RUN_LIMIT_DURING_CONTEST,
        "billing": "no billing",
        "card_copy": "Resume Checker unlimited · try before you pay.",
        "features": [
            "Resume Checker (always free, unlimited)",
            "1 OA-only company after Jul 21, 2026",
            "During contest window: 3 full 4-phase runs, any company",
        ],
        "cta": "Get started",
        "contest_boost": True,
    },
    {
        "id": "basic", "name": "Basic", "price": 399, "currency": "INR",
        "companies": 4, "runs": 10,
        "billing": "per month",
        "card_copy": "Four-company grind, full 4-phase · 10 runs/month.",
        "features": [
            "Full 4-phase pipeline (Resume → OA → Interview → Report)",
            "Up to 4 companies (swappable anytime)",
            "10 runs / month (resets every 30 days)",
        ],
        "cta": "Choose Basic",
    },
    {
        "id": "pro", "name": "Pro", "price": 799, "currency": "INR",
        "companies": 6, "runs": 20,
        "billing": "per month",
        "card_copy": "For the broader target list · 20 runs/month.",
        "features": [
            "Full 4-phase pipeline",
            "Up to 6 companies (swappable anytime)",
            "20 runs / month (resets every 30 days)",
        ],
        "cta": "Choose Pro",
        "highlight": True, "tag": "Most Picked",
    },
    {
        "id": "max", "name": "MAX", "price": 999, "currency": "INR",
        "companies": None, "runs": 25,
        "billing": "one-time · 90-day pass",
        "card_copy": "90-day pass, all 14 companies · 25 runs.",
        "features": [
            "All companies unlocked",
            "25 runs total over a 90-day window (no reset)",
            "PDF export + multi-resume support",
        ],
        "cta": "Buy MAX",
    },
    {
        "id": "supermax", "name": "SuperMAX", "price": 1399, "currency": "INR",
        "companies": None, "runs": 35,
        "billing": "one-time · 6-month pass",
        "card_copy": "6-month pass, half a placement season · 35 runs.",
        "features": [
            "All companies unlocked",
            "35 runs total over a 6-month window (no reset)",
            "PDF export + multi-resume support",
        ],
        "cta": "Buy SuperMAX",
        "tag": "Best Value",
    },
]
