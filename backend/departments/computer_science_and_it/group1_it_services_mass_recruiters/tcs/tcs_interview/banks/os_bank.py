# -*- coding: utf-8 -*-
"""TCS Technical-round Operating Systems question bank.

# SEED CONTENT: a small, hand-written STARTING set (3 questions), not
production-complete. Production should grow this to at least 8-10 items.
Freshly written for TCS, not copied from Dave's OS_QUESTIONS bank.

Shape: {id, topic, difficulty, text, key_points} -- see banks/_kp.py.
"""
from typing import Any, Dict, List

from ._kp import kp

OS_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-os-1", "topic": "os", "difficulty": "ninja",
        "text": "What is the difference between a process and a thread?",
        "key_points": [
            kp("a process has its own independent memory space/address space",
               "processes are isolated from each other in memory"),
            kp("threads within the same process share that process's memory space",
               "threads are lighter-weight and share resources of their parent process"),
        ],
    },
    {
        "id": "tcs-os-2", "topic": "os", "difficulty": "digital",
        "text": "What is a deadlock, and what is one condition that must hold for a deadlock to occur?",
        "key_points": [
            kp("a deadlock is a state where two or more processes/threads are each waiting on a resource the other holds, with none able to proceed",
               "a cycle of processes blocked waiting on each other forever"),
            kp("names at least one real deadlock condition, e.g. mutual exclusion, hold-and-wait, no preemption, or circular wait",
               "correctly names one of the classic deadlock conditions"),
        ],
    },
    {
        "id": "tcs-os-3", "topic": "os", "difficulty": "prime",
        "text": "What is virtual memory, and what problem does paging solve?",
        "key_points": [
            kp("virtual memory gives each process the illusion of its own large, contiguous address space, decoupled from physical RAM",
               "virtual memory abstracts physical memory away from the process"),
            kp("paging breaks memory into fixed-size pages/frames so a process doesn't need to be stored contiguously in physical RAM",
               "paging solves external fragmentation by using fixed-size chunks"),
        ],
    },
]
