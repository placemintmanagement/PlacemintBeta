"""Thin wrappers around two independent LLM paths, both calling the provider
SDKs directly (no third-party integration layer).

The Anthropic path (via AsyncAnthropic, using ANTHROPIC_API_KEY) is used for
resume analysis, the final report, the MCQ verification/explanation trust gate,
MCQ stem generation, and interview planning/grading (Sonnet 4.5 or Haiku 4.5
depending on call site — see each call site for which). The OpenAI path (via
AsyncOpenAI, using OPENAI_API_KEY) is used only for OA coding/open-answer
grading (GPT-5.4 Mini) — the one function in this codebase using OpenAI.
These are deliberately separate, non-unified code paths
(separate client, separate JSON-extraction call, separate error handling) rather than
a single provider-dispatching call_json — see the 2026-07-16 model-routing decision.

We use non-streaming calls for JSON-structured tasks because we need the final parsed
JSON, not tokens. Streaming is reserved for interview chat where we intentionally
build a chat-like feel.

Migrated off emergentintegrations (2026-07-16): every call previously went through
emergentintegrations' LlmChat, proxying through a single EMERGENT_LLM_KEY. Both
HAIKU and SONNET now call AsyncAnthropic directly. HAIKU/SONNET keep their
historical (provider_tag, model_id) tuple shape for backward compatibility with
existing callers (mcq_pool.py reads HAIKU[1]/SONNET[1] directly) — only model[1]
(the real model id) is used when calling Anthropic; the provider_tag is now
vestigial but left in place rather than touching every call site that reads it.
"""
from __future__ import annotations
import os
import json
import re
import logging
from typing import Any, Dict, List, Optional
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

HAIKU = ("anthropic", "claude-haiku-4-5-20251001")
SONNET = ("anthropic", "claude-sonnet-4-5-20250929")
GPT_MINI = "gpt-5.4-mini"

# Anthropic's Messages API requires max_tokens explicitly on every call (unlike
# OpenAI's Chat Completions, which defaults it) — this is a new explicit knob
# that had no equivalent under emergentintegrations. Generous fixed budget for
# the JSON-structured tasks this file drives (MCQ batches, resume analysis,
# interview plans). Call sites with unusually long expected output (e.g. the
# final report) pass a higher max_tokens explicitly rather than raising this
# default for everyone.
ANTHROPIC_MAX_TOKENS = 4096


_anthropic_client: Optional[AsyncAnthropic] = None


def _get_anthropic_client() -> AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return _anthropic_client


_openai_client: Optional[AsyncOpenAI] = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    return _openai_client


# Cognizant Round 1 (Speaking / Reading & Listening) voice transcription.
#
# TEMPORARY PROVIDER CHOICE — Groq, not OpenAI Whisper directly (2026-07-19):
# Groq's Developer tier is currently closed to new upgrades, so this runs on
# Groq's FREE tier only: 2,000 Whisper requests/day, no paid fallback if that
# cap is hit. We deliberately reuse the AsyncOpenAI client (already a
# dependency, see _get_openai_client above) pointed at Groq's OpenAI-compatible
# base_url, rather than adding the `groq` PyPI package — Groq's
# /audio/transcriptions endpoint matches OpenAI's Whisper API shape exactly.
# This makes swapping to real OpenAI Whisper later a one-line change: drop
# `base_url` (and switch GROQ_API_KEY -> OPENAI_API_KEY, model name to
# "whisper-1") on _get_groq_client below; transcribe_audio's call shape and
# every call site stay identical.
GROQ_WHISPER_MODEL = "whisper-large-v3"
_groq_client: Optional[AsyncOpenAI] = None


