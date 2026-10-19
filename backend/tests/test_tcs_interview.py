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


# ---- time-filling adaptive interview flow (Item 2) -------------------------
# Replaces the old fixed-question-count-per-phase model: each phase now
# pre-selects up to a `max_questions` ceiling (core.TCS_PHASE_BUDGETS), and
# the SAME grading call that scores an answer also decides whether to probe
# deeper with a follow-up (core.TCS_MAX_FOLLOWUPS_PER_TIER caps consecutive
# follow-ups per top-level question) -- see core.py's advance()/
# follow_up_depth_allows/follow_up_time_budget_allows and orchestration.py's
# answer_interview for the mechanics. No separate follow-up-generation
# call; no change to the flag-OFF behaviour tested above.

from fastapi import HTTPException as _HTTPException  # noqa: E402 (local, test-only import)


def test_followup_is_served_from_the_same_grading_call_no_extra_ai_call(tcs_world):
    tier = "digital"
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    tcs_world.model.needs_follow_up_value = True
    calls_before = len(tcs_world.model.calls)
    view = _answer(tcs_world, iid, started["current_question"]["id"], "An answer about my project.")
    assert len(tcs_world.model.calls) == calls_before + 1  # exactly one AI call, not two
    assert view["phase"] == "project"  # still in project -- the follow-up, not the next phase
    assert view["current_question"]["id"] == f"{started['current_question']['id']}-f1"


@pytest.mark.parametrize("tier", core.TCS_INTERVIEW_TIERS)
def test_followup_depth_never_exceeds_the_tiers_cap(tcs_world, tier):
    cap = core.TCS_MAX_FOLLOWUPS_PER_TIER[tier]
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    tcs_world.model.needs_follow_up_value = True  # always asks for one more, every single time
    view = _get(tcs_world, iid)
    base_id = view["current_question"]["id"]
    depths_seen = []
    for _ in range(cap + 3):  # try to push well past the cap
        view = _answer(tcs_world, iid, view["current_question"]["id"], "A detailed project answer.")
        qid = view["current_question"]["id"]
        if qid.startswith(f"{base_id}-f"):
            depths_seen.append(int(qid.rsplit("-f", 1)[1]))
        else:
            break  # moved off the base question entirely -- depth cap (or phase end) was hit
    assert depths_seen == list(range(1, cap + 1)), (
        f"{tier}: follow-up depth must stop exactly at its own cap ({cap}), got {depths_seen}"
    )


def test_followup_answer_is_graded_against_the_generic_followup_rubric(tcs_world):
    tier = "digital"
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    tcs_world.model.needs_follow_up_value = True
    _answer(tcs_world, iid, started["current_question"]["id"], "An answer about my project.")
    prompt = tcs_world.model.calls[-1]["prompt"]
    assert "needs_follow_up" in prompt  # the follow-up slot was offered on THIS call

    view = _get(tcs_world, iid)
    tcs_world.model.needs_follow_up_value = False
    _answer(tcs_world, iid, view["current_question"]["id"], "A deeper, specific answer to the follow-up.")
    followup_prompt = tcs_world.model.calls[-1]["prompt"]
    assert core.FOLLOWUP_KEY_POINTS[0]["statement"] in followup_prompt


def test_fast_student_gets_strictly_more_total_turns_than_a_slow_student(tcs_world):
    """Same tier/phase configuration; the only difference is how long each
    answer takes on the fake clock. A fast student keeps being served MORE
    pre-selected questions (up to each phase's max_questions) because they
    never trip a phase's own time-budget overrun; a slow student trips it
    almost immediately on every non-last phase and gets truncated down to
    each phase's min_questions floor, then runs out of overall time."""
    tier = "digital"
    tcs_world.model.needs_follow_up_value = False

    started_fast = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    _run_to_end(tcs_world, started_fast["interview_id"], latency_seconds=5)
    fast_turns = len(_stored(tcs_world, started_fast["interview_id"])["turns"])

    started_slow = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    _run_to_end(tcs_world, started_slow["interview_id"], latency_seconds=1200)  # 20 minutes/answer
    slow_turns = len(_stored(tcs_world, started_slow["interview_id"])["turns"])

    assert fast_turns > slow_turns > 0


@pytest.mark.parametrize("tier", core.TCS_INTERVIEW_TIERS)
@pytest.mark.parametrize("latency_seconds", [0, 90, 1200, 5000])
def test_no_simulated_student_ever_exceeds_the_overall_deadline(tcs_world, tier, latency_seconds):
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    _run_to_end(tcs_world, iid, latency_seconds=latency_seconds)
    stored = _stored(tcs_world, iid)
    assert stored["status"] in ("completed", "timed_out")
    # Once finished (for any reason, including running out of the overall
    # deadline), nothing further is ever accepted or graded -- the hard
    # stop is real, not just a status label.
    with pytest.raises(_HTTPException) as exc:
        _answer(tcs_world, iid, "any-question-id", "too late")
    assert exc.value.status_code == 409


