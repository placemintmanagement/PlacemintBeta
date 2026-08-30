# -*- coding: utf-8 -*-
"""Infosys recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
No real generation/grading logic lives here -- it stays in server.py's
shared, generic dispatch functions and companies.py's data. This module is
a readable entry point onto Infosys's actual OA shape and the shared
mechanisms its config invokes.

Infosys structure (source of truth: companies.py, id="infosys";
get_config() below re-exports it verbatim):
  - "verbal"    Verbal Ability      (mcq, 6 Qs) -- plain, no wrapper needed.
  - "aptitude"  Reasoning + Aptitude (mcq, 8 Qs) -- distinguishing: uses
    `extra_topics` to blend 2 Aptitude + 6 Reasoning questions (Infosys has
    no separate Logical Reasoning section, so this is folded in here per
    the cross-company reasoning-coverage rule -- see companies.py's own
    comment on this entry).
  - "pseudocode"  Pseudocode (highest cutoff 0.65) -- plain pseudocode, no
    extra_topics layered on top (unlike Capgemini/LTIMindtree's pseudocode-
    adjacent sections). No wrapper needed.
  - "puzzles"   Puzzles (mcq, 4 Qs) -- distinguishing: also uses
    `extra_topics`, routed entirely through the dedicated "puzzles"
    static-bank topic rather than the generic live-only path.
  - "essay"     Written Essay (essay, 1) -- plain, no target_words override.

Both "aptitude" and "puzzles" go through the exact same shared mechanism
(server._generate_extra_topics), just with different topic splits pulled
from this section's own companies.py config -- one reusable wrapper covers
both call sites below.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from companies import get_company
# server.py does not import this module today, so this import direction is
# safe (no circular import) -- see capgemini_recruitment_process.py's
# docstring for the one company where it would cycle.
from server import _generate_extra_topics


def get_config() -> Optional[Dict[str, Any]]:
    """Infosys's full section config, straight from companies.py."""
    return get_company("infosys")


async def generate_infosys_extra_topics_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """Thin wrapper over the shared per-topic pool-or-live-verify generator.
    Used for BOTH of Infosys's extra_topics-driven sections -- "aptitude"
    (Reasoning + Aptitude blend) and "puzzles" (dedicated puzzles topic) --
    since both invoke the identical shared mechanism, just with different
    section configs. Does not reimplement _generate_extra_topics' body."""
    return await _generate_extra_topics(
        company_name, section["extra_topics"], section.get("difficulty_target"), user_id,
    )


def build_recruitment_process():
    """Placeholder for a genuinely bespoke Infosys content bank, if that's
    ever built -- distinct from the thin orchestration wrapper above."""
    raise NotImplementedError("Bespoke Infosys recruitment process not yet implemented")
