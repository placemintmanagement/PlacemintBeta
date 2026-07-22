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
    {"stdout": str, "stderr": str, "exit_code": int, "timed_out": bool, "error": str | None}

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
import uuid
from typing import Dict, List, Tuple

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
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "", "exit_code": -1, "timed_out": True, "error": f"Timed out after {timeout}s"}
        except Exception as e:
            return {"stdout": "", "stderr": "", "exit_code": -1, "timed_out": False, "error": str(e)[:300]}


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
        return {"stdout": "", "stderr": "", "exit_code": -1, "timed_out": False, "error": f"Unsupported language: {language}"}
    if not code or not code.strip():
        return {"stdout": "", "stderr": "", "exit_code": -1, "timed_out": False, "error": "Empty code"}
    return runner(code, stdin, timeout)


def run_tests(language: str, code: str, tests: List[Dict[str, str]], timeout: int = DEFAULT_TIMEOUT) -> Tuple[int, List[Dict]]:
    """Run all tests for a submission. Returns (passed_count, details)."""
    passed = 0
    details = []
    for i, t in enumerate(tests):
        stdin = str(t.get("input", ""))
        expected = str(t.get("expected_output", "")).strip()
        result = run_code(language, code, stdin, timeout)
        got = (result["stdout"] or "").strip()
        ok = (not result["timed_out"]) and (result["exit_code"] == 0) and (got == expected)
        details.append({
            "index": i,
            "input": stdin,
            "expected": expected,
            "got": got,
            "passed": ok,
            "error": result.get("error"),
            "stderr": (result.get("stderr") or "")[:300] if not ok else None,
            "timed_out": result["timed_out"],
        })
        if ok:
            passed += 1
    return passed, details
