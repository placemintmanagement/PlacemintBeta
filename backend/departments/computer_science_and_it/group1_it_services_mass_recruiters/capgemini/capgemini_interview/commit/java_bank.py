# -*- coding: utf-8 -*-
"""Commit interview Java question bank (Capgemini Commit tier only).

13 questions (STATED range: 12-14), one per topic in the owner's list: JVM/
JRE/JDK; String immutability and the pool; == vs equals; the hashCode/equals
contract; HashMap internals; ArrayList vs LinkedList; checked vs unchecked
exceptions; final/finally; Comparable vs Comparator; Thread vs Runnable and
synchronized; garbage collection; pass-by-value; abstract class vs interface
(including default methods).

Fixed questions, no live follow-up writing -- the model only grades (STATED:
"No model-written questions"). Each question has 3-4 key_points, phrased as
statements a candidate could be quoted saying, plus exactly 2 FIXED
follow-ups (a depth ladder), each with its own 2-3 key_points -- same
_kp()/alternatives pattern as dave/cs.py, reused unchanged (grading accepts
a correct point in the candidate's own words; `alternatives` are examples,
not an exhaustive whitelist).

Code snippets inside key points/alternatives are plain-text references to
real Java semantics; the ones worth actually compiling and running live in
the scratchpad verification script (see the build report), not here -- this
module stays pure data, importable without a JDK.
"""
from typing import Any, Dict, List


def _kp(statement: str, *alternatives: str) -> Dict[str, Any]:
    return {"statement": statement, "alternatives": list(alternatives)}


def _fu(text: str, key_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"text": text, "key_points": key_points}


