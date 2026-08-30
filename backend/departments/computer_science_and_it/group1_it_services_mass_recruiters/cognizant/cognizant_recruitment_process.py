# -*- coding: utf-8 -*-
"""Cognizant GenC recruitment process.

Thin orchestration layer, added 2026-08 (backend restructure follow-up).
No real generation/grading logic lives here -- it stays in server.py's
shared, generic dispatch functions and services/ai_service.py. This module
is a readable entry point onto Cognizant's actual OA shape and the shared
mechanisms its companies.py config invokes.

Cognizant structure (source of truth: companies.py, id="cognizant";
get_config() below re-exports it verbatim), 3 rounds:
  Round 1 -- Communication Assessment (60 min total, reflects in final
  verdict, never blocks progression -- sectional scoring):
    - "grammar"             R1: Grammar             (grammar, 34 Qs)
    - "comprehension"       R1: Comprehension        (comprehension, 16 Qs)
    - "speaking"            R1: Speaking             (speaking, 1)
    - "reading_listening"   R1: Reading & Listening  (reading_listening, 5)
    "speaking" and "reading_listening" are Cognizant's distinguishing
    mechanism: both are voice-based -- the frontend records audio and
    calls the shared POST /oa/{attempt_id}/transcribe route, which itself
    is a thin wrapper over services.ai_service.transcribe_audio (Groq
    Whisper). See transcribe_cognizant_voice_response() below, which wraps
    that same shared STT function directly.
  Round 2 -- Quant + Gamified:
    - "quant"  R2: Quantitative Aptitude (mcq, 25 Qs) -- distinguishing:
      uses `extra_topics` to blend 19 Aptitude + 6 Reasoning (Cognizant has
      no separate Logical Reasoning section, folded in per the
      cross-company reasoning-coverage rule). See
      generate_cognizant_quant_section() below.
    - "gamified"  R2: Gamified Round (gamified_round, registry-driven via
      game_types.py/gamified_round.py -- not LLM-generated at all, no
      wrapper added here since it's DB-config-driven rather than a
      server.py mechanism).
  Round 3 -- Skill Cluster (candidate picks Java/Python via cluster_options
  on the company entry, not a per-section mechanism):
    - "coding"  R3: Coding (coding, 2, difficulty_target="easy_medium") --
      plain scalar difficulty_target, the same generic parameter every
      coding section can set; not Wipro's per-problem difficulty_targets
      LIST, so no dedicated wrapper needed.
    - "sql"     R3: SQL      (mcq, 2) -- plain.
    - "domain"  R3: Domain (Cloud Fundamentals) (mcq, 8) -- plain.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from companies import get_company
from services.ai_service import transcribe_audio
# server.py does not import this module today, so this import direction is
# safe (no circular import) -- see capgemini_recruitment_process.py's
# docstring for the one company where it would cycle.
from server import _generate_extra_topics


def get_config() -> Optional[Dict[str, Any]]:
    """Cognizant's full section config, straight from companies.py."""
    return get_company("cognizant")


async def generate_cognizant_quant_section(
    company_name: str, section: Dict[str, Any], user_id: str,
) -> List[dict]:
    """Cognizant's R2 Quantitative Aptitude section -- thin wrapper over the
    shared per-topic pool-or-live-verify generator, using this section's
    own extra_topics split (19 Aptitude + 6 Reasoning). Does not
    reimplement _generate_extra_topics' body."""
    return await _generate_extra_topics(
        company_name, section["extra_topics"], section.get("difficulty_target"), user_id,
    )


async def transcribe_cognizant_voice_response(audio_bytes: bytes, filename: str) -> str:
    """Cognizant's Speaking / Reading & Listening sections are voice-based
    -- thin wrapper over the shared Groq-Whisper transcription utility
    (the exact same function server.py's POST /oa/{attempt_id}/transcribe
    route calls). Stateless, same as the shared route: the caller is
    responsible for submitting the returned transcript through the normal
    answer flow."""
    return await transcribe_audio(audio_bytes, filename)


def build_recruitment_process():
    """Placeholder for a genuinely bespoke Cognizant content bank, if
    that's ever built -- distinct from the thin orchestration wrappers
    above."""
    raise NotImplementedError("Bespoke Cognizant recruitment process not yet implemented")
