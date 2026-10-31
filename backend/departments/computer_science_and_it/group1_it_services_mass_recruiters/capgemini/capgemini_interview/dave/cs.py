# -*- coding: utf-8 -*-
"""Dave interview CS-fundamentals question bank (Capgemini Dave tier only).

Topics: oops, sql, os (STATED -- no other topics). Fixed questions, no live
follow-ups; the model only grades, it never writes a CS-fundamentals
question. Each question has 3-4 key_points, phrased as statements a
candidate could be quoted saying; the grading prompt is told to accept a
correct point in the candidate's own words, not just the alternatives
listed here -- `alternatives` are extra accepted phrasings offered to the
grader as examples, not an exhaustive whitelist.

Excluded by design (STATED): normalization, transactions and other pure
DBMS theory under SQL -- the SQL bank covers joins, keys/constraints, GROUP
BY vs HAVING, DELETE vs TRUNCATE vs DROP, indexes, subqueries, plus
query-writing questions against a small shown schema.

Query-writing questions additionally carry schema_sql/sample_rows_sql (for
an in-memory SQLite verification pass: the reference query and every
accepted alternative approach must return the stored expected_result).
Each query question's own `text` is self-contained -- the schema and
sample rows are shown inline in the question text itself, not in a
separate display_schema field, since topics (and which specific question)
are drawn at random and a candidate asked cs-sql-q2 or cs-sql-q3 may never
have seen cs-sql-q1's schema.
"""
from typing import Any, Dict, List

CS_TOPIC_WEIGHTS: Dict[str, float] = {"oops": 0.4, "sql": 0.4, "os": 0.2}  # INTERPOLATED: "mostly OOPS and SQL" was stated, the exact split was not


def _kp(statement: str, *alternatives: str) -> Dict[str, Any]:
    return {"statement": statement, "alternatives": list(alternatives)}


