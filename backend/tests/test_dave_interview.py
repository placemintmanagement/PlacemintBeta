"""Capgemini Dave interview: stage machine, deadline, scoring, two-project
selection, CS-fundamentals selection/nudge, HR selection/exclusion/nudge,
timeout and client projection. Mocked clock, stubbed model, in-memory fake db
(no Mongo, no network). Mirrors test_spark_interview.py's structure for the
Dave tier."""
import asyncio

import pytest

import server
from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini import (
    capgemini_interview as ci,
)
from dave_support import (
    CLOSE_PRIYA, DAVE_PROJECTS, START, _answer, _get, _run_to_end, _start, _stored, dave_world,  # noqa: F401
)


def _drive_to_stage(w, iid, view, target_stage, answer="A clear, specific answer about my own work."):
    while view["stage"] != target_stage:
        view = _answer(w, iid, view["current_question"]["id"], answer)
    return view


# ---- deadline ---------------------------------------------------------------
def test_deadline_is_fifty_five_minutes_and_expires_at_the_boundary():
    state = ci.dave_new_state(START, ci.dave_duration_seconds({}))
    assert state["deadline_at"] == START + 55 * 60
    assert not ci.is_expired(state, START + 55 * 60 - 1)
    assert ci.is_expired(state, START + 55 * 60)


