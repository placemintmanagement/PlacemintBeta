"""Session-wide safety net: a plain `pytest` run must make ZERO real OpenAI
calls. There are exactly two live bindings of call_json_gpt in the codebase
(server.py's own `from services.ai_service import call_json_gpt`, and
capgemini_recruitment_process.py's identical import -- see the OpenAI-spend
audit) -- every other OpenAI-reaching function in server.py calls through
one of those two names. This file does not touch services/ai_service.py
itself or any production call path; it only stubs the two already-imported
names for the duration of a test, the same thing commit_world/dave_world/
spark_world already do per-test (tests/commit_support.py etc.) -- this just
makes that the DEFAULT for every test, not an opt-in per fixture.

Tests that genuinely need the real API: mark them @pytest.mark.live. They
are skipped unless RUN_LIVE_TESTS=1 (pytest_collection_modifyitems below),
and are exempt from the stub below (so they hit the real client).
"""
import os

import pytest

import server


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "live: hits the real OpenAI API; skipped unless RUN_LIVE_TESTS=1"
    )


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUN_LIVE_TESTS") == "1":
        return
    skip_live = pytest.mark.skip(reason="needs RUN_LIVE_TESTS=1 (hits the real OpenAI API)")
    for item in items:
        if item.get_closest_marker("live"):
            item.add_marker(skip_live)


async def _blocked_call_json_gpt(*args, **kwargs):
    raise RuntimeError(
        "A real OpenAI call was attempted during a pytest run that is not "
        "marked @pytest.mark.live. Mock call_json_gpt (see the commit_world/"
        "dave_world/spark_world pattern in tests/commit_support.py, "
        "dave_support.py, spark_support.py) or mark the test @pytest.mark.live "
        "and run with RUN_LIVE_TESTS=1."
    )


@pytest.fixture(autouse=True)
def _no_real_openai_calls_by_default(request, monkeypatch):
    if request.node.get_closest_marker("live"):
        return
    monkeypatch.setattr(server, "call_json_gpt", _blocked_call_json_gpt)
    monkeypatch.setattr(server.capgemini_recruitment_process, "call_json_gpt", _blocked_call_json_gpt)
