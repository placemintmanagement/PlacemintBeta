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
from typing import Any, Dict, List, Optional, Tuple

from companies import get_company
from banks import mcq_static_bank, problem_bank

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


# ---- Static-bank-only MCQ generation (2026-10, zero-AI-calls pass) --------
#
# TCS is marked "source": "static_bank_only" on every section in
# companies.py. The generic dispatch in server.py (_generate_section_
# questions) still has a live-LLM fallback path for a static-bank shortfall
# on plain "mcq" sections and extra_topics -- fine for every other company,
# but explicitly forbidden for TCS (STATED-BY-USER: zero AI calls anywhere
# in the TCS OA flow). This module's draw_tcs_foundation_and_advanced()
# replaces that generic path for TCS specifically: never calls an LLM,
# never falls back to live generation, and instead RECYCLES already-seen
# static-bank questions (least-recently-seen first) once the unseen pool
# for a topic runs dry.
#
# Topic sharing: "numerical" (Foundation) and "advanced"'s Quant sub-topic
# both draw from the SAME canonical topic ("aptitude") -- same for
# "reasoning" (Foundation) and "advanced"'s Reasoning sub-topic ("reasoning").
# Because this function draws SEQUENTIALLY (numerical, verbal, reasoning,
# then advanced's two sub-topics, each one awaited to completion before the
# next starts -- never asyncio.gather'd), each draw's mark-seen write is
# already persisted before the next draw's unseen-exclusion query runs, so
# "never repeat within a single attempt" falls out of the ordering alone,
# with no separate in-process exclusion set needed.
#
# Sibling-borrow: ONLY defined for "advanced"'s two sub-topics, since they
# are the one place TCS actually has two topics living in the same section.
# Foundation's three sections (numerical/verbal/reasoning) are each the only
# topic in their own section -- there is no sibling to borrow from, so a
# shortfall there is BLOCKED (TCSBankBlockedError) rather than silently
# pulling unrelated-topic content into a Foundation section.


class TCSBankBlockedError(RuntimeError):
    """Raised when a TCS section's static bank (plus sibling-borrow, where
    defined) cannot supply enough DISTINCT questions for one attempt's draw
    of that topic -- the one case where recycling itself cannot save the
    draw, since recycling only avoids CROSS-attempt repeats, not the
    within-one-attempt uniqueness requirement. Caller (server.py) turns this
    into generation_status="failed" with a clear message, and a synchronous
    pre-check in start_oa (check_tcs_static_feasibility) tries to catch the
    same condition before an attempt is even created, where possible."""

    def __init__(self, section_key: str, topic: str, needed: int, available: int):
        self.section_key = section_key
        self.topic = topic
        self.needed = needed
        self.available = available
        super().__init__(
            f"TCS static bank too small for section {section_key!r} (topic {topic!r}): "
            f"this attempt needs {needed} distinct questions, the bank only has {available} total."
        )


# Foundation section key -> its one canonical topic (no sibling in-section).
_FOUNDATION_TOPIC = {"numerical": "aptitude", "verbal": "verbal", "reasoning": "reasoning"}


async def _draw_one_topic(attempt_id: str, user_id: str, topic: str, count: int) -> Tuple[List[dict], int]:
    """One seeded, recycle-aware, never-live draw. Returns (items, unfilled)."""
    if count <= 0:
        return [], 0
    rng = random.Random(f"tcs-static:{attempt_id}:{topic}")
    items, _reused, unfilled = await mcq_static_bank.sample_static_with_reuse(user_id, topic, count, rng=rng)
    return items, unfilled