# ---- stage order, advanced only by code -------------------------------------
def test_full_run_visits_every_stage_in_order(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    assert doc["mode"] == "dave"
    assert doc["stage"] == "intro"
    seen_stages = [doc["stage"]]
    steps = _run_to_end(dave_world, iid)
    for s in steps:
        if s["stage"] not in seen_stages:
            seen_stages.append(s["stage"])
    # intro -> project1 -> followups -> project2 -> dsa -> time_complexity ->
    # space_complexity -> cs_fundamentals -> hr -> done, exactly in this
    # order, never skipped or reordered.
    assert seen_stages == ["intro", "project1", "followups", "project2", "dsa",
                           "time_complexity", "space_complexity", "cs_fundamentals", "hr", "done"]
    assert steps[-1]["status"] == "completed"


def test_client_cannot_skip_or_choose_the_next_stage(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    # Submitting a question_id that isn't the current one is rejected (code decides stage moves).
    with pytest.raises(Exception):
        _answer(dave_world, iid, "dave-dsa", "I would like to skip ahead")


# ---- two different projects, both fallbacks ---------------------------------
def test_two_different_projects_are_chosen(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    stored = _stored(dave_world, iid)
    assert stored["project1"] is not None
    assert stored["project2"] is not None
    assert stored["project1"]["name"] != stored["project2"]["name"]


def test_zero_project_resume_uses_both_fixed_fallbacks(dave_world):
    dave_world.db.resumes.docs[0]["analysis"]["extracted_projects"] = []
    doc = _start(dave_world)
    iid = doc["interview_id"]
    stored = _stored(dave_world, iid)
    assert stored["project1"] is None
    assert stored["project2"] is None
    assert stored["project2_text"] == "No resume project. The candidate was asked about an academic or practice project."
    view = _answer(dave_world, iid, doc["current_question"]["id"], "Intro answered.")  # intro -> project1
    assert view["current_question"]["prompt"] == ci.NO_PROJECT_QUESTION


def test_one_project_resume_uses_project1_and_the_project2_fallback(dave_world):
    dave_world.db.resumes.docs[0]["analysis"]["extracted_projects"] = [DAVE_PROJECTS[0]]
    doc = _start(dave_world)
    stored = _stored(dave_world, doc["interview_id"])
    assert stored["project1"]["name"] == DAVE_PROJECTS[0]["name"]
    assert stored["project2"] is None


def test_project2_fallback_question_is_the_fixed_template(dave_world):
    dave_world.db.resumes.docs[0]["analysis"]["extracted_projects"] = []
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = _answer(dave_world, iid, doc["current_question"]["id"], "Intro answered.")  # intro -> project1
    view = _answer(dave_world, iid, view["current_question"]["id"], "I built a practice to-do app.")
    assert view["stage"] == "followups"
    # drive through follow-ups to project2 -- budget is unspent, so a 6th follow-up is asked too (as Spark)
    for _ in range(ci.FOLLOWUP_MAX):
        view = _answer(dave_world, iid, view["current_question"]["id"], "A specific thing I personally did.")
    assert view["stage"] == "project2"
    assert view["current_question"]["prompt"] == ci.DAVE_NO_PROJECT2_QUESTION


# ---- project2 question count -------------------------------------------------
def test_project2_asks_overview_role_and_challenge_minimum(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    dave_world.model.project1_value = True
    dave_world.model.project2_value = True  # both role and challenge present -> no optional 3rd question
    view = doc
    while view["stage"] != "project2":
        view = _answer(dave_world, iid, view["current_question"]["id"], "A clear, specific answer about my work.")
    project2_question_ids = []
    while view["stage"] == "project2":
        project2_question_ids.append(view["current_question"]["id"])
        view = _answer(dave_world, iid, view["current_question"]["id"], "A clear, specific answer about my work.")
    assert project2_question_ids == ["dave-project2-overview", "dave-project2-role", "dave-project2-challenge"]
    assert view["stage"] == "dsa"


def test_project2_asks_optional_third_question_when_thin(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    dave_world.model.project2_value = False  # role/challenge signals absent -> "thin"
    view = doc
    while view["stage"] != "project2":
        view = _answer(dave_world, iid, view["current_question"]["id"], "A clear, specific answer about my work.")
    project2_question_ids = []
    while view["stage"] == "project2":
        project2_question_ids.append(view["current_question"]["id"])
        view = _answer(dave_world, iid, view["current_question"]["id"], "A vague answer.")
    assert project2_question_ids == ["dave-project2-overview", "dave-project2-role",
                                     "dave-project2-challenge", "dave-project2-optional"]
    assert view["stage"] == "dsa"


def test_project2_optional_question_skipped_when_budget_spent(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    dave_world.model.project2_value = False  # thin, but budget will be spent
    view = doc
    while view["stage"] != "project2":
        view = _answer(dave_world, iid, view["current_question"]["id"], "A clear answer.")
    # spend project2's budget before the challenge question is answered
    view = _answer(dave_world, iid, view["current_question"]["id"], "Overview given.")  # -> role question
    dave_world.clock.t += ci.DAVE_BUDGETS_SECONDS["project2"]
    view = _answer(dave_world, iid, view["current_question"]["id"], "A vague role answer.")  # -> challenge question
    view = _answer(dave_world, iid, view["current_question"]["id"], "A vague challenge answer.")  # -> should skip optional
    assert view["stage"] == "dsa"


# ---- fixed complexity templates, always asked -------------------------------
def test_complexity_questions_are_the_fixed_templates_and_always_both_asked(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    while view["stage"] != "dsa":
        view = _answer(dave_world, iid, view["current_question"]["id"], "A clear answer that states O(n) time.")
    assert view["current_question"]["stage"] == "dsa"
    view = _answer(dave_world, iid, view["current_question"]["id"],
                   "I'd use a hash set, O(n) time and O(n) space. Already covered complexity here.")
    assert view["stage"] == "time_complexity"
    assert view["current_question"]["prompt"] == ci.DAVE_TIME_COMPLEXITY_QUESTION
    view = _answer(dave_world, iid, view["current_question"]["id"], "O(n) time.")
    assert view["stage"] == "space_complexity"
    assert view["current_question"]["prompt"] == ci.DAVE_SPACE_COMPLEXITY_QUESTION


# ---- CS-fundamentals: topic order shuffled, question count, nudge -----------
def test_cs_first_two_questions_are_oops_and_sql_order_shuffled():
    import random
    r = random.Random(7)
    saw_oops_first = False
    saw_sql_first = False
    for _ in range(200):
        pair = ci.dave_cs_pick_first_two(r)
        topics = [q["topic"] for q in pair]
        assert set(topics) == {"oops", "sql"}  # never os in the first two
        if topics == ["oops", "sql"]:
            saw_oops_first = True
        if topics == ["sql", "oops"]:
            saw_sql_first = True
    assert saw_oops_first and saw_sql_first


def test_cs_weighted_draw_never_repeats_a_question():
    import random
    r = random.Random(11)
    for _ in range(300):
        pair = ci.dave_cs_pick_first_two(r)
        exclude = {pair[0]["id"], pair[1]["id"]}
        q3 = ci.dave_cs_pick_weighted(exclude, r)
        assert q3["id"] not in exclude
        exclude2 = exclude | {q3["id"]}
        q4 = ci.dave_cs_pick_weighted(exclude2, r)
        assert q4["id"] not in exclude2


def test_cs_asks_three_questions_when_budget_is_spent_before_the_fourth(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    view = _drive_to_stage(dave_world, iid, view, "cs_fundamentals",
                           answer="A clear answer, O(n) time and O(n) space.")
    cs_question_ids = []
    # spend the cs_fundamentals budget right away so Q4 is never offered
    dave_world.clock.t += ci.DAVE_BUDGETS_SECONDS["cs_fundamentals"]
    long_answer = "A clear, specific answer that explains the concept in my own words with an example. " * 2
    while view["stage"] == "cs_fundamentals":
        cs_question_ids.append(view["current_question"]["id"])
        view = _answer(dave_world, iid, view["current_question"]["id"], long_answer)
    assert cs_question_ids == ["dave-cs-0", "dave-cs-1", "dave-cs-2"]
    assert view["stage"] == "hr"


def test_cs_asks_four_questions_when_budget_is_not_spent(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    view = _drive_to_stage(dave_world, iid, view, "cs_fundamentals",
                           answer="A clear answer, O(n) time and O(n) space.")
    cs_question_ids = []
    long_answer = "A clear, specific answer that explains the concept in my own words with an example. " * 2
    while view["stage"] == "cs_fundamentals":
        cs_question_ids.append(view["current_question"]["id"])
        view = _answer(dave_world, iid, view["current_question"]["id"], long_answer)
    assert cs_question_ids == ["dave-cs-0", "dave-cs-1", "dave-cs-2", "dave-cs-3"]
    assert view["stage"] == "hr"


def test_cs_short_answer_gets_one_nudge_then_advances(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    view = _drive_to_stage(dave_world, iid, view, "cs_fundamentals",
                           answer="A clear answer, O(n) time and O(n) space.")
    first_q_id = view["current_question"]["id"]
    short_answer = "Not sure."  # under the 15-word threshold
    view = _answer(dave_world, iid, first_q_id, short_answer)
    assert view["current_question"]["id"] == f"{first_q_id}-nudge"
    assert view["current_question"]["prompt"] == ci.CS_NUDGE_TEXT
    # a second short answer after the nudge does NOT get a second nudge -- it advances
    view = _answer(dave_world, iid, view["current_question"]["id"], "Still short.")
    assert view["stage"] == "cs_fundamentals"
    assert not view["current_question"]["id"].endswith("-nudge")
    assert view["current_question"]["id"] == "dave-cs-1"


def test_cs_long_answer_gets_no_nudge(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    view = _drive_to_stage(dave_world, iid, view, "cs_fundamentals",
                           answer="A clear answer, O(n) time and O(n) space.")
    first_q_id = view["current_question"]["id"]
    long_answer = " ".join(["word"] * 20)  # at/over the 15-word threshold
    view = _answer(dave_world, iid, first_q_id, long_answer)
    assert not view["current_question"]["id"].endswith("-nudge")


def test_cs_no_nudge_when_remaining_time_under_two_minutes(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    view = _drive_to_stage(dave_world, iid, view, "cs_fundamentals",
                           answer="A clear answer, O(n) time and O(n) space.")
    dave_world.clock.t = view["deadline_epoch"] - 60
    first_q_id = view["current_question"]["id"]
    view = _answer(dave_world, iid, first_q_id, "Not sure.")
    assert not view["current_question"]["id"].endswith("-nudge")


# ---- HR selection and exclusion rule -----------------------------------------
def test_hr_asks_two_or_three_questions_q1_always_motivation(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    view = _drive_to_stage(dave_world, iid, view, "hr", answer="A clear answer, O(n) time and O(n) space.")
    stored = _stored(dave_world, iid)
    hr_qs = stored["hr_questions"]
    assert len(hr_qs) == 2  # the third is drawn later, only if the hr budget allows
    assert hr_qs[0]["category"] == "motivation"
    assert hr_qs[1]["category"] in ("teamwork", "strengths")
    long_answer = ("A clear, specific answer with a concrete example and a reflection on what I learned " * 3)
    asked_count = 0
    while view["stage"] == "hr":
        asked_count += 1
        view = _answer(dave_world, iid, view["current_question"]["id"], long_answer)
        if asked_count > 10:
            raise AssertionError("hr stage did not end")
    assert view["status"] == "completed"
    assert asked_count in (2, 3)
    stored = _stored(dave_world, iid)
    final_qs = stored["hr_questions"]
    assert len(final_qs) == asked_count
    categories = [q["category"] for q in final_qs]
    assert len(categories) == len(set(categories))  # never repeats a category
    assert sum(1 for q in final_qs if q["is_mistake"]) <= 1  # never both mistake questions together


def test_hr_third_question_skipped_when_hr_budget_is_spent(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    view = _drive_to_stage(dave_world, iid, view, "hr", answer="A clear answer, O(n) time and O(n) space.")
    long_answer = "A clear, specific answer with a concrete example and a reflection on what I learned. " * 3
    view = _answer(dave_world, iid, view["current_question"]["id"], long_answer)  # Q1 -> Q2
    dave_world.clock.t += ci.DAVE_BUDGETS_SECONDS["hr"]  # spend the hr budget before Q2 is answered
    view = _answer(dave_world, iid, view["current_question"]["id"], long_answer)  # Q2 -> should skip Q3
    assert view["status"] == "completed"


def test_hr_third_question_asked_when_hr_budget_is_not_spent(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    view = _drive_to_stage(dave_world, iid, view, "hr", answer="A clear answer, O(n) time and O(n) space.")
    long_answer = "A clear, specific answer with a concrete example and a reflection on what I learned. " * 3
    view = _answer(dave_world, iid, view["current_question"]["id"], long_answer)  # Q1 -> Q2
    view = _answer(dave_world, iid, view["current_question"]["id"], long_answer)  # Q2 -> Q3 (budget unspent)
    assert view["stage"] == "hr"
    assert view["current_question"]["id"] == "dave-hr-2"


def test_hr_selection_over_many_draws_always_valid():
    import random
    r = random.Random(123)
    for _ in range(600):
        first_two, second_category = ci.dave_pick_hr_first_two(r)
        assert first_two[0]["category"] == "motivation"
        assert second_category in ("teamwork", "strengths")
        assert first_two[1]["category"] == second_category
        third = ci.dave_pick_hr_third(second_category, first_two, r)
        all_three = first_two + [third]
        categories = [q["category"] for q in all_three]
        assert len(categories) == len(set(categories))  # never repeats a category
        assert sum(1 for q in all_three if q["is_mistake"]) <= 1  # never both mistake questions


# ---- the HR nudge rule --------------------------------------------------------
def test_hr_short_answer_gets_one_nudge_then_advances(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    view = _drive_to_stage(dave_world, iid, view, "hr", answer="A clear answer, O(n) time and O(n) space.")
    first_q_id = view["current_question"]["id"]
    short_answer = "Not sure."  # under the 25-word threshold
    view = _answer(dave_world, iid, first_q_id, short_answer)
    assert view["current_question"]["id"] == f"{first_q_id}-nudge"
    assert view["current_question"]["prompt"] == ci.HR_NUDGE_TEXT
    # a second short answer after the nudge does NOT get a second nudge -- it advances
    view = _answer(dave_world, iid, view["current_question"]["id"], "Still short.")
    assert view["stage"] == "hr"
    assert not view["current_question"]["id"].endswith("-nudge")


def test_hr_long_answer_gets_no_nudge(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    view = _drive_to_stage(dave_world, iid, view, "hr", answer="A clear answer, O(n) time and O(n) space.")
    first_q_id = view["current_question"]["id"]
    long_answer = " ".join(["word"] * 30)  # at/over the 25-word threshold
    view = _answer(dave_world, iid, first_q_id, long_answer)
    assert not view["current_question"]["id"].endswith("-nudge")


def test_hr_no_nudge_when_remaining_time_under_two_minutes(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = doc
    view = _drive_to_stage(dave_world, iid, view, "hr", answer="A clear answer, O(n) time and O(n) space.")
    # push the clock to inside 2 minutes of the deadline
    dave_world.clock.t = view["deadline_epoch"] - 60
    first_q_id = view["current_question"]["id"]
    view = _answer(dave_world, iid, first_q_id, "Not sure.")
    assert not view["current_question"]["id"].endswith("-nudge")


# ---- timeout mid-stage --------------------------------------------------------
def test_timeout_mid_followups_closes_the_interview(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    view = _answer(dave_world, iid, doc["current_question"]["id"], "Intro answered.")
    assert view["stage"] == "project1"
    view = _answer(dave_world, iid, view["current_question"]["id"], "Project1 answered.")
    assert view["stage"] == "followups"
    dave_world.clock.t = view["deadline_epoch"]  # exactly at the deadline
    with pytest.raises(Exception):
        _answer(dave_world, iid, view["current_question"]["id"], "Too late now.")
    final = _get(dave_world, iid)
    assert final["status"] == "timed_out"
    assert final["closing_message"] == CLOSE_PRIYA


# ---- closing message, no feedback/flags in client responses ------------------
def test_closing_message_and_no_feedback_during_or_after(dave_world):
    doc = _start(dave_world)
    iid = doc["interview_id"]
    steps = _run_to_end(dave_world, iid)
    for s in steps[:-1]:
        assert "flags" not in s
        assert "score" not in s
        assert "rubric" not in s
        for t in s.get("turns", []):
            assert "flags" not in t
            assert "verdict" not in t
    assert steps[-1]["closing_message"] == CLOSE_PRIYA
    stored = _stored(dave_world, iid)
    assert stored["dave_score"] is not None
    assert "dave_score" not in steps[-1]


# ---- scoring weights ----------------------------------------------------------
def test_interview_score_uses_the_stated_weights():
    score = ci.dave_interview_score(1.0, 1.0, 1.0, 1.0, 1.0)
    assert score["interview"] == 1.0
    score2 = ci.dave_interview_score(None, None, None, None, None)
    assert score2["interview"] == 0.0
    assert set(score2["not_reached"]) == {"followups", "project2", "dsa_complexity", "cs_fundamentals", "hr"}
    # weighted partial score, spot-checked against the named constants
    score3 = ci.dave_interview_score(1.0, 0.0, 0.0, 0.0, 0.0)
    assert score3["interview"] == ci.DAVE_WEIGHTS["project1_followups"]
