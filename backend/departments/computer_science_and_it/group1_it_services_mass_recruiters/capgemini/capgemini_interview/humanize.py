# -*- coding: utf-8 -*-
"""Humanizer for the Capgemini interviews (Spark, Dave, Commit) -- FEATURE A.

Pure module: no import from server.py, no database, no clock, no LLM call.
Everything here is either a constant line/line-set or a small rule-based
function operating on inputs the caller already has (rng, previous line,
deadline/now, the candidate's raw answer text). server.py calls into this
module; this module never calls back into server.py.

Tags on every constant/choice below:
  STATED       -- given directly in the humanizer spec.
  INTERPOLATED -- my choice to fill a gap in the spec; pending the owner's
                  review (flagged individually below).

HUMANIZE_ENABLED is read by server.py from an environment variable (not
here, to keep this module free of os/env access) and defaults OFF; every
function below is pure and has no opinion about whether the flag is on.
"""
import random
import re
from typing import Dict, List, Optional

# ---- Persona ----------------------------------------------------------------
# STATED: a constant name and label; the UI shows a small "AI interviewer"
# tag; no claim to be human.
PERSONA_NAME = "Priya"
PERSONA_LABEL = "Capgemini interview panel (AI)"
PERSONA_DISPLAY = f"{PERSONA_NAME} - {PERSONA_LABEL}"
AI_INTERVIEWER_TAG = "AI interviewer"  # INTERPOLATED: exact UI tag text

# ---- Neutral acknowledgements ------------------------------------------------
# STATED: 10-15 short lines, chosen by code from a seeded RNG, never the same
# as the previous one, NEVER selected or influenced by the answer's grade or
# content (enforced structurally: the picker function below takes no grade/
# flags/answer-text parameter at all). No praise.
NEUTRAL_ACKNOWLEDGEMENTS: List[str] = [
    "Okay, got it.",
    "Thanks for walking me through that.",
    "Alright, noted.",
    "Okay, thank you.",
    "Got it, thanks.",
    "Mm-hmm, I hear you.",
    "Alright, thanks for that.",
    "Okay, understood.",
    "Noted, thank you.",
    "Alright, let's continue.",
    "Thanks, that's recorded.",
    "Okay, moving along.",
]  # STATED count (12, within 10-15); wording INTERPOLATED

ACK_PROBABILITY = 0.6  # INTERPOLATED (STATED "about 60 percent")


def maybe_acknowledgement(rng: random.Random, previous: Optional[str],
                          is_first_turn_after_intro: bool) -> Optional[str]:
    """Returns an acknowledgement line, or None, per the STATED rules. Takes
    no grade/flags/answer parameter by design -- it cannot be influenced by
    the answer's content or correctness even by accident."""
    if is_first_turn_after_intro:
        return None
    if rng.random() >= ACK_PROBABILITY:
        return None
    choices = [a for a in NEUTRAL_ACKNOWLEDGEMENTS if a != previous]
    return rng.choice(choices)


# ---- Stage transitions -------------------------------------------------------
# STATED: 2-3 variants per stage change (into DSA, the CS stage, HR), with an
# optional name mention. Keyed generically ("dsa"/"cs"/"hr") since the
# content itself is not tier-specific -- both Dave's cs_fundamentals and
# Commit's cs_grilling use the "cs" key (INTERPOLATED: shared generic key
# rather than one entry per tier's own stage name, since the transition line
# says nothing Dave- or Commit-specific).
STAGE_TRANSITIONS: Dict[str, List[str]] = {
    "dsa": [
        "Let's move to a coding problem now.",
        "Next, I'd like to walk through a problem with you.",
        "Let's switch gears to a data structures and algorithms question.",
    ],
    "cs": [
        "Let's switch to some core CS fundamentals.",
        "Now I'd like to ask a few fundamentals questions.",
        "Let's shift to some computer-science basics for a bit.",
    ],
    "hr": [
        "Let's wrap up with a few general questions.",
        "Now for a handful of more general questions about you.",
        "Let's finish up with some HR-style questions.",
    ],
}
STAGE_TRANSITIONS_WITH_NAME: Dict[str, List[str]] = {
    "dsa": [
        "Alright {name}, let's move to a coding problem now.",
        "{name}, let's switch gears to a data structures and algorithms question.",
    ],
    "cs": [
        "Alright {name}, let's switch to some core CS fundamentals.",
        "{name}, let's shift to some computer-science basics for a bit.",
    ],
    "hr": [
        "Alright {name}, let's wrap up with a few general questions.",
        "{name}, let's finish up with some HR-style questions.",
    ],
}  # INTERPOLATED wording; STATED only that a name-mention variant should exist


