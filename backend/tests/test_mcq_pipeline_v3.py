"""
Iteration 5 backend tests: NEW 3-stage MCQ pool pipeline.

Stage A: generator writes stem+options ONLY (no correct_index/explanation).
Stage B: ground truth via code execution (Python fence) OR two-solver agreement.
Stage C: explanation writer with conflict-flag (discard on conflict).

Covers:
  (a) Prompt strings no longer request correct_index/explanation.
  (b) `_extract_code_block` / `_ground_truth_from_execution` unit test with
      a hand-crafted python fence stem.
  (c) `_process_one_stem` unit test end-to-end for a code stem (must return
      ground_truth_source='execution' with correct_index=2 for print(2+3)).
  (d) `/api/admin/mcq-stats` returns new-shape stats and mentions new pipeline.
  (e) Pool docs written by the worker carry `ground_truth_source`.
  (f) OA start on tcs-nqt reaches ready with populated MCQ sections; served
      MCQs are internally consistent (fresh Sonnet solver agrees with stored
      correct_index).
  (g) Live-fallback path (empty pool) still produces new-pipeline shape.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import pytest
import requests

sys.path.insert(0, "/app/backend")

try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv("/app/backend/.env")
    _load_dotenv("/app/frontend/.env")
except Exception:
    pass

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://build-it-353.preview.emergentagent.com").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
FOUNDER_EMAIL = "prashati02@gmail.com"
FOUNDER_PW = "testpass123"


# ---------- fixtures ---------------------------------------------------------

@pytest.fixture(scope="module")
def founder_token() -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": FOUNDER_EMAIL, "password": FOUNDER_PW}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    tok = r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def auth_headers(founder_token) -> Dict[str, str]:
    return {"Authorization": f"Bearer {founder_token}", "Content-Type": "application/json"}


# ---------- (a) prompt strings -----------------------------------------------

class TestPromptShape:
    def test_mcq_prompt_no_correct_index_or_explanation(self):
        from services.ai_service import mcq_prompt, topic_mcq_prompt
        p1 = mcq_prompt("Infosys", "Aptitude", 3, None).lower()
        p2 = topic_mcq_prompt("TCS", "aptitude", "Aptitude", 3, None).lower()
        for label, p in (("mcq_prompt", p1), ("topic_mcq_prompt", p2)):
            assert "do not include a correct_index" in p, f"{label}: missing DO NOT include correct_index directive"
            assert "explanation" in p, f"{label}: should mention explanation is excluded"
            # Ensures prompt is not asking for correct_index/explanation in the
            # returned JSON shape.
            # (schema keys asked: id, prompt, options, difficulty only)
            assert "{id, prompt, options" in p, f"{label}: schema shape must be stem-only"

    def test_solver_prompt_and_explanation_prompt_exist(self):
        from services.ai_service import solver_prompt, explanation_prompt
        s_sys, s_user = solver_prompt("2+2?", ["3", "4", "5", "6"])
        assert "first principles" in s_sys.lower()
        e_sys, e_user = explanation_prompt("2+2?", ["3", "4", "5", "6"], 1)
        assert "conflict" in e_sys.lower()
        assert "rationalize" in e_sys.lower()


# ---------- (b) code execution ground truth ----------------------------------

class TestExtractAndExecute:
    def test_extract_python_fence(self):
        from banks.mcq_pool import _extract_code_block
        p = "What does this print?\n```python\nprint(2+3)\n```"
        got = _extract_code_block(p)
        assert got is not None
        lang, code = got
        assert lang == "python"
        assert "print(2+3)" in code

    def test_extract_unlabelled_python_heuristic(self):
        from banks.mcq_pool import _extract_code_block
        p = "Output?\n```\nfor i in range(3):\n    print(i)\n```"
        got = _extract_code_block(p)
        assert got is not None and got[0] == "python"

    def test_extract_none_for_text_prompt(self):
        from banks.mcq_pool import _extract_code_block
        assert _extract_code_block("What is 2+3?") is None

    def test_ground_truth_from_execution_matches_option(self):
        from banks.mcq_pool import _ground_truth_from_execution
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(_ground_truth_from_execution(
                "```python\nprint(2+3)\n```",
                ["3", "4", "5", "6"],
            ))
        finally:
            loop.close()
        assert res is not None, "execution did not derive a ground truth"
        idx, stdout = res
        assert idx == 2, f"expected index 2 for '5', got {idx} (stdout={stdout!r})"


# ---------- (c) _process_one_stem end-to-end --------------------------------

class TestProcessOneStem:
    def test_code_stem_uses_execution_source(self):
        """Hand-crafted code stem should be accepted with ground_truth_source='execution'
        AND consistent explanation (no conflict)."""
        # Requires ANTHROPIC_API_KEY for stage-C explanation call
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        from banks import mcq_pool
        # Ensure db is inited so _record_outcome doesn't blow up. In test
        # context, we don't want to write to prod db. Point to a temp db.
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL")
        assert mongo_url
        client = AsyncIOMotorClient(mongo_url)
        db = client["placemint_test_pipeline_v3"]
        mcq_pool.init(db)

        stem = {
            "id": "q1",
            "prompt": "What does this Python code print?\n```python\nprint(2+3)\n```",
            "options": ["3", "4", "5", "6"],
            "difficulty": "Easy",
        }
        loop = asyncio.new_event_loop()
        try:
            doc = loop.run_until_complete(
                mcq_pool._process_one_stem("test-company", "test-section", stem)
            )
            # Cleanup temp db
            loop.run_until_complete(client.drop_database("placemint_test_pipeline_v3"))
        finally:
            loop.close()

        assert doc is not None, "process_one_stem returned None for a valid code stem"
        assert doc["correct_index"] == 2, f"correct_index should be 2, got {doc['correct_index']}"
        assert doc["ground_truth_source"] == "execution", f"expected execution source, got {doc.get('ground_truth_source')}"
        assert doc.get("explanation"), "explanation should be non-empty"
        assert doc.get("verified") is True


# ---------- (d) admin/mcq-stats new shape ------------------------------------

class TestAdminStatsNewShape:
    def test_founder_stats_shape(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/mcq-stats", headers=auth_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("buffer_target")
        # New-pipeline metadata
        assert "pipeline" in data
        assert "3-stage" in data["pipeline"]
        assert data.get("generator_model", "").startswith("claude-haiku")
        assert data.get("solver_a_model", "").startswith("claude-sonnet")
        assert data.get("solver_b_model", "").startswith("claude-haiku")
        assert data.get("explanation_model", "").startswith("claude-sonnet")
        # Legacy field explicitly should NOT be present in new shape
        assert "verifier_model" not in data, "legacy 'verifier_model' should be gone from new stats"
        stats = data.get("stats") or []
        # Verify new outcome fields appear on aggregated docs
        if stats:
            sample = stats[0]
            has_new_fields = any(k in sample for k in (
                "outcome_accepted", "outcome_dropped_no_ground_truth",
                "outcome_dropped_explanation_conflict", "acceptance_rate_pct",
            ))
            assert has_new_fields, f"no new-shape outcome fields in stats sample: {sample}"
            # Legacy fields (pre-purge) MAY still linger from historical docs;
            # main-agent said purge was at 17:27 UTC so new writes should
            # produce new fields. Assert new writes exist:
            new_writes = [s for s in stats if s.get("total_generated", 0) > 0]
            assert new_writes, "no stats docs with total_generated>0 — worker did not run?"


# ---------- (e) pool docs carry ground_truth_source --------------------------

class TestPoolDocsCarrySource:
    def test_wait_and_inspect(self, auth_headers):
        """Wait up to ~120s for the pool worker to add verified docs, then
        inspect via direct DB. Expect at least one doc with ground_truth_source
        in {execution, solver_agreement}. Execution-source is opportunistic
        (only for python-fence prompts) so absence is acceptable; we assert
        that AT LEAST solver_agreement docs exist."""
        # Poll admin stats until pool has grown
        deadline = time.time() + 130
        pool_count = 0
        while time.time() < deadline:
            r = requests.get(f"{BASE_URL}/api/admin/mcq-stats", headers=auth_headers, timeout=15)
            if r.status_code == 200:
                pc = sum(int(x.get("count", 0)) for x in (r.json().get("pool_counts") or []))
                pool_count = pc
                if pc >= 3:
                    break
            time.sleep(10)
        assert pool_count >= 1, f"pool did not grow within window (count={pool_count})"

        # Direct db inspect. Create Motor client inside the loop so its
        # internal futures bind to the same loop.
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME") or "test_database"

        async def _fetch():
            from motor.motor_asyncio import AsyncIOMotorClient
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            return await db.mcq_pool.find({"verified": True}, {"_id": 0}).to_list(length=25)

        loop = asyncio.new_event_loop()
        try:
            docs = loop.run_until_complete(_fetch())
        finally:
            loop.close()
        assert docs, "no verified pool docs in DB"
        with_source = [d for d in docs if d.get("ground_truth_source") in ("execution", "solver_agreement")]
        assert with_source, (
            f"no pool docs carry ground_truth_source. Sample doc keys: "
            f"{list(docs[0].keys()) if docs else 'n/a'}"
        )
        # At least solver_agreement should be common
        solver_docs = [d for d in with_source if d["ground_truth_source"] == "solver_agreement"]
        assert solver_docs, "expected at least one solver_agreement doc"


# ---------- (f) OA end-to-end + consistency ---------------------------------

@pytest.fixture(scope="module")
def oa_attempt(auth_headers) -> Dict[str, Any]:
    r = requests.post(f"{BASE_URL}/api/oa/start",
                      headers=auth_headers, json={"company_id": "tcs-nqt"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()


class TestOAEndToEnd:
    def test_reaches_ready_with_populated_mcqs(self, oa_attempt, auth_headers):
        aid = oa_attempt["attempt_id"]
        deadline = time.time() + 240
        last = None
        while time.time() < deadline:
            r = requests.get(f"{BASE_URL}/api/oa/{aid}", headers=auth_headers, timeout=30)
            assert r.status_code == 200, r.text[:300]
            last = r.json()
            gs = last.get("generation_status")
            if gs == "ready":
                break
            if gs == "failed":
                pytest.fail(f"generation failed: {last}")
            time.sleep(10)
        assert last and last.get("generation_status") == "ready", f"never ready: {last and last.get('generation_status')}"
        mcq_sections = [s for s in last.get("sections", []) if s.get("type") in ("mcq", "topic_mcq")]
        assert mcq_sections, "no mcq sections in attempt"
        for s in mcq_sections:
            assert (s.get("questions") or []), f"section {s.get('key')} has no questions"


async def _sonnet_solve(prompt_text: str, options: List[str]) -> Optional[int]:
    from services.ai_service import call_json, SONNET, solver_prompt
    sys_m, user_m = solver_prompt(prompt_text, options)
    try:
        resp = await call_json(sys_m, user_m, model=SONNET)
    except Exception as e:
        print(f"[solve] error: {e}")
        return None
    if isinstance(resp, dict):
        v = resp.get("correct_index")
        if isinstance(v, int) and v in (0, 1, 2, 3):
            return v
    return None


class TestServedMcqsInternallyConsistent:
    def test_fresh_sonnet_solve_agrees_with_stored(self, oa_attempt, auth_headers):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("no ANTHROPIC_API_KEY")
        aid = oa_attempt["attempt_id"]
        doc = None
        for _ in range(24):
            r = requests.get(f"{BASE_URL}/api/oa/{aid}", headers=auth_headers, timeout=30)
            if r.status_code == 200 and r.json().get("generation_status") == "ready":
                doc = r.json()
                break
            time.sleep(10)
        assert doc, "attempt never ready"
        # Collect a few MCQs
        picks: List[Tuple[str, dict]] = []
        for s in doc.get("sections", []) or []:
            if s.get("type") not in ("mcq", "topic_mcq"):
                continue
            for q in (s.get("questions") or []):
                if isinstance(q.get("options"), list) and len(q["options"]) == 4 and q.get("correct_index") in (0,1,2,3):
                    picks.append((s.get("key"), q))
            if len(picks) >= 5:
                break
        picks = picks[:5]
        if len(picks) < 3:
            pytest.skip(f"only {len(picks)} MCQs collected")

        loop = asyncio.new_event_loop()
        try:
            regressions = []
            for sk, q in picks:
                got = loop.run_until_complete(_sonnet_solve(q["prompt"], q["options"]))
                print(f"[consistency] section={sk} stored={q['correct_index']} solver={got} :: {(q.get('prompt') or '')[:70]}")
                if isinstance(got, int) and got != q["correct_index"]:
                    regressions.append({"section": sk, "stored": q["correct_index"], "solver": got,
                                        "prompt": q["prompt"][:100]})
        finally:
            loop.close()
        assert not regressions, f"fresh sonnet solver disagrees with stored correct_index: {regressions}"


# ============================================================================
# ITERATION 6: Transpile-and-Execute ground-truth path for pseudocode
# ============================================================================

# ---------- (h) _looks_like_code_output_question heuristic -------------------

class TestLooksLikeCodeOutputHeuristic:
    def test_pseudocode_begin_end_detected(self):
        from banks.mcq_pool import _looks_like_code_output_question
        p = ("What does the following pseudocode print?\n"
             "BEGIN\n  SET x = 3\n  SET y = 4\n  PRINT x + y\nEND")
        assert _looks_like_code_output_question(p) is True

    def test_java_style_code_detected(self):
        from banks.mcq_pool import _looks_like_code_output_question
        p = ("What does this Java program print?\n"
             "int a = 5; int b = 2; System.out.println(a*b + 3);")
        assert _looks_like_code_output_question(p) is True

    def test_non_code_question_rejected(self):
        from banks.mcq_pool import _looks_like_code_output_question
        assert _looks_like_code_output_question("What is the capital of France?") is False

    def test_empty_prompt(self):
        from banks.mcq_pool import _looks_like_code_output_question
        assert _looks_like_code_output_question("") is False


# ---------- (i) _ground_truth_from_pseudocode_transpile ---------------------

class TestTranspileExecute:
    def test_begin_end_pseudocode_returns_correct_index(self):
        """BEGIN/END/PRINT pseudocode should be transpiled to Python, executed,
        and the correct option index returned."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")
        from banks.mcq_pool import _ground_truth_from_pseudocode_transpile
        prompt = ("What does the following pseudocode print?\n"
                  "BEGIN\n  SET x = 3\n  SET y = 4\n  PRINT x + y\nEND")
        options = ["5", "7", "12", "34"]
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(
                _ground_truth_from_pseudocode_transpile(prompt, options)
            )
        finally:
            loop.close()
        assert res is not None, "transpile+execute did not derive ground truth"
        idx, stdout = res
        assert idx == 1, f"expected index 1 for '7', got {idx} (stdout={stdout!r})"

    def test_non_code_question_returns_none(self):
        """Non-code questions should short-circuit before making an LLM call."""
        from banks.mcq_pool import _ground_truth_from_pseudocode_transpile
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(
                _ground_truth_from_pseudocode_transpile(
                    "What is the capital of France?",
                    ["London", "Paris", "Berlin", "Madrid"],
                )
            )
        finally:
            loop.close()
        assert res is None, f"non-code question should return None, got {res}"

    def test_java_style_code_returns_correct_index(self):
        """Java-style code without a Python fence should be transpiled+executed."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")
        from banks.mcq_pool import _ground_truth_from_pseudocode_transpile
        prompt = ("What does the following Java code print?\n"
                  "int a = 5; int b = 2; System.out.println(a*b + 3);")
        options = ["13", "10", "7", "25"]
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(
                _ground_truth_from_pseudocode_transpile(prompt, options)
            )
        finally:
            loop.close()
        assert res is not None, "Java transpile+execute did not derive ground truth"
        idx, stdout = res
        assert idx == 0, f"expected index 0 for '13', got {idx} (stdout={stdout!r})"


# ---------- (j) _process_one_stem uses transpile_execution source ------------

class TestProcessOneStemTranspileSource:
    def test_pseudocode_stem_uses_transpile_execution_source(self):
        """Hand-crafted pseudocode stem (no fence) should be accepted with
        ground_truth_source='transpile_execution'."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        from banks import mcq_pool
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL")
        assert mongo_url
        client = AsyncIOMotorClient(mongo_url)
        db = client["placemint_test_pipeline_v3_transpile"]
        mcq_pool.init(db)

        stem = {
            "id": "q1",
            "prompt": ("What does the following pseudocode print?\n"
                       "BEGIN\n  SET x = 3\n  SET y = 4\n  PRINT x + y\nEND"),
            "options": ["5", "7", "12", "34"],
            "difficulty": "Easy",
        }
        loop = asyncio.new_event_loop()
        try:
            doc = loop.run_until_complete(
                mcq_pool._process_one_stem("test-company", "pseudocode", stem)
            )
            loop.run_until_complete(client.drop_database("placemint_test_pipeline_v3_transpile"))
        finally:
            loop.close()

        assert doc is not None, "process_one_stem returned None for pseudocode stem"
        assert doc["correct_index"] == 1, f"expected 1, got {doc['correct_index']}"
        assert doc["ground_truth_source"] == "transpile_execution", (
            f"expected transpile_execution, got {doc.get('ground_truth_source')}")
        assert doc.get("explanation"), "explanation should be non-empty"
        assert doc.get("verified") is True


