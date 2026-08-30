# -*- coding: utf-8 -*-
"""Microsoft SWE recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
No real generation/grading logic lives here -- it stays in server.py's
shared, generic dispatch functions. This module is a readable entry point
onto Microsoft SWE's actual OA shape and the two genuinely distinguishing
mechanisms its companies.py config invokes.

Microsoft SWE structure (source of truth: companies.py, id="microsoft-swe";
get_config() below re-exports it verbatim) -- UNVERIFIED, uses the generic
DSA-focused fallback template (same shape as product-general/core-default),
composite scoring:
  - "aptitude"  Quant + Reasoning  (mcq, 8) -- distinguishing: uses
    `extra_topics` to blend 2 Quantitative Aptitude + 6 Reasoning (no
    separate Reasoning section, folded in per the cross-company
    reasoning-coverage rule). See generate_microsoft_aptitude_section()
    below.
  - "cs-fundamentals"  CS Fundamentals (OS/DBMS/OOPS/CN/Architecture)
    (mcq, 10) -- distinguishing: also uses `extra_topics`, the standard
    5-topic equal split (2 each). See
    generate_microsoft_cs_fundamentals_section() below.
  - "coding"  DSA Coding (2 problems)  (coding) -- plain, no
    difficulty_targets.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from companies import get_company
# server.py does not import this module today, so this import direction is
# safe (no circular import) -- see capgemini_recruitment_process.py's
# docstring for the one company where it would cycle.
from server import _generate_extra_topics


def get_config() -> Optional[Dict[str, Any]]:
    """Microsoft SWE's full section config, straight from companies.py."""
    return get_company("microsoft-swe")


async def generate_microsoft_aptitude_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """Microsoft SWE's Quant + Reasoning section -- thin wrapper over the
    shared per-topic pool-or-live-verify generator, using this section's
    own 2+6 extra_topics split. Does not reimplement
    _generate_extra_topics' body."""
    return await _generate_extra_topics(
        company_name, section["extra_topics"], section.get("difficulty_target"), user_id,
    )


async def generate_microsoft_cs_fundamentals_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """Microsoft SWE's CS Fundamentals section -- thin wrapper over the
    shared per-topic pool-or-live-verify generator, using this section's
    own 5-way extra_topics split. Does not reimplement
    _generate_extra_topics' body."""
    return await _generate_extra_topics(
        company_name, section["extra_topics"], section.get("difficulty_target"), user_id,
    )


def build_recruitment_process():
    """Placeholder. Real per-company recruitment-process logic (content
    banks, draw functions, custom grading) goes here once built."""
    raise NotImplementedError("Recruitment process for Microsoft SWE not yet implemented")