def stage_transition_line(stage_key: str, rng: random.Random, previous: Optional[str],
                          name: Optional[str] = None) -> str:
    """One transition line for entering `stage_key` ("dsa"/"cs"/"hr"), never
    repeating `previous` back-to-back. `name` is optional; when given, a
    name-mention variant may be chosen (INTERPOLATED: 50/50 between the plain
    and name-mention pools when a name is available)."""
    pools = [STAGE_TRANSITIONS[stage_key]]
    if name:
        pools.append([v.format(name=name) for v in STAGE_TRANSITIONS_WITH_NAME[stage_key]])
    all_variants = [line for pool in pools for line in pool]
    choices = [v for v in all_variants if v != previous] or all_variants
    return rng.choice(choices)


# ---- Time awareness -----------------------------------------------------------
# STATED: one fixed line at named points, N computed from the server deadline.
def minutes_remaining(deadline_epoch: float, now: float) -> int:
    return max(0, round((deadline_epoch - now) / 60))


def time_remaining_line(minutes_left: int) -> str:
    return f"We have about {minutes_left} minutes left."  # STATED example wording


# ---- Clarification and pass handling (rule-based only, no model call) -------
# STATED trigger phrases for a clarification/repeat request.
CLARIFICATION_TRIGGERS = ("repeat", "pardon", "didn't understand", "did not understand",
                          "what do you mean", "rephrase", "come again", "say that again")
# INTERPOLATED guard: only treat short utterances as a clarification request --
# a long, substantive technical answer that happens to use the word "repeat"
# (e.g. describing a loop) should not be misread as "please repeat the
# question". MAX_CLARIFICATION_WORDS is a named constant so this guard is
# visible and adjustable, not a silent heuristic.
MAX_CLARIFICATION_WORDS = 12


def is_clarification_request(answer: str) -> bool:
    text = (answer or "").strip().lower()
    if not text or len(text.split()) > MAX_CLARIFICATION_WORDS:
        return False
    return any(trigger in text for trigger in CLARIFICATION_TRIGGERS)


# STATED pass phrases. INTERPOLATED guard: same rationale as above -- only a
# short utterance counts as a pass, so a substantive answer that happens to
# contain the word "pass" (e.g. "a two-pointer approach to pass through the
# array") is never misread as the candidate passing.
PASS_PHRASES = ("i don't know", "i dont know", "idk", "skip", "pass", "no idea",
               "not sure", "i'm not sure", "im not sure")
MAX_PASS_WORDS = 6
PASS_RESPONSE = "No problem, let's move on."  # STATED


def is_pass_phrase(answer: str) -> bool:
    text = (answer or "").strip().lower()
    text = re.sub(r"[^\w\s']", "", text)  # strip punctuation for matching only
    if not text or len(text.split()) > MAX_PASS_WORDS:
        return False
    words = set(text.split())
    for phrase in PASS_PHRASES:
        if " " in phrase:
            if phrase in text:
                return True
        elif phrase in words:
            return True
    return False


