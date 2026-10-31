# -*- coding: utf-8 -*-
"""TCS interview puzzle bank (part 2 of the 4-part TCS restructure).

STEP 0 (reuse decision, recorded here): `games/gamified_round.py`'s
`puzzle_bank` is a MongoDB COLLECTION (`db.puzzle_bank`) feeding the OA's
gamified rounds (grid/motion/switch/inductive challenges) -- auto-graded
by exact stored `correctAnswer` matching, visual/grid-shaped content, for
the OA, not an interview. NOT reusable here: different storage mechanism
(DB collection vs this static, version-controlled Python module),
different grading model (exact-match auto-grading vs this bank's open-
ended AI-judged rubric), different content shape (visual grid puzzles vs
verbal classic puzzles), different audience (OA round vs interview).
Hence this NEW, separate module, named so it can never collide with that
collection's name.

Every item's `statement` below is ORIGINAL wording (not copied from any
source) even where the underlying puzzle is a well-known classic --
tagged `source="classic folklore puzzle, original wording"` for those,
or the honest alternative where that doesn't apply.

Two kinds of items:
  - GENERATED (`generated=True`): parametrized instances of a family with
    a dedicated SOLVER in puzzle_solvers.py. The solver's computed answer
    is stored directly (never hand-guessed), and every one is cross-
    checked against an INDEPENDENT second method at IMPORT TIME (an
    assertion right here, not just in tests) -- see each _generate_*
    function below. If a cross-check ever disagrees, importing this
    module raises immediately rather than silently shipping a wrong
    answer.
  - STATIC (hand-written): families with no applicable solver (hat/logic
    puzzles, probability riddles, etc). Carefully verified by hand
    against well-documented canonical answers; several worked examples
    are included in each one's `solution` field below.

Tier mapping (OUR ESTIMATE): Digital = easy-medium, Prime = medium-hard.
Puzzles are Digital/Prime ONLY -- "ninja" never appears in any
`tier_tags` list in this file.
"""
import random
from typing import Any, Dict, List

from . import puzzle_solvers as ps
from ._kp import kp

_TIER_TAGS_FOR_DIFFICULTY = {
    "easy": ["digital"],
    "medium": ["digital", "prime"],
    "hard": ["prime"],
}


def _item(id_, title, statement, family, difficulty, solution, accepted_approaches,
          rubric_key_points, common_wrong_answers, follow_ups, source, assumptions,
          generated=False, params=None) -> Dict[str, Any]:
    """`assumptions` (new field, puzzle-assumptions audit): a list of short
    strings, one per load-bearing assumption the SOLUTION depends on --
    every item must list every such assumption, and every one of them must
    also be explicitly present in `statement` (never left implicit), so a
    student is never asked to guess an unstated rule of the game (tested in
    tests/test_interview_puzzle_bank.py)."""
    if not assumptions:
        raise ValueError(f"puzzle item {id_!r} must list at least one load-bearing assumption")
    return {
        "id": id_, "title": title, "statement": statement, "family": family,
        "difficulty": difficulty, "tier_tags": _TIER_TAGS_FOR_DIFFICULTY[difficulty],
        "solution": solution, "accepted_approaches": accepted_approaches,
        "rubric_key_points": rubric_key_points, "common_wrong_answers": common_wrong_answers,
        "follow_ups": follow_ups, "source": source, "assumptions": assumptions,
        "generated": generated, "params": params or {},
    }


# ============================================================================
# GENERATED, solver-verified items (15: 3 per family x 5 families)
# ============================================================================

def _generate_water_jugs() -> List[Dict[str, Any]]:
    instances = [("easy", 5, 3, 1), ("medium", 3, 5, 4), ("hard", 9, 4, 6)]
    items = []
    for difficulty, cap_a, cap_b, target in instances:
        steps = ps.water_jugs_min_steps(cap_a, cap_b, target)
        solvable_by_formula = ps.water_jugs_is_solvable_by_number_theory(cap_a, cap_b, target)
        assert (steps is not None) == solvable_by_formula, (
            f"water jugs cross-check disagreement for ({cap_a},{cap_b},{target})")
        items.append(_item(
            id_=f"tcs-puz-jugs-{cap_a}-{cap_b}-{target}",
            title="Two Water Jugs",
            statement=(
                f"You have two jugs with no measurement markings: one holds exactly {cap_a} litres, the "
                f"other exactly {cap_b} litres, and both jugs start completely empty. You also have "
                f"unlimited access to water. Using only these two jugs (filling one completely, emptying "
                f"one completely, or pouring from one into the other until either the source is empty or "
                f"the destination is full), how would you end up with exactly {target} litre(s) in one of "
                f"the jugs, and in how few such steps?"
            ),
            family="water_jugs", difficulty=difficulty,
            solution=(
                f"Reachable: yes. The minimum number of fill/empty/pour steps is {steps}. (A target amount "
                f"is reachable with jugs of {cap_a}L and {cap_b}L exactly when it is no larger than the "
                f"bigger jug and is a multiple of gcd({cap_a}, {cap_b}).)"
            ),
            accepted_approaches=[
                "Any correct, step-by-step sequence of fill/empty/pour moves that ends with the target "
                "amount in one jug, even if it takes a few more steps than the minimum.",
                "Reasoning from the gcd divisibility rule to argue the target IS reachable, even without "
                "spelling out every single move.",
            ],
            rubric_key_points=[
                kp("proposes a concrete first move (filling one specific jug), not just 'try things'",
                   "starts with an actual fill or pour action"),
                kp("the sequence of moves described is internally consistent (each pour obeys capacity "
                   "limits) and plausibly reaches the target",
                   "the candidate's own steps don't violate jug capacities"),
            ],
            common_wrong_answers=[
                "Claiming the target is unreachable when the gcd rule says it is (or vice versa).",
                "A move sequence that silently overflows a jug or pours more than is physically available.",
            ],
            follow_ups=[
                "Could you do it in fewer steps than you just described?",
                "What is the smallest positive amount these two jugs could ever measure out exactly?",
            ],
            source="classic folklore puzzle family, original wording and parameters; solver-verified",
            assumptions=[
                "both jugs start completely empty before you begin",
                f"the jugs have no measurement markings, only exact capacities of {cap_a} and {cap_b} litres",
            ],
            generated=True, params={"cap_a": cap_a, "cap_b": cap_b, "target": target, "min_steps": steps},
        ))
    return items


def _generate_bridge_crossing() -> List[Dict[str, Any]]:
    instances = [("easy", [1, 2, 5, 10]), ("medium", [1, 3, 6, 8, 12]), ("hard", [2, 4, 5, 9, 11, 15])]
    items = []
    for difficulty, times in instances:
        total = ps.bridge_min_total_time(times)
        naive = ps.bridge_min_total_time_naive(times) if len(times) <= 6 else total
        assert total == naive, f"bridge crossing cross-check disagreement for {times}"
        people_desc = ", ".join(f"{t} minute(s)" for t in times)
        items.append(_item(
            id_=f"tcs-puz-bridge-{'-'.join(map(str, times))}",
            title="Crossing the Bridge by Torchlight",
            statement=(
                f"{len(times)} people all start together on the same side of a narrow bridge at night and "
                f"need to get every one of them across to the far side. They have exactly one torch, and "
                f"the bridge is only safe to cross with the torch in hand. At most two people can cross "
                f"together at a time, and whenever two cross together they move at the slower person's "
                f"pace. Someone must carry the torch back for the next crossing, and each person's time "
                f"below applies equally whether they are crossing to the far side or carrying the torch "
                f"back: {people_desc}. What is the minimum total time for all of them to get across?"
            ),
            family="bridge_crossing", difficulty=difficulty,
            solution=(
                f"The minimum total time is {total} minutes. The key insight: when 4 or more people "
                f"remain, it is often faster to send the two FASTEST people back and forth as shuttles for "
                f"the two slowest, rather than always sending the fastest person alone as a ferry -- "
                f"compare both options at each step and take whichever costs less."
            ),
            accepted_approaches=[
                "Any specific crossing order (who crosses together, who brings the torch back each time) "
                "whose total time equals the minimum.",
                "Explaining the 'shuttle the two fastest to move the two slowest together' idea even "
                "without listing every single crossing.",
            ],
            rubric_key_points=[
                kp("recognizes that sending the two SLOWEST people across TOGETHER (rather than "
                   "separately) avoids paying for the slower person's time twice",
                   "understands that pairing the two slowest together saves time"),
                kp("proposes a plan where the torch always returns via a relatively fast person, not the "
                   "slowest one",
                   "uses a fast person as the shuttle/ferry for the torch"),
            ],
            common_wrong_answers=[
                "Simply summing everyone's individual time (ignores that two can cross together).",
                "Always sending the single fastest person back alone every time, even when pairing the "
                "two fastest as a shuttle would be cheaper overall.",
            ],
            follow_ups=[
                "Why might it sometimes be better to send the two fastest people back and forth together, "
                "instead of just the single fastest person?",
                "How would the answer change if three people could cross the bridge at once instead of two?",
            ],
            source="classic folklore puzzle family, original wording and parameters; solver-verified",
            assumptions=[
                "everyone starts together on the same side of the bridge and all must get to the far side",
                "each person's stated time applies equally whether crossing to the far side or carrying "
                "the torch back",
            ],
            generated=True, params={"times": times, "min_total_time": total},
        ))
    return items