def test_core_phase_budget_is_unaffected_by_an_overrunning_earlier_phase_with_followups(tcs_world):
    tier = "digital"
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    core_len_at_start = len(_stored(tcs_world, iid)["phase_questions"]["core"])

    # Force the FIRST phase (project) to run long via follow-ups, up to its
    # own tier's depth cap.
    tcs_world.model.needs_follow_up_value = True
    view = _get(tcs_world, iid)
    while view["phase"] == "project":
        view = _answer(tcs_world, iid, view["current_question"]["id"], "An answer about my project.")
    tcs_world.model.needs_follow_up_value = False

    stored = _stored(tcs_world, iid)
    assert len(stored["phase_questions"]["core"]) == core_len_at_start, (
        "project's follow-up overrun must never change core's own, independently pre-selected list"
    )

    _run_to_end(tcs_world, iid)
    final = _stored(tcs_world, iid)
    core_turns = [t for t in final["turns"] if t["phase"] == "core"]
    assert len(core_turns) >= core.TCS_PHASE_BUDGETS[tier]["core"]["min_questions"]


def test_same_interview_id_gives_the_same_question_and_followup_sequence(monkeypatch):
    """Determinism: re-seeding orchestration.start_interview's rng by
    interview_id (not an unseeded random.Random()) means the WHOLE
    sitting's pre-selected picks (project/coding/core, not just the
    puzzle) are a pure function of interview_id -- forcing new_id to
    return the SAME id twice, across two independent fake worlds, must
    reproduce byte-identical phase_questions and the same resulting
    turn sequence against the same scripted model/clock."""
    from tcs_support import _make_tcs_world
    fixed_id = "intv-determinism-fixture"

    def run_once():
        w = _make_tcs_world(monkeypatch)
        monkeypatch.setattr(server, "new_id", lambda prefix: fixed_id)
        w.model.needs_follow_up_value = True
        started = _start(w, company_id="tcs-nqt", tier="digital")
        assert started["interview_id"] == fixed_id
        _run_to_end(w, fixed_id, latency_seconds=0)
        stored = _stored(w, fixed_id)
        turn_sequence = [(t["phase"], t["question_id"]) for t in stored["turns"]]
        return turn_sequence, stored["phase_questions"]

    seq_a, phase_questions_a = run_once()
    seq_b, phase_questions_b = run_once()
    assert seq_a == seq_b
    assert phase_questions_a == phase_questions_b


def test_resume_mid_sitting_after_a_followup_was_served(tcs_world):
    tier = "digital"
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    tcs_world.model.needs_follow_up_value = True
    view = _answer(tcs_world, iid, started["current_question"]["id"], "An answer about my project.")
    followup_id = view["current_question"]["id"]
    assert followup_id.endswith("-f1")

    # Simulate a reload/resume: fetch fresh, exactly like a reconnecting
    # client would (no in-memory state reused from the call above).
    resumed = _get(tcs_world, iid)
    assert resumed["current_question"]["id"] == followup_id
    assert resumed["phase"] == "project"

    tcs_world.model.needs_follow_up_value = False
    continued = _answer(tcs_world, iid, followup_id, "A deeper answer to the follow-up.")
    assert continued["phase"] == "architecture"
    stored = _stored(tcs_world, iid)
    assert len(stored["turns"]) == 2


def test_rolling_context_stays_bounded_with_followup_turns_mixed_in(tcs_world):
    """Extends the fixed-count-era bounded-context guarantee to the new
    variable-length flow: driving a REAL interview with follow-ups turned
    on (so one phase accumulates many more turns than before this task)
    must never make orchestration._rolling_context grow past the same
    generous fixed cap the original test already checked."""
    tier = "digital"
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    tcs_world.model.needs_follow_up_value = True
    view = _get(tcs_world, iid)
    sizes = []
    for _ in range(15):
        if view["status"] != "in_progress":
            break
        view = _answer(tcs_world, iid, view["current_question"]["id"], "A detailed, specific answer.")
        stored = _stored(tcs_world, iid)
        ctx = orchestration._rolling_context(stored)
        sizes.append(len(ctx) if ctx else 0)
    assert sizes  # the loop actually ran
    assert max(sizes) < 2000


def test_tcs_interview_score_renormalizes_weights_when_a_phase_is_never_assessed():
    """Direct unit test of the renormalization path (not just prose): a
    phase with zero turns is marked not_assessed, excluded from scoring,
    and the remaining phases'/communication's weights are renormalized to
    still sum to 1.0 over that smaller set."""
    tier = "digital"
    turns = [
        {"phase": "project", "topic": "project", "flags": {"key_point_0": True, core.EXTRA_SIGNAL: True}},
        {"phase": "coding", "topic": "coding_discussion", "flags": {"key_point_0": True, core.EXTRA_SIGNAL: True}},
        {"phase": "puzzle", "topic": "puzzle", "flags": {"key_point_0": True, core.EXTRA_SIGNAL: True}},
        {"phase": "core", "topic": "oop", "flags": {"key_point_0": True, core.EXTRA_SIGNAL: True}},
    ]  # "architecture" never reached at all -- zero turns for it
    result = core.tcs_interview_score(tier, turns)
    assert result["not_assessed"] == ["architecture"]
    assert result["renormalized"] is True
    assert round(sum(result["weights_used"].values()), 6) == 1.0
    assert result["weights_used"]["architecture"] == 0.0
    assert "coverage_note" in result and "architecture" in result["coverage_note"].lower()


