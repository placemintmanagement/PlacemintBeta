"""Grading infra-failure handling, canary-based rework (2026-10): verifies
that an infrastructure_error (the sandbox itself failing to run candidate
code -- never the candidate's fault) is confirmed with a trivial
known-good "canary" program before anything is ever scored, and that a
student is never left unable to submit because of it. Covers both
layers the task named: services/code_runner.py's run_tests_with_canary_
check (the canary mechanics and classification) and server.py's
_grade_coding_section (the abort-the-whole-section-on-a-confirmed-infra-
failure behavior).

The 4 required scenarios (all using a FAKE run_code/run_canary -- no
real subprocess, no sandbox, no dependency on this machine's actual
subprocess-spawn speed):
  1. stalled machine: the canary fails twice in a row too -> grading
     stops immediately, nothing is scored.
  2. a student program that always blocks, on a healthy machine: the
     canary always passes -> every test is graded as a genuine
     time_limit_exceeded, normally, with no 503.
  3. a normal run's shape and counts are unchanged.
  4. the Windows path (no CPU-time counters at all) always defers to the
     canary rather than guessing time_limit_exceeded.

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
# Layer 1: services/code_runner -- the canary mechanics and classification
# ---------------------------------------------------------------------------

def test_windows_path_has_no_cpu_counters_and_always_defers_to_canary(monkeypatch):
    # Simulate a platform with no `resource` module at all (Windows):
    # _child_cpu_seconds() then always returns None, so _classify_timeout
    # must come back "infrastructure_error" for EVERY timeout -- there is
    # no CPU-time signal to even attempt a direct TLE verdict from, so the
    # canary becomes the sole arbiter, never an optional enhancement.
    monkeypatch.setattr(code_runner, "resource", None)
    assert code_runner._classify_timeout(cpu_before=None, timeout=5) == "infrastructure_error"
    assert code_runner._classify_timeout(cpu_before=1.0, timeout=5) == "infrastructure_error"
    assert code_runner._classify_timeout(cpu_before=4.9, timeout=5) == "infrastructure_error"


def test_stalled_machine_canary_fails_twice_aborts_immediately(monkeypatch):
    call_log = []

    def fake_run_code(language, code, stdin, timeout):
        call_log.append("run_code")
        return _result("infrastructure_error", timed_out=True)

    def fake_run_canary(language, timeout=code_runner.DEFAULT_TIMEOUT):
        call_log.append("run_canary")
        return False  # the whole machine is stalled -- canary never passes

    monkeypatch.setattr(code_runner, "run_code", fake_run_code)
    monkeypatch.setattr(code_runner, "run_canary", fake_run_canary)
    tests = [{"input": str(i), "expected_output": str(i)} for i in range(14)]
    passed, details, unresolved_infra = code_runner.run_tests_with_canary_check("python", "code", tests)
    assert unresolved_infra is True
    assert passed == 0
    # Stops after the FIRST suspicious test's canary sequence fails twice
    # -- never grinds through all 14 tests. This bounded-cost-then-abort
    # behavior is exactly what replaces the old 3x-per-test retry loop.
    assert len(details) == 1
    assert details[0]["status"] == "infrastructure_error"
    # 1 real run_code call (the suspicious test itself) + exactly 2 canary
    # calls (first try, then the one allowed retry) -- bounded, never more.
    assert call_log == ["run_code", "run_canary", "run_canary"]


def test_blocking_student_healthy_machine_is_tle_graded_normally_no_infra(monkeypatch):
    call_log = []

    def fake_run_code(language, code, stdin, timeout):
        call_log.append("run_code")
        return _result("infrastructure_error", timed_out=True)  # looks suspicious every time

    def fake_run_canary(language, timeout=code_runner.DEFAULT_TIMEOUT):
        call_log.append("run_canary")
        return True  # machine is healthy -- canary always passes immediately

    monkeypatch.setattr(code_runner, "run_code", fake_run_code)
    monkeypatch.setattr(code_runner, "run_canary", fake_run_canary)
    tests = [{"input": str(i), "expected_output": str(i)} for i in range(14)]
    passed, details, unresolved_infra = code_runner.run_tests_with_canary_check("python", "code", tests)
    assert unresolved_infra is False
    assert passed == 0
    assert len(details) == 14
    assert all(d["status"] == "time_limit_exceeded" for d in details)
    # Exactly 1 run_code + 1 run_canary per test -- no second canary call
    # and no test re-run needed, since the canary passes first try every time.
    assert call_log == ["run_code", "run_canary"] * 14


def test_transient_canary_blip_recovers_and_reruns_the_test_once(monkeypatch):
    run_code_log = []

    def fake_run_code(language, code, stdin, timeout):
        run_code_log.append(1)
        if len(run_code_log) == 1:
            return _result("infrastructure_error", timed_out=True)
        return _result("ok", stdout="42")  # the one allowed re-run succeeds

    canary_log = []

    def fake_run_canary(language, timeout=code_runner.DEFAULT_TIMEOUT):
        canary_log.append(1)
        return len(canary_log) >= 2  # fails first, passes on its own second try

    monkeypatch.setattr(code_runner, "run_code", fake_run_code)
    monkeypatch.setattr(code_runner, "run_canary", fake_run_canary)
    tests = [{"input": "x", "expected_output": "42"}]
    passed, details, unresolved_infra = code_runner.run_tests_with_canary_check("python", "code", tests)
    assert unresolved_infra is False
    assert passed == 1
    assert details[0]["status"] == "passed"
    assert run_code_log == [1, 1]  # initial run + exactly one re-run, never more
    assert canary_log == [1, 1]    # exactly two canary attempts, never more


def test_normal_pass_and_wrong_answer_unchanged(monkeypatch):
    def fake_run_code(language, code, stdin, timeout):
        return _result("ok", stdout=stdin)  # echoes stdin back as stdout

    monkeypatch.setattr(code_runner, "run_code", fake_run_code)
    tests = [
        {"input": "a", "expected_output": "a"},
        {"input": "b", "expected_output": "NOT_B"},
    ]
    passed, details, unresolved_infra = code_runner.run_tests_with_canary_check("python", "code", tests)
    assert passed == 1
    assert details[0]["status"] == "passed" and details[0]["passed"] is True
    assert details[1]["status"] == "wrong_answer" and details[1]["passed"] is False
    assert unresolved_infra is False
    # run_tests() (the plain, non-canary function) gives the identical
    # passed/status shape for the same inputs -- confirms normal-run
    # behavior is genuinely unchanged by this rework.
    passed2, details2 = code_runner.run_tests("python", "code", tests)
    assert passed2 == passed
    assert [d["status"] for d in details2] == [d["status"] for d in details]
    assert [d["passed"] for d in details2] == [d["passed"] for d in details]


def test_deadline_exceeded_aborts_like_persistent_infra(monkeypatch):
    def fake_run_code(language, code, stdin, timeout):
        return _result("ok", stdout="1")

    monkeypatch.setattr(code_runner, "run_code", fake_run_code)
    tests = [{"input": "1", "expected_output": "1"} for _ in range(5)]
    # A deadline already in the past -- the very first test should be
    # refused before even calling run_code.
    passed, details, unresolved_infra = code_runner.run_tests_with_canary_check(
        "python", "code", tests, deadline=0.0)
    assert unresolved_infra is True
    assert len(details) == 1
    assert details[0]["status"] == "infrastructure_error"


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
    def fake_run_tests_with_canary_check(language, code, tests, timeout=5, deadline=None):
        return 0, [{
            "index": 0, "status": "infrastructure_error", "passed": False,
            "input": "", "expected": "", "got": "", "error": "boom",
            "stderr": None, "timed_out": True,
        }], True

    monkeypatch.setattr(server, "_lang_run_tests_with_canary_check", fake_run_tests_with_canary_check)
    section = _section_with_one_problem()
    answers = {"p1": {"code": "print(1)", "language": "python"}}
    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(server._grade_coding_section(section, answers, use_ai_note=False))
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "grading_infra_error"


def test_grade_coding_section_tle_from_canary_scores_normally(monkeypatch):
    # From _grade_coding_section's point of view, a canary-confirmed
    # time_limit_exceeded looks exactly like any other failed test --
    # unresolved_infra comes back False, so grading proceeds normally.
    def fake_run_tests_with_canary_check(language, code, tests, timeout=5, deadline=None):
        details = [{
            "index": i, "status": "time_limit_exceeded", "passed": False,
            "input": t["input"], "expected": t["expected_output"], "got": "",
            "error": "Timed out after 5s", "stderr": None, "timed_out": True,
        } for i, t in enumerate(tests)]
        return 0, details, False

    monkeypatch.setattr(server, "_lang_run_tests_with_canary_check", fake_run_tests_with_canary_check)
    section = _section_with_one_problem()
    answers = {"p1": {"code": "while True: pass", "language": "python"}}
    result = asyncio.run(server._grade_coding_section(section, answers, use_ai_note=False))
    assert result["problems"][0]["visible"] == {"passed": 0, "total": 1}
    assert result["problems"][0]["hidden"] == {"passed": 0, "total": 1}
    assert result["score"] == 0.0


def test_grade_coding_section_normal_run_shape_unchanged(monkeypatch):
    def fake_run_tests_with_canary_check(language, code, tests, timeout=5, deadline=None):
        details = [{
            "index": i, "status": "passed", "passed": True,
            "input": t["input"], "expected": t["expected_output"], "got": t["expected_output"],
            "error": None, "stderr": None, "timed_out": False,
        } for i, t in enumerate(tests)]
        return len(tests), details, False

    monkeypatch.setattr(server, "_lang_run_tests_with_canary_check", fake_run_tests_with_canary_check)
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
