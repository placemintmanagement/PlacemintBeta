# -*- coding: utf-8 -*-
"""TCS NQT recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up),
rebuilt 2026-10 (owner-reviewed source pass) against the owner's explicit
per-field decisions. This file does NOT contain any real generation/grading
logic -- that stays exactly where it already lives, in server.py's shared,
generic dispatch functions and companies.py's data. This module exists so
someone opening `departments/.../tcs/` sees TCS's actual OA shape and which
shared mechanisms it uses, without having to dig through companies.py's full
15-company data blob or server.py's full dispatch chain.

TAGGING CONVENTION (2026-10, owner decision -- applies to every number in
this file and in companies.py's "tcs-nqt" entry):
  OFFICIAL-TCS            -- from https://www.tcs.com/careers/india/tcs-all-india-nqt-hiring,
                             the source of truth where it speaks at all.
  STATED-BY-USER          -- the repo owner told me this directly.
  USER-SUPPLIED-SECONDARY -- a screenshot / AI summary the owner supplied.
  PUBLIC-SOURCE-ONLY      -- a prep-site report (e.g. FACE Prep), not TCS itself.
  CONFLICTING-SOURCES     -- two sources disagree; the value picked is noted.
  INTERPOLATED            -- my own guess/placeholder, pending real data,
                             same meaning as capgemini_interview/core.py's
                             own INTERPOLATED tag.

TCS NQT structure (source of truth: companies.py, id="tcs-nqt";
get_config() below re-exports it verbatim):
  Part A -- Foundation (mandatory, 3 sections, all plain "mcq"):
    - "numerical"  Numerical Ability  (20 Qs, 25 min) -- OFFICIAL-TCS minutes;
      count is USER-SUPPLIED-SECONDARY (screenshot/AI summary), PUBLIC-SOURCE-ONLY
      agrees (FACE Prep).
    - "verbal"     Verbal Ability     (25 Qs, 25 min) -- same tagging as above.
    - "reasoning"  Reasoning Ability  (20 Qs, 25 min) -- same tagging as above.
    Foundation total: 65 Qs, 75 min (OFFICIAL-TCS for the per-section minutes
    and their sum). These three go through server.py's fully generic mcq
    path (pool-or-live-verify / static-bank split), same as any bare "mcq"
    section company-wide -- no wrapper needed for them.
  Part B -- Advanced (OPTIONAL -- see PART_B_OPTIONAL_NOTE below):
    - "advanced"  Advanced Quantitative + Reasoning Ability (mcq, 15 Qs,
      25 min, shared window) -- OFFICIAL-TCS for the minutes and the
      "shares one window" structure. The 15-question total is
      USER-SUPPLIED-SECONDARY ("14-15"); the 10 Quant / 5 Reasoning split is
      PUBLIC-SOURCE-ONLY (FACE Prep) -- TCS itself does not publish the
      split. Handled purely by companies.py's own `extra_topics` list (no
      wrapper needed -- server.py's generic extra_topics dispatch already
      splits a section by topic from that list alone).
    - "coding"    Advanced Coding (coding, 2 problems, 90 min) --
      STATED-BY-USER for the count (2, not an earlier guess of 3); 90
      minutes is OFFICIAL-TCS. See apply_coding_profile() below for the
      per-attempt profile draw.
    Advanced total: 15 + 2 = 17 "items" (15 MCQs + 2 coding problems), 115 min.
  GRAND TOTAL: 65 + 15 + 2 = 82 questions, 75 + 115 = 190 minutes
  (OFFICIAL-TCS for the 190-minute figure; the question count is this
  module's own sum of the component counts above, each individually tagged).

Track estimate (Ninja / Digital / Prime): TCS publishes no cutoffs and does
not state how scores decide the track -- see services/tcs_tiers.py, whose
every threshold is INTERPOLATED. The one rule that IS OFFICIAL-TCS (via the
official page's "mandatory if you aspire for a Digital or Prime offer"
wording): skipping Part B caps the estimate at Ninja. scoring_mode stays
"sectional".

Interview: the official page states only that "the skill chosen at
registration affects the interview evaluation" -- OFFICIAL-TCS, and the ONLY
fact it gives about the interview at all. Nothing else about TCS's
interview process (stage structure, technical/managerial/HR split, timing,
rubrics) has been built or even stubbed anywhere in this codebase; any such
detail added later must be tagged INTERPOLATED or PUBLIC-SOURCE-ONLY,
never written as a plain fact, until real evidence exists.
"""
from __future__ import annotations
import random
from typing import Any, Dict, List, Optional

from companies import get_company

