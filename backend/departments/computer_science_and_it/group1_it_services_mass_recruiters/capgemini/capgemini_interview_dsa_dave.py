# -*- coding: utf-8 -*-
"""Dave interview Medium DSA problems and rubrics (Capgemini Dave tier only).

14 Medium-difficulty problems, none used by Round 3 (debugging_bank), Round 4
(ai_assisted_bank) or the Spark DSA bank (capgemini_interview_dsa.py) -- see
the audit in the build report. Copied from banks/problem_bank.py's _RAW,
unmodified, except: two input_format strings that document an existing
omit-the-line-when-the-count-is-0 convention for a count that can legitimately
be 0 under that problem's own constraints (dp-longest-increasing-subsequence's
n, graph-bipartite-check's m; both references already handle it correctly),
and greedy-min-platforms's reference_solution (see KNOWN DIVERGENCE below).
problem_bank.py itself is not touched.

KNOWN DIVERGENCE from problem_bank.py: greedy-min-platforms's reference_solution
here uses `arr[i] < dep[j]` (strict) where problem_bank.py's own copy uses
`arr[i] <= dep[j]`. The <= version miscounts a platform as still occupied when
a train's arrival exactly coincides with another's departure, even though the
problem's own statement says that departure "frees the platform in time" --
confirmed wrong against a new test ('2\n100 200\n200 300', expects 1; the <=
version returns 2). This copy fixes it; problem_bank.py was NOT touched (out
of this module's scope) and still has the original <= bug. greedy-min-platforms
is sampled generically by banks.problem_bank.sample_problems() (no exclusion
for it), so the bug IS reachable in the OA wherever a Medium-difficulty problem
can be drawn -- but it is currently LATENT, not live: none of problem_bank.py's
own 5 stored test_inputs for this problem have an arrival time exactly equal to
a departure time, so the existing graded test suite never exercises the <=/<
boundary and no candidate is being mis-scored by it today. It would become live
the moment a test case (stored or generated) hits that exact boundary. Reported,
not fixed, pending the repo owner's decision.

Every rubric's required_approach is exactly two items: (a) correctness -- any
valid algorithm, phrased as something a candidate would say; (b) efficiency --
the specific approach named in accepted_complexities as the more efficient
one. accepted_complexities lists time/space for every approach accepted under
(a), keyed by approach name, so the complexity-grading stage can judge
"correct" against whichever approach the candidate actually described (e.g.
a hash-set approach stating O(n) space is correct; a two-pointer approach
stating O(1) space is also correct -- they are different accepted approaches,
not a single "the" answer).

Every reference solution was re-run through services/code_runner.run_python on
every test input before this file was written. The "check" field says how the
expected outputs were established.
"""

