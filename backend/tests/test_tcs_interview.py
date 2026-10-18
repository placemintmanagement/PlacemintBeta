"""TCS NQT interview: end-to-end coverage through the real route-handler-
equivalent call path (server.start_interview / submit_interview_answer /
get_interview / interview_report), with TCS_INTERVIEW_ENABLED turned on via
the tcs_world fixture (tests/tcs_support.py) and the AI boundary faked
(call_json_gpt stubbed; call_json stubbed per-test for the report step).
No real Mongo, no network, no live AI call anywhere in this file.

REWRITE (part 1 of the 4-part TCS restructure): the old TR/MR/HR
three-stage model is gone. Every tier now has a SINGLE "interview" stage
with an ordered list of phases (core.TCS_TIER_PHASE_ORDER):
  ninja:   project -> coding -> core
  digital: project -> architecture -> coding -> puzzle -> core
  prime:   project -> architecture -> coding -> puzzle -> core

Covers: a full deterministic run for each of the three tiers reaching a
final report; the new phase order/weights/durations; flag-OFF behaviour
byte-identical to the pre-existing blocked response; resume-required
before a TCS interview can start; tier_source; the 409 double-start guard;
the report route; the budget-protection guarantee for the LAST phase
(core); and the rolling-context prompt-size-bounded guarantee for long
Digital/Prime sittings.
"""
import asyncio

import pytest
from fastapi import HTTPException

import server
from departments.computer_science_and_it.group1_it_services_mass_recruiters.tcs.tcs_interview import core
from departments.computer_science_and_it.group1_it_services_mass_recruiters.tcs.tcs_interview import orchestration
from tcs_support import (  # noqa: F401
    TCS_PROJECTS, TCS_PROJECTS_SINGLE_LANGUAGE, _answer, _get, _run_to_end, _start, _stored, _tcs_attempt, tcs_world,
)

TCS_DURATION_SECONDS = {"ninja": 30 * 60, "digital": 60 * 60, "prime": 60 * 60}  # USER-STATED


# ---- full deterministic end-to-end run, one per tier -----------------------

@pytest.mark.parametrize("tier", ["ninja", "digital", "prime"])
def test_full_tcs_interview_reaches_a_final_report(tcs_world, monkeypatch, tier):
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    assert started["mode"] == "tcs"
    assert started["stage"] == "interview"
    assert started["phase"] == "project"
    assert started["status"] == "in_progress"

    steps = _run_to_end(tcs_world, iid)
    assert steps[-1]["status"] == "completed"
    assert steps[-1]["phase"] == "done"
    assert steps[-1]["closing_message"]

    stored = _stored(tcs_world, iid)
    assert stored["tier"] == tier
    assert stored["status"] == "completed"
    assert stored["tcs_score"]["interview"] >= 0.0
    assert set(stored["tcs_score"]["phases"]) == set(core.TCS_TIER_PHASE_ORDER[tier])
    assert len(stored["answers"]) == len(stored["turns"])
    # Never leaks grading internals to the client view at any step.
    for step in steps:
        assert "flags" not in step and "key_points" not in step and "tcs_score" not in step

    captured = []
    report = _report_by_interview_id(tcs_world, iid, monkeypatch, captured)
    assert report["interview_summary"]["completed"] is True
    assert report["interview_summary"]["skipped"] is False
    assert report["interview_summary"]["avg_score"] > 0
    assert captured[0]["oa_summary"] == {"skipped": True}  # no OA attempt behind this interview
    assert report["tier"] == tier
    assert report["tier_source"] == "chosen"


@pytest.mark.parametrize("tier,expected_phases", [
    ("ninja", ["project", "coding", "core"]),
    ("digital", ["project", "architecture", "coding", "puzzle", "core"]),
    ("prime", ["project", "architecture", "coding", "puzzle", "core"]),
])
def test_phase_order_matches_the_tier_config(tcs_world, tier, expected_phases):
    """USER-STATED phase order, per tier -- Ninja has NO architecture and NO
    puzzle phase at all."""
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    assert [p["phase"] for p in started["phases"]] == expected_phases
    assert core.TCS_TIER_PHASE_ORDER[tier] == expected_phases