def test_tcs_interview_score_normal_all_assessed_case_is_unaffected():
    for tier in core.TCS_INTERVIEW_TIERS:
        turns = [
            {"phase": phase, "topic": phase if phase != "core" else "oop",
             "flags": {"key_point_0": True, core.EXTRA_SIGNAL: True}}
            for phase in core.TCS_TIER_PHASE_ORDER[tier]
        ]
        result = core.tcs_interview_score(tier, turns)
        assert result["not_assessed"] == []
        assert result["renormalized"] is False
        assert result["weights_used"] == core.TCS_PHASE_WEIGHTS[tier]
        assert "coverage_note" not in result
        assert round(sum(result["weights_used"].values()), 6) == 1.0


def test_end_to_end_not_assessed_phase_when_a_student_stalls_before_the_last_phase(tcs_world, monkeypatch):
    """A real (fake-AI, fake-clock) sitting that stalls long enough right
    before its LAST phase ends up with that phase marked not_assessed in
    the persisted tcs_score, renormalized weights summing to 1.0, and the
    note surfaced in the actual report text (interview_summary), never
    silently omitted."""
    tier = "ninja"
    started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
    iid = started["interview_id"]
    view = _get(tcs_world, iid)
    while view["status"] == "in_progress" and view["phase"] != "core":
        view = _answer(tcs_world, iid, view["current_question"]["id"], "A clear, specific answer.")
    assert view["phase"] == "core"

    tcs_world.clock.t += 31 * 60  # blow the entire 30-minute ninja deadline before answering core at all
    with pytest.raises(_HTTPException) as exc:
        _answer(tcs_world, iid, view["current_question"]["id"], "Too late.")
    assert exc.value.detail["code"] == "time_up"

    stored = _stored(tcs_world, iid)
    assert stored["status"] == "timed_out"
    score = stored["tcs_score"]
    assert score["not_assessed"] == ["core"]
    assert score["renormalized"] is True
    assert round(sum(score["weights_used"].values()), 6) == 1.0

    captured = []
    report = _report_by_interview_id(tcs_world, iid, monkeypatch, captured)
    assert "tcs_coverage_note" in report["interview_summary"]
    assert "core" in report["interview_summary"]["tcs_coverage_note"].lower()


# ---- coding-discussion phase: separate pools by tier -----------------------

def test_digital_and_prime_coding_pools_are_tier_separated_not_shared():
    from departments.computer_science_and_it.group1_it_services_mass_recruiters.tcs.tcs_interview.banks.coding_discussion import (
        CODING_DISCUSSION_QUESTIONS,
    )
    digital_pool = {q["id"] for q in CODING_DISCUSSION_QUESTIONS if "digital" in q.get("tier_tags", [])}
    prime_pool = {q["id"] for q in CODING_DISCUSSION_QUESTIONS if "prime" in q.get("tier_tags", [])}
    assert "tcs-code-3" in prime_pool and "tcs-code-3" not in digital_pool, (
        "Prime's own deeper-follow-up item must never be drawable for Digital"
    )
    assert "tcs-code-2" in digital_pool and "tcs-code-2" not in prime_pool


@pytest.mark.parametrize("tier", core.TCS_INTERVIEW_TIERS)
def test_questions_per_sitting_fast_typical_slow(tcs_world, tier, capsys):
    """Real, measured (not estimated) total-turn counts per tier at three
    simulated answer speeds, against the actual orchestration/core code --
    feeds the Item-2 task report's 3x3 data table. fast/typical/slow are
    purely a difference in per-answer wall-clock latency on the fake
    clock (follow-ups off for fast/typical, on for slow) -- see
    test_fast_student_gets_strictly_more_total_turns_than_a_slow_student
    for the direct fast-vs-slow comparison this generalizes across tiers."""
    results = {}
    for speed_name, latency, follow_up in (("fast", 5, False), ("typical", 300, False), ("slow", 1200, True)):
        started = _start(tcs_world, company_id="tcs-nqt", tier=tier)
        tcs_world.model.needs_follow_up_value = follow_up
        _run_to_end(tcs_world, started["interview_id"], latency_seconds=latency)
        results[speed_name] = len(_stored(tcs_world, started["interview_id"])["turns"])
    with capsys.disabled():
        print(f"\n[questions-per-sitting] {tier}: fast={results['fast']} "
              f"typical={results['typical']} slow={results['slow']}")
    assert results["fast"] >= results["typical"] >= results["slow"] > 0


def test_prime_never_draws_digitals_exclusive_item_and_vice_versa(tcs_world):
    rng = __import__("random").Random(0)
    for _ in range(25):
        digital_draw = {q["id"] for q in core.select_coding_questions("digital", rng)}
        assert "tcs-code-3" not in digital_draw
        prime_draw = {q["id"] for q in core.select_coding_questions("prime", rng)}
        assert "tcs-code-2" not in prime_draw
