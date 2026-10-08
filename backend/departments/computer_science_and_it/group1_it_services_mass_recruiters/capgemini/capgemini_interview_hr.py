# -*- coding: utf-8 -*-
"""Dave interview HR questions (Capgemini Dave tier only).

Structure (as specified): 6 categories x 3 questions = 18 (the bank itself is
unchanged). Dave asks 2 or 3 of them (STATED, revised from an earlier fixed
4): Q1 is always Motivation; Q2 is Teamwork or Strengths, chosen at random;
Q3 is optional -- asked only if the HR stage's time budget is not spent
(code decides, never the model) -- drawn from the remaining categories (the
other of Teamwork/Strengths, Career, Flexibility, Situational), never
repeating a category already used in this interview. Exactly two questions
are tagged is_mistake=True (one in Teamwork, one in Situational) -- the two
"mistake" questions are never both asked in the same interview (STATED
rule). Selection and the exclusion check are code, never the model. Company
name is a constant (COMPANY_NAME), substituted into questions that mention
it -- never read from candidate input.
"""
import random
from typing import Any, Dict, List, Optional, Tuple

COMPANY_NAME = "Capgemini"

CATEGORIES = ("motivation", "teamwork", "strengths", "career", "flexibility", "situational")

QUESTIONS: List[Dict[str, Any]] = [
    # -- Motivation --
    {"id": "hr-m1", "category": "motivation", "is_mistake": False,
     "text": "Why do you want to work at {company}?"},
    {"id": "hr-m2", "category": "motivation", "is_mistake": False,
     "text": "What attracted you to the field you chose to study?"},
    {"id": "hr-m3", "category": "motivation", "is_mistake": False,
     "text": "What motivates you to do your best work?"},
    # -- Teamwork --
    {"id": "hr-t1", "category": "teamwork", "is_mistake": False,
     "text": "Tell me about a time you worked closely with a team to deliver something. What was your role?"},
    {"id": "hr-t2", "category": "teamwork", "is_mistake": False,
     "text": "Describe a disagreement you had with a teammate and how you resolved it."},
    {"id": "hr-t3", "category": "teamwork", "is_mistake": True,
     "text": "Tell me about a time you let your team down or made a mistake that affected others. "
             "What happened, and what did you do about it?"},
    # -- Strengths --
    {"id": "hr-s1", "category": "strengths", "is_mistake": False,
     "text": "What would you say is your biggest strength, and how has it helped you in your work or studies?"},
    {"id": "hr-s2", "category": "strengths", "is_mistake": False,
     "text": "How do you approach learning a new skill or technology quickly?"},
    {"id": "hr-s3", "category": "strengths", "is_mistake": False,
     "text": "Describe a skill you're particularly proud of, and how you developed it."},
    # -- Career --
    {"id": "hr-c1", "category": "career", "is_mistake": False,
     "text": "Where do you see yourself professionally in the next few years?"},
    {"id": "hr-c2", "category": "career", "is_mistake": False,
     "text": "What do you know about the kind of work {company} does, and which part of it interests you?"},
    {"id": "hr-c3", "category": "career", "is_mistake": False,
     "text": "What kind of projects or problems do you hope to work on in your career?"},
    # -- Flexibility --
    {"id": "hr-f1", "category": "flexibility", "is_mistake": False,
     "text": "How do you handle a sudden change in priorities or requirements midway through a task?"},
    {"id": "hr-f2", "category": "flexibility", "is_mistake": False,
     "text": "Tell me about a time you had to adapt to a new team, location or way of working."},
    {"id": "hr-f3", "category": "flexibility", "is_mistake": False,
     "text": "Tell me about a time you had to perform under pressure or against a tight deadline. "
             "How did you handle it?"},
    # -- Situational --
    {"id": "hr-si1", "category": "situational", "is_mistake": False,
     "text": "Suppose you're given a task with an unclear deadline and no one available to clarify it. "
             "What would you do?"},
    {"id": "hr-si2", "category": "situational", "is_mistake": True,
     "text": "Tell me about a time something you built or shipped didn't work as expected. "
             "How did you find out, and what did you do next?"},
    {"id": "hr-si3", "category": "situational", "is_mistake": False,
     "text": "If you disagreed with a decision your manager made, how would you handle it?"},
]

_BY_CATEGORY: Dict[str, List[Dict[str, Any]]] = {c: [q for q in QUESTIONS if q["category"] == c] for c in CATEGORIES}


def question_text(q: Dict[str, Any]) -> str:
    return q["text"].format(company=COMPANY_NAME)


def select_hr_first_two(rng: Optional[random.Random] = None) -> Tuple[List[Dict[str, Any]], str]:
    """Q1 is always Motivation (STATED). Q2 is Teamwork or Strengths, picked
    at random (STATED). Returns ([q1, q2], second_category) -- the category
    name is returned too so a later, budget-gated third draw knows which
    categories are still unused."""
    r = rng or random
    motivation = r.choice(_BY_CATEGORY["motivation"])
    second_category = r.choice(("teamwork", "strengths"))
    second = r.choice(_BY_CATEGORY[second_category])
    return [motivation, second], second_category


def select_hr_third(second_category: str, first_two: List[Dict[str, Any]],
                    rng: Optional[random.Random] = None) -> Dict[str, Any]:
    """The optional third question (STATED): drawn from the remaining
    categories (the other of teamwork/strengths, career, flexibility,
    situational), never repeating a category already used. If either of the
    first two questions was tagged is_mistake, the mistake question in this
    pool (there is at most one -- the other mistake question lives in
    whichever of teamwork/strengths was NOT used for Q2, or in situational)
    is excluded, so the two mistake questions are never both asked."""
    r = rng or random
    used_categories = {"motivation", second_category}
    remaining_categories = [c for c in CATEGORIES if c not in used_categories]
    pool = [q for c in remaining_categories for q in _BY_CATEGORY[c]]
    if any(q["is_mistake"] for q in first_two):
        pool = [q for q in pool if not q["is_mistake"]]
    return r.choice(pool)