def test_ninja_never_sees_an_architecture_or_puzzle_phase(tcs_world):
    started = _start(tcs_world, company_id="tcs-nqt", tier="ninja")
    iid = started["interview_id"]
    steps = _run_to_end(tcs_world, iid)
    phases_seen = {s["phase"] for s in steps if s["phase"] != "done"}
    phases_seen |= {started["phase"]}
    assert "architecture" not in phases_seen
    assert "puzzle" not in phases_seen
    stored = _stored(tcs_world, iid)
    assert "architecture" not in stored["phase_questions"]
    assert "puzzle" not in stored["phase_questions"]


@pytest.mark.parametrize("tier", ["digital", "prime"])
def test_digital_and_prime_see_architecture_right_after_project(tcs_world, tier):
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    phases = [p["phase"] for p in started["phases"]]
    assert phases.index("architecture") == phases.index("project") + 1


def test_core_phase_is_always_last(tcs_world):
    for tier in core.TCS_INTERVIEW_TIERS:
        assert core.TCS_TIER_PHASE_ORDER[tier][-1] == "core"


# ---- durations (USER-STATED) ------------------------------------------------

@pytest.mark.parametrize("tier,minutes", [("ninja", 30), ("digital", 60), ("prime", 60)])
def test_tier_durations_match_user_stated_minutes(tcs_world, tier, minutes):
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    assert started["deadline_epoch"] - started["server_now_epoch"] == minutes * 60
    assert core.TCS_TIER_DURATION_SECONDS[tier] == minutes * 60


# ---- weight/budget invariants (OUR ESTIMATE; safety net) ------------------

def test_phase_weights_sum_to_one_per_tier():
    for tier, weights in core.TCS_PHASE_WEIGHTS.items():
        assert round(sum(weights.values()), 6) == 1.0


def test_core_submix_sums_to_one_per_tier():
    for tier, submix in core.TCS_CORE_SUBMIX.items():
        assert round(sum(submix.values()), 6) == 1.0


def test_phase_minutes_sum_to_the_tier_total_duration():
    for tier, budgets in core.TCS_PHASE_BUDGETS.items():
        total_minutes = sum(b["minutes"] for b in budgets.values())
        assert total_minutes * 60 == core.TCS_TIER_DURATION_SECONDS[tier]


# ---- budget protection: core (last phase) is never shortchanged -----------

def test_core_phase_question_count_is_independent_of_earlier_phase_overrun():
    """build_phase_questions selects every phase's question list
    independently (no shared pool) -- so even if an earlier phase's list
    were artificially inflated (simulating an "overrun"), core's own list
    is completely unaffected, still >= its configured min_questions. This
    is the structural guarantee that makes core.py's "protect the last
    phase's budget" promise hold."""
    rng_a = __import__("random").Random(1)
    rng_b = __import__("random").Random(1)
    project = {"name": "P", "tech_stack": "Python", "one_line_summary": "x"}
    for tier in core.TCS_INTERVIEW_TIERS:
        normal = core.build_phase_questions(tier, TCS_PROJECTS, project, rng_a)
        core_len_normal = len(normal["core"])
        assert core_len_normal >= core.TCS_PHASE_BUDGETS[tier]["core"]["min_questions"]

        inflated = core.build_phase_questions(tier, TCS_PROJECTS, project, rng_b)
        inflated["project"] = inflated["project"] * 20  # simulate an earlier phase "overrunning"
        inflated["coding"] = inflated["coding"] * 20
        assert len(inflated["core"]) == core_len_normal, (
            "an earlier phase's inflated question list must never change core's own, independently-"
            "selected question count"
        )


def test_advance_never_skips_into_core_early_only_protects_non_last_phases(tcs_world):
    """The time-based overrun-skip in core.advance() only ever applies to
    NON-last phases (it needs a "next phase" to skip into) -- core, being
    last for every tier, is never truncated this way. Drive a real digital
    interview and force the clock far past the architecture phase's own
    minute budget after its minimum question count is met; architecture
    should be skipped early (protecting time for what follows), while core
    (reached later) still gets its full pre-selected list, un-shortened."""
    started = _start(tcs_world, company_id="tcs-nqt", tier="digital")
    iid = started["interview_id"]
    stored = _stored(tcs_world, iid)
    core_len_at_start = len(stored["phase_questions"]["core"])

    # Project phase (1 question, min_questions=1): answer it, then jump the
    # clock forward well past architecture's own 8-minute budget BEFORE
    # architecture's one question is answered, to exercise the overrun
    # check the moment architecture's minimum is met.
    view = _answer(tcs_world, iid, started["current_question"]["id"], "An answer about my project.")
    assert view["phase"] == "architecture"
    tcs_world.clock.t += 20 * 60  # 20 minutes >> architecture's 8-minute budget
    view = _answer(tcs_world, iid, view["current_question"]["id"], "An answer about the architecture.")
    assert view["phase"] == "coding"  # architecture's only question was its minimum -- moved on immediately anyway

    # Whatever happens upstream, core's own pre-selected list must still be
    # exactly what was chosen at start time.
    stored_again = _stored(tcs_world, iid)
    assert len(stored_again["phase_questions"]["core"]) == core_len_at_start


