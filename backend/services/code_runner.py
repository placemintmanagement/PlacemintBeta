"""Multi-language code runner used by the OA engine.

*** IMPORTANT SCALING CAVEAT ***
The concurrency guard below (_EXEC_LOCK) is a threading.Semaphore(1), which
is per-PROCESS, not per-app. It only guarantees "one execution at a time"
as long as this runs as a single worker process. If this app is ever
deployed with multiple Uvicorn/Gunicorn worker processes, each worker gets
its OWN semaphore, so the real system-wide concurrency becomes N (one per
worker), not 1. Achieving a true app-wide cap across multiple processes
would require a cross-process lock (e.g. a file lock or a Redis lock)
instead of this in-memory one. Re-check this before scaling past one
worker process.
*** END CAVEAT ***

Each language has one function ``run_<lang>(code, stdin, timeout) -> RunResult``.
All runners return the same shape so the caller doesn't care which language it is:
    {"stdout": str, "stderr": str, "exit_code": int, "timed_out": bool, "error": str | None,
     "category": "ok" | "runtime_error" | "time_limit_exceeded" | "infrastructure_error"}
"category" (2026-10, reworked with a canary check) distinguishes an
infrastructure failure -- the runner itself never got the candidate's
code running -- from a genuine failure of the candidate's own code.
A timed-out run's category of "infrastructure_error" is a SUSPICION,
not a verdict: run_tests_with_canary_check() below confirms or refutes
it by running a trivial known-good "canary" program through the same
runner under the same limits. A failing/stalled canary means a real
infra problem (grading stops immediately, nothing is scored); a healthy
canary means the STUDENT's program is what's actually slow, and that
test is reclassified as a genuine time_limit_exceeded. The canary's own
pass/fail check needs no CPU-time counters at all, so it's what makes
this whole scheme work identically on Windows (no `resource` module) as
on Linux. See the classification helpers below for the exact rule and
its known ambiguity, resolved by the canary rather than guessed.

Compile-then-run languages (C++, Java) share a two-step wrapper. Interpreted
languages (Python, Node) run directly.

Sandboxing: every subprocess spawned here (compile steps included) goes
through _run(), which:
  - Serializes ALL executions behind one process-wide threading.Semaphore(1),
    so at most one candidate-submitted program is running at any moment
    (see scaling caveat above).
  - Applies POSIX resource limits (RLIMIT_AS/CPU/NPROC/FSIZE) via preexec_fn
    on Linux/macOS. These are a no-op on Windows (`resource` doesn't exist
    there, and subprocess rejects a non-None preexec_fn on Windows) — local
    Windows dev keeps timeout-only protection; Linux prod gets the full set.
  - Drops privileges to the 'nobody' user in the child before exec, if the
    parent process is currently root. No-op if the parent isn't root.

Known limits: this is still a coarse sandbox, not a real jail (no seccomp,
network namespace, or filesystem isolation) — a further hardening pass would
use gVisor/firejail/nsjail per-execution containers.
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from typing import Dict, List, Optional, Tuple

try:
    import resource  # POSIX only
except ImportError:
    resource = None  # Windows: rlimits unavailable, timeout is the only guard

try:
    import pwd  # POSIX only
except ImportError:
    pwd = None

RunResult = Dict[str, object]

DEFAULT_TIMEOUT = 5  # seconds per test

# ---- Result classification (2026-10) ----------------------------------------
# Every RunResult now carries a "category": one of
#   "ok"                  -- the process exited 0 within the timeout (the
#                             caller still separately checks stdout to tell
#                             "passed" from "wrong_answer")
#   "runtime_error"       -- the process ran and exited non-zero (a crash,
#                             uncaught exception, compile error, etc.), or
#                             run_code() rejected the submission outright
#                             (unsupported language, empty code)
#   "time_limit_exceeded" -- the process was killed by the wall-clock
#                             timeout AFTER genuinely consuming CPU time
#                             commensurate with that timeout -- the
#                             student's own code ran and used its time
#   "infrastructure_error" -- the runner itself could not get the
#                             candidate's code running: a spawn failure, an
#                             OS error, or (POSIX only) a timeout where the
#                             killed child consumed almost no CPU time at
#                             all despite running for the full wall-clock
#                             timeout -- i.e. it was blocked, not computing
INFRA_CPU_TIME_FLOOR = 0.5   # seconds -- absolute floor so a short timeout
                             # doesn't make the ratio check below unreasonably tight
INFRA_CPU_TIME_RATIO = 0.1   # if the killed child used less than this fraction
                             # of the wall-clock timeout in actual CPU time, it
                             # was almost certainly blocked rather than computing


def _child_cpu_seconds() -> Optional[float]:
    """Cumulative CPU time (user+sys) of every child this process has
    reaped so far. POSIX only -- `resource` doesn't exist on Windows."""
    if resource is None:
        return None
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    return ru.ru_utime + ru.ru_stime