DAVE_DSA_PROBLEMS = [{'id': 'product-except-self',
  'title': 'Product of Array Except Self',
  'topic': 'arrays',
  'difficulty': 'Medium',
  'statement': 'Given an array, print an array where element i is the product of all other elements. Do NOT '
               'use division.',
  'input_format': 'Line 1: n. Line 2: n integers.',
  'output_format': 'n space-separated integers.',
  'constraints': '2 ≤ n ≤ 10^5',
  'reference_solution': 'n = int(input())\n'
                        'a = list(map(int, input().split()))\n'
                        'out = [1] * n\n'
                        'p = 1\n'
                        'for i in range(n):\n'
                        '    out[i] = p; p *= a[i]\n'
                        'p = 1\n'
                        'for i in range(n - 1, -1, -1):\n'
                        '    out[i] *= p; p *= a[i]\n'
                        "print(' '.join(map(str, out)))\n",
  'test_inputs': ['4\n1 2 3 4', '5\n-1 1 0 -3 3', '2\n2 3', '3\n1 1 1', '5\n2 3 4 5 6'],
  'expected_outputs': ['24 12 8 6', '0 0 9 0 0', '3 2', '1 1 1', '360 240 180 144 120'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py (unmodified)',
  'rubric': {'required_approach': ['Describes a correct way to compute each element as the product of all '
                                   'the others without division: a single pass building running prefix and '
                                   'suffix products (the optimal approach), building separate prefix and '
                                   'suffix arrays first, directly multiplying all the other elements for '
                                   'each index (brute force), or any other correct approach.',
                                   'Reaches the single-pass prefix/suffix approach using O(1) extra space '
                                   'besides the output, not two separate O(n)-space prefix/suffix arrays or '
                                   'the O(n^2) brute-force multiplication.'],
             'accepted_complexities': {'prefix_suffix_one_pass': {'time': 'O(n)',
                                                                  'space': 'O(1) extra, besides the output '
                                                                           'array'},
                                       'two_arrays_prefix_suffix': {'time': 'O(n)', 'space': 'O(n) extra'},
                                       'brute_force_nested': {'time': 'O(n^2)', 'space': 'O(1) extra'}},
             'edge_cases': ['exactly one zero in the array',
                            'more than one zero (every output is 0)',
                            'negative numbers'],
             'common_mistakes': ['Using division and special-casing zero (the problem forbids division)',
                                 'Off-by-one in the prefix or suffix loop bounds']}},
 {'id': 'search-rotated',
  'title': 'Search in Rotated Sorted Array',
  'topic': 'arrays',
  'difficulty': 'Medium',
  'statement': 'Given a sorted array rotated at an unknown pivot, find the index of target or print -1. '
               'O(log n).',
  'input_format': 'L1: n. L2: n ints. L3: target.',
  'output_format': 'Index or -1.',
  'constraints': '1 ≤ n ≤ 10^4',
  'reference_solution': 'n = int(input())\n'
                        'a = list(map(int, input().split()))\n'
                        't = int(input())\n'
                        'l, r = 0, n - 1; ans = -1\n'
                        'while l <= r:\n'
                        '    m = (l + r) // 2\n'
                        '    if a[m] == t: ans = m; break\n'
                        '    if a[l] <= a[m]:\n'
                        '        if a[l] <= t < a[m]: r = m - 1\n'
                        '        else: l = m + 1\n'
                        '    else:\n'
                        '        if a[m] < t <= a[r]: l = m + 1\n'
                        '        else: r = m - 1\n'
                        'print(ans)\n',
  'test_inputs': ['7\n4 5 6 7 0 1 2\n0',
                  '7\n4 5 6 7 0 1 2\n3',
                  '1\n1\n0',
                  '5\n5 1 2 3 4\n1',
                  '7\n6 7 0 1 2 4 5\n5',
                  '5\n1 2 3 4 5\n3'],
  'expected_outputs': ['4', '-1', '-1', '1', '6', '2'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py (unmodified)',
  'rubric': {'required_approach': ['Describes a correct way to find the target in a rotated sorted array: a '
                                   'binary search that works out which half is properly sorted at each step '
                                   'and searches the half that could contain the target; a linear scan '
                                   'checking every element (correct, but note that it does NOT meet the '
                                   "problem statement's own stated O(log n) requirement); or any other "
                                   'correct approach.',
                                   'Reaches the O(log n) binary-search approach, not an O(n) linear scan.'],
             'accepted_complexities': {'binary_search': {'time': 'O(log n)', 'space': 'O(1)'},
                                       'linear_scan': {'time': 'O(n)', 'space': 'O(1)'}},
             'edge_cases': ['target not present (print -1)',
                            'array of length 1',
                            'array not actually rotated (pivot at index 0)',
                            'target equal to a boundary element'],
             'common_mistakes': ['Deciding which half is sorted by comparing against the wrong boundary '
                                 '(a[l]/a[r] of the current window, not a[0]/a[n-1])',
                                 'Using the wrong comparison operator when checking if the target lies in '
                                 'the sorted half']}},
 {'id': 'longest-palindromic',
  'title': 'Longest Palindromic Substring Length',
  'topic': 'strings',
  'difficulty': 'Medium',
  'statement': 'Print the length of the longest palindromic substring.',
  'input_format': 'Single line string.',
  'output_format': 'Integer length.',
  'constraints': '1 ≤ |s| ≤ 1000',
  'reference_solution': 's = input(); n = len(s); best = 1\n'
                        'def expand(l, r):\n'
                        '    while l >= 0 and r < n and s[l] == s[r]: l -= 1; r += 1\n'
                        '    return r - l - 1\n'
                        'for i in range(n):\n'
                        '    best = max(best, expand(i, i), expand(i, i + 1))\n'
                        'print(best)\n',
  'test_inputs': ['babad', 'cbbd', 'a', 'ac', 'racecar'],
  'expected_outputs': ['3', '2', '1', '1', '7'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py (unmodified)',
  'rubric': {'required_approach': ['Describes a correct way to find the longest palindromic substring: '
                                   'expanding outward from each possible center (both odd-length and '
                                   'even-length centers), filling a DP table of which substrings are '
                                   'palindromes, checking every substring directly for being a '
                                   'palindrome, or any other correct approach.',
                                   'Reaches an O(n^2) approach (expand-around-center or the DP table), not '
                                   'checking every substring directly (O(n^3)).'],
             'accepted_complexities': {'expand_around_center': {'time': 'O(n^2)', 'space': 'O(1)'},
                                       'dp_table': {'time': 'O(n^2)', 'space': 'O(n^2)'},
                                       'brute_force_all_substrings': {'time': 'O(n^3)', 'space': 'O(1)'}},
             'edge_cases': ['single-character string',
                            'the entire string is a palindrome',
                            'no palindrome longer than length 1',
                            'an even-length palindrome (center between two characters)'],
             'common_mistakes': ['Only checking odd-length centers and missing even-length palindromes',
                                 'Off-by-one when computing the length from the expanded left/right '
                                 'pointers']}},
 {'id': 'tree-diameter',
  'title': 'Diameter of Binary Tree',
  'topic': 'trees',
  'difficulty': 'Medium',
  'statement': "Given a binary tree as a level-order list ('N' = missing child), print its diameter: the "
               'number of edges on the longest path between any two nodes (the path may or may not pass '
               'through the root).',
  'input_format': "Single line: level-order values with 'N' for null.",
  'output_format': 'Single integer.',
  'constraints': '1 <= number of real nodes <= 1000',
  'reference_solution': 'from collections import deque\n'
                        'class N:\n'
                        '    def __init__(self, v):\n'
                        '        self.v = int(v); self.l = None; self.r = None\n'
                        'def build(vals):\n'
                        "    if not vals or vals[0] == 'N':\n"
                        '        return None\n'
                        '    root = N(vals[0]); q = deque([root]); i = 1\n'
                        '    while q and i < len(vals):\n'
                        '        node = q.popleft()\n'
                        "        if i < len(vals) and vals[i] != 'N':\n"
                        '            node.l = N(vals[i]); q.append(node.l)\n'
                        '        i += 1\n'
                        "        if i < len(vals) and vals[i] != 'N':\n"
                        '            node.r = N(vals[i]); q.append(node.r)\n'
                        '        i += 1\n'
                        '    return root\n'
                        'vals = input().split()\n'
                        'root = build(vals)\n'
                        'best = 0\n'
                        'def depth(n):\n'
                        '    global best\n'
                        '    if n is None: return 0\n'
                        '    l = depth(n.l); r = depth(n.r)\n'
                        '    best = max(best, l + r)\n'
                        '    return 1 + max(l, r)\n'
                        'depth(root)\n'
                        'print(best)\n',
  'test_inputs': ['3 9 20 N N 15 7', '1', '1 2 N N 3', '1 2 3 4 5', '5 3 8 1 4 7 9'],
  'expected_outputs': ['3', '0', '2', '3', '4'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py (unmodified)',
  'rubric': {'required_approach': ["Describes a correct way to find the tree's diameter: a single post-order "
                                   "traversal that returns each subtree's height while tracking the best "
                                   'left-height-plus-right-height sum seen at any node; recomputing the '
                                   'height of the left and right subtrees separately for every node; or any '
                                   'other correct approach.',
                                   'Reaches the single O(n) post-order pass, not recomputing height from '
                                   'scratch at every node (O(n^2) on a skewed tree).'],
             'accepted_complexities': {'single_post_order_pass': {'time': 'O(n)',
                                                                  'space': 'O(H) recursion depth'},
                                       'recompute_height_per_node': {'time': 'O(n^2)',
                                                                     'space': 'O(H) recursion depth'}},
             'edge_cases': ['a single-node tree (diameter 0)',
                            'a skewed/linear tree (diameter = n-1 edges)',
                            'the longest path does not pass through the root'],
             'common_mistakes': ['Counting nodes on the path instead of edges',
                                 'Only checking the diameter candidate at the root instead of at every '
                                 'node']}},
 {'id': 'tree-kth-smallest-bst',
  'title': 'Kth Smallest Element in a BST',
  'topic': 'trees',
  'difficulty': 'Medium',
  'statement': "A valid binary search tree is given as a level-order list ('N' = missing child) on the first "
               'line, and an integer k on the second line. Print the k-th smallest value in the tree (k=1 is '
               'the smallest).',
  'input_format': "Line 1: level-order values with 'N' for null (guaranteed a valid BST). Line 2: k.",
  'output_format': 'Single integer.',
  'constraints': '1 <= k <= number of nodes',
  'reference_solution': 'from collections import deque\n'
                        'class N:\n'
                        '    def __init__(self, v):\n'
                        '        self.v = int(v); self.l = None; self.r = None\n'
                        'def build(vals):\n'
                        "    if not vals or vals[0] == 'N':\n"
                        '        return None\n'
                        '    root = N(vals[0]); q = deque([root]); i = 1\n'
                        '    while q and i < len(vals):\n'
                        '        node = q.popleft()\n'
                        "        if i < len(vals) and vals[i] != 'N':\n"
                        '            node.l = N(vals[i]); q.append(node.l)\n'
                        '        i += 1\n'
                        "        if i < len(vals) and vals[i] != 'N':\n"
                        '            node.r = N(vals[i]); q.append(node.r)\n'
                        '        i += 1\n'
                        '    return root\n'
                        'vals = input().split()\n'
                        'root = build(vals)\n'
                        'k = int(input())\n'
                        'res = []\n'
                        'def inorder(n):\n'
                        '    if n is None or len(res) >= k: return\n'
                        '    inorder(n.l)\n'
                        '    if len(res) < k: res.append(n.v)\n'
                        '    inorder(n.r)\n'
                        'inorder(root)\n'
                        'print(res[k-1])\n',
  'test_inputs': ['5 3 8 1 4 7 9\n1', '5 3 8 1 4 7 9\n4', '5 3 8 1 4 7 9\n7', '1\n1', '3 1 4 N 2\n2'],
  'expected_outputs': ['1', '5', '9', '1', '2'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py (unmodified)',
  'rubric': {'required_approach': ['Describes a correct way to find the k-th smallest value in a BST: an '
                                   'in-order traversal (which visits BST values in sorted order), either '
                                   'stopping as soon as the k-th value is reached, collecting all the '
                                   'values first and indexing into them, or any other correct approach.',
                                   'Reaches the early-stopping in-order traversal, not a full in-order '
                                   'traversal that collects every value before indexing.'],
             'accepted_complexities': {'early_stop_inorder': {'time': 'O(H + k)', 'space': 'O(H)'},
                                       'full_inorder_then_index': {'time': 'O(n)', 'space': 'O(n)'}},
             'edge_cases': ['k equals 1 (the minimum)',
                            'k equals the total number of nodes (the maximum)',
                            'a skewed BST'],
             'common_mistakes': ['Traversing in pre-order or post-order instead of in-order, which does not '
                                 'visit values in sorted order',
                                 'Off-by-one between the 1-indexed k and a 0-indexed collected list']}},
 {'id': 'greedy-two-city-scheduling',
  'title': 'Two City Scheduling',
  'topic': 'greedy',
  'difficulty': 'Medium',
  'statement': 'There are 2n people to fly to city A or city B; exactly n must go to each city. Sending '
               'person i to city A costs costA[i], to city B costs costB[i]. Print the minimum total cost to '
               'send everyone while sending exactly n people to each city.',
  'input_format': 'Line 1: n. Line 2: 2n costs to city A. Line 3: 2n costs to city B.',
  'output_format': 'Single integer: minimum total cost.',
  'constraints': '1 <= n <= 500',
  'reference_solution': 'n = int(input())\n'
                        'costA = list(map(int, input().split()))\n'
                        'costB = list(map(int, input().split()))\n'
                        'order = sorted(range(2 * n), key=lambda i: costA[i] - costB[i])\n'
                        'total = 0\n'
                        'for idx, i in enumerate(order):\n'
                        '    if idx < n:\n'
                        '        total += costA[i]\n'
                        '    else:\n'
                        '        total += costB[i]\n'
                        'print(total)\n',
  'test_inputs': ['2\n10 30 400 30\n20 200 50 20',
                  '1\n10 20\n30 40',
                  '3\n1 2 3 4 5 6\n6 5 4 3 2 1',
                  '1\n5 5\n5 5',
                  '2\n100 50 50 100\n50 100 100 50'],
  'expected_outputs': ['110', '50', '12', '10', '200'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py (unmodified)',
  'rubric': {'required_approach': ['Describes a correct way to minimize total cost: sorting people by how '
                                   'much cheaper city A is for them relative to city B, then sending the '
                                   'cheapest-for-A half to A and the rest to B; trying every possible way '
                                   'to split the 2n people into two equal-sized groups and taking the '
                                   'minimum-cost split; or any other correct approach.',
                                   'Reaches the O(n log n) sort-by-cost-difference approach, not trying '
                                   'every possible split.'],
             'accepted_complexities': {'sort_by_cost_difference': {'time': 'O(n log n)', 'space': 'O(n)'},
                                       'brute_force_all_splits': {'time': 'O(C(2n, n)) -- combinatorially '
                                                                          'many splits',
                                                                  'space': 'O(n)'}},
             'edge_cases': ['n = 1 (only two people total)',
                            'a tie in cost difference between two people',
                            'costA and costB identical for everyone'],
             'common_mistakes': ['Sorting by costA or costB alone instead of their difference',
                                 'Sending more or fewer than exactly n people to each city']}},
 {'id': 'greedy-min-platforms',
  'title': 'Minimum Platforms Needed',
  'topic': 'greedy',
  'difficulty': 'Medium',
  'statement': 'A railway station has n trains with given arrival and departure times. Print the minimum '
               'number of platforms needed so that no train ever has to wait (a platform can be reused once '
               'the train on it departs, and a departure at the same time as another arrival frees the '
               'platform in time).',
  'input_format': 'Line 1: n. Line 2: n arrival times. Line 3: n departure times.',
  'output_format': 'Single integer: minimum platforms.',
  'constraints': '1 <= n <= 10^4',
  'reference_solution': 'n = int(input())\n'
                        'arr = sorted(map(int, input().split()))\n'
                        'dep = sorted(map(int, input().split()))\n'
                        'i = j = 0\n'
                        'cur = best = 0\n'
                        'while i < n:\n'
                        '    if arr[i] < dep[j]:\n'
                        '        cur += 1; i += 1\n'
                        '        best = max(best, cur)\n'
                        '    else:\n'
                        '        cur -= 1; j += 1\n'
                        'print(best)\n',
  'test_inputs': ['6\n900 940 950 1100 1500 1800\n910 1200 1120 1130 1900 2000',
                  '3\n100 140 150\n110 200 220',
                  '1\n900\n1000',
                  '4\n100 200 300 400\n150 250 350 450',
                  '3\n100 100 100\n200 200 200',
                  '2\n100 200\n200 300'],
  'expected_outputs': ['3', '2', '1', '1', '3', '1'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py, modified: reference_solution changed from arr[i] <= dep[j] to '
            'arr[i] < dep[j] to fix an off-by-one in the platform-release check -- see the KNOWN DIVERGENCE '
            'note in this module\'s docstring.',
  'rubric': {'required_approach': ['Describes a correct way to find the minimum platforms needed: sorting '
                                   'arrival and departure times separately and sweeping through them '
                                   'counting how many trains are present at once; checking every pair of '
                                   'trains directly for a time overlap; or any other correct approach.',
                                   'Reaches the O(n log n) sort-and-sweep approach, not checking every pair '
                                   'of trains directly.'],
             'accepted_complexities': {'sort_and_sweep': {'time': 'O(n log n)', 'space': 'O(n)'},
                                       'pairwise_overlap_check': {'time': 'O(n^2)', 'space': 'O(1)'}},
             'edge_cases': ["a train's arrival exactly equal to another's departure (the platform is freed "
                            'in time)',
                            'all trains at the same time (needs n platforms)',
                            'only one train'],
             'common_mistakes': ['Treating an arrival at exactly a departure time as a conflict (using <=), '
                                 'which double-counts a platform that was actually free',
                                 'Sorting arrivals and departures together instead of as two separate sorted '
                                 'lists']}},
 {'id': 'greedy-jump-game-ii',
  'title': 'Jump Game II (Minimum Jumps)',
  'topic': 'greedy',
  'difficulty': 'Medium',
  'statement': 'Given an array where each element is the maximum jump length from that position, starting at '
               'index 0, print the minimum number of jumps needed to reach the last index. It is guaranteed '
               'the last index is always reachable.',
  'input_format': 'Line 1: n. Line 2: n integers.',
  'output_format': 'Single integer: minimum jumps.',
  'constraints': '1 <= n <= 10^5',
  'reference_solution': 'n = int(input())\n'
                        'a = list(map(int, input().split()))\n'
                        'jumps = 0\n'
                        'cur_end = 0\n'
                        'farthest = 0\n'
                        'for i in range(n - 1):\n'
                        '    farthest = max(farthest, i + a[i])\n'
                        '    if i == cur_end:\n'
                        '        jumps += 1\n'
                        '        cur_end = farthest\n'
                        'print(jumps)\n',
  'test_inputs': ['5\n2 3 1 1 4', '1\n0', '4\n1 1 1 1', '3\n2 1 1', '2\n1 1', '4\n2 0 1 0'],
  'expected_outputs': ['2', '0', '3', '1', '1', '2'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py (unmodified)',
  'rubric': {'required_approach': ['Describes a correct way to find the minimum number of jumps: a greedy '
                                   'sweep that tracks the farthest index reachable within the current number '
                                   'of jumps and increments the jump count whenever that range is exhausted, '
                                   "a DP where each index's minimum-jumps value is computed by checking "
                                   'every earlier index that can reach it, or any other correct approach.',
                                   'Reaches the O(n) greedy sweep, not the O(n^2) DP that checks every '
                                   'earlier index for each position.'],
             'accepted_complexities': {'greedy_range_sweep': {'time': 'O(n)', 'space': 'O(1)'},
                                       'dp_check_all_earlier': {'time': 'O(n^2)', 'space': 'O(n)'}},
             'edge_cases': ['array of length 1 (already at the last index, 0 jumps needed)',
                            'the last index reachable in exactly one jump',
                            'a 0 partway through that must be jumped over'],
             'common_mistakes': ['Incrementing the jump count at the wrong moment relative to when the '
                                 'current range runs out',
                                 'Iterating up to the last index instead of stopping one before it']}},
 {'id': 'graph-bipartite-check',
  'title': 'Is Graph Bipartite',
  'topic': 'graphs',
  'difficulty': 'Medium',
  'statement': "Given an undirected graph with n nodes (0-indexed) and m edges, print 'YES' if its nodes can "
               'be split into two groups such that every edge connects nodes from different groups, else '
               "'NO'.",
  'input_format': "Line 1: n m. Next m lines: 'u v' (omitted entirely if m is 0).",
  'output_format': 'YES or NO.',
  'constraints': '1 <= n <= 10^4, 0 <= m <= 10^4',
  'reference_solution': 'from collections import deque\n'
                        'n, m = map(int, input().split())\n'
                        'adj = [[] for _ in range(n)]\n'
                        'for _ in range(m):\n'
                        '    u, v = map(int, input().split())\n'
                        '    adj[u].append(v); adj[v].append(u)\n'
                        'color = [-1] * n\n'
                        'ok = True\n'
                        'for i in range(n):\n'
                        '    if color[i] == -1:\n'
                        '        color[i] = 0\n'
                        '        q = deque([i])\n'
                        '        while q:\n'
                        '            u = q.popleft()\n'
                        '            for v in adj[u]:\n'
                        '                if color[v] == -1:\n'
                        '                    color[v] = 1 - color[u]\n'
                        '                    q.append(v)\n'
                        '                elif color[v] == color[u]:\n'
                        '                    ok = False\n'
                        "print('YES' if ok else 'NO')\n",
  'test_inputs': ['4 4\n0 1\n1 2\n2 3\n3 0',
                  '3 3\n0 1\n1 2\n2 0',
                  '1 0',
                  '4 2\n0 1\n2 3',
                  '5 5\n0 1\n1 2\n2 3\n3 4\n4 0'],
  'expected_outputs': ['YES', 'NO', 'YES', 'YES', 'NO'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py; input_format documents the existing omit-when-0 convention '
            '(already true of the reference)',
  'rubric': {'required_approach': ['Describes a correct way to check bipartiteness: a BFS or DFS that tries '
                                   'to 2-color the graph, giving each unvisited neighbour the opposite color '
                                   'and failing as soon as a neighbour already has the same color as the '
                                   'current node, or any other correct approach.',
                                   'Reaches an O(V+E) traversal-based 2-coloring (BFS or DFS), not something '
                                   'that checks every pair of nodes directly.'],
             'accepted_complexities': {'bfs_2_coloring': {'time': 'O(V+E)', 'space': 'O(V)'},
                                       'dfs_2_coloring': {'time': 'O(V+E)', 'space': 'O(V)'}},
             'edge_cases': ['a graph with no edges (always bipartite)',
                            'a disconnected graph (every component needs checking)',
                            'an odd cycle (not bipartite)'],
             'common_mistakes': ['Only starting the traversal from node 0 and missing other disconnected '
                                 'components',
                                 'Not detecting a conflict when a neighbour already has the same color']}},
 {'id': 'graph-rotten-oranges',
  'title': 'Rotten Oranges (Minimum Time to Rot All)',
  'topic': 'graphs',
  'difficulty': 'Medium',
  'statement': 'A grid contains 0 (empty), 1 (fresh orange), or 2 (rotten orange). Every minute, a rotten '
               'orange rots every 4-directionally adjacent fresh orange. Print the minimum number of minutes '
               'until no fresh orange remains, or -1 if some fresh orange can never be reached.',
  'input_format': 'Line 1: rows cols. Next rows lines: cols space-separated 0/1/2 values.',
  'output_format': 'Single integer.',
  'constraints': '1 <= rows, cols <= 300',
  'reference_solution': 'from collections import deque\n'
                        'r, c = map(int, input().split())\n'
                        'g = [list(map(int, input().split())) for _ in range(r)]\n'
                        'q = deque()\n'
                        'fresh = 0\n'
                        'for i in range(r):\n'
                        '    for j in range(c):\n'
                        '        if g[i][j] == 2:\n'
                        '            q.append((i, j, 0))\n'
                        '        elif g[i][j] == 1:\n'
                        '            fresh += 1\n'
                        'mins = 0\n'
                        'while q:\n'
                        '    i, j, t = q.popleft()\n'
                        '    mins = max(mins, t)\n'
                        '    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n'
                        '        ni, nj = i + di, j + dj\n'
                        '        if 0 <= ni < r and 0 <= nj < c and g[ni][nj] == 1:\n'
                        '            g[ni][nj] = 2\n'
                        '            fresh -= 1\n'
                        '            q.append((ni, nj, t + 1))\n'
                        'print(mins if fresh == 0 else -1)\n',
  'test_inputs': ['3 3\n2 1 1\n1 1 0\n0 1 1',
                  '3 3\n2 1 1\n0 1 1\n1 0 1',
                  '1 1\n0',
                  '2 2\n2 1\n1 1',
                  '1 4\n1 2 1 1',
                  '2 2\n0 1\n1 1'],
  'expected_outputs': ['4', '-1', '0', '2', '2', '-1'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py (unmodified)',
  'rubric': {'required_approach': ['Describes a correct way to find the time until all fresh oranges rot: a '
                                   'BFS starting from all rotten oranges at once and expanding outward '
                                   'minute by minute; repeatedly scanning the whole grid once per minute '
                                   'and spreading rot to adjacent fresh oranges until nothing changes; or any '
                                   'other correct approach.',
                                   'Reaches the O(rows*cols) multi-source BFS starting from every rotten '
                                   'orange at once, not repeatedly rescanning the whole grid once per '
                                   'simulated minute.'],
             'accepted_complexities': {'multi_source_bfs': {'time': 'O(rows*cols)', 'space': 'O(rows*cols)'},
                                       'repeated_full_grid_scan': {'time': 'O((rows*cols)^2) in the worst '
                                                                           'case',
                                                                   'space': 'O(rows*cols)'}},
             'edge_cases': ['no fresh oranges at all (answer 0)',
                            'a fresh orange that can never be reached (answer -1)',
                            'no rotten oranges but at least one fresh orange (answer -1)'],
             'common_mistakes': ['Starting the BFS from only one rotten orange instead of all of them at '
                                 'once',
                                 'Returning the elapsed time instead of -1 when a fresh orange is '
                                 'unreachable']}},
 {'id': 'dp-longest-increasing-subsequence',
  'title': 'Longest Increasing Subsequence',
  'topic': '2d_dp',
  'difficulty': 'Medium',
  'statement': 'Given an array of integers, print the length of the longest strictly increasing subsequence.',
  'input_format': 'Line 1: n. Line 2: n integers (omit this line if n is 0).',
  'output_format': 'Single integer.',
  'constraints': '0 <= n <= 2500',
  'reference_solution': 'n = int(input())\n'
                        'a = list(map(int, input().split())) if n else []\n'
                        'dp = [1] * n\n'
                        'for i in range(n):\n'
                        '    for j in range(i):\n'
                        '        if a[j] < a[i]:\n'
                        '            dp[i] = max(dp[i], dp[j] + 1)\n'
                        'print(max(dp) if n else 0)\n',
  'test_inputs': ['8\n10 9 2 5 3 7 101 18', '1\n5', '5\n5 4 3 2 1', '6\n1 2 3 4 5 6', '4\n2 2 2 2', '0'],
  'expected_outputs': ['4', '1', '1', '6', '1', '0'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py; input_format documents the existing omit-when-0 convention '
            '(already true of the reference and test_inputs)',
  'rubric': {'required_approach': ['Describes a correct way to find the length of the longest strictly '
                                   'increasing subsequence: the O(n^2) DP comparing each index against every '
                                   'earlier index, or maintaining the smallest possible tail value for an '
                                   'increasing subsequence of each length and using binary search to place '
                                   'each new value, or any other correct approach.',
                                   'Reaches the O(n log n) tails-plus-binary-search approach, not the O(n^2) '
                                   'DP that compares every pair of indices.'],
             'accepted_complexities': {'nlogn_patience_binary_search': {'time': 'O(n log n)',
                                                                        'space': 'O(n)'},
                                       'on2_dp_pairwise': {'time': 'O(n^2)', 'space': 'O(n)'}},
             'edge_cases': ['empty array (length 0, answer 0)',
                            'all elements equal (answer 1, since it must be strictly increasing)',
                            'already strictly increasing (answer n)',
                            'strictly decreasing (answer 1)'],
             'common_mistakes': ['Using <= instead of < when comparing elements, which would allow equal '
                                 'values (not strictly increasing)',
                                 "Returning the DP array's last value instead of its maximum"]}},
 {'id': 'dp-partition-equal-subset-sum',
  'title': 'Partition Equal Subset Sum',
  'topic': '2d_dp',
  'difficulty': 'Medium',
  'statement': "Given an array of positive integers, print 'YES' if it can be partitioned into two subsets "
               "with equal sums, else 'NO'.",
  'input_format': 'Line 1: n. Line 2: n integers.',
  'output_format': 'YES or NO.',
  'constraints': '1 <= n <= 200',
  'reference_solution': 'n = int(input())\n'
                        'a = list(map(int, input().split()))\n'
                        'total = sum(a)\n'
                        'if total % 2 != 0:\n'
                        "    print('NO')\n"
                        'else:\n'
                        '    target = total // 2\n'
                        '    dp = [False] * (target + 1)\n'
                        '    dp[0] = True\n'
                        '    for x in a:\n'
                        '        for c in range(target, x - 1, -1):\n'
                        '            if dp[c - x]:\n'
                        '                dp[c] = True\n'
                        "    print('YES' if dp[target] else 'NO')\n",
  'test_inputs': ['4\n1 5 11 5', '3\n1 2 3', '3\n1 2 5', '1\n1', '4\n1 2 3 4'],
  'expected_outputs': ['YES', 'YES', 'NO', 'NO', 'YES'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py (unmodified)',
  'rubric': {'required_approach': ['Describes a correct way to check whether the array can be split into two '
                                   'equal-sum halves: a subset-sum DP over achievable sums up to half the '
                                   'total, checking every possible subset directly, or any other correct '
                                   'approach.',
                                   'Reaches the O(n * total_sum) subset-sum DP, not checking every possible '
                                   'subset directly (O(2^n)).'],
             'accepted_complexities': {'subset_sum_dp': {'time': 'O(n * total_sum)', 'space': 'O(total_sum)'},
                                       'brute_force_all_subsets': {'time': 'O(2^n)', 'space': 'O(n)'}},
             'edge_cases': ['an odd total sum (immediately impossible)',
                            'a single element',
                            'all elements equal (splittable if the count of them is even)'],
             'common_mistakes': ['Not checking for an odd total sum first and wasting a full DP pass',
                                 'Iterating the subset-sum DP forward instead of backward over the capacity, '
                                 'which lets one item be counted more than once']}},
 {'id': 'dp-maximal-square',
  'title': 'Maximal Square',
  'topic': '2d_dp',
  'difficulty': 'Medium',
  'statement': 'Given a binary matrix of 0s and 1s, find the largest square containing only 1s and print its '
               'area (side length squared).',
  'input_format': 'Line 1: rows cols. Next rows lines: cols space-separated 0/1 values.',
  'output_format': 'Single integer.',
  'constraints': '1 <= rows, cols <= 300',
  'reference_solution': 'rows, cols = map(int, input().split())\n'
                        'g = [list(map(int, input().split())) for _ in range(rows)]\n'
                        'dp = [[0] * cols for _ in range(rows)]\n'
                        'best = 0\n'
                        'for i in range(rows):\n'
                        '    for j in range(cols):\n'
                        '        if g[i][j] == 1:\n'
                        '            if i == 0 or j == 0:\n'
                        '                dp[i][j] = 1\n'
                        '            else:\n'
                        '                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1\n'
                        '            best = max(best, dp[i][j])\n'
                        'print(best * best)\n',
  'test_inputs': ['4 5\n1 0 1 0 0\n1 0 1 1 1\n1 1 1 1 1\n1 0 0 1 0',
                  '1 1\n0',
                  '1 1\n1',
                  '2 2\n1 1\n1 1',
                  '3 3\n0 1 1\n1 1 1\n0 1 1'],
  'expected_outputs': ['4', '0', '1', '4', '4'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py (unmodified)',
  'rubric': {'required_approach': ['Describes a correct way to find the largest all-1s square: a DP where '
                                   "each cell's value is the size of the largest square ending there, taken "
                                   'from the minimum of its top, left and top-left neighbours plus one, or '
                                   'checking at every cell how large a square of all 1s can be built outward '
                                   'from it by direct inspection, or any other correct approach.',
                                   'Reaches the O(rows*cols) DP approach, not checking every possible square '
                                   'size at every cell directly.'],
             'accepted_complexities': {'dp_min_of_neighbours': {'time': 'O(rows*cols)',
                                                                'space': 'O(rows*cols), or O(cols) with a '
                                                                         'rolling-row optimisation'},
                                       'brute_force_expand_each_cell': {'time': 'O(rows*cols*min(rows,cols)) '
                                                                                'or worse',
                                                                        'space': 'O(1) extra'}},
             'edge_cases': ['a grid with no 1s at all (answer 0)',
                            'a grid that is entirely 1s',
                            'a single cell'],
             'common_mistakes': ['Forgetting to special-case the first row/column, which has no '
                                 'top/left/top-left neighbour',
                                 'Printing the side length instead of the area (side length squared)']}},
 {'id': 'tp-subarray-product-less-than-k',
  'title': 'Subarray Product Less Than K',
  'topic': 'two_pointer_sliding_window',
  'difficulty': 'Medium',
  'statement': 'Given an array of positive integers and an integer k, count the number of contiguous '
               'subarrays whose product is strictly less than k.',
  'input_format': 'Line 1: n. Line 2: n positive integers. Line 3: k.',
  'output_format': 'Single integer.',
  'constraints': '1 <= n <= 3*10^4',
  'reference_solution': 'n = int(input())\n'
                        'a = list(map(int, input().split()))\n'
                        'k = int(input())\n'
                        'if k <= 1:\n'
                        '    print(0)\n'
                        'else:\n'
                        '    left = 0\n'
                        '    prod = 1\n'
                        '    count = 0\n'
                        '    for right in range(n):\n'
                        '        prod *= a[right]\n'
                        '        while prod >= k:\n'
                        '            prod //= a[left]\n'
                        '            left += 1\n'
                        '        count += right - left + 1\n'
                        '    print(count)\n',
  'test_inputs': ['4\n10 5 2 6\n100', '1\n5\n1', '1\n1\n2', '3\n1 1 1\n2', '5\n1 2 3 4 5\n1'],
  'expected_outputs': ['8', '0', '1', '6', '0'],
  'check': 'reference output via services.code_runner.run_python, hand-checked for at least 3 tests.',
  'source': 'copied from problem_bank.py (unmodified)',
  'rubric': {'required_approach': ['Describes a correct way to count subarrays with product less than k: a '
                                   'sliding window that shrinks from the left whenever the running product '
                                   "reaches or exceeds k, adding the window's current size to the count at "
                                   "each right-pointer step, checking every subarray's product directly, or "
                                   'any other correct approach.',
                                   'Reaches the O(n) sliding-window approach, not checking every subarray '
                                   'directly (O(n^2)).'],
             'accepted_complexities': {'sliding_window_two_pointer': {'time': 'O(n)', 'space': 'O(1)'},
                                       'brute_force_every_subarray': {'time': 'O(n^2)', 'space': 'O(1)'}},
             'edge_cases': ['k less than or equal to 1 (no subarray of positive integers qualifies, answer '
                            '0)',
                            'a single element at or above k',
                            'all elements equal to 1'],
             'common_mistakes': ['Not special-casing k <= 1 before dividing out the leftmost element',
                                 'Off-by-one when adding (right - left + 1) to the running count']}}]