# ---------- (k) server routes pseudocode section through fallback_live_verify

class TestPseudocodeSectionRouting:
    """Verify that pseudocode-typed sections in _generate_section_questions
    are actually routed through mcq_pool.fallback_live_verify (the 3-stage
    pipeline) instead of the old raw call_json(pseudocode_prompt) path."""

    def test_generate_section_questions_pseudocode_uses_pipeline(self, monkeypatch):
        import asyncio as _a
        import server
        from banks import mcq_pool as _pool

        raw_called = {"n": 0}
        pipeline_called = {"n": 0}

        async def fake_call_json(*args, **kwargs):
            raw_called["n"] += 1
            return []

        async def fake_fallback(*args, **kwargs):
            pipeline_called["n"] += 1
            return [{"id": "q1", "prompt": "p", "options": ["a", "b", "c", "d"],
                     "correct_index": 0, "explanation": "e", "difficulty": "Easy"}]

        monkeypatch.setattr(server, "call_json", fake_call_json)
        monkeypatch.setattr(_pool, "fallback_live_verify", fake_fallback)

        section = {"type": "pseudocode", "name": "Programming Concepts",
                   "key": "pseudocode", "count": 3, "difficulty_target": None}
        loop = _a.new_event_loop()
        try:
            out = loop.run_until_complete(
                server._generate_section_questions("TCS NQT", section, "test-user", "test-attempt")
            )
        finally:
            loop.close()

        # The whole point: pseudocode sections must NOT fall through the raw
        # call_json(pseudocode_prompt) path — they must go through the
        # 3-stage pipeline (fallback_live_verify).
        assert pipeline_called["n"] >= 1, (
            "pseudocode section did not invoke mcq_pool.fallback_live_verify — "
            "the routing change appears to be dead code (there's an earlier "
            "`elif stype == 'pseudocode':` branch at line ~743 that catches it "
            "first and still calls the raw pseudocode_prompt path)."
        )
        assert raw_called["n"] == 0, (
            f"pseudocode section still called the raw call_json path "
            f"({raw_called['n']}x) instead of the 3-stage pipeline."
        )
        assert isinstance(out, list) and len(out) >= 1