# ---- OOP (9 questions) ------------------------------------------------------
OOPS_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "cs-oops-1", "topic": "oops",
        "text": "What is the difference between a class and an object?",
        "key_points": [
            _kp("a class is a blueprint/template/definition",
                "a class defines the structure and behaviour something will have"),
            _kp("an object is a specific instance created from that class, with its own state",
                "an object is a concrete instantiation of a class"),
            _kp("multiple objects can be created from one class, each with independent data",
                "each object has its own copy of the instance fields"),
        ],
    },
    {
        "id": "cs-oops-2", "topic": "oops",
        "text": "What is encapsulation, and why is it useful?",
        "key_points": [
            _kp("bundles data and the methods that operate on it together",
                "combines state and behaviour into one unit"),
            _kp("restricts or hides direct access to internal state, e.g. via private fields with public "
                "getters/setters", "controls how outside code can read or change an object's data"),
            _kp("protects invariants and lets the internal implementation change without breaking external code",
                "decouples a class's public interface from its internal implementation"),
        ],
    },
    {
        "id": "cs-oops-3", "topic": "oops",
        "text": "What is inheritance, and what problem does it solve?",
        "key_points": [
            _kp("a child/derived class acquires the fields and methods of a parent/base class",
                "a subclass extends a superclass and gets its members"),
            _kp("lets common behaviour be written once and reused across related classes",
                "avoids duplicating shared code between similar classes"),
            _kp("a derived class can override or add behaviour on top of what it inherits",
                "the subclass can customize or extend inherited methods"),
        ],
    },
    {
        "id": "cs-oops-4", "topic": "oops",
        "text": "What is polymorphism? Give an example of how it shows up in code.",
        "key_points": [
            _kp("the same method call or interface behaves differently depending on the actual runtime type "
                "of the object", "one interface, many implementations, chosen at runtime"),
            _kp("commonly achieved through overriding a method in a subclass, or through a shared "
                "interface/abstract base class", "a subclass provides its own version of an inherited method"),
            _kp("lets calling code work with different types through one common interface without knowing "
                "the concrete type", "the caller doesn't need to know which specific subclass it's using"),
        ],
    },
    {
        "id": "cs-oops-5", "topic": "oops",
        "text": "What is abstraction, and how is it different from encapsulation?",
        "key_points": [
            _kp("abstraction hides implementation complexity and exposes only the relevant/essential "
                "behaviour -- what something does", "abstraction simplifies by showing only what matters"),
            _kp("encapsulation hides internal data/state and controls access to it -- how it's stored",
                "encapsulation is about protecting an object's internal state"),
            _kp("gives a concrete example that shows the distinction, e.g. a Shape interface exposing only "
                "area() (abstraction) while a BankAccount class hides its internal balance field behind "
                "methods (encapsulation)",
                "illustrates abstraction and encapsulation with a specific example rather than only defining "
                "them"),
        ],
    },
    {
        "id": "cs-oops-6", "topic": "oops",
        "text": "What is the difference between method overloading and method overriding?",
        "key_points": [
            _kp("in languages that support overloading, it's multiple methods with the same name but "
                "different parameter lists in the same class, resolved at compile time",
                "overloading differs by signature, not behaviour",
                "correctly notes that a language like Python doesn't have true method overloading (a later "
                "definition simply replaces an earlier one), which is also an accurate answer"),
            _kp("overriding is a subclass redefining a method with the same signature inherited from its "
                "parent, resolved at runtime based on the actual object type",
                "overriding replaces the parent's implementation with the subclass's own"),
            _kp("overloading is about having multiple versions of a method; overriding is about replacing "
                "inherited behaviour", "they happen at different times: compile time vs runtime"),
        ],
    },
    {
        "id": "cs-oops-7", "topic": "oops",
        "text": "What is a constructor, and when is it called?",
        "key_points": [
            _kp("a special method used to initialize a newly created object",
                "sets up an object's initial state when it's created"),
            _kp("it is called automatically when an object is instantiated",
                "it runs as part of creating a new instance, without being explicitly invoked"),
            _kp("it can take parameters to set up the object's initial fields",
                "a constructor can be given arguments used to initialize state"),
        ],
    },
    {
        "id": "cs-oops-8", "topic": "oops",
        "text": "What is the difference between an abstract class and an interface?",
        "key_points": [
            _kp("an abstract class can have both implemented (concrete) methods and unimplemented ones, and "
                "can hold state/fields", "an abstract class may provide default behaviour and store data"),
            _kp("an interface is mainly a contract of method signatures with no instance state (newer "
                "languages allow default/implemented methods on an interface)",
                "an interface is primarily a signature contract, even though some modern languages let it "
                "include default method bodies; it still can't hold instance fields"),
            _kp("a class can usually inherit from only one abstract/base class but can implement multiple "
                "interfaces", "single inheritance of a base class vs multiple interface implementation"),
        ],
    },
    {
        "id": "cs-oops-9", "topic": "oops",
        "text": "What is the difference between a static (class) member and an instance member?",
        "key_points": [
            _kp("a static member belongs to the class itself and is shared across all instances",
                "there's only one copy of a static field, shared by every object"),
            _kp("an instance member belongs to a specific object, and each object has its own copy of it",
                "each instance gets its own independent value for an instance field"),
            _kp("a static member can usually be accessed without creating an object; an instance member "
                "needs an object to exist first", "you can call a static method without instantiating the class"),
        ],
    },
]

