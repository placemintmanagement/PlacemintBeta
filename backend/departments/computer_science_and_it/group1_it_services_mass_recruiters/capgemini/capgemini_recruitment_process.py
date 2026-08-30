# -*- coding: utf-8 -*-
"""Capgemini recruitment process -- Round 1 (Communication Assessment).

Merged (2026-08, backend restructure) from the four formerly-separate
capgemini_round1_section1..4.py modules into one file, one per company,
matching this repo's department/group/company folder convention. This is a
structural merge only -- concatenation + de-duplication of shared imports,
NOT a rewrite. All logic, docstrings, and behavior are preserved from the
original four files; only symbols that collided under the same name across
sections were renamed to be section-specific (see the collision list
below). Nothing in server.py's call sites changed shape -- only the module
path and these renamed symbols.

Symbol collisions found during the merge (all four files independently
defined some of these under the same name) and how they were resolved,
confirmed by the repo owner before merging:
  - `_strip_for_client()` (three different bodies) -> `_strip_grammar_for_client()`
    (Section 1), `_strip_business_writing_for_client()` (Section 2),
    `_strip_situational_for_client()` (Section 3). Section 4 never had this
    function (reading comprehension is never stripped by this module --
    see that section's own docstring below) so nothing to rename there.
  - `_CLIENT_SAFE_FIELDS` (three different tuples) -> `SECTION1_CLIENT_SAFE_FIELDS`,
    `SECTION2_CLIENT_SAFE_FIELDS`, `SECTION3_CLIENT_SAFE_FIELDS`.
  - `TARGET_QUESTION_COUNT` (three different values: 10/6/4) ->
    `SECTION1_TARGET_QUESTION_COUNT`, `SECTION3_TARGET_QUESTION_COUNT`,
    `SECTION4_TARGET_QUESTION_COUNT`. (Section 2 used a differently-named
    `TARGET_SCENARIO_COUNT` from the start, so no collision/rename there.)
  None of these renamed symbols are referenced anywhere outside this
  module (confirmed via a repo-wide search before merging) -- server.py
  only ever calls the fully-qualified, uniquely-named draw_sectionN_
  questions()/grade_business_writing_submission() functions, which are
  unchanged.

Wired into the live OA flow as part of Capgemini's "capgemini_round1"
section in server.py's _generate_section_questions /
_grade_capgemini_round1_section / _strip_answer_fields_for_response.
Both existing security fixes remain untouched by this merge (their code
lives in server.py, not here): the answer-key whitelist applied in get_oa,
and the whole-attempt completion gate on the /review endpoint.

------------------------------------------------------------------------
Company OA structure summary (2026-08, thin-orchestration-layer pass)
------------------------------------------------------------------------
Added as documentation only -- no logic below this docstring was touched.
Source of truth is always the "capgemini" entry in companies.py; this is
a plain-English summary of it, not a second copy of the data:

  Round 1: Communication Assessment ("round1_communication", type
    capgemini_round1, 60 min, single shared timer) -- the 6 sub-parts this
    module implements (grammar/business_writing/situational/reading_comp/
    listening_comp/spoken_sim).
  Round 2: Online Assessment (formerly "Round 1"), 4 sections:
    - "technical" (R2a): pseudocode base (16 Qs) + extra_topics blend of
      OOPS/DBMS/OS/CN (6 each) -- generated via the SHARED
      server._generate_extra_topics helper, same mechanism every other
      company's cs-fundamentals-style block uses. Not implemented in this
      module; genuinely shared code, stays in server.py.
    - "essay" (R2b): plain essay section, no target_words override.
    - "cognitive" (R2c): registry-driven gamified_round (game_types.py /
      gamified_round.py), not an LLM-generated section.
    - "behavioral" (R2d): unscored (weight 0.0) plain mcq.
  Round 3: Coding Round (formerly "Round 2") -- 2 plain DSA problems, no
    difficulty_targets/automata_fix.

No wrapper functions are added in this pass for the Round 2/3 shared
mechanisms (extra_topics, gamified_round, plain coding): server.py already
imports THIS module (capgemini_recruitment_process) for the Round 1
dispatch, so this file importing back from server.py would be a direct
circular import -- unlike every other company file, which server.py does
NOT import today. See the sibling company files' docstrings for the same
mechanisms wrapped safely where no such cycle exists.
"""
from __future__ import annotations
import random
import re
from typing import Any, Dict, List, Optional

from companies import get_company
from services.ai_service import call_json_gpt, wrap_untrusted, GRADING_INJECTION_DEFENSE, flag_suspicious_grading


def get_config() -> Optional[Dict[str, Any]]:
    """Returns Capgemini's full section config straight from companies.py
    (the source of truth) -- so anyone opening this file can see the real
    OA shape without digging through the shared companies.py data blob."""
    return get_company("capgemini")

# =============================================================================
# ---- Section 1: Grammar & Sentence Correction ----
# =============================================================================
# Draw logic only. Question content lives in Mongo (`capgemini_round1_bank`,
# section="grammar_correction"), authored + staged via the scratchpad
# pipeline under capgemini_round1_pipeline/ and inserted separately.
#
# A pure function that takes an already-fetched pool of question docs (not
# a DB connection itself) and returns a random draw. The actual Mongo fetch
# happens in server.py's dispatch branch.
#
# strip=True (default) returns client-safe dicts (question_id/prompt/
# options only) -- this is what direct callers/tests expect and matches
# this module's original contract. The live generation path calls with
# strip=False: the FULL doc (including correct_option) must be PERSISTED
# into oa_attempts so submit_section can re-derive correctness later --
# stripping instead happens once, at get_oa response time
# (_strip_answer_fields_for_response in server.py), matching the
# established "store full, strip at response" security pattern used
# everywhere else in this codebase (see the 2026-08 get_oa answer-leak
# audit/fix).
#
# NOTE on the E-correct ("No correction required") ratio: this module's
# docstring originally assumed a ~20% E-correct target based on an earlier
# discussion, but a direct check against the live bank found the actual
# ratio is 12/130 = 9.2%, not ~20%. That's the real bank composition -- this
# module verifies the draw preserves whatever the ACTUAL ratio is, and this
# discrepancy is flagged here rather than silently designing around the
# wrong assumed number.

