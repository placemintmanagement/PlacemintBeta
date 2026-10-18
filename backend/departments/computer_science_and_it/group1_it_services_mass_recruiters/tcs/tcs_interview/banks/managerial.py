# -*- coding: utf-8 -*-
"""TCS Managerial-round question banks: situational scenarios (relocation,
pressure, deadlines) and resume-gap explanation prompts.

# SEED CONTENT: small, hand-written STARTING sets -- 4 situational
scenarios and 2 gap-explanation variants. Production should grow the
situational bank to at least 8-10 items (Prime draws up to 2 per sitting,
same variety reasoning as the Technical-round banks) and the gap bank to
3-4 variants. Freshly written for TCS; Dave's HR bank has a loosely
adjacent "situational" category (dave/hr.py's hr-si1/hr-si2/hr-si3) but
those are framed as HR questions, not managerial ones, so they were not
reused verbatim -- see tcs_interview/core.py's module docstring.

Shape: {id, topic, difficulty, text, key_points} -- see banks/_kp.py.
"""
from typing import Any, Dict, List

from ._kp import kp

MANAGERIAL_SITUATIONAL_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-mgr-si-1", "topic": "managerial_situational", "difficulty": "ninja",
        "text": (
            "Suppose TCS asks you to relocate to a different city for your project, with fairly short "
            "notice. How would you think about and respond to that?"
        ),
        "key_points": [
            kp("gives a thoughtful, realistic response rather than a one-word yes/no",
               "explains their actual reasoning, not just a flat answer"),
            kp("shows some practical awareness (e.g. logistics, family, notice period) without being evasive",
               "acknowledges real considerations while still engaging with the question directly"),
        ],
    },
    {
        "id": "tcs-mgr-si-2", "topic": "managerial_situational", "difficulty": "digital",
        "text": (
            "Tell me about a time you were under real pressure to deliver something on a tight deadline. "
            "What did you do, and what was the outcome?"
        ),
        "key_points": [
            kp("describes a specific, concrete situation (not a generic/hypothetical answer)",
               "names an actual deadline, task, or project they personally faced"),
            kp("explains the concrete action(s) they took to manage the pressure/deadline",
               "shows a real strategy, not just 'I worked hard'"),
            kp("states a clear outcome or result of that situation",
               "closes the story with what actually happened"),
        ],
    },
    {
        "id": "tcs-mgr-si-3", "topic": "managerial_situational", "difficulty": "digital",
        "text": (
            "If you were given a task with an unclear deadline and no one immediately available to clarify "
            "it, what would you do?"
        ),
        "key_points": [
            kp("gives a concrete first step (e.g. make a reasonable assumption and proceed, document it, "
               "escalate once someone is available) rather than freezing",
               "shows a practical plan of action under ambiguity"),
            kp("shows awareness that communication/follow-up matters once more information is available",
               "mentions checking back in or confirming the assumption later"),
        ],
    },
    {
        "id": "tcs-mgr-si-4", "topic": "managerial_situational", "difficulty": "prime",
        "text": (
            "Describe a time you disagreed with a decision made by someone senior to you on a project. "
            "How did you handle it, and what was the result?"
        ),
        "key_points": [
            kp("describes a specific real disagreement, not a hypothetical",
               "names the actual decision and context"),
            kp("explains how they raised or handled the disagreement professionally (not just complying silently "
               "or escalating badly)",
               "shows a constructive way of voicing disagreement"),
            kp("states what actually happened as a result",
               "closes with a real outcome, including if their view did not prevail"),
        ],
    },
]

GAP_EXPLANATION_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-mgr-gap-1", "topic": "managerial_gap", "difficulty": "ninja",
        "text": (
            "Looking at your resume's timeline, is there anything about gaps between activities, or "
            "transitions between them, that you'd like to explain?"
        ),
        "key_points": [
            kp("gives a direct, specific answer rather than deflecting or ignoring the question",
               "actually addresses the question asked, even if the honest answer is 'there isn't one'"),
            kp("the explanation given is specific and internally consistent, not vague",
               "if a gap/transition is described, it has real, checkable specifics"),
            kp("communicates it calmly and professionally, without being defensive",
               "keeps a professional, non-defensive tone throughout"),
        ],
    },
    {
        "id": "tcs-mgr-gap-2", "topic": "managerial_gap", "difficulty": "digital",
        "text": (
            "Was there any period where you weren't actively studying, working or building something, "
            "based on what's on your resume? If so, walk me through it."
        ),
        "key_points": [
            kp("gives a direct, specific answer rather than deflecting or ignoring the question",
               "actually addresses the question asked, even if the honest answer is 'no, there wasn't'"),
            kp("the explanation given is specific and internally consistent, not vague",
               "if a period is described, it has real, checkable specifics"),
            kp("communicates it calmly and professionally, without being defensive",
               "keeps a professional, non-defensive tone throughout"),
        ],
    },
]