# ---- Rephrases, keyed by the underlying bank question's own id --------------
# STATED: banks are read-only, so rephrases live in this sibling mapping
# keyed by question id, one entry per fixed question (Dave's CS/HR/DSA
# banks, Commit's Java/OOPS banks and the SQL questions they share with
# Dave, Spark's own DSA bank, and the four fixed complexity-question ids).
# INTERPOLATED wording throughout (the spec states the mechanism, not the
# text of each line). Fixed questions this map has no entry for (chiefly:
# the two per-question follow-up sub-prompts in Dave/Commit's CS stage,
# which have no bank id of their own) fall back to the caller re-sending the
# current question's own prompt text verbatim -- not a true rephrase, but it
# still answers "please repeat that" with no model call and no quota cost.
REPHRASES: Dict[str, str] = {
    # -- Dave CS bank: OOPS (9) --
    "cs-oops-1": "Let me ask it another way -- if a class is the blueprint, what exactly is an object?",
    "cs-oops-2": "Put differently -- what does encapsulation actually buy you in a design?",
    "cs-oops-3": "Let's rephrase that -- why would you reach for inheritance in the first place?",
    "cs-oops-4": "Different angle -- how would you explain polymorphism to someone who's never heard the term?",
    "cs-oops-5": "Let me put it another way -- what's the actual distinction between abstraction and encapsulation?",
    "cs-oops-6": "Rephrasing -- overloading versus overriding, what sets them apart?",
    "cs-oops-7": "Let's try that differently -- what does a constructor do, and when does it run?",
    "cs-oops-8": "Another way to ask -- how would you tell an abstract class apart from an interface?",
    "cs-oops-9": "Let me rephrase -- static versus instance members, what's the real difference?",
    # -- Dave CS bank: SQL (10) -- also used by Commit's cs_grilling (same ids) --
    "cs-sql-1": "Put differently -- how does an INNER JOIN behave differently from a LEFT JOIN?",
    "cs-sql-2": "Let me break that question down differently -- primary vs foreign keys, and what UNIQUE, "
               "NOT NULL and CHECK each enforce.",
    "cs-sql-3": "Rephrasing -- how do WHERE, GROUP BY and HAVING each fit into a query?",
    "cs-sql-4": "Another way to put it -- what's different about DELETE, TRUNCATE and DROP?",
    "cs-sql-5": "Let's rephrase -- what is an index actually giving you, and what does it cost?",
    "cs-sql-6": "Put differently -- what makes a correlated subquery different from an ordinary one?",
    "cs-sql-q1": "Let me put that another way -- write me a query for the second-highest salary from that "
                "employees table.",
    "cs-sql-q2": "Rephrasing the task -- write a query giving each department's employee count, only for "
                "departments with more than one employee.",
    "cs-sql-q3": "Let's try that again -- write a query for employees earning above their own department's "
                "average salary.",
    "cs-sql-q4": "Put differently -- write a query pairing each employee with their manager's name, from that "
                "same employees table.",
    # -- Dave CS bank: OS (5) --
    "cs-os-1": "Rephrasing -- what actually separates a process from a thread?",
    "cs-os-2": "Let me ask that differently -- what is a deadlock, and what has to be true for one to happen?",
    "cs-os-3": "Put another way -- what's the relationship between virtual address space, physical memory, "
              "and paging?",
    "cs-os-4": "Rephrasing -- what does CPU scheduling do, and how do preemptive and non-preemptive differ?",
    "cs-os-5": "Let's try that differently -- what's a race condition, and how would you stop one from "
              "happening?",
    # -- Dave/Commit HR bank (18) --
    "hr-m1": "Put differently -- what's drawing you to {company} specifically?",
    "hr-m2": "Let me ask that another way -- what pulled you toward this field in the first place?",
    "hr-m3": "Rephrasing -- what gets you to actually push for your best work?",
    "hr-t1": "Put another way -- tell me about a time you delivered something as part of a team, and what "
            "you did.",
    "hr-t2": "Let me rephrase -- describe a disagreement with a teammate and how it got resolved.",
    "hr-t3": "Different way to ask -- tell me about a time a mistake of yours affected your team, and what "
            "you did next.",
    "hr-s1": "Rephrasing -- what would you call your biggest strength, and where has it actually helped?",
    "hr-s2": "Put differently -- how do you go about picking up a new skill or technology quickly?",
    "hr-s3": "Let me ask that another way -- what's a skill you're proud of, and how did you build it up?",
    "hr-c1": "Rephrasing -- where do you picture yourself professionally a few years from now?",
    "hr-c2": "Put another way -- what do you know about {company}'s work, and what part of it interests you?",
    "hr-c3": "Let me rephrase -- what kind of problems do you want to be working on in your career?",
    "hr-f1": "Different way to ask -- how do you react when priorities shift suddenly mid-task?",
    "hr-f2": "Rephrasing -- tell me about a time you had to adjust to a new team or way of working.",
    "hr-f3": "Put differently -- tell me about handling pressure or a tight deadline.",
    "hr-si1": "Let me ask that another way -- what would you do with an unclear deadline and no one around "
             "to clarify it?",
    "hr-si2": "Rephrasing -- tell me about a time something you built didn't work out, and what you did "
             "about it.",
    "hr-si3": "Put another way -- how would you handle disagreeing with a decision your manager made?",
    # -- Dave/Commit DSA bank (14) --
    "product-except-self": "Let's go back to that one -- build the array where each spot holds the product "
                           "of every other element, no division.",
    "search-rotated": "Rephrasing -- find the target's index in that rotated sorted array, in log n time.",
    "longest-palindromic": "Put differently -- what's the length of the longest palindrome sitting inside "
                           "that string?",
    "tree-diameter": "Let me ask that again -- what's the diameter of that binary tree, the longest path "
                     "between any two nodes?",
    "tree-kth-smallest-bst": "Rephrasing -- find the k-th smallest value in that BST.",
    "greedy-two-city-scheduling": "Put another way -- split those 2n people between the two cities for "
                                  "minimum total cost.",
    "greedy-min-platforms": "Let's try that differently -- how many platforms does that station need, at "
                            "minimum?",
    "greedy-jump-game-ii": "Rephrasing -- what's the fewest jumps to reach the last index in that array?",
    "graph-bipartite-check": "Put differently -- can that graph's nodes be split into two groups with no "
                             "edge inside a group?",
    "graph-rotten-oranges": "Let me ask that again -- how many minutes until every fresh orange in that grid "
                           "has rotted?",
    "dp-longest-increasing-subsequence": "Rephrasing -- what's the length of the longest strictly increasing "
                                         "subsequence in that array?",
    "dp-partition-equal-subset-sum": "Put another way -- can that array be split into two subsets with equal "
                                     "sums?",
    "dp-maximal-square": "Let's try that differently -- what's the area of the largest all-1s square in that "
                         "grid?",
    "tp-subarray-product-less-than-k": "Rephrasing -- how many contiguous subarrays have a product strictly "
                                       "under k?",
    # -- Spark's own DSA bank (15) --
    "contains-duplicate": "Put differently -- does any value in that array show up more than once?",
    "merge-sorted": "Let me rephrase -- merge those two sorted arrays into one sorted result.",
    "tree-level-order": "Rephrasing -- walk that binary tree level by level and print what you see.",
    "tree-symmetric": "Put another way -- is that binary tree a mirror image of itself?",
    "tree-balanced": "Let's try that differently -- is that binary tree height-balanced?",
    "tree-min-depth": "Rephrasing -- what's the shortest path from the root to any leaf in that tree?",
    "string-longest-common-prefix": "Put differently -- what's the longest prefix shared by all of those "
                                    "strings?",
    "string-word-pattern": "Let me ask that again -- does that sentence's word pattern actually match the "
                          "given pattern string?",
    "tp-remove-duplicates-sorted": "Rephrasing -- remove the duplicates from that sorted array, in place.",
    "first-unique-char": "Put another way -- what's the index of the first character in that string that "
                        "never repeats?",
    "valid-parentheses": "Let's try that differently -- are those brackets properly opened and closed in "
                        "order?",
    "intersection-unique": "Rephrasing -- what values appear in both of those arrays?",
    "middle-of-linked-list": "Put differently -- find the middle node of that linked list.",
    "can-attend-meetings": "Let me ask that again -- can one person actually attend every one of those "
                          "meetings?",
    "pair-with-sum-sorted": "Rephrasing -- do any two positions in that sorted array add up to the target?",
    # -- Commit's own Java bank (13) --
    "java-1": "Let me put that another way -- how do the JVM, JRE and JDK actually relate to each other?",
    "java-2": "Rephrasing -- why are Strings immutable, and what's this string pool thing?",
    "java-3": "Put differently -- what's actually different between == and .equals()?",
    "java-4": "Let me ask that again -- what's the contract between hashCode() and equals(), and what "
             "breaks if you violate it?",
    "java-5": "Rephrasing -- walk me through what actually happens inside a HashMap on put() and get().",
    "java-6": "Put another way -- when would you reach for a LinkedList over an ArrayList, and why?",
    "java-7": "Let's try that differently -- checked versus unchecked exceptions, what separates them?",
    "java-8": "Rephrasing -- final the keyword versus a finally block, how are they different?",
    "java-9": "Put differently -- what's the real difference between Comparable and Comparator?",
    "java-10": "Let me ask that again -- Runnable versus extending Thread, and what does synchronized "
              "actually do?",
    "java-11": "Rephrasing -- how does the JVM decide an object is ready to be garbage collected?",
    "java-12": "Put another way -- is Java pass-by-value or pass-by-reference, really?",
    "java-13": "Let's try that differently -- abstract class versus interface, especially now that "
              "interfaces can have default methods?",
    # -- Commit's own OOPS bank (9) --
    "commit-oops-1": "Rephrasing -- composition versus inheritance, how do you actually decide between them?",
    "commit-oops-2": "Put differently -- what is dynamic dispatch, and why does it matter for polymorphism?",
    "commit-oops-3": "Let me ask that again -- what's the risk with downcasting that upcasting doesn't have?",
    "commit-oops-4": "Rephrasing -- what's the diamond problem, and how do languages deal with it?",
    "commit-oops-5": "Put another way -- what do coupling and cohesion mean, and why do we want low "
                     "coupling, high cohesion?",
    "commit-oops-6": "Let's try that differently -- what do the Single Responsibility and Open/Closed "
                     "principles each actually mean?",
    "commit-oops-7": "Rephrasing -- what does the Liskov Substitution Principle say, with a classic example "
                     "of breaking it?",
    "commit-oops-8": "Put differently -- what do Interface Segregation and Dependency Inversion each mean?",
    "commit-oops-9": "Let me ask that again -- association, aggregation and composition, how are they "
                     "different?",
    # -- Fixed complexity questions (Dave + Commit each use their own client-facing id "
    # for the same underlying text) --
    "dave-time-complexity": "Put differently -- what's the time complexity of the solution you just walked "
                            "through?",
    "commit-time-complexity": "Put differently -- what's the time complexity of the solution you just "
                              "walked through?",
    "dave-space-complexity": "Rephrasing -- and what's the space complexity of that same solution?",
    "commit-space-complexity": "Rephrasing -- and what's the space complexity of that same solution?",
}


def rephrase_for(question_id: str, fallback_prompt: str, company: Optional[str] = None) -> str:
    """The stored rephrase for `question_id`, or `fallback_prompt` verbatim if
    this id has no entry (see the module-level note above)."""
    line = REPHRASES.get(question_id)
    if line is None:
        return fallback_prompt
    if company and "{company}" in line:
        return line.format(company=company)
    return line


# ---- Idle prompt --------------------------------------------------------------
# STATED: frontend sends an idle event after 90s without input; server replies
# with this fixed line, at most once per question, never under 2 minutes left.
IDLE_SECONDS = 90  # STATED
IDLE_LINE = "Take your time. Would you like me to repeat the question?"  # STATED
IDLE_MIN_REMAINING_SECONDS = 120  # STATED ("never when under 2 minutes remain")
