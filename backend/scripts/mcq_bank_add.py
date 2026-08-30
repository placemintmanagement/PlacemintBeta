"""Reusable script to add verified questions to the static MCQ bank
(mcq_static_bank). Run manually, any month you want to grow a topic:

    python scripts/mcq_bank_add.py --topic oops --count 65
    python scripts/mcq_bank_add.py --topic dbms --count 50 --batch-label monthly-2026-08

This is the ONLY tool needed to add content — no new code per run. It reuses
the exact same Stage A (topic_mcq_prompt) / Stage B+C (mcq_pool's
_process_one_stem: two-independent-solver-agreement-or-code-execution, then
explanation-with-conflict-check) pipeline the live background pool already
uses, so every question added here meets the identical quality bar as
everything mcq_pool verifies. Generates in bounded-size raw batches (well
under Anthropic's 4096-output-token ceiling — see server.py's BATCH_SIZE
comment for the truncation bug this same discipline avoids) and asks for a
bit more than needed per round to absorb the real ~15-25% verification drop
rate observed live, looping until `count` verified questions accumulate or
a safety cap on rounds is hit.

Valid --topic values are the 8 canonical topics: aptitude, verbal, reasoning,
oops, dbms, os, cn, architecture (ai_service.TOPIC_INSTRUCTIONS).
"""
from __future__ import annotations
import argparse
import asyncio
import math
import os
import sys
from datetime import datetime, timezone

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
import banks.mcq_pool  # noqa: E402
from services.ai_service import topic_mcq_prompt, call_json, HAIKU, SONNET, TOPIC_INSTRUCTIONS  # noqa: E402

RAW_BATCH_SIZE = 15   # Stage-A ask cap per call — safely under the token-truncation ceiling
MAX_ROUNDS = 20        # safety cap on Stage-A rounds before giving up short of `count`
DROP_RATE_BUFFER = 1.3  # ask ~30% more than the shortfall per round to absorb verification drops

# {topic_key: topic_name} — reuses TOPIC_KEY_MAP as the single source of
# truth (values are (topic_key, topic_name) tuples) rather than duplicating it.
TOPIC_NAMES = dict(banks.mcq_pool.TOPIC_KEY_MAP.values())


async def _generate_verified_batch(topic_key: str, topic_name: str, ask: int) -> list:
    system = "You are an expert Indian tech OA question setter. Return only strict JSON."
    raw = await call_json(system, topic_mcq_prompt("StaticBankSeed", topic_key, topic_name, ask, None), model=HAIKU)
    if not isinstance(raw, list):
        return []
    tasks = [
        banks.mcq_pool._process_one_stem("StaticBankSeed", f"static-seed-{topic_key}", stem)
        for stem in raw if isinstance(stem, dict)
    ]
    docs = await asyncio.gather(*tasks, return_exceptions=True)
    return [d for d in docs if isinstance(d, dict)]


async def _next_question_id_start(db, topic: str) -> int:
    cursor = db.mcq_static_bank.find({"topic": topic}, {"question_id": 1}).sort("question_id", -1).limit(1)
    docs = await cursor.to_list(length=1)
    if not docs:
        return 1
    try:
        return int(docs[0]["question_id"].rsplit("-", 1)[-1]) + 1
    except Exception:
        return 1


async def add_batch(db, topic_key: str, count: int, batch_label: str | None) -> int:
    if topic_key not in TOPIC_INSTRUCTIONS:
        raise ValueError(f"Unknown topic '{topic_key}'. Valid: {sorted(TOPIC_INSTRUCTIONS)}")
    topic_name = TOPIC_NAMES.get(topic_key, topic_key.title())
    source_batch = batch_label or f"seed-{datetime.now(timezone.utc).strftime('%Y-%m')}"

    verified: list = []
    round_i = 0
    while len(verified) < count and round_i < MAX_ROUNDS:
        remaining = count - len(verified)
        ask = min(RAW_BATCH_SIZE, max(remaining + 3, math.ceil(remaining * DROP_RATE_BUFFER)))
        print(f"[{topic_key}] round {round_i + 1}: asking {ask} raw stems ({len(verified)}/{count} verified so far)")
        got = await _generate_verified_batch(topic_key, topic_name, ask)
        print(f"[{topic_key}] round {round_i + 1}: {len(got)}/{ask} passed verification")
        verified.extend(got)
        round_i += 1

    verified = verified[:count]
    if len(verified) < count:
        print(f"[{topic_key}] WARNING: only {len(verified)}/{count} verified after {round_i} rounds (MAX_ROUNDS reached)")

    start_id = await _next_question_id_start(db, topic_key)
    now = datetime.now(timezone.utc).isoformat()
    docs = [{
        "question_id": f"{topic_key}-{start_id + i:04d}",
        "topic": topic_key,
        "prompt": q["prompt"],
        "options": q["options"],
        "correct_index": q["correct_index"],
        "explanation": q.get("explanation", ""),
        "difficulty": q.get("difficulty", "Medium"),
        "ground_truth_source": q.get("ground_truth_source", "solver_agreement"),
        "date_added": now,
        "verified_by": f"{SONNET[1]}+{HAIKU[1]}",
        "source_batch": source_batch,
    } for i, q in enumerate(verified)]
    if docs:
        await db.mcq_static_bank.insert_many(docs)
    print(f"[{topic_key}] DONE: inserted {len(docs)} questions (source_batch={source_batch})")
    return len(docs)


async def main():
    parser = argparse.ArgumentParser(description="Add verified questions to the static MCQ bank.")
    parser.add_argument("--topic", required=True, choices=sorted(TOPIC_INSTRUCTIONS))
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--batch-label", default=None)
    args = parser.parse_args()

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    banks.mcq_pool.init(db)
    try:
        await add_batch(db, args.topic, args.count, args.batch_label)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
