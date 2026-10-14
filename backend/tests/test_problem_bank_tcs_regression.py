"""Regression tests for the TCS-driven problem_bank.py change (adding a new
``difficulty_target == "easy"`` elif branch to sample_problems()).

The diff is purely additive: one new elif branch inserted between the
existing 'medium' and the final 'else' branch, plus two docstring lines.
These tests prove that claim mechanically rather than by inspection alone:

1. For every difficulty_target string actually used by a company in
   companies.py today (None/"easy_medium"/"hard"/"medium" -- "easy" is new
   and TCS-only), sample_problems() run against the CURRENT module produces
   byte-identical output, seed-for-seed, to sample_problems() run against the
   module as it existed at HEAD (i.e. before this session's uncommitted
   "easy" branch was added). This is done by loading HEAD's copy of
   problem_bank.py into a throwaway module via `git show` and diffing its
   sample_problems() against the live one under the same random seed.
2. Capgemini is proven structurally incapable of being affected at all: its
   OA sections never set difficulty_target/difficulty_targets (so none of
   its coding draws route through sample_problems' branching in the first
   place), and its interview-stage DSA problems (Dave/Spark) are static
   copied dicts, not live sample_problems() calls.
"""
import asyncio
import random
import subprocess
import sys
import types
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

# Pinned to the last commit BEFORE this diff landed (2026-10 TCS static-bank
# work), not a floating "HEAD" -- once this diff itself gets committed, HEAD
# moves past the baseline and a bare "HEAD:" lookup would load the NEW code
# as its own "before" snapshot, silently turning every "is new, not a
# modification" assertion false. Update this hash only if a deliberate
# reason exists to re-baseline (e.g. a later, unrelated commit touches the
# same functions again and the new baseline should include it).
BASELINE_COMMIT = "2155881"

# difficulty_target strings actually used, today, by some company's "coding"
# section per companies.py (grepped at write-time: Wipro uses the per-problem
# list ["easy_medium", "hard"]; Zoho uses "easy_medium" for R2 and "hard" for
# R3; the generic fallback company uses "medium"; None is the Capgemini-
# round1-style / IBM-style default blend). "easy" is deliberately excluded --
# it's the new, TCS-only branch this diff adds, not something to prove
# "unchanged".
EXISTING_DIFFICULTY_TARGETS = [None, "easy_medium", "hard", "medium"]


def _load_head_problem_bank() -> types.ModuleType:
    """Load banks/problem_bank.py as it existed at BASELINE_COMMIT (before
    this session's 'easy'-branch / seen_at / sample_problems_with_reuse
    diff) into a standalone module, isolated from the live one under
    sys.modules so both can be imported side by side."""
    src = subprocess.check_output(
        ["git", "show", f"{BASELINE_COMMIT}:backend/banks/problem_bank.py"],
        cwd=REPO_ROOT, text=True,
    )
    mod = types.ModuleType("problem_bank_at_head")
    mod.__file__ = str(BACKEND_DIR / "banks" / "problem_bank.py")
    exec(compile(src, "<head:banks/problem_bank.py>", "exec"), mod.__dict__)
    return mod


@pytest.fixture(scope="module")
def head_problem_bank():
    return _load_head_problem_bank()


@pytest.fixture(scope="module")
def live_problem_bank():
    from banks import problem_bank as live
    return live


@pytest.mark.parametrize("difficulty_target", EXISTING_DIFFICULTY_TARGETS)
@pytest.mark.parametrize("seed", [0, 1, 42, 1234, 999999])
def test_sample_problems_byte_identical_to_head_for_existing_targets(
    difficulty_target, seed, head_problem_bank, live_problem_bank,
):
    random.seed(seed)
    before = head_problem_bank.sample_problems(3, difficulty_target=difficulty_target)
    random.seed(seed)
    after = live_problem_bank.sample_problems(3, difficulty_target=difficulty_target)
    before_ids = [p["id"] for p in before]
    after_ids = [p["id"] for p in after]
    assert before_ids == after_ids, (
        f"difficulty_target={difficulty_target!r} seed={seed}: HEAD gave {before_ids}, "
        f"current gives {after_ids} -- the new 'easy' branch must not perturb any "
        f"existing branch's draw order or content."
    )


