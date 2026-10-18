# -*- coding: utf-8 -*-
"""TCS HR-round question banks: motivation, strengths/weaknesses, TCS
company knowledge, and logistics (notice period, location).

# SEED CONTENT: small, hand-written STARTING sets -- 3 motivation, 3
strengths/weaknesses, 3 company-knowledge, 2 logistics. Production should
grow each to at least 4-6 items for real repeat-attempt variety. Dave's HR
bank (dave/hr.py) has directly-adjacent "motivation" and "strengths"
categories that are close in framing to this bank's first two lists, but
were re-authored here rather than imported, per tcs_interview/core.py's
"adapt, don't import" decision for Capgemini-package content. Company
knowledge and logistics have no Capgemini analog at all (TCS-specific facts
and factual-logistics questions don't exist anywhere else in this repo).

Shape: {id, topic, difficulty, text, key_points} -- see banks/_kp.py.
Logistics questions are graded continuously (clarity/honesty/
professionalism), same as every other key_points question here -- NOT a
pass/fail gate (explicit product decision; see core.py's TCS_HR_WEIGHTS).
"""
from typing import Any, Dict, List

from ._kp import kp

MOTIVATION_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-hr-mot-1", "topic": "hr_motivation", "difficulty": "ninja",
        "text": "Why do you want to work at TCS?",
        "key_points": [
            kp("gives a specific, genuine-sounding reason rather than a generic platitude",
               "names something concrete about TCS or the role, not just 'it's a good company'"),
            kp("connects the reason to their own background, goals or interests",
               "ties the answer back to something personal, not purely external facts about TCS"),
        ],
    },
    {
        "id": "tcs-hr-mot-2", "topic": "hr_motivation", "difficulty": "ninja",
        "text": "What motivates you to do your best work?",
        "key_points": [
            kp("names a specific, genuine motivator (not a vague cliche like 'passion')",
               "gives a concrete personal driver"),
            kp("supports it with a real example or reasoning",
               "backs the claim up rather than just stating it"),
        ],
    },
    {
        "id": "tcs-hr-mot-3", "topic": "hr_motivation", "difficulty": "digital",
        "text": "What attracted you to computer science or software engineering as a field?",
        "key_points": [
            kp("gives a specific, personal reason for choosing the field",
               "names a real moment, project or interest that led them here"),
            kp("shows genuine engagement with the subject, not just a career-practicality answer",
               "demonstrates some real interest in the subject matter itself"),
        ],
    },
]

STRENGTHS_WEAKNESSES_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-hr-sw-1", "topic": "hr_strengths_weaknesses", "difficulty": "ninja",
        "text": "What would you say is your biggest strength, and how has it helped you in your work or studies?",
        "key_points": [
            kp("names a specific strength, not a generic trait like 'hardworking' with no detail",
               "gives a concrete, specific strength"),
            kp("supports it with a real example of it helping them",
               "backs the claim with a real situation"),
        ],
    },
    {
        "id": "tcs-hr-sw-2", "topic": "hr_strengths_weaknesses", "difficulty": "digital",
        "text": "What is one area you're actively working to improve, and what are you doing about it?",
        "key_points": [
            kp("names a genuine, specific area for improvement (not a disguised strength like 'I work too hard')",
               "gives an honest, believable weakness"),
            kp("describes a concrete action they're taking to improve it",
               "shows active effort, not just acknowledgement"),
        ],
    },
    {
        "id": "tcs-hr-sw-3", "topic": "hr_strengths_weaknesses", "difficulty": "prime",
        "text": "Describe a skill you're particularly proud of, and how you developed it over time.",
        "key_points": [
            kp("names a specific skill with real depth (not just a buzzword)",
               "gives a concrete, specific skill"),
            kp("describes a real developmental process (practice, projects, mistakes, iteration)",
               "shows the skill was built, not innate or vague"),
        ],
    },
]

COMPANY_KNOWLEDGE_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-hr-ck-1", "topic": "hr_company_knowledge", "difficulty": "ninja",
        "text": "What does NQT stand for, and what is it used for?",
        "key_points": [
            kp("correctly states or closely approximates 'National Qualifier Test'",
               "shows awareness that NQT is TCS's standardized hiring test"),
            kp("describes its purpose correctly: a single test used to assess and hire freshers for TCS "
               "(often at scale, across colleges)",
               "connects NQT to TCS's fresher hiring process"),
        ],
    },
    {
        "id": "tcs-hr-ck-2", "topic": "hr_company_knowledge", "difficulty": "digital",
        "text": "What do you know about the kind of work TCS does, or the kinds of clients/industries it serves?",
        "key_points": [
            kp("names at least one real, correct fact about TCS's business (e.g. IT services, consulting, "
               "a named industry it serves, its global scale)",
               "shows genuine, specific knowledge, not a guess"),
            kp("the answer is plausible and not factually wrong about TCS",
               "doesn't confuse TCS with an unrelated company or make up facts"),
        ],
    },
    {
        "id": "tcs-hr-ck-3", "topic": "hr_company_knowledge", "difficulty": "prime",
        "text": "Name one business unit, practice area or type of project at TCS you'd be interested in working on, and why.",
        "key_points": [
            kp("names a specific, plausible business unit or project type (not a vague 'software development')",
               "shows they looked into TCS's actual structure or offerings, even informally"),
            kp("gives a genuine reason for the interest, connected to their own background or goals",
               "ties the choice back to something personal and specific"),
        ],
    },
]

LOGISTICS_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-hr-log-1", "topic": "hr_logistics", "difficulty": "ninja",
        "text": "What is your current notice period (or earliest availability to join), and are you clear on when you could start?",
        "key_points": [
            kp("clearly states a notice period or a concrete earliest-start timeframe",
               "gives a specific, unambiguous answer rather than 'whenever works'"),
            kp("the answer is stated honestly and consistently, without hedging or contradicting itself",
               "sounds like a genuine, considered answer, not an evasive one"),
        ],
    },
    {
        "id": "tcs-hr-log-2", "topic": "hr_logistics", "difficulty": "digital",
        "text": "Are you open to relocating for this role, and is there a specific location preference or constraint you want to mention?",
        "key_points": [
            kp("gives a clear, direct answer on relocation willingness (not a non-answer)",
               "actually commits to a position rather than staying vague"),
            kp("states any real constraint professionally and specifically, if one exists",
               "if there's a constraint, it's explained clearly and reasonably, not just asserted"),
        ],
    },
]
