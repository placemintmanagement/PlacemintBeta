"""Iteration 2 tests: multi-language code runner, password reset, email verification,
and hand-tuned company section metadata (Accenture, Zoho, Tech Mahindra)."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip()
                break
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

TESTUSER_EMAIL = "aarav.test@placemint.dev"
TESTUSER_PASSWORD = "testpass123"
TIMEOUT_LONG = 240


# ---------------- Fixtures ----------------

@pytest.fixture(scope="module")
def test_user_session():
    """Login as the persistent test user."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": TESTUSER_EMAIL, "password": TESTUSER_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Test user login failed: {r.text}"
    tok = r.json()["token"]
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s, tok


@pytest.fixture(scope="module")
def fresh_user():
    """Create fresh user for isolated tests (verify email + password reset)."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"test_it2_{uuid.uuid4().hex[:8]}@placemint.dev"
    pw = "initialpw123"
    r = s.post(f"{API}/auth/signup", json={"name": "It2 User", "email": email, "password": pw}, timeout=30)
    assert r.status_code == 200
    tok = r.json()["token"]
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return {"session": s, "token": tok, "email": email, "password": pw}


@pytest.fixture(scope="module")
def deloitte_attempt(test_user_session):
    """Start a Deloitte OA for the test user; used to exercise /oa/run for all languages.
    We reuse a *single* attempt because starting one is expensive and quota-limited."""
    s, _ = test_user_session
    r = s.post(f"{API}/oa/start", json={"company_id": "deloitte-usi"}, timeout=TIMEOUT_LONG)
    if r.status_code == 402:
        pytest.skip("quota exhausted for test user")
    assert r.status_code == 200, r.text
    attempt = r.json()
    coding = next((sec for sec in attempt["sections"] if sec["type"] == "coding"), None)
    assert coding is not None and coding.get("questions")
    return {
        "session": s,
        "attempt_id": attempt["attempt_id"],
        "section_key": coding["key"],
        "problem_id": str(coding["questions"][0]["id"]),
    }


# ---------------- 1. Multi-language code runner ----------------

CODE_SAMPLES = {
    "python": "import sys\ndata=sys.stdin.read()\nprint(data.strip())\n",
    "javascript": "let d=''; process.stdin.on('data',c=>d+=c); process.stdin.on('end',()=>process.stdout.write(d.trim()));",
    "cpp": "#include <bits/stdc++.h>\nusing namespace std;\nint main(){string s,l;while(getline(cin,l)){s+=l+\"\\n\";}while(!s.empty()&&isspace(s.back()))s.pop_back();cout<<s;return 0;}",
    "java": "import java.util.*;public class Main{public static void main(String[] a){Scanner sc=new Scanner(System.in);StringBuilder sb=new StringBuilder();while(sc.hasNextLine()){sb.append(sc.nextLine());sb.append('\\n');}System.out.print(sb.toString().trim());}}",
}


@pytest.mark.parametrize("lang", ["python", "javascript", "cpp", "java"])
def test_oa_run_multi_language(deloitte_attempt, lang):
    s = deloitte_attempt["session"]
    payload = {
        "attempt_id": deloitte_attempt["attempt_id"],
        "section_key": deloitte_attempt["section_key"],
        "problem_id": deloitte_attempt["problem_id"],
        "language": lang,
        "code": CODE_SAMPLES[lang],
    }
    r = s.post(f"{API}/oa/run", json=payload, timeout=60)
    assert r.status_code == 200, f"[{lang}] {r.status_code}: {r.text[:400]}"
    body = r.json()
    assert "results" in body and isinstance(body["results"], list)
    assert body.get("supported_languages") == ["python", "javascript", "cpp", "java"]
    assert body.get("language") == lang


# ---------------- 2. Password reset flow ----------------

def test_password_forgot_existing_returns_dev_link():
    s = requests.Session()
    r = s.post(f"{API}/auth/password/forgot", json={"email": TESTUSER_EMAIL}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    for k in ("ok", "message", "dev_link", "token", "expires_in_minutes"):
        assert k in data, f"missing key: {k}"
    assert data["ok"] is True


def test_password_forgot_nonexistent_no_leak():
    s = requests.Session()
    r = s.post(f"{API}/auth/password/forgot", json={"email": f"nope_{uuid.uuid4().hex}@placemint.dev"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "dev_link" not in data
    assert "token" not in data
    assert data.get("ok") is True
    assert "message" in data


def test_password_reset_full_flow_and_single_use():
    """Reset password → login with new → login with old fails → token cannot be reused → reset back."""
    s = requests.Session()
    # 1. request reset
    r = s.post(f"{API}/auth/password/forgot", json={"email": TESTUSER_EMAIL}, timeout=15)
    assert r.status_code == 200
    token = r.json()["token"]

    NEW_PW = "freshpass99"

    # 2. reset with token
    r = s.post(f"{API}/auth/password/reset", json={"token": token, "new_password": NEW_PW}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    # 3. login with new pw succeeds
    r = s.post(f"{API}/auth/login", json={"email": TESTUSER_EMAIL, "password": NEW_PW}, timeout=15)
    assert r.status_code == 200

    # 4. login with old pw fails
    r = s.post(f"{API}/auth/login", json={"email": TESTUSER_EMAIL, "password": TESTUSER_PASSWORD}, timeout=15)
    assert r.status_code == 401

    # 5. Reuse of same token must fail (single-use)
    r = s.post(f"{API}/auth/password/reset", json={"token": token, "new_password": "anotherpw123"}, timeout=15)
    assert r.status_code == 400
    assert "Invalid or expired" in r.text

    # 6. Reset password BACK to original so credentials remain valid
    r = s.post(f"{API}/auth/password/forgot", json={"email": TESTUSER_EMAIL}, timeout=15)
    assert r.status_code == 200
    tok2 = r.json()["token"]
    r = s.post(f"{API}/auth/password/reset", json={"token": tok2, "new_password": TESTUSER_PASSWORD}, timeout=15)
    assert r.status_code == 200

    # Final: original creds work again
    r = s.post(f"{API}/auth/login", json={"email": TESTUSER_EMAIL, "password": TESTUSER_PASSWORD}, timeout=15)
    assert r.status_code == 200, "FAILED to restore original test user password!"


# ---------------- 3. Email verification flow ----------------

def test_email_verification_flow(fresh_user):
    s = fresh_user["session"]
    # Should NOT be verified initially (password signup)
    r = s.get(f"{API}/auth/me", timeout=15)
    assert r.status_code == 200
    me = r.json()
    assert me.get("email_verified") is False
    assert me.get("auth_provider") == "password"

    # send-verification
    r = s.post(f"{API}/auth/email/send-verification", json={}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    for k in ("ok", "dev_link", "token", "expires_in_minutes"):
        assert k in data, f"missing key: {k}"
    token = data["token"]

    # verify with token
    r = s.post(f"{API}/auth/email/verify", json={"token": token}, timeout=15)
    assert r.status_code == 200
    assert r.json().get("ok") is True

    # /me now shows verified
    r = s.get(f"{API}/auth/me", timeout=15)
    assert r.json().get("email_verified") is True

    # Sending again returns already_verified
    r = s.post(f"{API}/auth/email/send-verification", json={}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("already_verified") is True


# ---------------- 4. Hand-tuned companies (metadata) ----------------

def test_accenture_cognitive_section_metadata():
    r = requests.get(f"{API}/companies/accenture", timeout=15)
    assert r.status_code == 200
    c = r.json()
    cog = next((s for s in c["sections"] if s["key"] == "cognitive"), None)
    assert cog is not None
    assert cog["type"] == "cognitive_game"
    assert cog.get("per_question_seconds") == 15


def test_zoho_pen_paper_metadata():
    r = requests.get(f"{API}/companies/zoho", timeout=15)
    assert r.status_code == 200
    c = r.json()
    coding = next((s for s in c["sections"] if s["key"] == "coding"), None)
    assert coding is not None
    assert coding.get("pen_paper") is True


def test_tech_mahindra_automata_fix_metadata():
    r = requests.get(f"{API}/companies/tech-mahindra", timeout=15)
    assert r.status_code == 200
    c = r.json()
    coding = next((s for s in c["sections"] if s["key"] == "coding"), None)
    assert coding is not None
    assert coding.get("automata_fix") is True
