# -*- coding: utf-8 -*-
"""Commit flag-off equivalence battery for the DSA-hints feature (STAGE 2).

NOTE ON THE "37/37" FIGURE: no pre-existing battery under that name (or any
"equivalence_battery"/"37/37" marker) was found anywhere in this repo before
this file -- searched explicitly. This is a FRESH battery built for this
task; it reports its own step count honestly rather than assume a number
from outside this session's context.

What it proves: a full Commit interview, driven end-to-end with the exact
same scripted answer at every turn, produces IDENTICAL views (every key,
every value, at every single step) whether HINTS_ENABLED is off, or on but
never actually triggered (every answer here is a genuine 15+-word
substantive attempt, so the hint/answer-request/confirmation detection path
in dsa_hints.classify_dsa_message never fires for any of them) -- except
for the one additive "hints" key the flag adds once the DSA stage is
reached. That is the strongest form of "flag off changes nothing": it shows
the feature is not just gated off by default, it is INERT whenever it is
never invoked, flag on or off."""
import asyncio
import random
from types import SimpleNamespace

import server
from spark_support import _Clock, _attempt, _Coll
from commit_support import _CommitModel, COMMIT_PROJECTS, _start as commit_start, _answer as commit_answer

# 15+ words, no code markers, no hint/answer-request/confirmation phrase --
# word count alone already guarantees _looks_like_attempt() is True (see
# dsa_hints._SUBSTANTIVE_WORD_THRESHOLD), so detection never fires here
# regardless of exact wording; chosen phrasing is just a realistic answer.
SCRIPTED_ANSWER = (
    "This is a genuine, substantive, and specific answer about my own contribution to the project, the "
    "trade-off I personally weighed, and why I made that particular decision over the alternatives I "
    "considered at the time, including the complexity involved."
)


def _build_commit_world(monkeypatch):
    clock = _Clock()
    model = _CommitModel()
    fake = SimpleNamespace(interviews=_Coll(), oa_attempts=_Coll([_attempt("commit")]), reports=_Coll(),
                           resumes=_Coll([{"resume_id": "res1", "analysis": {"extracted_projects": COMMIT_PROJECTS}}]))
    monkeypatch.setattr(server, "db", fake)
    monkeypatch.setattr(server, "now_utc", clock.now)
    monkeypatch.setattr(server, "call_json_gpt", model)
    monkeypatch.setattr(server.entitlements, "free_is_oa_only", lambda user: False)
    return SimpleNamespace(db=fake, clock=clock, model=model, user={"user_id": "u1", "name": "Priya"})


def _run_full_commit_interview(w, text, max_steps=200, seed=1234):
    # The DSA problem, CS questions and HR questions are drawn via the
    # shared, process-global `random` module (not mocked/seeded by
    # commit_world), so two SEPARATE full runs in the same test process
    # must each start from the identical seed or they draw different
    # questions for reasons that have nothing to do with this feature.
    random.seed(seed)
    doc = commit_start(w)
    iid = doc["interview_id"]
    views = [doc]
    view = doc
    for _ in range(max_steps):
        if view["status"] != "in_progress":
            return views
        q = view["current_question"]
        view = commit_answer(w, iid, q["id"], text)
        views.append(view)
    raise AssertionError("commit interview did not end within max_steps")


def test_commit_flag_off_equivalence_battery_full_interview(monkeypatch):
    monkeypatch.delenv("HINTS_ENABLED", raising=False)
    w_off = _build_commit_world(monkeypatch)
    views_off = _run_full_commit_interview(w_off, SCRIPTED_ANSWER)

    monkeypatch.setenv("HINTS_ENABLED", "1")
    w_on = _build_commit_world(monkeypatch)
    views_on = _run_full_commit_interview(w_on, SCRIPTED_ANSWER)

    assert len(views_off) == len(views_on), (
        f"the interview took a different number of turns to finish: "
        f"{len(views_off)} (flag off) vs {len(views_on)} (flag on, never triggered)"
    )

    # "interview_id" is a fresh random id (new_id()) each run, independent
    # of the seeded `random` module -- excluded here for the same reason
    # "hints" is: it is EXPECTED to differ, not a sign of a behaviour change.
    _IGNORED_KEYS = {"hints", "interview_id"}

    mismatches = []
    for i, (vo, vn) in enumerate(zip(views_off, views_on)):
        vo_sans_hints = {k: v for k, v in vo.items() if k not in _IGNORED_KEYS}
        vn_sans_hints = {k: v for k, v in vn.items() if k not in _IGNORED_KEYS}
        if vo_sans_hints != vn_sans_hints:
            mismatches.append(i)

    total = len(views_off)
    identical = total - len(mismatches)
    print(f"\nCommit flag-off equivalence battery: {identical}/{total} steps identical "
          f"(excluding the one additive 'hints' key the flag adds).")
    assert mismatches == [], f"views differed (beyond the additive 'hints' key) at steps: {mismatches}"

    # The ONLY observable difference anywhere: "hints" is never present when
    # the flag is off, and IS present (once the DSA stage is reached) when
    # the flag is on -- confirming the additive key is the sole delta.
    assert all("hints" not in v for v in views_off)
    assert any("hints" in v for v in views_on)


def test_commit_score_and_report_are_byte_identical_flag_on_but_never_triggered(monkeypatch):
    """The stored document's own commit_score and answers (the report
    source) must be identical too, not just the client-facing view --
    hints_used stays 0 throughout (never triggered), so the penalty
    multiplier is never applied regardless of the flag."""
    monkeypatch.delenv("HINTS_ENABLED", raising=False)
    w_off = _build_commit_world(monkeypatch)
    _run_full_commit_interview(w_off, SCRIPTED_ANSWER)
    stored_off = next(d for d in w_off.db.interviews.docs)

    monkeypatch.setenv("HINTS_ENABLED", "1")
    w_on = _build_commit_world(monkeypatch)
    _run_full_commit_interview(w_on, SCRIPTED_ANSWER)
    stored_on = next(d for d in w_on.db.interviews.docs)

    assert stored_off["commit_score"] == stored_on["commit_score"]
    assert stored_off["answers"] == stored_on["answers"]
    assert stored_on.get("hints_used", 0) == 0