# ---- SQL (10 questions: 6 conceptual + 4 query-writing) ---------------------
SQL_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "cs-sql-1", "topic": "sql", "kind": "concept",
        "text": "What is the difference between an INNER JOIN and a LEFT (OUTER) JOIN?",
        "key_points": [
            _kp("INNER JOIN returns only rows that have a matching row in both tables",
                "INNER JOIN keeps only matched rows from both sides"),
            _kp("LEFT JOIN returns all rows from the left/first table, with NULLs for the right table's "
                "columns when there's no match", "LEFT JOIN keeps every row from the left table regardless of a match"),
            _kp("gives a practical scenario where you'd prefer a LEFT JOIN over an INNER JOIN, e.g. listing "
                "every customer including ones who have placed no orders yet",
                "names a real situation where keeping unmatched left-side rows actually matters"),
        ],
    },
    {
        "id": "cs-sql-2", "topic": "sql", "kind": "concept",
        "text": "What is the difference between a primary key and a foreign key? And what do UNIQUE, "
                "NOT NULL and CHECK constraints each do?",
        "key_points": [
            _kp("a primary key uniquely identifies each row in its own table and cannot be NULL; a foreign "
                "key is a column (or columns) in one table that references a primary (or unique) key in "
                "another table",
                "a primary key is the table's unique non-null identifier, a foreign key points to a key in a "
                "different table"),
            _kp("UNIQUE enforces that a column's values are all distinct from each other (though, unlike a "
                "primary key, it may still allow NULLs depending on the database); NOT NULL simply disallows "
                "NULL values in a column",
                "UNIQUE stops duplicate values, NOT NULL stops missing values"),
            _kp("CHECK enforces an arbitrary condition on a column's value (e.g. age >= 0), and a foreign "
                "key constraint enforces referential integrity -- you can't insert a value that doesn't "
                "exist in the referenced table, or in some setups can't delete a referenced row",
                "CHECK validates a custom rule on the data, a foreign key constraint prevents orphaned "
                "references between tables"),
        ],
    },
    {
        "id": "cs-sql-3", "topic": "sql", "kind": "concept",
        "text": "What is the difference between WHERE, GROUP BY, and HAVING?",
        "key_points": [
            _kp("WHERE filters individual rows before any grouping or aggregation happens",
                "WHERE applies row-level filtering first"),
            _kp("GROUP BY groups rows that share the same value(s) in given columns, usually so aggregate "
                "functions like COUNT/SUM/AVG can be applied per group", "GROUP BY buckets rows for aggregation"),
            _kp("HAVING filters groups after aggregation, based on a condition on an aggregate value, which "
                "WHERE cannot reference", "HAVING can filter on COUNT(*) or SUM(...) directly, unlike WHERE"),
        ],
    },
    {
        "id": "cs-sql-4", "topic": "sql", "kind": "concept",
        "text": "What is the difference between DELETE, TRUNCATE, and DROP?",
        "key_points": [
            _kp("DELETE removes rows (optionally filtered with WHERE), is logged row-by-row, and can be "
                "rolled back in a transaction", "DELETE is a row-level operation that supports WHERE and rollback"),
            _kp("TRUNCATE removes all rows from a table at once, is typically faster and minimally logged, "
                "and usually can't be filtered with WHERE", "TRUNCATE wipes the whole table's data quickly"),
            _kp("DROP removes the entire table (or other object) definition itself, not just its data",
                "DROP deletes the table's structure, so it no longer exists at all"),
        ],
    },
    {
        "id": "cs-sql-5", "topic": "sql", "kind": "concept",
        "text": "What is an index, and what's the trade-off of adding one?",
        "key_points": [
            _kp("a data structure (commonly a B-tree) that lets the database find matching rows without "
                "scanning the whole table", "an index speeds up lookups by avoiding a full table scan"),
            _kp("speeds up reads/lookups and queries that filter, join, or sort on the indexed column(s)",
                "improves performance of SELECTs that use the indexed column"),
            _kp("adds overhead on writes, since INSERT/UPDATE/DELETE must also update the index, and uses "
                "extra storage", "indexes slow down writes a little and take extra disk space"),
        ],
    },
    {
        "id": "cs-sql-6", "topic": "sql", "kind": "concept",
        "text": "What is a subquery, and how is a correlated subquery different from a regular one?",
        "key_points": [
            _kp("a subquery is a query nested inside another query, often used in WHERE, SELECT, or FROM",
                "a subquery is a query inside a query"),
            _kp("a regular (non-correlated) subquery can run on its own and is evaluated once, independent "
                "of the outer query", "a non-correlated subquery doesn't depend on the outer query's rows"),
            _kp("a correlated subquery references a column from the outer query and is logically "
                "re-evaluated for each row the outer query processes",
                "a correlated subquery depends on, and re-runs per, each outer row"),
        ],
    },
    {
        "id": "cs-sql-q1", "topic": "sql", "kind": "query",
        "text": (
            "Given this schema and sample data:\n"
            "employees(id, name, salary, dept_id)\n"
            "1, Asha, 90000, 1\n2, Bilal, 85000, 1\n3, Chen, 85000, 2\n4, Deepa, 72000, 2\n\n"
            "Write a query that returns the second-highest salary. Walk me through the query you'd write."
        ),
        "schema_sql": ["CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, salary INTEGER, dept_id INTEGER)"],
        "sample_rows_sql": [
            "INSERT INTO employees VALUES (1,'Asha',90000,1)",
            "INSERT INTO employees VALUES (2,'Bilal',85000,1)",
            "INSERT INTO employees VALUES (3,'Chen',85000,2)",
            "INSERT INTO employees VALUES (4,'Deepa',72000,2)",
        ],
        "reference_query": "SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees)",
        "accepted_queries": [
            {"label": "subquery",
             "query": "SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees)"},
            {"label": "dense_rank",
             "query": "SELECT DISTINCT salary FROM (SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS rnk "
                      "FROM employees) WHERE rnk = 2"},
            {"label": "limit_offset",
             "query": "SELECT DISTINCT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1"},
        ],
        "expected_result": [(85000,)],
        "key_points": [
            _kp("correctly frames the goal as finding the highest salary that is strictly below the single "
                "highest salary -- the second-highest DISTINCT value, not just the second row",
                "wants the next distinct value down from the maximum"),
            _kp("uses a technique that isolates that value, e.g. a subquery comparing against the overall "
                "MAX, or sorting salaries descending and skipping/ranking past the top row",
                "either compares against the overall maximum directly, or sorts and skips the top entry"),
            _kp("uses a technique that is safe against a duplicated top salary BY CONSTRUCTION -- e.g. "
                "comparing against MAX() in a subquery, using DISTINCT, or RANK/DENSE_RANK -- rather than a "
                "plain OFFSET on non-distinct rows; this can be satisfied just by describing or writing a "
                "query that uses one of these techniques, without the candidate explicitly using the word "
                "'duplicate' or calling out the edge case in words",
                "the query itself naturally handles a tied highest salary, whether or not the candidate "
                "explicitly mentions that case out loud"),
        ],
    },
    {
        "id": "cs-sql-q2", "topic": "sql", "kind": "query",
        "text": (
            "Given this schema and sample data:\n"
            "employees(id, name, salary, dept_id)\n"
            "1, Asha, 90000, 1\n2, Bilal, 85000, 1\n3, Chen, 85000, 2\n4, Deepa, 72000, 2\n\n"
            "Write a query that lists each department id with its employee count, but only for departments "
            "with more than one employee."
        ),
        "schema_sql": ["CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, salary INTEGER, dept_id INTEGER)"],
        "sample_rows_sql": [
            "INSERT INTO employees VALUES (1,'Asha',90000,1)",
            "INSERT INTO employees VALUES (2,'Bilal',85000,1)",
            "INSERT INTO employees VALUES (3,'Chen',85000,2)",
            "INSERT INTO employees VALUES (4,'Deepa',72000,2)",
        ],
        "reference_query": "SELECT dept_id, COUNT(*) AS cnt FROM employees GROUP BY dept_id HAVING COUNT(*) > 1 ORDER BY dept_id",
        "accepted_queries": [
            {"label": "group_having",
             "query": "SELECT dept_id, COUNT(*) AS cnt FROM employees GROUP BY dept_id HAVING COUNT(*) > 1 ORDER BY dept_id"},
            {"label": "subquery_count",
             "query": "SELECT dept_id, cnt FROM (SELECT dept_id, COUNT(*) AS cnt FROM employees GROUP BY dept_id) t "
                      "WHERE cnt > 1 ORDER BY dept_id"},
        ],
        "expected_result": [(1, 2), (2, 2)],
        "key_points": [
            _kp("groups rows by department", "uses GROUP BY on dept_id"),
            _kp("uses COUNT to get the number of employees in each group", "counts rows per department"),
            _kp("filters groups (not individual rows) using HAVING, since the condition is on an aggregated "
                "value", "uses HAVING rather than WHERE because the condition is on COUNT(*)"),
        ],
    },
    {
        "id": "cs-sql-q3", "topic": "sql", "kind": "query",
        "text": (
            "Given this schema and sample data:\n"
            "employees(id, name, salary, dept_id)\n"
            "1, Asha, 90000, 1\n2, Bilal, 85000, 1\n3, Chen, 85000, 2\n4, Deepa, 72000, 2\n\n"
            "Write a query that returns the names of employees who earn more than the average salary of "
            "their own department."
        ),
        "schema_sql": ["CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, salary INTEGER, dept_id INTEGER)"],
        "sample_rows_sql": [
            "INSERT INTO employees VALUES (1,'Asha',90000,1)",
            "INSERT INTO employees VALUES (2,'Bilal',85000,1)",
            "INSERT INTO employees VALUES (3,'Chen',85000,2)",
            "INSERT INTO employees VALUES (4,'Deepa',72000,2)",
        ],
        "reference_query": (
            "SELECT e.name FROM employees e WHERE e.salary > "
            "(SELECT AVG(salary) FROM employees e2 WHERE e2.dept_id = e.dept_id) ORDER BY e.name"
        ),
        "accepted_queries": [
            {"label": "correlated_subquery",
             "query": "SELECT e.name FROM employees e WHERE e.salary > "
                      "(SELECT AVG(salary) FROM employees e2 WHERE e2.dept_id = e.dept_id) ORDER BY e.name"},
            {"label": "window_avg",
             "query": "SELECT name FROM (SELECT name, salary, AVG(salary) OVER (PARTITION BY dept_id) AS dept_avg "
                      "FROM employees) WHERE salary > dept_avg ORDER BY name"},
        ],
        "expected_result": [("Asha",), ("Chen",)],
        "key_points": [
            _kp("computes a department's average salary, e.g. with a correlated subquery or a window "
                "function", "finds each department's average salary"),
            _kp("compares each employee's own salary against their OWN department's average specifically, "
                "not one company-wide average", "the comparison is per-department, not company-wide"),
            _kp("returns only the matching employees' names (not all employees, and not extra columns like "
                "salary or department id)", "selects just the name column, filtered to the matching rows"),
        ],
    },
    {
        "id": "cs-sql-q4", "topic": "sql", "kind": "query",
        "text": (
            "Given this schema and sample data:\n"
            "employees(id, name, manager_id)\n"
            "1, Asha, NULL\n2, Bilal, 1\n3, Chen, 1\n4, Deepa, 2\n\n"
            "Write a query that returns each employee's name along with their manager's name (NULL if they "
            "have no manager)."
        ),
        "schema_sql": ["CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, manager_id INTEGER)"],
        "sample_rows_sql": [
            "INSERT INTO employees VALUES (1,'Asha',NULL)",
            "INSERT INTO employees VALUES (2,'Bilal',1)",
            "INSERT INTO employees VALUES (3,'Chen',1)",
            "INSERT INTO employees VALUES (4,'Deepa',2)",
        ],
        "reference_query": (
            "SELECT e.name AS employee, m.name AS manager FROM employees e "
            "LEFT JOIN employees m ON e.manager_id = m.id ORDER BY e.id"
        ),
        "accepted_queries": [
            {"label": "self_left_join",
             "query": "SELECT e.name AS employee, m.name AS manager FROM employees e "
                      "LEFT JOIN employees m ON e.manager_id = m.id ORDER BY e.id"},
            {"label": "correlated_subquery",
             "query": "SELECT e.name, (SELECT m.name FROM employees m WHERE m.id = e.manager_id) "
                      "FROM employees e ORDER BY e.id"},
        ],
        "expected_result": [("Asha", None), ("Bilal", "Asha"), ("Chen", "Asha"), ("Deepa", "Bilal")],
        "key_points": [
            _kp("joins the employees table to itself (a self-join) to look up manager names",
                "performs a self-join on the employees table"),
            _kp("uses a LEFT JOIN, not an INNER JOIN, so employees with no manager still appear with NULL "
                "for the manager name", "keeps employees without a manager in the result, with a NULL manager"),
            _kp("correctly matches each employee's manager_id to the id of the manager row",
                "joins on manager_id = id between the two sides"),
        ],
    },
]