@pytest.mark.parametrize("seed", [0, 7, 2026])
def test_needs_buggy_and_exclude_ids_paths_byte_identical_to_head(
    seed, head_problem_bank, live_problem_bank,
):
    # Exercises the needs_buggy filter and exclude_ids pruning (Wipro's/Tech
    # Mahindra's actual call shapes), not just a bare difficulty_target.
    random.seed(seed)
    before = head_problem_bank.sample_problems(
        2, difficulty_target="easy_medium", needs_buggy=True, exclude_ids={"two-sum"},
    )
    random.seed(seed)
    after = live_problem_bank.sample_problems(
        2, difficulty_target="easy_medium", needs_buggy=True, exclude_ids={"two-sum"},
    )
    assert [p["id"] for p in before] == [p["id"] for p in after]


def test_new_easy_branch_is_additive_not_a_replacement(live_problem_bank):
    import inspect
    src = inspect.getsource(live_problem_bank.sample_problems)
    # The new branch must be its own elif, not a rewrite of 'medium'/'hard'/
    # 'easy_medium'/the final else -- those four branch headers must all
    # still be present verbatim.
    assert 'difficulty_target == "easy_medium"' in src
    assert 'difficulty_target == "hard"' in src
    assert 'difficulty_target == "medium"' in src
    assert 'difficulty_target == "easy"' in src
    assert src.count("elif difficulty_target ==") == 3  # easy_medium handled by `if`; hard/medium/easy by elif
    assert "\n    else:\n" in src  # the original default-blend else branch survives


# ---- Capgemini is structurally decoupled from problem_bank.sample_problems --

def test_capgemini_oa_sections_never_set_a_problem_bank_difficulty_target():
    from companies import get_company
    cfg = get_company("capgemini")
    assert cfg is not None
    for section in cfg["sections"]:
        assert "difficulty_target" not in section, (
            f"Capgemini section {section.get('key')!r} unexpectedly sets "
            "difficulty_target -- if this ever changes, this diff's 'easy' "
            "branch could start affecting Capgemini and must be re-audited."
        )
        assert "difficulty_targets" not in section


def test_capgemini_interview_dsa_problems_are_static_not_live_sample_problems_calls():
    import ast

    def _has_sample_problems_call(path: Path) -> bool:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
                if name == "sample_problems":
                    return True
        return False

    dave_path = (
        BACKEND_DIR / "departments" / "computer_science_and_it" /
        "group1_it_services_mass_recruiters" / "capgemini" / "capgemini_interview" /
        "dave" / "dsa.py"
    )
    spark_path = (
        BACKEND_DIR / "departments" / "computer_science_and_it" /
        "group1_it_services_mass_recruiters" / "capgemini" / "capgemini_interview" /
        "spark" / "dsa.py"
    )
    for name, path in (("dave", dave_path), ("spark", spark_path)):
        # ast-based (not a text search): the docstrings in both files
        # mention "problem_bank.sample_problems()" in prose, which a plain
        # substring check would misfire on -- only an ACTUAL Call node
        # (sample_problems(...) executed as code) should fail this test.
        assert not _has_sample_problems_call(path), (
            f"capgemini_interview/{name}/dsa.py calls sample_problems() live -- "
            "it used to be a static copied list; if this changed, Capgemini's "
            "interview DSA draws are no longer provably decoupled from this diff."
        )


def test_capgemini_round1_round2_section_types_are_not_the_generic_coding_type():
    # Capgemini's OA rounds use dedicated "capgemini_round1"/"capgemini_round2_*"
    # types (drawn from their own capgemini_round1_bank), never the shared
    # "coding" section type that routes through sample_problems().
    from companies import get_company
    cfg = get_company("capgemini")
    coding_type_sections = [s for s in cfg["sections"] if s.get("type") == "coding"]
    assert coding_type_sections == [], (
        "Capgemini now has a plain 'coding'-type section -- re-audit whether "
        "it routes through problem_bank.sample_problems()."
    )


# ---- mark_seen() -- every company's real call shape (server.py:1079 etc.) --
# This diff added `seen_at` timestamp tracking (TCS's recycling needs it).
# The pre-existing $addToSet/question_ids/updated_at behavior every other
# company's coding/debugging/ai_assisted sections depend on must be
# unchanged -- proven here against HEAD with a minimal fake Mongo double.

class _FakeSeenColl:
    def __init__(self):
        self.docs = []

    async def update_one(self, query, update, upsert=False):
        target = next(
            (d for d in self.docs if d.get("user_id") == query.get("user_id") and d.get("topic") == query.get("topic")),
            None,
        )
        if target is None:
            if not upsert:
                return
            target = dict(query)
            self.docs.append(target)
        for field, values in update.get("$addToSet", {}).items():
            target.setdefault(field, [])
            for v in values.get("$each", []):
                if v not in target[field]:
                    target[field].append(v)
        for field, value in update.get("$set", {}).items():
            if "." in field:
                head, sub = field.split(".", 1)
                target.setdefault(head, {})[sub] = value
            else:
                target[field] = value


