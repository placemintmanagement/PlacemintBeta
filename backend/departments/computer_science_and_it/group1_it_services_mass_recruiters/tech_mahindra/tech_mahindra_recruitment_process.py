# -*- coding: utf-8 -*-
"""Tech Mahindra recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
No real generation/grading logic lives here -- it stays in server.py's
shared, generic dispatch functions and banks/problem_bank.py. This module
is a readable entry point onto Tech Mahindra's actual OA shape and the
three genuinely distinguishing mechanisms its companies.py config invokes.

Tech Mahindra structure (source of truth: companies.py, id="tech-mahindra";
get_config() below re-exports it verbatim), 4-round OA (170 min),
sectional scoring (Round 1 is an elimination gate):
  Round 1 -- Online Test (60 min, negative marking on every MCQ section):
    - "reasoning"  Logical Ability   (mcq, 12, negative=True) -- plain.
    - "quant"      Quantitative Ability (mcq, 12, negative=True) -- plain.
    - "verbal"     English           (mcq, 12, negative=True) -- plain.
    - "essay"      Essay Writing     (essay, 1) -- plain, no target_words.
  Round 2 -- Technical Test + Personality (90 min):
    - "programming"      Computer Programming (pseudocode, 12,
      negative=True) -- plain, no extra_topics.
    - "cs-fundamentals"  Computer Science (OS/DBMS/OOPS/CN/Architecture)
      (mcq, 12, negative=True) -- distinguishing: `extra_topics`, 5-topic
      split (2/2/3/3/2 to fit 12 questions). See
      generate_tech_mahindra_cs_fundamentals_section() below.
    - "coding"  Automata Fix -- repair the broken code (coding, 2) --
      Tech Mahindra's signature mechanism: `automata_fix: True`, which
      maps directly onto problem_bank.sample_problems'
      `needs_buggy=True` flag (only pull problems that carry a
      buggy_code field). This IS a standalone function, so it's wrapped
      directly below rather than going through server.py at all. See
      generate_tech_mahindra_automata_fix_problems() below.
    - "personality"  Personality Test (unscored, weight 0.0) (mcq, 72) --
      plain, forced-choice psychometric instrument.
  Round 3 -- Conversational Test (Voice) (20 min):
    - "conversational"  (voice_mixed, 20, listening_count=10) --
      distinguishing: reuses the exact same voice_mixed mechanism
      LTIMindtree's Spoken English uses. Generation is handled inline
      inside server._generate_section_questions (no standalone
      generation-only helper to wrap without duplicating it), but grading
      has its own standalone function (server._grade_voice_mixed_section)
      -- both wrapped below.
  Round 4 (Technical Interview + HR) is not a new OA section -- it maps to
  this app's existing Phase 3 interview flow, not anything in this module.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from companies import get_company
from banks.problem_bank import sample_problems
# server.py does not import this module today, so this import direction is
# safe (no circular import) -- see capgemini_recruitment_process.py's
# docstring for the one company where it would cycle.
from server import _generate_extra_topics, _generate_section_questions, _grade_voice_mixed_section


def get_config() -> Optional[Dict[str, Any]]:
    """Tech Mahindra's full section config, straight from companies.py."""
    return get_company("tech-mahindra")


def generate_tech_mahindra_automata_fix_problems(section: Dict[str, Any]) -> List[dict]:
    """Tech Mahindra's "Automata Fix" section -- thin wrapper over the
    shared problem bank sampler, using this section's own
    `automata_fix: True` flag (mapped to problem_bank.sample_problems'
    `needs_buggy=True`, which only pulls problems carrying a buggy_code
    field). Does not reimplement sample_problems' body."""
    return sample_problems(
        section.get("count", 2), difficulty_target=section.get("difficulty_target"),
        needs_buggy=bool(section.get("automata_fix")),
    )


async def generate_tech_mahindra_cs_fundamentals_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """Tech Mahindra's Computer Science section -- thin wrapper over the
    shared per-topic pool-or-live-verify generator, using this section's
    own 5-way extra_topics split. Does not reimplement
    _generate_extra_topics' body."""
    return await _generate_extra_topics(
        company_name, section["extra_topics"], section.get("difficulty_target"), user_id,
    )


async def generate_tech_mahindra_conversational_section(
    company_name: str, section: Dict[str, Any], user_id: str, attempt_id: str,
) -> List[dict]:
    """Tech Mahindra's Conversational Test (Voice) -- thin wrapper over the
    shared section dispatcher, whose "voice_mixed" branch already handles
    splitting `count` into a listening half and a speaking half. No
    standalone voice_mixed-only generator exists to wrap without
    duplicating that branch, so this calls the real dispatcher directly."""
    return await _generate_section_questions(company_name, section, user_id, attempt_id)


async def grade_tech_mahindra_conversational_section(section: Dict[str, Any], answers: Dict[str, Any]) -> dict:
    """Grades Tech Mahindra's Conversational Test (Voice) -- thin wrapper
    over the shared, standalone voice_mixed grader. Does not reimplement
    _grade_voice_mixed_section's body."""
    return await _grade_voice_mixed_section(section, answers)


def build_recruitment_process():
    """Placeholder for a genuinely bespoke Tech Mahindra content bank, if
    that's ever built -- distinct from the thin orchestration wrappers
    above."""
    raise NotImplementedError("Bespoke Tech Mahindra recruitment process not yet implemented")