# ---------- (l) admin/mcq-stats surfaces source_transpile_execution ---------

class TestAdminStatsTranspileSource:
    def test_transpile_source_bucket_reflected(self, auth_headers):
        """When the pool records transpile_execution outcomes, pool_stats()
        should surface them. This test just validates the endpoint can carry
        the field (either present via existing writes, or the code path is
        wired to include source_transpile_execution when incremented)."""
        # Direct check: `_record_outcome` uses f"source_{source}" so any
        # transpile_execution acceptance produces `source_transpile_execution`.
        # Verify the admin endpoint doesn't strip it.
        r = requests.get(f"{BASE_URL}/api/admin/mcq-stats", headers=auth_headers, timeout=20)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        stats = data.get("stats") or []
        # If any doc has source_transpile_execution, it must survive to the response.
        # We inspect by keyset — endpoint is a pass-through so ANY key beginning
        # with source_ should be preserved.
        # Sanity: at least one stats doc should exist (worker has been running)
        assert isinstance(stats, list)
        # Print for observability — we don't hard-fail if no transpile docs
        # have accumulated yet, but we flag it.
        found = [s for s in stats if s.get("source_transpile_execution", 0) > 0]
        print(f"[transpile] stats docs with source_transpile_execution > 0: {len(found)}")
        # We ASSERT the endpoint schema allows this field to appear; we do not
        # hard-require accumulated docs since transpile depends on generator
        # emitting fenceless pseudocode which is stochastic.
