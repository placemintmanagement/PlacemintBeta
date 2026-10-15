"""Grading infra-failure handling (2026-10): verifies that an
infrastructure_error (the sandbox itself failing to run candidate code --
never the candidate's fault) is retried and never silently scored as a
wrong answer or folded into a partial score. Covers both layers the task
named: services/code_runner.py's run_tests_with_retry (the retry +
classification mechanics) and server.py's _grade_coding_section (the
abort-the-whole-section-on-persistent-infra-failure behavior).

Uses a FAKE run_code / run_tests_with_retry throughout -- no real
subprocess, no sandbox, no dependency on this machine's actual
subprocess-spawn speed. That real mechanism (Windows Defender real-time/
IOAV scanning, a cluttered %TEMP%) was already investigated and explained
separately (see problem_bank.py's PM_BANK_REF_TIMEOUT comment and the
Stage 2c commit history); this file tests the DECISION logic in
isolation, deterministically, independent of host timing.

No model is used anywhere in this file.
"""
import asyncio

import pytest

import server
from services import code_runner


def _result(category, stdout="", exit_code=0, timed_out=False):
    return {
        "stdout": stdout, "stderr": "", "exit_code": exit_code,
        "timed_out": timed_out, "error": None, "category": category,
    }


# ---------------------------------------------------------------------------
# Layer 1: services/code_runner.run_tests_with_retry
# ---------------------------------------------------------------------------