def _classify_timeout(cpu_before: Optional[float], timeout: int) -> str:
    """Distinguish a genuine time_limit_exceeded (the student's own code
    ran and used its time) from an infrastructure_error (the runner never
    actually got the child meaningfully running -- e.g. blocked on process
    creation, antivirus/on-access-scan overhead on the newly-written source
    file before it could even be exec'd, or some other host-level stall),
    using how much CPU time the killed child actually consumed, measured
    via the CHANGE in this process's RUSAGE_CHILDREN across the call
    (subprocess.run reaps the killed child before raising TimeoutExpired,
    so its usage is already accounted by the time we get here).

    This function only ever returns "time_limit_exceeded" when it can
    PROVE the timeout wasn't an infra problem (comfortable CPU usage).
    Every other case -- including, critically, a platform with no CPU
    counters at all -- returns "infrastructure_error" instead, as a
    SUSPICION for the caller to confirm or refute with a canary run
    (see run_canary() and run_tests_with_canary_check() below), never as
    a final verdict on its own.

    On Windows (`resource` is None), there is no CPU-time signal at all,
    so EVERY timeout comes back "infrastructure_error" here -- the
    canary becomes the sole arbiter of TLE-vs-infra on that platform,
    not an optional enhancement on top of a CPU-time guess that doesn't
    exist there. This is what makes the canary mechanism load-bearing on
    Windows, not just a POSIX nicety.

    KNOWN AMBIGUITY, resolved by the canary rather than guessed here: a
    submission that itself blocks without consuming CPU -- `time.sleep
    (10)`, or code waiting on stdin/a socket/a lock that never arrives/
    frees -- produces the exact same near-zero-CPU/full-wall-time
    signature as a genuine infra stall, and is indistinguishable from
    one by this measurement alone. Flagging it "infrastructure_error"
    here is not the final answer: the caller's canary check resolves it
    -- a healthy canary means the MACHINE is fine, so a result like this
    is reclassified as a genuine time_limit_exceeded instead.
    """
    cpu_after = _child_cpu_seconds()
    if cpu_before is None or cpu_after is None:
        return "infrastructure_error"
    cpu_used = max(0.0, cpu_after - cpu_before)
    threshold = max(INFRA_CPU_TIME_FLOOR, timeout * INFRA_CPU_TIME_RATIO)
    return "infrastructure_error" if cpu_used < threshold else "time_limit_exceeded"