def test_advance_skips_remaining_optional_questions_once_a_non_last_phase_overruns():
    """Direct unit test of core.advance()'s overrun-skip branch itself
    (none of today's banks ever select MORE than a phase's min_questions,
    so the end-to-end tests above never exercise this branch for real --
    this constructs a synthetic phase with 3 questions, 2 more than its
    real min_questions=1, to prove the mechanism works when it matters):
    once architecture (a non-last phase) has met its min_questions AND run
    longer than its minutes budget, advance() skips its remaining optional
    questions and moves to the next phase immediately."""
    tier = "digital"
    phase_order = core.TCS_TIER_PHASE_ORDER[tier]
    phase_questions = {
        p: [{"id": f"{p}-{i}", "phase": p, "text": f"{p} q{i}"} for i in range(3 if p == "architecture" else 1)]
        for p in phase_order
    }
    state = {"stage": "interview", "phase": "architecture", "status": "in_progress", "timed_out": False,
             "started_at": 0.0, "deadline_at": 9999.0, "phase_started_at": {"architecture": 0.0}, "index": 0}
    nxt = core.advance(tier, phase_questions, state, now=9 * 60)  # 9 min > architecture's 8-minute budget
    assert nxt["phase"] == "coding", "architecture's 2 remaining optional questions should have been skipped"


def test_advance_never_applies_the_overrun_skip_to_the_last_phase():
    """Same synthetic setup, but on "core" (always the LAST phase for
    every tier): even with extra questions beyond its min_questions, and
    even far past its minutes budget, advance() must NOT skip ahead --
    there is nothing after core to protect by skipping, so its own
    pre-selected list is always delivered in full."""
    tier = "digital"
    phase_order = core.TCS_TIER_PHASE_ORDER[tier]
    phase_questions = {
        p: [{"id": f"{p}-{i}", "phase": p, "text": f"{p} q{i}"} for i in range(8 if p == "core" else 1)]
        for p in phase_order
    }
    state = {"stage": "interview", "phase": "core", "status": "in_progress", "timed_out": False,
             "started_at": 0.0, "deadline_at": 9999.0, "phase_started_at": {"core": 0.0}, "index": 4}
    # index=4 means 5 of core's 8 questions already asked (its min_questions=5 is already met).
    nxt = core.advance(tier, phase_questions, state, now=1000 * 60)  # wildly past the 18-minute budget
    assert nxt is not None and nxt["phase"] == "core" and nxt["id"] == "core-5", (
        "core, being the last phase, must never be cut short by the overrun-skip mechanism"
    )


# ---- rolling per-phase summary: prompt size stays bounded ------------------

def test_rolling_context_size_is_bounded_as_the_sitting_grows():
    """Simulate a growing number of turns within one phase and confirm the
    constructed context string does not grow past a fixed, checkable
    bound -- the whole point of NOT resending the full transcript on every
    AI call during a 60-minute Digital/Prime sitting."""
    def make_interview(n_turns):
        # Fixed-width content per turn (i zero-padded) so turn text length
        # never varies with the turn's index -- only the RECENT-TURNS CAP
        # should bound context size here, not incidental digit-count growth.
        turns = [
            {"phase": "core", "question": f"Question number {i:04d} " * 5, "verdict": f"Verdict {i:04d} " * 5,
             "topic": "oop", "flags": {"key_point_0": True}}
            for i in range(n_turns)
        ]
        return {
            "state": {"phase": "core"},
            "turns": turns,
            "phase_summaries": {"project": "project: 1 question(s) answered, avg content score 100%."},
        }

    sizes = []
    for n in (3, 10, 50, 500):
        ctx = orchestration._rolling_context(make_interview(n))
        sizes.append(len(ctx))

    # Past the recent-turns cap (3), adding more turns to the SAME phase
    # must not grow the context at all.
    assert sizes[1] == sizes[2] == sizes[3], f"context size grew unboundedly: {sizes}"
    # And it must stay well under a generous fixed cap regardless of how
    # many turns the sitting has actually taken.
    assert sizes[-1] < 2000