JAVA_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "java-1", "topic": "java",
        "text": "What is the difference between the JVM, the JRE, and the JDK?",
        "key_points": [
            _kp("the JVM (Java Virtual Machine) is the runtime engine that executes compiled bytecode, and is "
                "what makes Java platform-independent",
                "the JVM runs .class bytecode and abstracts away the underlying OS/hardware"),
            _kp("the JRE (Java Runtime Environment) bundles the JVM with the standard library/class files "
                "needed to RUN a Java program, but not the tools to develop one",
                "the JRE is the JVM plus the core libraries needed to execute programs"),
            _kp("the JDK (Java Development Kit) bundles the JRE with development tools such as the compiler "
                "(javac), debugger, and other tooling needed to WRITE and BUILD Java programs",
                "the JDK is the JRE plus compiler/dev tools; you need it to compile, not just to run"),
        ],
        "follow_ups": [
            _fu("If you only need to run a Java application on a server, which of these do you actually need "
                "installed, and why?",
                [_kp("the JRE is sufficient to run a compiled application, since running doesn't require "
                     "compiling source code",
                     "you don't need the JDK's compiler/dev tools just to execute an already-built program"),
                 _kp("the JDK would only be needed if that machine also has to compile Java source itself",
                     "the full JDK matters for building/development, not for pure execution")]),
            _fu("How does compiling to bytecode and running on a JVM give Java its \"write once, run "
                "anywhere\" property?",
                [_kp("javac compiles Java source into platform-independent bytecode (.class files), not "
                     "directly into native machine code for one specific OS/CPU",
                     "the compiler output isn't tied to any particular operating system"),
                 _kp("any machine with a JVM for its platform can run that same bytecode, so the same compiled "
                     "output runs unchanged across different operating systems",
                     "the JVM is the platform-specific piece; the bytecode above it is not")]),
        ],
    },
    {
        "id": "java-2", "topic": "java",
        "text": "Why are Strings immutable in Java, and what is the string pool?",
        "key_points": [
            _kp("a String's internal character data cannot be changed after it's created -- any operation "
                "that looks like it modifies a String (concatenation, substring, etc.) actually creates and "
                "returns a NEW String object",
                "String methods that seem to edit a string actually return a different object"),
            _kp("immutability makes Strings safe to share across threads without synchronization, safe to use "
                "as hash keys (the hash code can be cached since it never changes), and safer when used in "
                "security-sensitive contexts since a reference can't be mutated out from under other code",
                "benefits include thread-safety, stable hash codes for use in HashMap/HashSet, and security"),
            _kp("the string pool (string intern pool) is a special memory area where the JVM stores one "
                "shared copy of each distinct string literal, so that identical literals can reuse the same "
                "object instead of each allocating a new one",
                "literal strings are interned/deduplicated in a shared pool rather than each being a fresh "
                "object"),
        ],
        "follow_ups": [
            _fu("If you write `String a = \"hi\"; String b = \"hi\";`, do `a` and `b` refer to the same "
                "object in memory? What if you instead write `String c = new String(\"hi\");`?",
                [_kp("`a` and `b` refer to the SAME object, because both literals are looked up in/interned "
                     "into the same string pool",
                     "string literals with identical content share one pooled instance"),
                 _kp("`c` (created with `new String(...)`) is a DIFFERENT object on the heap, even though its "
                     "content is equal, because `new` explicitly forces a fresh allocation outside the pool",
                     "`new String(...)` bypasses the pool and always creates a distinct object")]),
            _fu("Since Strings are immutable, why does the standard library provide StringBuilder/"
                "StringBuffer, and when would you reach for one instead of plain String concatenation?",
                [_kp("StringBuilder is a mutable character sequence, so it can be modified/appended to in "
                     "place without allocating a brand-new object on every change",
                     "StringBuilder avoids creating a new String object for every intermediate edit"),
                 _kp("this matters for performance when building a string incrementally in a loop, since "
                     "repeated immutable-String concatenation would otherwise allocate and discard many "
                     "intermediate String objects",
                     "StringBuilder is preferred for loops/heavy concatenation to avoid repeated allocation")]),
        ],
    },
    {
        "id": "java-3", "topic": "java",
        "text": "What is the difference between == and .equals() in Java?",
        "key_points": [
            _kp("== compares reference equality for objects -- whether two variables point to the exact same "
                "object in memory",
                "== checks if both references point to the identical object"),
            _kp(".equals() is a method that compares logical/value equality -- whether two objects are "
                "considered equal in content, as defined by that class's own equals() implementation",
                "equals() compares content/meaning, as the class defines it"),
            _kp("for primitive types, == compares the actual values directly (there's no object identity "
                "concept for primitives)",
                "primitives don't have equals(); == is the only comparison and it compares values"),
        ],
        "follow_ups": [
            _fu("If a class doesn't override equals(), what does calling .equals() on its instances actually "
                "do?",
                [_kp("it falls back to Object's default equals(), which just does a == reference comparison",
                     "without an override, equals() behaves exactly like =="),
                 _kp("so two separately created instances with identical field values would be reported as "
                     "NOT equal, since there's no content comparison without an override",
                     "two objects with the same data are still unequal by default, since only reference "
                     "identity is checked")]),
            _fu("Given two Integer objects created with `new Integer(200)` each holding the value 200, what "
                "would == return, and why might this be different for small values like 100?",
                [_kp("== on two separately `new`-created wrapper objects returns false, since they are "
                     "distinct objects even with equal values",
                     "`new Integer(...)` always allocates a fresh object, so == is false between two of them"),
                 _kp("Java caches/interns boxed Integer values in a small range (commonly -128 to 127) via "
                     "autoboxing, so two autoboxed Integers in that range can be == true, while values outside "
                     "that cached range are not guaranteed to be",
                     "Integer caching for small values can make == true for autoboxed values in that range, "
                     "which is a classic gotcha")]),
        ],
    },
    {
        "id": "java-4", "topic": "java",
        "text": "What is the contract between hashCode() and equals(), and what goes wrong if you break it?",
        "key_points": [
            _kp("if two objects are equal according to equals(), they MUST return the same hashCode()",
                "equal objects are required to have equal hash codes"),
            _kp("the reverse is not required: two objects can have the same hashCode() without being equal "
                "(a hash collision is allowed)",
                "equal hash codes don't imply the objects are equal -- collisions are fine"),
            _kp("if you override equals() without also overriding hashCode() consistently (or vice versa), "
                "the contract is broken and hash-based collections like HashMap/HashSet can behave "
                "incorrectly -- e.g. a key that is .equals() to a stored key might not be found, because it "
                "lands in the wrong bucket",
                "breaking the contract causes lookups/containment checks in hash-based collections to fail "
                "even when equals() would say the objects match"),
        ],
        "follow_ups": [
            _fu("Concretely, if you put an object into a HashSet and then its hashCode() changes afterward "
                "(because a field it's based on was mutated), what happens when you try to find it again?",
                [_kp("the object was placed into a bucket based on its ORIGINAL hash code, so searching with "
                     "the new hash code looks in the wrong bucket and the object effectively becomes "
                     "unfindable/\"lost\" in the set, even though it's technically still there",
                     "a mutated hash code after insertion causes the entry to not be found on lookup since "
                     "the bucket no longer matches"),
                 _kp("the object is still physically present in the set's internal storage (it isn't removed "
                     "or garbage collected), it's just unreachable through contains()/remove() lookups with "
                     "its new hash code",
                     "the entry isn't deleted -- it's just practically unreachable by lookup afterward")]),
            _fu("Why is it recommended to use only immutable fields when computing hashCode(), especially for "
                "objects used as HashMap keys?",
                [_kp("if the fields used in hashCode() can change after the object is stored as a key, the "
                     "same lost-bucket problem occurs -- immutability guarantees the hash code (and therefore "
                     "the bucket) stays stable for the object's lifetime",
                     "using immutable fields keeps the hash code -- and thus the bucket placement -- stable "
                     "for as long as the object is used as a key"),
                 _kp("this is a specific instance of the general hashCode/equals contract rule, applied to "
                     "the key-stability problem rather than just the equals-mismatch problem",
                     "it's the same underlying contract concern, but focused on keeping a key's hash stable "
                     "over its lifetime as a map key")]),
        ],
    },
    {
        "id": "java-5", "topic": "java",
        "text": "How does a HashMap work internally -- what happens on put() and get()?",
        "key_points": [
            _kp("internally it's backed by an array of buckets; a key's hashCode() is used (often after "
                "additional hash-spreading) to compute an index into that array, deciding which bucket the "
                "entry goes into",
                "the key's hash determines which bucket/array-slot an entry lands in"),
            _kp("when two different keys hash to the same bucket (a collision), that bucket holds multiple "
                "entries -- historically as a linked list, and in modern Java implementations a bucket that "
                "grows large enough converts to a balanced tree for faster lookups",
                "collisions are handled by chaining entries in a bucket (list, or a tree once a bucket is "
                "large enough in recent JVMs)"),
            _kp("get() recomputes the key's hash code to find the right bucket, then uses equals() to find "
                "the matching entry within that bucket (since multiple keys can share a bucket)",
                "lookup uses the hash to find the bucket, then equals() to pick the right entry inside it"),
        ],
        "follow_ups": [
            _fu("Why does a HashMap need BOTH a correct hashCode() and a correct equals() implementation on "
                "its keys to work correctly, not just one or the other?",
                [_kp("hashCode() is needed to find the right bucket at all; equals() is then needed to "
                     "correctly distinguish between different keys that happen to land in the same bucket",
                     "hashCode gets you to the right bucket, equals confirms it's actually the same key once "
                     "there"),
                 _kp("with only hashCode() and no correct equals(), the map couldn't reliably tell two "
                     "different keys in the same bucket apart, and with only equals() and no good hashCode() "
                     "every key could land in one bucket, degrading lookups toward O(n)",
                     "missing either one breaks either correctness (telling keys apart) or performance "
                     "(avoiding everything piling into one bucket)")]),
            _fu("What happens to a HashMap's internal array as more entries are added -- does it grow, and "
                "what's the cost of that?",
                [_kp("the internal array is resized (commonly doubled) once the number of entries crosses a "
                     "load-factor threshold relative to the array's capacity",
                     "the map rehashes/resizes to a bigger table once it gets sufficiently full"),
                 _kp("resizing requires rehashing and redistributing all existing entries into the new, "
                     "larger array, which is an expensive O(n) operation when it happens",
                     "a resize is costly since every existing entry has to be re-placed into the new table")]),
        ],
    },
    {
        "id": "java-6", "topic": "java",
        "text": "What is the difference between ArrayList and LinkedList, and when would you choose one over "
                "the other?",
        "key_points": [
            _kp("ArrayList is backed by a resizable array, so random access by index is O(1), but inserting "
                "or removing from the middle requires shifting elements, which is O(n)",
                "ArrayList gives fast indexed access but slow middle insert/remove"),
            _kp("LinkedList is backed by a doubly-linked list of nodes, so accessing an arbitrary index is "
                "O(n) (you have to walk the list), but inserting/removing at a KNOWN position (e.g. via an "
                "iterator, or at the head/tail) can be done in O(1) without shifting other elements",
                "LinkedList gives slow indexed access but fast insert/remove once you're already at the "
                "position"),
            _kp("prefer ArrayList for frequent random-access reads; consider LinkedList (or at least think "
                "twice before defaulting to ArrayList) when you're doing a lot of insertions/removals, "
                "especially at the ends, and don't need frequent indexed access",
                "the choice depends on whether the workload is read/index-heavy or insert/remove-heavy"),
        ],
        "follow_ups": [
            _fu("If you need to repeatedly add elements to the END of a growing list and also read by index "
                "often, which would you actually pick in practice, and why might ArrayList still win even "
                "though LinkedList is theoretically O(1) for insertion?",
                [_kp("ArrayList's amortized append (addAtEnd) is also effectively O(1) on average because of "
                     "how the backing array grows, so for end-appends plus frequent indexed reads, ArrayList "
                     "is usually the better practical choice",
                     "ArrayList append is amortized O(1) too, and it additionally keeps O(1) indexed access, "
                     "so it tends to win when both operations matter"),
                 _kp("LinkedList's O(1) insertion advantage only really applies at a position you already "
                     "have a direct reference/iterator to -- the indexed reads still cost it O(n) just to "
                     "walk to that position in the first place",
                     "LinkedList's cheap insertion doesn't help once you factor in the O(n) cost of reaching "
                     "an index by position")]),
            _fu("Why is removing an element from the middle of an ArrayList more expensive than from a "
                "LinkedList, mechanically?",
                [_kp("removing from the middle of an ArrayList requires shifting every subsequent element one "
                     "position to fill the gap, which touches O(n) elements",
                     "ArrayList removal shifts the remaining elements, costing O(n)"),
                 _kp("removing a node from a LinkedList (once you already have a reference/iterator to that "
                     "node) only requires re-pointing a couple of neighboring node links, with no shifting of "
                     "other elements",
                     "LinkedList removal at a known node just relinks pointers, independent of list size")]),
        ],
    },
    {
        "id": "java-7", "topic": "java",
        "text": "What is the difference between a checked exception and an unchecked exception in Java?",
        "key_points": [
            _kp("checked exceptions (subclasses of Exception other than RuntimeException) are checked by the "
                "compiler -- a method that can throw one must either catch it or declare it in its `throws` "
                "clause, or the code won't compile",
                "checked exceptions are enforced at compile time via catch-or-declare"),
            _kp("unchecked exceptions (RuntimeException and its subclasses, e.g. NullPointerException, "
                "ArrayIndexOutOfBoundsException) are NOT checked by the compiler -- you're not required to "
                "catch or declare them",
                "unchecked/runtime exceptions have no compile-time catch-or-declare requirement"),
            _kp("checked exceptions are generally meant for recoverable conditions the caller should "
                "reasonably anticipate and handle (e.g. a file not found), while unchecked exceptions "
                "typically represent programming errors or conditions not expected to be routinely handled",
                "the intended use is checked for expected/recoverable situations, unchecked for programmer "
                "errors or unexpected conditions"),
        ],
        "follow_ups": [
            _fu("Error is also a subclass of Throwable but is neither Exception's checked branch nor "
                "RuntimeException. Where does something like OutOfMemoryError fit into this picture, and "
                "should application code typically try to catch it?",
                [_kp("Error (and its subclasses like OutOfMemoryError, StackOverflowError) represents serious "
                     "problems that a normal application usually isn't expected to catch or recover from, "
                     "since they often indicate the JVM itself is in trouble",
                     "Errors are typically not meant to be caught/handled by ordinary application code"),
                 _kp("Error, like RuntimeException, is unchecked (not subject to the catch-or-declare rule), "
                     "even though it sits in its own separate branch of the Throwable hierarchy from "
                     "Exception/RuntimeException",
                     "Error is unchecked too, despite not actually being a RuntimeException itself")]),
            _fu("If a checked exception doesn't fit any of your method's existing `throws` declarations, what "
                "are your options, and what's the trade-off of wrapping it in an unchecked exception instead?",
                [_kp("you can add it to the method's `throws` clause (pushing the catch-or-declare obligation "
                     "up to the caller), catch and handle it locally, or wrap it in an unchecked exception "
                     "(e.g. a custom RuntimeException) and rethrow",
                     "the choices are: declare it, handle it, or wrap it as unchecked"),
                 _kp("wrapping it as unchecked avoids forcing every caller up the chain to declare/catch it, "
                     "but it also means callers can more easily forget to handle it at all, since the "
                     "compiler no longer enforces that",
                     "wrapping trades compiler-enforced handling for flexibility, at the risk of the error "
                     "being silently ignored by callers")]),
        ],
    },
    {
        "id": "java-8", "topic": "java",
        "text": "What is the difference between the `final` keyword and a `finally` block?",
        "key_points": [
            _kp("`final` is a modifier applied to a variable (making its reference/value unreassignable after "
                "initialization), a method (preventing it from being overridden), or a class (preventing it "
                "from being subclassed)",
                "final marks something as unmodifiable/unextendable, depending on whether it's on a "
                "variable, method, or class"),
            _kp("`finally` is a block attached to a try/catch statement that always runs after the try (and "
                "any catch) completes, whether or not an exception was thrown, typically used for cleanup",
                "finally is a guaranteed-to-run cleanup block tied to try/catch"),
            _kp("the two are unrelated keywords that happen to look similar -- one is about "
                "immutability/non-overridability/non-extensibility, the other is about guaranteed execution "
                "for cleanup", "they solve completely different problems despite the similar spelling"),
        ],
        "follow_ups": [
            _fu("If a try block returns a value AND the finally block also has a return statement, what "
                "happens?",
                [_kp("the finally block's return overrides/replaces the try block's return -- whatever "
                     "finally returns is what the method actually returns",
                     "a return in finally wins over a return in try, which is generally considered a "
                     "footgun/bad practice"),
                 _kp("the same silent-override behaviour applies to an exception too: a return (or another "
                     "exception) in finally can swallow an exception that was in the middle of propagating "
                     "out of the try/catch",
                     "finally can suppress an in-flight exception from try/catch, not just override a "
                     "return value")]),
            _fu("What is `finalize()`, and how is it different from both `final` and `finally`?",
                [_kp("finalize() is a method objects could historically override to run cleanup code before "
                     "the garbage collector reclaims them, called by the GC itself rather than deterministically "
                     "by the programmer",
                     "finalize() was a GC-invoked cleanup hook, unrelated to the final keyword or a finally "
                     "block"),
                 _kp("it's unreliable (timing isn't guaranteed, and it may never run at all) and is "
                     "deprecated/discouraged in modern Java in favor of try-with-resources or explicit close "
                     "methods",
                     "finalize() is considered deprecated/unreliable; try-with-resources is the modern "
                     "replacement for deterministic cleanup")]),
        ],
    },
    {
        "id": "java-9", "topic": "java",
        "text": "What is the difference between the Comparable and Comparator interfaces?",
        "key_points": [
            _kp("Comparable is implemented BY the class whose instances need a natural ordering -- it defines "
                "a single compareTo(other) method inside that class itself",
                "Comparable is implemented by the object's own class, defining its natural/default order"),
            _kp("Comparator is a SEPARATE object that defines an ordering externally, via a compare(a, b) "
                "method, without modifying the class being compared -- useful for sorting the same type in "
                "multiple different ways",
                "Comparator is an external, pluggable ordering, not tied to the class's own definition"),
            _kp("a class can implement Comparable only once (one natural order), but you can write as many "
                "different Comparators as you need for different sort criteria",
                "Comparable gives one natural order; Comparator lets you define many different orders"),
        ],
        "follow_ups": [
            _fu("If you want to sort a list of Employee objects by salary in one place and by name in "
                "another, without changing the Employee class itself, which of these two would you reach "
                "for, and why?",
                [_kp("Comparator, specifically because you need multiple different orderings for the same "
                     "class without baking one fixed order into the class via Comparable",
                     "Comparator lets you define salary-order and name-order separately, externally, for the "
                     "same class"),
                 _kp("you'd write two separate Comparator implementations (or lambdas), one per sort "
                     "criterion, and pass whichever one is needed into the sort call at each call site",
                     "each sort order becomes its own Comparator, chosen per call rather than fixed on the "
                     "class")]),
            _fu("What does compareTo() (or compare()) need to return, and what do a negative, zero, and "
                "positive result each mean?",
                [_kp("it returns a negative number if the first/this object should come before the other, "
                     "zero if they're considered equal in order, and a positive number if it should come "
                     "after", "negative = comes first, zero = equal ordering, positive = comes after"),
                 _kp("only the SIGN of the returned number matters for ordering purposes, not its exact "
                     "magnitude -- returning -1 versus -1000 has the same ordering meaning",
                     "the exact numeric value doesn't matter, only whether it's negative, zero, or positive")]),
        ],
    },
    {
        "id": "java-10", "topic": "java",
        "text": "What is the difference between implementing Runnable and extending Thread, and what does "
                "the `synchronized` keyword do?",
        "key_points": [
            _kp("extending Thread means your class IS-A Thread and directly overrides its run() method, "
                "which also uses up your one allowed superclass since Java doesn't support multiple "
                "inheritance of classes",
                "extending Thread ties up your single-inheritance slot on that class"),
            _kp("implementing Runnable means your class just provides a run() method and is passed to a "
                "Thread (or an executor) to be run, which is generally preferred since it keeps the class "
                "free to extend something else and separates \"the task\" from \"the thread that runs it\"",
                "implementing Runnable is the generally preferred approach since it doesn't consume your "
                "inheritance slot and decouples the task from the threading mechanism"),
            _kp("`synchronized` (on a method or a block) ensures that only one thread at a time can execute "
                "that method/block on a given object (or class, for static synchronized), by acquiring a "
                "lock/monitor, which prevents race conditions on shared state",
                "synchronized enforces mutual exclusion so only one thread can be in that critical section at "
                "a time"),
        ],
        "follow_ups": [
            _fu("If two threads both call a synchronized instance method on the SAME object, what happens? "
                "What if they call it on two DIFFERENT instances of the same class?",
                [_kp("on the SAME object, the second thread must wait until the first thread releases the "
                     "lock on that object before it can enter",
                     "synchronized on the same instance serializes access between threads sharing that "
                     "object"),
                 _kp("on two DIFFERENT instances, each object has its own independent lock, so both threads "
                     "can proceed concurrently without blocking each other",
                     "different instances have separate monitors, so synchronized on one doesn't block "
                     "threads using a different instance")]),
            _fu("What's a risk of using `synchronized` too liberally (e.g. synchronizing a very broad or "
                "frequently-called block)?",
                [_kp("it can hurt performance/throughput by serializing work that didn't actually need to be "
                     "mutually exclusive, since threads end up waiting unnecessarily",
                     "over-synchronizing reduces concurrency and can create a performance bottleneck"),
                 _kp("it can also contribute to deadlock risk if multiple synchronized blocks/locks are "
                     "acquired in inconsistent orders across different code paths",
                     "poorly structured synchronized blocks can lead to deadlocks between threads")]),
        ],
    },
    {
        "id": "java-11", "topic": "java",
        "text": "What is garbage collection in Java, and roughly how does the JVM decide an object can be "
                "collected?",
        "key_points": [
            _kp("garbage collection is the JVM automatically reclaiming memory used by objects that are no "
                "longer reachable/referenced by the running program, so the programmer doesn't have to "
                "manually free memory",
                "GC automatically frees memory for objects the program can no longer reach"),
            _kp("an object becomes eligible for collection once there are no more reachable references to it "
                "from any live thread's stack, static fields, or other GC roots -- reachability, not just a "
                "simple reference count, is what's actually tracked",
                "eligibility is based on reachability from GC roots, not merely whether a reference count "
                "hit zero"),
            _kp("the programmer doesn't control exactly WHEN collection happens (calling System.gc() is only "
                "a hint/suggestion to the JVM, not a guarantee)",
                "GC timing is managed by the JVM itself; System.gc() does not force immediate collection"),
        ],
        "follow_ups": [
            _fu("If two objects reference each other (A points to B, B points to A) but nothing else in the "
                "program references either of them, are they eligible for garbage collection?",
                [_kp("yes -- since reachability is tracked from GC roots outward, a cycle of objects that "
                     "isn't reachable from any root is still collectible, unlike a naive reference-counting "
                     "scheme which would get stuck on the mutual reference",
                     "a reference cycle unreachable from any GC root is still garbage-collectible, because "
                     "Java's GC isn't simple reference counting"),
                 _kp("this is precisely why Java's GC design is reachability-based (e.g. mark-and-sweep/"
                     "tracing) rather than pure reference counting -- reference counting alone cannot detect "
                     "and collect cycles like this",
                     "reachability-based tracing handles cycles correctly in a way plain reference counting "
                     "cannot")]),
            _fu("Why might a generational garbage collector treat recently-created objects differently from "
                "long-lived ones?",
                [_kp("most objects are observed to die young in typical programs, so generational collectors "
                     "focus frequent, cheap collection passes on a young/new-object area, and only "
                     "occasionally run more expensive collection on an old/long-lived area",
                     "generational GC exploits the fact that most objects become garbage quickly, so it "
                     "collects the young generation more often and cheaply"),
                 _kp("an object that survives enough young-generation collection cycles gets promoted/moved "
                     "to the old generation, on the assumption that it's likely to keep living for a while "
                     "longer",
                     "objects that keep surviving get promoted into the less-frequently-collected old "
                     "generation")]),
        ],
    },
    {
        "id": "java-12", "topic": "java",
        "text": "Is Java pass-by-value or pass-by-reference? Explain what actually happens when you pass an "
                "object to a method.",
        "key_points": [
            _kp("Java is always strictly pass-by-value -- there is no true pass-by-reference in Java",
                "every argument passed to a Java method is passed by value, with no exceptions"),
            _kp("for object arguments, what's actually copied by value is the REFERENCE (the pointer-like "
                "value) to the object, not the object itself -- so the method gets its own copy of the "
                "reference, but that copy still points to the same object on the heap",
                "the object reference itself is copied by value, while both the original and the copy point "
                "to the same underlying object"),
            _kp("this means a method CAN mutate the object's internal state through that shared reference "
                "(since both references point to the same object), but it CANNOT make the caller's original "
                "reference variable point to a different object by reassigning the parameter inside the "
                "method",
                "mutating the object's fields through the reference is visible to the caller, but "
                "reassigning the local parameter variable itself is not"),
        ],
        "follow_ups": [
            _fu("If a method does `list.add(\"x\")` on a List parameter, does the caller see that change "
                "after the method returns? What if the method instead does `list = new ArrayList<>()` inside "
                "itself?",
                [_kp("the add() call mutates the shared object's internal state through the copied reference, "
                     "so the caller DOES see the new element afterward",
                     "mutating through the reference is visible outside the method"),
                 _kp("reassigning the local `list` parameter to a brand-new ArrayList only changes what that "
                     "LOCAL copy of the reference points to -- the caller's original variable still points to "
                     "the original object, unaffected",
                     "reassigning the parameter inside the method does not change what the caller's variable "
                     "refers to")]),
            _fu("Does this same reasoning apply to primitive parameters like int, and why or why not?",
                [_kp("yes, in the same pass-by-value sense -- the method gets a copy of the primitive value "
                     "itself, so any change to that local copy inside the method has no effect on the "
                     "caller's original variable, since there's no reference/object involved at all for "
                     "primitives",
                     "primitives are copied by value directly; there's no shared reference for the method to "
                     "mutate through"),
                 _kp("the difference versus an object parameter is only in WHAT gets copied (a raw value vs a "
                     "reference), not in whether copying happens -- both are passed by value in Java",
                     "primitives and object references are both passed by value; they just differ in what "
                     "that copied value represents")]),
        ],
    },
    {
        "id": "java-13", "topic": "java",
        "text": "What is the difference between an abstract class and an interface in Java, including how "
                "default methods changed things?",
        "key_points": [
            _kp("an abstract class can hold instance state (fields) and a mix of fully implemented methods "
                "and abstract (unimplemented) ones, and a class can extend only one abstract class",
                "abstract classes can carry state and partial implementation, but only single inheritance of "
                "one"),
            _kp("a classic (pre-Java 8) interface could only declare method signatures with no "
                "implementation and no instance fields, but a class can implement multiple interfaces",
                "interfaces traditionally had no implementation or instance state, but allowed multiple "
                "implementation"),
            _kp("since Java 8, interfaces can include default methods (and static methods) that DO provide a "
                "method body, letting an interface supply default behaviour without breaking existing "
                "implementers -- but an interface still cannot hold instance fields the way an abstract "
                "class can",
                "default methods let interfaces provide implemented behaviour since Java 8, though interfaces "
                "still can't carry instance state like an abstract class can"),
        ],
        "follow_ups": [
            _fu("If a class implements two interfaces that both define the SAME default method signature with "
                "different bodies, what happens?",
                [_kp("it's a compile error unless the implementing class explicitly overrides that method "
                     "itself to resolve the conflict -- Java won't silently pick one default over the other",
                     "a default-method clash between interfaces must be resolved explicitly by the "
                     "implementing class; it doesn't compile otherwise"),
                 _kp("inside its own override, the class can still explicitly choose to call one of the "
                     "specific interfaces' default implementations (e.g. InterfaceName.super.method()) if it "
                     "wants that behaviour rather than writing entirely new logic",
                     "the class's override can still delegate to a specific interface's default via a "
                     "qualified super call")]),
            _fu("Given that interfaces can now have default methods too, what's still a genuine reason to "
                "choose an abstract class over an interface for a given design?",
                [_kp("when the type needs to hold and manage actual instance state (fields) shared across "
                     "subclasses, since interfaces still cannot declare instance fields",
                     "needing shared mutable/instance state is a reason to use an abstract class, since "
                     "interfaces can't hold fields"),
                 _kp("when you need a true is-a base-class relationship with constructor logic, since "
                     "interfaces have no constructors and a class can only extend one class but can "
                     "implement many interfaces",
                     "abstract classes support constructors and a deeper is-a hierarchy; interfaces are "
                     "better for multiple, more loosely-coupled capabilities")]),
        ],
    },
]