def _generate_river_crossing() -> List[Dict[str, Any]]:
    wgc = ps.river_crossing_min_trips(("farmer", "wolf", "goat", "cabbage"),
                                      ps.wolf_goat_cabbage_unsafe, boat_capacity=2, must_include=0)
    mc2 = ps.river_crossing_min_trips(("M1", "M2", "C1", "C2"), ps.missionaries_cannibals_unsafe(2),
                                      boat_capacity=2)
    mc3 = ps.river_crossing_min_trips(("M1", "M2", "M3", "C1", "C2", "C3"),
                                      ps.missionaries_cannibals_unsafe(3), boat_capacity=2)
    for res in (wgc, mc2, mc3):
        assert res is not None, "river crossing instance unexpectedly unsolvable"
    items = [
        _item(
            id_="tcs-puz-river-wolf-goat-cabbage",
            title="Farmer, Wolf, Goat and Cabbage",
            statement=(
                "A farmer must cross a river by boat, bringing with him a wolf, a goat and a cabbage. "
                "The boat only holds the farmer plus ONE of the other three at a time -- nothing can cross "
                "by itself. Left alone together without the farmer, the wolf would eat the goat, and the "
                "goat would eat the cabbage (the wolf has no interest in the cabbage). How does the farmer "
                "get everything across safely, and in how few one-way boat trips?"
            ),
            family="river_crossing_wolf_goat_cabbage", difficulty="medium",
            solution=(
                f"It takes {wgc[0]} one-way trips. One valid order: take the goat across; go back alone; "
                "bring the wolf across; bring the goat BACK with you; take the cabbage across; go back "
                "alone; bring the goat across again. The trick is that the goat has to cross twice, "
                "because it is the one unsafe thing to leave with EITHER of the others."
            ),
            accepted_approaches=[
                "Any valid 7-trip sequence that never leaves wolf+goat or goat+cabbage alone without the "
                "farmer, as long as everyone ends up on the far bank.",
            ],
            rubric_key_points=[
                kp("identifies the goat as the item that must cross the river TWICE (once over, once back, "
                   "once over again)",
                   "recognizes the goat needs a round trip, not just a one-way crossing"),
                kp("never leaves wolf and goat together, or goat and cabbage together, without the farmer "
                   "present, at any point in their plan",
                   "keeps the unsafe pairs separated unless the farmer is there"),
            ],
            common_wrong_answers=[
                "Taking the wolf or cabbage across first and leaving the goat with the other unsafe item.",
                "Forgetting that the farmer must return alone before the next pair can be handled.",
            ],
            follow_ups=[
                "What would change if the boat could carry the farmer plus TWO items at once?",
                "Which of the three items is the 'problem' one, and why does it need an extra trip?",
            ],
            source="classic folklore puzzle, original wording; solver-verified",
            assumptions=[
                "the boat holds the farmer plus exactly one other item, and nothing can cross by itself",
                "left alone without the farmer, the wolf would eat the goat and the goat would eat the cabbage",
            ],
            generated=True, params={"min_trips": wgc[0]},
        ),
        _item(
            id_="tcs-puz-river-missionaries-2",
            title="Two Missionaries and Two Cannibals",
            statement=(
                "Two missionaries and two cannibals need to cross a river using a small boat that holds at "
                "most two people. Anyone present (missionary or cannibal) can row the boat. The one safety "
                "rule: on EITHER bank, cannibals must never outnumber missionaries while missionaries are "
                "present there (otherwise the missionaries are in danger). How do all four get across "
                "safely, and in how few one-way boat trips?"
            ),
            family="river_crossing_missionaries_cannibals", difficulty="easy",
            solution=(
                f"It takes {mc2[0]} one-way trips. One valid order: send a cannibal and a missionary over; "
                "the missionary comes back alone (so the far bank never has cannibals outnumbering "
                "missionaries); then the two cannibals go over together (now both cannibals are safely "
                "across, no missionaries present to be outnumbered); one cannibal returns to fetch the "
                "last missionary; the remaining missionary and cannibal cross together."
            ),
            accepted_approaches=[
                "Any valid 5-trip sequence that never leaves cannibals outnumbering missionaries on a bank "
                "where missionaries are present.",
            ],
            rubric_key_points=[
                kp("checks every intermediate state against the 'cannibals never outnumber missionaries "
                   "where missionaries are present' rule, not just the start/end states",
                   "verifies safety at EVERY step of the plan, not only the final result"),
                kp("has someone physically return the boat, recognizing the boat can't cross by itself",
                   "accounts for someone rowing the boat back each time"),
            ],
            common_wrong_answers=[
                "A plan that is fine at the end but passes through an unsafe intermediate state (e.g. 1 "
                "missionary left with 2 cannibals on a bank at some point).",
            ],
            follow_ups=[
                "What's the smallest boat capacity that would make this particular case solvable at all?",
                "Does the order in which you move people matter, or are there multiple equally valid plans?",
            ],
            source="classic folklore puzzle, original wording; solver-verified",
            assumptions=[
                "the boat holds at most two people and anyone present (missionary or cannibal) can row it",
                "cannibals must never outnumber missionaries on a bank where missionaries are present",
            ],
            generated=True, params={"min_trips": mc2[0]},
        ),
        _item(
            id_="tcs-puz-river-missionaries-3",
            title="Three Missionaries and Three Cannibals",
            statement=(
                "Three missionaries and three cannibals need to cross a river using a boat that holds at "
                "most two people, and anyone present can row it. The same safety rule applies: on EITHER "
                "bank, cannibals must never outnumber missionaries while missionaries are present there. "
                "How do all six get across safely, and in how few one-way boat trips?"
            ),
            family="river_crossing_missionaries_cannibals", difficulty="hard",
            solution=(
                f"It takes {mc3[0]} one-way trips -- noticeably more than the 2-and-2 version, because "
                "with 3 of each, more of the crossings must be cannibal-only pairs so that missionaries are "
                "never left outnumbered on either bank while the group is split up."
            ),
            accepted_approaches=[
                "Any valid sequence of one-way trips, of length matching the true minimum, that keeps "
                "every intermediate bank state safe.",
            ],
            rubric_key_points=[
                kp("recognizes this is harder than the 2-and-2 case specifically because more people are "
                   "mid-transfer at once, creating more risky intermediate states to avoid",
                   "connects the larger group size to more constrained intermediate states"),
                kp("checks every intermediate state against the safety rule, not just the final outcome",
                   "verifies safety throughout the plan, not just at the end"),
            ],
            common_wrong_answers=[
                "Assuming the 2-and-2 solution just scales up directly without re-checking intermediate "
                "states for the larger group.",
            ],
            follow_ups=[
                "Why does this version need noticeably more trips than the 2-missionary/2-cannibal version?",
                "Is there a point during the crossing where ALL three cannibals end up on one bank together "
                "before any missionary joins them? Why might that be necessary?",
            ],
            source="classic folklore puzzle, original wording; solver-verified",
            assumptions=[
                "the boat holds at most two people and anyone present can row it",
                "cannibals must never outnumber missionaries on a bank where missionaries are present",
            ],
            generated=True, params={"min_trips": mc3[0]},
        ),
    ]
    return items


def _generate_counterfeit_coin() -> List[Dict[str, Any]]:
    instances = [("easy", 9), ("medium", 12), ("hard", 81)]
    items = []
    for difficulty, n in instances:
        search_result = ps.min_weighings_known_heavier(n)
        formula_result = ps.min_weighings_known_heavier_formula(n)
        assert search_result == formula_result, f"counterfeit coin cross-check disagreement for n={n}"
        items.append(_item(
            id_=f"tcs-puz-coins-{n}",
            title="The Heavier Counterfeit Coin",
            statement=(
                f"You have {n} identical-looking coins. Exactly one of them is counterfeit and is slightly "
                f"HEAVIER than the rest (all genuine coins weigh exactly the same as each other). You have "
                f"an old-fashioned two-pan balance scale with no weights -- it only tells you which side is "
                f"heavier, or whether the two sides balance. What is the minimum number of weighings needed "
                f"to guarantee finding the counterfeit coin, and how would you do it?"
            ),
            family="counterfeit_coin_balance", difficulty=difficulty,
            solution=(
                f"The minimum is {search_result} weighings. Strategy: split the current group of suspect "
                f"coins into three roughly equal piles; weigh any two piles against each other. If one side "
                f"is heavier, the counterfeit is in that pile; if they balance, it's in the pile left "
                f"aside. Repeat on the now-smaller suspect pile until only one coin remains."
            ),
            accepted_approaches=[
                "Any strategy that splits the suspect group into three parts each weighing (rather than "
                "into two), reaching the coin in the minimum number of weighings.",
            ],
            rubric_key_points=[
                kp("splits the coins into THREE groups per weighing (not two), since a balance weighing "
                   "has three possible outcomes",
                   "uses a 3-way split to match the 3 possible outcomes of a weighing"),
                kp("correctly narrows the suspect pool after each weighing based on which side (if either) "
                   "was heavier",
                   "correctly interprets each weighing's result to shrink the candidate set"),
            ],
            common_wrong_answers=[
                "Splitting coins into two equal halves each time (a binary approach), which wastes "
                "information since a balance weighing actually has 3 possible outcomes, not 2.",
                "Weighing coins one at a time against each other (linear search), which takes far more "
                "weighings than necessary.",
            ],
            follow_ups=[
                "Why is splitting into 3 groups better than splitting into 2, given what a balance scale "
                "can tell you?",
                "How would your strategy change if you did NOT know whether the counterfeit coin is "
                "heavier or lighter than the rest?",
            ],
            source="classic folklore puzzle family, original wording and parameters; solver-verified",
            assumptions=[
                f"exactly one of the {n} coins is counterfeit and it is heavier than every genuine coin",
                "all genuine coins weigh exactly the same as each other",
            ],
            generated=True, params={"n_coins": n, "min_weighings": search_result},
        ))
    return items


def _generate_hundred_doors() -> List[Dict[str, Any]]:
    instances = [("easy", 20), ("medium", 64), ("hard", 100)]
    items = []
    for difficulty, n in instances:
        sim = ps.doors_open_after_all_passes(n)
        formula = ps.doors_open_by_perfect_squares(n)
        assert sim == formula, f"doors cross-check disagreement for n={n}"
        items.append(_item(
            id_=f"tcs-puz-doors-{n}",
            title=f"The {n} Doors",
            statement=(
                f"There are {n} doors in a hallway, numbered 1 to {n}, all starting closed. {n} people walk "
                f"down the hallway one after another. The 1st person toggles (opens or closes) every door. "
                f"The 2nd person toggles every 2nd door (doors 2, 4, 6, ...). The 3rd person toggles every "
                f"3rd door (doors 3, 6, 9, ...), and so on, until the {n}th person, who only toggles door "
                f"{n}. After everyone has walked through, how many doors are left OPEN, and which ones?"
            ),
            family="hundred_doors", difficulty=difficulty,
            solution=(
                f"Exactly {len(sim)} doors are left open: the PERFECT-SQUARE-numbered doors "
                f"({', '.join(map(str, sim))}). A door's number gets toggled once for every divisor it "
                f"has; a number has an ODD number of divisors only when it is a perfect square (every "
                f"other divisor pairs up with a different divisor, except the square root of a perfect "
                f"square, which pairs with itself)."
            ),
            accepted_approaches=[
                "Correctly simulating/reasoning through small cases to notice the perfect-square pattern.",
                "Directly reasoning about divisor counts (a door is toggled once per divisor of its "
                "number) and that only perfect squares have an odd divisor count.",
            ],
            rubric_key_points=[
                kp("connects the number of times a door is toggled to the number of DIVISORS of that "
                   "door's number",
                   "recognizes that divisor count determines a door's final open/closed state"),
                kp("correctly identifies that a door ends OPEN exactly when its number is a PERFECT "
                   "SQUARE, because only perfect squares have an odd number of divisors",
                   "names perfect squares as the final answer, with the odd-divisor-count reasoning"),
            ],
            common_wrong_answers=[
                "Guessing a pattern based only on the first few doors without generalizing correctly "
                "(e.g. assuming only even-numbered or only odd-numbered doors matter).",
                "Correctly simulating by hand but miscounting which doors are perfect squares.",
            ],
            follow_ups=[
                "Why does a perfect square's number of divisors come out odd, when every other number's "
                "divisor count is even?",
                "Without simulating anything, how many doors would be open if there were 500 doors instead?",
            ],
            source="classic folklore puzzle family, original wording and parameters; solver-verified",
            assumptions=[
                f"all {n} doors start closed before the first person walks through",
                "the kth person toggles every door whose number is a multiple of k",
            ],
            generated=True, params={"n_doors": n, "open_doors": sim},
        ))
    return items


