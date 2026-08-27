"""All 14 supported company OA structures.

Each company has a real, researched structure (or a clearly-marked generic fallback).
Sections describe the sequence, timing, and question mix. The OA engine uses this
metadata to generate AI-driven questions and enforce section timing + cutoffs.
"""
from typing import List, Dict, Any

# Question type primitives:
#   mcq                  -> single-correct multiple choice
#   coding               -> full LeetCode-style problem with hidden test cases
#   essay                -> written long-form answer (150-400 words)
#   pseudocode           -> pseudocode / trace-the-output MCQ
#   comm                 -> communication assessment MCQ (grammar / comprehension)
#
# The old per-company gamified-round types (cognitive_game/game,
# capgemini_challenges, cognizant_games, accenture_games) were deleted
# entirely (2026-08) in favor of a registry-driven "gamified_round" system --
# game_types.py (code registry) + gamified_round_config/puzzle_bank/
# game_session (MongoDB). Capgemini, Cognizant, Accenture, and IBM each have
# a "gamified_round" section below (type: "gamified_round"), currently
# serving the one registered game type, deductive_grid.

COMPANIES: List[Dict[str, Any]] = [
    {
        "id": "tcs-nqt",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "TCS NQT",
        "tagline": "Foundation (Ninja) \u2192 Advanced Quant+Reasoning (Digital) \u2192 Advanced Coding (Prime)",
        "logo": "SiTcs",
        "verified": True,
        "time_minutes": 191,
        # Rebuilt 2026-07-21 per newly confirmed 2026 TCS iON research, replacing
        # the earlier estimated structure entirely. No email-writing section --
        # none existed in the prior structure either, nothing removed.
        # No negative marking anywhere below -- confirmed absent, same as before.
        #
        # Exam-behavior requirements (real TCS iON UX, NOT built today -- flagged
        # for the frontend team to eventually match): section switching disabled,
        # sub-section switching disabled, browser tab-switch ends the exam
        # immediately, candidates CAN revisit already-answered questions within
        # the current section. None of this is enforced by this schema yet.
        #
        # "Ninja/Digital/Prime tiers" is a DESCRIPTIVE label only, same as before
        # this change -- server.py has no actual per-tier gating logic today, so
        # there's nothing to "re-verify" beyond keeping the label accurate.
        "scoring_mode": "sectional",
        "chips": [
            "Foundation: 3 mandatory sections (Ninja)",
            "Advanced R1: combined Quant+Reasoning pool (Digital)",
            "Advanced R2: 3 coding problems (Prime)",
        ],
        "sections": [
            # --- Part A: Foundation (76 min, 65 Qs, mandatory for Ninja) ---
            {"key": "numerical", "name": "Numerical Ability", "type": "mcq", "count": 20, "minutes": 25, "cutoff": 0.5},
            {"key": "verbal", "name": "Verbal Ability", "type": "mcq", "count": 25, "minutes": 26, "cutoff": 0.5},
            {"key": "reasoning", "name": "Reasoning Ability", "type": "mcq", "count": 20, "minutes": 25, "cutoff": 0.5},
            # --- Part B: Advanced (115 min, mandatory for Digital/Prime) ---
            {
                "key": "advanced", "name": "Advanced Quantitative + Reasoning Ability",
                "type": "mcq", "count": 15, "minutes": 25, "cutoff": 0.5,
                # Source gives a SHARED 14-16 questions combined (not each) --
                # picked 15 (midpoint), split via extra_topics below, confirmed
                # 2026-07-21.
                "extra_topics": [
                    # key must be a canonical topic key (mcq_static_bank.CANONICAL_TOPICS),
                    # not a raw section-key alias like "quant" -- extra_topics are checked
                    # directly against CANONICAL_TOPICS (server.py's _generate_extra_topics),
                    # they don't go through SECTION_KEY_TO_TOPIC. "quant" would silently get
                    # 0% static-bank draw and hit a never-populated "core-quant" pool key.
                    {"key": "aptitude", "name": "Advanced Quantitative Ability", "count": 8},
                    {"key": "reasoning", "name": "Advanced Reasoning Ability", "count": 7},
                ],
            },
            # 3 questions per explicit user override (2026-07-21) of the source's
            # internal table discrepancy (which suggested 2) -- going with 3.
            {"key": "coding", "name": "Advanced Coding", "type": "coding", "count": 3, "minutes": 90, "cutoff": 0.5},
        ],
    },
    {
        "id": "infosys",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "Infosys",
        "tagline": "Verbal \u2192 Aptitude \u2192 Pseudocode \u2192 Puzzles \u2192 Essay",
        "logo": "SiInfosys",
        "verified": True,
        "time_minutes": 100,
        "scoring_mode": "sectional",
        "chips": ["Pseudocode highest cutoff", "Written Essay", "Puzzles round"],
        "sections": [
            {"key": "verbal", "name": "Verbal Ability", "type": "mcq", "count": 6, "minutes": 10, "cutoff": 0.5},
            {
                "key": "aptitude", "name": "Reasoning + Aptitude", "type": "mcq", "count": 8, "minutes": 20, "cutoff": 0.5,
                # No separate Logical Reasoning section anywhere in Infosys's
                # structure (confirmed 2026-08-18 audit) despite this section's
                # own name already promising "Reasoning + Aptitude" -- it was
                # previously drawing 100% from the aptitude topic pool. Blended
                # in per the new cross-company reasoning-coverage rule.
                "extra_topics": [
                    {"key": "aptitude", "name": "Aptitude", "count": 2},
                    {"key": "reasoning", "name": "Reasoning", "count": 6},
                ],
            },
            {"key": "pseudocode", "name": "Pseudocode (highest cutoff)", "type": "pseudocode", "count": 6, "minutes": 15, "cutoff": 0.65},
            {
                "key": "puzzles", "name": "Puzzles", "type": "mcq", "count": 4, "minutes": 10, "cutoff": 0.5,
                # Previously fully live -- "puzzles" isn't in SECTION_KEY_TO_TOPIC
                # (it means logic/text puzzles here, not an aptitude/reasoning
                # alias), so it fell through to 100% live generation. Now
                # covered by the dedicated puzzles static-bank topic
                # (mcq_static_bank.CANONICAL_TOPICS) via extra_topics, same
                # mechanism as the cs-fundamentals fix.
                "extra_topics": [
                    {"key": "puzzles", "name": "Puzzles", "count": 4},
                ],
            },
            {"key": "essay", "name": "Written Essay", "type": "essay", "count": 1, "minutes": 20, "cutoff": 0.5},
        ],
    },
    {
        "id": "wipro",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "Wipro Elite NTH",
        "tagline": "Aptitude \u2192 Coding \u2192 Written Communication",
        "logo": "SiWipro",
        "verified": True,
        "time_minutes": 124,
        "scoring_mode": "sectional",
        "chips": ["Aptitude: Quant + Logical + Verbal", "2 coding problems (easy-med + hard)", "Written comm ~400 words"],
        "sections": [
            {
                "key": "aptitude", "name": "Aptitude Test (Quant + Logical + Verbal)",
                "type": "mcq", "count": 45, "minutes": 44, "cutoff": 0.5,
                # "key" added to each group (2026-07-22) so this blended section can
                # participate in the static-bank split like every other pooled
                # section -- see _generate_topic_mix in server.py. Previously these
                # groups had no canonical key at all, which is exactly why this
                # section always bypassed the static bank 100%.
                "topic_groups": [
                    {"key": "aptitude", "name": "Quantitative Aptitude", "topics": ["Time & Work", "Time/Speed/Distance", "Percentages", "Profit & Loss", "Geometry", "Probability"]},
                    {"key": "reasoning", "name": "Logical Reasoning", "topics": ["Syllogisms", "Coding-Decoding", "Blood Relations", "Data Sufficiency", "Seating Arrangements"]},
                    {"key": "verbal", "name": "Verbal Ability", "topics": ["Reading Comprehension", "Synonyms/Antonyms", "Error Identification", "Sentence Correction"]},
                ],
            },
            {
                "key": "coding", "name": "Coding", "type": "coding", "count": 2, "minutes": 60, "cutoff": 0.5,
                # Problem 1 easy-medium, Problem 2 "medium-advanced" -- no such
                # tier exists in problem_bank.py (only Easy/Medium/Hard), so
                # "hard" (all Hard, tops up with Medium) is the closest fit.
                "difficulty_targets": ["easy_medium", "hard"],
            },
            {
                "key": "essay", "name": "Written Communication (auto-evaluated)",
                "type": "essay", "count": 1, "minutes": 20, "cutoff": 0.6, "target_words": 400,
                # cutoff/gate MECHANISM unchanged (kept per 2026-07-20 confirmation)
                # -- only the label softened away from "(elimination gate)" since
                # new research frames this as "evaluated automatically", not an
                # explicit gate. Functionally identical either way: cutoff +
                # scoring_mode: sectional never blocks mid-attempt progression,
                # only flips the final verdict if failed (see oa_review).
            },
        ],
    },
    {
        "id": "cognizant",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "Cognizant GenC",
        "tagline": "Communication gate \u2192 Quant + Gamified \u2192 Skill Cluster (Coding/SQL/Domain)",
        "logo": "SiCognizant",
        "verified": True,
        "time_minutes": 164,
        "scoring_mode": "sectional",
        "cluster_options": ["Java", "Python"],
        "chips": ["Communication gate reflects in final verdict, doesn't block", "Pick Java or Python cluster"],
        "sections": [
            # Round 1: Communication Assessment (60 min total). Each section
            # carries its own cutoff: 0.5 \u2014 sectional scoring means failing any
            # one only flips the final verdict to not_ready (oa_review's
            # any_failed check); it never stops the candidate mid-run since
            # submit_section always advances current_section_index regardless
            # of pass/fail. Logical Reasoning (present in the original 2026
            # research) is deliberately dropped, not relocated \u2014 confirmed
            # 2026-07-19.
            {"key": "grammar", "name": "R1: Grammar", "type": "grammar", "count": 34, "minutes": 25, "cutoff": 0.5},
            {"key": "comprehension", "name": "R1: Comprehension", "type": "comprehension", "count": 16, "minutes": 15, "cutoff": 0.5},
            {"key": "speaking", "name": "R1: Speaking", "type": "speaking", "count": 1, "minutes": 5, "cutoff": 0.5},
            {"key": "reading_listening", "name": "R1: Reading & Listening (repeat statements)", "type": "reading_listening", "count": 5, "minutes": 15, "cutoff": 0.5},
            # Round 2: Quant + Gaming (Logical Reasoning dropped, see above).
            {
                "key": "quant", "name": "R2: Quantitative Aptitude", "type": "mcq", "count": 25, "minutes": 35, "cutoff": 0.5,
                # Logical Reasoning was dropped entirely from Cognizant's
                # structure (see the comment above, 2026-07-19) -- audited
                # 2026-08-18 and confirmed no reasoning-mapped section exists
                # anywhere else in this company's structure either. Per the
                # cross-company reasoning-coverage rule, blended into THIS
                # section rather than restoring a dedicated one (explicit
                # user decision, not a relocation of the dropped section).
                "extra_topics": [
                    {"key": "aptitude", "name": "Quantitative Aptitude", "count": 19},
                    {"key": "reasoning", "name": "Reasoning", "count": 6},
                ],
            },
            # Gamified round (R2) — registry-driven (see game_types.py /
            # gamified_round.py), replaces the deleted cognizant_games.py.
            # Runs all 5 registered game types every session (deductive_grid,
            # switch_challenge, grid_challenge, inductive_challenge,
            # motion_challenge); minutes below is the section-level backstop,
            # sized (2026-08-18) for the realistic 5-type total (~11:19 raw,
            # see gamified_round.py's module docstring for the full breakdown).
            {"key": "gamified", "name": "R2: Gamified Round", "type": "gamified_round", "count": 5, "minutes": 14, "cutoff": 0.5},
            # Round 3: Skill Cluster \u2014 candidate picks Java or Python at start
            # via cluster_options above (C# dropped: code_runner.py has no C#
            # execution path). Coding stays language-agnostic (candidate can
            # still pick their submission language in the coding UI); SQL and
            # Domain are cluster-agnostic MCQ sections.
            {"key": "coding", "name": "R3: Coding", "type": "coding", "count": 2, "minutes": 30, "cutoff": 0.5, "difficulty_target": "easy_medium"},
            {"key": "sql", "name": "R3: SQL (multi-table joins & schemas)", "type": "mcq", "count": 2, "minutes": 10, "cutoff": 0.5},
            {"key": "domain", "name": "R3: Domain (Cloud Fundamentals)", "type": "mcq", "count": 8, "minutes": 15, "cutoff": 0.5},
        ],
    },
    {
        "id": "accenture",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "Accenture",
        "tagline": "5 sections \u2013 Behavioral \u2192 Cognitive \u2192 Tech MCQs \u2192 Coding \u2192 Comm",
        "logo": "SiAccenture",
        "verified": True,
        "time_minutes": 164,
        "scoring_mode": "composite",
        "chips": ["5 sections", "Gamified cognitive", "Stack-specific coding"],
        "sections": [
            {"key": "behavioral", "name": "Behavioral (unscored)", "type": "mcq", "count": 5, "minutes": 15, "cutoff": 0.0, "weight": 0.0},  # was missing weight — silently counted at full weight despite the "(unscored)" label; now matches Core Assessment's correct pattern
            # Gamified Cognitive section — registry-driven (see game_types.py /
            # gamified_round.py), replaces the deleted accenture_games.py.
            # Runs all 5 registered game types every session; minutes below
            # sized (2026-08-18) for the realistic 5-type total (~11:19 raw).
            {"key": "cognitive", "name": "Gamified Cognitive", "type": "gamified_round", "count": 5, "minutes": 14, "cutoff": 0.5},
            {"key": "technical", "name": "Tech MCQs (Pseudocode/MS Office/Cloud/Net/CS)", "type": "mcq", "count": 12, "minutes": 45, "cutoff": 0.5},
            {"key": "coding", "name": "Stack-specific Coding", "type": "coding", "count": 1, "minutes": 45, "cutoff": 0.5},
            # Deliberate deviation from Accenture's real researched (all-MCQ+
            # written) Communication format, added by choice (2026-07-20):
            # ~10 of the 20 items become spoken-response (mic -> Groq Whisper
            # -> essay-pipeline grading, same shared machinery as Cognizant's
            # Speaking section), the other ~10 stay MCQ/written. See
            # server.py's "comm_mixed" branch / _grade_comm_mixed_section.
            {"key": "communication", "name": "Communication (MCQ/Written + Spoken)", "type": "comm_mixed", "count": 20, "minutes": 45, "cutoff": 0.5},
        ],
    },
    {
        "id": "product-general",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "Product Company (Generic)",
        "tagline": "Explicit generic fallback template",
        "logo": "LuBriefcaseBusiness",
        "verified": True,
        "time_minutes": 120,
        "scoring_mode": "composite",
        "chips": ["Generic fallback", "DSA-heavy", "Aptitude + Coding"],
        "sections": [
            {
                "key": "aptitude", "name": "Quant + Reasoning", "type": "mcq", "count": 10, "minutes": 25, "cutoff": 0.5,
                # No separate Reasoning section in this generic fallback
                # template -- blended per the cross-company reasoning-coverage
                # rule (2026-08-18), matching what this section's own name
                # already promised.
                "extra_topics": [
                    {"key": "aptitude", "name": "Quantitative Aptitude", "count": 4},
                    {"key": "reasoning", "name": "Reasoning", "count": 6},
                ],
            },
            {
                "key": "cs-fundamentals", "name": "CS Fundamentals (OS/DBMS/OOPS/CN/Architecture)",
                "type": "mcq", "count": 8, "minutes": 20, "cutoff": 0.5,
                # Was a bare mcq section (100% live, never actually wired to
                # the static bank -- confirmed 2026-08-25 audit: this key
                # isn't in SECTION_KEY_TO_TOPIC, and having no extra_topics
                # meant it never hit the branch that would have mapped it).
                # cs_fundamentals is now formally the 5-topic group (OS,
                # DBMS, OOPS, CN, Architecture), split as evenly as possible.
                "extra_topics": [
                    {"key": "os", "name": "Operating Systems", "count": 2},
                    {"key": "dbms", "name": "DBMS", "count": 2},
                    {"key": "oops", "name": "OOPS", "count": 2},
                    {"key": "cn", "name": "Computer Networks", "count": 1},
                    {"key": "architecture", "name": "Computer Architecture", "count": 1},
                ],
            },
            {"key": "coding", "name": "DSA Coding", "type": "coding", "count": 2, "minutes": 75, "cutoff": 0.5},
        ],
    },
    {
        "id": "microsoft-swe",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "Microsoft SWE",
        "tagline": "Unverified \u2013 uses generic fallback",
        "logo": "SiMicrosoft",
        "verified": False,
        "time_minutes": 120,
        "scoring_mode": "composite",
        "chips": ["Unverified pattern", "Fallback template", "DSA-focused"],
        "sections": [
            {
                "key": "aptitude", "name": "Quant + Reasoning", "type": "mcq", "count": 8, "minutes": 20, "cutoff": 0.5,
                # No separate Reasoning section in this unverified fallback
                # template -- blended per the cross-company reasoning-coverage
                # rule (2026-08-18), matching what this section's own name
                # already promised.
                "extra_topics": [
                    {"key": "aptitude", "name": "Quantitative Aptitude", "count": 2},
                    {"key": "reasoning", "name": "Reasoning", "count": 6},
                ],
            },
            {
                "key": "cs-fundamentals", "name": "CS Fundamentals (OS/DBMS/OOPS/CN/Architecture)",
                "type": "mcq", "count": 10, "minutes": 25, "cutoff": 0.5,
                # Was a bare mcq section (100% live -- see product-general's
                # note above for the same root cause). cs_fundamentals is now
                # formally the 5-topic group, split evenly (10/5=2 each).
                "extra_topics": [
                    {"key": "os", "name": "Operating Systems", "count": 2},
                    {"key": "dbms", "name": "DBMS", "count": 2},
                    {"key": "oops", "name": "OOPS", "count": 2},
                    {"key": "cn", "name": "Computer Networks", "count": 2},
                    {"key": "architecture", "name": "Computer Architecture", "count": 2},
                ],
            },
            {"key": "coding", "name": "DSA Coding (2 problems)", "type": "coding", "count": 2, "minutes": 75, "cutoff": 0.5},
        ],
    },
    {
        "id": "ibm",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "IBM",
        "tagline": "Coding-first, light aptitude gate",
        "logo": "SiIbm",
        "verified": True,
        "time_minutes": 119,
        "scoring_mode": "composite",
        "chips": ["Coding-first", "Light aptitude", "Cognitive round"],
        "sections": [
            # Cognitive section — registry-driven (see game_types.py /
            # gamified_round.py), replaces IBM's old live-LLM "game" type
            # (cognitive_game_prompt, no bespoke module of its own).
            # Runs all 5 registered game types every session; minutes below
            # sized (2026-08-18) for the realistic 5-type total (~11:19 raw).
            {"key": "cognitive", "name": "Cognitive", "type": "gamified_round", "count": 5, "minutes": 14, "cutoff": 0.5},
            {
                "key": "aptitude", "name": "Aptitude (light gate)", "type": "mcq", "count": 6, "minutes": 15, "cutoff": 0.4,
                # No separate Reasoning section -- but this section is only 6
                # questions total, too small for the standard 6-7 reasoning
                # minimum (would consume the whole section or exceed it,
                # leaving no room for genuine aptitude content). Reduced 3+3
                # split confirmed with user 2026-08-18 as this company's
                # deliberate exception to the standard blend count.
                "extra_topics": [
                    {"key": "aptitude", "name": "Quantitative Aptitude", "count": 3},
                    {"key": "reasoning", "name": "Reasoning", "count": 3},
                ],
            },
            {"key": "coding", "name": "Coding (2 problems)", "type": "coding", "count": 2, "minutes": 90, "cutoff": 0.5},
        ],
    },
    {
        "id": "zoho",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "Zoho",
        "tagline": "3 rounds \u2013 Aptitude+Tech MCQs \u2192 5 Programs \u2192 Advanced DSA",
        "logo": "LuCode",
        "verified": True,
        "time_minutes": 340,  # ~5h40m \u2014 matches Zoho's real all-day OA
        "scoring_mode": "composite",
        "chips": ["Pen-paper Round 1", "5 basic programs (E\u2013M)", "Advanced DSA (Hard)"],
        "sections": [
            # Round 1: Written Aptitude + Technical MCQs (pen-paper). 20-25 questions total, 60-90 min.
            {"key": "r1-aptitude", "name": "R1a: Quantitative Aptitude (pen-paper)", "type": "mcq", "count": 12, "minutes": 40, "cutoff": 0.5},
            {"key": "r1-technical", "name": "R1b: Technical MCQs \u2013 predict C/Java output", "type": "pseudocode", "count": 13, "minutes": 45, "cutoff": 0.5},
            # Round 2: Basic Programming. 5 problems, Easy\u2013Medium, 3 hours.
            {"key": "r2-basic-coding", "name": "R2: Basic Programming \u2013 5 problems (Easy\u2013Medium)", "type": "coding", "count": 5, "minutes": 180, "cutoff": 0.7, "difficulty_target": "easy_medium"},
            # Round 3: Advanced DSA. 1-2 hard problems, 60-90 min.
            {"key": "r3-advanced-coding", "name": "R3: Advanced DSA \u2013 recursion/trees/graphs/DP", "type": "coding", "count": 2, "minutes": 75, "cutoff": 0.5, "difficulty_target": "hard"},
        ],
    },
    {
        "id": "capgemini",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "Capgemini",
        "tagline": "Round 1: Tech MCQ+Pseudo \u2192 Essay \u2192 Game \u2192 Behavioral \u00b7 Round 2: Coding",
        "logo": "SiCapgemini",
        "verified": True,
        "time_minutes": 169,
        "scoring_mode": "sectional",
        "chips": ["Round 1: OA (4 sections)", "Round 2: 2 DSA Coding", "Behavioral (unscored)"],
        "sections": [
            # ROUND 1: Online Assessment (4 sections, in order)
            {
                "key": "technical",
                "name": "R1a: Technical MCQs + Pseudocode",
                "type": "pseudocode",
                "count": 40,
                "pseudocode_count": 16,  # untouched pseudocode call's own count \u2014 NOT resized
                                         # by the section's total `count` above (see
                                         # server.py's pseudocode dispatch for how these
                                         # two interact)
                "minutes": 40,
                "cutoff": 0.5,
                "extra_topics": [
                    {"key": "oops", "name": "OOPS", "count": 6},
                    {"key": "dbms", "name": "DBMS", "count": 6},
                    {"key": "os", "name": "Operating Systems", "count": 6},
                    {"key": "cn", "name": "Computer Networks", "count": 6},
                ],
            },
            {"key": "essay", "name": "R1b: Essay Writing", "type": "essay", "count": 1, "minutes": 25, "cutoff": 0.5},
            # R1c: Game Based Cognitive Test — registry-driven (see
            # game_types.py / gamified_round.py), replaces the deleted
            # capgemini_challenges.py.
            # Runs all 5 registered game types every session; minutes below
            # sized (2026-08-18) for the realistic 5-type total (~11:19 raw).
            {"key": "cognitive", "name": "R1c: Game Based Cognitive Test", "type": "gamified_round", "count": 5, "minutes": 14, "cutoff": 0.5},
            # NEW (2026-07-19): never built before, based on newly confirmed research.
            # Unscored, same pattern as Accenture/Core Assessment's Behavioral sections \u2014
            # weight: 0.0 is what actually excludes it from the composite (cutoff alone
            # does not; see Accenture's weight fix for why that distinction matters).
            {"key": "behavioral", "name": "R1d: Behavioral / PowerSkills (unscored)", "type": "mcq", "count": 5, "minutes": 20, "cutoff": 0.0, "weight": 0.0},
            # ROUND 2: Coding Round
            {"key": "coding", "name": "R2: Coding Round (2 DSA Problems)", "type": "coding", "count": 2, "minutes": 60, "cutoff": 0.5},
        ],
    },
    {
        "id": "hcltech",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "HCLTech",
        "tagline": "5-section OA -- 77 questions, 95 minutes (confirmed structure)",
        "logo": "SiHcl",
        "verified": True,
        "time_minutes": 95,
        # Confirmed 2026-07-21: full section-level breakdown below, replacing the
        # prior generic-template structure entirely. Totals independently check
        # out against the earlier aggregate research (77 questions, 95 minutes,
        # 5 sections) -- this is now real, confirmed data, not an estimate.
        #
        # UNRECONCILED: the source separately mentions "4 rounds" without
        # specifying how they map onto these 5 sections. That round-grouping is
        # NOT confirmed -- deliberately not inventing a specific mapping here.
        #
        # scoring_mode chosen deliberately (2026-07-21, confirmed with user):
        # sectional cutoffs, matching TCS/Infosys/Wipro/Capgemini in this
        # codebase. The source data itself doesn't specify scoring mode -- this
        # was a considered choice, not inherited from the old composite default.
        "scoring_mode": "sectional",
        "chips": ["77 questions, 5 sections", "95 minutes total", "Sectional cutoffs"],
        "sections": [
            {"key": "numerical", "name": "Numerical Ability", "type": "mcq", "count": 15, "minutes": 15, "cutoff": 0.5},
            {"key": "verbal", "name": "Verbal Ability", "type": "mcq", "count": 15, "minutes": 15, "cutoff": 0.5},
            {"key": "reasoning", "name": "Logical Reasoning Ability", "type": "mcq", "count": 15, "minutes": 15, "cutoff": 0.5},
            {
                "key": "cs-fundamentals", "name": "Computer Fundamentals (OS/DBMS/OOPS/CN/Architecture)",
                "type": "mcq", "count": 30, "minutes": 30, "cutoff": 0.5,
                # Was a bare mcq section (100% live -- see product-general's
                # note above for the same root cause). cs_fundamentals is now
                # formally the 5-topic group, split evenly (30/5=6 each).
                "extra_topics": [
                    {"key": "os", "name": "Operating Systems", "count": 6},
                    {"key": "dbms", "name": "DBMS", "count": 6},
                    {"key": "oops", "name": "OOPS", "count": 6},
                    {"key": "cn", "name": "Computer Networks", "count": 6},
                    {"key": "architecture", "name": "Computer Architecture", "count": 6},
                ],
            },
            {"key": "coding", "name": "Coding", "type": "coding", "count": 2, "minutes": 20, "cutoff": 0.5},
        ],
    },
    {
        "id": "ltimindtree",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "LTIMindtree",
        "tagline": "7-section, 130 min \u2013 confirmed structure (111 Qs)",
        "logo": "LuLayers",
        "verified": True,
        "time_minutes": 130,
        "scoring_mode": "composite",
        "chips": ["7 sections, 111 Qs", "Spoken English (voice)", "CS Fundamentals (topic-tagged)"],
        "sections": [
            {"key": "english", "name": "English Comprehension", "type": "comprehension", "count": 12, "minutes": 15, "cutoff": 0.5},
            {"key": "logical", "name": "Logical Reasoning", "type": "mcq", "count": 12, "minutes": 15, "cutoff": 0.5},
            {"key": "analytical", "name": "Basic Analytical Ability", "type": "mcq", "count": 10, "minutes": 10, "cutoff": 0.5},
            {"key": "quant", "name": "Quantitative Ability", "type": "mcq", "count": 12, "minutes": 15, "cutoff": 0.5},
            {"key": "programming", "name": "Computer Programming", "type": "pseudocode", "count": 25, "minutes": 35, "cutoff": 0.5},
            {
                "key": "cs-fundamentals", "name": "Computer Science (OS/DBMS/OOPS/CN/Architecture)",
                "type": "mcq", "count": 20, "minutes": 20, "cutoff": 0.5,
                # Normalized 2026-08-25: cs_fundamentals is now formally the
                # 5-topic group (OS/DBMS/OOPS/CN/Architecture) in equal ratio
                # across every company that has this section, not just the
                # DBMS/OOPS/OS subset this company originally shipped with.
                # 20/5=4 each (previously dbms:7, oops:7, os:6, no cn/arch).
                "extra_topics": [
                    {"key": "os", "name": "Operating Systems", "count": 4},
                    {"key": "dbms", "name": "DBMS", "count": 4},
                    {"key": "oops", "name": "OOPS", "count": 4},
                    {"key": "cn", "name": "Computer Networks", "count": 4},
                    {"key": "architecture", "name": "Computer Architecture", "count": 4},
                ],
            },
            {
                # Reverses the earlier text-only conversion for THIS company
                # specifically (2026-07-20) \u2014 Tech Mahindra's separate Written
                # Communication section is untouched. Assesses listening,
                # speaking, and sentence mastery per 2026 research: half the
                # items are listening (repeat-statement, graded by string
                # similarity) half are speaking (open response, essay-pipeline
                # graded via transcript) \u2014 see server.py's "voice_mixed" branch.
                "key": "spoken-english", "name": "Spoken English / Communication",
                "type": "voice_mixed", "count": 20, "minutes": 20, "cutoff": 0.5,
                "listening_count": 10,
            },
        ],
    },
    {
        "id": "tech-mahindra",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "Tech Mahindra",
        "tagline": "4-round OA (170 min) \u2013 elimination gate in R1, voice-based R3",
        "logo": "SiTeamviewer",
        "verified": True,
        "time_minutes": 170,
        # Rebuilt 2026-07-21 per newly confirmed 2026 research, replacing the
        # earlier 3-round estimate entirely. Round 4 (Technical Interview + HR)
        # is NOT a new OA section -- it describes real interview content and
        # maps to the app's existing Phase 3 interview; no OA section for it.
        #
        # scoring_mode: confirmed with user 2026-07-21. Schema only supports one
        # company-wide mode (not per-round), so this follows the same precedent
        # already used for Wipro/Cognizant: when ANY section carries a genuine
        # elimination consequence (Round 1 here), the whole company is marked
        # "sectional" -- sectional never blocks mid-attempt progression, it only
        # flips the final verdict if that one section fails (see oa_review).
        "scoring_mode": "sectional",
        "chips": [
            "R1 is an elimination gate (Aptitude/negative marking)",
            "Automata Fix (code repair) + voice-based Conversational round",
            "Personality Test (72 Qs, unscored)",
        ],
        "sections": [
            # --- Round 1: Online Test (60 min, elimination gate) ---
            # Rekeyed "aptitude" -> "reasoning" (2026-08-18 audit): this
            # section is named "Logical Ability" and was always intended as
            # pure reasoning content, but SECTION_KEY_TO_TOPIC matches by KEY
            # not name -- it had been silently drawing 100% from the
            # APTITUDE topic pool this whole time, a pre-existing miskey bug
            # unrelated to (found while investigating) the cross-company
            # reasoning-blend rule. Tech Mahindra's genuine quant content is
            # the separate "quant"-keyed section below, untouched.
            {"key": "reasoning", "name": "Logical Ability", "type": "mcq", "count": 12, "minutes": 15, "cutoff": 0.5, "negative": True},
            {"key": "quant", "name": "Quantitative Ability", "type": "mcq", "count": 12, "minutes": 15, "cutoff": 0.5, "negative": True},
            {"key": "verbal", "name": "English", "type": "mcq", "count": 12, "minutes": 15, "cutoff": 0.5, "negative": True},
            # Confirmed with user 2026-07-21: negative marking kept on R1/R2
            # MCQ sections despite the new source being silent on it, since the
            # old data explicitly had it and nothing contradicts it -- surfaced
            # to the candidate up front via the chips above (this file's
            # existing pre-OA-disclosure convention), not a new field.
            {"key": "essay", "name": "Essay Writing", "type": "essay", "count": 1, "minutes": 15, "cutoff": 0.5},
            # --- Round 2: Technical Test + Personality (90 min) ---
            {"key": "programming", "name": "Computer Programming", "type": "pseudocode", "count": 12, "minutes": 15, "cutoff": 0.5, "negative": True},
            {
                "key": "cs-fundamentals", "name": "Computer Science (OS/DBMS/OOPS/CN/Architecture)",
                "type": "mcq", "count": 12, "minutes": 15, "cutoff": 0.5, "negative": True,
                # Normalized 2026-08-25: cs_fundamentals is now formally the
                # 5-topic group (OS/DBMS/OOPS/CN/Architecture) in equal ratio
                # across every company that has this section, not just the
                # DBMS/OOPS/OS/CN subset this company originally shipped with.
                # 12/5=2 each + 2 remainder to the first two (os, dbms) --
                # previously an even 3/3/3/3 across just 4 topics, no
                # architecture.
                "extra_topics": [
                    {"key": "os", "name": "Operating Systems", "count": 3},
                    {"key": "dbms", "name": "DBMS", "count": 3},
                    {"key": "oops", "name": "OOPS", "count": 2},
                    {"key": "cn", "name": "Computer Networks", "count": 2},
                    {"key": "architecture", "name": "Computer Architecture", "count": 2},
                ],
            },
            # Automata Fix minutes: confirmed with user 2026-07-21 as 45 (not
            # the previously-stored 60) -- 45 is what the new Round 2 budget
            # (15+15+45+15=90) actually requires; the "unchanged" framing in
            # the source research didn't match what was actually stored here.
            {"key": "coding", "name": "Automata Fix \u2013 repair the broken code", "type": "coding", "count": 2, "minutes": 45, "cutoff": 0.5, "automata_fix": True},
            # Unscored, same weight:0.0 pattern as Accenture's Behavioral and
            # Capgemini's PowerSkills -- 72 Qs / 15 min is a forced-choice
            # psychometric instrument, not a graded knowledge test.
            {"key": "personality", "name": "Personality Test (unscored)", "type": "mcq", "count": 72, "minutes": 15, "cutoff": 0.0, "weight": 0.0},
            # --- Round 3: Conversational Test (20 min) -- voice-based ---
            # Reverses the earlier text-only decision for THIS company
            # specifically (2026-07-21): pronunciation, speaking, grammar,
            # reading per new research. Reuses the same Groq Whisper pipeline
            # and voice_mixed type as LTIMindtree's Spoken English (same
            # count/listening_count ratio -- no per-question count was given in
            # the source, so this mirrors LTIMindtree's established density as
            # the closest confirmed precedent rather than inventing a new one).
            {
                "key": "conversational", "name": "Conversational Test (Voice)",
                "type": "voice_mixed", "count": 20, "minutes": 20, "cutoff": 0.5,
                "listening_count": 10,
            },
        ],
    },
    {
        "id": "deloitte-usi",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "Deloitte USI",
        "tagline": "90 min \u2013 4 sections, heavy CS fundamentals block",
        "logo": "LuBriefcase",
        "verified": True,
        "time_minutes": 90,
        "scoring_mode": "composite",
        "chips": ["4 sections", "30-MCQ CS Fundamentals block", "Networking/Cloud/Security"],
        "sections": [
            {
                "key": "aptitude", "name": "Aptitude", "type": "mcq", "count": 8, "minutes": 20, "cutoff": 0.5,
                # No separate Reasoning section anywhere in Deloitte USI's
                # structure -- blended per the cross-company reasoning-coverage
                # rule (2026-08-18).
                "extra_topics": [
                    {"key": "aptitude", "name": "Aptitude", "count": 2},
                    {"key": "reasoning", "name": "Reasoning", "count": 6},
                ],
            },
            {"key": "verbal", "name": "Verbal", "type": "mcq", "count": 6, "minutes": 15, "cutoff": 0.5},
            {
                "key": "cs-fundamentals", "name": "CS Fundamentals (heavy: OS/DBMS/OOPS/CN/Architecture)",
                "type": "mcq", "count": 12, "minutes": 30, "cutoff": 0.5,
                # Was a bare mcq section (100% live -- see product-general's
                # note above for the same root cause). cs_fundamentals is now
                # formally the 5-topic group, 12/5=2 each + 2 remainder to
                # the first two (os, dbms).
                "extra_topics": [
                    {"key": "os", "name": "Operating Systems", "count": 3},
                    {"key": "dbms", "name": "DBMS", "count": 3},
                    {"key": "oops", "name": "OOPS", "count": 2},
                    {"key": "cn", "name": "Computer Networks", "count": 2},
                    {"key": "architecture", "name": "Computer Architecture", "count": 2},
                ],
            },
            {"key": "coding", "name": "Coding", "type": "coding", "count": 1, "minutes": 25, "cutoff": 0.5},
        ],
    },
    # ---------------------------------------------------------------------
    # Core Assessment (Default) — GENERIC practice track (15th entry).
    # Not modeled on any specific company's real elimination logic.
    # Deliberately harder than easy-tier companies; blended composite
    # scoring with explicit per-section weights.
    # ---------------------------------------------------------------------
    {
        "id": "core-default",
        "department": "cse",
        "group": "Group 1: IT Services & Mass Recruiters",
        "name": "Core Assessment (Default)",
        "tagline": "General-purpose practice — deliberately harder, broad topic coverage",
        "logo": "LuLayers",
        "verified": False,
        "generic": True,  # UI flag → renders the "general fallback" label
        "time_minutes": 109,  # +4 from adding reasoning as an 8th core-fundamentals topic (2026-08-18)
        "scoring_mode": "composite",
        "interview_difficulty": "medium",  # medium-skew DSA in Phase 3
        "chips": ["General practice", "Medium+ difficulty", "MCQ 40% + Coding 60%"],
        "hero_color": "#1F2937",
        "sections": [
            {
                "key": "core-fundamentals",
                "name": "Core Fundamentals (8-topic MCQ)",
                "type": "topic_mcq",
                "count": 8,
                "minutes": 34,  # proportional +4 from 30 (30 * 8/7 ≈ 34.3) -- 2026-08-18
                "cutoff": 0.5,
                "weight": 0.4,
                "difficulty_target": "medium_hard",
                "topics": [
                    {"key": "aptitude",     "name": "Aptitude"},
                    {"key": "verbal",       "name": "Verbal"},
                    {"key": "reasoning",    "name": "Reasoning"},
                    {"key": "oops",         "name": "OOPS"},
                    {"key": "dbms",         "name": "DBMS"},
                    {"key": "os",           "name": "Operating Systems"},
                    {"key": "cn",           "name": "Computer Networks"},
                    {"key": "architecture", "name": "Computer Architecture"},
                ],
            },
            {
                "key": "behavioral",
                "name": "Behavioral (unscored)",
                "type": "mcq",
                "count": 5,
                "minutes": 15,
                "cutoff": 0.0,
                "weight": 0.0,  # explicitly excluded from composite
            },
            {
                "key": "coding",
                "name": "DSA Coding (3 medium)",
                "type": "coding",
                "count": 3,
                "minutes": 60,
                "cutoff": 0.5,
                "weight": 0.6,
                "difficulty_target": "medium",
            },
        ],
    },
]


def get_company(company_id: str) -> Dict[str, Any] | None:
    for c in COMPANIES:
        if c["id"] == company_id:
            return c
    return None


# Landing-page department navigation. Purely a categorization/navigation
# layer over COMPANIES (matched via the "department" field on each company
# dict above) -- not read by any OA/scoring/MCQ logic.
DEPARTMENTS: List[Dict[str, Any]] = [
    {"id": "cse", "name": "Computer Science Engineering", "active": True},
    {"id": "entc", "name": "Electronics and Telecommunication Engineering", "active": False},
    {"id": "electronics", "name": "Electronics Engineering", "active": False},
    {"id": "mechanical", "name": "Mechanical Engineering", "active": False},
    {"id": "civil", "name": "Civil Engineering", "active": False},
]


def get_department(department_id: str) -> Dict[str, Any] | None:
    for d in DEPARTMENTS:
        if d["id"] == department_id:
            return d
    return None
