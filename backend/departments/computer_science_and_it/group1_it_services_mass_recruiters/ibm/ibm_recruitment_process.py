# -*- coding: utf-8 -*-
"""IBM recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
No real generation/grading logic lives here -- it stays in server.py's
shared, generic dispatch functions. This module is a readable entry point
onto IBM's actual OA shape and the one genuinely distinguishing mechanism
its companies.py config invokes.

IBM structure (source of truth: companies.py, id="ibm"; get_config() below
re-exports it verbatim), composite scoring, coding-first:
  - "cognitive"  Cognitive  (gamified_round, registry-driven via
    game_types.py/gamified_round.py -- not LLM-generated, no wrapper
    needed).
  - "aptitude"   Aptitude (light gate)  (mcq, 6 Qs, cutoff 0.4) --
    distinguishing: uses `extra_topics` with a reduced 3 Aptitude + 3
    Reasoning split (a deliberate exception to the standard 6-7 minimum
    blend, since this section is only 6 questions total). See
    generate_ibm_aptitude_section() below.
  - "coding"     Coding (2 problems)  (coding, plain, no
    difficulty_targets) -- no wrapper needed.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from companies import get_company
# server.py does not import this module today, so this import direction is
# safe (no circular import) -- see capgemini_recruitment_process.py's
# docstring for the one company where it would cycle.
from server import _generate_extra_topics


def get_config() -> Optional[Dict[str, Any]]:
    """IBM's full section config, straight from companies.py."""
    return get_company("ibm")


async def generate_ibm_aptitude_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """IBM's "Aptitude (light gate)" section -- thin wrapper over the
    shared per-topic pool-or-live-verify generator, using this section's
    own reduced 3+3 extra_topics split. Does not reimplement
    _generate_extra_topics' body."""
    return await _generate_extra_topics(
        company_name, section["extra_topics"], section.get("difficulty_target"), user_id,
    )


def build_recruitment_process():
    """Placeholder for a genuinely bespoke IBM content bank, if that's ever
    built -- distinct from the thin orchestration wrapper above."""
    raise NotImplementedError("Bespoke IBM recruitment process not yet implemented")
