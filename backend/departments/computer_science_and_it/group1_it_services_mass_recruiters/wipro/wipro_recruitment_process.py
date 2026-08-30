# -*- coding: utf-8 -*-
"""Wipro Elite NTH recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
No real generation/grading logic lives here -- it stays in server.py's
shared, generic dispatch functions, banks/problem_bank.py, and
services/ai_service.py. This module is a readable entry point onto
Wipro's actual OA shape and the three genuinely distinguishing mechanisms
its companies.py config invokes.

Wipro structure (source of truth: companies.py, id="wipro"; get_config()
below re-exports it verbatim):
  - "aptitude"  Aptitude Test (Quant + Logical + Verbal) (mcq, 45 Qs) --
    the ONLY company whose aptitude section uses `topic_groups` (a blended
    90/10 static-bank/live split PER SUB-GROUP, not one flat pool) --
    see generate_wipro_aptitude_section() below.
  - "coding"  Coding (coding, 2 problems) -- distinguishing: carries
    `difficulty_targets: ["easy_medium", "hard"]`, a PER-PROBLEM difficulty
    list (Problem 1 easy-medium, Problem 2 hard) rather than one blended
    difficulty_target for the whole section. This is handled inline inside
    server._generate_section_questions's "coding" branch (there is no
    separate standalone helper for the per-target loop to wrap without
    duplicating it) -- see generate_wipro_coding_section() below, which
    wraps that dispatcher directly rather than reimplementing the loop.
  - "essay"  Written Communication (auto-evaluated) (essay, 1, cutoff 0.6)
    -- distinguishing: `target_words: 400`, an explicit length override
    (every other essay-type company relies on the generic 150-250 word
    default). See wipro_written_communication_prompt() below, which wraps
    ai_service.essay_prompt directly (the one standalone function that
    actually reads target_words) rather than server.py.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from companies import get_company
from services.ai_service import essay_prompt
# server.py does not import this module today, so this import direction is
# safe (no circular import) -- see capgemini_recruitment_process.py's
# docstring for the one company where it would cycle.
from server import _generate_topic_mix, _generate_section_questions


def get_config() -> Optional[Dict[str, Any]]:
    """Wipro's full section config, straight from companies.py."""
    return get_company("wipro")


async def generate_wipro_aptitude_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """Wipro's blended Aptitude Test (Quant + Logical + Verbal) -- thin
    wrapper over the shared per-sub-group topic-mix generator, using this
    section's own topic_groups config. Does not reimplement
    _generate_topic_mix's body."""
    return await _generate_topic_mix(
        company_name, section.get("count", 45), section["topic_groups"],
        section.get("difficulty_target"), section.get("key"), user_id,
    )


async def generate_wipro_coding_section(
    company_name: str, section: Dict[str, Any], user_id: str, attempt_id: str,
) -> List[dict]:
    """Wipro's 2-problem Coding section (Problem 1 easy-medium, Problem 2
    hard) -- thin wrapper over the shared section dispatcher, whose
    "coding" branch already handles `difficulty_targets` (a per-problem
    list) as an alternative to the single-value `difficulty_target` every
    other coding section uses. No standalone per-target-loop helper exists
    to wrap without duplicating it, so this calls the real dispatcher
    directly instead of re-implementing that loop here."""
    return await _generate_section_questions(company_name, section, user_id, attempt_id)


def wipro_written_communication_prompt(section: Dict[str, Any]) -> Dict[str, str]:
    """Wipro's Written Communication essay prompt -- thin wrapper over the
    shared essay_prompt helper, passing this section's target_words: 400
    override (every other essay-type company omits target_words and gets
    the generic 150-250 word default)."""
    return essay_prompt(
        "Wipro Elite NTH", section.get("name", "Written Communication"),
        target_words=section.get("target_words"),
    )


def build_recruitment_process():
    """Placeholder for a genuinely bespoke Wipro content bank, if that's
    ever built -- distinct from the thin orchestration wrappers above."""
    raise NotImplementedError("Bespoke Wipro recruitment process not yet implemented")
