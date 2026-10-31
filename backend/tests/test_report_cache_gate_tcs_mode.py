"""Bug-fix regression test for _build_final_report_doc's report-cache gate
(server.py, the `capgemini_interview_open` local inside that function).

The gate exists so a Spark/Dave/Commit report is never read from, or written
to, the db.reports cache while that interview is still open (in_progress) --
otherwise the report would freeze stale before the interview finishes. The
gate used to recognise only mode in ("spark", "dave", "commit"). A TCS
interview (mode == "tcs", added in a later commit) was never added to that
tuple, so a TCS report WOULD be served from -- and written to -- the cache
while the TCS interview is still open, exactly the staleness bug the gate
exists to prevent for the other three tiers.

This test calls _build_final_report_doc directly with a bare, synthetic
interview_doc shaped like {"mode": "tcs", "state": {"status": "in_progress"},
...} -- deliberately not going through any real TCS start/answer flow (which
does not exist yet at this point in the commit sequence) -- to exercise the
gate's own logic in isolation. No real Mongo, no real AI: an in-memory fake
db (borrowed from spark_support.py's generic, tier-agnostic _Coll/_Result)
and a stubbed server.call_json.
"""
import asyncio
from types import SimpleNamespace

from spark_support import _Coll  # noqa: F401 -- generic, tier-agnostic fake Mongo collection

import server

USER = {"user_id": "u1", "name": "Priya"}


def _fresh_report_world(monkeypatch, *, interview_status: str, seed_stale_cache: bool = True):
    """A TCS-mode interview_doc, optionally with a STALE cached report
    already sitting in db.reports for the same cache_query. Returns
    (fake_db, interview_doc)."""
    interview_doc = {
        "interview_id": "intv-tcs-1",
        "user_id": "u1",
        "company_id": "tcs-nqt",
        "mode": "tcs",
        "tier": "ninja",
        "tier_source": "chosen",
        "resume_id": None,
        "answers": [],
        # "deadline_at" far in the future: _build_final_report_doc (once TCS
        # is fully wired, a later commit) also runs this doc through
        # _finalize_interview_if_expired -> tcs_orchestration.finalize_if_
        # expired before reaching the gate under test here, which reads
        # state["deadline_at"] even on an in_progress doc (to decide it is
        # NOT expired) -- a real TCS interview document always has this
        # field (core.new_state); this synthetic one needs it too so that
        # later wiring doesn't crash on a doc this test built by hand.
        "state": {"status": interview_status, "deadline_at": 9_999_999_999.0},
    }
    seed = [{
        "interview_id": "intv-tcs-1", "user_id": "u1",
        "report": {"stale": True}, "interview_summary": {"skipped": True},
    }] if seed_stale_cache else []
    fake_db = SimpleNamespace(
        reports=_Coll(seed),
        resumes=_Coll([]),
    )
    monkeypatch.setattr(server, "db", fake_db)

    async def fake_call_json(system, prompt, **kwargs):
        return {"overall_verdict": "borderline", "overall_score": 42, "narrative": "fresh",
                "weakest_dimension": "", "strongest_dimension": "", "next_steps": []}

    monkeypatch.setattr(server, "call_json", fake_call_json)
    return fake_db, interview_doc


def _call(interview_doc):
    return asyncio.run(server._build_final_report_doc(
        attempt=None, interview_doc=interview_doc, user=USER, company_name="TCS NQT",
        cache_query={"interview_id": "intv-tcs-1", "user_id": "u1"},
        extra_doc_fields={},
    ))


def test_a_tcs_report_is_not_served_stale_from_cache_while_the_interview_is_open(monkeypatch):
    """THE BUG: before the fix, mode == "tcs" is not in the gate's tuple, so
    `capgemini_interview_open` is always False for a TCS doc regardless of its
    real state["status"] -- the stale cached report is served even though the
    interview is still in_progress. After the fix, the gate recognises "tcs"
    too, correctly refuses the stale cache for an in-progress interview, and
    regenerates a fresh report instead."""
    fake_db, interview_doc = _fresh_report_world(monkeypatch, interview_status="in_progress")

    report = _call(interview_doc)

    assert report.get("report", {}).get("stale") is None, (
        "a TCS report was served from the pre-interview cache while the interview "
        "is still in_progress -- this is exactly the staleness bug the "
        "capgemini_interview_open gate exists to prevent for spark/dave/commit, "
        "now reproduced for mode=='tcs'"
    )
    # Nothing new should have been written to the cache either, while open.
    fresh_docs = [d for d in fake_db.reports.docs if d.get("report") != {"stale": True}]
    assert fresh_docs == [], "a fresh report must not be cached while the TCS interview is still open"


def test_a_finished_tcs_interviews_report_is_computed_and_cached(monkeypatch):
    """Sanity check on the other side of the gate: once the TCS interview is
    no longer in_progress (and nothing is already cached for it), the report
    is built fresh and persisted to the cache -- same as Spark/Dave/Commit's
    own completed-interview behaviour."""
    fake_db, interview_doc = _fresh_report_world(
        monkeypatch, interview_status="completed", seed_stale_cache=False)

    report = _call(interview_doc)

    assert report.get("report", {}).get("overall_score") == 42
    assert len(fake_db.reports.docs) == 1, "a finished TCS interview's report should be cached, same as spark/dave/commit"
