# -*- coding: utf-8 -*-
"""Tiny shared helper for every TCS interview bank below: a key_points entry
is {statement, alternatives} -- the grading prompt (ai_service.py's
tcs_key_point_flags_prompt) accepts the candidate's own phrasing OR any of
the listed alternatives, never requiring exact wording. Same shape as
Capgemini Dave's own cs.py _kp() helper (dave/cs.py:31-32) -- re-authored
here, not imported, so this package has zero dependency on the Capgemini
interview package (see tcs_interview/core.py's module docstring)."""
from typing import Any, Dict, List


def kp(statement: str, *alternatives: str) -> Dict[str, Any]:
    return {"statement": statement, "alternatives": list(alternatives)}


def by_id(questions: List[Dict[str, Any]], question_id: str):
    return next((q for q in questions if q["id"] == question_id), None)
