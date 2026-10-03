"""One-off loader: inserts the verified DSA MCQ bank (batches 1-2, authored
+ independently blind-verified via the scratchpad pipeline) into the shared
`mcq_static_bank` collection under topic key "dsa".

Mirrors mcq_bank_add.py's document shape (question_id/topic/prompt/options/
correct_index/explanation/difficulty/date_added/source_batch) plus two
DSA-specific fields (subtopic, question_style) that the existing 8 canonical
topics don't carry — additive, doesn't change how sample_static() reads
existing topics.

Deliberately does NOT add "dsa" to mcq_static_bank.CANONICAL_TOPICS,
ai_service.TOPIC_INSTRUCTIONS, mcq_pool.TOPIC_KEY_MAP, or
mcq_pool.POOLED_SECTION_KEYS, and does not write any draw/session-composition
logic — this only seeds the bank's data so a draw path can be built on top
of it later, same scope boundary as the AI Literacy loader.

Idempotent: upserts on `question_id`, so re-running is safe.

    python scripts/dsa_bank_insert.py
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

BATCH_FILES = [
    "dsa_bank_batch1.json",
    "dsa_bank_batch2.json",
]


def _load_questions() -> list[dict]:
    questions: list[dict] = []
    for fname in BATCH_FILES:
        path = os.path.join(_SCRATCHPAD, fname)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        questions.extend(data["questions"])
    return questions


async def main() -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    questions = _load_questions()

    ids = [q["question_id"] for q in questions]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"Duplicate question_id(s) within source files: {dupes}")

    now = None
    inserted, updated = 0, 0
    for q in questions:
        doc = {
            "question_id": q["question_id"],
            "topic": q["topic"],
            "subtopic": q["subtopic"],
            "question_style": q["question_style"],
            "prompt": q["prompt"],
            "options": q["options"],
            "correct_index": q["correct_index"],
            "explanation": q.get("explanation", ""),
            "difficulty": q.get("difficulty", "Medium"),
            "source_batch": "dsa-batch-1-2",
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

    total_docs = await db.mcq_static_bank.count_documents({"topic": "dsa"})
    print(f"Questions in source files: {len(questions)}")
    print(f"Inserted: {inserted} | Updated (already present, re-synced): {updated}")
    print(f"mcq_static_bank now holds {total_docs} 'dsa' documents total")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
