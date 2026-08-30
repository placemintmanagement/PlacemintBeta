# -*- coding: utf-8 -*-
"""HCLTech recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
No real generation/grading logic lives here -- it stays in server.py's
shared, generic dispatch functions. This module is a readable entry point
onto HCLTech's actual OA shape and the one genuinely distinguishing
mechanism its companies.py config invokes.

HCLTech structure (source of truth: companies.py, id="hcltech";
get_config() below re-exports it verbatim), 5-section confirmed structure
(77 Qs / 95 min), sectional scoring:
  - "numerical"       Numerical Ability          (mcq, 15) -- plain.
  - "verbal"          Verbal Ability             (mcq, 15) -- plain.
  - "reasoning"       Logical Reasoning Ability  (mcq, 15) -- plain.
  - "cs-fundamentals" Computer Fundamentals (OS/DBMS/OOPS/CN/Architecture)
    (mcq, 30) -- distinguishing: uses `extra_topics`, the standard 5-topic
    equal split (6 each) every cs-fundamentals-style company section in
    this codebase now follows. See
    generate_hcltech_cs_fundamentals_section() below.
  - "coding"          Coding (2 problems)  -- plain, no difficulty_targets.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from companies import get_company
# server.py does not import this module today, so this import direction is
# safe (no circular import) -- see capgemini_recruitment_process.py's
# docstring for the one company where it would cycle.
from server import _generate_extra_topics


def get_config() -> Optional[Dict[str, Any]]:
    """HCLTech's full section config, straight from companies.py."""
    return get_company("hcltech")


async def generate_hcltech_cs_fundamentals_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """HCLTech's Computer Fundamentals section -- thin wrapper over the
    shared per-topic pool-or-live-verify generator, using this section's
    own 5-way (OS/DBMS/OOPS/CN/Architecture) extra_topics split. Does not
    reimplement _generate_extra_topics' body."""
    return await _generate_extra_topics(
        company_name, section["extra_topics"], section.get("difficulty_target"), user_id,
    )


def build_recruitment_process():
    """Placeholder for a genuinely bespoke HCLTech content bank, if that's
    ever built -- distinct from the thin orchestration wrapper above."""
    raise NotImplementedError("Bespoke HCLTech recruitment process not yet implemented")
