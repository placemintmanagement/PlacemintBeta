# -*- coding: utf-8 -*-
"""Commit-owned follow-ups for Dave's SQL bank (dave/cs.py's SQL_QUESTIONS,
reused read-only for Commit's CS-grilling weighted topic draw).

Gap found while building the test suite: SQL_QUESTIONS was authored for
Dave, which never asks SQL follow-ups, so it carries no `follow_ups` field
at all. Commit's CS-grilling rule (STATED) gives every question -- whichever
topic the weighted draw lands on -- exactly 2 fixed follow-ups, so a SQL
draw needs them too. Owner's call: author them here rather than skip
follow-ups for SQL draws, keeping every CS-grilling question uniform.

One entry per SQL_QUESTIONS id (10 keys, verified to match exactly).
dave/cs.py itself is never read from here beyond its public SQL_QUESTIONS
ids/text (for authoring context) and is never modified. server.py attaches
these onto a COPY of each SQL question dict at call time (see
_commit_cs_bank in server.py); the original SQL_QUESTIONS list is untouched.
"""
from typing import Any, Dict, List


def _kp(statement: str, *alternatives: str) -> Dict[str, Any]:
    return {"statement": statement, "alternatives": list(alternatives)}


def _fu(text: str, key_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"text": text, "key_points": key_points}