def test_rolling_context_includes_finished_phase_summaries_not_their_turns():
    interview = {
        "state": {"phase": "coding"},
        "turns": [
            {"phase": "project", "question": "Q1", "verdict": "V1", "topic": "project", "flags": {}},
            {"phase": "coding", "question": "Q2", "verdict": "V2", "topic": "coding_discussion", "flags": {}},
        ],
        "phase_summaries": {"project": "project: 1 question(s) answered, avg content score 100%."},
    }
    ctx = orchestration._rolling_context(interview)
    assert "project: 1 question(s) answered" in ctx
    assert "Q1" not in ctx  # the finished phase's own turn text is gone, only its summary line remains
    assert "Q2" in ctx  # the CURRENT phase's own recent turn is still included


# ---- flag OFF: byte-identical to the pre-existing blocked response --------

def test_flag_off_tcs_interview_start_is_blocked_exactly_as_before(monkeypatch):
    """TCS_INTERVIEW_ENABLED unset (the default) -- same exact
    {"code": "interview_not_available", "message": "This company does not
    have an interview phase yet."} / 400 contract that
    test_interview_oa_independence.py's test_tcs_company_id_start_has_no_
    interview_phase already pins (that test never sets the flag either),
    confirmed again here directly against the exact response shape."""
    monkeypatch.delenv("TCS_INTERVIEW_ENABLED", raising=False)
    from types import SimpleNamespace
    from spark_support import _Coll
    fake = SimpleNamespace(interviews=_Coll(), oa_attempts=_Coll(), reports=_Coll(), resumes=_Coll())
    monkeypatch.setattr(server, "db", fake)
    monkeypatch.setattr(server.entitlements, "free_is_oa_only", lambda user: False)
    body = server.StartInterviewIn(company_id="tcs-nqt", tier="ninja")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, {"user_id": "u1", "name": "Priya"}))
    assert exc.value.status_code == 400
    assert exc.value.detail == {
        "code": "interview_not_available",
        "message": "This company does not have an interview phase yet.",
    }


def test_flag_off_valid_interview_tiers_and_tier_start_fn_are_also_unchanged():
    """Direct unit check on the two helpers hook 2/hook 3 extended --
    with the flag off, both behave exactly as they did before TCS had any
    interview branch at all."""
    import os
    assert os.environ.get("TCS_INTERVIEW_ENABLED") in (None, "", "0", "false")
    assert server._valid_interview_tiers("tcs-nqt") == []
    assert server._tier_start_fn("tcs-nqt", "ninja") is None


# ---- hub-only guard: attempt_id path is broken for TCS, always blocked ----

def test_tcs_attempt_id_start_is_blocked_hub_only_when_flag_is_on(tcs_world):
    """With TCS_INTERVIEW_ENABLED on, "tcs-nqt" is no longer in
    _no_interview_company_ids(), so the attempt_id path (tcs_world's
    fixture already seeds one OA attempt, attempt_id="att1", via
    tcs_support._tcs_attempt()) would otherwise fall through
    _tier_start_fn (tier resolves to None off attempt.capgemini_tier,
    which a TCS attempt never has) into the WRONG generic AI-planned
    interview flow. The new guard in server.start_interview blocks this
    before any of that, with a TCS-specific error distinct from the
    generic interview_not_available."""
    body = server.StartInterviewIn(attempt_id="att1")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, tcs_world.user))
    assert exc.value.status_code == 400
    assert exc.value.detail == {
        "code": "tcs_interview_hub_only",
        "message": "TCS NQT interviews must be started from the hub by choosing a tier -- "
                   "not from a completed OA attempt.",
    }


def test_tcs_attempt_id_guard_does_not_affect_the_company_id_tier_path(tcs_world):
    """The SAME flag-on world, started the normal (hub) way, is completely
    unaffected by the new guard -- it only looks at the attempt_id path."""
    started = _start(tcs_world, company_id="tcs-nqt", tier="digital")
    assert started["mode"] == "tcs"
    assert started["tier"] == "digital"
    assert started["status"] == "in_progress"


