"""MCQ pre-generation + ground-truth pool.

New three-stage pipeline (post the Feb-13-2026 architectural fix):

    Stage A — GENERATE STEM: the generator LLM (Haiku) writes ONLY the
      question prompt + 4 options + difficulty. It is explicitly NOT asked
      for a `correct_index` or `explanation`. This closes the failure mode
      where the explanation is written to rationalize a fixed target answer.

    Stage B — DERIVE GROUND TRUTH: for questions whose prompt contains a
      code block, we transpile-and-execute the code and match stdout against
      the options — pure ground-truth, no LLM judgment. For everything else,
      we run TWO independent solver calls (Sonnet + Haiku, both blind to
      each other and to any claimed answer). Only when both solvers agree
      does the answer make it through.

    Stage C — EXPLANATION WITH CONFLICT-FLAG: a separate LLM call is asked
      to reason from first principles about the derived answer and either
      (a) produce an explanation that supports it, or (b) FLAG A CONFLICT
      if its own reasoning doesn't match — instructed explicitly NOT to
      rationalize. Any conflict discards the question.

Every stored question thus carries a `ground_truth_source` in {"execution",
"solver_agreement"} plus an explanation that the C-stage LLM will stand
behind (no contortion). Historical questions predating this pipeline still
carry the old shape — they're gradually replaced as the pool refills.

Only these section keys are pooled (matching the config in companies.py):
    verbal, reasoning, numerical, aptitude, cs-fundamentals, technical,
    logical, quant, analytical, english, puzzles, advanced, and per-topic
    core-* keys for the Core Assessment (Default) track.

Everything else (coding, essay, comm, cognitive_game, pseudocode-typed
sections, game, pen-paper, Automata Fix) goes through their existing live
paths untouched.
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.ai_service import (
    call_json, HAIKU, SONNET,
    mcq_prompt, topic_mcq_prompt, aptitude_topic_mix_prompt,
    solver_prompt, explanation_prompt,
)
from services.code_runner import run_code

logger = logging.getLogger(__name__)

# ---- Configuration ----------------------------------------------------------

POOL_BUFFER = 10                   # target per (company, section_key) while active
MAX_VERIFY_RETRIES = 2             # per attempt, before giving up for this loop
WORKER_TICK_SECONDS = 15           # how often the worker checks pool levels
LOG_STATS_EVERY_N_VERIFIES = 20    # emit disagreement rate to logs every N verifies

# Demand-aware pause (2026-07-21): the worker used to top up every pool 24/7
# regardless of real traffic. Now it only speculatively warms while there's
# been recent real activity; long idle stretches pause the sweep entirely
# except for a small safety floor. See record_activity() / _worker_loop().
IDLE_THRESHOLD_SECONDS = 1200       # 20 min with no real activity -> pause speculative warming
MIN_SAFETY_BUFFER = 2               # floor maintained even while paused -- a pool never hits 0

# Topic → generic "topic label" used when picking a broad company for warmup.
# Keeps the pool tagged by section_key so we serve the same style back.
POOLED_SECTION_KEYS = {
    "verbal", "reasoning", "numerical", "aptitude", "cs-fundamentals",
    "technical", "logical", "quant", "analytical", "english", "puzzles",
    "advanced",
    # Per-topic keys used by the "Core Assessment (Default)" track. These are
    # populated by the pool worker one-per-topic via topic_mcq_prompt.
    "core-aptitude", "core-verbal", "core-oops", "core-dbms", "core-os",
    "core-cn", "core-architecture", "core-reasoning",
}

# Section keys whose pool entries are generated via topic_mcq_prompt rather
# than mcq_prompt. Maps the pool key to (topic_key, topic_name).
TOPIC_KEY_MAP = {
    "core-aptitude":     ("aptitude",     "Aptitude"),
    "core-verbal":       ("verbal",       "Verbal"),
    "core-oops":         ("oops",         "Object-Oriented Programming"),
    "core-dbms":         ("dbms",         "Database Management Systems"),
    "core-os":           ("os",           "Operating Systems"),
    "core-cn":           ("cn",           "Computer Networks"),
    "core-architecture": ("architecture", "Computer Architecture"),
    "core-reasoning":    ("reasoning",    "Logical Reasoning"),
}

# ---- DB handle wiring -------------------------------------------------------
# server.py holds the Motor client; we inject the db instance at startup so this
# module doesn't need to import server (and avoid circular imports).

_db = None  # set by init(db)


def init(db) -> None:
    global _db
    _db = db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- Demand-aware activity clock --------------------------------------------
# In-process timestamp of the last real demand signal (a live-pool serve, or an
# OA session starting). No DB round-trip needed -- the worker loop and every
# real-serving call site live in this one process.
_last_activity_ts: float = datetime.now(timezone.utc).timestamp()


def record_activity() -> None:
    global _last_activity_ts
    _last_activity_ts = datetime.now(timezone.utc).timestamp()


# ---- Public API called from the live request path --------------------------

async def is_pooled_key(section_key: str) -> bool:
    return section_key in POOLED_SECTION_KEYS


async def pop_from_pool(company_name: str, section_key: str, section_name: str, count: int) -> List[dict]:
    """Atomically remove up to `count` verified questions from the pool for
    (company_name, section_key). Returns however many were available.
    """
    record_activity()
    if _db is None:
        return []
    out: List[dict] = []
    for _ in range(count):
        doc = await _db.mcq_pool.find_one_and_delete(
            {"company_name": company_name, "section_key": section_key, "verified": True},
        )
        if not doc:
            break
        out.append({
            "id": f"q{len(out)+1}",
            "prompt": doc["prompt"],
            "options": doc["options"],
            "correct_index": doc["correct_index"],
            "explanation": doc.get("explanation", ""),
            "difficulty": doc.get("difficulty", "Medium"),
        })
    return out


async def _pipeline_shape(raw: Any, cap: Optional[int] = None, company_name: str = "live", section_key: str = "live") -> List[dict]:
    """Live fallback: run generator stems through the same 3-stage pipeline
    used by the background worker. Used when the pool is empty at serve time."""
    if not isinstance(raw, list):
        return []
    tasks = [
        _process_one_stem(company_name, section_key, stem)
        for stem in raw if isinstance(stem, dict)
    ]
    docs = await asyncio.gather(*tasks, return_exceptions=True)
    kept: List[dict] = []
    for d in docs:
        if isinstance(d, dict):
            kept.append({
                "id": f"q{len(kept)+1}",
                "prompt": d.get("prompt", ""),
                "options": d.get("options", []),
                "correct_index": d.get("correct_index"),
                "explanation": d.get("explanation", ""),
                "difficulty": d.get("difficulty", "Medium"),
            })
    if cap is not None:
        kept = kept[:cap]
    for i, q in enumerate(kept):
        q["id"] = f"q{i+1}"
    return kept


async def fallback_live_verify(company_name: str, section_name: str, section_key: str, count: int, difficulty_target: Optional[str]) -> List[dict]:
    """Fallback path when the pool is empty (e.g. first-boot warmup). Runs
    the exact same 3-stage ground-truth pipeline as the background worker,
    just synchronously in the request path. User is never served an
    unverified question."""
    record_activity()
    system = "You are an expert Indian tech OA question setter. Return only strict JSON."
    raw = await call_json(system, mcq_prompt(company_name, section_name, count, difficulty_target), model=HAIKU)
    return await _pipeline_shape(raw, cap=count, company_name=company_name, section_key=section_key)


async def fallback_live_verify_topic_mix(
    company_name: str, count: int, topic_groups: List[Dict[str, Any]], difficulty_target: Optional[str], section_key: str,
) -> List[dict]:
    """Wipro's 3-sub-section Aptitude Test (Quant + Logical + Verbal). Same
    ground-truth pipeline as fallback_live_verify, seeded with the topic-mix
    prompt instead of the plain one. Always live-generates for whatever `count`
    it's given — deliberately bypasses the cross-company pool (pop_from_pool),
    since pool entries for a shared key like "aptitude" are generic and don't
    know about this company's specific topic_groups split.

    Since 2026-07-22 this is no longer always the section's sole source: the
    caller (server.py's _generate_topic_mix) now calls this once PER sub-group
    with only that group's post-static-bank shortfall, not the full section
    count in one call. This function's own behavior is unchanged -- it's just
    invoked with a smaller `count` and a single-group `topic_groups` list."""
    record_activity()
    system = "You are an expert Indian tech OA question setter. Return only strict JSON."
    raw = await call_json(system, aptitude_topic_mix_prompt(company_name, count, topic_groups, difficulty_target), model=HAIKU)
    return await _pipeline_shape(raw, cap=count, company_name=company_name, section_key=section_key)


async def fallback_live_verify_topic(company_name: str, topic_key: str, topic_name: str, count: int, difficulty_target: Optional[str]) -> List[dict]:
    """Topic-specific fallback. Same pipeline, per-topic prompt.

    Accumulates across attempts rather than discarding a partial first
    result — previously, a non-empty-but-short first attempt (e.g. 5 of 6
    requested, because one candidate failed ground-truth verification) was
    accepted as final with no retry, silently under-serving that topic by
    however many candidates got dropped. Now the second attempt asks only
    for the remaining shortfall and appends to what's already verified."""
    record_activity()
    system = "You are an expert Indian tech OA question setter. Return only strict JSON."
    section_key = f"core-{topic_key}"
    out: List[dict] = []
    for attempt in range(2):
        needed = count - len(out)
        if needed <= 0:
            break
        ask = max(needed, 3) if attempt == 0 else needed + 1
        raw = await call_json(system, topic_mcq_prompt(company_name, topic_key, topic_name, ask, difficulty_target), model=HAIKU)
        got = await _pipeline_shape(raw, cap=needed, company_name=company_name, section_key=section_key)
        out.extend(got)
    return out[:count]


# ---- Stage-B ground-truth derivation ---------------------------------------
# When the prompt contains a code snippet, we EXECUTE it (real Python
# interpreter subprocess) and match stdout against the options. This is the
# only path that gives byte-for-byte ground truth — no LLM judgment.

# Match fenced code blocks. We accept python/py fences by default; unlabelled
# fences are treated as Python if the code looks like Python (heuristic below).
_CODE_FENCE_RE = re.compile(r"```(?P<lang>[a-zA-Z0-9+_-]*)\s*\n(?P<code>.*?)```", re.DOTALL)
_PY_HINTS = re.compile(r"\b(print|def |class |for |while |if |import |return )\b")


def _extract_code_block(prompt_text: str) -> Optional[Tuple[str, str]]:
    """Return (language, code) if the prompt contains a runnable Python fence,
    else None. Currently we only auto-execute Python — trying to run arbitrary
    C/C++/Java from generated prompts is too fragile for a background worker."""
    for m in _CODE_FENCE_RE.finditer(prompt_text or ""):
        lang = (m.group("lang") or "").strip().lower()
        code = m.group("code") or ""
        if not code.strip():
            continue
        if lang in ("python", "py", "python3"):
            return "python", code
        if lang == "" and _PY_HINTS.search(code):
            return "python", code
    return None


def _normalize(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _match_stdout_to_options(stdout: str, options: List[str]) -> Optional[int]:
    """Match a program's stdout against 4 options. Return the index if EXACTLY
    one option matches (normalized equality first, containment fallback), else
    None. This is shared by the code-fence execution path AND the pseudocode
    transpile path — both derive answers from real stdout, no LLM judgment."""
    if not stdout:
        return None
    norm_out = _normalize(stdout)
    matches: List[int] = []
    for i, opt in enumerate(options):
        if _normalize(str(opt)) == norm_out:
            matches.append(i)
    if len(matches) == 1:
        return matches[0]
    # Looser containment match (handles trailing newlines, wrapped strings).
    matches = []
    for i, opt in enumerate(options):
        norm_opt = _normalize(str(opt))
        if norm_opt and (norm_opt in norm_out or norm_out in norm_opt):
            matches.append(i)
    if len(matches) == 1:
        return matches[0]
    return None


async def _ground_truth_from_execution(prompt_text: str, options: List[str]) -> Optional[Tuple[int, str]]:
    """Direct-execution ground truth: if the prompt contains a Python code
    fence, run it and match stdout against options."""
    extracted = _extract_code_block(prompt_text)
    if not extracted:
        return None
    lang, code = extracted
    try:
        result = await asyncio.to_thread(run_code, lang, code, "", 5)
    except Exception as e:
        logger.info("[mcq_pool] execution failed on generated snippet: %s", e)
        return None
    if not isinstance(result, dict):
        return None
    if result.get("timed_out") or result.get("exit_code") not in (0, None):
        return None
    stdout = str(result.get("stdout") or "").strip()
    matched = _match_stdout_to_options(stdout, options)
    if matched is None:
        return None
    return matched, stdout


# ---- Transpile-and-execute ground truth for PSEUDOCODE ---------------------
# For pseudocode questions the generator often writes language-neutral code
# ("SET x = 5", "FOR i FROM 1 TO 10", etc.) that can't be executed directly.
# We ask an LLM to do a mechanical, semantics-preserving transpilation into
# Python and then run it. The LLM is instructed NOT to fix bugs or reshape
# logic — just translate — and to flag `unclear` if the source isn't
# runnable code at all. The answer comes from the interpreter, not the LLM.

_CODE_OUTPUT_HINTS = re.compile(
    r"(?i)\b(output|prints?|prints?ed|printed|display|returns?|program|"
    r"pseudo\s*code|pseudocode|trace|what\s+will\s+be|what\s+does)\b"
)
_CODE_SYNTAX_HINTS = re.compile(
    r"(?:\bdef\b|\bclass\b|\bfor\b|\bwhile\b|\bprint\s*\(|\bif\b|\breturn\b|"
    r"\bBEGIN\b|\bEND\b|\bSET\b|\bLET\b|\bDECLARE\b|"
    r"[{};]|:=|<<|>>|->|==|!=|\+\+|\-\-|%%|\|\|)"
)


def _looks_like_code_output_question(prompt_text: str) -> bool:
    if not prompt_text:
        return False
    return bool(_CODE_OUTPUT_HINTS.search(prompt_text) and _CODE_SYNTAX_HINTS.search(prompt_text))


def _transpile_prompt(prompt_text: str) -> Tuple[str, str]:
    return (
        "You convert pseudocode (or arbitrary language code) into runnable Python. "
        "STRICT RULES:\n"
        "  1) Semantics MUST match the source exactly — same output, same order, "
        "     same side effects. Do NOT fix bugs. Do NOT restructure logic. Do NOT "
        "     add tests, prints, or output that the source didn't produce.\n"
        "  2) You may rename identifiers only when required to make the code valid "
        "     Python (e.g. reserved words). Otherwise keep names.\n"
        "  3) If the source is already Python, return it verbatim.\n"
        "  4) If the source contains ambiguous constructs (e.g. undefined "
        "     functions, missing loop bounds, non-executable pseudo like 'do stuff'), "
        "     return {\"unclear\": true, \"reason\": \"<one line>\"}.\n"
        "  5) If the question is NOT about tracing code output, return {\"unclear\": true}.\n"
        "Return ONLY strict JSON: {\"python\": \"<runnable python code as a single string>\"} "
        "OR {\"unclear\": true, \"reason\": \"<one line>\"}.",
        f"Question containing pseudocode:\n{prompt_text}\n\n"
        "Extract the pseudocode and translate it into equivalent Python that prints "
        "exactly what the pseudocode would print."
    )


async def _ground_truth_from_pseudocode_transpile(
    prompt_text: str, options: List[str],
) -> Optional[Tuple[int, str]]:
    """LLM converts pseudocode → Python (mechanical, low creativity), we run
    it, and the interpreter's actual stdout becomes the correct answer."""
    if not _looks_like_code_output_question(prompt_text):
        return None
    system, user = _transpile_prompt(prompt_text)
    try:
        resp = await call_json(system, user, model=HAIKU)  # mechanical → Haiku is cheap enough
    except Exception as e:
        logger.info("[mcq_pool] transpile call failed: %s", e)
        return None
    if not isinstance(resp, dict) or resp.get("unclear"):
        return None
    py = resp.get("python")
    if not isinstance(py, str) or not py.strip():
        return None
    try:
        result = await asyncio.to_thread(run_code, "python", py, "", 5)
    except Exception as e:
        logger.info("[mcq_pool] transpile-execute failed: %s", e)
        return None
    if not isinstance(result, dict):
        return None
    if result.get("timed_out") or result.get("exit_code") not in (0, None):
        return None
    stdout = str(result.get("stdout") or "").strip()
    matched = _match_stdout_to_options(stdout, options)
    if matched is None:
        return None
    return matched, stdout


async def _solver_pick(prompt_text: str, options: List[str], model: tuple) -> Optional[int]:
    system, user = solver_prompt(prompt_text, options)
    try:
        resp = await call_json(system, user, model=model)
    except Exception as e:
        logger.warning("[mcq_pool] solver call (%s) failed: %s", model[1], e)
        return None
    if not isinstance(resp, dict):
        return None
    v = resp.get("correct_index")
    return v if v in (0, 1, 2, 3) else None


async def _ground_truth_from_solvers(prompt_text: str, options: List[str]) -> Optional[int]:
    """Two independent LLM solvers must agree. Sonnet + Haiku, both blind."""
    a, b = await asyncio.gather(
        _solver_pick(prompt_text, options, SONNET),
        _solver_pick(prompt_text, options, HAIKU),
    )
    if a is None or b is None:
        return None
    if a == b:
        return a
    return None


# ---- Stage-C explanation writer -------------------------------------------
# Told the derived answer, but instructed to reason from first principles and
# flag a conflict rather than rationalize toward the target. If the writer
# doesn't agree with the derived answer, the question is discarded.

async def _write_explanation_or_conflict(
    prompt_text: str, options: List[str], correct_index: int,
) -> Tuple[Optional[str], Optional[int]]:
    """Return (explanation, conflicting_index).
      - (str, None)   → explanation written, no conflict → serve the question
      - (None, int)   → conflict flagged, explanation writer derived a different
                        index; caller should discard.
      - (None, None)  → LLM call failed / bad shape → caller should discard.
    """
    system, user = explanation_prompt(prompt_text, options, correct_index)
    try:
        resp = await call_json(system, user, model=SONNET)
    except Exception as e:
        logger.warning("[mcq_pool] explanation call failed: %s", e)
        return None, None
    if not isinstance(resp, dict):
        return None, None
    if resp.get("conflict"):
        alt = resp.get("my_derived_index")
        alt = alt if alt in (0, 1, 2, 3) else None
        return None, alt
    exp = resp.get("explanation")
    if isinstance(exp, str) and exp.strip():
        return exp.strip(), None
    return None, None


# ---- Pool worker ------------------------------------------------------------

_worker_task: Optional[asyncio.Task] = None
_worker_stop = False
_worker_was_idle = False  # tracks idle/active transitions for once-per-transition logging


async def _process_one_stem(company_name: str, section_key: str, stem: dict) -> Optional[dict]:
    """Run the full 3-stage pipeline on one generator-produced stem. Returns
    the pool-ready doc on success, or None if the question should be dropped.
    Also records the outcome in mcq_pool_stats for the founder dashboard."""
    prompt_text = stem.get("prompt") or ""
    options = stem.get("options") or []
    if (not prompt_text) or (not isinstance(options, list)) or len(options) != 4:
        await _record_outcome(company_name, section_key, outcome="dropped_malformed")
        return None

    # Stage B: derive ground truth. Preferred order:
    #   1) Direct execution of a fenced Python block in the prompt.
    #   2) Transpile-and-execute for pseudocode/trace-the-output questions.
    #   3) Two independent LLM solvers must agree.
    exec_result = await _ground_truth_from_execution(prompt_text, options)
    if exec_result is not None:
        correct_index, _ = exec_result
        source = "execution"
    else:
        transpile_result = await _ground_truth_from_pseudocode_transpile(prompt_text, options)
        if transpile_result is not None:
            correct_index, _ = transpile_result
            source = "transpile_execution"
        else:
            solved = await _ground_truth_from_solvers(prompt_text, options)
            if solved is None:
                await _record_outcome(company_name, section_key, outcome="dropped_no_ground_truth")
                return None
            correct_index = solved
            source = "solver_agreement"

    # Stage C: explanation with conflict-flag.
    explanation, conflicting_idx = await _write_explanation_or_conflict(prompt_text, options, correct_index)
    if explanation is None:
        # Explanation writer either failed OR flagged a conflict.
        outcome = "dropped_explanation_conflict" if conflicting_idx is not None else "dropped_explanation_failure"
        await _record_outcome(company_name, section_key, outcome=outcome, conflicting_idx=conflicting_idx, derived_idx=correct_index)
        return None

    await _record_outcome(company_name, section_key, outcome="accepted", source=source)
    return {
        "pool_id": uuid.uuid4().hex,
        "company_name": company_name,
        "section_key": section_key,
        "prompt": prompt_text,
        "options": options,
        "correct_index": correct_index,
        "explanation": explanation,
        "difficulty": stem.get("difficulty", "Medium"),
        "verified": True,
        "ground_truth_source": source,
        "created_at": _now_iso(),
    }


async def _generate_and_pool_one(company_name: str, section_key: str, section_name: str, difficulty_target: Optional[str]) -> None:
    """Generate a batch of stems, then pipe each through the 3-stage pipeline."""
    if _db is None:
        return
    system = "You are an expert Indian tech OA question setter. Return only strict JSON."
    batch_size = 3
    topic_meta = TOPIC_KEY_MAP.get(section_key)
    if topic_meta:
        topic_key, topic_name = topic_meta
        gen_prompt = topic_mcq_prompt(company_name, topic_key, topic_name, batch_size, difficulty_target)
    else:
        gen_prompt = mcq_prompt(company_name, section_name, batch_size, difficulty_target)
    raw = await call_json(system, gen_prompt, model=HAIKU)
    if not isinstance(raw, list):
        return
    for stem in raw:
        if not isinstance(stem, dict):
            continue
        doc = await _process_one_stem(company_name, section_key, stem)
        if doc:
            await _db.mcq_pool.insert_one(doc)


async def _record_outcome(
    company_name: str, section_key: str, outcome: str,
    source: Optional[str] = None,
    conflicting_idx: Optional[int] = None,
    derived_idx: Optional[int] = None,
) -> None:
    """Track pipeline outcomes per (company, section) for the founder dashboard.

    `outcome` ∈ {
        "accepted",
        "dropped_malformed",
        "dropped_no_ground_truth",   # two solvers disagreed and no code to run
        "dropped_explanation_conflict",  # C-stage refused to rationalize
        "dropped_explanation_failure",   # C-stage LLM error / bad shape
    }
    """
    if _db is None:
        return
    key = {"company_name": company_name, "section_key": section_key}
    inc: Dict[str, int] = {
        "total_generated": 1,
        f"outcome_{outcome}": 1,
    }
    if source:
        inc[f"source_{source}"] = 1
    update = {
        "$inc": inc,
        "$set": {"updated_at": _now_iso()},
        "$setOnInsert": {**key, "created_at": _now_iso()},
    }
    doc = await _db.mcq_pool_stats.find_one_and_update(key, update, upsert=True, return_document=True)
    tg = doc.get("total_generated", 0) if doc else 0
    if tg and tg % LOG_STATS_EVERY_N_VERIFIES == 0:
        accepted = doc.get("outcome_accepted", 0)
        dropped_ng = doc.get("outcome_dropped_no_ground_truth", 0)
        dropped_conflict = doc.get("outcome_dropped_explanation_conflict", 0)
        by_exec = doc.get("source_execution", 0)
        by_solvers = doc.get("source_solver_agreement", 0)
        logger.info(
            "[mcq_pool_stats] %s/%s: %d generated, accepted=%d "
            "(exec=%d, solvers=%d) · dropped_no_gt=%d · dropped_conflict=%d",
            company_name, section_key, tg, accepted, by_exec, by_solvers, dropped_ng, dropped_conflict,
        )


def _iter_pool_targets(companies: List[dict]) -> List[Tuple[str, str, str, Optional[str]]]:
    """Return list of (company_name, section_key, section_name, difficulty_target)
    for every pool-eligible section across every company."""
    out = []
    for c in companies:
        cname = c["name"]
        for s in c.get("sections", []):
            stype = s.get("type")
            diff = s.get("difficulty_target")

            # `extra_topics` (Capgemini's Technical: OOPS/DBMS/OS/CN alongside
            # pseudocode; LTIMindtree's CS Fundamentals: DBMS/OOPS/OS standalone)
            # is an OPTIONAL additive layer independent of the section's own
            # `type` — fan out into one target per topic ("core-{topic}"),
            # same as topic_mcq below. Previously unrecognized entirely here,
            # meaning the worker never knew these "core-*" pool keys needed
            # topping up, so server.py's _generate_extra_topics always paid
            # full live-verify cost regardless of how long the server ran.
            extra_topics = s.get("extra_topics") or []
            for t in extra_topics:
                topic_key = t.get("key")
                if not topic_key:
                    continue
                pool_key = f"core-{topic_key}"
                if pool_key not in POOLED_SECTION_KEYS:
                    continue
                out.append((cname, pool_key, t.get("name", topic_key), diff))

            # Compound topic-MCQ sections (used by "Core Assessment (Default)")
            # fan out into one target per topic key so the pool worker keeps
            # each topic bucket independently topped up.
            if stype == "topic_mcq":
                for t in s.get("topics", []) or []:
                    topic_key = t.get("key")
                    if not topic_key:
                        continue
                    pool_key = f"core-{topic_key}"
                    if pool_key not in POOLED_SECTION_KEYS:
                        continue
                    out.append((cname, pool_key, t.get("name", topic_key), diff))
                continue
            if stype != "mcq":
                continue
            if extra_topics or s.get("topic_groups"):
                # This section's OWN key is never read by server.py's serving
                # code (extra_topics/topic_groups sections bypass it entirely
                # — see the mcq branch's dedicated checks) — don't waste
                # worker cycles pre-warming a pool nothing will ever pop from.
                # (topic_groups, e.g. Wipro's blended Quant+Logical+Verbal
                # Aptitude, isn't fanned out per-topic here either — one
                # combined prompt call doesn't split cleanly into per-topic
                # pool keys the way extra_topics's separate per-topic calls
                # do; it stays live-only until/unless that's redesigned.)
                continue
            key = s.get("key")
            if key not in POOLED_SECTION_KEYS:
                continue
            out.append((cname, key, s.get("name", key), diff))
    return out


async def _worker_loop(companies: List[dict]) -> None:
    global _worker_was_idle
    logger.info("[mcq_pool] worker started, buffer=%d, verify_model=%s", POOL_BUFFER, SONNET[1])
    targets = _iter_pool_targets(companies)
    while not _worker_stop:
        try:
            # Demand-aware pause: with no real activity (a live-pool serve or an
            # OA session start) in the last IDLE_THRESHOLD_SECONDS, most targets
            # get skipped entirely this sweep -- only a target that's dropped
            # below MIN_SAFETY_BUFFER still tops up, so a pool never hits 0 even
            # through a long idle stretch. Real requests are never blocked by
            # this either way (server.py's fallback_live_verify* already
            # generates synchronously on demand) -- this only stops speculative
            # pre-warming for requests that haven't happened yet.
            now = datetime.now(timezone.utc).timestamp()
            idle = (now - _last_activity_ts) > IDLE_THRESHOLD_SECONDS
            if idle != _worker_was_idle:
                logger.info(
                    "[mcq_pool] worker %s (idle_for=%.0fs)",
                    "pausing speculative warming" if idle else "resuming normal warming",
                    now - _last_activity_ts,
                )
                _worker_was_idle = idle
            target_level = MIN_SAFETY_BUFFER if idle else POOL_BUFFER

            for cname, key, sname, diff in targets:
                if _worker_stop:
                    break
                if _db is None:
                    break
                count = await _db.mcq_pool.count_documents({
                    "company_name": cname, "section_key": key, "verified": True,
                })
                if count < target_level:
                    try:
                        await _generate_and_pool_one(cname, key, sname, diff)
                    except Exception as e:
                        logger.warning("[mcq_pool] gen failed for %s/%s: %s", cname, key, e)
                    # brief yield to avoid hammering the LLM key
                    await asyncio.sleep(1.0)
            # Tick pause between full sweeps
            await asyncio.sleep(WORKER_TICK_SECONDS)
        except asyncio.CancelledError:
            break
        except Exception as e:  # pragma: no cover
            logger.exception("[mcq_pool] worker loop error: %s", e)
            await asyncio.sleep(10)
    logger.info("[mcq_pool] worker stopped")


def start_worker(companies: List[dict]) -> None:
    """Kick off the singleton worker task. Idempotent."""
    global _worker_task
    if _worker_task is not None and not _worker_task.done():
        return
    _worker_task = asyncio.create_task(_worker_loop(companies))


def stop_worker() -> None:
    global _worker_stop, _worker_task
    _worker_stop = True
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()


# ---- Admin readouts ---------------------------------------------------------

async def pool_stats() -> Dict[str, Any]:
    """Founder-only readout — new-pipeline metrics tell you WHERE questions are
    being dropped (no ground truth vs. explanation-flagged conflict) and WHICH
    ground-truth source (execution vs. solver-agreement) is producing them.
    """
    if _db is None:
        return {"pool_counts": [], "stats": []}
    pool = []
    async for doc in _db.mcq_pool.aggregate([
        {"$group": {"_id": {"c": "$company_name", "k": "$section_key"}, "count": {"$sum": 1}}},
        {"$project": {"_id": 0, "company_name": "$_id.c", "section_key": "$_id.k", "count": 1}},
        {"$sort": {"company_name": 1, "section_key": 1}},
    ]):
        pool.append(doc)
    stats = []
    async for doc in _db.mcq_pool_stats.find({}, {"_id": 0}):
        tg = doc.get("total_generated", 0)
        accepted = doc.get("outcome_accepted", 0)
        dropped_no_gt = doc.get("outcome_dropped_no_ground_truth", 0)
        dropped_conflict = doc.get("outcome_dropped_explanation_conflict", 0)
        dropped_expfail = doc.get("outcome_dropped_explanation_failure", 0)
        by_exec = doc.get("source_execution", 0)
        by_solvers = doc.get("source_solver_agreement", 0)
        doc["acceptance_rate_pct"] = round((accepted / tg) * 100, 2) if tg else 0.0
        doc["dropped_no_ground_truth_pct"] = round((dropped_no_gt / tg) * 100, 2) if tg else 0.0
        doc["dropped_explanation_conflict_pct"] = round((dropped_conflict / tg) * 100, 2) if tg else 0.0
        doc["dropped_explanation_failure_pct"] = round((dropped_expfail / tg) * 100, 2) if tg else 0.0
        doc["from_execution"] = by_exec
        doc["from_solver_agreement"] = by_solvers
        stats.append(doc)
    stats.sort(key=lambda d: (d.get("company_name", ""), d.get("section_key", "")))
    return {
        "buffer_target": POOL_BUFFER,
        "pipeline": "3-stage: generate-stem-only -> execute-or-two-solvers -> explanation-with-conflict-flag",
        "generator_model": HAIKU[1],
        "solver_a_model": SONNET[1],
        "solver_b_model": HAIKU[1],
        "explanation_model": SONNET[1],
        "pool_counts": pool,
        "stats": stats,
    }
