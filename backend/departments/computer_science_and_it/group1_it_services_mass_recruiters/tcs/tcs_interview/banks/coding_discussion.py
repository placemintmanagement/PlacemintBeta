# -*- coding: utf-8 -*-
"""TCS coding-discussion phase bank.

Deliberately LIGHTER than Capgemini's Spark/Dave/Commit DSA stages (OUR
ESTIMATE / product decision, per the task brief): the candidate DISCUSSES
their approach in words -- no code execution, no required_approach/
edge_cases/accepted_complexities rubric, no hint ladder, no pushback. Graded
the same way every other TCS question is (key_points, evidence-quote
defended), just with points aimed at approach/reasoning instead of
fundamentals recall.

USER-STATED: coding discussion is Easy for Ninja, Medium for Digital and
Prime -- never Hard (TCS does not use Hard). `difficulty` below uses
"easy"/"medium" (NOT the ninja/digital/prime tier-rank scale every other
Core-CS bank in this package uses) because this phase's draw
(core.select_coding_questions) filters directly on that easy/medium label,
per tier, rather than the tier-rank fallback the Core-CS banks use. Prime
differs from Digital by deeper FOLLOW-UP framing on the same Medium
difficulty, never a harder problem -- see tcs-code-3's extra follow-up
depth below.

`tier_tags` (new, time-filling adaptive flow -- a prior audit confirmed
Digital and Prime previously drew from the IDENTICAL 3-Medium-item pool
with EQUAL odds, so "Prime gets deeper follow-ups" was not actually true
as coded): tcs-code-3, Prime's own deeper-follow-up item, is now
tier_tags=["prime"] ONLY -- it can never be drawn for Digital. tcs-code-2
is tier_tags=["digital"] only. tcs-code-4 is tagged for BOTH, since with
only 3 Medium items total, giving each tier a fully disjoint 1-item pool
would leave a tier with literally nothing to draw a 2nd question from;
tcs-code-4 is the one item both tiers still share.

# SEED CONTENT: a small, hand-written STARTING set (4 short classic
problems), not production-complete. Production should grow this to at
least 8-10 items so repeat attempts see real variety. KNOWN SHORTFALL
(confirmed numerically, see tests/test_tcs_interview.py's cost/coverage
checks and the Item-2 task report): with tier_tags now splitting the pool,
Digital's own tagged pool is only 2 items (tcs-code-2, tcs-code-4) and
Prime's is only 2 items (tcs-code-3, tcs-code-4) -- each tier needs at
least 4-6 of its own tier-tagged Medium items (not 2) for a comfortable
non-repeating pool across retakes at the new, longer-running coding-phase
question count (up to max_questions=4 top-level questions per sitting,
see core.TCS_PHASE_BUDGETS). This file's tier-filtering is implemented and
kept correct regardless (core.select_coding_questions never silently
falls back to sharing Digital's and Prime's pools) -- the fix for the
thinness itself is a content-authoring task, not a code task.

Shape: {id, topic, difficulty ("easy"|"medium"), text, key_points,
tier_tags} -- see banks/_kp.py.
"""
from typing import Any, Dict, List

from ._kp import kp

CODING_DISCUSSION_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-code-1", "topic": "coding_discussion", "difficulty": "easy", "tier_tags": ["ninja"],
        "text": (
            "Suppose you need to check whether a given string reads the same forwards and backwards "
            "(a palindrome). In words, how would you approach this -- what is your plan, and roughly "
            "how efficient is it?"
        ),
        "key_points": [
            kp("describes a concrete, correct plan (e.g. compare characters from both ends moving inward, "
               "or reverse the string and compare)",
               "gives a specific algorithmic approach, not just 'check if it's a palindrome'"),
            kp("gives a reasonable sense of efficiency (e.g. that it's a single linear pass, or names "
               "O(n) informally)",
               "shows some awareness of how much work the approach does relative to input size"),
        ],
    },
    {
        "id": "tcs-code-2", "topic": "coding_discussion", "difficulty": "medium", "tier_tags": ["digital"],
        "text": (
            "You're given an array of integers and need to find if there are two numbers in it that add "
            "up to a given target. Walk me through how you'd solve this efficiently -- what would a "
            "naive approach look like, and how would you improve on it?"
        ),
        "key_points": [
            kp("names the naive approach (checking every pair, roughly O(n^2))",
               "describes a brute-force approach as a starting point"),
            kp("describes the improvement using a hash set/map to look up the needed complement in one pass",
               "explains an O(n) approach using extra space to track seen values"),
        ],
    },
    {
        # Prime's deeper-follow-up framing (same Medium difficulty as tcs-code-2/4,
        # USER-STATED: Prime never gets a Hard problem -- it gets more follow-up depth).
        "id": "tcs-code-3", "topic": "coding_discussion", "difficulty": "medium", "tier_tags": ["prime"],
        "text": (
            "Given a large sorted array, how would you find whether a specific value exists in it, and "
            "why would you prefer that approach over scanning the array from the start? What would "
            "change about your approach if the array were NOT sorted, and what's the actual complexity "
            "cost of that change?"
        ),
        "key_points": [
            kp("describes binary search on the sorted array, repeatedly halving the search range",
               "names binary search specifically, not just 'search efficiently'"),
            kp("explains why binary search beats a linear scan on a sorted array (O(log n) vs O(n))",
               "gives a reason tied to the sortedness of the data, not a vague 'it's faster'"),
            kp("correctly states that binary search no longer applies if the array is unsorted, and "
               "names a fallback (e.g. linear scan, or sorting first) with its complexity cost",
               "recognizes sortedness as the precondition the whole approach depends on, and quantifies "
               "the fallback's cost (e.g. O(n) linear scan, or O(n log n) to sort first)"),
        ],
    },
    {
        "id": "tcs-code-4", "topic": "coding_discussion", "difficulty": "medium",
        "tier_tags": ["digital", "prime"],
        "text": (
            "You need to check whether two strings are anagrams of each other (same letters, same "
            "counts, different order). How would you approach this, and how efficient is your approach?"
        ),
        "key_points": [
            kp("describes a concrete, correct approach, e.g. sorting both strings and comparing, or "
               "counting character frequencies and comparing the counts",
               "names a specific algorithmic approach, not just 'compare the letters'"),
            kp("gives a reasonable efficiency estimate for the chosen approach (e.g. O(n log n) for "
               "sorting, or O(n) for a frequency-count approach)",
               "shows awareness of the approach's time complexity"),
        ],
    },
]
