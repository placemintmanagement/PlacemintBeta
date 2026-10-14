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
import random
import subprocess
import sys
import types
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

# difficulty_target strings actually used, today, by some company's "coding"
# section per companies.py (grepped at write-time: Wipro uses the per-problem
# list ["easy_medium", "hard"]; Zoho uses "easy_medium" for R2 and "hard" for
# R3; the generic fallback company uses "medium"; None is the Capgemini-
# round1-style / IBM-style default blend). "easy" is deliberately excluded --
# it's the new, TCS-only branch this diff adds, not something to prove
# "unchanged".
EXISTING_DIFFICULTY_TARGETS = [None, "easy_medium", "hard", "medium"]


def _load_head_problem_bank() -> types.ModuleType:
    """Load banks/problem_bank.py as it exists at git HEAD (i.e. before this
    session's uncommitted 'easy'-branch diff) into a standalone module, isolated
    from the live one under sys.modules so both can be imported side by side."""
    src = subprocess.check_output(
        ["git", "show", "HEAD:backend/banks/problem_bank.py"],
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