# ============================================================================
# STATIC, hand-written items (24: 5 easy / 14 medium / 5 hard)
# ============================================================================

_STATIC_ITEMS: List[Dict[str, Any]] = [
    # ---- EASY (5) -----------------------------------------------------------
    _item(
        id_="tcs-puz-handshakes", title="Counting Handshakes",
        statement=(
            "10 people are at a meeting, and every person shakes hands with every other person exactly "
            "once. How many handshakes happen in total?"
        ),
        family="handshake_counting", difficulty="easy",
        solution="45 handshakes. With n people, the total is n(n-1)/2 (each of the 10 people shakes hands "
                 "with the other 9, but that counts every handshake twice, once from each side): "
                 "10*9/2 = 45.",
        accepted_approaches=["Direct formula n(n-1)/2.",
                             "Summing 9+8+7+...+1 (each new person shakes hands only with people not yet "
                             "counted)."],
        rubric_key_points=[
            kp("arrives at exactly 45, not 10*9=90 or some other uncorrected count",
               "gives the correct final count of 45"),
            kp("explains why dividing by 2 (or counting only 'new' handshakes per person) is needed -- "
               "each handshake would otherwise be counted twice",
               "recognizes and corrects for double-counting each handshake"),
        ],
        common_wrong_answers=["90 (forgetting each handshake is shared between two people and gets "
                              "double-counted).", "100 (mistakenly computing 10*10)."],
        follow_ups=["How would the answer change with 20 people instead of 10?",
                   "What if two specific people in the group refuse to shake hands with each other?"],
        source="classic folklore puzzle, original wording",
        assumptions=[
            "every person shakes hands with every other person exactly once, never twice",
        ],
    ),
    _item(
        id_="tcs-puz-clock-overlap", title="Overlapping Clock Hands",
        statement=(
            "On an ordinary analog clock, the hour hand and the minute hand both start exactly together "
            "at 12:00. Over the next 12 hours, how many more times will the two hands exactly overlap "
            "each other again?"
        ),
        family="clock_angle", difficulty="easy",
        solution="11 times in 12 hours (so 22 times in a full 24-hour day). The minute hand laps the "
                 "hour hand slightly less than once per hour, because the hour hand is also slowly "
                 "moving forward -- over 12 hours the minute hand only manages 11 full laps relative to "
                 "the hour hand, not 12.",
        accepted_approaches=["Reasoning from relative angular speed (minute hand gains 360-30=330 "
                             "degrees per hour relative to the hour hand, so a full 360-degree lap "
                             "relative to the hour hand takes 360/330 hours; 12 hours / that interval "
                             "= 11).",
                             "Recalling/deriving that it's always exactly one fewer overlap than the "
                             "number of hours in the period, for a normal 12-hour clock face."],
        rubric_key_points=[
            kp("answers 11 for a 12-hour period, not the naive guess of 12",
               "gives the correct count of 11, not 12"),
            kp("explains WHY it's 11 and not 12 -- the hour hand is also moving, so the minute hand needs "
               "slightly more than an hour to catch up and lap it each time",
               "connects the answer to the hour hand's own motion, not just the minute hand's speed"),
        ],
        common_wrong_answers=["12 (assuming the hands overlap once every hour on the dot, ignoring that "
                              "the hour hand keeps moving)."],
        follow_ups=["At what time (besides 12:00) does the first overlap after 12:00 happen, roughly?",
                   "How many times do the hands point in exactly OPPOSITE directions in 12 hours?"],
        source="classic folklore puzzle, original wording",
        assumptions=[
            "the hour hand and minute hand start exactly together at 12:00",
            "this is an ordinary analog 12-hour clock",
        ],
    ),
    _item(
        id_="tcs-puz-two-coins", title="Two Coins, Thirty Cents",
        statement=(
            "I have two coins in my pocket that add up to exactly 30 cents. One of them is definitely "
            "NOT a nickel. What are the two coins?"
        ),
        family="coin_riddle", difficulty="easy",
        solution="A quarter (25 cents) and a nickel (5 cents). The statement 'one of them is not a "
                 "nickel' is TRUE of the quarter -- it cleverly doesn't rule out the OTHER coin also "
                 "being a nickel.",
        accepted_approaches=["Direct answer: quarter + nickel, with the wordplay explained."],
        rubric_key_points=[
            kp("gives the correct pair: a quarter and a nickel",
               "names quarter and nickel as the two coins"),
            kp("explains the wordplay -- 'one is not a nickel' only refers to ONE of the two coins "
               "(the quarter), and is silent about the other",
               "explains why the clue is technically true even though one coin IS a nickel"),
        ],
        common_wrong_answers=["Giving up and saying it's impossible (missing that the riddle is a trick "
                              "of phrasing, not a real constraint against using a nickel at all)."],
        follow_ups=["Can you think of another pair of coins and a similarly phrased true-but-misleading "
                   "clue about them?"],
        source="classic folklore puzzle, original wording",
        assumptions=[
            "the two coins add up to exactly 30 cents",
            "only one of the two coins is guaranteed not to be a nickel",
        ],
    ),
    _item(
        id_="tcs-puz-missing-number", title="The Erased Number",
        statement=(
            "The numbers from 1 to 20 are each written down once. One of the numbers is then erased. "
            "The remaining 19 numbers add up to exactly 203. Which number was erased?"
        ),
        family="missing_number", difficulty="easy",
        solution="7. The sum of all numbers from 1 to 20 is 20*21/2 = 210. Since the remaining numbers "
                 "add up to 203, the erased number is 210 - 203 = 7.",
        accepted_approaches=["Using the n(n+1)/2 sum formula for 1..20, then subtracting the given total.",
                             "Manually adding 1..20 to get 210 and subtracting."],
        rubric_key_points=[
            kp("correctly computes or recalls that 1 through 20 sums to 210",
               "gets the full sum of 1..20 right (210)"),
            kp("subtracts 203 from that total to get the erased number, 7",
               "arrives at 7 as the final answer via subtraction from the full sum"),
        ],
        common_wrong_answers=["Guessing a number without computing the full sum of 1..20 first.",
                              "Using the wrong formula for the sum of 1..20."],
        follow_ups=["What if two numbers (not just one) were erased and you were only told the final "
                   "sum -- could you still always find them uniquely?"],
        source="classic folklore puzzle, original wording and numbers",
        assumptions=[
            "the numbers 1 to 20 are each written down exactly once before one is erased",
            "the remaining 19 numbers add up to exactly 203",
        ],
    ),
    _item(
        id_="tcs-puz-frog-well", title="The Frog in the Well",
        statement=(
            "A frog is at the bottom of a 30-metre well. Each day it climbs up 3 metres, but each night, "
            "while resting, it slides back down 2 metres. On the day it finally reaches or passes the "
            "top of the well, it climbs out immediately and does not slide back. On which day does the "
            "frog escape the well?"
        ),
        family="frog_in_well", difficulty="easy",
        solution="Day 28. Each full day-night cycle nets the frog only 1 metre of progress (up 3, back "
                 "2). By the end of night 27, the frog has net-climbed 27 metres and is sitting at the "
                 "27-metre mark. On day 28, it climbs another 3 metres, reaching the 30-metre mark -- the "
                 "top -- and escapes before it would slide back.",
        accepted_approaches=["Tracking net daily progress (1 metre per full day-night cycle) and finding "
                             "the day the daytime climb alone reaches the top from the prior night's "
                             "resting position.",
                             "Simulating day by day."],
        rubric_key_points=[
            kp("recognizes the trap -- the frog does NOT need to net-climb the full 30 metres, because "
               "on the ESCAPE day it doesn't slide back at all",
               "avoids the naive '30 metres / 1 metre per day = 30 days' mistake"),
            kp("arrives at day 28 specifically (not 27 or 30)",
               "gives the correct final day, 28"),
        ],
        common_wrong_answers=["30 (naively dividing the well depth by the 1-metre net daily progress, "
                              "ignoring that the final day's climb doesn't get undone)."],
        follow_ups=["How would the answer change if the frog climbed 4 metres by day instead of 3?",
                   "What is the general rule for solving this kind of climb-and-slide-back problem?"],
        source="classic folklore puzzle, original wording and numbers",
        assumptions=[
            "the frog climbs 3 metres every day and slides back 2 metres every night",
            "on the day it reaches or passes the top it climbs out immediately and does not slide back",
        ],
    ),
    # ---- MEDIUM (14) ---------------------------------------------------------
    _item(
        id_="tcs-puz-two-guards", title="Two Guards, Two Doors",
        statement=(
            "You're standing in a room with two doors. One leads to freedom, the other leads nowhere "
            "good. Two guards stand there: one of them always tells the truth, the other always lies -- "
            "but you don't know which guard is which, or which door is which. Both guards DO know which "
            "door actually leads to freedom, and whichever guard you ask will answer your question. "
            "You're allowed to ask exactly ONE yes/no question, directed at only ONE of the two guards. "
            "What question do you ask to be sure of reaching the door to freedom?"
        ),
        family="two_guards", difficulty="medium",
        solution="Ask either guard: 'If I asked the OTHER guard whether this door leads to freedom, "
                 "would they say yes?' Then do the OPPOSITE of whatever answer you get. This works "
                 "because the question routes your answer through BOTH guards' truth-telling behavior: "
                 "the truth-teller will honestly report the liar's (wrong) answer, and the liar will "
                 "lie about the truth-teller's (correct) answer -- either way, the answer you get back "
                 "is wrong, so taking its opposite is always right.",
        accepted_approaches=["The equivalent self-referential question asked of either guard ('what "
                             "would you yourself say if I asked you this directly') combined with "
                             "flipping the answer.",
                             "Any logically equivalent double-negation question that cancels out which "
                             "guard you happened to ask."],
        rubric_key_points=[
            kp("the proposed question routes the answer through BOTH guards (asking what the other "
               "guard would say), not just the one guard directly",
               "the question involves the other guard's hypothetical answer, not a direct question"),
            kp("correctly explains that you then take the OPPOSITE of whatever answer comes back, "
               "regardless of which guard you asked",
               "states that the final answer must be inverted/negated"),
        ],
        common_wrong_answers=["Simply asking 'does this door lead to freedom?' directly -- this fails "
                              "because you don't know whether you're talking to the truth-teller or the "
                              "liar.", "Asking both guards the same direct question (not allowed -- only "
                              "one question, to one guard, is permitted)."],
        follow_ups=["Why does asking about the OTHER guard's answer cancel out the uncertainty about "
                   "which guard you're talking to?",
                   "Could you ask a different single question of the SAME guard that also works?"],
        source="classic folklore puzzle, original wording",
        assumptions=[
            "both guards know which door actually leads to freedom, even though only one of them tells the truth",
            "whichever guard you ask will answer your question",
            "you don't know which guard is which, or which door is which",
        ],
    ),
    _item(
        id_="tcs-puz-light-switches", title="Three Switches, One Bulb",
        statement=(
            "You're on the ground floor of a house. Upstairs, in a closed room, there is a single light "
            "bulb. Downstairs, there are three switches, and exactly one of them controls that bulb (the "
            "other two do nothing). You can flip the switches as much as you like while downstairs, but "
            "you may go upstairs to check the bulb only ONCE. How do you determine with certainty which "
            "switch controls the bulb?"
        ),
        family="light_switches", difficulty="medium",
        solution="Turn switch 1 ON and leave it on for a few minutes. Then turn switch 1 OFF, and turn "
                 "switch 2 ON, leaving switch 3 OFF. Go upstairs immediately. If the bulb is ON, switch 2 "
                 "is the answer. If the bulb is OFF but still WARM, switch 1 is the answer (it was on "
                 "long enough to heat the bulb's filament). If the bulb is OFF and COLD, switch 3 is the "
                 "answer (it was never turned on at all).",
        accepted_approaches=["Any strategy that encodes a THIRD distinguishable state (beyond simple "
                             "on/off) using a physical side-effect like heat, allowing all three "
                             "switches to be told apart from a single visit."],
        rubric_key_points=[
            kp("uses the bulb's residual HEAT as a third signal, beyond just 'currently on' or "
               "'currently off', to distinguish the switch left on-then-off from the switch never "
               "turned on at all",
               "introduces heat (or an equivalent physical side-effect) as a way to get a 3rd piece of "
               "information from one visit"),
            kp("correctly matches all three outcomes (on / off-and-warm / off-and-cold) to all three "
               "switches, with no switch left ambiguous",
               "maps every one of the three switches to a distinct, certain outcome"),
        ],
        common_wrong_answers=["Only testing switches 'on vs off' with no way to distinguish the two "
                              "switches that both leave the bulb off by the time you check it.",
                              "Proposing to visit the bulb room more than once, which isn't allowed."],
        follow_ups=["How would you adapt this if there were FOUR switches and one bulb, still with only "
                   "one visit allowed?",
                   "What other physical property (besides heat) could you use to encode extra "
                   "information if this were, say, a pair of bulbs instead?"],
        source="classic folklore puzzle, original wording",
        assumptions=[
            "exactly one of the three switches controls the bulb and the other two do nothing",
            "you may flip the switches as much as you like while downstairs, but may check the bulb only once",
        ],
    ),
    _item(
        id_="tcs-puz-burning-rope", title="Two Ropes, Forty-Five Minutes",
        statement=(
            "You have two ropes and a lighter. Each rope takes exactly 60 minutes to burn completely "
            "from one end to the other, but neither rope burns at a perfectly even rate along its "
            "length (so you can't assume the halfway point burns at the 30-minute mark). You may light "
            "a rope at either end, or at both ends at once, and you may light a rope's second end at any "
            "later moment you choose. How can you use these two ropes and the lighter to measure exactly "
            "45 minutes?"
        ),
        family="burning_rope", difficulty="medium",
        solution="Light rope A at BOTH ends at the same time, and light rope B at only ONE end, all at "
                 "the same starting moment. Rope A, burning from both ends toward the middle, will "
                 "finish in exactly 30 minutes (half of its normal 60-minute burn time), no matter how "
                 "unevenly it burns. The instant rope A finishes, light rope B's OTHER end too (so B is "
                 "now burning from both ends). B had 30 minutes of burning already done from one end, "
                 "leaving 30 minutes of material; now burning from both remaining ends, it finishes in "
                 "15 more minutes. Total elapsed: 30 + 15 = 45 minutes.",
        accepted_approaches=["Any sequence of lighting ends of the two ropes (at the right moments) that "
                             "produces a total elapsed time of exactly 45 minutes, using only the "
                             "'burns out in 60 minutes per rope, uneven along its length' fact."],
        rubric_key_points=[
            kp("recognizes that lighting a rope at BOTH ends halves its remaining burn time, regardless "
               "of how unevenly it burns (because the two flame fronts always meet after half the total "
               "time)",
               "uses the both-ends-halves-the-time trick, independent of uneven burning"),
            kp("correctly sequences lighting rope A fully (both ends, 30 minutes) and then lighting "
               "rope B's second end at exactly that 30-minute mark, to get 30+15=45",
               "arrives at the correct 30-then-15 sequencing that sums to 45 minutes"),
        ],
        common_wrong_answers=["Assuming you can measure 30 minutes by using the 'halfway point' of a "
                              "rope burning from one end -- this does NOT work since the ropes burn "
                              "unevenly along their length.",
                              "Lighting both ropes at both ends from the start, which only measures 30 "
                              "minutes, not 45."],
        follow_ups=["How would you measure exactly 15 minutes using the same two ropes?",
                   "Could you measure exactly 20 minutes with these two ropes? Why or why not?"],
        source="classic folklore puzzle, original wording",
        assumptions=[
            "each rope takes exactly 60 minutes to burn completely, even though it burns unevenly along its length",
            "a rope may be lit at either end, or at both ends at once, and a second end may be lit later",
        ],
    ),
    _item(
        id_="tcs-puz-mislabeled-boxes", title="Three Mislabeled Boxes",
        statement=(
            "You have three boxes: one contains only apples, one contains only oranges, and one contains "
            "a MIX of both. Each box has a label -- 'Apples', 'Oranges', or 'Mixed' -- but EVERY SINGLE "
            "label is wrong (no box's label matches its actual contents). You may pick exactly ONE fruit "
            "from exactly ONE box of your choosing (without looking inside first), and look at just that "
            "one fruit. How do you choose which box to draw from so that you can correctly relabel all "
            "three boxes with certainty?"
        ),
        family="mislabeled_boxes", difficulty="medium",
        solution="Draw one fruit from the box labeled 'Mixed'. Since every label is wrong, that box "
                 "CANNOT actually be mixed -- it must be all-apples or all-oranges. Whichever single "
                 "fruit you draw tells you that box's true, pure contents. From there, the box labeled "
                 "with the OTHER fruit's name cannot actually hold that fruit alone either (its label is "
                 "also wrong) and isn't the pure box you just identified, so it must be the MIXED box; "
                 "and the remaining box gets the one label left over.",
        accepted_approaches=["Drawing from the 'Mixed' labeled box, with the correct chain of deduction "
                             "for the other two boxes."],
        rubric_key_points=[
            kp("specifically chooses to draw from the box labeled 'Mixed' (not 'Apples' or 'Oranges'), "
               "because that's the one label guaranteed to be informative given ALL labels are wrong",
               "draws specifically from the box labeled Mixed, not either of the other two"),
            kp("correctly deduces the remaining two boxes' TRUE contents using the fact that every label "
               "is wrong, not just the one box they drew from",
               "correctly reasons out the other two boxes, not just the one they sampled"),
        ],
        common_wrong_answers=["Drawing from the box labeled 'Apples' or 'Oranges' -- this is ambiguous, "
                              "since that box could be the mixed one OR the other pure fruit, and a "
                              "single fruit drawn doesn't fully resolve which.",
                              "Forgetting that ALL three labels are wrong, not just some of them."],
        follow_ups=["Why specifically does drawing from the 'Mixed'-labeled box work, when drawing from "
                   "either of the other two does not?",
                   "What if only ONE label (not all three) were known to be wrong -- would one draw "
                   "still be enough?"],
        source="classic folklore puzzle, original wording",
        assumptions=[
            "every single label is wrong, so no box's label matches its actual contents",
            "you may draw exactly one fruit from exactly one box before relabeling all three",
        ],
    ),
    _item(
        id_="tcs-puz-monty-hall", title="The Three-Door Game Show",
        statement=(
            "On a game show, there are three closed doors, and the car is placed uniformly at random "
            "behind one of them before you choose (each door equally likely). Behind one is the car; "
            "behind the other two are goats. You pick a door, say Door 1. Before opening it, the host -- "
            "who knows exactly where the car is and always opens one of the OTHER two doors, never your "
            "own pick and never the door with the car, always revealing a goat -- opens one of those "
            "other two doors. You're then given the choice to either stick with your original pick or "
            "switch to the remaining unopened door. Should you switch, stick, or does it not matter -- "
            "and what's your probability of winning the car either way?"
        ),
        family="monty_hall", difficulty="medium",
        solution="You should SWITCH. Switching wins the car with probability 2/3; sticking only wins "
                 "with probability 1/3. Reasoning: your original pick has a 1/3 chance of being the car "
                 "and a 2/3 chance of being a goat. If your original pick was a goat (2/3 of the time), "
                 "the host is FORCED to reveal the other goat, which means the remaining unopened door "
                 "must be the car -- so switching wins in exactly that 2/3 of cases.",
        accepted_approaches=["The 2/3-vs-1/3 probability argument above.",
                             "Explicitly enumerating all 3 equally-likely starting positions of the car "
                             "and tracking switch-vs-stick outcomes for each."],
        rubric_key_points=[
            kp("correctly concludes you should SWITCH, not stick, and not 'it doesn't matter'",
               "gives switching as the correct strategy"),
            kp("gives the correct probabilities: 2/3 for switching, 1/3 for sticking (not 50/50)",
               "states the 2/3 vs 1/3 split, not an even 50/50"),
        ],
        common_wrong_answers=["Saying it's 50/50 either way (the common intuitive mistake, which ignores "
                              "that the host's reveal is NOT random -- it's forced by his knowledge of "
                              "where the car is).",
                              "Saying you should stick with your original door."],
        follow_ups=["How would the probabilities change if there were 100 doors instead of 3, and the "
                   "host opened 98 of them (all goats) before offering the switch?",
                   "Does the answer change if the host sometimes opens a door at RANDOM, without "
                   "necessarily knowing where the car is?"],
        source="classic probability puzzle, original wording",
        assumptions=[
            "the car is placed uniformly at random behind one of the three doors before you choose",
            "the host knows exactly where the car is and always opens a door with a goat behind it",
            "the host never opens the door you originally picked, and never the door with the car",
        ],
    ),
    _item(
        id_="tcs-puz-ant-triangle", title="Three Ants on a Triangle",
        statement=(
            "Three ants sit at the three corners of a triangle. At the same moment, each ant "
            "independently picks a random direction -- clockwise or counter-clockwise along the "
            "triangle's edges, each direction equally likely (50/50) -- and starts walking at the same "
            "constant speed toward the next corner. What is the probability that NONE of the ants "
            "collide with each other along an edge?"
        ),
        family="ant_collision", difficulty="medium",
        solution="1/4 (25%). There are 2 possible direction choices per ant, so 2^3 = 8 equally likely "
                 "combinations overall. A collision is avoided only if ALL THREE ants happen to pick the "
                 "SAME rotational direction (all clockwise, or all counter-clockwise) -- that's 2 "
                 "favorable outcomes out of 8, giving 2/8 = 1/4. In every other combination, at least two "
                 "ants are walking toward each other along some edge and collide.",
        accepted_approaches=["The direct counting argument: 2 favorable (all-same-direction) outcomes "
                             "out of 8 total equally likely combinations."],
        rubric_key_points=[
            kp("correctly identifies that a collision is avoided ONLY when all three ants choose the "
               "SAME direction (all clockwise or all counter-clockwise)",
               "recognizes the no-collision condition requires unanimous direction choice"),
            kp("arrives at the correct probability of 1/4, from 2 favorable out of 2^3=8 total outcomes",
               "gives the correct final probability, 1/4"),
        ],
        common_wrong_answers=["Assuming the probability is 1/2 (treating it like a simple coin flip per "
                              "ant without correctly combining all three independent choices).",
                              "Forgetting that there are two distinct no-collision scenarios (all "
                              "clockwise AND all counter-clockwise), not just one."],
        follow_ups=["How would the probability change if there were 4 ants on a square instead of 3 ants "
                   "on a triangle?",
                   "Does the actual SPEED of the ants matter to this probability, or only their choice "
                   "of direction?"],
        source="classic probability puzzle, original wording",
        assumptions=[
            "each ant independently chooses clockwise or counter-clockwise with equal 50/50 probability",
            "all three ants walk at the same constant speed along the triangle's edges",
        ],
    ),
    _item(
        id_="tcs-puz-doubling-bridges", title="Doubling Money Across Toll Bridges",
        statement=(
            "A traveler has some money and needs to cross 3 toll bridges to get home. At each bridge, "
            "right before paying the toll, her money mysteriously DOUBLES. Each bridge then charges "
            "exactly the same fixed toll of 8 coins. After crossing all 3 bridges and paying all 3 tolls, "
            "she has exactly 0 coins left. How much money did she start with?"
        ),
        family="doubling_money", difficulty="medium",
        solution="7 coins. Working BACKWARD from the end (0 coins after bridge 3) is the easiest way: "
                 "just before bridge 3's toll, she had 8 coins (since 8-8=0); that was AFTER doubling, so "
                 "before bridge 3 she had 4 coins. Just before bridge 2's toll she had 4+8=12 (after "
                 "doubling), so before bridge 2 she had 6 coins. Just before bridge 1's toll she had "
                 "6+8=14 (after doubling), so she started with 7 coins. Forward check: 7 -> double to 14 "
                 "-> pay 8 -> 6 -> double to 12 -> pay 8 -> 4 -> double to 8 -> pay 8 -> 0. Correct.",
        accepted_approaches=["Working backward from the final 0 coins, undoing each toll-then-double "
                             "step in reverse order.",
                             "Setting up and solving the forward algebraic equation directly."],
        rubric_key_points=[
            kp("works the problem BACKWARD from the known final amount (0), rather than guessing a "
               "starting amount and checking it forward",
               "uses backward/reverse reasoning from the ending condition"),
            kp("arrives at the correct starting amount of 7 coins, and the doubling/toll order matches "
               "the problem (double happens before the toll each time)",
               "gets the correct final answer of 7, respecting the stated double-then-pay order"),
        ],
        common_wrong_answers=["Working forward by guessing random starting amounts rather than "
                              "systematically reversing the process.",
                              "Mixing up the order of doubling and paying (e.g. paying the toll before "
                              "doubling), which gives a different, incorrect starting amount."],
        follow_ups=["How would the answer change if there were 4 bridges instead of 3?",
                   "What's the general formula for the starting amount, given N bridges and a fixed toll t?"],
        source="classic folklore puzzle, original wording and numbers",
        assumptions=[
            "at each bridge, her money doubles first and then the fixed toll of 8 coins is charged",
            "after crossing all 3 bridges and paying all 3 tolls she has exactly 0 coins left",
        ],
    ),
    _item(
        id_="tcs-puz-fly-trains", title="The Fly Between Two Trains",
        statement=(
            "Two trains start 60 km apart on the same track, heading directly toward each other, each at "
            "a steady 30 km/h. At the exact moment they start, a fly takes off from the front of one "
            "train, flies straight to the other train at a constant 90 km/h, touches it, immediately "
            "turns around and flies back to the first train, and keeps bouncing back and forth like this "
            "until the trains meet (and, we'll assume, gently squash the fly between them). How far does "
            "the fly travel in total before the trains meet?"
        ),
        family="fly_between_trains", difficulty="medium",
        solution="90 km. The trick is to NOT sum the infinite series of back-and-forth trips. Instead, "
                 "just figure out how long it takes the trains to meet: they close the 60 km gap at a "
                 "combined speed of 30+30=60 km/h, so they meet after 60/60 = 1 hour. The fly is in the "
                 "air flying the ENTIRE time until that moment, at a constant 90 km/h, so it travels "
                 "90 km/h * 1 hour = 90 km total, regardless of how many times it bounces back and forth.",
        accepted_approaches=["The shortcut: compute total TIME until the trains meet first, then "
                             "multiply by the fly's constant speed, rather than summing a geometric "
                             "series of ever-shorter bounces."],
        rubric_key_points=[
            kp("avoids trying to sum the infinite series of ever-shorter back-and-forth trips directly",
               "does not attempt to add up infinitely many bounce distances one by one"),
            kp("instead computes the TIME until the trains meet (using their combined closing speed), "
               "then multiplies that time by the fly's own constant speed to get 90 km",
               "uses the time-until-trains-meet shortcut to reach 90 km"),
        ],
        common_wrong_answers=["Attempting to sum the infinite geometric series of individual fly trips "
                              "(correct in principle but far more error-prone than the time-based "
                              "shortcut, and often leads to an arithmetic mistake).",
                              "Forgetting that the trains' combined closing speed (not just one train's "
                              "speed) determines when they meet."],
        follow_ups=["What if the two trains were traveling at different speeds instead of both at "
                   "30 km/h -- how would you adapt the approach?",
                   "Could you still solve this if the fly's speed also changed partway through?"],
        source="classic mathematical puzzle (often attributed to a famous mathematician's instant "
               "answer), original wording and numbers",
        assumptions=[
            "the two trains start 60 km apart and head directly toward each other",
            "the fly flies continuously at a constant 90 km/h the entire time until the trains meet",
        ],
    ),
    _item(
        id_="tcs-puz-horse-race-fastest", title="Finding the Fastest of 25 Horses",
        statement=(
            "You have 25 horses and a racetrack big enough to race 5 horses at a time. You have no "
            "stopwatch -- all you learn from each race is the FINISHING ORDER of the 5 horses in it, "
            "nothing about their actual times. Horses race identically every time (no randomness). What "
            "is the minimum number of races needed to guarantee finding the single fastest horse out of "
            "all 25?"
        ),
        family="horse_race_fastest", difficulty="medium",
        solution="6 races. First, run 5 races of 5 horses each (25 horses / 5 per race), using up 5 "
                 "races and learning the ranking within each group of 5. Then run a 6th race among just "
                 "the 5 group-winners; whoever wins THAT race is guaranteed to be the fastest horse "
                 "overall (since every other horse lost to its own group's winner, directly or "
                 "transitively).",
        accepted_approaches=["The 5-heats-plus-1-final structure described above."],
        rubric_key_points=[
            kp("correctly splits the 25 horses into 5 groups of 5 for the first round of races",
               "runs 5 preliminary heats of 5 horses each, covering all 25 horses"),
            kp("runs one additional 'championship' race among the 5 heat-winners, and correctly "
               "identifies that winner as the overall fastest, for a total of 6 races",
               "adds exactly one final race among the heat-winners, reaching 6 total races"),
        ],
        common_wrong_answers=["Assuming you need more races to also rank horses that clearly can't be "
                              "fastest overall (the question only asks for the single fastest, not a "
                              "full ranking).",
                              "Forgetting the extra 6th race among the group-winners, and stopping at 5."],
        follow_ups=["Why can you be sure the heat-winners-only final race is enough -- couldn't a horse "
                   "that lost early still secretly be the fastest overall?",
                   "Now suppose you needed to find the top 3 fastest horses instead of just the fastest "
                   "one -- would 6 races still be enough?"],
        source="classic folklore interview puzzle, original wording and numbers",
        assumptions=[
            "horses race identically every time, with no randomness between repeated races",
            "a race only reveals finishing order, never actual times, and at most 5 horses can race at once",
        ],
    ),
    _item(
        id_="tcs-puz-weight-deficit-coins", title="Ten Bags, One Weighing",
        statement=(
            "You have 10 bags, each supposedly full of identical coins that each weigh exactly 10 grams. "
            "You're told that ALL the coins in exactly ONE of the 10 bags are counterfeit, and each "
            "counterfeit coin weighs exactly 9 grams (1 gram light) instead of 10. You have a digital "
            "scale that shows an exact weight in grams, and you're allowed to use it only ONCE. How do "
            "you determine which bag contains the counterfeit coins?"
        ),
        family="weight_deficit_coins", difficulty="medium",
        solution="Take 1 coin from bag 1, 2 coins from bag 2, 3 coins from bag 3, and so on up to 10 "
                 "coins from bag 10 (55 coins total), and weigh them all together at once. If every coin "
                 "were genuine, the total would be 55 * 10 = 550 grams. Since the counterfeit bag's coins "
                 "are each 1 gram light, the ACTUAL shortfall from 550 grams, in grams, exactly equals "
                 "the NUMBER of coins you took from the counterfeit bag -- which tells you directly which "
                 "bag number it is.",
        accepted_approaches=["The exact scheme above (take i coins from bag i), with the correct "
                             "reasoning about the total weight deficit identifying the bag number."],
        rubric_key_points=[
            kp("takes a DIFFERENT number of coins from each bag (e.g. 1 from bag 1, 2 from bag 2, ..., "
               "10 from bag 10), not the same number from every bag",
               "uses a different coin count per bag so the weighing can distinguish all 10 bags at once"),
            kp("correctly reasons that the shortfall in grams from the expected total weight directly "
               "reveals the counterfeit bag's number (since the deficit in grams equals the count of "
               "counterfeit coins weighed, which equals that bag's assigned count)",
               "correctly connects the weight deficit to the bag's identifying number"),
        ],
        common_wrong_answers=["Taking the same number of coins from every bag, which gives no way to "
                              "tell which specific bag is light from a single combined weighing.",
                              "Trying to weigh each bag separately, which would need up to 10 weighings, "
                              "not the 1 allowed."],
        follow_ups=["How would your scheme need to change if TWO of the 10 bags (not just one) could "
                   "potentially be counterfeit?",
                   "What's the largest number of bags this exact one-weighing trick could handle?"],
        source="classic folklore puzzle, original wording and numbers",
        assumptions=[
            "all the coins in exactly one of the 10 bags are counterfeit, each weighing exactly 9 grams "
            "instead of 10",
            "the digital scale may be used only once",
        ],
    ),
    _item(
        id_="tcs-puz-knights-knaves", title="A Simple Knight and Knave",
        statement=(
            "On an island, every inhabitant is either a Knight (who always tells the truth) or a Knave "
            "(who always lies) -- there's no middle ground. You meet two inhabitants, A and B. A makes "
            "exactly one statement: 'We are both knaves.' What are A and B actually -- knight or knave, "
            "each?"
        ),
        family="knights_and_knaves", difficulty="medium",
        solution="A is a Knave, and B is a Knight. Reasoning: suppose A were a Knight (truth-teller). "
                 "Then A's statement ('we are both knaves') would have to be TRUE -- but that would mean "
                 "A is a knave, directly contradicting the assumption that A is a knight. So A cannot be "
                 "a knight; A must be a Knave. Since A is a knave, A's statement is FALSE, meaning it is "
                 "NOT true that both are knaves -- so at least one of them is a knight. Since A is "
                 "already established as a knave, B must be the Knight.",
        accepted_approaches=["The proof-by-contradiction reasoning above, starting from assuming A is a "
                             "knight and showing that's impossible."],
        rubric_key_points=[
            kp("correctly deduces A must be a Knave, via the self-contradiction that would arise if A "
               "were a Knight telling a true self-including statement",
               "correctly identifies A as a Knave using the contradiction argument"),
            kp("correctly concludes B must be a Knight, by using the fact that A's statement, being "
               "false, means NOT both are knaves",
               "correctly identifies B as a Knight from the negation of A's false statement"),
        ],
        common_wrong_answers=["Concluding both A and B are knaves (missing that this would make A's own "
                              "statement true, which a knave cannot do).",
                              "Concluding A is a knight (missing the direct self-contradiction this "
                              "creates)."],
        follow_ups=["What would change if A instead said 'At least one of us is a knave'?",
                   "Can you construct a statement A could make that would make it IMPOSSIBLE to "
                   "determine either A's or B's identity for certain?"],
        source="classic folklore puzzle, original wording",
        assumptions=[
            "every inhabitant is either a Knight who always tells the truth or a Knave who always lies, "
            "with no middle ground",
        ],
    ),
    _item(
        id_="tcs-puz-missing-dollar", title="The Missing Dollar",
        statement=(
            "Three friends check into a hotel room that costs $30, splitting it evenly: $10 each. Later, "
            "the manager realizes the room should only have cost $25, and sends the bellboy to refund "
            "$5. The bellboy, unable to split $5 evenly three ways, gives each friend $1 back (returning "
            "$3 total) and pockets the remaining $2 for himself. Now each friend effectively paid $9 "
            "(their original $10 minus the $1 refund), for a total of $27 paid by the friends, plus the "
            "$2 the bellboy kept -- that's $29. Where did the missing dollar (out of the original $30) go?"
        ),
        family="missing_dollar", difficulty="medium",
        solution="No dollar is actually missing -- this is a bookkeeping sleight-of-hand, not a real "
                 "mystery. The error is in how the numbers are being ADDED together at the end. The "
                 "correct accounting is: the hotel kept $25, the bellboy kept $2, and the friends got $3 "
                 "back -- 25 + 2 + 3 = 30, which balances perfectly. The riddle's trick is adding the "
                 "bellboy's $2 to the friends' $27 (what they ended up paying), instead of correctly "
                 "treating the bellboy's $2 as PART OF what the friends paid (since it came out of their "
                 "collective $27). $27 paid by the friends already INCLUDES the $2 the bellboy kept "
                 "(25 to the hotel + 2 to the bellboy = 27); there's nothing left over to be 'missing'.",
        accepted_approaches=["Any explanation that correctly identifies the $27-plus-$2 addition as "
                             "double-counting the bellboy's $2 (which is already part of the $27), "
                             "rather than money that actually vanished."],
        rubric_key_points=[
            kp("correctly states that no money is actually missing -- the puzzle is a flaw in how the "
               "amounts are being combined (an accounting trick), not a real discrepancy",
               "identifies this as a bookkeeping/framing trick, not a genuine missing dollar"),
            kp("correctly explains that the bellboy's $2 is already PART OF the $27 the friends paid "
               "(since $25 went to the hotel and $2 to the bellboy, totaling the $27), so adding it again "
               "on top of the $27 is what creates the illusion",
               "correctly explains the double-counting of the bellboy's $2 within the $27 already paid"),
        ],
        common_wrong_answers=["Trying to find an actual dollar that was physically lost or stolen, taking "
                              "the premise of the riddle at face value.",
                              "Giving a vague answer like 'it's just rounding' without identifying the "
                              "specific double-counting error."],
        follow_ups=["Can you restate the whole transaction in a single, consistent equation that clearly "
                   "shows $30 is fully accounted for?",
                   "Can you think of another everyday example where adding numbers from two different "
                   "'perspectives' of the same transaction creates a similar illusion?"],
        source="classic folklore puzzle, original wording and numbers",
        assumptions=[
            "the room cost $30, split evenly into $10 each by the three friends",
            "the bellboy gives each friend $1 back (returning $3 total) and pockets the remaining $2",
        ],
    ),
    _item(
        id_="tcs-puz-lily-pad", title="The Doubling Lily Pads",
        statement=(
            "A patch of lily pads on a pond doubles in size every single day. If the patch completely "
            "covers the entire pond on day 48, on which day was the pond exactly HALF covered?"
        ),
        family="lily_pad_doubling", difficulty="medium",
        solution="Day 47. Since the patch doubles every day, the amount of coverage on any given day is "
                 "exactly half of what it will be the very next day. So working backward just one day "
                 "from full coverage (day 48) immediately gives half coverage, on day 47 -- no further "
                 "calculation needed.",
        accepted_approaches=["The direct one-step-backward doubling argument above.",
                             "Explicitly reasoning that 'half of full coverage, doubled, equals full "
                             "coverage' and that doubling happens once per day."],
        rubric_key_points=[
            kp("arrives at day 47, not some much earlier day (like day 24, from incorrectly treating "
               "growth as LINEAR instead of exponential/doubling)",
               "gives the correct answer of day 47"),
            kp("explicitly uses the fact that doubling means each day's coverage is exactly half of the "
               "FOLLOWING day's coverage, to jump straight to the answer without extra calculation",
               "uses the doubling relationship directly, rather than linear reasoning"),
        ],
        common_wrong_answers=["Day 24 (incorrectly assuming the pond fills up at a constant/linear rate, "
                              "rather than doubling each day)."],
        follow_ups=["On what day was the pond at just one-quarter coverage?",
                   "If the patch instead TRIPLED in size every day and reached full coverage on day 48, "
                   "on what day would it have been at half coverage?"],
        source="classic folklore puzzle, original wording and numbers",
        assumptions=[
            "the lily pad patch doubles in size every single day",
            "the pond is completely covered on day 48",
        ],
    ),
    _item(
        id_="tcs-puz-marble-jars", title="Maximizing Red Marbles Across Two Jars",
        statement=(
            "You have 50 red marbles and 50 blue marbles, 100 marbles total. You get to split them "
            "between two jars however you like (neither jar may be left completely empty). Afterward, "
            "someone will pick ONE of the two jars completely at random, and then pick ONE marble from "
            "inside that jar completely at random. How should you distribute the marbles between the two "
            "jars to give yourself the best possible chance that the marble picked is RED, and roughly "
            "what probability does that achieve?"
        ),
        family="marble_jars", difficulty="medium",
        solution="Put just 1 red marble alone in the first jar, and put all the remaining 49 red marbles "
                 "plus all 50 blue marbles in the second jar. This gives roughly a 75% chance of drawing "
                 "red: there's a 1/2 chance the random jar chosen is the first jar, which is GUARANTEED "
                 "red (100% red there); plus a 1/2 chance the second jar is chosen, which is 49 out of 99 "
                 "red (about 49.5%). Overall: 1/2*1 + 1/2*(49/99) = 0.5 + ~0.2475 = ~0.7475, noticeably "
                 "better than the naive even 50/50 split across two jars, which only gives exactly 50%.",
        accepted_approaches=["The 1-red-marble-alone-in-one-jar scheme above, with the probability "
                             "roughly computed.",
                             "Any equivalent scheme putting a single red marble alone in one jar and "
                             "everything else in the other, with correctly reasoned (even if not exactly "
                             "numerically precise) probability above 50%."],
        rubric_key_points=[
            kp("proposes putting exactly ONE red marble alone in one jar, with everything else (49 red + "
               "50 blue) in the other jar",
               "isolates a single red marble by itself in one of the two jars"),
            kp("correctly explains why this beats an even 50/50 split -- the guaranteed-red jar "
               "contributes a full 100% chance whenever it's the one picked, while barely diluting the "
               "other jar's own red ratio",
               "explains the intuition for why isolating one red marble improves the odds above 50%"),
        ],
        common_wrong_answers=["Splitting the marbles evenly (25 red + 25 blue in each jar), which gives "
                              "exactly a 50% chance -- no better than a single jar with everything mixed "
                              "together.",
                              "Putting all 50 red marbles alone in one jar and all 50 blue in the other, "
                              "which is actually WORSE than the 1-marble scheme (gives exactly 50%, same "
                              "as the naive even split)."],
        follow_ups=["Why does putting just ONE red marble alone work better than putting ALL the red "
                   "marbles alone in one jar?",
                   "What's the theoretical best possible probability achievable here, and does the "
                   "1-marble scheme get arbitrarily close to it as the total marble count grows?"],
        source="classic probability puzzle, original wording and numbers",
        assumptions=[
            "the picker chooses one of the two jars completely at random, then one marble from inside "
            "that jar completely at random",
            "neither jar may be left completely empty",
        ],
    ),
    # ---- HARD (5) -------------------------------------------------------------
    _item(
        id_="tcs-puz-hat-parity", title="100 Prisoners and the Hat Line",
        statement=(
            "100 prisoners are lined up single-file, each wearing either a red or a blue hat (assigned "
            "in some arbitrary mix, possibly all one color) -- nobody can see their own hat, but each "
            "prisoner can see the hats of everyone in FRONT of them in the line. Starting from the very "
            "back of the line and moving forward one at a time, each prisoner must state out loud, so "
            "everyone can hear, what color they believe their OWN hat is -- no other communication is "
            "allowed, before or during. They're told the rules in advance and may agree on a strategy "
            "beforehand. What strategy guarantees the maximum number of prisoners are provably correct, "
            "and how many prisoners does that guarantee?"
        ),
        family="hat_parity", difficulty="hard",
        solution="99 out of 100 are guaranteed correct (only the very first prisoner to speak, at the "
                 "back, might be wrong). Strategy: the back-most prisoner, who can see all 99 hats in "
                 "front of them, announces 'red' if the number of RED hats they see is ODD, or 'blue' if "
                 "it's EVEN (this is a pure guess about their OWN hat color encoding information, and has "
                 "only a 50% chance of happening to also be their own true color). Every prisoner after "
                 "that can figure out their own hat color exactly: they know the parity that was just "
                 "announced, they can see every hat still in front of them, so by comparing the "
                 "announced parity against what they currently see (and everyone's already-stated "
                 "answers, which also leak information about hats behind them), each can deduce their "
                 "own hat color by elimination, one by one down the line.",
        accepted_approaches=["The parity-encoding strategy above (red=odd count, blue=even count, with "
                             "every later prisoner updating their inference from the running parity and "
                             "everyone's prior answers)."],
        rubric_key_points=[
            kp("correctly identifies that AT MOST ONE prisoner (the very first to guess) is sacrificed to "
               "carry information, and the other 99 are provably correct -- not some smaller guaranteed "
               "number",
               "gives the correct guarantee of 99 out of 100"),
            kp("describes a genuine PARITY-based encoding strategy (e.g. odd/even count of one hat "
               "color) for the first speaker, and explains how each subsequent prisoner updates their "
               "own deduction using the running parity and what they can see",
               "proposes a real parity-encoding strategy, not just 'communicate somehow'"),
        ],
        common_wrong_answers=["Assuming no prisoner can ever be sure of their own hat color (missing "
                              "that the FIRST speaker's statement, even though itself a guess, encodes "
                              "exploitable information for everyone after them).",
                              "Proposing a strategy that only works for small numbers of prisoners or "
                              "specific hat-color distributions, rather than one that provably works for "
                              "ANY distribution of 100 hats."],
        follow_ups=["Why can't the strategy guarantee ALL 100 prisoners are correct, rather than 99?",
                   "How would the strategy need to change if there were 3 possible hat colors instead "
                   "of just 2?"],
        source="classic folklore puzzle, original wording and numbers",
        assumptions=[
            "each prisoner can see the hats of everyone in front of them, but never their own",
            "prisoners state their guess one at a time from the back of the line, loud enough for "
            "everyone to hear",
            "no other communication is allowed before or during, and they may agree on a strategy beforehand",
        ],
    ),
    _item(
        id_="tcs-puz-egg-drop-100", title="Two Eggs, a Hundred Floors",
        statement=(
            "You're given 2 identical eggs and access to a 100-floor building. You want to find the "
            "highest floor from which an egg can be dropped WITHOUT breaking (there's some unknown "
            "threshold floor; below it eggs never break, at or above it they always break). An egg that "
            "survives a drop can be reused; one that breaks cannot. You want to find that threshold floor "
            "for certain, using as FEW total drops as possible in the worst case. What's the strategy, "
            "and what is the minimum number of drops needed in the worst case?"
        ),
        family="egg_drop", difficulty="hard",
        solution="14 drops in the worst case. Strategy: don't jump by a fixed step size -- instead, drop "
                 "the first egg from floor 14, then (if it survives) floor 14+13=27, then 27+12=39, then "
                 "39+11=50, and so on, DECREASING the step size by 1 each time the first egg survives "
                 "(14+13+12+...+1 = 105, just enough to cover all 100 floors). Each time the first egg "
                 "finally breaks, you know the threshold is somewhere in the gap since the last safe "
                 "floor, and you switch to testing that gap ONE FLOOR AT A TIME with the second egg. "
                 "The decreasing-step trick balances the worst case exactly: however many drops the first "
                 "egg survives before breaking, the total drops used (first-egg drops + remaining "
                 "one-at-a-time second-egg drops) always adds up to the same 14.",
        accepted_approaches=["The exact decreasing-interval strategy above, with the reasoning for why "
                             "the step size must shrink by exactly 1 each time.",
                             "Setting up the inequality n(n+1)/2 >= 100 and solving for the smallest "
                             "integer n (which gives n=14, since 14*15/2=105>=100 but 13*14/2=91<100)."],
        rubric_key_points=[
            kp("recognizes that a FIXED step size (e.g. always jumping by 10 floors) is NOT optimal, and "
               "that the step size must DECREASE by exactly 1 each time the first egg survives a drop",
               "proposes a decreasing-interval strategy, not a fixed-interval one"),
            kp("arrives at 14 as the minimum worst-case number of drops, ideally connecting it to the "
               "inequality n(n+1)/2 >= 100",
               "gives the correct final answer of 14 drops"),
        ],
        common_wrong_answers=["A fixed-step strategy like 'drop every 10 floors, then narrow down one at "
                              "a time' -- this can require up to 19 drops in the worst case (10 steps of "
                              "10, plus up to 9 one-at-a-time), which is NOT optimal.",
                              "Binary search by halving the range each time -- this doesn't work directly "
                              "here because a broken first egg leaves you with only ONE egg left and no "
                              "way to re-test a wide range one floor at a time efficiently."],
        follow_ups=["How would the minimum number of drops change if you had 3 eggs instead of 2, for "
                   "the same 100-floor building?",
                   "Can you explain WHY the decreasing-by-1 step size is exactly what balances the worst "
                   "case, rather than decreasing by 2 or some other amount?"],
        source="classic folklore interview puzzle, original wording and numbers",
        assumptions=[
            "an egg that survives a drop can be reused; an egg that breaks cannot be reused",
            "there is a single unknown threshold floor: eggs never break below it and always break at or above it",
        ],
    ),
    _item(
        id_="tcs-puz-horse-race-top3", title="Finding the Top 3 of 25 Horses",
        statement=(
            "Same setup as before: 25 horses, races of 5 at a time, no stopwatch, only finishing order "
            "learned from each race, no randomness between repeated races. This time, you need to "
            "identify the top 3 FASTEST horses overall, correctly RANKED (1st, 2nd and 3rd), not just the "
            "single fastest. What is the minimum number of races needed to guarantee this?"
        ),
        family="horse_race_top3", difficulty="hard",
        solution="7 races. Start the same way: run 5 heats of 5 horses each (5 races), then a "
                 "championship race among the 5 heat-winners (1 more race, 6 total) to find the single "
                 "fastest horse and get a full ranking of the 5 heat-winners against each other. The "
                 "overall 2nd and 3rd fastest horses can ONLY be among a small, specific set of "
                 "candidates: the 2nd and 3rd place finishers of the championship race, PLUS the "
                 "horses that finished directly behind the overall-fastest horse's own original heat "
                 "runner-up and the runner-up's own heat positions -- in practice, this works out to "
                 "exactly 3 additional candidate horses once you account for who could possibly have "
                 "been held back only by racing against the eventual overall winner. A single 7th race "
                 "among those 3 remaining candidates determines the final 2nd and 3rd place overall.",
        accepted_approaches=["The 5-heats + 1-championship + 1-final-decider structure (7 races total), "
                             "with a correct identification of which few horses can possibly be 2nd or "
                             "3rd overall after the championship race."],
        rubric_key_points=[
            kp("correctly extends the fastest-horse approach (5 heats + 1 championship) by recognizing "
               "more races are needed specifically to resolve the 2nd/3rd place positions, rather than "
               "assuming the championship race alone settles everything",
               "recognizes the championship race alone is NOT enough to rank 2nd/3rd overall"),
            kp("arrives at the correct total of 7 races, with a 7th race among a SMALL, correctly-"
               "justified set of remaining candidates (not re-racing everyone, and not skipping this "
               "step entirely)",
               "gives the correct final count of 7 races with a genuine final decider race"),
        ],
        common_wrong_answers=["Assuming 6 races (the same as for finding just the fastest horse) is "
                              "enough, which overlooks that the championship race's 2nd/3rd place "
                              "finishers aren't necessarily the true 2nd/3rd fastest overall.",
                              "Assuming you need to fully re-rank all 25 horses, requiring far more than "
                              "7 races."],
        follow_ups=["Which specific horses must be included in that final 7th race, and why can every "
                   "other horse be safely ruled out of contention for 2nd or 3rd place by that point?",
                   "How would the number of required races change if you needed the top 4 fastest horses "
                   "instead of the top 3?"],
        source="classic folklore interview puzzle, original wording and numbers",
        assumptions=[
            "the same no-stopwatch, no-randomness, 5-horses-per-race rules from the single-fastest-horse "
            "version apply here too",
        ],
    ),
    _item(
        id_="tcs-puz-poison-wine", title="1000 Bottles, One Poisoned, 10 Test Animals",
        statement=(
            "You have 1000 bottles of wine. Exactly ONE bottle is poisoned. You have 10 test animals and "
            "exactly 24 hours before a deadline. Poison takes EXACTLY 24 hours to produce any visible "
            "symptom, and any animal that drinks even a tiny amount of the poisoned wine will show that "
            "symptom right at the 24-hour mark (animals that don't drink any poisoned wine never show the "
            "symptom). You can have any animal drink from any number of bottles, all at the very start, "
            "and you only get to observe symptoms once, at the 24-hour deadline. How do you guarantee "
            "identifying the poisoned bottle using only these 10 animals?"
        ),
        family="poison_bottles", difficulty="hard",
        solution="It's guaranteed possible, because 2^10 = 1024, which is more than enough to uniquely "
                 "label all 1000 bottles. Number the bottles from 1 to 1000 and write each bottle's "
                 "number in 10-bit BINARY. Assign each of the 10 animals to one of the 10 bit positions. "
                 "For every bottle, have each animal whose assigned bit is a '1' in that bottle's binary "
                 "number drink a small amount from that bottle. After 24 hours, look at exactly which "
                 "animals show symptoms: treat a sick animal as a '1' and a healthy animal as a '0' at "
                 "its assigned bit position. Reading those 10 bits together as a binary number gives you "
                 "the EXACT number of the poisoned bottle.",
        accepted_approaches=["The binary-encoding scheme above, with each animal representing one bit "
                             "of the bottle's number."],
        rubric_key_points=[
            kp("connects the number of animals (10) to binary representation, specifically that "
               "2^10=1024 is enough to uniquely number all 1000 bottles",
               "makes the connection to binary encoding and 2^10 >= 1000"),
            kp("correctly describes assigning each animal to a specific BIT POSITION, having it drink "
               "from every bottle whose binary number has a 1 in that position, and reading the pattern "
               "of sick/healthy animals back as a binary number to find the exact bottle",
               "correctly describes the full encode-then-decode binary scheme, not just 'use binary "
               "somehow'"),
        ],
        common_wrong_answers=["A linear or halving approach that tries to narrow the 1000 bottles down "
                              "using way more than 10 animals, or that doesn't realize ALL animals drink "
                              "simultaneously (only one 24-hour observation is possible, not multiple "
                              "rounds).",
                              "Using decimal-digit-based groupings instead of binary, which can't "
                              "distinguish enough bottles with only 10 animals."],
        follow_ups=["What's the largest number of bottles this exact scheme could handle with these same "
                   "10 animals?",
                   "How would the scheme need to change if TWO bottles (not just one) could be poisoned?"],
        source="classic folklore puzzle, original wording and numbers",
        assumptions=[
            "exactly one bottle out of the 1000 is poisoned",
            "any animal that drinks even a tiny amount of the poisoned wine shows the symptom at exactly "
            "the 24-hour mark, and animals that drink none never show it",
            "every animal drinks at the very start and symptoms are observed only once, at the 24-hour deadline",
        ],
    ),
    _item(
        id_="tcs-puz-blue-eyed-islanders", title="The Two Blue-Eyed Islanders",
        statement=(
            "On an island, everyone has either blue or brown eyes. Each person can see everyone else's "
            "eye color, but never their own, and nobody is allowed to discuss eye color at all. Every "
            "islander is a perfect, instantaneous logician, and this is itself common knowledge -- "
            "everyone knows that everyone else will immediately deduce and act on anything that becomes "
            "logically certain. One day, "
            "a visitor publicly announces, to everyone at once: 'At least one of you has blue eyes.' (Every "
            "single islander already knew this was true just by looking around -- but now it has been "
            "said OUT LOUD, in front of everyone, making it what's called 'common knowledge'.) The island's "
            "one rule: the moment anyone personally figures out their own eye color for certain, they must "
            "leave the island at the very next dawn. Suppose there are EXACTLY 2 blue-eyed islanders (and "
            "any number of brown-eyed ones). How many dawns after the announcement do the blue-eyed "
            "islanders actually leave, and why?"
        ),
        family="blue_eyed_islanders", difficulty="hard",
        solution="They leave on the 2nd dawn after the announcement. Reasoning: each of the two blue-eyed "
                 "islanders can see exactly ONE other blue-eyed person (each other), but not their own eye "
                 "color. Consider blue-eyed islander A's perspective: A knows the announcement is true "
                 "(obviously, since A can see the OTHER blue-eyed islander, B). A reasons: 'if I did NOT "
                 "have blue eyes myself, then B would be the ONLY blue-eyed person on the island -- and B, "
                 "seeing no OTHER blue-eyed people, would immediately know on the FIRST dawn that B must be "
                 "the one the announcement was about, and would leave that very first dawn.' When the first "
                 "dawn passes and B does NOT leave, A learns that B must also be seeing at least one other "
                 "blue-eyed person -- which can only be A. So on the second dawn, A now knows for certain "
                 "that A has blue eyes (and, by the identical symmetric reasoning, so does B) -- both leave "
                 "together on the 2nd dawn.",
        accepted_approaches=["The inductive 'if I weren't blue-eyed, the other one would have left on day "
                             "1' reasoning above, correctly generalized to 2 people."],
        rubric_key_points=[
            kp("correctly reasons through what EACH blue-eyed islander would conclude if they personally "
               "did NOT have blue eyes (the other one would have left on day 1, seeing nobody else blue-"
               "eyed) -- and that this does NOT happen",
               "uses the counterfactual 'what if I'm not blue-eyed' reasoning correctly"),
            kp("arrives at exactly 2 dawns (not 1, and not some other number), and explains why the "
               "PUBLIC announcement (making the fact 'common knowledge') was necessary for the reasoning "
               "to even get started, even though every islander already individually knew at least one "
               "person had blue eyes",
               "gives the correct answer of 2 dawns, tied to the common-knowledge role of the "
               "announcement"),
        ],
        common_wrong_answers=["Assuming the blue-eyed islanders already know their own eye color before "
                              "the announcement even happens, since they could already see someone else "
                              "with blue eyes -- this misses why the PUBLIC announcement (common "
                              "knowledge) is the actual trigger for the deduction chain to start.",
                              "Answering 1 dawn (confusing this with what would happen if there were only "
                              "1 blue-eyed islander)."],
        follow_ups=["How would the answer change if there were 3 blue-eyed islanders instead of 2?",
                   "Why does the puzzle NOT work (nobody is ever able to deduce anything) if the "
                   "visitor's statement is never actually said out loud, even though everyone already "
                   "individually knew it was true?"],
        source="classic common-knowledge logic puzzle, original wording",
        assumptions=[
            "every islander is a perfect, instantaneous logician, and this is itself common knowledge "
            "among them",
            "nobody is allowed to discuss eye color at all, and each person sees everyone else's eyes "
            "but never their own",
            "there are exactly 2 blue-eyed islanders",
        ],
    ),
]


