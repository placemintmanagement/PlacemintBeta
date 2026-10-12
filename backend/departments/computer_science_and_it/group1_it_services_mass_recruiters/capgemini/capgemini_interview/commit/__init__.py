# -*- coding: utf-8 -*-
"""Capgemini Commit tier (text, 75 minutes, 7.50 LPA) -- public entry point.

Re-exports flow.py (the stage machine, budgets, weights, selection) and the
two question banks (java_bank.py, oops_bank.py) so server.py can do
`from ...capgemini_interview import commit` and use `commit.<name>`, same
import shape as `capgemini_interview.dave_*`. See flow.py's own docstring
for the full design (what's reused read-only from core.py/dave/, what's new
here, and every INTERPOLATED decision).

commit_cs_bank() lives here (not in server.py) so the whole CS-grilling bank
-- Commit's own oops/java plus Dave's SQL bank with Commit's own follow-ups
attached -- is assembled inside this package, the same place its three
source files live. server.py just calls capgemini_commit.commit_cs_bank().
"""
from typing import Any, Dict, List

from .. import core
from .flow import *  # noqa: F401,F403
from .java_bank import JAVA_QUESTIONS  # noqa: F401
from .oops_bank import OOPS_QUESTIONS  # noqa: F401
from .sql_followups import SQL_FOLLOWUPS  # noqa: F401


def commit_cs_bank() -> Dict[str, List[Dict[str, Any]]]:
    """oops/java are Commit's own banks; sql is Dave's SQL bank (core.CS_SQL_
    QUESTIONS) reused read-only (STATED), with Commit's own follow_ups
    attached onto a COPY of each question dict -- dave/cs.py's SQL_QUESTIONS
    has no follow_ups field at all (that bank was authored for Dave, which
    never asks SQL follow-ups), but every Commit CS-grilling question gets
    exactly 2 fixed follow-ups (STATED), including a SQL draw. dave/cs.py
    itself is never modified. Built fresh each call -- these are plain
    module-level lists, cheap to reference."""
    sql_with_followups = [dict(q, follow_ups=SQL_FOLLOWUPS[q["id"]]) for q in core.CS_SQL_QUESTIONS]
    return {"oops": OOPS_QUESTIONS, "java": JAVA_QUESTIONS, "sql": sql_with_followups}