# ---- Resource limits (applied via preexec_fn; no-op on Windows) -------------
MEM_LIMIT_BYTES = 128 * 1024 * 1024          # native run step: python/node/c/cpp
COMPILE_MEM_LIMIT_BYTES = 256 * 1024 * 1024  # gcc/g++ compile
JAVA_MEM_LIMIT_BYTES = 1536 * 1024 * 1024    # javac/java: a modern JVM's OWN startup
                                              # overhead — JIT code cache, compressed class
                                              # space, metaspace, thread stacks — adds up to
                                              # more virtual memory than a naive "loose backstop"
                                              # guess. Empirically re-verified even with every
                                              # footprint flag below applied (SerialGC, capped
                                              # code cache/class space, CDS off, perfdata off,
                                              # 4MB stacks): 1024MB and 768MB both still crash
                                              # the JVM's own native allocator before a single
                                              # byte of candidate heap is touched (Chunk::new
                                              # malloc failures) — 1536MB is the practical floor
                                              # for this JDK build, not a conservative guess.
                                              # This is still just a backstop, not the real
                                              # per-submission constraint — that's -Xmx128m
                                              # plus the explicit code-cache/class-space caps
                                              # below, both applied on the run step.
JAVA_JVM_FOOTPRINT_FLAGS = [
    "-XX:+UseSerialGC",              # tiny short-lived programs don't need G1's parallel/
                                      # concurrent GC machinery, and SerialGC's much smaller
                                      # native bookkeeping (and single GC thread) leaves more
                                      # headroom under both JAVA_MEM_LIMIT_BYTES and NPROC.
    "-XX:CompressedClassSpaceSize=64m",  # default is a fixed 1GB *reservation* regardless
                                          # of heap size — nowhere near needed for one class.
    "-XX:ReservedCodeCacheSize=64m",     # default ~240MB reservation for JIT'd code; a
                                          # one-shot OA submission never runs long enough
                                          # to benefit from more.
    "-Xshare:off",                    # disables Class Data Sharing (mmaps a shared class
                                       # archive at startup) — one-shot processes get no
                                       # reuse benefit from it, so it's pure overhead here.
    "-XX:-UsePerfData",               # disables the perf-monitoring memory-mapped file
                                       # (used by jps/jstat etc.); nothing in this sandbox
                                       # attaches to it, so it's pure overhead too.
]
CPU_LIMIT_SECONDS = 2            # run step, all languages
COMPILE_CPU_LIMIT_SECONDS = 10   # gcc/g++/javac
NPROC_LIMIT = 32                 # fork-bomb tripwire; RLIMIT_NPROC is per-real-uid,
                                  # not per process-tree, so this is coarse by nature
JAVA_NPROC_LIMIT = 64            # JVMs commonly spawn 15-30+ threads (GC threads scaled
                                  # to visible CPU count, JIT compiler threads, VM/signal/
                                  # finalizer threads), and RLIMIT_NPROC counts threads too
                                  # on Linux — the default NPROC_LIMIT can false-trip a
                                  # perfectly healthy JVM launch, so Java gets its own
                                  # headroom instead of raising the limit for every language.
FSIZE_LIMIT_BYTES = 10 * 1024 * 1024
SANDBOX_USER = "nobody"

# Only one candidate program (or compiler invocation) runs at a time, across
# this process. threading.Semaphore, not asyncio.Semaphore: _run() is a
# plain blocking function called both from asyncio.to_thread() worker
# threads and, at some call sites, directly from request handlers — neither
# path guarantees a running event loop in that thread, which asyncio
# primitives require. threading.Semaphore works from any thread and only
# blocks the calling thread; as long as every caller routes through
# asyncio.to_thread (see server.py), acquiring this never blocks the event
# loop itself, only the worker thread waiting its turn.
# NOTE: this is per-process — see the scaling caveat in the module docstring.
_EXEC_LOCK = threading.Semaphore(1)


def _mk_workdir() -> str:
    d = tempfile.mkdtemp(prefix="pm_run_")
    # mkdtemp creates the dir 0700-owned by whoever calls this (the parent
    # harness process, typically root). The child that later runs inside it
    # drops to SANDBOX_USER before exec (see _make_preexec_fn) and would
    # otherwise have zero access to a dir it doesn't own — every read of the
    # source file and every write of compiler output would fail with EACCES.
    # Chown it to the sandbox user now, while we're still root, so the
    # dropped-privilege child can actually use it. Best-effort, same guard
    # pattern as _make_preexec_fn: no-ops on Windows or if we aren't root.
    if pwd is not None and hasattr(os, "geteuid") and os.geteuid() == 0:
        try:
            nobody = pwd.getpwnam(SANDBOX_USER)
            os.chown(d, nobody.pw_uid, nobody.pw_gid)
        except (KeyError, OSError):
            pass
    return d


