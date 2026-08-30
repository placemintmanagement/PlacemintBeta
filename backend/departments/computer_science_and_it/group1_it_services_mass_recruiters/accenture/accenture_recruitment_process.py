# -*- coding: utf-8 -*-
"""Accenture recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
No real generation/grading logic lives here -- it stays in server.py's
shared, generic dispatch functions. This module is a readable entry point
onto Accenture's actual OA shape and the one genuinely distinguishing
mechanism its companies.py config invokes.

Accenture structure (source of truth: companies.py, id="accenture";
get_config() below re-exports it verbatim), 5 sections, composite scoring:
  - "behavioral"     Behavioral (unscored, weight 0.0)      (mcq, 5)
  - "cognitive"       Gamified Cognitive       (gamified_round, registry-
    driven via game_types.py/gamified_round.py -- not LLM-generated, no
    wrapper needed, same as Cognizant's gamified round).
  - "technical"       Tech MCQs (Pseudocode/MS Office/Cloud/Net/CS) (mcq,
    12) -- plain, no extra_topics; "technical" isn't a canonical static-
    bank topic so this stays 100% live-generated via the generic mcq path.
  - "coding"          Stack-specific Coding    (coding, 1) -- plain.
  - "communication"   Communication (MCQ/Written + Spoken) (comm_mixed, 20)
    -- Accenture's distinguishing mechanism: a DELIBERATE deviation from
    Accenture's real (all-MCQ+written) researched format, added by choice
    (2026-07-20) so ~half the items become spoken-response. `comm_mixed`
    generation is handled inline inside server._generate_section_questions
    (there's no standalone generation-only helper to wrap without
    duplicating it), but grading has its own standalone function
    (server._grade_comm_mixed_section) -- both are wrapped below.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from companies import get_company
# server.py does not import this module today, so this import direction is
# safe (no circular import) -- see capgemini_recruitment_process.py's
# docstring for the one company where it would cycle.
from server import _generate_section_questions, _grade_comm_mixed_section


def get_config() -> Optional[Dict[str, Any]]:
    """Accenture's full section config, straight from companies.py."""
    return get_company("accenture")


async def generate_accenture_communication_section(
    company_name: str, section: Dict[str, Any], user_id: str, attempt_id: str,
) -> List[dict]:
    """Accenture's mixed Communication Assessment -- thin wrapper over the
    shared section dispatcher, whose "comm_mixed" branch already handles
    splitting `count` into an MCQ half and a spoken-response half. No
    standalone comm_mixed-only generator exists to wrap without
    duplicating that branch, so this calls the real dispatcher directly."""
    return await _generate_section_questions(company_name, section, user_id, attempt_id)


async def grade_accenture_communication_section(section: Dict[str, Any], answers: Dict[str, Any]) -> dict:
    """Grades Accenture's mixed Communication Assessment -- thin wrapper
    over the shared, standalone comm_mixed grader (mcq items via
    correct_index, speaking items via the essay-pipeline transcript
    grader). Does not reimplement _grade_comm_mixed_section's body."""
    return await _grade_comm_mixed_section(section, answers)


def build_recruitment_process():
    """Placeholder for a genuinely bespoke Accenture content bank, if
    that's ever built -- distinct from the thin orchestration wrappers
    above."""
    raise NotImplementedError("Bespoke Accenture recruitment process not yet implemented")
