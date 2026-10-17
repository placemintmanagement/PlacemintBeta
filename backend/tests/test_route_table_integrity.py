"""Route-table integrity guards (2026-10), added after a real bug was found
and fixed: @api.get("/report/{attempt_id}") had been left attached to
_build_tcs_template_report (a plain helper inserted directly below it by a
later commit) instead of final_report, leaving the real report route
undecorated and effectively unreachable over HTTP. Two permanent checks so
a future insertion can't silently do the same thing again:

1. No @api route decorator may land on a function whose name starts with
   an underscore -- every leading-underscore name in this codebase is a
   plain internal helper, never meant to be called by FastAPI's own
   dependency-injected request handling.
2. The live route table (method, path, endpoint function name) must match
   a committed snapshot -- any real route change (adding, removing or
   repointing a route) must update the snapshot in the SAME diff, making
   it a deliberate, reviewed change rather than an accidental side effect
   of inserting a function in the wrong place.

No database, no network, no model calls -- pure introspection of the real
FastAPI app object (server.app), built once at import time exactly like
production.
"""
import json
from pathlib import Path

import server

SNAPSHOT_PATH = Path(__file__).parent / "route_table_snapshot.json"


def _live_route_table():
    """[method, path, endpoint_function_name] for every real APIRoute
    (skips the /media StaticFiles mount, which has no single endpoint
    function), sorted for a stable diff."""
    rows = []
    for r in server.app.routes:
        endpoint = getattr(r, "endpoint", None)
        if endpoint is None:
            continue  # not an APIRoute (e.g. the /media StaticFiles mount)
        path = getattr(r, "path", None)
        methods = sorted(getattr(r, "methods", None) or [])
        for m in methods:
            rows.append([m, path, endpoint.__name__])
    rows.sort()
    return rows


def test_no_api_route_decorator_on_a_private_function():
    offenders = [
        (m, p, name) for m, p, name in _live_route_table() if name.startswith("_")
    ]
    assert offenders == [], (
        f"these routes are decorated onto an underscore-prefixed (internal helper) "
        f"function, which is almost certainly a misplaced decorator: {offenders}"
    )


def test_live_route_table_matches_committed_snapshot():
    live = _live_route_table()
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    live_set = {tuple(r) for r in live}
    snap_set = {tuple(r) for r in snapshot}
    added = sorted(live_set - snap_set)
    removed = sorted(snap_set - live_set)
    assert not added and not removed, (
        f"Live route table drifted from {SNAPSHOT_PATH.name} -- if this change is "
        f"deliberate, regenerate the snapshot (see this test file's module "
        f"docstring for the _live_route_table() helper used to build it).\n"
        f"Added: {added}\nRemoved: {removed}"
    )
