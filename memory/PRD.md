# Placemint — PRD

## Original Problem Statement
Build "Placemint" — a placement-prep simulator for Indian engineering freshers that runs the actual Online Assessment and interview structure each of 14 supported companies really uses. Four phases: Resume Checker → Online Assessment → Interview → Cross-Phase Review.

## User Personas
- **Primary:** Final-year Indian engineering student prepping for TCS NQT, Infosys, Wipro, Cognizant, Accenture, IBM, Zoho, Capgemini, HCLTech, LTIMindtree, Tech Mahindra, Deloitte USI, Microsoft SWE, or a generic product-based company.
- **Secondary:** College placement cells running batch prep.

## Core Requirements (static)
1. **Landing** — hero + pipeline diagram + 14-company grid + pricing + FAQ.
2. **Auth** — JWT email/password + Emergent-managed Google OAuth.
3. **Resume Checker** — free, unlimited. PDF upload → Claude Haiku 4.5 analysis against a specific company/role.
4. **Online Assessment engine** — each of the 14 companies runs its real section order, timing, cutoff logic (sectional vs composite), and question mix. Question generation via Claude Haiku 4.5.
5. **Coding rounds** — LeetCode-style split panel with dark Monaco editor; visible + hidden tests; Python live-runnable.
6. **Adaptive Interview** — 2 DSA + 2 project (from actual resume) + 3 CS fundamentals. Chat UX.
7. **Cross-Phase Report** — one cohesive narrative from resume + OA + interview.
8. **Pricing / Razorpay** — 5 tiers (Free, Basic ₹299/mo, Pro ₹599/mo, MAX ₹799, SuperMAX ₹1099). Razorpay checkout wired; mock mode when keys are placeholders.

## Tech Stack
- **Backend:** FastAPI + Motor (MongoDB) + direct Anthropic SDK (Claude Sonnet 4.5 / Haiku 4.5, via ANTHROPIC_API_KEY) + direct OpenAI SDK (GPT-5.4 Mini for OA coding/open-answer grading only, via OPENAI_API_KEY) + Razorpay SDK + pdfplumber. Migrated off emergentintegrations 2026-07-16.
- **Frontend:** React CRA + CRACO + Tailwind + framer-motion + Monaco Editor + react-router + sonner.
- **Design tokens:** #FAF8F3 bg, #0FAE73 mint primary, #FF6F4D coral accent, Outfit/Inter/JetBrains Mono.

## Changelog

- **Feb 13, 2026 (9)** — Extended ground-truth pipeline with transpile-and-execute for pseudocode.
  - **New Stage-B step:** `_ground_truth_from_pseudocode_transpile` — an LLM (Haiku, mechanical low-creativity) converts pseudocode / non-Python code in the prompt into equivalent Python, then `code_runner.run_code("python", ...)` executes it and `_match_stdout_to_options` maps stdout to the correct option. Transpiler is explicitly forbidden from fixing bugs, restructuring logic, or adding output; if the source is not runnable code it returns `{unclear: true}` and the pipeline moves on. New shared `_match_stdout_to_options` helper (used by both direct-execute and transpile-execute paths).
  - **New Stage-B order:** (1) direct execution of a Python code fence → (2) transpile-execute for pseudocode-shape prompts → (3) two independent LLM solvers must agree → discard. `ground_truth_source` now takes a third value `"transpile_execution"`.
  - **Pseudocode-typed sections now use the pipeline.** `server._generate_section_questions` previously took `stype == 'pseudocode'` through a raw `call_json(pseudocode_prompt(...))` path — no ground truth, no verification. That branch now calls `mcq_pool.fallback_live_verify(...)` so TCS NQT, Wipro Elite, Cognizant NQT, and Infosys HackWithInfy R1 pseudocode sections all get the 3-stage pipeline.
  - Heuristic `_looks_like_code_output_question` short-circuits the transpile call on non-code prompts (verbal / quant / etc.), saving ~1 LLM call per stem during pool warmup.
  - **Testing (`testing_agent_v3_fork` iterations 6 + 7):** iteration 6 → 20/21 with a critical shadowed-elif bug caught in `server.py:743`; fix was a two-line change (replaced dead raw path with the pipeline call, deleted the unreachable duplicate branch). Iteration 7 → **21/21 green**, ~101s runtime, no regressions. Unit-verified transpile path on BEGIN/END pseudo (idx 1 = "7"), Java-style code (idx 0 = "13"), and a non-code question (skipped correctly).