# ---- OS (5 questions) --------------------------------------------------------
OS_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "cs-os-1", "topic": "os",
        "text": "What is the difference between a process and a thread?",
        "key_points": [
            _kp("a process is an independent program in execution with its own memory address space",
                "a process has its own isolated memory"),
            _kp("a thread is a unit of execution within a process, and threads in the same process share "
                "that process's memory/address space", "threads of one process share the same memory space"),
            _kp("creating or switching threads is generally cheaper (lighter-weight) than creating or "
                "switching processes", "thread context switches are less costly than process context switches"),
        ],
    },
    {
        "id": "cs-os-2", "topic": "os",
        "text": "What is a deadlock, and what conditions typically need to hold for one to occur?",
        "key_points": [
            _kp("a deadlock is a state where two or more processes/threads are each waiting for a resource "
                "held by another, and none can proceed", "everyone involved is stuck waiting on everyone else"),
            _kp("conditions commonly cited include mutual exclusion, hold-and-wait, no preemption, and "
                "circular wait", "the four classic deadlock conditions"),
            _kp("can be addressed through prevention or avoidance strategies, e.g. enforcing a consistent "
                "lock-ordering, using timeouts, or a deadlock-detection algorithm",
                "mentions a way to prevent, avoid or detect deadlocks, such as always acquiring locks in the "
                "same order"),
        ],
    },
    {
        "id": "cs-os-3", "topic": "os",
        "text": "What is the difference between a process's virtual address space and physical memory, and "
                "what is the role of paging?",
        "key_points": [
            _kp("a process sees a virtual/logical address space that doesn't necessarily correspond "
                "directly to physical memory layout", "the addresses a process uses aren't real physical addresses"),
            _kp("the OS/MMU translates virtual addresses to physical addresses",
                "there's a translation step from virtual to physical memory"),
            _kp("paging divides memory into fixed-size pages/frames so a process's memory doesn't need to "
                "be contiguous in physical RAM, and allows pages to be swapped in/out as needed",
                "paging lets memory be managed in fixed-size chunks that can be moved or swapped"),
        ],
    },
    {
        "id": "cs-os-4", "topic": "os",
        "text": "What is CPU scheduling, and what's the difference between preemptive and non-preemptive "
                "scheduling?",
        "key_points": [
            _kp("CPU scheduling decides which ready process/thread gets to run on the CPU next",
                "scheduling picks the next process to run"),
            _kp("in preemptive scheduling, a running process can be interrupted and moved back to the ready "
                "state before it finishes, e.g. for a higher-priority process or a timer",
                "preemptive scheduling can forcibly take the CPU away from a running process"),
            _kp("in non-preemptive scheduling, once a process starts running it keeps the CPU until it "
                "finishes or voluntarily gives it up, e.g. for I/O",
                "non-preemptive scheduling only switches when the running process itself yields"),
        ],
    },
    {
        "id": "cs-os-5", "topic": "os",
        "text": "What is a race condition, and how can it be prevented?",
        "key_points": [
            _kp("a race condition occurs when the correctness of a result depends on the relative "
                "timing/interleaving of multiple threads/processes accessing shared data",
                "the outcome depends on which thread happens to run first"),
            _kp("it typically arises from an unprotected/unsynchronized critical section where shared data "
                "is read and written by multiple threads", "it comes from concurrent, unguarded access to shared state"),
            _kp("it can be prevented using synchronization mechanisms such as locks/mutexes, semaphores, or "
                "atomic operations that ensure mutual exclusion", "locks or mutexes can serialize access to the shared data"),
        ],
    },
]

BY_TOPIC: Dict[str, List[Dict[str, Any]]] = {"oops": OOPS_QUESTIONS, "sql": SQL_QUESTIONS, "os": OS_QUESTIONS}