def _make_preexec_fn(cpu_seconds: int, mem_bytes: int, nproc_limit: int = NPROC_LIMIT):
    """Build a preexec_fn that caps resources and drops root in the child,
    or None where POSIX rlimits aren't available (subprocess raises if a
    non-None preexec_fn is passed on Windows)."""
    if resource is None:
        return None

    def _preexec():
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_NPROC, (nproc_limit, nproc_limit))
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_FSIZE, (FSIZE_LIMIT_BYTES, FSIZE_LIMIT_BYTES))
        except (ValueError, OSError):
            pass
        # Drop root last, after limits are set; no-op if we aren't root.
        if pwd is not None and hasattr(os, "geteuid") and os.geteuid() == 0:
            try:
                nobody = pwd.getpwnam(SANDBOX_USER)
                os.setgroups([])
                os.setgid(nobody.pw_gid)
                os.setuid(nobody.pw_uid)
            except (KeyError, OSError):
                pass

    return _preexec


def _run(cmd: List[str], stdin: str, cwd: str, timeout: int,
         cpu_seconds: int = CPU_LIMIT_SECONDS, mem_bytes: int = MEM_LIMIT_BYTES,
         nproc_limit: int = NPROC_LIMIT) -> RunResult:
    preexec = _make_preexec_fn(cpu_seconds, mem_bytes, nproc_limit)
    with _EXEC_LOCK:
        cpu_before = _child_cpu_seconds()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                preexec_fn=preexec,
            )
            return {
                "stdout": proc.stdout or "",
                "stderr": proc.stderr or "",
                "exit_code": proc.returncode,
                "timed_out": False,
                "error": None,
                "category": "ok" if proc.returncode == 0 else "runtime_error",
            }
        except subprocess.TimeoutExpired:
            category = _classify_timeout(cpu_before, timeout)
            return {"stdout": "", "stderr": "", "exit_code": -1, "timed_out": True,
                    "error": f"Timed out after {timeout}s", "category": category}
        except Exception as e:
            # Process creation itself failed (spawn failure, OS error, a
            # missing interpreter, a permissions problem writing the temp
            # workdir, ...) -- the candidate's code never got a chance to
            # run at all, so this is never the candidate's fault.
            return {"stdout": "", "stderr": "", "exit_code": -1, "timed_out": False,
                    "error": str(e)[:300], "category": "infrastructure_error"}


# ---- Python -----------------------------------------------------------------