SQL_FOLLOWUPS: Dict[str, List[Dict[str, Any]]] = {
    "cs-sql-1": [
        _fu("What would a RIGHT JOIN give you instead, and how would you get the same result using only "
            "LEFT JOIN?",
            [_kp("a RIGHT JOIN keeps all rows from the right-hand table, with NULLs for the left table's "
                 "columns when there's no match",
                 "RIGHT JOIN is the mirror of LEFT JOIN -- it keeps everything from the table on the right"),
             _kp("swapping the order of the two tables and using LEFT JOIN produces the same result as a "
                 "RIGHT JOIN",
                 "a RIGHT JOIN can always be rewritten as a LEFT JOIN with the tables swapped")]),
        _fu("If you added a WHERE condition on a column from the right-hand table to this LEFT JOIN, what "
            "could go wrong?",
            [_kp("a WHERE filter on the right table's column can exclude the unmatched rows that the LEFT "
                 "JOIN was keeping, since those rows have NULL there and usually fail the comparison -- "
                 "effectively turning it back into an INNER JOIN",
                 "filtering on the right side's column in WHERE can silently drop the NULL rows LEFT JOIN "
                 "was supposed to preserve"),
             _kp("to keep the unmatched rows you'd need to explicitly allow for NULL in that condition, or "
                 "move the condition into the join's ON clause instead",
                 "the fix is handling NULL explicitly, e.g. in the ON clause rather than WHERE")]),
    ],
    "cs-sql-2": [
        _fu("Can a foreign key column contain NULL? What does that mean for the row?",
            [_kp("yes, a foreign key column can normally hold NULL unless it is additionally marked NOT "
                 "NULL, meaning that row simply has no reference to the other table yet",
                 "a FK column is nullable by default -- NULL just means 'no reference set'"),
             _kp("NULL doesn't violate referential integrity because there's no actual value to check "
                 "against the referenced table",
                 "the foreign key constraint has nothing to validate when the value is NULL")]),
        _fu("What happens if you try to insert a row whose foreign key value doesn't exist in the "
            "referenced table?",
            [_kp("the database rejects the insert with a referential integrity / foreign key constraint "
                 "violation error",
                 "the insert fails because the referenced row doesn't exist"),
             _kp("this is exactly what the foreign key constraint exists to prevent -- orphaned references "
                 "to rows that aren't really there",
                 "the constraint's purpose is blocking exactly this kind of dangling reference")]),
    ],
    "cs-sql-3": [
        _fu("Could you write WHERE COUNT(*) > 1 instead of using HAVING here? Why or why not?",
            [_kp("no -- WHERE is evaluated before grouping/aggregation happens, so COUNT(*) doesn't exist "
                 "yet at the point WHERE is applied",
                 "WHERE runs before GROUP BY, so it can't reference an aggregate that hasn't been computed"),
             _kp("HAVING is the clause designed to filter on aggregate values, evaluated after GROUP BY",
                 "HAVING exists specifically to filter grouped/aggregated results")]),
        _fu("If you need to filter out individual rows AND filter the groups by an aggregate condition in "
            "the same query, which clause does each job?",
            [_kp("row-level filtering (on columns of individual rows) goes in WHERE, applied before grouping",
                 "WHERE handles the per-row filter"),
             _kp("the aggregate/group-level condition goes in HAVING, applied after grouping",
                 "HAVING handles the per-group filter on the aggregated value")]),
    ],
    "cs-sql-4": [
        _fu("If you need to remove 90% of a table's rows but keep the table's definition and be able to "
            "roll back if something goes wrong, which of DELETE, TRUNCATE or DROP would you use, and why?",
            [_kp("DELETE with a WHERE clause, because it's the one of the three that supports filtering "
                 "which rows to remove and can be rolled back inside a transaction",
                 "DELETE is the right tool here because it's filterable and transactional"),
             _kp("TRUNCATE and DROP are ruled out: TRUNCATE generally can't be filtered the same way and "
                 "DROP removes the table's structure entirely, not just some of its rows",
                 "TRUNCATE wipes everything and DROP removes the table itself, so neither fits a partial, "
                 "reversible delete")]),
        _fu("Does TRUNCATE let you filter which rows get removed? What follows from that?",
            [_kp("no, TRUNCATE removes all rows in the table at once and generally cannot take a WHERE "
                 "clause",
                 "TRUNCATE is all-or-nothing -- it clears the whole table"),
             _kp("so if only some rows need to go, TRUNCATE is the wrong tool -- DELETE with a WHERE clause "
                 "is what allows a filtered removal",
                 "a partial removal has to be done with DELETE, not TRUNCATE")]),
    ],
    "cs-sql-5": [
        _fu("Would you add an index to a column that's updated constantly but rarely queried? Why or why "
            "not?",
            [_kp("probably not -- the index adds write overhead (every update also has to update the "
                 "index) without providing a matching read benefit, since the column is rarely queried",
                 "the write cost of maintaining the index wouldn't be paid back by read gains here"),
             _kp("an index is worth that trade-off when the column is actually read, filtered, joined, or "
                 "sorted on often enough to outweigh the extra write cost",
                 "indexes pay off when read/query frequency on that column is high enough")]),
        _fu("How does an index actually make a lookup faster, concretely?",
            [_kp("it lets the database jump directly to matching rows using the index's own data structure "
                 "(commonly a B-tree) instead of scanning every row in the table",
                 "the index structure avoids a full table scan by locating matches directly"),
             _kp("this avoids a linear full-table scan in favor of navigating the index's own structure "
                 "directly -- for a common index type like a B-tree, that means roughly logarithmic cost "
                 "for finding a specific key, rather than checking every row",
                 "it's the difference between checking every row and navigating a structured lookup, "
                 "roughly O(log n) for a B-tree rather than O(n)")]),
    ],
    "cs-sql-6": [
        _fu("If a correlated subquery references a column from the outer query, can you run that subquery "
            "by itself, on its own?",
            [_kp("generally no -- it depends on the specific row currently being processed by the outer "
                 "query, so outside that context it has no value to reference for the outer column",
                 "a correlated subquery needs the outer row's value, so it can't stand alone"),
             _kp("a non-correlated subquery, by contrast, is self-contained and can run independently on "
                 "its own",
                 "a non-correlated subquery doesn't need anything from the outer query to execute")]),
        _fu("Why might a correlated subquery tend to be slower than an equivalent rewrite using a join on "
            "the same tables?",
            [_kp("because it is conceptually (and often literally) re-evaluated once per row the outer "
                 "query processes, rather than being computed just once",
                 "it effectively repeats the subquery's work for every outer row"),
             _kp("a join-based rewrite usually lets the database process the data in a single combined "
                 "pass instead of repeating a subquery per row",
                 "joins tend to let the database combine the data once rather than row by row")]),
    ],
    "cs-sql-q1": [
        _fu("What would your query return if two employees were tied for the single highest salary? Would "
            "it still be correct?",
            [_kp("a subquery comparing against MAX(), or a window function like DENSE_RANK, still "
                 "correctly returns the single next-highest DISTINCT salary even when the top salary is "
                 "duplicated",
                 "the subquery/rank-based approaches handle a tied top salary correctly by construction"),
             _kp("a naive ORDER BY salary DESC LIMIT 1 OFFSET 1 would incorrectly return the duplicated top "
                 "salary itself in that tied case, instead of the true second-highest distinct value",
                 "a plain OFFSET-based query breaks when the highest salary is duplicated")]),
        _fu("Could you solve this with a window function instead of a subquery? Which one, and how?",
            [_kp("yes -- DENSE_RANK() (or RANK()) ordered by salary descending assigns rank 2 to the "
                 "second-highest distinct salary",
                 "a ranking window function ordered by salary descending gives the second-highest its own "
                 "rank"),
             _kp("you then filter the ranked result down to the row(s) where that rank equals 2",
                 "the final step is selecting where the computed rank is 2")]),
    ],
    "cs-sql-q2": [
        _fu("What would change in your query if you instead wanted departments with more than one employee "
            "AND an average salary above 80000?",
            [_kp("add the second condition into the same HAVING clause (e.g. combined with AND), since both "
                 "are conditions on the aggregated group",
                 "both conditions belong together in HAVING because both reference aggregated values"),
             _kp("COUNT(*) > 1 and AVG(salary) > 80000 both have to be evaluated after grouping, not in "
                 "WHERE, since WHERE runs before the aggregation exists",
                 "neither condition could go in WHERE because both depend on the aggregated group")]),
        _fu("If you also wanted this result sorted by employee count, descending, where would you add that?",
            [_kp("add ORDER BY cnt DESC (or ORDER BY COUNT(*) DESC) at the end of the query, after GROUP BY "
                 "and HAVING",
                 "the sort goes in a trailing ORDER BY clause"),
             _kp("ORDER BY is applied after grouping and the HAVING filter, to sort the already-filtered "
                 "final result rows",
                 "ordering happens last, once the groups are already formed and filtered")]),
    ],
    "cs-sql-q3": [
        _fu("Why can't you just compare against one overall company-wide average instead of each "
            "employee's own department average?",
            [_kp("the question specifically asks for employees who beat their OWN department's average, "
                 "and that average can differ substantially between departments",
                 "the comparison has to be per-department because department averages aren't the same"),
             _kp("a single company-wide average would misclassify employees in a high-paying department as "
                 "'below average', or employees in a low-paying department as 'above average', relative to "
                 "their actual department",
                 "a company-wide average gives the wrong comparison baseline for employees in an "
                 "unusually high- or low-paying department")]),
        _fu("Could this be rewritten using a window function instead of a correlated subquery? What would "
            "that look like?",
            [_kp("yes -- AVG(salary) OVER (PARTITION BY dept_id) computes each department's average "
                 "without needing a correlated subquery",
                 "a window function partitioned by department can compute the same per-department average"),
             _kp("you then filter to the rows where that employee's own salary is greater than the computed "
                 "per-department average value",
                 "the final filter compares each row's salary against its own partition's average")]),
    ],
    "cs-sql-q4": [
        _fu("Why does using an INNER JOIN instead of LEFT JOIN here cause a problem, specifically for Asha?",
            [_kp("Asha has no manager (her manager_id is NULL), so an INNER JOIN would find no matching "
                 "row for her on the right side and she would be dropped from the result entirely",
                 "an INNER JOIN would exclude Asha because there's no manager row to match her NULL "
                 "manager_id"),
             _kp("LEFT JOIN keeps her row in the result and simply shows NULL for the manager name instead "
                 "of excluding her",
                 "LEFT JOIN preserves employees with no manager, showing NULL rather than dropping them")]),
        _fu("What makes this query a 'self-join' rather than an ordinary join between two different tables?",
            [_kp("both sides of the join are the same employees table, just referenced twice under "
                 "different aliases (e.g. e and m)",
                 "it's one table joined to itself using two different aliases"),
             _kp("the join relates rows within that same table to each other -- each employee row to "
                 "another row in that same table representing their manager",
                 "it's used to connect an employee row to its own manager's row, both living in the same "
                 "table")]),
    ],
}
