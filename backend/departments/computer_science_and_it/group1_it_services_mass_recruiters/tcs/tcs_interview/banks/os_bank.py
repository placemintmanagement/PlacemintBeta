# -*- coding: utf-8 -*-
"""TCS Core-CS: Operating Systems question bank.

Expanded (part 1 of the 4-part TCS restructure) to cover the USER-STATED
OS scope with tiered depth:
  processes vs threads, scheduling, deadlocks, memory management (paging,
  segmentation, virtual memory), synchronization (mutex, semaphore,
  classic problems), file system basics.
  Ninja = definitions. Digital = how-and-when. Prime = internals/tradeoffs.

# SEED CONTENT: every item below is a hand-written STARTING set (11
items, covering all 6 USER-STATED sub-topics at least once, several at
2-3 depth levels). Production should keep growing this bank for
repeat-attempt variety (see Part 4's content-gap table).

Shape: {id, topic, subtopic, difficulty, text, key_points} -- subtopic is
purely descriptive/reporting (groups items by the 6 USER-STATED OS areas);
grading and selection key off `topic`/`difficulty` exactly as every other
Core-CS bank in this package. See banks/_kp.py for kp().
"""
from typing import Any, Dict, List

from ._kp import kp

OS_QUESTIONS: List[Dict[str, Any]] = [
    # -- processes vs threads ------------------------------------------------
    {
        "id": "tcs-os-1", "topic": "os", "subtopic": "processes_threads", "difficulty": "ninja",
        "text": "What is the difference between a process and a thread?",  # SEED CONTENT
        "key_points": [
            kp("a process has its own independent memory space/address space",
               "processes are isolated from each other in memory"),
            kp("threads within the same process share that process's memory space",
               "threads are lighter-weight and share resources of their parent process"),
        ],
    },
    {
        "id": "tcs-os-4", "topic": "os", "subtopic": "processes_threads", "difficulty": "digital",
        "text": (  # SEED CONTENT
            "When would you reach for multiple threads instead of multiple processes to parallelize "
            "work, and when would you do the opposite?"
        ),
        "key_points": [
            kp("threads are preferred when tasks need to share memory/state cheaply and communication "
               "overhead matters (e.g. within one app)",
               "threads suit fine-grained, shared-state parallel work"),
            kp("processes are preferred for isolation/fault tolerance (one crashing doesn't take down "
               "the others) even at higher memory/communication cost",
               "processes suit workloads needing crash isolation or separate address spaces"),
        ],
    },
    # -- scheduling -----------------------------------------------------------
    {
        "id": "tcs-os-5", "topic": "os", "subtopic": "scheduling", "difficulty": "ninja",
        "text": "What is CPU scheduling, and can you name one scheduling algorithm?",  # SEED CONTENT
        "key_points": [
            kp("CPU scheduling decides which ready process/thread runs on the CPU next",
               "scheduling is about ordering competing processes for CPU time"),
            kp("names a real scheduling algorithm, e.g. First-Come-First-Served, Round Robin, "
               "Shortest Job First, or Priority scheduling",
               "correctly names at least one scheduling algorithm"),
        ],
    },
    {
        "id": "tcs-os-6", "topic": "os", "subtopic": "scheduling", "difficulty": "digital",
        "text": (  # SEED CONTENT
            "What's the practical difference between First-Come-First-Served and Round Robin "
            "scheduling, and when would you prefer Round Robin?"
        ),
        "key_points": [
            kp("FCFS runs processes strictly in arrival order, with no preemption, which can starve "
               "short jobs behind long ones",
               "FCFS is non-preemptive and order-dependent"),
            kp("Round Robin gives each process a fixed time slice and preempts it, which is fairer "
               "for interactive/short jobs even with switching overhead",
               "Round Robin trades some overhead for fairness/responsiveness"),
        ],
    },
    # -- deadlocks --------------------------------------------------------------
    {
        "id": "tcs-os-2", "topic": "os", "subtopic": "deadlocks", "difficulty": "digital",
        "text": "What is a deadlock, and what is one condition that must hold for a deadlock to occur?",  # SEED CONTENT
        "key_points": [
            kp("a deadlock is a state where two or more processes/threads are each waiting on a resource the other holds, with none able to proceed",
               "a cycle of processes blocked waiting on each other forever"),
            kp("names at least one real deadlock condition, e.g. mutual exclusion, hold-and-wait, no preemption, or circular wait",
               "correctly names one of the classic deadlock conditions"),
        ],
    },
    {
        "id": "tcs-os-7", "topic": "os", "subtopic": "deadlocks", "difficulty": "prime",
        "text": (  # SEED CONTENT
            "Name one real strategy for preventing or avoiding deadlock, and what it costs you in "
            "return for that safety."
        ),
        "key_points": [
            kp("names a real deadlock prevention/avoidance strategy, e.g. breaking one of the four "
               "conditions (e.g. resource ordering to prevent circular wait), or the Banker's algorithm",
               "correctly names a concrete deadlock-handling strategy, not just 'avoid deadlocks'"),
            kp("names a real tradeoff/cost of that strategy (e.g. reduced concurrency, extra "
               "bookkeeping overhead, needing resource-need info upfront)",
               "shows the strategy isn't free -- names what it gives up"),
        ],
    },
    # -- memory management ------------------------------------------------------
    {
        "id": "tcs-os-8", "topic": "os", "subtopic": "memory_management", "difficulty": "ninja",
        "text": "What is the difference between paging and segmentation, at a basic level?",  # SEED CONTENT
        "key_points": [
            kp("paging divides memory into fixed-size fixed blocks (pages/frames)",
               "paging uses equal-sized chunks"),
            kp("segmentation divides memory into variable-size logical units (e.g. code, data, stack)",
               "segmentation uses logically meaningful, variable-sized chunks"),
        ],
    },
    {
        "id": "tcs-os-3", "topic": "os", "subtopic": "memory_management", "difficulty": "prime",
        "text": "What is virtual memory, and what problem does paging solve?",  # SEED CONTENT
        "key_points": [
            kp("virtual memory gives each process the illusion of its own large, contiguous address space, decoupled from physical RAM",
               "virtual memory abstracts physical memory away from the process"),
            kp("paging breaks memory into fixed-size pages/frames so a process doesn't need to be stored contiguously in physical RAM",
               "paging solves external fragmentation by using fixed-size chunks"),
        ],
    },
    # -- synchronization ---------------------------------------------------------
    {
        "id": "tcs-os-9", "topic": "os", "subtopic": "synchronization", "difficulty": "ninja",
        "text": "What is a mutex, in simple terms, and what problem does it solve?",  # SEED CONTENT
        "key_points": [
            kp("a mutex is a lock that allows only one thread to access a shared resource/critical "
               "section at a time",
               "a mutex enforces mutual exclusion"),
            kp("it prevents a race condition from two threads reading/writing shared data at the same time",
               "it protects shared state from concurrent, unsafe access"),
        ],
    },
    {
        "id": "tcs-os-10", "topic": "os", "subtopic": "synchronization", "difficulty": "digital",
        "text": (  # SEED CONTENT
            "What is the producer-consumer problem, and how does a semaphore help solve it?"
        ),
        "key_points": [
            kp("producer-consumer is about coordinating a producer filling a shared buffer and a "
               "consumer draining it, without overflow, underflow or data races",
               "describes the producer/consumer coordination problem correctly"),
            kp("a semaphore tracks available slots/items (e.g. counting semaphore) and makes a "
               "producer/consumer wait when the buffer is full/empty respectively",
               "explains a semaphore as a counter that blocks/wakes threads appropriately"),
        ],
    },
    # -- file system basics -------------------------------------------------------
    {
        "id": "tcs-os-11", "topic": "os", "subtopic": "file_system", "difficulty": "ninja",
        "text": "At a basic level, what is a file system, and what does it keep track of for each file?",  # SEED CONTENT
        "key_points": [
            kp("a file system organizes and manages how data is stored and retrieved on a storage device",
               "it is the layer that lets an OS store/retrieve named files"),
            kp("it tracks metadata like file name, size, location/blocks on disk, and permissions",
               "names at least one concrete piece of file metadata it tracks"),
        ],
    },
]
