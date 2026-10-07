# -*- coding: utf-8 -*-
"""Spark interview DSA problems and rubrics (Capgemini Spark tier only).

Pending review: this file is generated, and every problem and rubric in it is
authored content, tagged INTERPOLATED until the repo owner spot-checks it.
Problems are kept here, not in banks/problem_bank.py, so Round 3, Round 4
and every other draw keep their exact behaviour. Nine problems are copies of
problem_bank entries; six are new. Each record's "source" field says which.

Every reference solution was run through services/code_runner.run_python on
every test input before this file was written. The "check" field says how
the expected outputs were established.
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
  'rubric': {'required_approach': ['Uses a set or dict to remember values already seen (or sorts and '
                                   'compares neighbours)',
                                   'Stops at the first repeat rather than comparing every pair'],
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
  'input_format': 'L1: n. L2: n ints. L3: m. L4: m ints.',
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
                  '0\n0\n3\n1 2 3',
                  '3\n1 2 3\n0\n0',
                  '5\n1 1 1 1 1\n5\n2 2 2 2 2',
                  '2\n-3 -1\n3\n-2 0 2'],
  'expected_outputs': ['1 2 3 4 5 6', '', '1 2 3', '1 1 1 1 1 2 2 2 2 2', '-3 -2 -1 0 2'],
  'check': 'reference output (same convention as problem_bank)',
  'source': 'copied from problem_bank.py (unchanged)',
  'rubric': {'required_approach': ['Two pointers, one per sorted array, always taking the smaller head',
                                   'Appends the leftover tail of the array that is not yet exhausted'],
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
  'rubric': {'required_approach': ['Breadth-first search with a queue',
                                   'Groups nodes by level, e.g. by taking the queue length at the start of '
                                   'each level'],
             'complexity': {'time': 'O(N)', 'space': 'O(W), W = widest level (O(N) worst case)'},
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
  'rubric': {'required_approach': ['Compares the left subtree with the right subtree as a mirror: left.left '
                                   'with right.right and left.right with right.left',
                                   'Uses recursion or a queue of mirrored pairs'],
             'complexity': {'time': 'O(N)', 'space': 'O(H) recursion depth (O(N) worst case)'},
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
  'rubric': {'required_approach': ['Post-order height computation where each node returns its height',
                                   "Flags the tree unbalanced as soon as any node's subtree heights differ "
                                   'by more than 1'],
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
  'rubric': {'required_approach': ['BFS from the root, returning the depth of the first leaf reached',
                                   'A leaf has no children at all; a node with one missing child is not a '
                                   'leaf'],
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
  'rubric': {'required_approach': ['Shrinks a running prefix against each next string, or compares column by '
                                   'column',
                                   'Stops at the first mismatch or the end of the shortest string'],
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
  'rubric': {'required_approach': ['Two maps: pattern letter to word and word to letter, both checked for '
                                   'consistency',
                                   'Checks that the number of words equals the pattern length first'],
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
  'input_format': 'Line 1: n. Line 2: n integers (sorted, non-decreasing).',
  'output_format': 'Line 1: new length. Line 2: deduplicated values.',
  'constraints': '0 <= n <= 3*10^4',
  'reference_solution': 'n = int(input())\n'
                        'a = list(map(int, input().split()))\n'
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
  'test_inputs': ['5\n1 1 2 2 3', '8\n0 0 1 1 1 2 2 3', '1\n5', '3\n1 1 1', '0\n\n'],
  'expected_outputs': ['3\n1 2 3', '4\n0 1 2 3', '1\n5', '1\n1', '0'],
  'check': 'reference output (same convention as problem_bank)',
  'source': 'copied from problem_bank.py (unchanged)',
  'rubric': {'required_approach': ['Two pointers: a write index for distinct values and a scan index',
                                   'Compares against the last kept value, not the adjacent element'],
             'complexity': {'time': 'O(n)', 'space': 'O(1) in place'},
             'edge_cases': ['empty array (print 0 then an empty line)', 'all values equal', 'single element'],
             'common_mistakes': ['Printing the original length instead of the new length',
                                 'Off-by-one when comparing with the last kept index']}},
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
  'rubric': {'required_approach': ['Counts every character in one pass with a hash map',
                                   'Second pass returns the first index whose count is 1'],
             'complexity': {'time': 'O(n)', 'space': 'O(alphabet), O(n) worst case'},
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
  'rubric': {'required_approach': ['Pushes opening brackets on a stack',
                                   'On a closing bracket, checks the stack top is its matching opener, then '
                                   'pops'],
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
  'rubric': {'required_approach': ['Intersects the two arrays as sets', 'Sorts the result before printing'],
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
  'rubric': {'required_approach': ['Slow and fast pointers: slow moves one node, fast moves two',
                                   'When fast reaches the end, slow is on the middle node, the second middle '
                                   'for an even count'],
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
  'rubric': {'required_approach': ['Sorts meetings by start time',
                                   'Checks each meeting starts at or after the previous one ends'],
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
  'rubric': {'required_approach': ['Two pointers from both ends of the sorted array',
                                   'Moves the left pointer up when the sum is too small and the right '
                                   'pointer down when it is too large'],
             'complexity': {'time': 'O(n)', 'space': 'O(1)'},
             'edge_cases': ['no pair exists (NO)',
                            'equal values forming the pair (3 3 for target 6)',
                            'negative values'],
             'common_mistakes': ['Using the same index twice',
                                 'Nested loops over all pairs, ignoring the sorted order (O(n^2))']}}]
