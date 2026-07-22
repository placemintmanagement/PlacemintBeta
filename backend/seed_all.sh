#!/bin/bash
set -e
for topic in aptitude verbal reasoning oops dbms os cn architecture; do
    echo "=== SEEDING TOPIC: $topic ==="
    python scripts/mcq_bank_add.py --topic "$topic" --count 65 --batch-label seed-initial
done
echo "=== ALL 8 TOPICS SEEDED ==="
