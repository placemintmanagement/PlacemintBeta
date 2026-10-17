"""Budget/weight-sum invariants for Spark and Dave, mirroring the ones
test_commit_interview.py already has for Commit (test_budgets_sum_to_
seventy_five_minutes, test_weights_sum_to_one, test_cs_topic_weights_sum_to_
one, lines 33-42 there) -- see the design doc's bug #3 ("Test-suite invariant
coverage is inconsistent across the three tiers... Commit is protected
against a future constant-edit mistake that Spark and Dave are not").

This file adds the missing two invariants for EACH of Spark and Dave:
  - its own *_BUDGETS_SECONDS dict sums to exactly its own duration constant
  - its own *_WEIGHTS dict (the report-only scoring weights) sums to 1.0

Both invariants hold today for both tiers (verified below; this is a pure
characterization test, not a fix) -- the inline comments in core.py already
claim this arithmetic by hand (core.py:59-60 "intro + pf + dsa + buffer = 35
min", core.py:96-97 "3+14+6+8+4+10+5+5 = 55 min"), but nothing previously
asserted it. A future refactor that moves these numbers into a shared config
table now has the same guard for Spark and Dave that Commit already had.

CS_TOPIC_WEIGHTS (core.py, used by Dave's cs_fundamentals stage, and reused
unchanged by Commit's cs_grilling stage) is the SAME module-level dict object
test_commit_interview.py's test_cs_topic_weights_sum_to_one already asserts
sums to 1.0 -- so that invariant is already covered for Dave too (it would be
redundant, not a gap, to re-assert the identical object here); it is included
below anyway, imported from Dave's own module rather than through Commit's,
so this file does not depend on the commit package to state an invariant
that is really about Dave's own stage."""
import pytest

from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini import (
    capgemini_interview as ci,
)
from departments.computer_science_and_it.group1_it_services_mass_recruiters.capgemini.capgemini_interview.dave.cs import (
    CS_TOPIC_WEIGHTS,
)


# ---- Spark ------------------------------------------------------------------
def test_spark_budgets_sum_to_thirty_five_minutes():
    assert sum(ci.SPARK_BUDGETS_SECONDS.values()) == 35 * 60


def test_spark_weights_sum_to_one():
    assert sum(ci.SPARK_WEIGHTS.values()) == pytest.approx(1.0)


# ---- Dave ---------------------------------------------------------------------
def test_dave_budgets_sum_to_fifty_five_minutes():
    assert sum(ci.DAVE_BUDGETS_SECONDS.values()) == 55 * 60


def test_dave_weights_sum_to_one():
    assert sum(ci.DAVE_WEIGHTS.values()) == pytest.approx(1.0)


def test_dave_cs_topic_weights_sum_to_one():
    assert sum(CS_TOPIC_WEIGHTS.values()) == pytest.approx(1.0)
