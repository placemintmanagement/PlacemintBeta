# -*- coding: utf-8 -*-
"""Read-only TCS syllabus-coverage breakdown for mcq_static_bank.

    python scripts/tcs_syllabus_coverage_count.py

ONLY count_documents()/distinct() reads run against the database -- no
find_one, no writes, no deletes, no index/drop, no $out/$merge
aggregation. Never prints MONGO_URL/DB_NAME contents or any secret.

IMPORTANT CAVEAT, read before trusting any number this prints:
mcq_static_bank documents have NO subtopic/tag field at all (confirmed by
inspecting scripts/mcq_bank_add.py, the actual seeding script for
aptitude/verbal/reasoning -- it writes only topic/question_id/prompt/
options/correct_index/explanation/difficulty/chart/svg_diagram/
source_batch/date_added/ground_truth_source/verified_by; "subtopic" only
exists in the unrelated scripts/dsa_bank_insert.py for the DSA bank).

So every per-syllabus-topic count below is a HEURISTIC regex match
against the `prompt` text, not a stored, authoritative tag:
  - It WILL undercount: a question can test "profit and loss" without the
    literal words "profit" or "loss" appearing (e.g. a pure cost-price/
    selling-price numeric question with no labeled terms).
  - It CAN double-count: a single question can match more than one
    syllabus topic's pattern (e.g. a "ratio" question phrased with
    "percentage" in the same prompt matches both).
  - It is a reasonable first estimate, not a certified classification.
    Treat every number below as "at least this many, probably more,
    possibly overlapping" -- not exact.

Advanced Quant / Advanced Reasoning do NOT have their own separate bank:
per companies.py, TCS's "advanced" section's extra_topics use topic keys
"aptitude" and "reasoning" -- the SAME canonical topics Foundation's
numerical/reasoning sections draw from. So "Advanced Quant coverage" below
is a different keyword slice of the IDENTICAL aptitude pool, not a
distinct bank; same for Advanced Reasoning / reasoning.
"""
import asyncio
import os
import re

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from motor.motor_asyncio import AsyncIOMotorClient

READINESS_TARGET_MULTIPLE = 3

# Per-attempt draw, by topic (Foundation-only / Foundation+Part B) -- same
# numbers as scripts/tcs_bank_readiness_count.py, taken from companies.py.
TOPIC_DRAW = {
    "aptitude": {"foundation_only": 20, "foundation_plus_part_b": 30},
    "verbal": {"foundation_only": 25, "foundation_plus_part_b": 25},
    "reasoning": {"foundation_only": 20, "foundation_plus_part_b": 25},
}

# ---------------------------------------------------------------------------
# Syllabus subtopic -> regex pattern (case-insensitive), per TCS section.
# These are deliberately broad-ish keyword/phrase matches, not a precise
# NLP classifier -- see the module docstring's caveat.
# ---------------------------------------------------------------------------

NUMERICAL_PATTERNS = {
    "number system": r"number system|divisib|prime number|\bremainder\b",
    "LCM/HCF": r"\bLCM\b|\bHCF\b|least common multiple|highest common factor|greatest common divisor|\bGCD\b",
    "percentages": r"percent|%",
    "allegations and mixtures": r"allegat|mixture|\balloy\b",
    "ratio and proportion": r"\bratio\b|\bproportion\b",
    "work and time": r"(work.{0,20}time|time.{0,20}work)|complete the work|pipes? and cisterns?|finish the (job|work)",
    "speed, time and distance": r"\bspeed\b|\bdistance\b|km/h|kmph|train.{0,30}platform",
    "profit and loss": r"\bprofit\b|\bloss\b|cost price|selling price|\bC\.?P\.?\b|\bS\.?P\.?\b",
    "averages": r"\baverage\b",
    "ages": r"age of|years old|ages? of|father.{0,15}son|father.{0,15}age",
    "probability": r"\bprobability\b|\bdice\b|coin.{0,15}toss",
    "clocks and calendars": r"\bclock\b|\bcalendar\b|day of the week|leap year",
    "series": r"\bseries\b|next (number|term)",
    "permutations and combinations": r"permutation|combination|ways can|arrange(d)? in",
    "pie/tabular/graphical DI": r"pie chart|bar graph|bar chart|line graph|table below|data interpretation",
}

VERBAL_PATTERNS = {
    "word completion": r"complete the word|fill in the missing letters?",
    "sentence completion": r"complete the sentence|fill in the blank",
    "error identification": r"identify the error|grammatical error|grammatically correct|spot the error",
    "passage ordering": r"rearrange the sentences|correct order.{0,20}sentences|parajumble",
    "sentence joining": r"join the sentences|combine the sentences|using a conjunction",
    "meanings": r"synonym|antonym|meaning of the word|nearest meaning|opposite of",
    "reading comprehension": r"Read the passage and answer the question",
}

