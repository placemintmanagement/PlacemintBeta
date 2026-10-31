# -*- coding: utf-8 -*-
"""TCS Core-CS: Software Development question bank (NEW, part 1 of the
4-part TCS restructure -- did not exist before this commit).

USER-STATED scope: SDLC models, Agile/Scrum, testing types (unit/
integration/system, TDD basics), Git basics (branch/merge/rebase),
debugging approach, code review and quality; PLUS CI/CD and REST/API
basics for Digital and Prime ONLY.

# SEED CONTENT: a hand-written STARTING set (9 items). The two
Digital/Prime-only items (CI/CD, REST basics) are tagged `tier_tags` as a
HARD allow-list -- core.py's `_draw` helper filters these out for Ninja
even under its difficulty-rank fallback, so Ninja can never draw a
CI/CD or REST question regardless of pool size.

Shape: {id, topic, subtopic, difficulty, text, key_points, tier_tags?}.
See banks/_kp.py for kp().
"""
from typing import Any, Dict, List

from ._kp import kp

SOFTWARE_DEVELOPMENT_QUESTIONS: List[Dict[str, Any]] = [
    # -- SDLC -----------------------------------------------------------------
    {
        "id": "tcs-sd-1", "topic": "software_development", "subtopic": "sdlc", "difficulty": "ninja",
        "text": "What is the SDLC (Software Development Life Cycle), and can you name a few of its phases?",  # SEED CONTENT
        "key_points": [
            kp("describes SDLC as the structured process of planning, building, testing and releasing software",
               "SDLC is the end-to-end process a software project follows"),
            kp("names at least two real phases, e.g. requirements, design, implementation, testing, deployment, maintenance",
               "correctly names multiple SDLC phases"),
        ],
    },
    # -- Agile/Scrum -------------------------------------------------------------
    {
        "id": "tcs-sd-2", "topic": "software_development", "subtopic": "agile_scrum", "difficulty": "digital",
        "text": "How does a Scrum team structure its work into sprints, and what is a sprint's purpose?",  # SEED CONTENT
        "key_points": [
            kp("a sprint is a fixed, short time-box (commonly 1-4 weeks) in which a defined chunk of work is delivered",
               "describes a sprint as a fixed-length iteration"),
            kp("names at least one real Scrum ritual/artifact, e.g. sprint planning, daily stand-up, "
               "sprint review/retrospective, or the backlog",
               "correctly names a concrete Scrum practice"),
        ],
    },
    # -- Testing types / TDD ------------------------------------------------------
    {
        "id": "tcs-sd-3", "topic": "software_development", "subtopic": "testing", "difficulty": "ninja",
        "text": "What is the difference between unit testing and integration testing?",  # SEED CONTENT
        "key_points": [
            kp("unit testing checks one small piece of code (e.g. a function/class) in isolation",
               "unit tests target a single unit of code, isolated from its dependencies"),
            kp("integration testing checks that multiple units/components work correctly together",
               "integration tests verify the interaction between combined parts"),
        ],
    },
    {
        "id": "tcs-sd-4", "topic": "software_development", "subtopic": "testing", "difficulty": "digital",
        "text": "What does TDD (test-driven development) mean, and what is the red-green-refactor cycle?",  # SEED CONTENT
        "key_points": [
            kp("TDD means writing a (failing) test BEFORE writing the code that makes it pass",
               "tests are written first, driving the implementation"),
            kp("red-green-refactor: write a failing test (red), make it pass with minimal code (green), "
               "then clean up the code while keeping tests passing (refactor)",
               "correctly describes the three-step red-green-refactor cycle"),
        ],
    },
    # -- Git basics -----------------------------------------------------------------
    {
        "id": "tcs-sd-5", "topic": "software_development", "subtopic": "git", "difficulty": "ninja",
        "text": "Why do developers use a version control system like Git, and what does a branch let you do?",  # SEED CONTENT
        "key_points": [
            kp("version control tracks changes over time and lets multiple people collaborate on the "
               "same codebase safely",
               "it records history and enables safe collaboration"),
            kp("a branch lets you work on changes separately from the main line of code without "
               "affecting it until merged",
               "a branch is an isolated line of development"),
        ],
    },
    {
        "id": "tcs-sd-6", "topic": "software_development", "subtopic": "git", "difficulty": "digital",
        "text": "What's the practical difference between `git merge` and `git rebase` when bringing branch changes together?",  # SEED CONTENT
        "key_points": [
            kp("merge creates a new merge commit combining both branches' histories, keeping the full "
               "original history intact",
               "merge preserves both branches' commit history as-is"),
            kp("rebase replays one branch's commits on top of another, producing a linear history "
               "(rewriting commit history rather than merging it)",
               "rebase rewrites commits to create a cleaner, linear history"),
        ],
    },
    # -- Debugging / code review -----------------------------------------------------
    {
        "id": "tcs-sd-7", "topic": "software_development", "subtopic": "debugging", "difficulty": "digital",
        "text": "A bug is reported that you can't reproduce locally. Walk me through how you'd approach debugging it.",  # SEED CONTENT
        "key_points": [
            kp("gathers more information first -- logs, exact steps, environment/input differences -- "
               "rather than guessing",
               "starts by narrowing down the conditions under which the bug happens"),
            kp("describes a systematic narrowing strategy, e.g. reproducing with matched environment/"
               "data, adding logging, or bisecting recent changes",
               "names a concrete technique for isolating the cause, not just 'I would debug it'"),
        ],
    },
    {
        "id": "tcs-sd-8", "topic": "software_development", "subtopic": "code_review", "difficulty": "digital",
        "text": "When you review a teammate's pull request, what do you actually look for beyond 'does it work'?",  # SEED CONTENT
        "key_points": [
            kp("checks for readability/maintainability (naming, structure, following conventions), not just correctness",
               "looks at code quality and clarity, not only functional correctness"),
            kp("checks for test coverage, edge cases, or potential side effects/regressions",
               "considers whether the change is adequately tested and doesn't break other things"),
        ],
    },
    # -- CI/CD and REST/API basics: Digital/Prime ONLY (USER-STATED) -----------------
    {
        "id": "tcs-sd-9", "topic": "software_development", "subtopic": "ci_cd", "difficulty": "digital",
        "tier_tags": ["digital", "prime"],
        "text": "What is CI/CD, and why does running tests automatically on every commit (continuous integration) help a team?",  # SEED CONTENT
        "key_points": [
            kp("CI/CD stands for continuous integration and continuous delivery/deployment -- automatically "
               "building/testing (and often deploying) code changes",
               "correctly expands what CI/CD means at a high level"),
            kp("continuous integration catches integration bugs/regressions early, right when a change "
               "is made, instead of discovering them much later",
               "explains that CI surfaces problems quickly, close to when they were introduced"),
        ],
    },
    {
        "id": "tcs-sd-10", "topic": "software_development", "subtopic": "rest_api", "difficulty": "digital",
        "tier_tags": ["digital", "prime"],
        "text": "What makes an API 'RESTful'? Name a couple of the ideas REST is built on.",  # SEED CONTENT
        "key_points": [
            kp("REST APIs are built around resources, typically accessed via standard HTTP methods "
               "(GET, POST, PUT/PATCH, DELETE)",
               "correctly ties REST to resource-oriented access over HTTP verbs"),
            kp("names a real REST idea, e.g. statelessness (each request is independent), or using URLs "
               "to identify resources",
               "correctly names a genuine REST constraint/principle"),
        ],
    },
]