class _FakeProblemBankSeenDb:
    def __init__(self):
        self.problem_bank_seen = _FakeSeenColl()


@pytest.mark.parametrize("question_ids", [["two-sum"], ["two-sum", "lru-cache"], []])
def test_mark_seen_addtoset_and_question_ids_unchanged_from_head(
    question_ids, head_problem_bank, live_problem_bank,
):
    # Real call shape: await problem_bank.mark_seen(user_id, [p["id"] for p in picks])
    # -- default topic="coding", used by every company's "coding" section.
    head_db = _FakeProblemBankSeenDb()
    head_problem_bank.init(head_db)
    asyncio.run(head_problem_bank.mark_seen("u-regress", question_ids))

    live_db = _FakeProblemBankSeenDb()
    live_problem_bank.init(live_db)
    asyncio.run(live_problem_bank.mark_seen("u-regress", question_ids))

    if not question_ids:
        assert head_db.problem_bank_seen.docs == []
        assert live_db.problem_bank_seen.docs == []
        return

    head_doc = head_db.problem_bank_seen.docs[0]
    live_doc = live_db.problem_bank_seen.docs[0]
    assert head_doc["question_ids"] == live_doc["question_ids"] == question_ids
    assert "updated_at" in head_doc and "updated_at" in live_doc
    # The new, additive bit: live also records a per-id seen_at, HEAD never did.
    assert "seen_at" not in head_doc
    assert "seen_at" in live_doc
    for qid in question_ids:
        assert qid in live_doc["seen_at"]


def test_mark_seen_second_call_still_addtoset_not_overwrite(head_problem_bank, live_problem_bank):
    # Two separate mark_seen calls for the same user/topic must UNION
    # question_ids (the original $addToSet contract), not replace the list --
    # same assertion against both HEAD and live to prove the new $set keys
    # (seen_at.*) didn't accidentally change the $addToSet merge behavior.
    head_db = _FakeProblemBankSeenDb()
    head_problem_bank.init(head_db)
    asyncio.run(head_problem_bank.mark_seen("u2", ["two-sum"]))
    asyncio.run(head_problem_bank.mark_seen("u2", ["lru-cache"]))

    live_db = _FakeProblemBankSeenDb()
    live_problem_bank.init(live_db)
    asyncio.run(live_problem_bank.mark_seen("u2", ["two-sum"]))
    asyncio.run(live_problem_bank.mark_seen("u2", ["lru-cache"]))

    assert head_db.problem_bank_seen.docs[0]["question_ids"] == ["two-sum", "lru-cache"]
    assert live_db.problem_bank_seen.docs[0]["question_ids"] == ["two-sum", "lru-cache"]


# ---- sample_problems_with_reuse / bank_size_by_difficulty are NEW, --------
# ---- TCS-only additions, not modifications of an existing function -------

def test_sample_problems_with_reuse_and_bank_size_by_difficulty_are_new(head_problem_bank, live_problem_bank):
    assert not hasattr(head_problem_bank, "sample_problems_with_reuse"), (
        "sample_problems_with_reuse already existed at HEAD -- this is supposed "
        "to be a brand-new, TCS-only function; re-audit what actually changed."
    )
    assert not hasattr(head_problem_bank, "bank_size_by_difficulty")
    assert hasattr(live_problem_bank, "sample_problems_with_reuse")
    assert hasattr(live_problem_bank, "bank_size_by_difficulty")


def test_no_other_company_calls_sample_problems_with_reuse():
    # Only tcs_recruitment_process.py may call the new function -- every
    # other company's coding section must still go through the unmodified
    # sample_problems()/sample_problems_with_reuse-free path.
    import ast

    tcs_path = (
        BACKEND_DIR / "departments" / "computer_science_and_it" /
        "group1_it_services_mass_recruiters" / "tcs" / "tcs_recruitment_process.py"
    )
    other_dirs = [
        p for p in (BACKEND_DIR / "departments").rglob("*_recruitment_process.py")
        if p != tcs_path
    ]
    for path in other_dirs:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "sample_problems_with_reuse":
                pytest.fail(f"{path} references sample_problems_with_reuse -- TCS-only function leaked to another company")
            if isinstance(node, ast.Name) and node.id == "sample_problems_with_reuse":
                pytest.fail(f"{path} references sample_problems_with_reuse -- TCS-only function leaked to another company")
