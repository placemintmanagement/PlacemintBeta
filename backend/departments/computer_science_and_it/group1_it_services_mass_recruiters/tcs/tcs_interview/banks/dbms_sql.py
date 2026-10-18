# -*- coding: utf-8 -*-
"""TCS Technical-round DBMS/SQL question bank.

# SEED CONTENT: a small, hand-written STARTING set (4 questions), not
production-complete. Production should grow this to at least 10-12 items,
same ratio reasoning as oop.py. Freshly written for TCS, not copied from
Dave's SQL_QUESTIONS bank -- see oop.py's docstring for the reuse decision.

Shape: {id, topic, difficulty, text, key_points} -- see banks/_kp.py.
"""
from typing import Any, Dict, List

from ._kp import kp

DBMS_SQL_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-dbms-1", "topic": "dbms_sql", "difficulty": "ninja",
        "text": "What is a primary key, and how is it different from a foreign key?",
        "key_points": [
            kp("a primary key uniquely identifies each row in its own table, and cannot be null",
               "a primary key enforces entity-level uniqueness"),
            kp("a foreign key is a column (or set of columns) in one table that references the primary key of another table",
               "a foreign key enforces a relationship between two tables"),
        ],
    },
    {
        "id": "tcs-dbms-2", "topic": "dbms_sql", "difficulty": "ninja",
        "text": "What is the difference between an INNER JOIN and a LEFT JOIN?",
        "key_points": [
            kp("INNER JOIN returns only rows that have a match in both tables",
               "INNER JOIN excludes unmatched rows from either side"),
            kp("LEFT JOIN returns every row from the left table, with NULLs for unmatched columns from the right table",
               "LEFT JOIN keeps all left-side rows even without a match"),
        ],
    },
    {
        "id": "tcs-dbms-3", "topic": "dbms_sql", "difficulty": "digital",
        "text": "What does normalization mean in database design, and why would a table be normalized?",
        "key_points": [
            kp("normalization organizes columns/tables to reduce data redundancy",
               "normalization avoids storing the same fact in multiple places"),
            kp("it reduces the risk of update/insert/delete anomalies from duplicated data",
               "normalization improves data consistency when rows change"),
        ],
    },
    {
        "id": "tcs-dbms-4", "topic": "dbms_sql", "difficulty": "prime",
        "text": "What does the ACID acronym stand for in the context of database transactions, and why does Atomicity matter for a banking-style transfer?",
        "key_points": [
            kp("names Atomicity, Consistency, Isolation and Durability correctly",
               "correctly expands all four letters of ACID"),
            kp("explains Atomicity as: a transaction either fully completes or fully rolls back, no partial effect",
               "connects atomicity to a transfer example -- debit and credit must both happen or neither should"),
        ],
    },
]