async def draw_tcs_foundation_and_advanced(
    attempt_id: str, user_id: str, sections: List[Dict[str, Any]],
) -> Dict[str, List[dict]]:
    """Draws every TCS MCQ section's questions (numerical/verbal/reasoning/
    advanced) SEQUENTIALLY, static-bank-only, with least-recently-seen
    recycling and same-section sibling-borrow for Advanced. Never calls an
    LLM. Raises TCSBankBlockedError if a section genuinely cannot be filled
    (bank, even combined with sibling-borrow where defined, is smaller than
    this attempt's draw for that topic).

    Idempotent per section: a section whose `questions` list in `sections`
    is already non-empty is skipped entirely (returns it as-is) rather than
    drawn again -- covers a retried/duplicated generation call for the same
    attempt (the "double start must not double-mark seen" requirement)
    without needing a separate lock, since the attempt's OWN stored section
    content is the source of truth for "has this already been drawn"."""
    by_key = {s["key"]: s for s in sections}
    out: Dict[str, List[dict]] = {}

    for key, topic in _FOUNDATION_TOPIC.items():
        sec = by_key.get(key)
        if not sec:
            continue
        if sec.get("questions"):
            out[key] = sec["questions"]
            continue
        count = sec.get("count", 0)
        items, unfilled = await _draw_one_topic(attempt_id, user_id, topic, count)
        if unfilled > 0:
            bank_size = await mcq_static_bank.topic_bank_size(topic)
            raise TCSBankBlockedError(key, topic, count, bank_size)
        random.Random(f"tcs-static-shuffle:{attempt_id}:{key}").shuffle(items)
        for q in items:
            q["topic"] = sec.get("name", key)
        out[key] = items

    advanced = by_key.get("advanced")
    if advanced and not advanced.get("questions"):
        extra_topics = advanced.get("extra_topics") or []
        if len(extra_topics) != 2:
            # Defensive: the sibling-borrow logic below assumes exactly the
            # two sub-topics TCS's config has today (aptitude + reasoning).
            # If that ever changes, fail loudly instead of guessing which
            # pair is "siblings".
            raise RuntimeError(
                f"draw_tcs_foundation_and_advanced: expected exactly 2 extra_topics on "
                f"'advanced', got {len(extra_topics)} -- sibling-borrow logic needs updating."
            )
        needs = [(t["key"], t.get("name", t["key"]), t.get("count", 0)) for t in extra_topics]
        drawn: Dict[str, List[dict]] = {}
        shortfalls: Dict[str, int] = {}
        for tkey, _tname, tcount in needs:
            items, unfilled = await _draw_one_topic(attempt_id, user_id, tkey, tcount)
            drawn[tkey] = items
            shortfalls[tkey] = unfilled
        # Sibling-borrow: if one sub-topic came up short, pull the shortfall
        # as EXTRA questions from the other sub-topic's bank (same section,
        # borrowed items are tagged so the attempt doc records what happened
        # -- see _tag_borrowed below). Only raises BLOCKED if the borrow
        # itself also can't cover the gap.
        (key_a, name_a, _count_a), (key_b, name_b, _count_b) = needs
        for (short_key, short_name), (lender_key, _lender_name) in (
            ((key_a, name_a), (key_b, name_b)), ((key_b, name_b), (key_a, name_a)),
        ):
            short = shortfalls[short_key]
            if short <= 0:
                continue
            already_drawn_ids = {q["id"] for items in drawn.values() for q in items}
            borrow_rng = random.Random(f"tcs-static-borrow:{attempt_id}:{short_key}")
            borrowed, _reused, still_unfilled = await mcq_static_bank.sample_static_with_reuse(
                user_id, lender_key, short, rng=borrow_rng,
            )
            # Exclude anything already drawn for either sub-topic this
            # attempt (sample_static_with_reuse only excludes THIS topic's
            # own seen-set, not the sibling's) -- drop any accidental
            # overlap rather than risk an in-attempt duplicate.
            borrowed = [q for q in borrowed if q["id"] not in already_drawn_ids]
            if len(borrowed) < short or still_unfilled > 0:
                bank_size = await mcq_static_bank.topic_bank_size(short_key)
                lender_bank_size = await mcq_static_bank.topic_bank_size(lender_key)
                raise TCSBankBlockedError(
                    "advanced", short_key, shortfalls[short_key] + len(drawn[short_key]),
                    bank_size + lender_bank_size,
                )
            for q in borrowed:
                q["_borrowed_from_topic"] = lender_key
                q["topic"] = short_name  # still labelled as the section the candidate is in
            drawn[short_key] = drawn[short_key] + borrowed
        advanced_items = drawn[key_a] + drawn[key_b]
        random.Random(f"tcs-static-shuffle:{attempt_id}:advanced").shuffle(advanced_items)
        out["advanced"] = advanced_items
    elif advanced:
        out["advanced"] = advanced["questions"]

    return out


