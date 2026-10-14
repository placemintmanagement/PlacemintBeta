# -*- coding: utf-8 -*-
"""Static DSA hint ladders for the Capgemini Spark tier (STAGE 1 of the
DSA-hints build -- hints only, zero wiring; see tests/test_dsa_hints_lint.py
and the leak-check review file in the scratchpad for how these were
checked). One entry per problem in spark/dsa.py (SPARK_DSA_PROBLEMS, 15
problems), keyed by the same "id". Every hint was written after reading
that problem's own statement and reference_solution, so each ladder is
specific to how that problem is actually solved, not a generic template.

Each ladder is exactly 3 static hints, at most 40 words each, with NO
model call involved at any point -- these strings are shown to the
candidate as-is (STAGE 2 wraps them in a short spoken lead-in):
  L1 -- a thinking nudge: a question or observation about the problem.
        Names NO technique or data structure.
  L2 -- names the technique/data structure that applies, with one line on
        why it fits. No step-by-step.
  L3 -- the key insight, in one sentence. Never the algorithm's steps,
        code, pseudocode, or its time/space complexity.
Plain spoken English throughout; never "Hint:", never corporate phrasing,
and never a verdict on whether the candidate's own approach is right or
wrong (that judgement stays with the real grader, not a hint)."""

SPARK_DSA_HINTS = {
    "contains-duplicate": [
        "What's the fastest way you could tell, for any one value, whether you've already come across it before?",
        "A hash set of values you've already seen works well here — checking membership in it is instant, so you catch a repeat the moment you see it.",
        "Checking a set costs the same whether it holds one value or a million, which is what makes this approach worth using at all.",
    ],
    "merge-sorted": [
        "Both lists are already in order — if you're looking at the front of each one, how do you decide which value belongs next in the merged list?",
        "Two pointers, one on each array, each advancing only when its value gets placed, build the merged list in a single left-to-right sweep.",
        "Whichever front value is smaller always belongs next, so you never need to look back once you've placed it.",
    ],
    "tree-level-order": [
        "Each node is reachable from the one above it — how would you process this structure so that you finish an entire depth before moving to the next?",
        "A queue that holds one depth's worth of nodes at a time, processing them together before adding their children, gives you breadth-first order naturally.",
        "There's a natural signal for when you've finished one level and are about to start the next, if you think about what's sitting in your queue at that instant.",
    ],
    "tree-symmetric": [
        "Picture folding this structure down its middle — which two nodes would need to land on each other for every mirrored pair, and what would have to be true about them?",
        "Comparing the left side against the right side as true mirror images of each other, recursively, confirms the whole structure folds onto itself.",
        "Being mirror images is a property that has to hold recursively — true at the top only if it's true for the pair of children one level down, too.",
    ],
    "tree-balanced": [
        "If one branch of a node runs much deeper than the other, what would that tell you about whether this whole structure is evenly shaped?",
        "Computing each node's height bottom-up in a single pass, and bailing out the moment two sides differ by more than one, avoids repeating work.",
        "Every single node needs its two sides checked, not just the very top one, or an imbalance deeper down slips past unnoticed.",
    ],
    "tree-min-depth": [
        "What's the very first leaf you'd reach if you explored level by level outward from the top, and why would that matter for the shortest path?",
        "A queue that visits nodes level by level gets you to candidates for the shortest path in the right order — but not every node missing a child is actually one of them.",
        "Whether a node counts as a true stopping point for the shortest path depends on more than just how many children it's missing.",
    ],
    "string-longest-common-prefix": [
        "If you compare the first two strings character by character, how far do you get before they stop agreeing, and what does that tell you about the other strings?",
        "Treating the first string as a starting candidate and checking how far it still matches against each new string, one at a time, narrows things down efficiently.",
        "The common prefix can only ever get shorter as you check more strings, never longer, so you can stop the moment it hits zero.",
    ],
    "string-word-pattern": [
        "What would it mean for two different pattern letters to end up pointing at the exact same word — is that actually allowed here?",
        "Two maps, one from letter to word and one from word back to letter, checked together, catch a mismatch in either direction.",
        "A mapping only holds up if it works the same way in both directions, letter-to-word and word-to-letter, for every position at once.",
    ],
    "tp-remove-duplicates-sorted": [
        "Since every equal value sits right next to the others in this array, where exactly would a repeat of the value you just kept have to be?",
        "Keeping one pointer for where the next distinct value should go, and another scanning ahead for it, lets you overwrite in place.",
        "Sorted order means everything you'd need to know about past distinct values is already captured in whichever one you kept most recently.",
    ],
    "first-unique-char": [
        "If you knew exactly how many times each letter showed up in the whole string, how would that help you find the first one that's alone?",
        "Tallying up how often each character appears, just once, gives you everything you need to identify which ones are actually alone.",
        "A character's total tally tells you whether it was ever repeated — but tallying alone doesn't tell you which one came first.",
    ],
    "valid-parentheses": [
        "When you hit a closing bracket, which opening bracket does it actually need to match — the very first one you saw, or the most recent one still open?",
        "A stack of open brackets, popped and checked against each closer as it arrives, naturally tracks whichever one opened most recently.",
        "Every closing bracket must match whatever opener is currently on top, and nothing is valid if openers are still waiting at the very end.",
    ],
    "intersection-unique": [
        "If you could instantly check whether any single value shows up in the second array, how would that change your approach to the first one?",
        "Converting each array into a set of its distinct values turns a pairwise comparison problem into a much cheaper membership question.",
        "A value only belongs in your result once no matter how many times it repeats in either array, so duplicates need collapsing before you're done.",
    ],
    "middle-of-linked-list": [
        "Without counting the whole list first, is there a way to know you've reached the middle just by how two different-speed walks through it compare?",
        "Two pointers moving through the list together, one twice as fast as the other, land the slow one on the middle when the fast one runs out.",
        "By the time the faster walker has covered the whole list, the slower one is sitting exactly at the middle node.",
    ],
    "can-attend-meetings": [
        "If two meetings are listed in a random order, what would you need to do to them first before you could easily spot an overlap?",
        "Ordering meetings by their start time first turns the problem into checking only neighbouring pairs, one quick comparison at a time.",
        "Once meetings are in start-time order, any clash can only ever happen between two that sit right next to each other.",
    ],
    "pair-with-sum-sorted": [
        "The numbers are already arranged smallest to largest — if the two you're currently looking at add up to less than the target, which one should you move, and in which direction?",
        "Two pointers starting at opposite ends of the sorted array, moving the low one up or the high one down based on the current sum, close in on the target.",
        "Moving a pointer always changes the sum in a predictable, single direction, which is what makes closing in on the target possible without ever checking every pair.",
    ],
}
