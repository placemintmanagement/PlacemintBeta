# -*- coding: utf-8 -*-
"""One-off, read-only MongoDB connectivity check after a DB user password
rotation. Uses the same client construction as server.py (AsyncIOMotorClient
against MONGO_URL/DB_NAME) -- this is a separate script process so it can't
literally share server.py's live client object, but it's built identically
rather than via a different driver/pattern. Delete after use."""
import asyncio
import os
import re
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from motor.motor_asyncio import AsyncIOMotorClient

# Collections worth sampling for a "is real data still readable" check.
# NOTE: "reasoning questions" and "DBMS questions" are NOT separate physical
# collections in this schema -- both live in mcq_static_bank, distinguished
# by a `topic` field. deductive_grid puzzles live in the separate puzzle_bank
# collection, distinguished by a `gameType` field. Checked accordingly below.
CHECKS = [
    {"label": "reasoning questions", "collection": "mcq_static_bank", "filter": {"topic": "reasoning"}},
    {"label": "DBMS questions", "collection": "mcq_static_bank", "filter": {"topic": "dbms"}},
    {"label": "deductive_grid puzzle bank", "collection": "puzzle_bank", "filter": {"gameType": "deductive_grid"}},
]


def mask_mongo_url(url: str) -> str:
    return re.sub(r"://([^:/@]+):([^@/]+)@", r"://\1:****@", url)


def truncate(value, max_len=200):
    s = str(value)
    return s if len(s) <= max_len else s[:max_len] + "...(truncated)"


async def main():
    mongo_url = os.environ.get("MONGO_URL", "")
    db_name = os.environ.get("DB_NAME", "")
    print(f"MONGO_URL (masked): {mask_mongo_url(mongo_url)}")
    print(f"DB_NAME: {db_name}")
    print()

    if not mongo_url or not db_name:
        print("CONNECTION FAILED: MONGO_URL or DB_NAME missing from .env")
        return

    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=15000)
    try:
        await client.admin.command("ping")
    except Exception as e:
        print(f"CONNECTION FAILED: {type(e).__name__}: {e}")
        client.close()
        return

    print("CONNECTION SUCCESSFUL (ping + auth OK)\n")

    try:
        db_names = await client.list_database_names()
        print(f"Databases visible on this cluster ({len(db_names)}): {db_names}\n")

        db = client[db_name]
        collection_names = sorted(await db.list_collection_names())
        print(f"Collections in '{db_name}' ({len(collection_names)}):")
        for name in collection_names:
            print(f"  - {name}")
        print()

        for check in CHECKS:
            label, coll_name, flt = check["label"], check["collection"], check["filter"]
            if coll_name not in collection_names:
                print(f"[{label}] collection '{coll_name}' NOT FOUND in this database")
                continue
            coll = db[coll_name]
            count = await coll.count_documents(flt)
            print(f"[{label}] {coll_name} matching {flt}: {count} documents")
            sample = await coll.find_one(flt, {"_id": 0})
            if sample:
                print(f"  sample doc: {truncate(sample)}")
            else:
                print("  sample doc: NONE (count was 0 or filter matched nothing)")
            print()

        print("CONNECTION SUCCESSFUL -- all checks completed, no data modified.")
    except Exception as e:
        print(f"CONNECTION SUCCESSFUL but a later read failed: {type(e).__name__}: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