async def draw_tcs_coding_problems(
    attempt_id: str, user_id: str, difficulty_targets: List[str], existing_questions: Optional[List[dict]] = None,
) -> List[dict]:
    """Draws TCS's 2 coding problems (profile A: easy+medium, profile B:
    medium+medium -- problem 2 is always medium in both profiles) using
    problem_bank.sample_problems_with_reuse: unseen-first, then
    least-recently-seen recycling WITHIN each slot's own difficulty,
    seeded per (attempt_id, slot index) so the draw is reproducible. Never
    calls an LLM -- problem_bank already has no generation path at all for
    coding content, only test-result grading (see server.py's
    _grade_coding_section TCS branch for the AI-free grading side of this).

    Idempotent: if `existing_questions` is already populated (non-empty),
    returns it unchanged instead of drawing again -- same "double start
    must not double-mark seen" guarantee as
    draw_tcs_foundation_and_advanced."""
    if existing_questions:
        return existing_questions
    picks: List[dict] = []
    excluded: set = set()
    for i, target in enumerate(difficulty_targets):
        rng = random.Random(f"tcs-coding-static:{attempt_id}:{i}:{target}")
        got, unfilled = await problem_bank.sample_problems_with_reuse(
            user_id, target, exclude_ids=excluded, rng=rng,
        )
        if unfilled:
            bank_size = problem_bank.bank_size_by_difficulty(target)
            raise TCSBankBlockedError(f"coding[{i}]", target, 1, bank_size)
        picks.extend(got)
        excluded.update(p["id"] for p in got)
    for i, p in enumerate(picks):
        p.setdefault("id", f"q{i+1}")
        p["id"] = str(p["id"])
    return picks


async def check_tcs_static_feasibility() -> Optional[str]:
    """Synchronous (no per-user seen-state, no marking) feasibility check,
    called from start_oa BEFORE an attempt is created or a run is charged.
    Recycling means a topic's TOTAL bank size (not any one candidate's
    unseen subset) is what determines whether one attempt's draw can ever
    be filled without an in-attempt repeat -- so this only needs total
    counts, not a specific user_id.

    Deliberately conservative: checks each topic against its OWN combined
    attempt-need (Foundation section + Advanced's same-topic sub-count),
    WITHOUT crediting potential sibling-borrow between Advanced's two
    sub-topics. A combined aptitude+reasoning deficit that borrowing could
    theoretically still cover will be reported as infeasible here even
    though the real draw might succeed -- i.e. this can reject a start that
    would have worked, but will never accept one that then fails. Returns
    None if feasible, else a human-readable reason."""
    cfg = get_company("tcs-nqt")
    if not cfg:
        return None
    by_key = {s["key"]: s for s in cfg["sections"]}
    needs: Dict[str, int] = {}
    for key, topic in _FOUNDATION_TOPIC.items():
        sec = by_key.get(key)
        if sec:
            needs[topic] = needs.get(topic, 0) + sec.get("count", 0)
    advanced = by_key.get("advanced")
    if advanced:
        for t in advanced.get("extra_topics") or []:
            needs[t["key"]] = needs.get(t["key"], 0) + t.get("count", 0)
    for topic, needed in needs.items():
        size = await mcq_static_bank.topic_bank_size(topic)
        if size < needed:
            return (
                f"TCS's static question bank for '{topic}' has {size} questions, "
                f"fewer than the {needed} a single attempt needs. Bank is too small "
                f"for this section -- see scratchpad/tcs_bank_readiness.md."
            )
    # Coding: worst case across either profile is 1 Easy + 2 Medium (profile
    # A needs 1 Easy + 1 Medium; profile B needs 2 Medium) -- checking both
    # unconditionally, regardless of which profile this attempt will later
    # roll, keeps this check profile-draw-order-independent.
    if problem_bank.bank_size_by_difficulty("easy") < 1:
        return "TCS's coding bank has no Easy problems -- Advanced Coding profile A cannot be served."
    if problem_bank.bank_size_by_difficulty("medium") < 2:
        return "TCS's coding bank has fewer than 2 Medium problems -- Advanced Coding cannot be served."
    return None


def build_recruitment_process():
    """Placeholder for a genuinely bespoke TCS content bank (dedicated
    question authoring, custom grading), if that's ever built -- distinct
    from the thin orchestration wrappers above, which just call into the
    shared generic mechanisms TCS's config already uses today."""
    raise NotImplementedError("Bespoke TCS recruitment process not yet implemented")
