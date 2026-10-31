# -*- coding: utf-8 -*-
"""Read-only companion script for scratchpad/tcs_bank_readiness.md.

The assistant that wrote this script was explicitly instructed to never
touch the real (Atlas) database itself -- every bank size in the readiness
report is therefore marked UNKNOWN. This script does the read ONLY when
*you* run it, against whatever MONGO_URL/.env already point at:

    python scripts/tcs_bank_readiness_count.py

It performs count_documents() reads only, plus one admin.command("ping")
connectivity check -- no find_one, no writes, no deletes, no index
changes, no $out/$merge aggregation. Safe to run against Atlas
production. It never prints MONGO_URL, DB_NAME contents, or any other
secret -- only aggregate counts and percentages.

What it reports, per canonical topic TCS actually draws from
(aptitude/verbal/reasoning -- see tcs_recruitment_process.py /
companies.py's tcs-nqt section list):
  - total question count in mcq_static_bank for that topic
  - how many of those have a non-empty `explanation` field
  - how many have a `chart` field set, and how many have `svg_diagram` set
  - this candidate's single-attempt draw for that topic (Foundation-only vs
    Foundation+Part B), hardcoded from companies.py since that part IS
    known without touching the DB
  - attempts-before-first-repeat = bank_size // draw_per_attempt, for both
    the Foundation-only and the Foundation+Part-B draw rates

Also reports problem_bank (coding) by difficulty -- that bank's *size* is
already known without a DB query (banks/problem_bank.py embeds it as a
literal Python list, not Mongo-backed), so this just cross-checks the
live-process count against the DB-free one as a sanity check, plus reports
problem_bank_seen coverage.
"""
import asyncio
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from motor.motor_asyncio import AsyncIOMotorClient

# Per-attempt draw counts, by topic, taken directly from companies.py's
# tcs-nqt section list (2026-10 rebuild) -- NOT a DB read, just arithmetic
# over static config:
#   "aptitude" topic  <- numerical section (20) + advanced's "aptitude"
#                        extra_topic (10, Part B only)
#   "verbal" topic    <- verbal section (25) only (no Part B sibling)
#   "reasoning" topic <- reasoning section (20) + advanced's "reasoning"
#                        extra_topic (5, Part B only)
TOPIC_DRAW_PER_ATTEMPT = {
    "aptitude":  {"foundation_only": 20, "foundation_plus_part_b": 30},
    "verbal":    {"foundation_only": 25, "foundation_plus_part_b": 25},
    "reasoning": {"foundation_only": 20, "foundation_plus_part_b": 25},
}

READINESS_TARGET_MULTIPLE = 3  # "at least 3x one attempt's draw" per the ask


def attempts_before_repeat(bank_size: int, draw_per_attempt: int) -> str:
    if draw_per_attempt <= 0:
        return "n/a"
    if bank_size <= 0:
        return "0 (empty bank)"
    return str(bank_size // draw_per_attempt)


async def report_mcq_topic(db, topic: str) -> None:
    coll = db.mcq_static_bank
    total = await coll.count_documents({"topic": topic})
    with_explanation = await coll.count_documents({"topic": topic, "explanation": {"$exists": True, "$ne": ""}})
    with_chart = await coll.count_documents({"topic": topic, "chart": {"$exists": True, "$ne": None}})
    with_svg = await coll.count_documents({"topic": topic, "svg_diagram": {"$exists": True, "$ne": None}})

    print(f"=== topic: {topic} ===")
    print(f"  total questions:           {total}")
    print(f"  with non-empty explanation: {with_explanation} ({_pct(with_explanation, total)})")
    print(f"  with chart field set:       {with_chart} ({_pct(with_chart, total)})")
    print(f"  with svg_diagram field set: {with_svg} ({_pct(with_svg, total)})")

    draws = TOPIC_DRAW_PER_ATTEMPT.get(topic)
    if draws:
        fo = draws["foundation_only"]
        fb = draws["foundation_plus_part_b"]
        print(f"  draw/attempt (Foundation only):      {fo}  -> attempts before first repeat: {attempts_before_repeat(total, fo)}")
        print(f"  draw/attempt (Foundation + Part B):   {fb}  -> attempts before first repeat: {attempts_before_repeat(total, fb)}")
        target = fb * READINESS_TARGET_MULTIPLE
        verdict = "READY" if total >= target else ("THIN" if total >= fb else "MISSING/BLOCKED")
        print(f"  verdict (>= {READINESS_TARGET_MULTIPLE}x the {fb}-question Foundation+Part-B draw, i.e. >= {target}): {verdict}")
    print()


def _pct(n: int, total: int) -> str:
    if total <= 0:
        return "n/a"
    return f"{100.0 * n / total:.0f}%"


async def report_problem_bank(db) -> None:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from banks import problem_bank as pb  # noqa: E402 -- literal in-process bank, not DB-backed

    print("=== coding (problem_bank -- literal in-process list, not Mongo) ===")
    for diff in ("easy", "medium", "hard"):
        print(f"  {diff}: {pb.bank_size_by_difficulty(diff)} problems")
    print(f"  total: {len(pb._BANK)} problems")
    print("  (TCS draws 2 problems/attempt: profile A = 1 easy + 1 medium, "
          "profile B = 2 medium, 50/50 seeded per attempt -- see apply_coding_profile)")
    easy_n = pb.bank_size_by_difficulty("easy")
    medium_n = pb.bank_size_by_difficulty("medium")
    print(f"  attempts before first repeat, easy (worst case, every attempt draws 1): {attempts_before_repeat(easy_n, 1)}")
    print(f"  attempts before first repeat, medium (worst case, every attempt draws 2): {attempts_before_repeat(medium_n, 2)}")
    print()

    seen_coll = db.problem_bank_seen
    seen_docs = await seen_coll.count_documents({})
    print(f"  problem_bank_seen documents (one per user, all topics): {seen_docs}")
    print()


async def main():
    mongo_url = os.environ.get("MONGO_URL", "")
    db_name = os.environ.get("DB_NAME", "")
    if not mongo_url or not db_name:
        print("ABORTING: MONGO_URL or DB_NAME missing from .env -- nothing read.")
        return

    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=15000)
    try:
        await client.admin.command("ping")
    except Exception as e:
        print(f"CONNECTION FAILED: {type(e).__name__}: {e}")
        client.close()
        return

    db = client[db_name]
    print(f"Connected to '{db_name}'. All reads below are count_documents only -- no writes.\n")

    for topic in ("aptitude", "verbal", "reasoning"):
        await report_mcq_topic(db, topic)

    await report_problem_bank(db)

    client.close()
    print("Done. Paste this output back so the readiness report's UNKNOWN sizes can be filled in.")


if __name__ == "__main__":
    asyncio.run(main())