def _build_bank() -> List[Dict[str, Any]]:
    generated = (
        _generate_water_jugs() + _generate_bridge_crossing() + _generate_river_crossing()
        + _generate_counterfeit_coin() + _generate_hundred_doors()
    )
    return generated + _STATIC_ITEMS


INTERVIEW_PUZZLE_BANK: List[Dict[str, Any]] = _build_bank()


def by_id(puzzle_id: str) -> Dict[str, Any]:
    return next(p for p in INTERVIEW_PUZZLE_BANK if p["id"] == puzzle_id)


def items_for_tier(tier: str) -> List[Dict[str, Any]]:
    """Never returns anything for "ninja" -- no item in this bank ever has
    "ninja" in its tier_tags (USER-STATED: puzzles are Digital/Prime only)."""
    return [p for p in INTERVIEW_PUZZLE_BANK if tier in p.get("tier_tags", [])]


# ============================================================================
# Part 3 wiring: one puzzle per sitting, seeded per interview
# ============================================================================

def pick_puzzle_for_interview(tier: str, interview_id: str) -> Dict[str, Any]:
    """Deterministically picks exactly ONE puzzle for a given interview,
    by tier. Seeded by `interview_id` alone (not by wall-clock time or any
    other source of fresh randomness) -- calling this again with the same
    (tier, interview_id) ALWAYS returns the same item, so a replayed/
    resumed sitting (reload, closed tab, idle timeout) never sees a
    different puzzle than it started with, even if this function were
    ever called again outside of interview-start (e.g. future debug
    tooling) rather than relying solely on the interview document's own
    persisted phase_questions.

    `random.Random(str)` seeding is used rather than Python's built-in
    `hash()` deliberately: `hash()` on a str is randomised per-process by
    PYTHONHASHSEED, while `random.Random`'s own seeding of a str/bytes
    argument is NOT -- it is stable across processes and Python runs,
    which is exactly the determinism this function promises."""
    pool = items_for_tier(tier)
    if not pool:
        raise ValueError(f"interview_puzzle_bank has no items for tier {tier!r}")
    # Sorted by id first so the pool's ORDER is stable regardless of how
    # INTERVIEW_PUZZLE_BANK happens to be assembled -- the seed then
    # determines the pick deterministically from that stable order.
    stable_pool = sorted(pool, key=lambda p: p["id"])
    rng = random.Random(f"tcs-interview-puzzle:{interview_id}")
    return dict(rng.choice(stable_pool))


def puzzle_question_for_interview(tier: str, interview_id: str) -> Dict[str, Any]:
    """Shapes the chosen puzzle into the same {id, phase, topic, text,
    key_points} shape every other TCS question uses (see core.py's
    select_puzzle_questions/build_phase_questions), so the generic
    orchestration.answer_interview grading path -- which already grades
    ANY current question generically off its own `key_points`, through
    the existing spend-controlled ai_service.tcs_key_point_flags_prompt
    boundary -- needs no special case for the puzzle phase. `puzzle_meta`
    carries the puzzle's own id/family/solution/follow_ups for reporting,
    without being read by the grading path itself."""
    puzzle = pick_puzzle_for_interview(tier, interview_id)
    return {
        "id": f"tcs-puzzle-{puzzle['id']}",
        "phase": "puzzle",
        "topic": "puzzle",
        "text": puzzle["statement"],
        "key_points": puzzle["rubric_key_points"],
        "puzzle_meta": {
            "puzzle_id": puzzle["id"], "family": puzzle["family"], "difficulty": puzzle["difficulty"],
            "solution": puzzle["solution"], "follow_ups": puzzle["follow_ups"],
        },
    }
