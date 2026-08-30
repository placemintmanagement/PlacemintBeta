# -*- coding: utf-8 -*-
"""LTIMindtree recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
No real generation/grading logic lives here -- it stays in server.py's
shared, generic dispatch functions. This module is a readable entry point
onto LTIMindtree's actual OA shape and the two genuinely distinguishing
mechanisms its companies.py config invokes.

LTIMindtree structure (source of truth: companies.py, id="ltimindtree";
get_config() below re-exports it verbatim), 7-section confirmed structure
(111 Qs / 130 min), composite scoring:
  - "english"      English Comprehension     (comprehension, 12) -- plain.
  - "logical"      Logical Reasoning         (mcq, 12) -- plain.
  - "analytical"   Basic Analytical Ability  (mcq, 10) -- plain.
  - "quant"        Quantitative Ability      (mcq, 12) -- plain.
  - "programming"  Computer Programming      (pseudocode, 25) -- plain, no
    extra_topics layered on top (unlike the cs-fundamentals section below).
  - "cs-fundamentals"  Computer Science (OS/DBMS/OOPS/CN/Architecture)
    (mcq, 20) -- distinguishing: `extra_topics`-only, no pseudocode base at
    all (unlike Capgemini's "technical" section, which pairs extra_topics
    WITH a pseudocode base) -- LTIMindtree is the company the shared
    _generate_extra_topics helper was explicitly generalized for. Standard
    5-topic equal split (4 each). See
    generate_ltimindtree_cs_fundamentals_section() below.
  - "spoken-english"  Spoken English / Communication (voice_mixed, 20,
    listening_count=10) -- distinguishing: LTIMindtree is the company
    `voice_mixed` was originally built for -- half listening
    (repeat-statement, string-similarity graded), half speaking (open
    response, essay-pipeline graded). Generation is handled inline inside
    server._generate_section_questions (no standalone generation-only
    helper to wrap without duplicating it), but grading has its own
    standalone function (server._grade_voice_mixed_section) -- both
    wrapped below.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from companies import get_company
# server.py does not import this module today, so this import direction is
# safe (no circular import) -- see capgemini_recruitment_process.py's
# docstring for the one company where it would cycle.
from server import _generate_extra_topics, _generate_section_questions, _grade_voice_mixed_section


def get_config() -> Optional[Dict[str, Any]]:
    """LTIMindtree's full section config, straight from companies.py."""
    return get_company("ltimindtree")


async def generate_ltimindtree_cs_fundamentals_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """LTIMindtree's Computer Science section -- topic-only, no pseudocode
    base. Thin wrapper over the shared per-topic pool-or-live-verify
    generator, using this section's own 5-way extra_topics split. Does not
    reimplement _generate_extra_topics' body."""
    return await _generate_extra_topics(
        company_name, section["extra_topics"], section.get("difficulty_target"), user_id,
    )


async def generate_ltimindtree_spoken_english_section(
    company_name: str, section: Dict[str, Any], user_id: str, attempt_id: str,
) -> List[dict]:
    """LTIMindtree's Spoken English / Communication section -- thin wrapper
    over the shared section dispatcher, whose "voice_mixed" branch already
    handles splitting `count` into a listening half and a speaking half
    per this section's listening_count. No standalone voice_mixed-only
    generator exists to wrap without duplicating that branch, so this
    calls the real dispatcher directly."""
    return await _generate_section_questions(company_name, section, user_id, attempt_id)


async def grade_ltimindtree_spoken_english_section(section: Dict[str, Any], answers: Dict[str, Any]) -> dict:
    """Grades LTIMindtree's Spoken English / Communication section -- thin
    wrapper over the shared, standalone voice_mixed grader (deterministic
    string-similarity for listening items, essay-pipeline transcript
    grading for speaking items). Does not reimplement
    _grade_voice_mixed_section's body."""
    return await _grade_voice_mixed_section(section, answers)


def build_recruitment_process():
    """Placeholder for a genuinely bespoke LTIMindtree content bank, if
    that's ever built -- distinct from the thin orchestration wrappers
    above."""
    raise NotImplementedError("Bespoke LTIMindtree recruitment process not yet implemented")
