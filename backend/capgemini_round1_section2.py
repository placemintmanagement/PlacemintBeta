# -*- coding: utf-8 -*-
"""Capgemini Round 1 Section 2 (Business Communication Writing) -- grading
pipeline only. Scenario content lives in Mongo (`capgemini_round1_bank`,
section="business_writing"), authored + staged via the scratchpad pipeline
under capgemini_round1_pipeline/ and inserted separately.

Not yet wired into any live session/registry route -- server.py has no
Round 1 section-dispatch code yet (that's the still-pending session-model
restructure). This module is grading-side application logic, ready to be
called once that wiring exists.

Generation/grading separation: scenario `context` and `rubric` are authored
content (no LLM call involved at all -- hand-written, see the scratchpad
pipeline). Grading is a genuinely separate LLM call, invoked only after a
candidate submits their email, and must NEVER regenerate or "improve" the
rubric it's handed -- it only scores the candidate's text against the fixed
rubric it's given.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from ai_service import call_json_gpt

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
        f"CANDIDATE'S EMAIL:\n\"\"\"\n{email_text}\n\"\"\"\n\n"
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
    return {
        "raw_total": raw_total,
        "max_total": max_total,
        "scaled_score": scaled_score,
        "breakdown": breakdown,
    }


async def grade_business_writing_submission(scenario: Dict[str, Any], email_text: str) -> Dict[str, Any]:
    """The actual async grading call. Fully separate from scenario
    generation -- never invoked in the same call/session that created the
    scenario or its rubric (there IS no generation call for this content;
    scenarios are hand-authored, see module docstring). Uses call_json_gpt
    (GPT-5.4 Mini via the OpenAI path), matching this codebase's existing
    convention for open-answer grading (grade_essay_prompt, grade_spoken_
    response_prompt in ai_service.py) rather than the Anthropic path used
    for generation/verification tasks.

    Returns a dict with `status` plus (on success) raw_total/max_total/
    scaled_score/breakdown -- ready to store on the candidate's attempt
    record. Never raises: a failed or unparseable grading call resolves to
    STATUS_FAILED with zero scores rather than propagating an exception,
    since one candidate's malformed LLM response shouldn't 500 the request.
    """
    grading_result = await call_json_gpt(
        "You are a strict, fair evaluator of workplace business emails. Return only strict JSON.",
        business_writing_grading_prompt(scenario, email_text),
    )
    if not grading_result or not grading_result.get("scores"):
        return {"status": STATUS_FAILED, "raw_total": 0, "max_total": 0, "scaled_score": 0.0, "breakdown": []}
    scored = score_business_writing_email(scenario, grading_result)
    return {"status": STATUS_GRADED, **scored}