def test_tcs_attempt_id_start_flag_off_is_still_interview_not_available_not_hub_only(monkeypatch):
    """Flag OFF: "tcs-nqt" is still in _no_interview_company_ids(), so that
    earlier check raises its own generic error FIRST -- the new hub-only
    guard is never reached, and this exact response is byte-identical to
    before this guard existed (see also
    tests/test_interview_oa_independence.py's
    test_tcs_attempt_id_start_is_also_blocked, which pins the same thing)."""
    monkeypatch.delenv("TCS_INTERVIEW_ENABLED", raising=False)
    from types import SimpleNamespace
    from spark_support import _Coll
    fake = SimpleNamespace(
        interviews=_Coll(), reports=_Coll(), resumes=_Coll(),
        oa_attempts=_Coll([{"attempt_id": "a1", "user_id": "u1", "company_id": "tcs-nqt",
                            "status": "completed"}]),
    )
    monkeypatch.setattr(server, "db", fake)
    monkeypatch.setattr(server.entitlements, "free_is_oa_only", lambda user: False)
    body = server.StartInterviewIn(attempt_id="a1")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, {"user_id": "u1", "name": "Priya"}))
    assert exc.value.status_code == 400
    assert exc.value.detail == {
        "code": "interview_not_available",
        "message": "This company does not have an interview phase yet.",
    }


# ---- resume required before a TCS interview can start ----------------------

def test_resume_required_before_a_tcs_interview_can_start(tcs_world):
    tcs_world.db.resumes.docs.clear()  # no resume on file for this user+company
    body = server.StartInterviewIn(company_id="tcs-nqt", tier="ninja")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, tcs_world.user))
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "resume_required"


# ---- tier_source: oa_designated vs chosen, student's free choice ----------

def test_use_designated_true_produces_the_oa_designated_tier(tcs_world):
    tcs_world.db.oa_attempts.docs.append({
        "attempt_id": "att-oa-1", "user_id": "u1", "company_id": "tcs-nqt",
        "tcs_tier": {"tier": "digital"},
    })
    started = _start(tcs_world, company_id="tcs-nqt", use_designated=True)
    assert started["tier"] == "digital"
    assert started["tier_source"] == "oa_designated"


def test_explicit_tier_choice_is_not_gated_by_the_oa_result(tcs_world):
    """The OA designated 'ninja', but the student is free to choose any of
    the three tiers regardless -- same permissiveness Capgemini already has
    for an explicit tier= with use_designated=false."""
    tcs_world.db.oa_attempts.docs.append({
        "attempt_id": "att-oa-1", "user_id": "u1", "company_id": "tcs-nqt",
        "tcs_tier": {"tier": "ninja"},
    })
    started = _start(tcs_world, company_id="tcs-nqt", tier="prime")
    assert started["tier"] == "prime"
    assert started["tier_source"] == "chosen"


def test_unknown_tier_is_rejected(tcs_world):
    body = server.StartInterviewIn(company_id="tcs-nqt", tier="not-a-real-tier")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, tcs_world.user))
    assert exc.value.detail["code"] == "unknown_tier"


# ---- 409 in-progress guard --------------------------------------------------

def test_409_starting_a_second_tcs_interview_while_one_is_in_progress(tcs_world):
    _start(tcs_world, company_id="tcs-nqt", tier="ninja")
    body = server.StartInterviewIn(company_id="tcs-nqt", tier="digital")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_interview(body, tcs_world.user))
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "interview_already_in_progress"


# ---- report route (builds on the earlier report-cache gate fix) ------------

def _fake_final_report_call_json(monkeypatch, captured=None):
    async def fake_call_json(system, prompt, **kwargs):
        return {"overall_verdict": "borderline", "overall_score": 55, "narrative": "n",
                "weakest_dimension": "", "strongest_dimension": "", "next_steps": []}
    monkeypatch.setattr(server, "call_json", fake_call_json)

    if captured is not None:
        real = server.final_report_prompt

        def spy(company, resume_analysis, oa_summary, interview_summary):
            captured.append({"company": company, "oa_summary": oa_summary, "interview_summary": interview_summary})
            return real(company, resume_analysis, oa_summary, interview_summary)

        monkeypatch.setattr(server, "final_report_prompt", spy)


def _report_by_interview_id(w, iid, monkeypatch, captured=None):
    _fake_final_report_call_json(monkeypatch, captured)
    return asyncio.run(server.interview_report(iid, w.user))