- **Feb 13, 2026 (8)** — Bug fix: re-architected MCQ pool pipeline into 3 stages after user architectural critique ("ground-truth execution, not LLM-judgment, should set correct_index" + "explanation generation should not be told the correct answer to rationalize toward").
  - **Stage A — generate stem only.** `mcq_prompt` / `topic_mcq_prompt` now emit ONLY `{id, prompt, options, difficulty}`. Explicitly forbid `correct_index` and `explanation` in the generator's output. Closes the "explanation rationalizes toward a fixed target" failure mode at the source.
  - **Stage B — derive ground truth independently.**
    - For questions whose prompt contains a Python code fence, `_ground_truth_from_execution` transpile-and-executes via `code_runner.run_code("python", …)` (subprocess, 5s timeout) and matches stdout against options. Byte-for-byte ground truth, no LLM judgment.
    - Otherwise, two independent LLM solvers (Sonnet + Haiku, both blind) via `_ground_truth_from_solvers`. Must agree. Any disagreement or -1 = discard.
  - **Stage C — explanation with conflict-flag.** New `explanation_prompt` gives the LLM the derived correct_index BUT instructs it to reason from first principles and return `{conflict: true, my_derived_index, reason}` rather than rationalize. Any conflict = discard.
  - Retired the old `_verify_question` / `_verify_and_shape` dual-Sonnet gate. Every pool doc now carries `ground_truth_source` ∈ {"execution", "solver_agreement"}.
  - New `mcq_pool_stats` shape (`outcome_*`, `source_*`, `acceptance_rate_pct`). `/api/admin/mcq-stats` returns new pipeline description + 4-model breakdown (generator/solver_a/solver_b/explanation).
  - Purged existing pool (106 docs) + stats (25 docs) so the new pipeline seeds from scratch.
  - **Testing (`testing_agent_v3_fork` iteration 5):** 11/11 pytest cases passed in ~100s. Unit test on hand-crafted code stem (`print(2+3)`) → execution ground truth picks index 2. Live pool grows with `ground_truth_source: "solver_agreement"` docs. Independent Sonnet re-check on 5 served MCQs → 0 regressions. Regression suite: `/app/backend/tests/test_mcq_pipeline_v3.py`; older `test_mcq_verification.py` deleted (referenced removed fields).


