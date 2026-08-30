# -*- coding: utf-8 -*-
"""TCS NQT recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
This file does NOT contain any real generation/grading logic -- that stays
exactly where it already lives, in server.py's shared, generic dispatch
functions and companies.py's data. This module exists so someone opening
`departments/.../tcs/` sees TCS's actual OA shape and which shared
mechanisms it uses, without having to dig through companies.py's full
15-company data blob or server.py's full dispatch chain.

TCS NQT structure (source of truth: companies.py, id="tcs-nqt";
get_config() below re-exports it verbatim):
  Part A -- Foundation (Ninja tier, mandatory, 3 sections, all plain "mcq"):
    - "numerical"  Numerical Ability      (20 Qs)
    - "verbal"     Verbal Ability         (25 Qs)
    - "reasoning"  Reasoning Ability      (20 Qs)
    These three have no special config beyond count/minutes/cutoff -- they
    go through server.py's fully generic mcq path (pool-or-live-verify /
    static-bank split), same as any bare "mcq" section company-wide. No
    wrapper needed for them; wrapping the generic path per-company would
    just be a same-body re-export, not a real orchestration difference.
  Part B -- Advanced (Digital/Prime tier, mandatory):
    - "advanced"  Advanced Quantitative + Reasoning Ability (mcq, 15 Qs)
      Genuinely distinguishing: uses `extra_topics` to split the section
      into an 8-question Advanced Quantitative pool and a 7-question
      Advanced Reasoning pool (companies.py's own comment: the source
      material gives a single combined 14-16 count, split via extra_topics
      here). See generate_tcs_advanced_section() below.
    - "coding"    Advanced Coding (coding, 3 problems) -- plain, no
      difficulty_targets/automata_fix, uses the default problem_bank split.
      No wrapper needed for the same reason as Part A.

No pass/fail gate between Part A and Part B in this codebase today (TCS's
real "Ninja/Digital/Prime" tiering is a descriptive label only -- see
companies.py's own comment on this entry); scoring_mode is "sectional".
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from companies import get_company
# server.py does NOT import this module (only capgemini_recruitment_process
# is imported back into server.py today), so importing server here is safe
# -- no circular import. See capgemini_recruitment_process.py's docstring
# for the one company where this direction would actually cycle.
from server import _generate_extra_topics


def get_config() -> Optional[Dict[str, Any]]:
    """TCS's full section config, straight from companies.py (the source of
    truth) -- so the real OA shape is visible without leaving this file."""
    return get_company("tcs-nqt")


async def generate_tcs_advanced_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """TCS's "Advanced Quantitative + Reasoning Ability" section -- thin
    wrapper over the shared per-topic pool-or-live-verify generator, using
    this section's own extra_topics split (8 Advanced Quant + 7 Advanced
    Reasoning). Does not reimplement any of _generate_extra_topics' body."""
    return await _generate_extra_topics(
        company_name, section["extra_topics"], section.get("difficulty_target"), user_id,
    )


def build_recruitment_process():
    """Placeholder for a genuinely bespoke TCS content bank (dedicated
    question authoring, custom grading), if that's ever built -- distinct
    from the thin orchestration wrappers above, which just call into the
    shared generic mechanisms TCS's config already uses today."""
    raise NotImplementedError("Bespoke TCS recruitment process not yet implemented")
