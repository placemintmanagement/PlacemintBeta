"""One-off loader: inserts the verified SWE Fundamentals MCQ bank (REST API
+ Git/VCS, authored + independently blind-verified via the scratchpad
pipeline, 5 verification rounds) into the shared `mcq_static_bank`
collection under topic key "swe_fundamentals". Fills the specific gap an
earlier audit found in Capgemini Round 2's Technical Assessment topic --
OOP and DBMS coverage already existed and needed no changes; only REST API
design and Git/VCS were missing.

Mirrors dsa_bank_insert.py's document shape and scope boundary exactly
(question_id/topic/subtopic/prompt/options/correct_index/explanation/
difficulty/source_batch) -- same schema convention, no question_style field
here since that's DSA-specific (trace_execution/conceptual has no swe_
fundamentals equivalent).

Deliberately does NOT add "swe_fundamentals" to mcq_static_bank.
CANONICAL_TOPICS, ai_service.TOPIC_INSTRUCTIONS, mcq_pool.TOPIC_KEY_MAP, or
mcq_pool.POOLED_SECTION_KEYS, and does not write any draw/session-composition
logic -- this only seeds the bank's data, same scope boundary as the DSA and
AI Literacy loaders before it.

Idempotent: upserts on `question_id`, so re-running is safe.

    python scripts/swe_fundamentals_bank_insert.py
"""
from __future__ import annotations
import asyncio
import json
import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

_SCRATCHPAD = r"C:\Users\Anushka\AppData\Local\Temp\claude\c--Users-Anushka-Desktop-PLACEMINT-BETA-PLACEMINT-BETA-main\490a37ca-fa1e-41f9-8883-b6d887ce1a1c\scratchpad"

BANK_FILE = "swe_fundamentals_bank.json"


def _load_questions() -> list[dict]:
    path = os.path.join(_SCRATCHPAD, BANK_FILE)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"]


async def main() -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    questions = _load_questions()

    ids = [q["question_id"] for q in questions]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"Duplicate question_id(s) within source file: {dupes}")

    inserted, updated = 0, 0
    for q in questions:
        doc = {
            "question_id": q["question_id"],
            "topic": q["topic"],
            "subtopic": q["subtopic"],
            "prompt": q["prompt"],
            "options": q["options"],
            "correct_index": q["correct_index"],
            "explanation": q.get("explanation", ""),
            "difficulty": q.get("difficulty", "Medium"),
            "source_batch": "swe_fundamentals-v1",
        }
        result = await db.mcq_static_bank.update_one(
            {"question_id": q["question_id"]},
            {"$set": doc},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
        elif result.modified_count:
            updated += 1

    total_docs = await db.mcq_static_bank.count_documents({"topic": "swe_fundamentals"})
    print(f"Questions in source file: {len(questions)}")
    print(f"Inserted: {inserted} | Updated (already present, re-synced): {updated}")
    print(f"mcq_static_bank now holds {total_docs} 'swe_fundamentals' documents total")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
