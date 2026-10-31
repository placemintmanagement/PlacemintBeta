# -*- coding: utf-8 -*-
"""Static DSA hint ladders for the Capgemini Dave tier (STAGE 1 of the
DSA-hints build -- hints only, zero wiring; see tests/test_dsa_hints_lint.py
and the leak-check review file in the scratchpad for how these were
checked). One entry per problem in dave/dsa.py (DAVE_DSA_PROBLEMS, 14
Medium-difficulty problems), keyed by the same "id". The Commit tier
reuses this same module (it draws its DSA problem from the same bank;
see commit/flow.py) rather than duplicating these ladders. Every hint was
written after reading that problem's own statement and
reference_solution, so each ladder is specific to how that problem is
actually solved, not a generic template.

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

DAVE_DSA_HINTS = {
    "product-except-self": [
        "Without using division, what would happen if you multiplied together every number that comes before a position, and separately every number that comes after it?",
        "Tracking a running product as you move in one direction, and a separate one as you move in the other, avoids ever needing division.",
        "Everything a position needs can be split cleanly into what's to its left and what's to its right, with neither side ever needing the other's full detail.",
    ],
    "search-rotated": [
        "Even though the array got rotated, is there still some property of a middle element that tells you which side of it is properly ordered?",
        "Checking which half around the midpoint is still in ascending order tells you which half could possibly hold the target, halving the search each time.",
        "One side of any midpoint is always properly ordered, and that tells you immediately whether the target could be hiding in it.",
    ],
    "longest-palindromic": [
        "If you picked a single character, or a gap between two characters, as a center and grew outward symmetrically, how far could you go before it stopped matching?",
        "Treating every character, and every gap between two characters, as a possible center lets you grow outward and test symmetry directly.",
        "Nothing about a palindrome tells you its center in advance, so the only way to be sure you've found the longest one is to let every position prove itself.",
    ],
    "tree-diameter": [
        "For any single node, if you knew how far down its two branches reach, what would that tell you about the longest path passing through that node?",
        "Visiting children before their parent, so each node already knows its own branch heights by the time you look at it, is the natural order here.",
        "The longest path doesn't have to pass through the top at all — some node partway down may serve its two branches better than the root does.",
    ],
    "tree-kth-smallest-bst": [
        "Given how values are arranged in this particular kind of structure, is there a visiting order that would naturally hand you every value from smallest to largest?",
        "An in-order walk — left, node, right — is the traversal order that matches exactly how values are arranged in this kind of structure.",
        "Since the walk already produces values in increasing order, keeping a running count as you go tells you exactly when you've reached the k-th smallest.",
    ],
    "greedy-two-city-scheduling": [
        "For each person, what single number would capture how much they'd personally save the group by going to one city instead of the other?",
        "Looking at how much cheaper one city is for each person, relative to the other, reframes this as a straightforward ordering problem.",
        "What matters for each person isn't either cost alone, but the gap between the two costs, which decides which city they should go to.",
    ],
    "greedy-min-platforms": [
        "If you lined up every arrival and every departure on a single timeline, separately, what would rising and falling counts along that timeline tell you?",
        "Sorting arrivals and departures as two separate lists and sweeping through them together, counting trains present at once, tracks platform demand directly.",
        "The busiest moment, whenever that is, is exactly how many platforms you need — not any particular train's own schedule.",
    ],
    "greedy-jump-game-ii": [
        "From your current position, what's the farthest you could reach in one more jump, and does that range actually need to be used up before jumping again?",
        "Tracking the farthest index reachable within your current jump count, and only incrementing the jump count once that range runs out, counts jumps greedily.",
        "You only need one more jump once you've actually run out of positions reachable within your current one, not before.",
    ],
    "graph-bipartite-check": [
        "If you gave the starting node one label, and every connection meant its other end had to get the opposite label, when exactly would that labelling break down?",
        "Exploring node by node and giving each unvisited neighbour the opposite color of the current node fails the moment a neighbour already shares its color.",
        "The whole structure only fails the two-coloring the instant two directly connected nodes are forced to share the same label.",
    ],
    "graph-rotten-oranges": [
        "If every rotten orange started spreading outward at the exact same moment, all at once, how would you track how many minutes pass before nothing fresh is left?",
        "Starting from every rotten orange at once and expanding outward minute by minute, level by level, spreads rot in the fewest possible total minutes.",
        "Starting the spread from all rotten oranges simultaneously, rather than one at a time, is what actually gives the true minimum time.",
    ],
    "dp-longest-increasing-subsequence": [
        "For each number in the array, if you only cared about numbers that came before it and were smaller, what would you want to know about those?",
        "Building up an answer per position, using what you've already worked out for earlier positions, is the kind of problem dynamic programming is built for.",
        "Nothing about a position's best answer depends on anything further along in the array, only on positions already resolved.",
    ],
    "dp-partition-equal-subset-sum": [
        "If the total of everything got split evenly in half, what would that tell you about which smaller totals you'd need to be able to reach using some of the numbers?",
        "Tracking which totals up to half the overall sum are reachable using some subset of the numbers is the classic table-filling fit here.",
        "The whole thing is only even possible at all if the overall total is even to begin with, before you check anything else.",
    ],
    "dp-maximal-square": [
        "If you wanted to know the largest all-1s square ending at a cell by filling a table one cell at a time, what's the least you'd need to know about cells you've already solved?",
        "Dynamic programming, where each cell stores how large a square can end there — because that value turns out to depend on only a small, fixed-size neighborhood rather than on the whole matrix solved so far.",
        "Exactly how a cell's nearby answers turn into its own answer is the one piece of arithmetic that makes the whole table work, and it's worth testing by hand on a small example first.",
    ],
    "tp-subarray-product-less-than-k": [
        "As you extend a running stretch of the array to the right and its product grows too large, what would you need to trim away from the left to fix that?",
        "A window that grows on the right and shrinks from the left whenever its running product reaches the limit is exactly what this kind of counting problem calls for.",
        "Every subarray ending at the current right edge that lies fully inside the current valid window is valid too, not just the longest one.",
    ],
}
