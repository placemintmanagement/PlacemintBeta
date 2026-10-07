# -*- coding: utf-8 -*-
"""Spark interview DSA problems and rubrics (Capgemini Spark tier only).

v2 fix pass: merge-sorted test 2 was malformed (it silently tested n=0,m=0
instead of "first array empty, second 1 2 3" -- problem_bank.py has the same
malformed test; it was NOT changed, see the review file); test 3 cleaned to
the same convention. tp-remove-duplicates-sorted's Spark copy of the
reference now omits the array line when n=0 (problem_bank.py's own copy is
unchanged). All three array-input problems (merge-sorted,
tp-remove-duplicates-sorted, intersection-unique) now share one convention:
a count-then-array pair of lines is reduced to just the count when that
count is 0.

Every rubric's required_approach is exactly two items: (a) correctness --
any valid algorithm, including a slower brute-force one; (b) efficiency --
the specific efficient approach named in complexity, not a slower-but-
correct one. Six problems accept a named alternative approach as correct:
tree-min-depth, tree-level-order, middle-of-linked-list,
pair-with-sum-sorted, tp-remove-duplicates-sorted, merge-sorted and
can-attend-meetings (7, not 6 -- can-attend-meetings and merge-sorted share
the "slower but correct" framing). first-unique-char and tree-symmetric
have updated complexity text (see each rubric).

Problems are kept here, not in banks/problem_bank.py, so Round 3, Round 4
and every other draw keep their exact behaviour. Nine problems are based on
problem_bank entries (two of those nine, noted above, have a modified
reference/test in this copy only); six are new. Each record's "source"
field says which.

Every reference solution was re-run through services/code_runner.run_python
on every test input before this file was written. The "check" field says
how the expected outputs were established.
"""

