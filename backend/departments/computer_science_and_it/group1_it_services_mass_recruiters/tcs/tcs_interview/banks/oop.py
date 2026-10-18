# -*- coding: utf-8 -*-
"""TCS Technical-round OOP question bank.

# SEED CONTENT: this is a small, hand-written STARTING set (4 questions),
not a production-complete bank. Dave's own OOPS_QUESTIONS (capgemini/
capgemini_interview/dave/cs.py) has 9 items for a 1-2-question-per-sitting
draw; this bank needs roughly the same per-tier draw depth (Prime draws up
to 2) and the same repeat-attempt-variety ratio, so production should grow
this to at least 10-12 items. Content here is freshly written for TCS (not
copied from Dave's bank), though the *topics* naturally overlap (OOP
fundamentals are OOP fundamentals) -- see tcs_interview/core.py's module
docstring for the "adapt the shape, not the words" reuse decision.

Each entry: {id, topic, difficulty ("ninja"|"digital"|"prime" -- the LOWEST
tier this question is suitable for; a higher tier may still draw a
lower-difficulty item if the pool is short), text, key_points}.
"""
from typing import Any, Dict, List

from ._kp import kp

OOP_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-oop-1", "topic": "oop", "difficulty": "ninja",
        "text": "What are the four main pillars of object-oriented programming, and can you briefly describe one of them?",
        "key_points": [
            kp("names at least two of encapsulation, abstraction, inheritance, polymorphism",
               "lists the core OOP principles"),
            kp("gives a correct, non-trivial description of at least one of them",
               "explains what one of the named pillars actually means, not just the name"),
        ],
    },
    {
        "id": "tcs-oop-2", "topic": "oop", "difficulty": "ninja",
        "text": "What is the difference between method overloading and method overriding?",
        "key_points": [
            kp("overloading is same method name with a different parameter list, resolved at compile time",
               "overloading is static/compile-time polymorphism"),
            kp("overriding is a subclass redefining a method it inherits, resolved at runtime",
               "overriding is dynamic/runtime polymorphism, needs an inheritance relationship"),
        ],
    },
    {
        "id": "tcs-oop-3", "topic": "oop", "difficulty": "digital",
        "text": "What is an abstract class, and how is it different from an interface?",
        "key_points": [
            kp("an abstract class can have both implemented and unimplemented (abstract) methods",
               "an abstract class may contain concrete method bodies"),
            kp("an interface (classically) only declares method signatures, no implementation",
               "an interface is a pure contract of what a class must provide"),
            kp("a class can implement multiple interfaces but typically extends only one abstract/base class",
               "multiple inheritance of behaviour is usually only possible via interfaces, not abstract classes"),
        ],
    },
    {
        "id": "tcs-oop-4", "topic": "oop", "difficulty": "prime",
        "text": "Why would you choose composition over inheritance when designing two related classes? Give a concrete example.",
        "key_points": [
            kp("inheritance creates a tight 'is-a' coupling that can break if the hierarchy doesn't hold cleanly",
               "deep inheritance hierarchies become fragile to change"),
            kp("composition ('has-a') lets behaviour be reused and swapped more flexibly, without the rigid hierarchy",
               "composition favors flexibility and loose coupling"),
            kp("gives a concrete, specific example (not just the abstract rule) showing composition solving a real design problem",
               "illustrates the point with a named class relationship, not only theory"),
        ],
    },
]