def test_infra_error_then_success_counts_as_pass(monkeypatch):
    calls = {"n": 0}

    def fake_run_code(language, code, stdin, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return _result("infrastructure_error")
        return _result("ok", stdout="42")

    monkeypatch.setattr(code_runner, "run_code", fake_run_code)
    tests = [{"input": "x", "expected_output": "42"}]
    passed, details, unresolved_infra = code_runner.run_tests_with_retry("python", "code", tests)
    assert passed == 1
    assert details[0]["status"] == "passed"
    assert details[0]["attempts"] == 2
    assert unresolved_infra is False


def test_persistent_infra_error_reports_unresolved(monkeypatch):
    def fake_run_code(language, code, stdin, timeout):
        return _result("infrastructure_error")

    monkeypatch.setattr(code_runner, "run_code", fake_run_code)
    tests = [{"input": "x", "expected_output": "42"}]
    passed, details, unresolved_infra = code_runner.run_tests_with_retry(
        "python", "code", tests, max_retries=2)
    assert passed == 0
    assert details[0]["status"] == "infrastructure_error"
    assert details[0]["attempts"] == 3  # 1 initial + 2 retries, never more
    assert unresolved_infra is True


def test_genuine_tle_is_not_retried_and_counts_as_failed(monkeypatch):
    calls = {"n": 0}

    def fake_run_code(language, code, stdin, timeout):
        calls["n"] += 1
        return _result("time_limit_exceeded", timed_out=True)

    monkeypatch.setattr(code_runner, "run_code", fake_run_code)
    tests = [{"input": "x", "expected_output": "42"}]
    passed, details, unresolved_infra = code_runner.run_tests_with_retry("python", "code", tests)
    assert passed == 0
    assert details[0]["status"] == "time_limit_exceeded"
    assert details[0]["attempts"] == 1  # a real TLE is never retried
    assert calls["n"] == 1
    assert unresolved_infra is False


def test_normal_pass_and_wrong_answer_unchanged(monkeypatch):
    def fake_run_code(language, code, stdin, timeout):
        return _result("ok", stdout=stdin)  # echoes stdin back as stdout

    monkeypatch.setattr(code_runner, "run_code", fake_run_code)
    tests = [
        {"input": "a", "expected_output": "a"},
        {"input": "b", "expected_output": "NOT_B"},
    ]
    passed, details, unresolved_infra = code_runner.run_tests_with_retry("python", "code", tests)
    assert passed == 1
    assert details[0]["status"] == "passed" and details[0]["passed"] is True
    assert details[1]["status"] == "wrong_answer" and details[1]["passed"] is False
    assert unresolved_infra is False
    # run_tests() (the pre-existing, non-retry function) gives the identical
    # passed/status shape for the same inputs -- confirms normal-run
    # behavior is genuinely unchanged by adding its retry-aware sibling.
    passed2, details2 = code_runner.run_tests("python", "code", tests)
    assert passed2 == passed
    assert [d["status"] for d in details2] == [d["status"] for d in details]
    assert [d["passed"] for d in details2] == [d["passed"] for d in details]


# ---------------------------------------------------------------------------
# Layer 2: server._grade_coding_section
# ---------------------------------------------------------------------------

def _section_with_one_problem():
    return {
        "questions": [{
            "id": "p1", "title": "Problem 1",
            "visible_tests": [{"input": "1", "expected_output": "1"}],
            "hidden_tests": [{"input": "2", "expected_output": "2"}],
        }],
    }


def test_grade_coding_section_persistent_infra_raises_503(monkeypatch):
    def fake_run_tests_with_retry(language, code, tests, timeout=5, max_retries=2):
        return 0, [{
            "index": 0, "status": "infrastructure_error", "passed": False, "attempts": 3,
            "input": "", "expected": "", "got": "", "error": "boom",
            "stderr": None, "timed_out": True,
        }], True

    monkeypatch.setattr(server, "_lang_run_tests_with_retry", fake_run_tests_with_retry)
    section = _section_with_one_problem()
    answers = {"p1": {"code": "print(1)", "language": "python"}}
    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(server._grade_coding_section(section, answers, use_ai_note=False))
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "grading_infra_error"


def test_grade_coding_section_infra_then_success_scores_normally(monkeypatch):
    # From _grade_coding_section's point of view, a transient infra error
    # that run_tests_with_retry already resolved internally is invisible --
    # unresolved_infra comes back False, so grading proceeds exactly as a
    # normal all-pass run would.
    def fake_run_tests_with_retry(language, code, tests, timeout=5, max_retries=2):
        details = [{
            "index": i, "status": "passed", "passed": True, "attempts": 2,
            "input": t["input"], "expected": t["expected_output"], "got": t["expected_output"],
            "error": None, "stderr": None, "timed_out": False,
        } for i, t in enumerate(tests)]
        return len(tests), details, False

    monkeypatch.setattr(server, "_lang_run_tests_with_retry", fake_run_tests_with_retry)
    section = _section_with_one_problem()
    answers = {"p1": {"code": "print(1)", "language": "python"}}
    result = asyncio.run(server._grade_coding_section(section, answers, use_ai_note=False))
    assert result["problems"][0]["visible"] == {"passed": 1, "total": 1}
    assert result["problems"][0]["hidden"] == {"passed": 1, "total": 1}
    assert result["score"] == 1.0


def test_grade_coding_section_genuine_tle_still_counts_as_failed(monkeypatch):
    def fake_run_tests_with_retry(language, code, tests, timeout=5, max_retries=2):
        details = [{
            "index": i, "status": "time_limit_exceeded", "passed": False, "attempts": 1,
            "input": t["input"], "expected": t["expected_output"], "got": "",
            "error": "Timed out after 5s", "stderr": None, "timed_out": True,
        } for i, t in enumerate(tests)]
        return 0, details, False  # a real TLE -- NOT unresolved_infra

    monkeypatch.setattr(server, "_lang_run_tests_with_retry", fake_run_tests_with_retry)
    section = _section_with_one_problem()
    answers = {"p1": {"code": "while True: pass", "language": "python"}}
    result = asyncio.run(server._grade_coding_section(section, answers, use_ai_note=False))
    assert result["problems"][0]["visible"] == {"passed": 0, "total": 1}
    assert result["problems"][0]["hidden"] == {"passed": 0, "total": 1}
    assert result["score"] == 0.0


def test_grade_coding_section_normal_run_shape_unchanged(monkeypatch):
    def fake_run_tests_with_retry(language, code, tests, timeout=5, max_retries=2):
        details = [{
            "index": i, "status": "passed", "passed": True, "attempts": 1,
            "input": t["input"], "expected": t["expected_output"], "got": t["expected_output"],
            "error": None, "stderr": None, "timed_out": False,
        } for i, t in enumerate(tests)]
        return len(tests), details, False

    monkeypatch.setattr(server, "_lang_run_tests_with_retry", fake_run_tests_with_retry)
    section = _section_with_one_problem()
    answers = {"p1": {"code": "print(1)", "language": "python"}}
    result = asyncio.run(server._grade_coding_section(section, answers, use_ai_note=False))
    # Shape is exactly what it was before this round's work: {"score",
    # "problems", "passed"}, each problem carrying {"visible": {"passed",
    # "total"}, "hidden": {"passed", "total"}} -- the precise shape
    # services/tcs_tiers.py's _problem_result reads for track computation.
    assert set(result.keys()) >= {"score", "problems", "passed"}
    assert set(result["problems"][0].keys()) >= {"problem_id", "title", "visible", "hidden", "ai"}
    assert result["problems"][0]["visible"] == {"passed": 1, "total": 1}
    assert result["problems"][0]["hidden"] == {"passed": 1, "total": 1}
    assert result["score"] == 1.0