SPARK_DSA_PROBLEMS = [{'id': 'contains-duplicate',
  'title': 'Contains Duplicate',
  'topic': 'arrays',
  'difficulty': 'Easy',
  'statement': "Return 'YES' if any value appears at least twice in the array, else 'NO'.",
  'input_format': 'Line 1: n. Line 2: n integers.',
  'output_format': 'YES or NO.',
  'constraints': '1 ≤ n ≤ 10^5',
  'reference_solution': 'n = int(input())\n'
                        'a = input().split()\n'
                        "print('YES' if len(set(a)) != len(a) else 'NO')\n",
  'test_inputs': ['4\n1 2 3 1', '4\n1 2 3 4', '10\n1 1 1 3 3 4 3 2 4 2', '1\n5', '5\n7 7 7 7 7'],
  'expected_outputs': ['YES', 'NO', 'YES', 'NO', 'YES'],
  'check': 'reference output (same convention as problem_bank)',
  'source': 'copied from problem_bank.py (unchanged)',
  'rubric': {'required_approach': ['Describes a correct way to detect a repeated value: a hash set or dict, '
                                   'sorting then comparing neighbours, or even a brute-force check of every '
                                   'pair.',
                                   'Reaches a hash set/dict (O(n)) or sort-then-scan (O(n log n)) approach, '
                                   'not a brute-force check of every pair (O(n^2)).'],
             'complexity': {'time': 'O(n) average with a hash set (O(n log n) if sorting)',
                            'space': 'O(n) for the set'},
             'edge_cases': ['n = 1 has no duplicate', 'every value equal', 'negative values'],
             'common_mistakes': ['Comparing only adjacent elements without sorting first',
                                 'Nested loops over all pairs (O(n^2))']}},
 {'id': 'merge-sorted',
  'title': 'Merge Two Sorted Arrays',
  'topic': 'two_pointer_sliding_window',
  'difficulty': 'Easy',
  'statement': 'Merge two sorted integer arrays and print the merged sorted array (space-separated).',
  'input_format': 'L1: n. L2: n ints (omit this line if n is 0). L3: m. L4: m ints (omit this line if m is '
                  '0).',
  'output_format': 'n+m sorted ints, space-separated.',
  'constraints': '0 ≤ n,m ≤ 10^4',
  'reference_solution': 'n = int(input())\n'
                        'a = list(map(int, input().split())) if n else []\n'
                        'm = int(input())\n'
                        'b = list(map(int, input().split())) if m else []\n'
                        'out = []; i = j = 0\n'
                        'while i < n and j < m:\n'
                        '    if a[i] <= b[j]: out.append(a[i]); i += 1\n'
                        '    else: out.append(b[j]); j += 1\n'
                        'out += a[i:]; out += b[j:]\n'
                        "print(' '.join(map(str, out)))\n",
  'test_inputs': ['3\n1 3 5\n3\n2 4 6',
                  '0\n3\n1 2 3',
                  '3\n1 2 3\n0',
                  '5\n1 1 1 1 1\n5\n2 2 2 2 2',
                  '2\n-3 -1\n3\n-2 0 2'],
  'expected_outputs': ['1 2 3 4 5 6', '1 2 3', '1 2 3', '1 1 1 1 1 2 2 2 2 2', '-3 -2 -1 0 2'],
  'check': 'reference output (same convention as problem_bank)',
  'source': 'copied from problem_bank.py, test 2 fixed and test 3 cleaned for the Spark empty-array '
            'convention (problem_bank.py itself is unchanged -- see report)',
  'rubric': {'required_approach': ['Describes a correct way to merge two sorted arrays into one sorted '
                                   'array: two pointers taking the smaller head each step, concatenating the '
                                   'two arrays and sorting the result, or a nested comparison.',
                                   'Reaches the two-pointer approach (O(n+m)), not concatenate-and-sort '
                                   '(O((n+m) log(n+m))) or a slower comparison.'],
             'complexity': {'time': 'O(n + m)', 'space': 'O(n + m) for the output'},
             'edge_cases': ['either array empty', 'equal values across arrays', 'negative values'],
             'common_mistakes': ['Forgetting the leftover tail', 'Indexing past the end of an array']}},
 {'id': 'tree-level-order',
  'title': 'Binary Tree Level Order Traversal',
  'topic': 'trees',
  'difficulty': 'Easy',
  'statement': "A binary tree is given as a level-order list of values on a single line, where 'N' marks a "
               "missing child (root first, then each node's left then right child in BFS order). Print the "
               "tree's level-order traversal: one line per depth level, values space-separated left to "
               'right.',
  'input_format': "Single line: space-separated values and 'N' tokens.",
  'output_format': 'One line per level.',
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
                        'level = [root]\n'
                        'while level:\n'
                        "    print(' '.join(str(n.v) for n in level))\n"
                        '    nxt = []\n'
                        '    for n in level:\n'
                        '        if n.l: nxt.append(n.l)\n'
                        '        if n.r: nxt.append(n.r)\n'
                        '    level = nxt\n',
  'test_inputs': ['3 9 20 N N 15 7', '1', '1 2 3 N N N N', '5 3 8 1 4 7 9', '1 N 2 N 3'],
  'expected_outputs': ['3\n9 20\n15 7', '1', '1\n2 3', '5\n3 8\n1 4 7 9', '1\n2\n3'],
  'check': 'reference output (same convention as problem_bank)',
  'source': 'copied from problem_bank.py (unchanged)',
  'rubric': {'required_approach': ['Describes a correct way to group values by depth: breadth-first search '
                                   "with a queue, or depth-first search that tracks each node's depth and "
                                   'groups values by it.',
                                   'Reaches the BFS-with-a-queue approach specifically, processing one level '
                                   'at a time, rather than a DFS-based approach -- even a DFS that correctly '
                                   'tracks depth is the less efficient of the two correct approaches here, '
                                   'since BFS needs no extra depth bookkeeping to group by level.'],
             'complexity': {'time': 'O(N)',
                            'space': 'O(W), W = widest level for BFS (O(H) for DFS tracking depth)'},
             'edge_cases': ['single node',
                            'a skewed tree with one node per level',
                            'N tokens are missing children, not values'],
             'common_mistakes': ['Depth-first traversal that does not group by level',
                                 'Treating N as a node value']}},
 {'id': 'tree-symmetric',
  'title': 'Symmetric Tree',
  'topic': 'trees',
  'difficulty': 'Easy',
  'statement': "Given a binary tree as a level-order list ('N' = missing child), print 'YES' if it is a "
               "mirror of itself (symmetric around its center), else 'NO'.",
  'input_format': "Single line: level-order values with 'N' for null.",
  'output_format': 'YES or NO.',
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
                        'def mirror(a, b):\n'
                        '    if a is None and b is None: return True\n'
                        '    if a is None or b is None: return False\n'
                        '    return a.v == b.v and mirror(a.l, b.r) and mirror(a.r, b.l)\n'
                        "print('YES' if root is None or mirror(root.l, root.r) else 'NO')\n",
  'test_inputs': ['1 2 2 3 4 4 3', '1 2 2 N 3 N 3', '1', '3 9 20 N N 15 7', '1 2 2 N N N N'],
  'expected_outputs': ['YES', 'NO', 'YES', 'NO', 'YES'],
  'check': 'reference output (same convention as problem_bank)',
  'source': 'copied from problem_bank.py (unchanged)',
  'rubric': {'required_approach': ['Describes a correct way to check mirror symmetry: comparing left.left '
                                   'with right.right and left.right with right.left, via recursion or an '
                                   'explicit queue of mirrored pairs.',
                                   'Reaches an O(N) approach (recursion or a queue), not something that '
                                   'rebuilds or re-traverses either subtree per comparison.'],
             'complexity': {'time': 'O(N)',
                            'space': 'O(H) recursion depth for the recursive version; O(W), up to O(N), for '
                                     'the explicit-queue version'},
             'edge_cases': ['root alone is symmetric',
                            'only one side has children',
                            'same values, different shape'],
             'common_mistakes': ['Comparing left with right directly (not mirrored)',
                                 'Comparing values only and ignoring shape']}},
 {'id': 'tree-balanced',
  'title': 'Balanced Binary Tree',
  'topic': 'trees',
  'difficulty': 'Easy',
  'statement': "Given a binary tree as a level-order list ('N' = missing child), print 'YES' if it is "
               'height-balanced (for every node, the heights of its left and right subtrees differ by at '
               "most 1), else 'NO'.",
  'input_format': "Single line: level-order values with 'N' for null.",
  'output_format': 'YES or NO.',
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
                        'ok = True\n'
                        'def h(n):\n'
                        '    global ok\n'
                        '    if n is None: return 0\n'
                        '    lh = h(n.l); rh = h(n.r)\n'
                        '    if abs(lh - rh) > 1: ok = False\n'
                        '    return 1 + max(lh, rh)\n'
                        'h(root)\n'
                        "print('YES' if ok else 'NO')\n",
  'test_inputs': ['3 9 20 N N 15 7', '1 2 N 3 N 4', '1', '5 3 8 1 4 7 9', '1 2 2 3 3 N N 4 4'],
  'expected_outputs': ['YES', 'NO', 'YES', 'YES', 'NO'],
  'check': 'reference output (same convention as problem_bank)',
  'source': 'copied from problem_bank.py (unchanged)',
  'rubric': {'required_approach': ['Describes a correct way to check height-balance at every node, not just '
                                   'the root: a post-order height computation that detects any subtree pair '
                                   'differing by more than 1.',
                                   'Reaches the single post-order pass (O(N)), not recomputing height from '
                                   'scratch for every node (O(N^2) on a skewed tree).'],
             'complexity': {'time': 'O(N)', 'space': 'O(H)'},
             'edge_cases': ['single node is balanced', 'a deep chain on one side', 'a node with one child'],
             'common_mistakes': ["Checking only the root's children heights, not every node",
                                 'Recomputing heights top-down for every node (O(N^2) on skewed trees)']}},
 {'id': 'tree-min-depth',
  'title': 'Minimum Depth of Binary Tree',
  'topic': 'trees',
  'difficulty': 'Easy',
  'statement': "Given a binary tree as a level-order list ('N' = missing child), print its minimum depth: "
               'the number of nodes on the shortest path from the root down to any leaf (a leaf has no '
               'children at all).',
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
                        'from collections import deque as dq\n'
                        'def mindepth(n):\n'
                        '    if n is None: return 0\n'
                        '    q = dq([(n, 1)])\n'
                        '    while q:\n'
                        '        node, d = q.popleft()\n'
                        '        if node.l is None and node.r is None:\n'
                        '            return d\n'
                        '        if node.l: q.append((node.l, d + 1))\n'
                        '        if node.r: q.append((node.r, d + 1))\n'
                        'print(mindepth(root))\n',
  'test_inputs': ['2 N 3 N 4 N 5', '1', '3 9 20 N N 15 7', '1 2', '5 3 8 1 4 7 9'],
  'expected_outputs': ['4', '1', '2', '2', '3'],
  'check': 'reference output (same convention as problem_bank)',
  'source': 'copied from problem_bank.py (unchanged)',
  'rubric': {'required_approach': ['Describes a correct way to find the shortest root-to-leaf path: BFS '
                                   'stopping at the first leaf, or a DFS/recursive approach that correctly '
                                   'treats a node with only one child as NOT a leaf.',
                                   'Defines a leaf as a node with no children (both left and right missing), '
                                   'so a node with one child is not treated as a leaf.'],
             'complexity': {'time': 'O(N)', 'space': 'O(W)'},
             'edge_cases': ['root only', 'root with exactly one child', 'a deep chain on one side'],
             'common_mistakes': ['Taking min(left, right) when one child is missing (gives 1 at the root)',
                                 'Counting edges instead of nodes']}},
 {'id': 'string-longest-common-prefix',
  'title': 'Longest Common Prefix',
  'topic': 'strings',
  'difficulty': 'Easy',
  'statement': 'Given n strings, print the longest string that is a prefix of all of them. Print an empty '
               'line if there is no common prefix.',
  'input_format': 'Line 1: n. Next n lines: one string each.',
  'output_format': 'The longest common prefix (may be empty).',
  'constraints': '1 <= n <= 200',
  'reference_solution': 'n = int(input())\n'
                        'words = [input() for _ in range(n)]\n'
                        'pre = words[0]\n'
                        'for w in words[1:]:\n'
                        '    i = 0\n'
                        '    while i < len(pre) and i < len(w) and pre[i] == w[i]:\n'
                        '        i += 1\n'
                        '    pre = pre[:i]\n'
                        '    if not pre:\n'
                        '        break\n'
                        'print(pre)\n',
  'test_inputs': ['3\nflower\nflow\nflight', '3\ndog\nracecar\ncar', '1\nsingle', '2\nab\nab', '2\nabc\nabd'],
  'expected_outputs': ['fl', '', 'single', 'ab', 'ab'],
  'check': 'reference output (same convention as problem_bank)',
  'source': 'copied from problem_bank.py (unchanged)',
  'rubric': {'required_approach': ['Describes a correct way to find the longest common prefix: shrinking a '
                                   'running prefix against each next string, comparing characters column by '
                                   'column, or sorting the strings and comparing only the first and last.',
                                   'Reaches an approach bounded by the characters actually compared (at most '
                                   'n times the shortest length), not comparing every pair of strings '
                                   'separately.'],
             'complexity': {'time': 'O(total characters compared), at most n * shortest length',
                            'space': 'O(1) beyond the output'},
             'edge_cases': ['n = 1 returns the whole string',
                            'no common prefix prints an empty line',
                            'one string is a prefix of another'],
             'common_mistakes': ['Printing None or -1 instead of an empty line',
                                 "Running past the shortest string's length"]}},
 {'id': 'string-word-pattern',
  'title': 'Word Pattern',
  'topic': 'strings',
  'difficulty': 'Easy',
  'statement': "Given a pattern string and a sentence of space-separated words, print 'YES' if there is a "
               'one-to-one (bijective) mapping between each pattern character and the word at that position, '
               "else 'NO'.",
  'input_format': 'Line 1: pattern. Line 2: space-separated words.',
  'output_format': 'YES or NO.',
  'constraints': '1 <= |pattern| <= 300',
  'reference_solution': 'pattern = input()\n'
                        'words = input().split()\n'
                        'if len(pattern) != len(words):\n'
                        "    print('NO')\n"
                        'else:\n'
                        '    m1, m2 = {}, {}\n'
                        '    ok = True\n'
                        '    for a, b in zip(pattern, words):\n'
                        '        if a in m1 and m1[a] != b:\n'
                        '            ok = False; break\n'
                        '        if b in m2 and m2[b] != a:\n'
                        '            ok = False; break\n'
                        '        m1[a] = b; m2[b] = a\n'
                        "    print('YES' if ok else 'NO')\n",
  'test_inputs': ['abba\ndog cat cat dog',
                  'abba\ndog cat cat fish',
                  'aaaa\ndog cat cat dog',
                  'abba\ndog dog dog dog',
                  'a\ndog'],
  'expected_outputs': ['YES', 'NO', 'NO', 'NO', 'YES'],
  'check': 'reference output (same convention as problem_bank)',
  'source': 'copied from problem_bank.py (unchanged)',
  'rubric': {'required_approach': ['Describes a correct way to check the bijection: two maps, pattern-letter '
                                   'to word and word to letter, both checked for consistency, after '
                                   'confirming the word count matches the pattern length.',
                                   'Reaches a single O(L) pass with hash maps, not a comparison of every '
                                   'pair of positions.'],
             'complexity': {'time': 'O(L), L = pattern length', 'space': 'O(L)'},
             'edge_cases': ['word count differs from pattern length',
                            'same word for two letters (abba with dog dog dog dog)',
                            'single letter'],
             'common_mistakes': ['Only one-directional map (lets two letters share one word)',
                                 'No length check, causing index errors']}},
 {'id': 'tp-remove-duplicates-sorted',
  'title': 'Remove Duplicates from Sorted Array',
  'topic': 'two_pointer_sliding_window',
  'difficulty': 'Easy',
  'statement': 'Given a sorted array, remove duplicates in place so each distinct value appears once, '
               'keeping relative order. Print the resulting length, then the deduplicated values '
               '(space-separated) on the next line; print an empty second line if the array was empty.',
  'input_format': 'Line 1: n. Line 2: n integers, sorted, non-decreasing (omit this line if n is 0).',
  'output_format': 'Line 1: new length. Line 2: deduplicated values.',
  'constraints': '0 <= n <= 3*10^4',
  'reference_solution': 'n = int(input())\n'
                        'a = list(map(int, input().split())) if n else []\n'
                        'if n == 0:\n'
                        '    print(0)\n'
                        "    print('')\n"
                        'else:\n'
                        '    k = 1\n'
                        '    for i in range(1, n):\n'
                        '        if a[i] != a[k - 1]:\n'
                        '            a[k] = a[i]\n'
                        '            k += 1\n'
                        '    print(k)\n'
                        "    print(' '.join(map(str, a[:k])))\n",
  'test_inputs': ['5\n1 1 2 2 3', '8\n0 0 1 1 1 2 2 3', '1\n5', '3\n1 1 1', '0'],
  'expected_outputs': ['3\n1 2 3', '4\n0 1 2 3', '1\n5', '1\n1', '0'],
  'check': 'reference output (same convention as problem_bank)',
  'source': 'copied from problem_bank.py, reference guarded to omit the array line when n=0, matching the '
            'Spark empty-array convention (problem_bank.py itself is unchanged -- see report)',
  'rubric': {'required_approach': ['Describes a correct way to remove duplicates from a sorted array: '
                                   'comparing each element with the last distinct value kept so far -- on a '
                                   'sorted array this is equivalent to comparing with the immediately '
                                   'preceding element, so either framing is correct -- or building a fresh '
                                   'deduplicated list.',
                                   'Reaches the in-place two-pointer approach (O(n) time, O(1) extra space), '
                                   'not building a new list or using a set (O(n) extra space).'],
             'complexity': {'time': 'O(n)', 'space': 'O(1) in place'},
             'edge_cases': ['empty array (print 0 then an empty line)', 'all values equal', 'single element'],
             'common_mistakes': ['Printing the original length instead of the new length',
                                 'Not handling the empty-array case (should print 0 then an empty line)']}},
 {'id': 'first-unique-char',
  'title': 'First Unique Character',
  'topic': 'strings_hashing',
  'difficulty': 'Easy',
  'statement': 'Given a lowercase string, print the index (0-based) of the first character that appears '
               'exactly once. Print -1 if no character is unique.',
  'input_format': 'Single line: the string.',
  'output_format': 'One integer: the index, or -1.',
  'constraints': '1 <= |s| <= 10^5, lowercase letters only',
  'reference_solution': 'from collections import Counter\n'
                        's = input().strip()\n'
                        'c = Counter(s)\n'
                        'for i, ch in enumerate(s):\n'
                        '    if c[ch] == 1:\n'
                        '        print(i)\n'
                        '        break\n'
                        'else:\n'
                        '    print(-1)\n',
  'test_inputs': ['leetcode', 'loveleetcode', 'aabb', 'z', 'aabbcdc'],
  'expected_outputs': ['0', '2', '-1', '0', '5'],
  'check': 'hand-computed expected outputs match the reference run',
  'source': 'authored for Spark (new)',
  'rubric': {'required_approach': ['Describes a correct way to find the first unique character: counting '
                                   'every character in one pass, then scanning again for the first with '
                                   'count 1.',
                                   'Reaches O(n) time. Space is O(1) if using the lowercase-only constraint '
                                   '(at most 26 counters); O(n) in general is also acceptable since the '
                                   'alphabet is small either way.'],
             'complexity': {'time': 'O(n)',
                            'space': 'O(1) using the lowercase-letters constraint (at most 26 distinct '
                                     'characters); O(n) in general is also acceptable if that constraint '
                                     "isn't used"},
             'edge_cases': ['single character',
                            'no unique character gives -1',
                            'the unique character is the last one'],
             'common_mistakes': ['Returning the index of the last unique character',
                                 'list.index per character (O(n^2))']}},
 {'id': 'valid-parentheses',
  'title': 'Valid Parentheses',
  'topic': 'stack',
  'difficulty': 'Easy',
  'statement': 'Given a string of brackets from ()[]{}, print YES if every opening bracket is closed by the '
               'same type in the correct order, else NO.',
  'input_format': 'Single line: the bracket string.',
  'output_format': 'YES or NO.',
  'constraints': '1 <= |s| <= 10^4',
  'reference_solution': 's = input().strip()\n'
                        "pairs = {')': '(', ']': '[', '}': '{'}\n"
                        'st = []\n'
                        'ok = True\n'
                        'for ch in s:\n'
                        "    if ch in '([{':\n"
                        '        st.append(ch)\n'
                        '    else:\n'
                        '        if not st or st[-1] != pairs[ch]:\n'
                        '            ok = False\n'
                        '            break\n'
                        '        st.pop()\n'
                        "print('YES' if ok and not st else 'NO')\n",
  'test_inputs': ['()', '()[]{}', '(]', '([)]', '(('],
  'expected_outputs': ['YES', 'YES', 'NO', 'NO', 'NO'],
  'check': 'hand-computed expected outputs match the reference run',
  'source': 'authored for Spark (new)',
  'rubric': {'required_approach': ['Describes a correct stack-based approach: pushes openers, and on a '
                                   'closer checks the stack top is the matching opener before popping.',
                                   'Processes the string in one pass, as the stack approach naturally does, '
                                   'rather than something that re-scans the string multiple times (for '
                                   'example repeatedly finding and removing an innermost matched pair like '
                                   '"()" until none remain).'],
             'complexity': {'time': 'O(n)', 'space': 'O(n)'},
             'edge_cases': ['unclosed openers at the end ((',
                            'a closer with an empty stack )',
                            'interleaved types ([)]'],
             'common_mistakes': ['Counting brackets without order, so ([)] passes',
                                 'Not checking the stack is empty at the end']}},
 {'id': 'intersection-unique',
  'title': 'Intersection of Two Arrays',
  'topic': 'arrays_hashing',
  'difficulty': 'Easy',
  'statement': 'Given two integer arrays, print their intersection: each value that appears in both, listed '
               'once, in ascending order, space-separated. Print an empty line if there is no common value.',
  'input_format': 'Line 1: n. Line 2: n integers (omit this line if n is 0). Line 3: m. Line 4: m integers '
                  '(omit if m is 0).',
  'output_format': 'Common values ascending, space-separated (may be an empty line).',
  'constraints': '0 <= n, m <= 10^4',
  'reference_solution': 'n = int(input())\n'
                        'a = list(map(int, input().split())) if n else []\n'
                        'm = int(input())\n'
                        'b = list(map(int, input().split())) if m else []\n'
                        "print(' '.join(map(str, sorted(set(a) & set(b)))))\n",
  'test_inputs': ['4\n1 2 2 3\n3\n2 3 4',
                  '3\n1 2 3\n3\n4 5 6',
                  '5\n5 5 5 5 5\n2\n5 5',
                  '0\n2\n1 2',
                  '4\n-1 0 1 2\n4\n2 1 0 -1'],
  'expected_outputs': ['2 3', '', '5', '', '-1 0 1 2'],
  'check': 'hand-computed expected outputs match the reference run',
  'source': 'authored for Spark (new)',
  'rubric': {'required_approach': ['Describes a correct way to find the common values: intersecting the two '
                                   'arrays as sets, or checking membership of each element of one array in '
                                   'the other and then deduplicating and sorting.',
                                   'Reaches an O(n+m) hash-set approach, not a nested-loop comparison of '
                                   'every pair (O(n*m)).'],
             'complexity': {'time': 'O(n + m) plus O(k log k) for the k common values', 'space': 'O(n + m)'},
             'edge_cases': ['one array empty (its line is omitted)',
                            'duplicates within an input array',
                            'no overlap prints an empty line'],
             'common_mistakes': ['Printing duplicates in the intersection', 'Printing unsorted output']}},
 {'id': 'middle-of-linked-list',
  'title': 'Middle of a Linked List',
  'topic': 'linked_list',
  'difficulty': 'Easy',
  'statement': 'The values are the nodes of a singly linked list, in order. Build the list and print the '
               'value of its middle node. For an even number of nodes, print the second of the two middle '
               'nodes.',
  'input_format': 'Line 1: n. Line 2: n values in list order.',
  'output_format': "The middle node's value.",
  'constraints': '1 <= n <= 10^4',
  'reference_solution': 'class Node:\n'
                        '    def __init__(self, v):\n'
                        '        self.v = v\n'
                        '        self.next = None\n'
                        'n = int(input())\n'
                        'vals = input().split()\n'
                        'head = tail = None\n'
                        'for v in vals:\n'
                        '    node = Node(v)\n'
                        '    if tail is None:\n'
                        '        head = tail = node\n'
                        '    else:\n'
                        '        tail.next = node\n'
                        '        tail = node\n'
                        'slow = fast = head\n'
                        'while fast and fast.next:\n'
                        '    slow = slow.next\n'
                        '    fast = fast.next.next\n'
                        'print(slow.v)\n',
  'test_inputs': ['1\n7', '2\n1 2', '3\n1 2 3', '5\n1 2 3 4 5', '6\n10 20 30 40 50 60'],
  'expected_outputs': ['7', '2', '2', '3', '40'],
  'check': 'hand-computed expected outputs match the reference run',
  'source': 'authored for Spark (new)',
  'rubric': {'required_approach': ['Describes a correct way to find the middle node: slow/fast pointers '
                                   "(slow moves one step, fast moves two), or counting the list's length "
                                   'first and then walking to the correct index (the second of the two '
                                   'middles for an even count).',
                                   'Reaches the single-pass slow/fast approach rather than two full passes '
                                   '(count, then walk) -- both are O(n) time, but one pass is the more '
                                   'efficient of the two correct approaches.'],
             'complexity': {'time': 'O(n)', 'space': 'O(1)'},
             'edge_cases': ['one node', 'two nodes returns the second', 'even length in general'],
             'common_mistakes': ['Returning the first middle for an even count',
                                 "Off-by-one on the fast pointer's end check"]}},
 {'id': 'can-attend-meetings',
  'title': 'Can Attend All Meetings',
  'topic': 'sorting',
  'difficulty': 'Easy',
  'statement': 'Given meetings as [start, end] pairs, print YES if one person can attend all of them (no two '
               'meetings overlap), else NO. A meeting that ends at the instant another starts does not '
               'overlap it.',
  'input_format': 'Line 1: n. Next n lines: start end.',
  'output_format': 'YES or NO.',
  'constraints': '0 <= n <= 10^4, 0 <= start < end <= 10^9',
  'reference_solution': 'n = int(input())\n'
                        'iv = []\n'
                        'for _ in range(n):\n'
                        '    s, e = map(int, input().split())\n'
                        '    iv.append((s, e))\n'
                        'iv.sort()\n'
                        'ok = all(iv[i][1] <= iv[i + 1][0] for i in range(len(iv) - 1))\n'
                        "print('YES' if ok else 'NO')\n",
  'test_inputs': ['3\n0 30\n5 10\n15 20', '2\n7 10\n2 4', '2\n1 5\n5 8', '1\n3 4', '4\n1 4\n2 3\n5 6\n7 8'],
  'expected_outputs': ['NO', 'YES', 'YES', 'YES', 'NO'],
  'check': 'hand-computed expected outputs match the reference run',
  'source': 'authored for Spark (new)',
  'rubric': {'required_approach': ['Describes a correct way to check for any overlap: sorting meetings by '
                                   'start time and checking each against the previous, or comparing every '
                                   'pair of meetings directly for overlap.',
                                   'Reaches the sort-then-scan approach (O(n log n)), not a comparison of '
                                   'every pair of meetings (O(n^2)).'],
             'complexity': {'time': 'O(n log n)', 'space': 'O(n) for the sorted copy'},
             'edge_cases': ['zero or one meeting',
                            'end equals the next start (allowed)',
                            'input not in order'],
             'common_mistakes': ['Comparing consecutive input lines without sorting',
                                 'Treating touching meetings as overlapping']}},
 {'id': 'pair-with-sum-sorted',
  'title': 'Pair With Target Sum (Sorted)',
  'topic': 'two_pointers',
  'difficulty': 'Easy',
  'statement': 'Given a sorted (non-decreasing) array and a target, print YES if two different positions '
               'hold values that add up to the target, else NO.',
  'input_format': 'Line 1: n. Line 2: n sorted integers. Line 3: target.',
  'output_format': 'YES or NO.',
  'constraints': '2 <= n <= 10^4',
  'reference_solution': 'n = int(input())\n'
                        'a = list(map(int, input().split()))\n'
                        't = int(input())\n'
                        'i, j = 0, n - 1\n'
                        'found = False\n'
                        'while i < j:\n'
                        '    s = a[i] + a[j]\n'
                        '    if s == t:\n'
                        '        found = True\n'
                        '        break\n'
                        '    if s < t:\n'
                        '        i += 1\n'
                        '    else:\n'
                        '        j -= 1\n'
                        "print('YES' if found else 'NO')\n",
  'test_inputs': ['4\n1 2 3 4\n6', '4\n1 2 3 4\n8', '2\n3 3\n6', '5\n-4 -1 0 2 5\n1', '3\n1 2 3\n10'],
  'expected_outputs': ['YES', 'NO', 'YES', 'YES', 'NO'],
  'check': 'hand-computed expected outputs match the reference run',
  'source': 'authored for Spark (new)',
  'rubric': {'required_approach': ['Describes a correct way to find a pair summing to the target: two '
                                   'pointers from both ends of the sorted array, or a hash set recording '
                                   'values seen so far.',
                                   'Reaches an O(1)-extra-space approach (two pointers), not O(n) extra '
                                   'space (a hash set) -- both run in O(n) time.'],
             'complexity': {'time': 'O(n)', 'space': 'O(1)'},
             'edge_cases': ['no pair exists (NO)',
                            'equal values forming the pair (3 3 for target 6)',
                            'negative values'],
             'common_mistakes': ['Using the same index twice',
                                 'Nested loops over all pairs, ignoring the sorted order (O(n^2))']}}]
