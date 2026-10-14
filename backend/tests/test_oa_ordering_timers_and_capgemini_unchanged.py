"""Three things requested for the TCS Part-B work, that are about the shared
OA engine rather than TCS specifically:

1. Whether Foundation-style sections are actually non-reorderable and
   actually have a server-enforced timer TODAY. These are written as
   strict xfail probes, not passing tests, because direct experimentation
   (see the probe in this file) shows NEITHER property currently holds for
   ANY company's submit_section flow -- this predates the TCS work and is
   not something this session's diff introduced or touched. Marking them
   xfail(strict=True) keeps this gap visible in test output (as XFAIL, not
   a silent pass) rather than asserting the current, unenforced behavior
   as if it were the desired spec.
2. That the client cannot set or influence tcs_tier via the normal
   submit_section completion path (finish-part-a's equivalent is covered in
   test_tcs_finish_part_a.py).
3. That the Capgemini OA flow is byte-for-byte unchanged by this session's
   diff -- proven directly against git HEAD, not just by inspection.
"""
import asyncio
import json
import subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException

import server
from services import capgemini_tiers, tcs_tiers

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


class _FakeOAAttempts:
    def __init__(self, docs):
        self.docs = {d["attempt_id"]: d for d in docs}
        self.update_calls = []

    async def find_one(self, query, projection=None):
        doc = self.docs.get(query.get("attempt_id"))
        if doc is None:
            return None
        if "user_id" in query and doc.get("user_id") != query["user_id"]:
            return None
        return json.loads(json.dumps(doc))

    async def update_one(self, query, update):
        aid = query["attempt_id"]
        self.update_calls.append(update["$set"])
        self.docs[aid] = {**self.docs[aid], **update["$set"]}


class _FakeDb:
    def __init__(self, docs):
        self.oa_attempts = _FakeOAAttempts(docs)


def _tcs_sections():
    return [
        {"key": "numerical", "type": "mcq", "questions": []},
        {"key": "verbal", "type": "mcq", "questions": []},
        {"key": "reasoning", "type": "mcq", "questions": []},
        {"key": "advanced", "type": "mcq", "optional": True, "questions": []},
        {"key": "coding", "type": "coding", "optional": True, "questions": []},
    ]


def _attempt(current_section_index=0, company_id="tcs-nqt", section_results=None, extra=None):
    doc = {
        "attempt_id": "a1", "user_id": "u1", "company_id": company_id,
        "status": "in_progress", "sections": _tcs_sections(),
        "section_results": section_results or {}, "answers": {},
        "current_section_index": current_section_index,
    }
    if extra:
        doc.update(extra)
    return doc


# ---- 1. Ordering / timers: current, real behavior -- marked xfail(strict) --

@pytest.mark.xfail(
    strict=True,
    reason=(
        "GAP (pre-existing, not TCS-specific): submit_section looks up the "
        "target section by body.section_key via `next(s for s in "
        "attempt['sections'] if s['key'] == body.section_key)`, not by "
        "position, and then unconditionally advances current_section_index "
        "by 1 regardless of which key was actually submitted. There is no "
        "check anywhere that body.section_key == "
        "attempt['sections'][current_section_index]['key']. Today a client "
        "CAN submit 'reasoning' (Foundation's 3rd section) while "
        "current_section_index is still 0 ('numerical'), and the server "
        "accepts and grades it. Decision #5 wants Foundation to be "
        "non-reorderable server-side; this is the gap that would need "
        "closing to make that true -- flagged here rather than silently "
        "patched into the shared 14-company submit_section endpoint."
    ),
)
def test_foundation_sections_are_not_yet_reorder_blocked_server_side(monkeypatch):
    fake = _FakeDb([_attempt(current_section_index=0)])  # should still be on "numerical"
    server.db = fake
    monkeypatch.setattr(
        server, "_grade_mcq_like",
        lambda section, answers: {"score": 1.0, "correct": 1, "total": 1, "passed": True},
    )
    body = server.SubmitSectionIn(section_key="reasoning", answers={})  # out of order
    with pytest.raises(HTTPException):
        # Desired behavior: the server should REJECT this (409/400). Today
        # it does not raise at all -- it grades "reasoning" and advances the
        # index -- so this assertion currently fails, which is the point.
        asyncio.run(server.submit_section("a1", body, user={"user_id": "u1"}))


@pytest.mark.xfail(
    strict=True,
    reason=(
        "GAP (pre-existing, not TCS-specific): no oa_attempts document ever "
        "stores a per-section (or per-attempt) start timestamp or deadline "
        "anywhere in server.py -- grepped repo-wide, zero hits for "
        "started_at/deadline_at/expires_at on the generic OA 'sections' "
        "flow (those fields exist only for the separate Capgemini interview "
        "state machine, a different code path entirely). submit_section "
        "accepts a submission at any wall-clock time with no late check. "
        "Decision #5 wants Foundation's timers 'enforced on the server'; "
        "this is what's missing to make that true."
    ),
)
def test_oa_attempts_have_no_server_tracked_section_deadline_today():
    fake = _FakeDb([_attempt()])
    server.db = fake
    stored = asyncio.run(server.db.oa_attempts.find_one({"attempt_id": "a1", "user_id": "u1"}))
    # Desired: some server-computed deadline for the in-progress section.
    assert any(k for k in stored if "deadline" in k or "started_at" in k)


# ---- 2. Client cannot set/influence tcs_tier via normal submit_section -----

