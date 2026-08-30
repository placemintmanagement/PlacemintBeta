# -*- coding: utf-8 -*-
"""Zoho recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
No real generation/grading logic lives here -- it stays in server.py's
shared, generic dispatch functions. This module is a readable entry point
onto Zoho's actual OA shape.

Zoho structure (source of truth: companies.py, id="zoho"; get_config()
below re-exports it verbatim), 3 rounds, ~5h40m total (matches Zoho's real
all-day OA), composite scoring:
  - "r1-aptitude"        R1a: Quantitative Aptitude (pen-paper) (mcq, 12)
  - "r1-technical"       R1b: Technical MCQs -- predict C/Java output
    (pseudocode, 13)
  - "r2-basic-coding"    R2: Basic Programming -- 5 problems
    (coding, difficulty_target="easy_medium")
  - "r3-advanced-coding" R3: Advanced DSA (coding,
    difficulty_target="hard")

Checked against the live companies.py data (not assumed from the earlier
audit summary): Zoho's config has NO `extra_topics`, NO `topic_groups`, NO
per-problem `difficulty_targets` list, and NO `target_words` override --
every section here uses only the plain scalar `difficulty_target` string
(a generic parameter every coding/pseudocode section can set, already
threaded through server._generate_section_questions for every company).
That's not a distinguishing mechanism the way Wipro's per-problem
difficulty_targets LIST or Capgemini/LTIMindtree's extra_topics blends
are, so no wrapper functions are added here -- there is nothing
company-specific to orchestrate beyond what get_config() already exposes.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

from companies import get_company


def get_config() -> Optional[Dict[str, Any]]:
    """Zoho's full section config, straight from companies.py."""
    return get_company("zoho")


def build_recruitment_process():
    """Placeholder. Real per-company recruitment-process logic (content
    banks, draw functions, custom grading) goes here once built."""
    raise NotImplementedError("Recruitment process for Zoho not yet implemented")