SECTION1_TARGET_QUESTION_COUNT = 10

SECTION1_CLIENT_SAFE_FIELDS = ("question_id", "prompt", "options")


def _strip_grammar_for_client(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Whitelist projection, NOT gamified_round.strip_answer()'s blacklist
    approach -- deliberately different here because an MCQ bank doc carries
    purely-internal audit fields (ground_truth_source, verified_by,
    source_batch, date_added, difficulty) that have no client-facing
    purpose at all, unlike a puzzle doc where most fields (grid, shapes,
    colors, ...) ARE legitimate client content and only correctAnswer/
    explanation need dropping. Whitelisting question_id/prompt/options is
    simpler and safer here: correct_option and explanation are excluded by
    construction, not by remembering to blacklist them."""
    return {k: doc[k] for k in SECTION1_CLIENT_SAFE_FIELDS}


def draw_section1_questions(
    question_pool: List[Dict[str, Any]],
    rng: Optional[random.Random] = None,
    strip: bool = True,
) -> List[Dict[str, Any]]:
    """Randomly selects exactly SECTION1_TARGET_QUESTION_COUNT (10)
    questions from `question_pool` (a list of capgemini_round1_bank docs
    with section="grammar_correction"), without repeats within the draw.

    strip=True (default): client-safe dicts (question_id/prompt/options),
    correct_option and explanation excluded. strip=False: full docs
    unchanged, for the generation/persist path -- see module docstring.

    Raises ValueError if the pool has fewer than SECTION1_TARGET_QUESTION_COUNT
    questions -- there's no partial-draw fallback here (unlike
    mcq_static_bank.sample_static's graceful shortfall) since this bank is
    a large, fixed, non-per-user-tracked pool; a shortfall here would mean
    the bank itself is too small, not that a user has exhausted their view
    of it."""
    rng = rng or random.Random()
    if len(question_pool) < SECTION1_TARGET_QUESTION_COUNT:
        raise ValueError(
            f"question pool too small to draw {SECTION1_TARGET_QUESTION_COUNT} questions "
            f"(have {len(question_pool)})"
        )
    selected = rng.sample(question_pool, SECTION1_TARGET_QUESTION_COUNT)
    if not strip:
        return [dict(q) for q in selected]
    return [_strip_grammar_for_client(q) for q in selected]


# =============================================================================
# ---- Section 2: Business Communication Writing ----
# =============================================================================
# Draw and grading logic. Scenario content lives in Mongo
# (`capgemini_round1_bank`, section="business_writing"), authored + staged
# via the scratchpad pipeline under capgemini_round1_pipeline/ and inserted
# separately.
#
# Generation/grading separation: scenario `context` and `rubric` are
# authored content (no LLM call involved at all -- hand-written, see the
# scratchpad pipeline). Grading is a genuinely separate LLM call, invoked
# only after a candidate submits their email, and must NEVER regenerate or
# "improve" the rubric it's handed -- it only scores the candidate's text
# against the fixed rubric it's given.

TARGET_SCENARIO_COUNT = 2

# EssaySection (OARunner.jsx) shows candidates only topic/instructions/
# min_words/max_words for free-text prompts -- no rubric detail at all, even
# though essay grading also happens against an internal rubric-like scoring
# prompt. Business writing follows that exact precedent: candidates see the
# scenario situation and enough metadata to write an appropriate response
# (who it's to, what tone), but not the rubric's criteria/weights/max_score
# -- those are grading-internal, same category as correct_option elsewhere.
SECTION2_CLIENT_SAFE_FIELDS = ("scenario_id", "context", "recipient_type", "tone_expected")


def _strip_business_writing_for_client(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {k: doc[k] for k in SECTION2_CLIENT_SAFE_FIELDS}


def draw_section2_questions(
    scenario_pool: List[Dict[str, Any]],
    rng: Optional[random.Random] = None,
    strip: bool = True,
) -> List[Dict[str, Any]]:
    """Randomly selects exactly TARGET_SCENARIO_COUNT (2) scenarios from
    `scenario_pool` (a list of capgemini_round1_bank docs with
    section="business_writing"), without repeats within the draw.

    strip=True (default): client-safe dicts (scenario_id/context/
    recipient_type/tone_expected) -- no rubric, matching EssaySection's
    existing no-rubric-shown precedent. strip=False: full docs including
    `rubric`, for the generation/persist path -- grade_business_writing_
    submission needs the rubric from the STORED attempt document later,
    so it can't be stripped away before persisting (same "store full,
    strip at response" reasoning as Sections 1 and 3).

    Raises ValueError if the pool has fewer than TARGET_SCENARIO_COUNT
    scenarios."""
    rng = rng or random.Random()
    if len(scenario_pool) < TARGET_SCENARIO_COUNT:
        raise ValueError(
            f"scenario pool too small to draw {TARGET_SCENARIO_COUNT} scenarios "
            f"(have {len(scenario_pool)})"
        )
    selected = rng.sample(scenario_pool, TARGET_SCENARIO_COUNT)
    if not strip:
        return [dict(s) for s in selected]
    return [_strip_business_writing_for_client(s) for s in selected]


# ---- Attempt/record status -------------------------------------------------
# Grading is a real network round-trip (LLM call), not an instant
# index-comparison like MCQ grading -- an attempt record can sit in
# "grading_pending" between submission and the grading call resolving.
# Round 1's overall round_status/gating must not block on this resolving in
# real time: gating off ROUND1_PASS_THRESHOLD is already a no-op until that
# threshold is configured (informational-only default), so a Section 2/3
# item stuck in "grading_pending" cannot itself stall round progression.
STATUS_PENDING = "grading_pending"
STATUS_GRADED = "graded"
STATUS_FAILED = "grading_failed"


def business_writing_grading_prompt(scenario: Dict[str, Any], email_text: str) -> str:
    """Only criterion + description go into the prompt -- weight and
    max_score are applied programmatically in score_business_writing_email,
    never by the LLM (per spec: the model scores 0-5 per criterion, code
    does the weighting/scaling afterward)."""
    rubric_lines = "\n".join(
        f"- {c['criterion']}: {c['description']}" for c in scenario["rubric"]
    )
    return (
        "You are grading a candidate's business email response for a "
        "workplace communication assessment.\n\n"
        f"SCENARIO CONTEXT: {scenario['context']}\n"
        f"RECIPIENT TYPE: {scenario['recipient_type']}\n"
        f"EXPECTED TONE: {scenario['tone_expected']}\n\n"
        f"CANDIDATE'S EMAIL:\n{wrap_untrusted(email_text)}\n\n"
        "Score the email against EXACTLY these criteria, and no others:\n"
        f"{rubric_lines}\n\n"
        "For each criterion, score 0-5:\n"
        "  0 = criterion entirely absent or failed\n"
        "  1-2 = attempted but weak, unclear, or misses the point of the criterion\n"
        "  3-4 = present and mostly effective, minor issues only\n"
        "  5 = criterion fully and clearly met\n"
        "Score STRICTLY against the description given for each criterion above -- "
        "not your own general idea of 'good business writing'. Do not invent or "
        "consider criteria that aren't listed.\n\n"
        "Return JSON: {scores: [{criterion, score (integer 0-5), justification "
        "(1-2 sentences, specific to what the candidate actually wrote)}, ... "
        "one entry per criterion listed above, same order]}."
    )


def score_business_writing_email(scenario: Dict[str, Any], grading_result: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic post-processing (NOT the LLM's job). Reads weight/
    max_score straight off scenario["rubric"] rather than assuming 6x5=30 --
    so if per-criterion weighting ever stops being uniform, this function
    doesn't need to change, only the rubric data does.

    Missing/malformed criteria in grading_result score 0 rather than raising
    -- a partially-malformed LLM response shouldn't crash the submission."""
    scores_by_criterion = {
        s.get("criterion"): s for s in (grading_result.get("scores") or [])
    }
    breakdown: List[Dict[str, Any]] = []
    raw_total = 0.0
    max_total = 0.0
    for rubric_item in scenario["rubric"]:
        criterion = rubric_item["criterion"]
        weight = rubric_item.get("weight", 1)
        max_score = rubric_item.get("max_score", 5)
        entry = scores_by_criterion.get(criterion) or {}
        raw_score = entry.get("score", 0)
        try:
            raw_score = max(0, min(max_score, int(raw_score)))
        except (TypeError, ValueError):
            raw_score = 0
        raw_total += raw_score * weight
        max_total += max_score * weight
        breakdown.append({
            "criterion": criterion,
            "score": raw_score,
            "max_score": max_score,
            "weight": weight,
            "justification": entry.get("justification", ""),
        })
    scaled_score = round((raw_total / max_total) * 100, 1) if max_total else 0.0
    flag_reason = flag_suspicious_grading(
        [(b["score"], b["max_score"]) for b in breakdown],
        [b["justification"] for b in breakdown],
    )
    return {
        "raw_total": raw_total,
        "max_total": max_total,
        "scaled_score": scaled_score,
        "breakdown": breakdown,
        "flagged_for_review": flag_reason is not None,
        "flag_reason": flag_reason,
    }


async def grade_business_writing_submission(scenario: Dict[str, Any], email_text: str) -> Dict[str, Any]:
    """The actual async grading call. Fully separate from scenario
    generation -- never invoked in the same call/session that created the
    scenario or its rubric (there IS no generation call for this content;
    scenarios are hand-authored, see module docstring). Uses call_json_gpt
    (GPT-5.4 Mini via the OpenAI path), matching this codebase's existing
    convention for open-answer grading (grade_essay_prompt, grade_spoken_
    response_prompt in services/ai_service.py) rather than the Anthropic
    path used for generation/verification tasks.

    Returns a dict with `status` plus (on success) raw_total/max_total/
    scaled_score/breakdown -- ready to store on the candidate's attempt
    record. Never raises: a failed or unparseable grading call resolves to
    STATUS_FAILED with zero scores rather than propagating an exception,
    since one candidate's malformed LLM response shouldn't 500 the request.
    """
    grading_result = await call_json_gpt(
        "You are a strict, fair evaluator of workplace business emails. Return only strict JSON.\n\n"
        + GRADING_INJECTION_DEFENSE,
        business_writing_grading_prompt(scenario, email_text),
    )
    if not grading_result or not grading_result.get("scores"):
        return {"status": STATUS_FAILED, "raw_total": 0, "max_total": 0, "scaled_score": 0.0, "breakdown": []}
    scored = score_business_writing_email(scenario, grading_result)
    return {"status": STATUS_GRADED, **scored}


# =============================================================================
# ---- Section 3: Task Situational Awareness & Response ----
# =============================================================================
# Draw logic only. Question content lives in Mongo (`capgemini_round1_bank`,
# section="situational_response"), authored + staged via the scratchpad
# pipeline under capgemini_round1_pipeline/ and inserted separately.
#
# strip=True (default) returns client-safe dicts; strip=False returns full
# docs for the generation/persist path (so submit_section can re-derive
# correctness from the stored attempt later) -- see Section 1's comments
# above for the full "store full, strip at response" reasoning.

SECTION3_TARGET_QUESTION_COUNT = 6

SECTION3_CLIENT_SAFE_FIELDS = ("question_id", "scenario_prompt", "options")


def _strip_situational_for_client(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Whitelist projection -- same reasoning as
    _strip_grammar_for_client above: this bank's docs carry purely-internal
    audit fields (verified_by, source_batch, date_added) alongside
    sender_type/urgency (not client-facing per the target return shape)
    and correct_option/explanation (answer-revealing). Whitelisting
    question_id/scenario_prompt/options excludes all of these by
    construction."""
    return {k: doc[k] for k in SECTION3_CLIENT_SAFE_FIELDS}


def draw_section3_questions(
    question_pool: List[Dict[str, Any]],
    rng: Optional[random.Random] = None,
    strip: bool = True,
) -> List[Dict[str, Any]]:
    """Randomly selects exactly SECTION3_TARGET_QUESTION_COUNT (6)
    questions from `question_pool` (a list of capgemini_round1_bank docs
    with section="situational_response"), without repeats within the draw.

    strip=True (default): client-safe dicts (question_id/scenario_prompt/
    options). strip=False: full docs unchanged, for the generation/persist
    path.

    Raises ValueError if the pool has fewer than SECTION3_TARGET_QUESTION_COUNT
    questions, same reasoning as Section 1's draw function -- this is a
    fixed bank-size guard, not a per-user shortfall case."""
    rng = rng or random.Random()
    if len(question_pool) < SECTION3_TARGET_QUESTION_COUNT:
        raise ValueError(
            f"question pool too small to draw {SECTION3_TARGET_QUESTION_COUNT} questions "
            f"(have {len(question_pool)})"
        )
    selected = rng.sample(question_pool, SECTION3_TARGET_QUESTION_COUNT)
    if not strip:
        return [dict(q) for q in selected]
    return [_strip_situational_for_client(q) for q in selected]


# =============================================================================
# ---- Section 4: Workplace Reading Comprehension ----
# =============================================================================
# Draw logic only. Passage content lives in Mongo (`capgemini_round1_bank`,
# section="reading_comprehension"), authored + staged via the scratchpad
# pipeline under capgemini_round1_pipeline/ and inserted separately.
#
# Given a pool of passage docs (each carrying 1 or 2 questions), draws
# passages until exactly 4 questions have been accumulated, since the bank
# deliberately mixes 1-question and 2-question passages rather than using a
# fixed passage-count split. This section never strips its own output (no
# _strip_*_for_client here, unlike Sections 1-3) -- that's the caller's
# responsibility when preparing a client-facing response, same as every
# other bank in this codebase.

SECTION4_TARGET_QUESTION_COUNT = 4


def draw_section4_questions(
    passage_pool: List[Dict[str, Any]],
    rng: Optional[random.Random] = None,
) -> List[Dict[str, Any]]:
    """Randomly selects passages from `passage_pool` such that the total
    number of questions across the selected passages is exactly
    SECTION4_TARGET_QUESTION_COUNT (4) -- never more, never fewer.

    Only passages with 1 or 2 questions are supported (matches the bank's
    design: ~60% 1-question, ~40% 2-question). The three ways to reach
    exactly 4 are: four 1-question passages, two 1-question + one
    2-question passage, or two 2-question passages -- one combination is
    picked at random (uniformly among shapes that are actually satisfiable
    given the pool's current composition), then specific passages are
    sampled at random within that shape.

    Does not mutate or strip any passage content (e.g. correct_option) --
    that's the caller's responsibility when preparing a client-facing
    response, same as every other bank in this codebase.

    Raises ValueError if the pool doesn't have enough passages of either
    type to assemble any valid 4-question combination."""
    rng = rng or random.Random()
    one_q = [p for p in passage_pool if len(p.get("questions", [])) == 1]
    two_q = [p for p in passage_pool if len(p.get("questions", [])) == 2]

    shapes = []
    if len(one_q) >= 4:
        shapes.append("four_ones")
    if len(one_q) >= 2 and len(two_q) >= 1:
        shapes.append("two_ones_one_two")
    if len(two_q) >= 2:
        shapes.append("two_twos")
    if not shapes:
        raise ValueError(
            f"passage pool too small to assemble {SECTION4_TARGET_QUESTION_COUNT} questions "
            f"(have {len(one_q)} one-question, {len(two_q)} two-question passages)"
        )

    shape = rng.choice(shapes)
    if shape == "four_ones":
        selected = rng.sample(one_q, 4)
    elif shape == "two_ones_one_two":
        selected = rng.sample(one_q, 2) + rng.sample(two_q, 1)
    else:
        selected = rng.sample(two_q, 2)

    total_questions = sum(len(p["questions"]) for p in selected)
    assert total_questions == SECTION4_TARGET_QUESTION_COUNT, (
        f"internal error: drew {total_questions} questions, expected {SECTION4_TARGET_QUESTION_COUNT}"
    )
    return selected


# =============================================================================
# ---- Section 5: Workplace Listening Comprehension ----
# =============================================================================
# Draw logic only. Clip content lives in Mongo (`capgemini_round1_bank`,
# section="listening_comprehension"), authored + staged via the scratchpad
# pipeline under capgemini_round1_pipeline/ and inserted separately (22
# clips / 31 questions, 11 dialogue / 11 monologue, 1-2 questions per clip).
#
# Same variable question-accumulation shape as Section 4 (draws clips until
# exactly 4 questions have been accumulated) -- reuses that exact
# shape-selection algorithm below, since this bank was deliberately authored
# with the same ~60/40 one-question/two-question split.
#
# UNLIKE every other section here: every clip also carries `tts_status`
# ("pending" | "generated") and, once generated, `audio_url`. A clip with no
# real audio yet must NEVER be drawable -- this is a listening test, so a
# clip a candidate can't actually hear is not a usable question, regardless
# of how complete its script/question content is. `draw_section5_questions`
# filters `clip_pool` down to `tts_status == "generated"` BEFORE running the
# shape-selection logic, so the accumulation math only ever sees clips that
# are actually playable. As of this writing (2026-08, code-wiring pass) the
# live bank has 0 "generated" clips -- audio generation is a separate,
# still-blocked task (see that task's own report for why) -- so calling this
# function against the live bank today will deterministically raise
# ValueError. That's correct, expected behavior, not a bug: this function is
# written and tested now, but is NOT wired into server.py's live
# capgemini_round1 generation branch yet, specifically so that fact doesn't
# break Sections 1-4, which remain fully generated and live today.

SECTION5_TARGET_QUESTION_COUNT = 4

# Top-level (clip) whitelist. Uses the NATURAL id field `clip_id`, not
# `id` -- same reasoning the module docstring above gives for why
# server.py doesn't reuse Sections 1-3's own _strip_*_for_client helpers:
# at the point this module's own draw_section5_questions(strip=True) runs
# (called directly, without going through server.py's generation branch),
# no `id` field exists yet -- only `clip_id` does. server.py's OWN,
# separate whitelist (_R1_LISTENING_CLIP_FIELDS) uses `id` instead, because
# ITS caller (the capgemini_round1 generation branch) copies
# `id = clip_id` before ever stripping anything -- same split Sections 1-3
# already use (SECTION2_CLIENT_SAFE_FIELDS uses `scenario_id`, not `id`,
# for the identical reason). `script` (the spoken transcript) is
# deliberately excluded: showing the transcript would let a candidate read
# instead of listen, defeating the section's whole purpose -- a genuine
# design choice, not an oversight inherited from a stricter section.
SECTION5_CLIP_CLIENT_SAFE_FIELDS = ("clip_id", "clip_type", "speaker_count", "audio_url", "estimated_duration_seconds")

# Nested per-question whitelist, one level down inside each clip's
# `questions` list (same nesting shape as reading_comprehension's
# passage-level `questions`). `question_id` is REQUIRED here despite not
# being literally listed in the original wiring-task spec ("prompt/options
# only") -- omitting it would leave the frontend with no key to submit an
# answer under for that specific sub-question, since (exactly like
# reading_comprehension) each nested question is graded by its own
# question_id, not by the parent clip's id. `question_focus` is also
# included, matching SECTION3/reading_comprehension's SUBQ whitelist shape
# exactly (harmless category metadata, not an answer-revealing field).
SECTION5_QUESTION_CLIENT_SAFE_FIELDS = ("question_id", "prompt", "question_focus", "options")


def _strip_listening_for_client(clip: Dict[str, Any]) -> Dict[str, Any]:
    """Whitelist projection -- module-internal convenience strip, mirroring
    Sections 1-3's own `_strip_*_for_client` helpers (used when this
    function is called directly with strip=True, e.g. standalone/test use).
    The LIVE server.py dispatch path calls this module's draw functions
    with strip=False and does its own separate, later whitelisting at
    get_oa response time (see _strip_capgemini_round1_question in
    server.py) -- same "store full, strip at response" split every other
    Round 1 section already uses."""
    item = {k: clip[k] for k in SECTION5_CLIP_CLIENT_SAFE_FIELDS if k in clip}
    item["questions"] = [
        {k: q[k] for k in SECTION5_QUESTION_CLIENT_SAFE_FIELDS if k in q}
        for q in (clip.get("questions") or [])
    ]
    return item


def draw_section5_questions(
    clip_pool: List[Dict[str, Any]],
    rng: Optional[random.Random] = None,
    strip: bool = True,
) -> List[Dict[str, Any]]:
    """Randomly selects clips from `clip_pool` such that the total number of
    questions across the selected clips is exactly SECTION5_TARGET_QUESTION_
    COUNT (4) -- never more, never fewer. Same shape-selection algorithm as
    draw_section4_questions (four 1-question clips, two 1-question + one
    2-question clip, or two 2-question clips), applied AFTER filtering
    clip_pool down to tts_status == "generated" only.

    strip=True (default): client-safe dicts via _strip_listening_for_client
    (no script, no correct_option/explanation). strip=False: full docs
    unchanged (including script/correct_option/explanation/tts_status),
    for the generation/persist path -- matches Sections 1-3's strip=False
    convention when called from server.py.

    Raises ValueError if there aren't enough GENERATED clips (regardless of
    total pool size) to assemble any valid 4-question combination -- the
    error message says explicitly whether the shortfall is real content
    scarcity or just missing audio, since those need very different fixes."""
    rng = rng or random.Random()
    generated_pool = [c for c in clip_pool if c.get("tts_status") == "generated"]
    one_q = [c for c in generated_pool if len(c.get("questions", [])) == 1]
    two_q = [c for c in generated_pool if len(c.get("questions", [])) == 2]

    shapes = []
    if len(one_q) >= 4:
        shapes.append("four_ones")
    if len(one_q) >= 2 and len(two_q) >= 1:
        shapes.append("two_ones_one_two")
    if len(two_q) >= 2:
        shapes.append("two_twos")
    if not shapes:
        total_in_pool = len(clip_pool)
        raise ValueError(
            f"listening clip pool too small to assemble {SECTION5_TARGET_QUESTION_COUNT} questions "
            f"from GENERATED (audio-ready) clips only (have {len(one_q)} one-question, "
            f"{len(two_q)} two-question generated clips out of {len(generated_pool)} generated / "
            f"{total_in_pool} total in pool -- clips with tts_status != 'generated' are never drawable)"
        )

    shape = rng.choice(shapes)
    if shape == "four_ones":
        selected = rng.sample(one_q, 4)
    elif shape == "two_ones_one_two":
        selected = rng.sample(one_q, 2) + rng.sample(two_q, 1)
    else:
        selected = rng.sample(two_q, 2)

    total_questions = sum(len(c["questions"]) for c in selected)
    assert total_questions == SECTION5_TARGET_QUESTION_COUNT, (
        f"internal error: drew {total_questions} questions, expected {SECTION5_TARGET_QUESTION_COUNT}"
    )
    if not strip:
        return [dict(c) for c in selected]
    return [_strip_listening_for_client(c) for c in selected]


# =============================================================================
# ---- Section 6: Spoken Communication Simulation ----
# =============================================================================
# Bank content lives in Mongo (`capgemini_round1_bank`,
# section="spoken_simulation"), authored + staged via the scratchpad
# pipeline under capgemini_round1_pipeline/ and inserted separately (35
# read_aloud + 35 respond_to_prompt = 70 items). Draw logic
# (draw_section6_questions, below Type B) pulls exactly 1 read_aloud + 1
# respond_to_prompt per session -- a fixed mix, not random -- and is wired
# into server.py's live capgemini_round1 generation/strip/grading paths,
# same as Sections 1-5.
#
# Two item types, graded by completely different pipelines:
#   - read_aloud: candidate reads `passage_text` aloud -> graded by Word
#     Error Rate (WER) against that exact text. Deterministic, NO LLM call.
#   - respond_to_prompt: candidate gives a spoken response to `scenario` ->
#     graded by the SAME rubric-LLM pipeline Section 2 already built
#     (score_business_writing_email, reused directly below, not
#     duplicated).
#
# BOTH types: the STT transcript is produced server-side from the
# candidate's submitted audio via the EXISTING, already-generic
# POST /oa/{attempt_id}/transcribe endpoint (Groq Whisper -- same one
# Cognizant's Speaking/Reading&Listening sections already use). That
# endpoint never branches by section type -- it just runs Whisper and
# returns {"transcript": ...} -- so nothing there needed to change for this
# section; the frontend submits the returned transcript through the normal
# answers[qid] flow, exactly like an essay answer. A client-submitted
# transcript is never trusted as ground truth beyond being the thing to
# grade -- same "security by re-derivation" principle as every other grader
# in this app: _grade_capgemini_round1_section's "spoken_sim" case (in
# server.py) compares the transcript against the FULL stored item
# (passage_text or rubric), never anything the client asserts about
# correctness. The functions below take an ALREADY-TRANSCRIBED string,
# exactly like grade_business_writing_submission takes already-composed
# email_text rather than raw audio/HTML -- the transcription step itself
# happens one layer up, in server.py, not in this module.

# ---- Type A: read_aloud (WER-based, deterministic) -------------------------
#
# No WER library (jiwer or similar) is currently a dependency of this
# backend -- checked requirements.txt before writing this, confirmed
# absent. Rather than add a new external dependency for one deterministic
# function, this implements standard word-level edit-distance WER directly
# in pure Python. This mirrors the codebase's own existing precedent for
# STT-transcript comparison: server.py's _grade_reading_listening_section
# already uses stdlib difflib.SequenceMatcher (a RATIO-based similarity,
# not true WER) for Cognizant's Reading & Listening section rather than
# pulling in an external library -- same "stdlib first" instinct, applied
# here to a true WER metric instead, since read_aloud's spec explicitly
# calls for WER, not a generic similarity ratio.

_WER_PUNCT_RE = re.compile(r"[^\w\s]")


def _normalize_for_wer(text: str) -> List[str]:
    """Lowercase + strip ALL punctuation (including apostrophes -- this is
    what makes "it's"/"its" and "don't"/"dont" compare equal, per spec,
    without a separate contraction-expansion table) + collapse whitespace,
    then split into words."""
    normalized = _WER_PUNCT_RE.sub("", (text or "").lower())
    return normalized.split()


def _word_edit_distance(ref: List[str], hyp: List[str]) -> int:
    """Levenshtein distance at WORD granularity (not character) -- the
    substitutions/deletions/insertions WER is defined over. Classic
    O(len(ref) * len(hyp)) DP, single-row rolling (no need to keep the
    full matrix)."""
    n, m = len(ref), len(hyp)
    if n == 0:
        return m
    if m == 0:
        return n
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        curr = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,        # deletion
                curr[j - 1] + 1,    # insertion
                prev[j - 1] + cost,  # substitution / match
            )
        prev = curr
    return prev[m]


def compute_wer(reference_text: str, hypothesis_text: str) -> float:
    """Standard WER = edit_distance(ref_words, hyp_words) / len(ref_words).
    Can exceed 1.0 if the hypothesis has far more words than the reference
    (heavy insertions) -- callers convert this to a floored-at-0 accuracy
    score (see grade_read_aloud_response), not this function itself, so the
    raw WER value stays inspectable/auditable exactly as computed."""
    ref_words = _normalize_for_wer(reference_text)
    hyp_words = _normalize_for_wer(hypothesis_text)
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    distance = _word_edit_distance(ref_words, hyp_words)
    return distance / len(ref_words)


# Accuracy-percentage -> /5 score banding. Anchors the 3 tiers the spec
# explicitly requires (>=90% full marks / 75-89% partial credit / <75% low
# score) with finer resolution WITHIN each tier so the score isn't just a
# flat 5/3/0 across a wide range -- an explicit, documented scale since the
# spec asked for an exact one, not an implicit choice:
#   accuracy >= 90%          -> 5   (full marks)
#   80% <= accuracy < 90%    -> 4  }
#   75% <= accuracy < 80%    -> 3  } "partial credit" tier (75-89%)
#   60% <= accuracy < 75%    -> 2  }
#   40% <= accuracy < 60%    -> 1  } "low score" tier (<75%)
#   accuracy < 40%           -> 0  }
_WER_SCORE_BANDS = [(90.0, 5), (80.0, 4), (75.0, 3), (60.0, 2), (40.0, 1), (0.0, 0)]


def _band_wer_score(accuracy_pct: float) -> int:
    for threshold, score in _WER_SCORE_BANDS:
        if accuracy_pct >= threshold:
            return score
    return 0  # unreachable (last band's threshold is 0.0) -- kept for safety


def grade_read_aloud_response(item: Dict[str, Any], transcript: str) -> Dict[str, Any]:
    """Grades a read_aloud submission -- purely deterministic, NO LLM call
    at all (unlike respond_to_prompt below). `item` must carry the original
    `passage_text`; `transcript` is the ALREADY-TRANSCRIBED text (server-
    side Whisper output -- see module docstring, never trusted from the
    client as-is). Returns wer/accuracy_pct/score_0_5/scaled_score so a
    future caller can plug this into the same 0.0-1.0-per-item averaging
    every other Round 1 part uses (scaled_score/100, same convention
    grade_business_writing_submission's scaled_score already establishes)."""
    wer = compute_wer(item["passage_text"], transcript)
    accuracy_pct = max(0.0, (1 - wer) * 100)
    score_0_5 = _band_wer_score(accuracy_pct)
    return {
        "wer": round(wer, 4),
        "accuracy_pct": round(accuracy_pct, 1),
        "score_0_5": score_0_5,
        "scaled_score": round((score_0_5 / 5) * 100, 1),
    }


# ---- Type B: respond_to_prompt (LLM rubric grading) -------------------------
#
# Deliberately REUSES Section 2's grading infrastructure rather than
# duplicating it: score_business_writing_email() (above, Section 2) is
# already generic over any dict carrying a "rubric" list of
# {criterion, description, weight, max_score} dicts -- nothing in its body
# is business-writing-specific despite the name (confirmed by reading it
# before reusing it here, not assumed). respond_to_prompt's own rubric
# (clarity/relevance/structure/professionalism) has the exact same shape as
# Section 2's, so this calls that function DIRECTLY rather than writing a
# second copy of the same weighting/scaling logic. Only the PROMPT text
# differs (spoken-response framing vs. email framing), hence a new prompt
# builder below rather than reusing business_writing_grading_prompt's
# wording verbatim. STATUS_PENDING/STATUS_GRADED/STATUS_FAILED (defined
# above, Section 2) are already generic constants, not business-writing-
# specific, and are reused as-is.

def spoken_response_grading_prompt(item: Dict[str, Any], transcript: str) -> str:
    """Only criterion + description go into the prompt -- weight and
    max_score are applied programmatically in score_business_writing_email
    (reused, not duplicated), never by the LLM -- same split
    business_writing_grading_prompt already established."""
    rubric_lines = "\n".join(
        f"- {c['criterion']}: {c['description']}" for c in item["rubric"]
    )
    return (
        "You are grading a candidate's SPOKEN response (already transcribed "
        "to text) for a workplace communication assessment. The transcript "
        "may contain natural speech artifacts (filler words, informal "
        "phrasing, run-on sentences) -- judge the CONTENT and delivery "
        "quality as spoken communication, not written-prose polish.\n\n"
        f"SCENARIO: {item['scenario']}\n\n"
        f"CANDIDATE'S SPOKEN RESPONSE (transcript):\n{wrap_untrusted(transcript)}\n\n"
        "Score the response against EXACTLY these criteria, and no others:\n"
        f"{rubric_lines}\n\n"
        "For each criterion, score 0-5:\n"
        "  0 = criterion entirely absent or failed\n"
        "  1-2 = attempted but weak, unclear, or misses the point of the criterion\n"
        "  3-4 = present and mostly effective, minor issues only\n"
        "  5 = criterion fully and clearly met\n"
        "Score STRICTLY against the description given for each criterion above -- "
        "not your own general idea of a 'good spoken response'. Do not invent or "
        "consider criteria that aren't listed, and do not penalize normal spoken-"
        "language artifacts (a stray 'um', a restarted sentence) unless they "
        "genuinely hurt clarity or structure.\n\n"
        "Return JSON: {scores: [{criterion, score (integer 0-5), justification "
        "(1-2 sentences, specific to what the candidate actually said)}, ... "
        "one entry per criterion listed above, same order]}."
    )


async def grade_respond_to_prompt_submission(item: Dict[str, Any], transcript: str) -> Dict[str, Any]:
    """The actual async grading call for respond_to_prompt -- mirrors
    grade_business_writing_submission's structure exactly (separate prompt
    builder + call_json_gpt + reused score_business_writing_email post-
    processing). Never invoked in the same call/session that created the
    item (there IS no generation call for this content; scenarios are
    hand-authored, same as every other bank in this module). Never raises:
    a failed or unparseable grading call resolves to STATUS_FAILED with
    zero scores, same convention as grade_business_writing_submission."""
    grading_result = await call_json_gpt(
        "You are a strict, fair evaluator of workplace spoken communication. Return only strict JSON.\n\n"
        + GRADING_INJECTION_DEFENSE,
        spoken_response_grading_prompt(item, transcript),
    )
    if not grading_result or not grading_result.get("scores"):
        return {"status": STATUS_FAILED, "raw_total": 0, "max_total": 0, "scaled_score": 0.0, "breakdown": []}
    scored = score_business_writing_email(item, grading_result)  # reused verbatim, see note above
    return {"status": STATUS_GRADED, **scored}


# ---- Draw logic (follow-up pass, 2026-08) -----------------------------------
#
# Pulls exactly 1 read_aloud + 1 respond_to_prompt per session -- a fixed
# mix, not a random selection across both pools, since a session with 0 or 2
# of either type would break the "one read, one respond" assessment design.
# `item_pool` is expected to be the full section="spoken_simulation" pool
# (both item_types together, exactly like every other draw_sectionN_
# questions function here takes one already-fetched pool); this function
# splits it internally by item_type before sampling.

# read_aloud docs carry passage_text (not sensitive -- the candidate needs to
# see it to read it aloud, unlike an MCQ answer key) + estimated_duration_
# seconds. respond_to_prompt docs carry scenario + rubric -- rubric is
# EXCLUDED from the client-safe shape, same no-rubric-shown precedent as
# Section 2's business_writing. respond_to_prompt docs do NOT actually carry
# an estimated_duration_seconds field (checked the batch-authoring helper,
# add_respond_to_prompt() never sets one, unlike add_read_aloud()) -- listed
# here anyway per spec and guarded by `if k in item`, so this whitelist is
# ready the moment that field is added to the bank without needing a second
# edit.
SECTION6_READ_ALOUD_CLIENT_SAFE_FIELDS = ("item_id", "item_type", "passage_text", "estimated_duration_seconds")
SECTION6_RESPOND_TO_PROMPT_CLIENT_SAFE_FIELDS = ("item_id", "item_type", "scenario", "estimated_duration_seconds")


def _strip_spoken_sim_for_client(item: Dict[str, Any]) -> Dict[str, Any]:
    """Module-internal convenience strip (used when draw_section6_questions
    is called directly with strip=True) -- mirrors every other section's own
    _strip_*_for_client helper. Branches on item_type since the two types
    have entirely different client-safe shapes (unlike Sections 1/3's single
    MCQ shape)."""
    fields = (
        SECTION6_READ_ALOUD_CLIENT_SAFE_FIELDS if item.get("item_type") == "read_aloud"
        else SECTION6_RESPOND_TO_PROMPT_CLIENT_SAFE_FIELDS
    )
    return {k: item[k] for k in fields if k in item}


def draw_section6_questions(
    item_pool: List[Dict[str, Any]],
    rng: Optional[random.Random] = None,
    strip: bool = True,
) -> List[Dict[str, Any]]:
    """Selects exactly 1 read_aloud item + 1 respond_to_prompt item from
    `item_pool` (a list of capgemini_round1_bank docs with
    section="spoken_simulation", both item_types mixed together) -- a fixed
    1+1 mix, not a random draw across the combined pool.

    strip=True (default): client-safe dicts via _strip_spoken_sim_for_client
    (no rubric for respond_to_prompt). strip=False: full docs unchanged
    (including rubric), for the generation/persist path -- grade_respond_
    to_prompt_submission needs the rubric from the STORED attempt document
    later, same "store full, strip at response" reasoning as every other
    section here.

    Raises ValueError, loudly and separately per type, if either pool is
    empty -- with 35/35 in the live bank this should never happen, but a
    silent partial draw (e.g. 2 read_aloud, 0 respond_to_prompt) would be a
    much worse failure mode than a clear error."""
    rng = rng or random.Random()
    read_aloud_pool = [it for it in item_pool if it.get("item_type") == "read_aloud"]
    respond_pool = [it for it in item_pool if it.get("item_type") == "respond_to_prompt"]
    if not read_aloud_pool:
        raise ValueError("read_aloud pool is empty -- cannot draw Section 6 (need exactly 1 read_aloud item)")
    if not respond_pool:
        raise ValueError("respond_to_prompt pool is empty -- cannot draw Section 6 (need exactly 1 respond_to_prompt item)")

    selected = [rng.choice(read_aloud_pool), rng.choice(respond_pool)]
    if not strip:
        return [dict(it) for it in selected]
    return [_strip_spoken_sim_for_client(it) for it in selected]