def test_submit_section_in_has_no_tier_or_track_field():
    import inspect
    fields = set(server.SubmitSectionIn.model_fields.keys())
    assert fields == {"section_key", "answers"}, (
        f"SubmitSectionIn grew a new field {fields - {'section_key', 'answers'}} -- "
        "if that's tier/track-shaped, re-audit for client-controlled tier input."
    )


def test_submit_section_overwrites_a_preexisting_stale_tcs_tier_on_final_section(monkeypatch):
    # Reach "completed" via the NORMAL sequential path (current_section_index
    # points at the last section, "coding") with a stale/tampered tcs_tier
    # of "prime" already sitting on the doc, and weak coding/advanced scores
    # that should only clear "ninja". The final computed tier must come from
    # section_results alone, not the pre-existing stored value.
    stale = {"tier": "prime", "lpa": tcs_tiers.TCS_LPA["prime"], "part_b_attempted": True}
    section_results = {
        "numerical": {"score": 1.0, "correct": 20, "total": 20},
        "verbal": {"score": 1.0, "correct": 25, "total": 25},
        "reasoning": {"score": 1.0, "correct": 20, "total": 20},
        "advanced": {"score": 0.0, "correct": 0, "total": 15},
    }
    fake = _FakeDb([_attempt(current_section_index=4, section_results=section_results, extra={"tcs_tier": stale})])
    server.db = fake
    monkeypatch.setattr(server, "_grade_coding_section", _async_return({"score": 0.0}))
    body = server.SubmitSectionIn(section_key="coding", answers={})
    response = asyncio.run(server.submit_section("a1", body, user={"user_id": "u1"}))
    assert response["tcs_tier"]["tier"] == "ninja"
    assert fake.oa_attempts.docs["a1"]["tcs_tier"]["tier"] == "ninja"
    assert fake.oa_attempts.docs["a1"]["tcs_tier"]["part_b_attempted"] is True


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value
    return _inner


# ---- 3. Capgemini OA flow: byte-for-byte unchanged, proven against HEAD ----

def _git_show(path: str) -> str:
    # encoding="utf-8" explicitly -- text=True alone defaults to the
    # platform's locale codec (cp1252 on Windows), which chokes on some of
    # these files' non-ASCII bytes (e.g. unicode en-dashes).
    return subprocess.check_output(
        ["git", "show", f"HEAD:{path}"], cwd=REPO_ROOT, encoding="utf-8",
    )


@pytest.mark.parametrize("rel_path", [
    "backend/services/capgemini_tiers.py",
    "backend/departments/computer_science_and_it/group1_it_services_mass_recruiters/capgemini/capgemini_recruitment_process.py",
    "backend/departments/computer_science_and_it/group1_it_services_mass_recruiters/capgemini/capgemini_interview/dave/dsa.py",
    "backend/departments/computer_science_and_it/group1_it_services_mass_recruiters/capgemini/capgemini_interview/spark/dsa.py",
    "backend/departments/computer_science_and_it/group1_it_services_mass_recruiters/capgemini/capgemini_interview/core.py",
])
def test_capgemini_files_are_byte_identical_to_head(rel_path):
    head_src = _git_show(rel_path)
    live_src = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
    assert head_src == live_src, f"{rel_path} differs from HEAD -- this session's diff must not touch Capgemini."


def test_server_py_capgemini_branches_present_unchanged_in_live_diff():
    # server.py itself DID change (new TCS imports/wiring), so a whole-file
    # byte-diff isn't the right check here -- instead confirm the specific
    # Capgemini-tier lines survive byte-for-byte inside the live file.
    live_src = (BACKEND_DIR / "server.py").read_text(encoding="utf-8")
    for must_contain in (
        'if doc.get("capgemini_tier"):\n        doc["capgemini_tier"] = capgemini_tiers.client_view(doc["capgemini_tier"])',
        'if status == "completed" and attempt.get("company_id") == "capgemini":\n        tier_eval = capgemini_tiers.evaluate(section_results)',
        'if tier_eval is not None:\n        update["capgemini_tier"] = {**tier_eval, "computed_at": iso(now_utc())}',
        'if tier_eval is not None:\n        response["capgemini_tier"] = {"tier": tier_eval["tier"], "lpa": tier_eval["lpa"]}',
    ):
        assert must_contain in live_src, "A Capgemini-tier line in server.py was altered or removed."


def test_capgemini_oa_flow_end_to_end_tier_unaffected_by_tcs_changes(monkeypatch):
    # Before/after comparison using the LIVE evaluate() against a fixed
    # section_results, matching test_capgemini_views.py's own fixture shape --
    # if this diff had perturbed capgemini_tiers.py or its call site, this
    # would drift from the known "dave"/5.75 result that test already locks in.
    section_results = {
        "ai_literacy": {"score": 0.0, "correct": 16, "total": 20, "passed": True},
        "technical_assessment": {"score": 0.0, "correct": 15, "total": 20, "passed": True},
        "round3_debugging": {"score": 0.7, "passed": True},
        "round4_ai_assisted": {
            "score": 0.6, "passed": True,
            "components": {"self_review_correct": 1.0, "bug_explanation_quality": 0.9, "stage_efficiency": 0.2},
        },
        "round5_cognitive": {"score": 0.7, "passed": True},
    }
    result = capgemini_tiers.evaluate(section_results)
    assert result["tier"] == "dave"
    assert result["lpa"] == 5.75
