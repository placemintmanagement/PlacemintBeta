# -*- coding: utf-8 -*-
"""TCS Technical-round coding-discussion bank.

Deliberately LIGHTER than Capgemini's Spark/Dave/Commit DSA stages (OUR
ESTIMATE / product decision, per the task brief): the candidate DISCUSSES
their approach in words -- no code execution, no required_approach/
edge_cases/accepted_complexities rubric, no hint ladder, no pushback. Graded
the same way every other TCS Technical-round question is (key_points,
evidence-quote defended), just with points aimed at approach/reasoning
instead of fundamentals recall.

# SEED CONTENT: a small, hand-written STARTING set (3 short classic
problems), not production-complete. Production should grow this to at
least 8-10 items so repeat attempts see real variety.

Shape: {id, topic, difficulty, text, key_points} -- see banks/_kp.py.
"""
from typing import Any, Dict, List

from ._kp import kp

CODING_DISCUSSION_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-code-1", "topic": "coding_discussion", "difficulty": "ninja",
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
        "id": "tcs-code-2", "topic": "coding_discussion", "difficulty": "digital",
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
        "id": "tcs-code-3", "topic": "coding_discussion", "difficulty": "prime",
        "text": (
            "Given a large sorted array, how would you find whether a specific value exists in it, and "
            "why would you prefer that approach over scanning the array from the start? What would "
            "change about your approach if the array were NOT sorted?"
        ),
        "key_points": [
            kp("describes binary search on the sorted array, repeatedly halving the search range",
               "names binary search specifically, not just 'search efficiently'"),
            kp("explains why binary search beats a linear scan on a sorted array (O(log n) vs O(n))",
               "gives a reason tied to the sortedness of the data, not a vague 'it's faster'"),
            kp("correctly states that binary search no longer applies if the array is unsorted, and "
               "names a fallback (e.g. linear scan, or sorting first)",
               "recognizes sortedness as the precondition the whole approach depends on"),
        ],
    },
]