REASONING_PATTERNS = {
    "word pattern": r"word pattern|letter pattern",
    "letter series": r"letter series|next letter",
    "number series": r"number series|next number in the series",
    "seating arrangements": r"seated|seating arrangement|around a (round|circular) table|sit(s|ting)? in a row",
    "blood relations": r"blood relation|father'?s son|mother'?s daughter|how is .* related to",
    "directions": r"direction.{0,20}(north|south|east|west)|walks? (north|south|east|west)",
    "statement-conclusion": r"statements?.{0,30}conclusions?|which conclusion",
    "syllogism": r"syllogism|all .* are .*some",
    "data sufficiency": r"data sufficiency|is the data sufficient",
    "logical Venn": r"venn diagram",
    "cube folding / paper cuts / visual-spatial (needs images)": r"\bcube\b|paper (is )?folded|paper cut|mirror image|water image",
}

ADVANCED_QUANT_PATTERNS = {
    # Overlapping-with-Foundation topics reuse the same patterns on purpose
    # -- Advanced Quant draws from the identical "aptitude" bank.
    "number systems": NUMERICAL_PATTERNS["number system"],
    "percentages": NUMERICAL_PATTERNS["percentages"],
    "averages": NUMERICAL_PATTERNS["averages"],
    "profit and loss": NUMERICAL_PATTERNS["profit and loss"],
    "SI/CI": r"simple interest|compound interest|\bS\.?I\.?\b|\bC\.?I\.?\b",
    "time and work": NUMERICAL_PATTERNS["work and time"],
    "time and distance": NUMERICAL_PATTERNS["speed, time and distance"],
    "probability": NUMERICAL_PATTERNS["probability"],
    "P&C": NUMERICAL_PATTERNS["permutations and combinations"],
    "ratio": NUMERICAL_PATTERNS["ratio and proportion"],
    "algebra": r"\bequation\b|\bvariable\b|solve for x|\balgebra",
    "geometry": r"\btriangle\b|\bcircle\b|\brectangle\b|area of|perimeter|\bvolume\b|\bgeometry\b",
    "trigonometry": r"\bsin\b|\bcos\b|\btan\b|trigonometry|angle of elevation",
}

ADVANCED_REASONING_PATTERNS = {
    "complex seating": REASONING_PATTERNS["seating arrangements"],
    "distance and directions": REASONING_PATTERNS["directions"],
    "odd one out": r"odd one out|which (one|word|number) does not belong",
    "symbols and notations": r"if .* means|symbol(s)? represents?|coded as",
    "letter analogy": r"analogy|is related to.{0,20}in the same way",
    "numerical patterns": REASONING_PATTERNS["number series"],
    "meaningful word creation": r"meaningful word|rearrange the letters",
}

SECTIONS = [
    ("TCS Numerical", "aptitude", NUMERICAL_PATTERNS, False),
    ("TCS Verbal", "verbal", VERBAL_PATTERNS, False),
    ("TCS Reasoning", "reasoning", REASONING_PATTERNS, False),
    ("TCS Advanced Quant (same bank as Numerical)", "aptitude", ADVANCED_QUANT_PATTERNS, True),
    ("TCS Advanced Reasoning (same bank as Reasoning)", "reasoning", ADVANCED_REASONING_PATTERNS, True),
]


def _verdict(count: int, draw: int) -> str:
    if count <= 0:
        return "MISSING"
    return "READY" if count >= draw * READINESS_TARGET_MULTIPLE else "THIN"


async def _count(coll, topic: str, pattern: str) -> int:
    return await coll.count_documents({"topic": topic, "prompt": {"$regex": pattern, "$options": "i"}})


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
    coll = db.mcq_static_bank
    print(f"Connected to '{db_name}'. All reads are count_documents/distinct -- no writes.\n")
    print("Reminder: every per-subtopic count below is a HEURISTIC regex match")
    print("against `prompt` text, not a stored tag. See this script's docstring.\n")

    for topic in ("aptitude", "verbal", "reasoning"):
        diffs = await coll.distinct("difficulty", {"topic": topic})
        print(f"=== {topic}: difficulty breakdown ===")
        for d in sorted(diffs):
            n = await coll.count_documents({"topic": topic, "difficulty": d})
            print(f"  {d}: {n}")
        print()

    for section_name, topic, patterns, is_advanced in SECTIONS:
        draws = TOPIC_DRAW[topic]
        draw = draws["foundation_plus_part_b"] if is_advanced else draws["foundation_only"]
        print(f"=== {section_name} (topic={topic!r}, draw/attempt={draw}) ===")
        for subtopic, pattern in patterns.items():
            n = await _count(coll, topic, pattern)
            print(f"  {subtopic:55s} {n:6d}  {_verdict(n, draw)}")
        if is_advanced and section_name.startswith("TCS Advanced Quant"):
            hard_n = await coll.count_documents({"topic": topic, "difficulty": "Hard"})
            print(f"  -- hard-tagged questions in the whole '{topic}' bank: {hard_n}")
        print()

    rc_count = await _count(coll, "verbal", VERBAL_PATTERNS["reading comprehension"])
    print(f"Reading comprehension: {rc_count} questions match the RC prompt pattern.")
    print("Each RC question embeds its OWN full copy of the passage text (no shared")
    print("passage collection/grouping exists), so passages-count == questions-count")
    print(f"here: {rc_count} passages, {rc_count} questions (1 question per passage by construction).")
    print()

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
