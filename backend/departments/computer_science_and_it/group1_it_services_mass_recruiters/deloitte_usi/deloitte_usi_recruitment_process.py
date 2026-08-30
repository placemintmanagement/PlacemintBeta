# -*- coding: utf-8 -*-
"""Deloitte USI recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
No real generation/grading logic lives here -- it stays in server.py's
shared, generic dispatch functions. This module is a readable entry point
onto Deloitte USI's actual OA shape and the two genuinely distinguishing
mechanisms its companies.py config invokes.

Deloitte USI structure (source of truth: companies.py, id="deloitte-usi";
get_config() below re-exports it verbatim), 4 sections (90 min), composite
scoring:
  - "aptitude"  Aptitude  (mcq, 8) -- distinguishing: uses `extra_topics`
    to blend 2 Aptitude + 6 Reasoning (Deloitte USI has no separate
    Reasoning section, folded in per the cross-company reasoning-coverage
    rule). See generate_deloitte_aptitude_section() below.
  - "verbal"    Verbal    (mcq, 6) -- plain.
  - "cs-fundamentals"  CS Fundamentals (heavy: OS/DBMS/OOPS/CN/Architecture)
    (mcq, 12) -- distinguishing: also uses `extra_topics`, the 5-topic
    split (3/3/2/2/2 to fit 12 questions). See
    generate_deloitte_cs_fundamentals_section() below.
  - "coding"    Coding    (coding, 1) -- plain, no difficulty_targets.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from companies import get_company
# server.py does not import this module today, so this import direction is
# safe (no circular import) -- see capgemini_recruitment_process.py's
# docstring for the one company where it would cycle.
from server import _generate_extra_topics


def get_config() -> Optional[Dict[str, Any]]:
    """Deloitte USI's full section config, straight from companies.py."""
    return get_company("deloitte-usi")


async def generate_deloitte_aptitude_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """Deloitte USI's Aptitude section -- thin wrapper over the shared
    per-topic pool-or-live-verify generator, using this section's own
    2 Aptitude + 6 Reasoning extra_topics split. Does not reimplement
    _generate_extra_topics' body."""
    return await _generate_extra_topics(
        company_name, section["extra_topics"], section.get("difficulty_target"), user_id,
    )


async def generate_deloitte_cs_fundamentals_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """Deloitte USI's CS Fundamentals (heavy) section -- thin wrapper over
    the shared per-topic pool-or-live-verify generator, using this
    section's own 5-way extra_topics split. Does not reimplement
    _generate_extra_topics' body."""
    return await _generate_extra_topics(
        company_name, section["extra_topics"], section.get("difficulty_target"), user_id,
    )


def build_recruitment_process():
    """Placeholder for a genuinely bespoke Deloitte USI content bank, if
    that's ever built -- distinct from the thin orchestration wrappers
    above."""
    raise NotImplementedError("Bespoke Deloitte USI recruitment process not yet implemented")