def run_python(code: str, stdin: str, timeout: int = DEFAULT_TIMEOUT) -> RunResult:
    d = _mk_workdir()
    try:
        path = os.path.join(d, "main.py")
        with open(path, "w") as f:
            f.write(code)
        return _run(["python3", path], stdin, d, timeout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---- JavaScript (Node) ------------------------------------------------------

def run_javascript(code: str, stdin: str, timeout: int = DEFAULT_TIMEOUT) -> RunResult:
    d = _mk_workdir()
    try:
        path = os.path.join(d, "main.js")
        with open(path, "w") as f:
            f.write(code)
        return _run(["node", path], stdin, d, timeout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---- C --------------------------------------------------------------------

def run_c(code: str, stdin: str, timeout: int = DEFAULT_TIMEOUT) -> RunResult:
    d = _mk_workdir()
    try:
        src = os.path.join(d, "main.c")
        exe = os.path.join(d, "a.out")
        with open(src, "w") as f:
            f.write(code)
        comp = _run(["gcc", "-O2", "-o", exe, src], "", d, 15,
                     cpu_seconds=COMPILE_CPU_LIMIT_SECONDS, mem_bytes=COMPILE_MEM_LIMIT_BYTES)
        if comp["exit_code"] != 0:
            return {"stdout": "", "stderr": comp["stderr"], "exit_code": -1, "timed_out": False, "error": "Compile error"}
        return _run([exe], stdin, d, timeout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---- C++ --------------------------------------------------------------------

def run_cpp(code: str, stdin: str, timeout: int = DEFAULT_TIMEOUT) -> RunResult:
    d = _mk_workdir()
    try:
        src = os.path.join(d, "main.cpp")
        exe = os.path.join(d, "a.out")
        with open(src, "w") as f:
            f.write(code)
        # Compile
        comp = _run(["g++", "-O2", "-std=c++17", "-o", exe, src], "", d, 15,
                     cpu_seconds=COMPILE_CPU_LIMIT_SECONDS, mem_bytes=COMPILE_MEM_LIMIT_BYTES)
        if comp["exit_code"] != 0:
            return {"stdout": "", "stderr": comp["stderr"], "exit_code": -1, "timed_out": False, "error": "Compile error"}
        # Execute
        return _run([exe], stdin, d, timeout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---- Java -------------------------------------------------------------------
_JAVA_CLASS_RE = re.compile(r"public\s+class\s+(\w+)")


def run_java(code: str, stdin: str, timeout: int = DEFAULT_TIMEOUT) -> RunResult:
    """Compile & run a Java program. The public class name is auto-detected;
    if none is found we assume ``Main``.
    """
    d = _mk_workdir()
    try:
        m = _JAVA_CLASS_RE.search(code)
        class_name = m.group(1) if m else "Main"
        src = os.path.join(d, f"{class_name}.java")
        with open(src, "w") as f:
            f.write(code)
        javac_flags = ["-J-Xmx256m"] + [f"-J{flag}" for flag in JAVA_JVM_FOOTPRINT_FLAGS]
        comp = _run(["javac"] + javac_flags + [src], "", d, 20,
                     cpu_seconds=COMPILE_CPU_LIMIT_SECONDS, mem_bytes=JAVA_MEM_LIMIT_BYTES,
                     nproc_limit=JAVA_NPROC_LIMIT)
        if comp["exit_code"] != 0:
            # A JVM boot failure (e.g. can't reserve its default ergonomic
            # heap under RLIMIT_AS) prints to stdout, not stderr, unlike a
            # normal javac syntax error - surface both so this isn't silent.
            return {"stdout": "", "stderr": (comp["stderr"] or comp["stdout"]), "exit_code": -1, "timed_out": False, "error": "Compile error"}
        java_flags = ["-Xmx128m", "-Xss4m"] + JAVA_JVM_FOOTPRINT_FLAGS
        return _run(["java"] + java_flags + ["-cp", d, class_name], stdin, d, timeout,
                     cpu_seconds=CPU_LIMIT_SECONDS, mem_bytes=JAVA_MEM_LIMIT_BYTES,
                     nproc_limit=JAVA_NPROC_LIMIT)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---- Dispatcher -------------------------------------------------------------

_RUNNERS = {
    "python": run_python,
    "python3": run_python,
    "py": run_python,
    "javascript": run_javascript,
    "js": run_javascript,
    "node": run_javascript,
    "c": run_c,
    "cpp": run_cpp,
    "c++": run_cpp,
    "java": run_java,
}

SUPPORTED_LANGUAGES = ["python", "javascript", "c", "cpp", "java"]


def run_code(language: str, code: str, stdin: str, timeout: int = DEFAULT_TIMEOUT) -> RunResult:
    runner = _RUNNERS.get(language.lower())
    if runner is None:
        return {"stdout": "", "stderr": "", "exit_code": -1, "timed_out": False,
                "error": f"Unsupported language: {language}", "category": "runtime_error"}
    if not code or not code.strip():
        return {"stdout": "", "stderr": "", "exit_code": -1, "timed_out": False,
                "error": "Empty code", "category": "runtime_error"}
    return runner(code, stdin, timeout)


def _classify_run_result(result: RunResult, got: str, expected: str) -> str:
    """Maps a RunResult + output comparison to one of the 5 grading
    statuses: passed, wrong_answer, runtime_error, time_limit_exceeded,
    infrastructure_error."""
    category = result.get("category", "ok")
    if category == "ok":
        return "passed" if got == expected else "wrong_answer"
    return category


def run_tests(language: str, code: str, tests: List[Dict[str, str]], timeout: int = DEFAULT_TIMEOUT) -> Tuple[int, List[Dict]]:
    """Run all tests for a submission. Returns (passed_count, details).

    Each detail now also carries "status", one of passed/wrong_answer/
    runtime_error/time_limit_exceeded/infrastructure_error -- additive,
    the existing "passed"/"timed_out" booleans and overall behavior for
    every non-infra outcome are unchanged. This function does NOT retry
    an infrastructure_error -- see run_tests_with_retry() below, which
    _grade_coding_section uses specifically so a bare infra hiccup never
    gets silently recorded as a wrong answer."""
    passed = 0
    details = []
    for i, t in enumerate(tests):
        stdin = str(t.get("input", ""))
        expected = str(t.get("expected_output", "")).strip()
        result = run_code(language, code, stdin, timeout)
        got = (result["stdout"] or "").strip()
        status = _classify_run_result(result, got, expected)
        ok = status == "passed"
        details.append({
            "index": i,
            "input": stdin,
            "expected": expected,
            "got": got,
            "passed": ok,
            "status": status,
            "error": result.get("error"),
            "stderr": (result.get("stderr") or "")[:300] if not ok else None,
            "timed_out": result["timed_out"],
        })
        if ok:
            passed += 1
    return passed, details


# ---- Canary (2026-10 rework) -------------------------------------------
# A trivial, known-good, fixed-output program per language -- the same
# runner function a real submission would use, so it goes through the
# exact same workdir/subprocess/timeout machinery (and, on POSIX, the
# same resource limits). Its pass/fail check below is deliberately NOT
# based on CPU-time accounting at all: "did this finish and print
# exactly the expected sentinel within the timeout" needs nothing POSIX
# -only, so it works identically on Windows.
_CANARY_SENTINEL = "CANARY_OK_7f3a9c2b"
_CANARY_SOURCE_BY_RUNNER = {
    run_python: f'print("{_CANARY_SENTINEL}")\n',
    run_javascript: f'console.log("{_CANARY_SENTINEL}");\n',
    run_c: f'#include <stdio.h>\nint main(){{printf("{_CANARY_SENTINEL}\\n");return 0;}}\n',
    run_cpp: f'#include <iostream>\nint main(){{std::cout<<"{_CANARY_SENTINEL}"<<std::endl;return 0;}}\n',
    run_java: f'public class Main {{ public static void main(String[] args) '
              f'{{ System.out.println("{_CANARY_SENTINEL}"); }} }}\n',
}


def run_canary(language: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """True iff the trivial known-good program for `language` ran to
    completion and printed exactly its expected sentinel within
    `timeout` -- i.e. the SANDBOX itself is healthy for this language
    right now. False means a real infrastructure problem: the exact
    same runner that just failed/stalled on the candidate's code also
    fails/stalls on code that is trivially, unconditionally correct."""
    runner = _RUNNERS.get(language.lower())
    source = _CANARY_SOURCE_BY_RUNNER.get(runner) if runner else None
    if runner is None or source is None:
        return False
    result = runner(source, "", timeout)
    return (
        not result["timed_out"]
        and result["exit_code"] == 0
        and (result.get("stdout") or "").strip() == _CANARY_SENTINEL
    )


def run_tests_with_canary_check(language: str, code: str, tests: List[Dict[str, str]],
                                 timeout: int = DEFAULT_TIMEOUT,
                                 deadline: Optional[float] = None,
                                 ) -> Tuple[int, List[Dict], bool]:
    """Same per-test grading as run_tests(), except a test whose result
    classifies as "infrastructure_error" (a SUSPICION -- see
    _classify_timeout's docstring) triggers a canary check instead of
    blindly retrying the student's test:

      - Canary passes -> the SANDBOX is healthy, so the suspicious
        result was the student's own program being slow (this is also
        the only path on Windows, where _classify_timeout can't measure
        CPU time at all and so is ALWAYS "suspicious" on a timeout).
        Reclassify the test as a genuine time_limit_exceeded and move on
        -- no retry of the student's test.
      - Canary fails -> give the CANARY itself (not the student's test)
        one more try, in case that was a transient blip:
          - Second canary attempt passes -> the blip was transient; give
            the student's ACTUAL test one re-run (at most one) before
            trusting its result. If that re-run is STILL infrastructure_
            error, treat it as persistent after all and stop.
          - Second canary attempt also fails -> a real, persistent
            infrastructure problem. Stop grading IMMEDIATELY: no more
            tests in this call are run, and this call's result must
            never be used to store a score (see unresolved_infra below).

    A genuine time_limit_exceeded (resolved directly by _classify_timeout
    without any ambiguity, or reclassified via a passing canary above) is
    never retried: the student's own code ran and used its time, so
    re-running it would just burn the same outcome again.

    `deadline`, if given, is an absolute time.monotonic() value: if it's
    already passed when about to start a new test, grading stops here
    too (treated the same as a persistent infra failure) -- this is the
    hard per-submission wall-time cap, enforced across every problem in
    a section by the caller threading the SAME deadline through each of
    its calls, not just within one call's own tests.

    Returns (passed_count, details, unresolved_infra). unresolved_infra
    is True iff this call stopped early on a persistent infra problem or
    the deadline -- the caller (_grade_coding_section) uses this to
    abort the WHOLE section grade, raising instead of ever returning a
    score built on an infra failure or a partial result."""
    passed = 0
    details = []
    unresolved_infra = False
    for i, t in enumerate(tests):
        if deadline is not None and time.monotonic() > deadline:
            details.append({
                "index": i, "input": str(t.get("input", "")),
                "expected": str(t.get("expected_output", "")).strip(), "got": "",
                "passed": False, "status": "infrastructure_error",
                "error": "grading wall-time cap exceeded", "stderr": None, "timed_out": False,
            })
            unresolved_infra = True
            break
        stdin = str(t.get("input", ""))
        expected = str(t.get("expected_output", "")).strip()
        result = run_code(language, code, stdin, timeout)
        got = (result["stdout"] or "").strip()
        status = _classify_run_result(result, got, expected)
        if status == "infrastructure_error":
            if run_canary(language, timeout):
                # Sandbox is healthy -- the student's program is what's
                # actually slow/stuck, not the runner.
                status = "time_limit_exceeded"
            elif run_canary(language, timeout):
                # The canary's OWN first failure was transient (it
                # recovered on its second try) -- worth one re-run of
                # the student's actual test before giving up on it.
                result = run_code(language, code, stdin, timeout)
                got = (result["stdout"] or "").strip()
                status = _classify_run_result(result, got, expected)
                if status == "infrastructure_error":
                    unresolved_infra = True
            else:
                # Canary failed twice in a row -- a real, persistent
                # infrastructure problem, not the student's fault.
                unresolved_infra = True
        ok = status == "passed"
        details.append({
            "index": i,
            "input": stdin,
            "expected": expected,
            "got": got,
            "passed": ok,
            "status": status,
            "error": result.get("error"),
            "stderr": (result.get("stderr") or "")[:300] if not ok else None,
            "timed_out": result["timed_out"],
        })
        if ok:
            passed += 1
        if unresolved_infra:
            break  # stop grading immediately -- never grind through the rest
    return passed, details, unresolved_infra