def test_report_is_not_cached_while_the_tcs_interview_is_open(tcs_world, monkeypatch):
    tcs_world.db.reports.docs.append({
        "interview_id": "will-not-match", "user_id": "u1",
        "report": {"stale": True}, "interview_summary": {"skipped": True},
    })
    started = _start(tcs_world, company_id="tcs-nqt", tier="ninja")
    iid = started["interview_id"]
    _answer(tcs_world, iid, started["current_question"]["id"], "A thoughtful, specific first answer.")

    captured = []
    report = _report_by_interview_id(tcs_world, iid, monkeypatch, captured)

    assert captured[0]["interview_summary"]["skipped"] is False
    assert captured[0]["interview_summary"]["completed"] is False
    assert report.get("report", {}).get("stale") is None
    assert _stored(tcs_world, iid)["status"] == "in_progress"
    matching_cache = [d for d in tcs_world.db.reports.docs if d.get("interview_id") == iid]
    assert matching_cache == []  # nothing cached for THIS interview while it's open


def test_report_route_closes_an_abandoned_tcs_interview_and_caches_the_result(tcs_world, monkeypatch):
    started = _start(tcs_world, company_id="tcs-nqt", tier="ninja")
    iid = started["interview_id"]
    _answer(tcs_world, iid, started["current_question"]["id"], "Hello there.")  # then abandoned
    tcs_world.clock.t += TCS_DURATION_SECONDS["ninja"] + 1  # deadline passes; nobody reopens it
    assert _stored(tcs_world, iid)["status"] == "in_progress"  # nothing has closed it yet

    report = _report_by_interview_id(tcs_world, iid, monkeypatch)

    stored = _stored(tcs_world, iid)
    assert stored["status"] == "timed_out" and stored["state"]["timed_out"] is True
    assert stored["current_question"] is None
    assert report["interview_summary"]["completed"] is False
    matching_cache = [d for d in tcs_world.db.reports.docs if d.get("interview_id") == iid]
    assert len(matching_cache) == 1  # now cached, with the interview included


# ---- opener question: fewer than 2 inferable languages ---------------------

def test_opener_asks_directly_when_fewer_than_two_languages_are_inferable(tcs_world):
    tcs_world.db.resumes.docs[0]["analysis"]["extracted_projects"] = TCS_PROJECTS_SINGLE_LANGUAGE
    started = _start(tcs_world, company_id="tcs-nqt", tier="ninja")
    assert started["current_question"]["prompt"] == (
        "Which two programming languages would you like to be evaluated in during this interview, and why?"
    )


# ---- coding-discussion difficulty: Easy for Ninja, Medium for Digital/Prime, never Hard --

@pytest.mark.parametrize("tier,expected_difficulty", [("ninja", "easy"), ("digital", "medium"), ("prime", "medium")])
def test_coding_phase_difficulty_matches_tier(tcs_world, tier, expected_difficulty):
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    stored = _stored(tcs_world, started["interview_id"])
    coding_qs = stored["phase_questions"]["coding"]
    assert coding_qs  # never empty
    for q in coding_qs:
        assert q["difficulty"] == expected_difficulty


def test_no_tier_ever_draws_a_hard_coding_question():
    from departments.computer_science_and_it.group1_it_services_mass_recruiters.tcs.tcs_interview.banks.coding_discussion import (
        CODING_DISCUSSION_QUESTIONS,
    )
    assert all(q["difficulty"] in ("easy", "medium") for q in CODING_DISCUSSION_QUESTIONS)


# ---- puzzle phase stub (Part 1): Digital/Prime only, Ninja never calls it --

@pytest.mark.parametrize("tier", ["digital", "prime"])
def test_puzzle_stub_is_present_for_digital_and_prime(tcs_world, tier):
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    stored = _stored(tcs_world, started["interview_id"])
    assert "puzzle" in stored["phase_questions"]
    assert len(stored["phase_questions"]["puzzle"]) == 1


def test_ninja_puzzle_phase_is_never_selected_not_even_as_a_stub(tcs_world):
    rng = __import__("random").Random(1)
    calls = []

    def spy_provider(tier, rng):
        calls.append(tier)
        return core.stub_puzzle_provider(tier, rng)

    questions = core.select_puzzle_questions("ninja", rng, puzzle_provider=spy_provider)
    assert questions == []
    assert calls == []  # the provider function itself is never invoked for Ninja


# ---- core-CS submix: every tier's core draw covers all 5 sub-topics --------

@pytest.mark.parametrize("tier", ["ninja", "digital", "prime"])
def test_core_phase_covers_every_core_cs_subtopic(tcs_world, tier):
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    stored = _stored(tcs_world, started["interview_id"])
    topics = {q["topic"] for q in stored["phase_questions"]["core"]}
    assert topics == {"oop", "dbms_sql", "networking", "os", "software_development"}
