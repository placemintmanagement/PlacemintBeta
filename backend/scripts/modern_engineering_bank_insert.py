"""One-off loader: inserts the verified Modern Engineering Awareness MCQ
bank (Docker/Agile/DevOps/cloud fundamentals/API keys vs tokens/
Kubernetes, authored in 2 batches of 50 + independently blind-verified
via the scratchpad pipeline -- 3 rounds on batch 1, 3 rounds on batch 2,
plus a 4-round bank-wide final gate that caught and fixed a cross-batch
statistical tell neither batch's individual audit could see) into the
shared `mcq_static_bank` collection under topic key "modern_engineering".

Mirrors dsa_bank_insert.py / swe_fundamentals_bank_insert.py's document
shape and scope boundary exactly (question_id/topic/subtopic/prompt/
options/correct_index/explanation/difficulty/source_batch) -- same
schema convention, no question_style field here.

Deliberately does NOT add "modern_engineering" to mcq_static_bank.
CANONICAL_TOPICS, ai_service.TOPIC_INSTRUCTIONS, mcq_pool.TOPIC_KEY_MAP,
or mcq_pool.POOLED_SECTION_KEYS, and does not write any draw/session-
composition logic -- this only seeds the bank's data, same scope
boundary as the DSA, AI Literacy, and SWE Fundamentals loaders before it.

Idempotent: upserts on `question_id`, so re-running is safe.

    python scripts/modern_engineering_bank_insert.py
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

BANK_FILE = "modern_engineering_full.json"


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
        source_batch = "modern_engineering-b1" if "-b1-" in q["question_id"] else "modern_engineering-b2"
        doc = {
            "question_id": q["question_id"],
            "topic": q["topic"],
            "subtopic": q["subtopic"],
            "prompt": q["prompt"],
            "options": q["options"],
            "correct_index": q["correct_index"],
            "explanation": q.get("explanation", ""),
            "difficulty": q.get("difficulty", "Medium"),
            "source_batch": source_batch,
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

    total_docs = await db.mcq_static_bank.count_documents({"topic": "modern_engineering"})
    print(f"Questions in source file: {len(questions)}")
    print(f"Inserted: {inserted} | Updated (already present, re-synced): {updated}")
    print(f"mcq_static_bank now holds {total_docs} 'modern_engineering' documents total")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