# PART B OPTIONAL (companies.py config flag: "part_b_optional": True on the
# tcs-nqt entry, "optional": True on the "advanced" and "coding" sections).
# OFFICIAL-TCS wording, shown to the candidate verbatim when offering the
# choice to stop after Foundation (server.py's POST /oa/{id}/finish-part-a,
# frontend's OARunner.jsx Part-B gate): the official page says Part B is
# "mandatory if you aspire for a Digital or Prime offer" -- everyone is
# still encouraged to attempt both parts; skipping Part B is a candidate
# choice, not a track decision made for them, and (per services/tcs_tiers.py)
# caps the estimate at Ninja.
PART_B_OPTIONAL_NOTE = (
    "Part B (Advanced) is optional. TCS's own guidance: it is "
    '"mandatory if you aspire for a Digital or Prime offer." You can finish '
    "after Foundation for a Ninja-track estimate, or continue to Part B for "
    "a chance at Digital or Prime."
)

# Coding languages (STATED-BY-USER: C, C++, Java, Python). C# was requested
# "only if the sandbox already supports it" -- confirmed NOT supported
# (services/code_runner.py's SUPPORTED_LANGUAGES = ["python", "javascript",
# "c", "cpp", "java"], no C# runner registered), so it is excluded here.
# "javascript" is in the sandbox's general list but was not part of the
# user's requested set for TCS specifically, so it is excluded too.
TCS_CODING_LANGUAGES = ["c", "cpp", "java", "python"]  # STATED-BY-USER (+ sandbox-support check)


def get_config() -> Optional[Dict[str, Any]]:
    """TCS's full section config, straight from companies.py (the source of
    truth) -- so the real OA shape is visible without leaving this file."""
    return get_company("tcs-nqt")


# ---- Advanced Coding: per-attempt profile draw (INTERPOLATED 50/50) -------
# INTERPOLATED: "each attempt draws, with seeded RNG, profile A = 1 easy +
# 1 medium or profile B = 2 medium; weights 50/50" -- the OWNER'S decision on
# HOW to draw (seeded RNG, no repeats within an attempt), the 50/50 WEIGHT
# ITSELF is INTERPOLATED (TCS states no profile-mix ratio anywhere).
# "No repeats within an attempt" is already guaranteed generically by
# server.py's _generate_section_questions: when a section carries
# `difficulty_targets` (a list, one entry per problem), each problem is
# sampled individually with the PRIOR picks' ids added to the exclusion set
# before the next draw (see server.py's difficulty_targets loop) -- so
# passing a 2-entry list here, rather than a single blended difficulty, is
# sufficient on its own; this function does not need to re-implement
# exclusion itself.
_PROFILE_A = ["easy", "medium"]   # 1 easy + 1 medium
_PROFILE_B = ["medium", "medium"]  # 2 medium


def roll_coding_profile(attempt_id: str) -> Dict[str, Any]:
    """Seeded per-attempt 50/50 draw between profile A and profile B.
    Seeded on `attempt_id` (not the global `random` module) so the draw is
    reproducible for debugging a specific attempt and independent of
    generation order/concurrency with other attempts -- same reasoning as
    this repo's other seeded-RNG pickers (e.g.
    capgemini_interview/core.py's dave_pick_hr_first_two accepting an
    optional rng)."""
    rng = random.Random(f"tcs-coding-profile:{attempt_id}")
    profile = "A" if rng.random() < 0.5 else "B"  # INTERPOLATED weight (50/50)
    return {"profile": profile, "difficulty_targets": _PROFILE_A if profile == "A" else _PROFILE_B}


def apply_coding_profile(sections: List[Dict[str, Any]], attempt_id: str) -> List[Dict[str, Any]]:
    """Called once, at /oa/start, on the attempt's own copy of its section
    list (never on companies.py's shared config dict) -- sets this one
    attempt's "coding" section `difficulty_targets` to its rolled profile.
    A no-op pass-through for any section list that doesn't have a "coding"
    key (defensive; every call site today only ever passes TCS's own
    sections, but this function doesn't assume that)."""
    roll = roll_coding_profile(attempt_id)
    out = []
    for s in sections:
        if s.get("key") == "coding":
            s = {**s, "difficulty_targets": roll["difficulty_targets"], "coding_profile": roll["profile"]}
        out.append(s)
    return out


def build_recruitment_process():
    """Placeholder for a genuinely bespoke TCS content bank (dedicated
    question authoring, custom grading), if that's ever built -- distinct
    from the thin orchestration wrappers above, which just call into the
    shared generic mechanisms TCS's config already uses today."""
    raise NotImplementedError("Bespoke TCS recruitment process not yet implemented")