def _get_groq_client() -> AsyncOpenAI:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncOpenAI(
            api_key=os.environ.get("GROQ_API_KEY", ""),
            base_url="https://api.groq.com/openai/v1",
        )
    return _groq_client


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribes a recorded audio clip to text via Groq Whisper. Returns an
    empty string (rather than raising) on any provider error, so callers can
    treat a failed transcription the same as an unanswered question."""
    client = _get_groq_client()
    try:
        resp = await client.audio.transcriptions.create(
            model=GROQ_WHISPER_MODEL,
            file=(filename, audio_bytes),
        )
        return (resp.text or "").strip()
    except Exception:
        logger.exception("Groq transcription failed")
        return ""


def _extract_json(text: str) -> Any:
    """Robust JSON extraction from an LLM reply.

    Tries plain json.loads first, then hunts for the first balanced { ... } or
    [ ... ] block. Returns None if nothing parses.
    """
    if not text:
        return None
    text = text.strip()
    # strip common code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    # find first { or [
    for start_ch, end_ch in (("{", "}"), ("[", "]")):
        i = text.find(start_ch)
        while i != -1:
            depth = 0
            for j in range(i, len(text)):
                if text[j] == start_ch:
                    depth += 1
                elif text[j] == end_ch:
                    depth -= 1
                    if depth == 0:
                        chunk = text[i : j + 1]
                        try:
                            return json.loads(chunk)
                        except Exception:
                            break
            i = text.find(start_ch, i + 1)
    return None


async def call_json(
    system: str,
    prompt: str,
    session_id: Optional[str] = None,
    model: tuple = HAIKU,
    max_tokens: int = ANTHROPIC_MAX_TOKENS,
) -> Any:
    """Call an LLM with instructions to return strict JSON. Returns parsed JSON.

    Defaults to Haiku 4.5 (cheap, fast). Pass `model=SONNET` for higher-stakes
    calls (e.g. the MCQ verification trust gate). Pass `max_tokens` to raise the
    output budget above the default for calls with unusually long expected
    output (e.g. the final report).

    Retries once if the first response fails to parse as JSON before giving up
    and returning None — this backs the majority of the app's AI calls now, so
    a single transient bad-format response shouldn't be fatal.

    `session_id` is accepted for backward compatibility with existing call sites
    but unused — every call here was already stateless per-call even under the
    old emergentintegrations path (a fresh LlmChat was constructed every time)."""
    system_full = (
        system
        + "\n\nCRITICAL: Respond ONLY with valid JSON. No prose, no code fences, "
          "no leading/trailing commentary. If unsure, return the best-guess JSON that "
          "matches the requested shape."
    )
    client = _get_anthropic_client()

    async def _attempt() -> tuple:
        resp = await client.messages.create(
            model=model[1],
            max_tokens=max_tokens,
            system=system_full,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in resp.content if hasattr(block, "text"))
        return _extract_json(text), text

    parsed, text = await _attempt()
    if parsed is None:
        logger.info("call_json: first attempt failed to parse, retrying once. Raw text: %s", text[:400])
        parsed, text = await _attempt()
    if parsed is None:
        logger.warning("call_json: failed to parse after retry. Raw text: %s", text[:400])
    return parsed


async def call_text(system: str, prompt: str, session_id: Optional[str] = None) -> str:
    client = _get_anthropic_client()
    resp = await client.messages.create(
        model=HAIKU[1],
        max_tokens=ANTHROPIC_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if hasattr(block, "text"))


async def call_json_gpt(system: str, prompt: str, model: str = GPT_MINI) -> Any:
    """Call GPT via the OpenAI SDK directly (separate path from call_json/emergent-
    integrations above) with instructions to return strict JSON. Returns parsed JSON.

    Used for tasks with no independent cross-check needed: MCQ stem generation,
    interview planning/grading, OA coding/open-answer grading. Reuses the same
    _extract_json parser as call_json since that logic is provider-agnostic."""
    system_full = (
        system
        + "\n\nCRITICAL: Respond ONLY with valid JSON. No prose, no code fences, "
          "no leading/trailing commentary. If unsure, return the best-guess JSON that "
          "matches the requested shape."
    )
    client = _get_openai_client()
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_full},
            {"role": "user", "content": prompt},
        ],
    )
    text = resp.choices[0].message.content or ""
    parsed = _extract_json(text)
    if parsed is None:
        logger.warning("call_json_gpt: failed to parse. Raw text: %s", text[:400])
    return parsed


# ---- Prompt templates -------------------------------------------------------

def resume_prompt(company_name: str, role: str, resume_text: str) -> str:
    return (
        f"Analyse this candidate's resume specifically for a {role} role at "
        f"{company_name}. Return JSON with keys:\n"
        "- strengths: array of 3-5 short strings (specific to this company/role)\n"
        "- weaknesses: array of 3-5 short strings\n"
        "- extracted_projects: array of {name, tech_stack, one_line_summary}\n"
        "- fit_score: integer 0-100\n"
        "- verdict: one short sentence\n\n"
        f"RESUME TEXT:\n{resume_text[:6000]}"
    )


DIFFICULTY_RULE = (
    "DIFFICULTY DISTRIBUTION: Aim for a mix of ~15% Easy, ~65% Medium, ~20% Hard. "
    "Absolute majority must be Medium. Easy questions should still require actual reasoning "
    "(no pure definition-recall). Hard means multi-step logic or non-obvious insight. "
    "For coding problems, calibrate against LeetCode Easy/Medium/Hard tiers respectively."
)


def _difficulty_override(target: Optional[str]) -> str:
    """Return a stronger difficulty rule when a section has an explicit target."""
    if not target:
        return DIFFICULTY_RULE
    t = target.lower()
    if t in ("easy_medium", "easy-medium"):
        return (
            "DIFFICULTY DISTRIBUTION: ~60% Easy, ~40% Medium, ZERO Hard. "
            "These should feel like LeetCode Easy-to-lower-Medium tier problems. "
            "Loops, string manipulation, arrays, and basic data structures only."
        )
    if t in ("hard", "advanced"):
        return (
            "DIFFICULTY DISTRIBUTION: ~20% Medium, ~80% Hard. ZERO Easy. "
            "Advanced DSA only: recursion depth, trees, graphs, or dynamic programming. "
            "Grade both correctness AND time/space complexity. Non-optimal answers are penalized."
        )
    if t == "medium":
        return (
            "DIFFICULTY DISTRIBUTION: 100% Medium. ZERO Easy, ZERO Hard. "
            "Solidly LeetCode-Medium tier — non-trivial data structures / algorithms, "
            "but solvable in 15-20 minutes by a well-prepared fresher."
        )
    if t in ("medium_hard", "medium-hard"):
        return (
            "DIFFICULTY DISTRIBUTION: ~75% Medium, ~15% Hard, ~10% Easy. "
            "This track is deliberately harder than easy-tier company OAs. "
            "Favor concept-application questions over lookup/recall; only a small "
            "minority of items should be recall-level."
        )
    return DIFFICULTY_RULE


TOPIC_INSTRUCTIONS = {
    "aptitude":     "Quantitative aptitude — percentages, ratios, time-speed-distance, probability, permutations.",
    "verbal":       "Verbal English — sentence correction, vocabulary in context, reading-comprehension inference (compact form, not long passages).",
    "oops":         "Object-oriented programming — inheritance, polymorphism, encapsulation, virtual/abstract dispatch, SOLID principles. Prefer conceptual questions over language trivia; use Java/C++/Python examples interchangeably.",
    "dbms":         "Database systems — SQL query output, normalization (1NF/2NF/3NF/BCNF), joins, indexing, transactions, ACID.",
    "os":           "Operating systems — processes vs threads, scheduling, deadlocks, semaphores/mutexes, virtual memory, paging.",
    "cn":           "Computer networks — OSI/TCP-IP layers, TCP vs UDP, subnetting, HTTP/HTTPS, DNS, routing.",
    "architecture": "Computer architecture — pipelining, cache hierarchy, memory ordering, cache-coherence, addressing modes, instruction encoding, MIPS/RISC concepts.",
    "reasoning":    "Logical/analytical reasoning — syllogisms, coding-decoding, blood relations, seating arrangements, data sufficiency, series/pattern completion, direction sense, analogies, classification/odd-one-out, statement-assumption/conclusion, input-output machines, ranking/ordering, cube and dice.",
}


def mcq_prompt(company: str, section_name: str, count: int, difficulty_target: Optional[str] = None) -> str:
    """Stage-A prompt: generate question stem + 4 options ONLY. Explicitly does
    not ask for correct_index or explanation — those are derived downstream by
    independent solvers (LLM reasoning + code execution when applicable)."""
    return (
        f"Generate {count} multiple-choice questions for the '{section_name}' "
        f"section of the {company} Online Assessment. Return a JSON array. Each item: "
        "{id, prompt, options: [exactly 4 strings], difficulty ('Easy'|'Medium'|'Hard')}. "
        "DO NOT include a correct_index or explanation — those are derived by a "
        "separate solver. Your job is only to write the QUESTION and 4 plausible options. "
        "Exactly one option must be objectively correct; the other three must be "
        "plausible but demonstrably wrong. Options should not paraphrase each other. "
        "For code-output questions, include the code snippet in a fenced block "
        "inside `prompt` so the executor can run it verbatim. "
        "Questions must reflect the section's actual style. Do NOT repeat questions. "
        + _difficulty_override(difficulty_target)
    )


def aptitude_topic_mix_prompt(
    company: str, count: int, topic_groups: List[Dict[str, Any]], difficulty_target: Optional[str] = None,
) -> str:
    """Stage-A prompt for Wipro's 3-sub-section Aptitude Test (Quant +
    Logical + Verbal), each with its own named topic list. Same
    generate-stem-only contract as mcq_prompt/topic_mcq_prompt — correct_index
    is derived downstream by the same Stage-B ground-truth pipeline
    (see mcq_pool.fallback_live_verify_topic_mix), not by this prompt."""
    n_groups = max(1, len(topic_groups))
    per_group = max(1, count // n_groups)
    lines = []
    for g in topic_groups:
        gname = g.get("name", "")
        topics = ", ".join(g.get("topics", []))
        lines.append(f"- {gname} (~{per_group} questions): cover these topics — {topics}.")
    groups_text = "\n".join(lines)
    return (
        f"Generate {count} multiple-choice questions for {company}'s Aptitude Test, "
        f"split evenly across these {n_groups} sub-sections:\n{groups_text}\n"
        "Return ONE combined JSON array (do not group by section in the output). Each item: "
        "{id, prompt, options: [exactly 4 strings], topic (the specific topic from the list "
        "above this question covers), difficulty ('Easy'|'Medium'|'Hard')}. "
        "DO NOT include a correct_index or explanation — those are derived by a separate solver. "
        "Exactly one option must be objectively correct; the other three must be plausible but "
        "demonstrably wrong. Do NOT repeat questions. "
        + _difficulty_override(difficulty_target)
    )


def topic_mcq_prompt(company: str, topic_key: str, topic_name: str, count: int, difficulty_target: Optional[str] = None) -> str:
    """Stage-A prompt for topic-specific MCQs (Core Assessment company). Same
    generate-stem-only contract as mcq_prompt."""
    topic_hint = TOPIC_INSTRUCTIONS.get(topic_key, f"{topic_name} — standard undergraduate CS/aptitude curriculum.")
    return (
        f"Generate {count} multiple-choice questions on the topic: {topic_name}. "
        f"{topic_hint} "
        "Return a JSON array. Each item: "
        "{id, prompt, options: [exactly 4 strings], difficulty ('Easy'|'Medium'|'Hard')}. "
        "DO NOT include a correct_index or explanation — those are derived downstream. "
        "Prompts must be self-contained. Options must be plausible distractors; exactly "
        "one is objectively correct. "
        "For code-output questions, include the code snippet in a fenced block inside "
        "`prompt` so the executor can run it verbatim. "
        "Do NOT repeat questions. "
        + _difficulty_override(difficulty_target)
    )


# ---- Stage-B: independent solver ------------------------------------------
# The solver is a SEPARATE LLM call that has never seen a claimed answer. It
# is asked to reason from first principles and pick the correct option index.

def solver_prompt(prompt_text: str, options: List[str]) -> tuple:
    opts = "\n".join(f"{i}. {o}" for i, o in enumerate(options))
    return (
        "You are an expert solver. Given a multiple-choice question and 4 options, "
        "reason from first principles and pick the correct answer. You have never "
        "been told what the setter claimed. If exactly one option is unambiguously "
        "correct, return {\"correct_index\": 0|1|2|3, \"confidence\": \"high\"|\"medium\"|\"low\"}. "
        "If the question is ambiguous or NO option is correct, return "
        "{\"correct_index\": -1, \"confidence\": \"low\"}. Return ONLY strict JSON.",
        f"Question:\n{prompt_text}\n\nOptions:\n{opts}\n\nWhich option index (0-3) is correct?"
    )


# ---- Stage-C: explanation writer with conflict-flagging -------------------
# The explanation writer is told the derived correct_index BUT is instructed
# to reason from first principles AND to flag a conflict rather than
# rationalize toward the answer if the answer doesn't hold up. This is the
# critical fix for the "explanation contorts to justify a wrong answer" bug.

def explanation_prompt(prompt_text: str, options: List[str], correct_index: int) -> tuple:
    opts = "\n".join(f"{i}. {o}" for i, o in enumerate(options))
    correct_opt = options[correct_index] if 0 <= correct_index < len(options) else "?"
    return (
        "You are writing an explanation for a multiple-choice question whose "
        "correct answer has already been independently determined. Your job is to "
        "explain WHY the given answer is correct — but ONLY if it actually is. "
        "Reason from first principles as if you did NOT know the target answer, "
        "then compare your derivation to the target. If your derivation matches, "
        "write a 1-2 line explanation and return "
        "{\"explanation\": \"<text>\", \"conflict\": false}. "
        "If your derivation does NOT support the target answer, return "
        "{\"explanation\": \"\", \"conflict\": true, \"my_derived_index\": <your index 0-3>, "
        "\"reason\": \"<one-line why>\"}. DO NOT rationalize toward the target. "
        "Return ONLY strict JSON.",
        f"Question:\n{prompt_text}\n\nOptions:\n{opts}\n\n"
        f"Target correct answer: index {correct_index} ({correct_opt}). "
        "Reason from first principles. Do your work match the target? If yes, "
        "write the explanation. If not, flag conflict."
    )


def coding_prompt(company: str, section_name: str, count: int, difficulty_target: Optional[str] = None) -> str:
    return (
        f"Generate {count} LeetCode-style coding problems for {company}'s "
        f"{section_name}. Return JSON array. Each: {{id, title, difficulty ('Easy'|'Medium'|'Hard'), "
        "statement (markdown, 4-8 lines with examples), input_format, output_format, "
        "constraints, visible_tests: [{input, expected_output}, {input, expected_output}], "
        "hidden_tests: [{input, expected_output} x 3], "
        "reference_solution (a WORKING Python 3 program that reads from stdin and writes to stdout, "
        "correctly solves the problem, and produces the exact expected_output shown for every test case above)}}. "
        "The reference_solution MUST be self-contained, run under 3 seconds, use only the standard library, "
        "and MATCH the expected_output byte-for-byte on every test case. Double-check the math before returning. "
        "Use stdin/stdout style so any language works. "
        + _difficulty_override(difficulty_target)
    )


def pseudocode_prompt(company: str, section_name: str, count: int, difficulty_target: Optional[str] = None) -> str:
    return (
        f"Generate {count} pseudocode / trace-the-output MCQ questions for {company}'s "
        f"{section_name}. Return JSON array of {{id, prompt (include a 6-15 line "
        "pseudocode block as a code block in the string), options: [4], correct_index, explanation, difficulty ('Easy'|'Medium'|'Hard')}}. "
        "For technical MCQ sections specifically about predicting output of C or Java programs, focus on pointers, "
        "loops, recursion, and operator precedence. "
        + _difficulty_override(difficulty_target)
    )


def comm_prompt(company: str, count: int, difficulty_target: Optional[str] = None) -> str:
    return (
        f"Generate {count} communication assessment MCQs for {company} "
        "(grammar, sentence correction, reading comprehension). Return JSON array of "
        "{id, prompt, options: [4], correct_index, explanation, difficulty ('Easy'|'Medium'|'Hard')}. "
        + _difficulty_override(difficulty_target)
    )


def grammar_prompt(company: str, count: int, difficulty_target: Optional[str] = None) -> str:
    return (
        f"Generate {count} grammar MCQs for {company}'s communication assessment "
        "(sentence correction, tense/subject-verb agreement, prepositions, error "
        "identification, vocabulary-in-context). Return JSON array of "
        "{id, prompt, options: [4], correct_index, explanation, difficulty ('Easy'|'Medium'|'Hard')}. "
        + _difficulty_override(difficulty_target)
    )


def comprehension_prompt(company: str, count: int, difficulty_target: Optional[str] = None) -> str:
    return (
        f"Generate {count} reading-comprehension MCQs for {company}'s communication "
        "assessment. Write ~4 short passages (120-180 words each) and ~4 questions per "
        "passage. Each question's `prompt` field must be FULLY SELF-CONTAINED: repeat "
        "the relevant passage text (prefixed 'Passage: ') followed by the question "
        "(prefixed 'Question: ') — do not reference a passage by number, since the "
        "candidate only ever sees one question at a time. Return JSON array of "
        "{id, prompt, options: [4], correct_index, explanation, difficulty ('Easy'|'Medium'|'Hard')}. "
        + _difficulty_override(difficulty_target)
    )


def game_prompt(company: str, count: int) -> str:
    return (
        f"Generate {count} short 'gamified cognitive' tasks (pattern completion, "
        f"speed math, spatial rotation described in text) as MCQs for {company}. "
        "Return JSON array of {id, prompt, options: [4], correct_index, explanation}."
    )


def cognitive_game_prompt(company: str, count: int) -> str:
    """Accenture-style timed cognitive minigames. Each question is one of four
    styles: pattern, sequence (odd-one-out), spatial (described in text), speed_math.
    The frontend enforces a per-question timer (default 15s).
    """
    return (
        f"Generate {count} short 'gamified cognitive' MCQs for {company} in the style of "
        "Accenture's cognitive round. Return JSON array. Each item: "
        "{id, style ('pattern'|'sequence'|'spatial'|'speed_math'), "
        "prompt (1-2 lines, snappy), options: [4 short strings], correct_index (0-3), "
        "explanation (one line)}. Mix the four styles evenly. "
        "Rules by style:\n"
        "- pattern: give a numeric or symbol sequence with one blank. Example: '2, 6, 12, 20, ?'\n"
        "- sequence: give 4 short items and ask which one doesn't fit.\n"
        "- spatial: describe a shape rotation/mirror in words. Options are also short text.\n"
        "- speed_math: single arithmetic expression solvable in <5s. Example: '17 * 6 - 12'.\n"
        "Keep prompts SHORT (max 90 chars) so they fit a 15-second per-question timer."
    )


def automata_fix_prompt(company: str, count: int) -> str:
    """Tech Mahindra Automata Fix. Instead of writing a solution, the candidate
    is given buggy code that ALMOST solves the problem and must fix it so that
    all visible + hidden tests pass. Small edits (1-3 line changes) only.
    """
    return (
        f"Generate {count} 'Automata Fix' problems for {company}. Each problem gives buggy code "
        "that ALMOST solves a small task. The candidate must find and fix small bugs so all tests pass. "
        "Return JSON array. Each item: "
        "{id, title, difficulty ('Medium'|'Hard'), statement (2-4 lines describing what the code should do), "
        "input_format, output_format, "
        "buggy_code (a single Python 3 program, 8-20 lines, that has 2-4 real bugs \u2013 off-by-one, "
        "wrong operator, wrong loop bound, wrong comparison. Uses input() and print()), "
        "reference_solution (the SAME program with all bugs fixed \u2013 a working Python 3 solution that produces the "
        "exact expected_output for every test case, byte-for-byte), "
        "visible_tests: [2 objects {input, expected_output}], hidden_tests: [3 objects {input, expected_output}]. "
        "The bugs must be REAL and fixable in under 60 seconds \u2013 no algorithm rewrites. "
        "The reference_solution MUST match every test case's expected_output exactly. "
        + DIFFICULTY_RULE
    )


def essay_prompt(company: str, section_name: str, target_words: Optional[int] = None) -> Dict[str, str]:
    """`target_words` is optional and additive — omitted (None), every
    caller behaves exactly as before (150-250 words example). Only Wipro's
    Written Communication section sets it (~400 words, per 2026-07-20
    research), via a company-specific length hint instead of the generic
    example, without touching the shared default any other essay-type
    company relies on (e.g. Capgemini's untouched Essay Writing)."""
    length_hint = f"{target_words} words (±15%), not 150-250" if target_words else "150-250 words"
    return {
        "system": "You write short, realistic essay prompts for Indian tech OA rounds.",
        "prompt": (
            f"Generate 1 essay prompt for {company}'s '{section_name}' section. "
            f"Return JSON: {{id, topic (1 line), instructions (2 lines, e.g. {length_hint}, "
            "argue both sides), min_words, max_words}."
        ),
    }


def grade_essay_prompt(topic: str, answer: str, min_w: int, max_w: int) -> str:
    return (
        f"Grade this essay. Topic: \"{topic}\". Required length {min_w}-{max_w} words. "
        f"Answer:\n\"\"\"\n{answer}\n\"\"\"\n\n"
        "Return JSON: {score: 0-100, strengths: [2-3 strings], "
        "weaknesses: [2-3 strings], rewrite_suggestion: one sentence}."
    )


def speaking_prompt(company: str) -> Dict[str, str]:
    """Generation-side prompt for Cognizant's Speaking section: a single
    spoken-response topic, phrased for a ~60-second conversational answer
    (not an essay) after a 30-second prep window."""
    return {
        "system": "You write short spoken-response prompts for Indian tech OA communication rounds.",
        "prompt": (
            f"Generate 1 spoken-response topic for {company}'s Speaking section. "
            "The candidate gets 30 seconds to prepare and ~60 seconds to speak "
            "(roughly 90-160 words). Return JSON: {id, topic (1 line, everyday/HR-style, "
            "e.g. describe a place/hobby/experience — NOT an essay debate topic), "
            "instructions (1 line telling them to speak naturally for about a minute), "
            "min_words: 70, max_words: 170}."
        ),
    }


def communication_speaking_prompts(company: str, count: int) -> Dict[str, str]:
    """Batched sibling of speaking_prompt — generates `count` spoken-response
    topics in ONE call (used by Accenture's mixed Communication Assessment,
    where ~half the section is spoken items) instead of `count` separate
    round-trips. Same per-item shape as speaking_prompt's single topic."""
    return {
        "system": "You write short spoken-response prompts for Indian tech OA communication rounds.",
        "prompt": (
            f"Generate {count} DISTINCT spoken-response topics for {company}'s Communication "
            "Assessment. Each candidate gets ~30 seconds to prepare and ~60 seconds to speak per "
            "topic (roughly 90-160 words). Return JSON array, each item: "
            "{id, topic (1 line, everyday/HR-style, e.g. describe a place/hobby/experience/opinion "
            "— NOT an essay debate topic), instructions (1 line telling them to speak naturally for "
            "about a minute), min_words: 70, max_words: 170}. Vary the topics — no two should be "
            "close variants of each other."
        ),
    }


def grade_spoken_response_prompt(topic: str, transcript: str, min_w: int, max_w: int) -> str:
    """Sibling to grade_essay_prompt, deliberately NOT framed as essay grading —
    a Whisper transcript of natural speech is conversational and shouldn't be
    penalized for lacking essay structure or for filler words/false starts."""
    return (
        f"Grade this transcript of a SPOKEN response (not a written essay — it's a "
        f"Whisper transcription of ~60 seconds of natural speech, so short sentences, "
        f"informal phrasing, and minor false starts are normal and should NOT be "
        f"penalized). Topic: \"{topic}\". Expected length {min_w}-{max_w} words. "
        f"Transcript:\n\"\"\"\n{transcript}\"\"\"\n\n"
        "Judge clarity, relevance to the topic, and fluency of spoken English. "
        "Return JSON: {score: 0-100, strengths: [2-3 strings], "
        "weaknesses: [2-3 strings], rewrite_suggestion: one sentence}."
    )


def reading_listening_prompt(company: str, count: int) -> str:
    """Generates short standalone sentences for Cognizant's Reading & Listening
    (repeat-statements) section. These are shown to the candidate to read/repeat
    aloud, so unlike puzzle answer keys they are NOT secret."""
    return (
        f"Generate {count} short standalone sentences for {company}'s Reading & "
        "Listening communication-assessment section. Each sentence should be "
        "8-16 words, natural spoken English, suitable for a candidate to read "
        "aloud or repeat after hearing it once. Vary vocabulary and sentence "
        "structure across items. Return JSON array of {id, text}."
    )


def grade_coding_prompt(problem: dict, code: str, language: str, visible_pass: int, visible_total: int, hidden_pass: int, hidden_total: int) -> str:
    return (
        "Grade this coding submission. Only consider correctness "
        "(tests passed) and code quality. "
        f"Problem title: {problem.get('title')}. "
        f"Visible tests passed: {visible_pass}/{visible_total}. "
        f"Hidden tests passed: {hidden_pass}/{hidden_total}.\n"
        f"Language: {language}\nCode:\n```\n{code[:3500]}\n```\n\n"
        "Return JSON: {score: 0-100, complexity_note: one sentence, "
        "correctness_note: one sentence, style_note: one sentence}."
    )


INTERVIEW_SYSTEM = (
    "You are a strict but fair Indian tech interviewer for the company shown. "
    "Ask 1 question at a time. Follow up on vague/incorrect answers. Cover: "
    "2 DSA problems, 2 questions on the candidate's actual resume projects, "
    "3 core CS fundamentals questions (OS/DBMS/Networks/OOP). "
    "Keep each question under 60 words. Do not reveal answers until the end."
)


def interview_plan_prompt(company: str, resume_projects: List[dict], difficulty_hint: Optional[str] = None) -> str:
    proj_text = json.dumps(resume_projects[:5]) if resume_projects else "[]"
    if (difficulty_hint or "").lower() in ("medium", "medium_hard", "medium-hard"):
        dsa_line = (
            "Include exactly 2 DSA questions at solid Medium difficulty "
            "(non-trivial data structures / algorithms — not warm-up level), "
        )
    else:
        dsa_line = "Include exactly 2 DSA (easy/medium — describe the problem in prose with one input/output example inline in the same string), "
    return (
        f"Plan a 7-question interview for a fresher at {company}. Return JSON: "
        "{questions: [{id (unique string like 'q1'), kind (dsa|project|fundamentals), "
        "prompt (a single plain string — no nested objects, no markdown headings, "
        "just the question the interviewer would say out loud), "
        "expected_signals: [2-3 short strings]}]}. "
        f"Candidate projects: {proj_text}. "
        f"{dsa_line}"
        "2 project questions (reference the projects by name), and 3 fundamentals questions. "
        "CRITICAL: `prompt` MUST be a string, never an object."
    )


def grade_answer_prompt(question: dict, answer: str) -> str:
    return (
        f"Grade this interview answer. Question: \"{question['prompt']}\" "
        f"(kind={question.get('kind')}). Expected signals: {question.get('expected_signals', [])}. "
        f"Answer:\n\"\"\"\n{answer}\n\"\"\"\n\n"
        "Return JSON: {score: 0-100, signals_hit: [strings], missed: [strings], "
        "follow_up: one short follow-up question OR null if no follow-up needed, "
        "one_line_verdict: string}."
    )


def final_report_prompt(company: str, resume_analysis: dict, oa_summary: dict, interview_summary: dict) -> str:
    return (
        f"Write ONE cohesive final report tying resume, OA, and interview together for "
        f"{company}. Do NOT split into disconnected sections. Return JSON: "
        "{overall_verdict: 'clear'|'borderline'|'not_ready', "
        "overall_score: 0-100, narrative: 3-5 short paragraphs as a single string with \\n\\n between them, "
        "weakest_dimension: string, strongest_dimension: string, "
        "next_steps: [3 short action items]}.\n\n"
        f"RESUME_ANALYSIS: {json.dumps(resume_analysis)[:2000]}\n\n"
        f"OA_SUMMARY: {json.dumps(oa_summary)[:2000]}\n\n"
        f"INTERVIEW_SUMMARY: {json.dumps(interview_summary)[:2000]}"
    )