- **Feb 13, 2026 (7)** — Bug fix: "answer is marked wrong even though the explanation reasons toward the picked answer."
  - **Root cause:** Haiku sometimes writes an `explanation` arguing for option B while emitting `correct_index: 2 (C)`. The independent verifier (Sonnet, blind to the explanation) could occasionally hallucinate the same wrong pick, letting an inconsistent question into the pool.
  - **Fix (per user's suggestion — check the "why" first, then the answer):** `_verify_question` now runs TWO Sonnet calls in parallel: (1) the original independent verifier (sees only question + options), (2) a new **explanation-derived-index** call (reads the explanation and identifies which option it argues for). Decision matrix:
    - Both agree with each other AND with generator's claim → serve as-is.
    - Both agree with each other but NOT with generator's claim → **override** `correct_index` to the explanation/verifier consensus (log the override).
    - Disagree with each other → discard the question.
    - Explanation-derived returns -1/None (ambiguous or empty) → **discard** (closes a silent-fallback vulnerability caught in code review).
  - Purged the current MCQ pool (306 docs) + stats (36 docs) so new attempts pull from the fixed pipeline. Historical `oa_attempts` are not migrated — old attempts may still show the old bug on review, but every fresh attempt from now on uses the corrected verifier.
  - **Testing (testing_agent_v3_fork iterations 3 + 4):** 8/8 pytest cases passed both runs. Pool grew 34 → 72 verified docs across 10 buckets during the 4-min re-verify window (stricter gate did not starve). Zero regressions on the "fresh Sonnet re-picks from stored explanation" consistency check for served MCQs and `/review` answer keys.

- **Feb 13, 2026 (6)** — Pricing/entitlements structure rebuild.
  - New `backend/entitlements.py` module — single source of truth for plan caps, credit balance, and company-selection enforcement. `PLAN_LIMITS`, `can_start_run(user)` (returns source: plan/credit/bypass), `assert_company_allowed`, `maybe_reset_period` (30-day rollover for Basic/Pro), `plan_expired`, `build_state` (dashboard snapshot).
  - **Plans (exact per spec):** Free ₹0 (3 runs contest / 1 OA-only after Jul 21, 2026, 1 co); Basic ₹399/mo (10 runs monthly reset, 4 co swappable); Pro ₹799/mo (20 runs, 6 co, "Most Picked"); MAX ₹999 one-time (25 runs 90-day, all companies, PDF export + multi-resume); SuperMAX ₹1,399 one-time (35 runs 180-day, "Best Value").
  - **Credit packs:** ₹49/1 · ₹199/5 · ₹349/10. Never expire, granted only via `POST /api/payments/verify` after signature check.
  - **Enforcement:** `/api/oa/start` runs the maybe_reset → company_cap check → run gate (plan → credits fallback) → deducts run from correct source (`charged_source` recorded on attempt). Resume of in-progress attempts never blocked. Founder emails bypass all.
  - **New endpoints:** `POST /api/user/company-selection` (swap Free/Basic/Pro slots), unified `POST /api/payments/order` (accepts `plan_id` OR `credit_pack_id`), extended `/api/payments/verify` to set `plan_expires_at` from validity_days and `$inc credits` for credit packs.
  - **`/auth/me`** now returns full `entitlements` block: runs_remaining_on_plan, credits, company_cap, company_selections, plan_expires_at, contest_window_active, free_is_oa_only, extras.
  - **Interview** endpoint returns 402 with `code: interview_locked_free_tier` when `free_is_oa_only(user)` is true (post-contest-window).
  - **Frontend:** rewritten Pricing page (all 5 plans + credit pack section) with correct copy, tags, and mock/real Razorpay flow reused across both. Dashboard shows **three separate chips**: Plan (with expiry date), Plan runs left (N/limit), Credits (never expire, "buy more →" link).
  - Verified via curl e2e: fresh Free signup → 3 runs allowed (contest boost), 402 `company_cap_reached` on 2nd company, swap endpoint works, 402 `limit_reached_no_credits` on 4th run, granting 2 credits allows 4th run with `charged_source: "credit"` and decrements to 1.

- **Feb 13, 2026 (5)** — Added 15th company: **"Core Assessment (Default)"**.
  - **Section 1** — new `type: topic_mcq` compound section. 7 topics (Aptitude, Verbal, OOPS, DBMS, OS, CN, Computer Architecture), 1 verified MCQ per topic, generated in parallel. Pool worker fans out into 7 per-topic buckets (`core-aptitude` … `core-architecture`) with the same generate→verify pipeline (Haiku gen, Sonnet 4.5 verify).
  - **Section 2** — Behavioral (5 MCQs, unscored, `weight: 0.0`).
  - **Section 3** — Coding, 3 problems, all `difficulty_target: "medium"` pulled from `problem_bank.py` (bank has 10 Medium — plenty of rotation depth). Extended `sample_problems` with a `"medium"` target.
  - **Difficulty**: new `medium_hard` label in `_difficulty_override` — 75% Medium / 15% Hard / 10% Easy. Applied to the MCQ section.
  - **Scoring**: extended `/oa/{attempt_id}/review` composite to use **per-section weights** (MCQ 40% + Coding 60% for this track). Old equal-weight behavior preserved when no section defines a weight. Weakest-section calc also weight-aware.
  - **Interview**: added `interview_difficulty: "medium"` on the company; `interview_plan_prompt` now accepts a hint and phrases the 2 DSA prompts as solid Medium (not warm-up level) when the hint is `medium`/`medium_hard`.
  - **UI**: `CompanyCard` shows a mint "general practice" chip when `company.generic === true`; `CompanyDetail` header shows "general-purpose practice · not a specific company's real OA" chip instead of the coral "unverified pattern" warning.
  - Verified end-to-end via curl: fresh OA start → 3 medium DSA problems from bank (Longest Palindromic, Container With Most Water, Number of Islands) + 5 behavioral MCQs + 7 topic-covered verified MCQs (Aptitude, Verbal, OOPS, DBMS, OS, CN, Architecture, all Medium). Full section-gen completes in ~60s cold (parallel topic fanout).

- **Feb 13, 2026 (4)** — Personal review deck.
  - New Mongo collection `review_deck` with unique index on (user_id, source_attempt_id, section_key, question_id) to make add-to-deck idempotent.
  - Backend endpoints: `POST /api/deck/add` (either specific `question_ids: [{section_key, question_id}]` or auto-add every wrong/skipped MCQ from an attempt), `GET /api/deck?unmastered=0|1`, `POST /api/deck/{card_id}/attempt` (records answer, computes mastery — 2 consecutive correct = mastered), `DELETE /api/deck/{card_id}`.
  - Frontend: `OAReview.jsx` now shows a headline "Save all N wrong to review deck" CTA + inline "Save to review deck" bookmark button on every wrong/skipped question. New `/deck` page (`ReviewDeck.jsx`) shows one card at a time with **option order shuffled** (deterministic per-card seed) so users can't just memorize position. Two consecutive correct = mastered, mastered cards drop out of the "Unmastered" filter. Header nav includes a "Review deck" link.
  - Verified end-to-end via curl: added 21 cards from a completed TCS NQT attempt, submitted wrong (streak reset), submitted correct twice (`mastered=true`), unmastered filter correctly drops the mastered card (20 remain).

- **Feb 13, 2026 (3)** — Added post-OA answer key.
  - Backend `/api/oa/{attempt_id}/review` now returns an `answer_key` array with per-section `questions[]` containing `prompt`, `options`, `correct_index`, `user_index`, `is_correct`, `answered`, `explanation`, `difficulty`. Only MCQ-style section types (mcq/pseudocode/comm/game) are included — coding + essay don't have a single canonical answer.
  - Frontend `OAReview.jsx` renders a collapsible "Answer key" block per MCQ section. Card header shows `✓ N correct · ✗ N wrong · – N skipped · N total`. Expanded rows show prompt, all 4 options (correct = mint highlight, user's wrong pick = coral highlight, user's correct pick = "✓ you"), plus the "Why" explanation.
  - Verified: TCS NQT attempt renders 4 sections × 8-10 MCQs each, correct/wrong badges + explanations all visible.

- **Feb 13, 2026 (2)** — MCQ pre-generation + verification pool.
  - Long-running asyncio worker (`_mcq_pool_worker`) launched on FastAPI startup; iterates every pool-eligible `(company, section_key)` and tops it up to buffer=10 verified questions.
  - Generation: Claude Haiku 4.5 (batches of 3). Verification: Claude Sonnet 4.5, shown ONLY prompt + options (no claimed answer) — the trust gate.
  - Retry ≤2 times on disagreement; never persist unverified questions. Stats tracked in `mcq_pool_stats` collection; disagreement rate emitted to stdout every 20 verifications per (company, section).
  - Live serve path: `_generate_section_questions` for MCQ now atomic-pops from `mcq_pool` (findOneAndDelete). Falls back to live-generate + single-pass verify only if pool is empty — user is never blocked.
  - Scope: `verbal`, `reasoning`, `numerical`, `aptitude`, `cs-fundamentals`, `technical`, `logical`, `quant`, `analytical`, `english`, `puzzles`, `advanced` across all companies. Untouched: coding (uses `problem_bank.py`), essay, comm, cognitive_game, pseudocode, game, pen-paper, Automata Fix.
  - Founder-only readout: `GET /api/admin/mcq-stats` — buffer target, generator/verifier models, per-section pool counts, per-section verification stats + disagreement rate %.
  - Verified working: after 2 min runtime, TCS NQT/verbal at 4/10, 50% first-try disagreement rate (2 needed retry, all 4 eventually agreed).

- **Feb 13, 2026 (1)** — Fixed Interview-round React crash "Objects are not valid as a React child (found: object with keys {type, loc, msg, input, url})". Root cause: FastAPI 422 responses return `detail: [{type,loc,msg,input,url}]` and this array was being passed straight to `toast.error(...)` in 12+ places. Added a global axios response interceptor in `frontend/src/api.js` that normalizes Pydantic validation error arrays to a readable string. Also hardened `/interview/start` to guarantee every question has string `id` + string `prompt` (defends against LLM returning object prompts), tightened `interview_plan_prompt` to require string prompts, and added defensive `asText()` rendering in `Interview.jsx`.

## Changelog (older)

## What's Implemented (Jan 13, 2026)
- All 14 companies with real section structures in `backend/companies.py`.
- End-to-end AI-generated OA (MCQ, pseudocode, comm, game, essay, coding) with grading (structured JSON via Haiku).
- **Multi-language live code runner (Python, JavaScript, C++, Java)** via `backend/code_runner.py` — real subprocess execution with per-test 5s timeout.
- Auth: signup/login/logout (bcrypt+JWT) + Emergent Google OAuth callback.
- **Password reset + email verification (dev-mode)** — single-use tokens with 30-min expiry, dev links echoed in the JSON response and printed to backend logs. Ready to swap in real email transport later.
- **Hand-tuned company mechanics:**
  - Accenture — cognitive_game section with per-question 15s timer + 4 game styles (pattern/sequence/spatial/speed_math)
  - Zoho — pen-paper coding mode (plain textarea, no autocomplete, no run button)
  - Tech Mahindra — Automata Fix (buggy code pre-filled in editor; candidate must repair it)
- Dashboard, Company Detail, OA Runner (per-type renderers + timer), OA Review, Interview chat, Final Report.
- Pricing page with Razorpay checkout script + mock-mode fallback when RAZORPAY keys are placeholders.

## Known Gaps / Deferred (P1)
- **Razorpay live keys not provided** → all checkouts run in MOCK mode (auto-verify, still marks plan as paid in DB).
- **Real email transport not wired** — swap `logger.info(...)` for `resend.emails.send(...)` in `send_verification` / `forgot_password` when you have keys.
- `server.py` growing (~1170 lines) — split into routers when convenient.
- `code_runner.py` has NO sandbox — safe for MVP dev, needs seccomp/firejail before prod.
- No section-level negative marking UI badge (only Tech Mahindra sections have `negative: true` but UI doesn't warn).
- Voice input / TTS intentionally removed for MVP (text-only interview).

## Backlog
- P1: Real Razorpay keys, Groq Whisper voice input, per-company hand-tuned mechanics (Accenture cognitive minigames, Zoho pen-paper, Tech Mahindra Automata Fix code-repair mode).
- P2: Batch/college mode, leaderboards, streaks, referral loop.

## Auth / Credentials
See `/app/memory/test_credentials.md`.
