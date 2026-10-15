"""Shared helper for loading a historical copy of banks/problem_bank.py
via `git show`, used by both test_problem_bank_target_tests_regression.py
and test_greedy_min_platforms_fix.py. Cached (per test-worker process) so
running both files together only pays the expensive full-bank hydration
(104 problems, each run through its reference solution via subprocess)
for a given commit ONCE, not once per file -- not a test module itself
(no test_ prefix, same convention as spark_support.py/dave_support.py)."""
import functools
import subprocess
import types
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


@functools.lru_cache(maxsize=None)
def load_commit_problem_bank(commit: str) -> types.ModuleType:
    src = subprocess.check_output(
        ["git", "show", f"{commit}:backend/banks/problem_bank.py"],
        cwd=REPO_ROOT, text=True,
    )
    mod = types.ModuleType(f"problem_bank_at_{commit}")
    mod.__file__ = str(BACKEND_DIR / "banks" / "problem_bank.py")
    exec(compile(src, f"<{commit}:banks/problem_bank.py>", "exec"), mod.__dict__)
    return mod
