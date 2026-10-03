"""Curated bank of classic LeetCode-style problems.

Each problem is stored ONCE with:
- title / difficulty / statement / IO format / constraints
- reference_solution: verified working Python 3 program (stdin/stdout)
- test_inputs: list of stdin strings; expected outputs are DERIVED at load
  time by running the reference solution, guaranteeing byte-for-byte
  consistency. If reference_solution ever changes, test outputs update
  automatically \u2014 you can never end up with an inconsistent problem.
- buggy_solution (optional): the same program with 2-4 real bugs, used for
  Tech Mahindra's Automata Fix rounds.
"""
from __future__ import annotations
import random
import subprocess
import tempfile
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

_RAW: List[Dict[str, Any]] = [
    # ------------------------------------------------------------------ EASY
    {
        "id": "two-sum", "title": "Two Sum", "difficulty": "Easy", "topic": "arrays",
        "statement": "Given an array `nums` and a target integer, return the 0-indexed positions of the two numbers whose sum equals the target. Each input has exactly one solution.\n\nExample: nums=[2,7,11,15], target=9 -> `0 1`.",
        "input_format": "Line 1: n. Line 2: n space-separated integers. Line 3: target.",
        "output_format": "Two space-separated indices (i < j).",
        "constraints": "2 \u2264 n \u2264 10^4",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
t = int(input())
seen = {}
for i, v in enumerate(a):
    if t - v in seen:
        print(seen[t - v], i); break
    seen[v] = i
""",
        "buggy_solution":
"""n = int(input())
a = list(map(int, input().split()))
t = int(input())
seen = {}
for i, v in enumerate(a):
    if t + v in seen:
        print(seen[t - v], i); break
    seen[v] = i
""",
        "test_inputs": ["4\n2 7 11 15\n9", "3\n3 2 4\n6", "2\n3 3\n6", "5\n-1 -2 -3 -4 -5\n-8", "5\n1 5 3 8 2\n10"],
    },
    {
        "id": "reverse-string", "title": "Reverse String", "difficulty": "Easy", "topic": "strings",
        "statement": "Read a string and print it reversed. No leading/trailing whitespace in output.",
        "input_format": "Single line string.", "output_format": "Reversed string.",
        "constraints": "1 \u2264 |s| \u2264 10^5",
        "reference_solution": "print(input()[::-1])\n",
        "buggy_solution": "print(input()[::-2])\n",
        "test_inputs": ["hello", "a", "racecar", "Placemint", "12345"],
    },
    {
        "id": "fizzbuzz", "title": "Fizz Buzz", "difficulty": "Easy",
        # Doesn't genuinely fit any of the 8 topics (pure control-flow/modulo,
        # no array/string/DSA concept) -- tagged "arrays" as the least-bad
        # practical bucket rather than left untagged. Flagged during the
        # 2026-09 topic-tagging audit.
        "topic": "arrays",
        "statement": "For each integer from 1 to n, print 'Fizz' if divisible by 3, 'Buzz' if divisible by 5, 'FizzBuzz' if divisible by both, else the number. One per line.",
        "input_format": "Single integer n.", "output_format": "n lines.",
        "constraints": "1 \u2264 n \u2264 100",
        "reference_solution":
"""n = int(input())
for i in range(1, n + 1):
    if i % 15 == 0: print('FizzBuzz')
    elif i % 3 == 0: print('Fizz')
    elif i % 5 == 0: print('Buzz')
    else: print(i)
""",
        "buggy_solution":
"""n = int(input())
for i in range(1, n):
    if i % 15 == 0: print('FizzBuzz')
    elif i % 5 == 0: print('Fizz')
    elif i % 3 == 0: print('Buzz')
    else: print(i)
""",
        "test_inputs": ["5", "15", "1", "20", "30"],
    },
    {
        "id": "valid-palindrome", "title": "Valid Palindrome", "difficulty": "Easy", "topic": "two_pointer_sliding_window",
        "statement": "Return 'YES' if the input string is a palindrome ignoring case and non-alphanumeric characters, else 'NO'.",
        "input_format": "Single line string.", "output_format": "YES or NO.",
        "constraints": "1 \u2264 |s| \u2264 10^5",
        "reference_solution":
"""s = ''.join(c.lower() for c in input() if c.isalnum())
print('YES' if s == s[::-1] else 'NO')
""",
        "test_inputs": ["A man, a plan, a canal: Panama", "race a car", "abba", "hello", " "],
    },
    {
        "id": "max-subarray-sum", "title": "Maximum Subarray Sum (Kadane)", "difficulty": "Easy", "topic": "arrays",
        "statement": "Find the contiguous subarray with the largest sum and print that sum.",
        "input_format": "Line 1: n. Line 2: n integers.", "output_format": "Max sum.",
        "constraints": "1 \u2264 n \u2264 10^5",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
best = cur = a[0]
for x in a[1:]:
    cur = max(x, cur + x)
    best = max(best, cur)
print(best)
""",
        "buggy_solution":
"""n = int(input())
a = list(map(int, input().split()))
best = cur = a[0]
for x in a[1:]:
    cur = min(x, cur + x)
    best = max(best, cur)
print(best)
""",
        "test_inputs": ["9\n-2 1 -3 4 -1 2 1 -5 4", "1\n1", "5\n-1 -2 -3 -4 -5", "5\n5 4 -1 7 8", "3\n0 0 0"],
    },
    # ------------------------------------------------------------------ MEDIUM
    {
        "id": "group-anagrams", "title": "Group Anagrams (count)", "difficulty": "Medium", "topic": "strings",
        "statement": "Count the number of distinct anagram groups in the list of words. Two words are anagrams if they contain the same multiset of characters.",
        "input_format": "Line 1: n. Line 2: n space-separated words.",
        "output_format": "Number of distinct anagram groups.",
        "constraints": "1 \u2264 n \u2264 10^4",
        "reference_solution":
"""n = int(input())
words = input().split()
groups = {tuple(sorted(w)) for w in words}
print(len(groups))
""",
        "test_inputs": ["6\neat tea tan ate nat bat", "1\nsolo", "3\nabc bca cab", "4\nab ba abc cba", "5\naa aa aa bb cc"],
    },
    {
        "id": "longest-substring-no-repeat", "title": "Longest Substring Without Repeating Characters", "difficulty": "Medium", "topic": "two_pointer_sliding_window",
        "statement": "Given a string, print the length of the longest substring with all unique characters.",
        "input_format": "Single line string.", "output_format": "Integer length.",
        "constraints": "0 \u2264 |s| \u2264 5 * 10^4",
        "reference_solution":
"""s = input()
last = {}
start = best = 0
for i, c in enumerate(s):
    if c in last and last[c] >= start:
        start = last[c] + 1
    last[c] = i
    best = max(best, i - start + 1)
print(best)
""",
        "buggy_solution":
"""s = input()
last = {}
start = best = 0
for i, c in enumerate(s):
    if c in last and last[c] > start:
        start = last[c] + 1
    last[c] = i
    best = max(best, i - start + 1)
print(best)
""",
        "test_inputs": ["abcabcbb", "bbbbb", "pwwkew", "dvdf", "abcdefg"],
    },
    {
        "id": "coin-change", "title": "Coin Change (Min Coins)", "difficulty": "Medium", "topic": "2d_dp",
        "statement": "Given coin denominations and a target amount, find the minimum number of coins needed. Print -1 if impossible.",
        "input_format": "Line 1: n. Line 2: n coins. Line 3: amount.",
        "output_format": "Min coins or -1.",
        "constraints": "1 \u2264 n \u2264 12, 1 \u2264 amount \u2264 10^4",
        "reference_solution":
"""n = int(input())
coins = list(map(int, input().split()))
amount = int(input())
INF = amount + 1
dp = [0] + [INF] * amount
for i in range(1, amount + 1):
    for c in coins:
        if c <= i:
            dp[i] = min(dp[i], dp[i - c] + 1)
print(dp[amount] if dp[amount] <= amount else -1)
""",
        "test_inputs": ["3\n1 2 5\n11", "1\n2\n3", "1\n1\n0", "3\n1 3 4\n6", "4\n2 5 10 1\n27"],
    },
    {
        "id": "product-except-self", "title": "Product of Array Except Self", "difficulty": "Medium", "topic": "arrays",
        "statement": "Given an array, print an array where element i is the product of all other elements. Do NOT use division.",
        "input_format": "Line 1: n. Line 2: n integers.",
        "output_format": "n space-separated integers.",
        "constraints": "2 \u2264 n \u2264 10^5",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
out = [1] * n
p = 1
for i in range(n):
    out[i] = p; p *= a[i]
p = 1
for i in range(n - 1, -1, -1):
    out[i] *= p; p *= a[i]
print(' '.join(map(str, out)))
""",
        "test_inputs": ["4\n1 2 3 4", "5\n-1 1 0 -3 3", "2\n2 3", "3\n1 1 1", "5\n2 3 4 5 6"],
    },
    {
        "id": "rotate-image", "title": "Rotate Matrix 90\u00b0 Clockwise", "difficulty": "Medium", "topic": "arrays",
        "statement": "Rotate an n x n matrix by 90 degrees clockwise. Print the rotated matrix.",
        "input_format": "Line 1: n. Next n lines: n integers each.",
        "output_format": "n lines of n integers.",
        "constraints": "1 \u2264 n \u2264 100",
        "reference_solution":
"""n = int(input())
m = [list(map(int, input().split())) for _ in range(n)]
rot = [[m[n - 1 - j][i] for j in range(n)] for i in range(n)]
for row in rot: print(' '.join(map(str, row)))
""",
        "test_inputs": [
            "3\n1 2 3\n4 5 6\n7 8 9",
            "2\n1 2\n3 4",
            "1\n5",
            "4\n1 2 3 4\n5 6 7 8\n9 10 11 12\n13 14 15 16",
            "3\n0 0 0\n0 1 0\n0 0 0",
        ],
    },
    {
        "id": "num-islands", "title": "Number of Islands", "difficulty": "Medium", "topic": "graphs",
        "statement": "Count the number of islands (connected components of 1s, 4-directional) in a 2D grid of 0s and 1s.",
        "input_format": "Line 1: rows cols. Next rows lines: cols space-separated 0/1 values.",
        "output_format": "Island count.",
        "constraints": "1 \u2264 rows, cols \u2264 300",
        "reference_solution":
"""import sys
sys.setrecursionlimit(200000)
r, c = map(int, input().split())
g = [list(map(int, input().split())) for _ in range(r)]
def dfs(i, j):
    if i < 0 or j < 0 or i >= r or j >= c or g[i][j] != 1: return
    g[i][j] = 2
    dfs(i+1,j); dfs(i-1,j); dfs(i,j+1); dfs(i,j-1)
cnt = 0
for i in range(r):
    for j in range(c):
        if g[i][j] == 1:
            cnt += 1; dfs(i, j)
print(cnt)
""",
        "test_inputs": [
            "3 3\n1 1 0\n0 1 0\n1 0 1",
            "1 1\n0",
            "2 4\n1 0 1 0\n0 1 0 1",
            "3 3\n1 1 1\n1 1 1\n1 1 1",
            "4 4\n1 0 0 1\n0 0 0 0\n1 0 1 0\n1 0 1 1",
        ],
    },
    # ------------------------------------------------------------------ HARD
    {
        "id": "edit-distance", "title": "Edit Distance (Levenshtein)", "difficulty": "Hard", "topic": "2d_dp",
        "statement": "Compute the minimum number of insert/delete/replace operations to transform string a into string b.",
        "input_format": "Line 1: a. Line 2: b.",
        "output_format": "Integer distance.",
        "constraints": "0 \u2264 |a|,|b| \u2264 500",
        "reference_solution":
"""a = input(); b = input()
n, m = len(a), len(b)
dp = [[0]*(m+1) for _ in range(n+1)]
for i in range(n+1): dp[i][0] = i
for j in range(m+1): dp[0][j] = j
for i in range(1, n+1):
    for j in range(1, m+1):
        if a[i-1] == b[j-1]: dp[i][j] = dp[i-1][j-1]
        else: dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
print(dp[n][m])
""",
        "test_inputs": ["horse\nros", "intention\nexecution", "abc\nabc", "\na", "kitten\nsitting"],
    },
    {
        "id": "trap-rain", "title": "Trapping Rain Water", "difficulty": "Hard", "topic": "two_pointer_sliding_window",
        "statement": "Given non-negative integers representing bar heights, compute how much water it can trap after raining.",
        "input_format": "Line 1: n. Line 2: n integers.",
        "output_format": "Total trapped water.",
        "constraints": "0 \u2264 n \u2264 2 * 10^4",
        "reference_solution":
"""n = int(input())
h = list(map(int, input().split())) if n else []
if n == 0: print(0); import sys; sys.exit()
l, r = 0, n-1; lmax = rmax = 0; ans = 0
while l < r:
    if h[l] < h[r]:
        if h[l] >= lmax: lmax = h[l]
        else: ans += lmax - h[l]
        l += 1
    else:
        if h[r] >= rmax: rmax = h[r]
        else: ans += rmax - h[r]
        r -= 1
print(ans)
""",
        "test_inputs": ["12\n0 1 0 2 1 0 1 3 2 1 2 1", "6\n4 2 0 3 2 5", "3\n1 2 3", "5\n5 4 3 2 1", "0\n"],
    },
    {
        "id": "word-ladder-length", "title": "Word Ladder Length", "difficulty": "Hard", "topic": "graphs",
        "statement": "Given begin, end, and a list of words, find the shortest transformation sequence length changing one letter at a time. Each intermediate must be in the list. Print 0 if impossible.",
        "input_format": "Line 1: begin. Line 2: end. Line 3: n. Line 4: n space-separated words.",
        "output_format": "Length (including begin and end) or 0.",
        "constraints": "1 \u2264 n \u2264 5000, all same length",
        "reference_solution":
"""from collections import deque
begin = input(); end = input()
n = int(input())
words = set(input().split())
if end not in words: print(0); import sys; sys.exit()
q = deque([(begin, 1)]); seen = {begin}
while q:
    w, d = q.popleft()
    if w == end: print(d); break
    for i in range(len(w)):
        for c in 'abcdefghijklmnopqrstuvwxyz':
            nw = w[:i] + c + w[i+1:]
            if nw in words and nw not in seen:
                seen.add(nw); q.append((nw, d+1))
else:
    print(0)
""",
        "test_inputs": [
            "hit\ncog\n6\nhot dot dog lot log cog",
            "hit\ncog\n5\nhot dot dog lot log",
            "a\nc\n2\nb c",
            "abc\nxyz\n2\nabd xyz",
            "cat\ndog\n4\ncot cog dog cag",
        ],
    },
    # ------------------------------------------------------------------ MORE EASY
    {
        "id": "contains-duplicate", "title": "Contains Duplicate", "difficulty": "Easy", "topic": "arrays",
        "statement": "Return 'YES' if any value appears at least twice in the array, else 'NO'.",
        "input_format": "Line 1: n. Line 2: n integers.", "output_format": "YES or NO.",
        "constraints": "1 \u2264 n \u2264 10^5",
        "reference_solution":
"""n = int(input())
a = input().split()
print('YES' if len(set(a)) != len(a) else 'NO')
""",
        "buggy_solution":
"""n = int(input())
a = input().split()
print('NO' if len(set(a)) != len(a) else 'YES')
""",
        "test_inputs": ["4\n1 2 3 1", "4\n1 2 3 4", "10\n1 1 1 3 3 4 3 2 4 2", "1\n5", "5\n7 7 7 7 7"],
    },
    {
        "id": "missing-number", "title": "Missing Number", "difficulty": "Easy", "topic": "arrays",
        "statement": "Given an array of n distinct numbers taken from [0, n], find the one that is missing.",
        "input_format": "Line 1: n. Line 2: n integers.", "output_format": "Missing integer.",
        "constraints": "1 \u2264 n \u2264 10^4",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
print(n * (n + 1) // 2 - sum(a))
""",
        "test_inputs": ["3\n3 0 1", "2\n0 1", "9\n9 6 4 2 3 5 7 0 1", "1\n0", "5\n0 1 2 3 4"],
    },
    {
        "id": "buy-sell-stock", "title": "Best Time to Buy and Sell Stock", "difficulty": "Easy", "topic": "greedy",
        "statement": "Given daily prices, find the max profit from one buy + one later sell. Print 0 if impossible.",
        "input_format": "Line 1: n. Line 2: n prices.", "output_format": "Max profit.",
        "constraints": "1 \u2264 n \u2264 10^5",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
best = 0; lo = a[0]
for x in a:
    lo = min(lo, x); best = max(best, x - lo)
print(best)
""",
        "buggy_solution":
"""n = int(input())
a = list(map(int, input().split()))
best = 0; lo = a[0]
for x in a:
    best = max(best, x - lo); lo = min(lo, x)
print(best)
""",
        "test_inputs": ["6\n7 1 5 3 6 4", "5\n7 6 4 3 1", "1\n5", "5\n1 2 3 4 5", "5\n5 4 3 2 1"],
    },
    {
        "id": "climb-stairs", "title": "Climbing Stairs", "difficulty": "Easy", "topic": "2d_dp",
        "statement": "Count the number of distinct ways to climb n stairs taking 1 or 2 steps at a time.",
        "input_format": "Single integer n.", "output_format": "Number of ways.",
        "constraints": "1 \u2264 n \u2264 45",
        "reference_solution":
"""n = int(input())
a, b = 1, 1
for _ in range(n): a, b = b, a + b
print(a)
""",
        "test_inputs": ["2", "3", "5", "10", "45"],
    },
    {
        "id": "merge-sorted", "title": "Merge Two Sorted Arrays", "difficulty": "Easy", "topic": "two_pointer_sliding_window",
        "statement": "Merge two sorted integer arrays and print the merged sorted array (space-separated).",
        "input_format": "L1: n. L2: n ints. L3: m. L4: m ints.",
        "output_format": "n+m sorted ints, space-separated.",
        "constraints": "0 \u2264 n,m \u2264 10^4",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split())) if n else []
m = int(input())
b = list(map(int, input().split())) if m else []
out = []; i = j = 0
while i < n and j < m:
    if a[i] <= b[j]: out.append(a[i]); i += 1
    else: out.append(b[j]); j += 1
out += a[i:]; out += b[j:]
print(' '.join(map(str, out)))
""",
        "test_inputs": ["3\n1 3 5\n3\n2 4 6", "0\n0\n3\n1 2 3", "3\n1 2 3\n0\n0", "5\n1 1 1 1 1\n5\n2 2 2 2 2", "2\n-3 -1\n3\n-2 0 2"],
    },
    # ------------------------------------------------------------------ MORE MEDIUM
    {
        "id": "search-rotated", "title": "Search in Rotated Sorted Array", "difficulty": "Medium", "topic": "arrays",
        "statement": "Given a sorted array rotated at an unknown pivot, find the index of target or print -1. O(log n).",
        "input_format": "L1: n. L2: n ints. L3: target.", "output_format": "Index or -1.",
        "constraints": "1 \u2264 n \u2264 10^4",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
t = int(input())
l, r = 0, n - 1; ans = -1
while l <= r:
    m = (l + r) // 2
    if a[m] == t: ans = m; break
    if a[l] <= a[m]:
        if a[l] <= t < a[m]: r = m - 1
        else: l = m + 1
    else:
        if a[m] < t <= a[r]: l = m + 1
        else: r = m - 1
print(ans)
""",
        "buggy_solution":
"""n = int(input())
a = list(map(int, input().split()))
t = int(input())
l, r = 0, n - 1; ans = -1
while l < r:
    m = (l + r) // 2
    if a[m] == t: ans = m; break
    if a[l] <= a[m]:
        if a[l] <= t < a[m]: r = m - 1
        else: l = m + 1
    else:
        if a[m] < t <= a[r]: l = m + 1
        else: r = m - 1
print(ans)
""",
        "test_inputs": ["7\n4 5 6 7 0 1 2\n0", "7\n4 5 6 7 0 1 2\n3", "1\n1\n0", "5\n5 1 2 3 4\n1", "7\n6 7 0 1 2 4 5\n5"],
    },
    {
        "id": "container-water", "title": "Container With Most Water", "difficulty": "Medium", "topic": "two_pointer_sliding_window",
        "statement": "Given heights, find the max water two lines can trap (area = min(h[i],h[j])*(j-i)).",
        "input_format": "L1: n. L2: n heights.", "output_format": "Max area.",
        "constraints": "2 \u2264 n \u2264 10^5",
        "reference_solution":
"""n = int(input())
h = list(map(int, input().split()))
l, r = 0, n - 1; best = 0
while l < r:
    best = max(best, min(h[l], h[r]) * (r - l))
    if h[l] < h[r]: l += 1
    else: r -= 1
print(best)
""",
        "test_inputs": ["9\n1 8 6 2 5 4 8 3 7", "2\n1 1", "3\n4 3 2", "5\n1 2 3 4 5", "6\n1 2 4 3 5 4"],
    },
    {
        "id": "longest-palindromic", "title": "Longest Palindromic Substring Length", "difficulty": "Medium", "topic": "strings",
        "statement": "Print the length of the longest palindromic substring.",
        "input_format": "Single line string.", "output_format": "Integer length.",
        "constraints": "1 \u2264 |s| \u2264 1000",
        "reference_solution":
"""s = input(); n = len(s); best = 1
def expand(l, r):
    while l >= 0 and r < n and s[l] == s[r]: l -= 1; r += 1
    return r - l - 1
for i in range(n):
    best = max(best, expand(i, i), expand(i, i + 1))
print(best)
""",
        "test_inputs": ["babad", "cbbd", "a", "ac", "racecar"],
    },
    {
        "id": "combination-sum-count", "title": "Combination Sum (Count)", "difficulty": "Medium", "topic": "2d_dp",
        "statement": "Given distinct positive integers and a target, count unordered combinations (with repetition) summing to target.",
        "input_format": "L1: n. L2: n ints. L3: target.", "output_format": "Combination count.",
        "constraints": "1 \u2264 n \u2264 30, 1 \u2264 target \u2264 500",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
t = int(input())
a.sort()
res = 0
def dfs(i, rem):
    global res
    if rem == 0: res += 1; return
    if i == n or rem < 0: return
    for j in range(i, n):
        if a[j] > rem: break
        dfs(j, rem - a[j])
dfs(0, t)
print(res)
""",
        "test_inputs": ["3\n2 3 6\n7", "2\n2 3\n5", "1\n2\n1", "3\n1 2 3\n4", "2\n7 3\n18"],
    },
    # ------------------------------------------------------------------ MORE HARD (user's key ask)
    {
        "id": "median-two-sorted", "title": "Median of Two Sorted Arrays", "difficulty": "Hard", "topic": "arrays",
        "statement": "Given two sorted arrays, print the median of the combined array. If total length is even, print the two middle values averaged (as float with one decimal).",
        "input_format": "L1: n. L2: n ints. L3: m. L4: m ints.",
        "output_format": "Median as float (one decimal).",
        "constraints": "0 \u2264 n,m \u2264 10^4, n+m \u2265 1",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split())) if n else (input(), [])[1]
m = int(input())
b = list(map(int, input().split())) if m else (input(), [])[1]
c = sorted(a + b); k = len(c)
if k % 2: print(f'{c[k//2]:.1f}')
else: print(f'{(c[k//2-1] + c[k//2]) / 2:.1f}')
""",
        "test_inputs": ["2\n1 3\n1\n2", "2\n1 2\n2\n3 4", "0\n0\n1\n1", "3\n1 2 3\n3\n4 5 6", "1\n100\n1\n200"],
    },
    {
        "id": "largest-rect-hist", "title": "Largest Rectangle in Histogram", "difficulty": "Hard", "topic": "advanced_dsa",
        "statement": "Given n bar heights, find the area of the largest rectangle in the histogram.",
        "input_format": "L1: n. L2: n heights.", "output_format": "Max area.",
        "constraints": "1 \u2264 n \u2264 10^5",
        "reference_solution":
"""n = int(input())
h = list(map(int, input().split())) + [0]
st = []; best = 0
for i, x in enumerate(h):
    while st and h[st[-1]] > x:
        top = st.pop()
        w = i if not st else i - st[-1] - 1
        best = max(best, h[top] * w)
    st.append(i)
print(best)
""",
        "test_inputs": ["6\n2 1 5 6 2 3", "2\n2 4", "1\n5", "5\n1 1 1 1 1", "7\n6 7 5 2 4 5 9"],
    },
    {
        "id": "longest-valid-paren", "title": "Longest Valid Parentheses", "difficulty": "Hard", "topic": "advanced_dsa",
        "statement": "Given a string of '(' and ')', print the length of the longest valid (well-formed) substring.",
        "input_format": "Single line string.", "output_format": "Integer length.",
        "constraints": "0 \u2264 |s| \u2264 3 * 10^4",
        "reference_solution":
"""import sys
s = sys.stdin.read().rstrip('\\n')
st = [-1]; best = 0
for i, c in enumerate(s):
    if c == '(': st.append(i)
    else:
        st.pop()
        if not st: st.append(i)
        else: best = max(best, i - st[-1])
print(best)
""",
        "test_inputs": ["(()", ")()())", "", "()(()", "(()())"],
    },
    {
        "id": "n-queens-count", "title": "N-Queens (Count Solutions)", "difficulty": "Hard", "topic": "advanced_dsa",
        "statement": "Count the number of distinct N-Queens board arrangements for a given n.",
        "input_format": "Single integer n.", "output_format": "Solution count.",
        "constraints": "1 \u2264 n \u2264 10",
        "reference_solution":
"""n = int(input()); count = 0
cols = set(); d1 = set(); d2 = set()
def solve(r):
    global count
    if r == n: count += 1; return
    for c in range(n):
        if c in cols or (r - c) in d1 or (r + c) in d2: continue
        cols.add(c); d1.add(r - c); d2.add(r + c)
        solve(r + 1)
        cols.remove(c); d1.remove(r - c); d2.remove(r + c)
solve(0); print(count)
""",
        "test_inputs": ["4", "1", "8", "6", "9"],
    },
    {
        "id": "merge-k-sorted", "title": "Merge K Sorted Arrays", "difficulty": "Hard", "topic": "advanced_dsa",
        "statement": "Merge k sorted arrays into one sorted output (space-separated).",
        "input_format": "L1: k. Then k pairs of lines: length line + values line.",
        "output_format": "All values sorted, space-separated.",
        "constraints": "1 \u2264 k \u2264 100, total values \u2264 10^5",
        "reference_solution":
"""import heapq
k = int(input()); arrs = []
for _ in range(k):
    n = int(input())
    arrs.append(list(map(int, input().split())) if n else [])
out = list(heapq.merge(*arrs))
print(' '.join(map(str, out)))
""",
        "test_inputs": [
            "3\n3\n1 4 5\n3\n1 3 4\n2\n2 6",
            "1\n3\n1 2 3",
            "2\n0\n3\n5 6 7",
            "3\n1\n1\n1\n2\n1\n3",
            "4\n2\n-3 -1\n2\n0 2\n1\n5\n2\n-4 4",
        ],
    },
    {
        "id": "sudoku-valid", "title": "Validate a 9x9 Sudoku Board", "difficulty": "Hard", "topic": "arrays",
        "statement": "Given a 9x9 board (0 = empty), print 'VALID' if no row / column / 3x3 box has duplicate 1-9 values, else 'INVALID'.",
        "input_format": "9 lines of 9 space-separated ints.",
        "output_format": "VALID or INVALID.",
        "constraints": "-",
        "reference_solution":
"""grid = [list(map(int, input().split())) for _ in range(9)]
def ok(cells):
    seen = set()
    for v in cells:
        if v == 0: continue
        if v in seen: return False
        seen.add(v)
    return True
for i in range(9):
    if not ok(grid[i]): print('INVALID'); import sys; sys.exit()
    if not ok([grid[r][i] for r in range(9)]): print('INVALID'); import sys; sys.exit()
for br in range(0, 9, 3):
    for bc in range(0, 9, 3):
        if not ok([grid[r][c] for r in range(br, br+3) for c in range(bc, bc+3)]):
            print('INVALID'); import sys; sys.exit()
print('VALID')
""",
        "test_inputs": [
            "5 3 0 0 7 0 0 0 0\n6 0 0 1 9 5 0 0 0\n0 9 8 0 0 0 0 6 0\n8 0 0 0 6 0 0 0 3\n4 0 0 8 0 3 0 0 1\n7 0 0 0 2 0 0 0 6\n0 6 0 0 0 0 2 8 0\n0 0 0 4 1 9 0 0 5\n0 0 0 0 8 0 0 7 9",
            "5 5 0 0 7 0 0 0 0\n6 0 0 1 9 5 0 0 0\n0 9 8 0 0 0 0 6 0\n8 0 0 0 6 0 0 0 3\n4 0 0 8 0 3 0 0 1\n7 0 0 0 2 0 0 0 6\n0 6 0 0 0 0 2 8 0\n0 0 0 4 1 9 0 0 5\n0 0 0 0 8 0 0 7 9",
            "0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0",
            "1 2 3 4 5 6 7 8 9\n4 5 6 7 8 9 1 2 3\n7 8 9 1 2 3 4 5 6\n2 3 4 5 6 7 8 9 1\n5 6 7 8 9 1 2 3 4\n8 9 1 2 3 4 5 6 7\n3 4 5 6 7 8 9 1 2\n6 7 8 9 1 2 3 4 5\n9 1 2 3 4 5 6 7 8",
            "1 1 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0 0",
        ],
    },
    # ------------------------------------------------------------------ TREES (net-new, 2026-09)
    {
        "id": "tree-level-order", "title": "Binary Tree Level Order Traversal", "topic": "trees",
        "difficulty": "Easy",
        "statement": "A binary tree is given as a level-order list of values on a single line, where 'N' marks a missing child (root first, then each node's left then right child in BFS order). Print the tree's level-order traversal: one line per depth level, values space-separated left to right.",
        "input_format": "Single line: space-separated values and 'N' tokens.", "output_format": "One line per level.",
        "constraints": "1 <= number of real nodes <= 1000",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
level = [root]
while level:
    print(' '.join(str(n.v) for n in level))
    nxt = []
    for n in level:
        if n.l: nxt.append(n.l)
        if n.r: nxt.append(n.r)
    level = nxt
""",
        "test_inputs": ["3 9 20 N N 15 7", "1", "1 2 3 N N N N", "5 3 8 1 4 7 9", "1 N 2 N 3"],
    },
    {
        "id": "tree-max-depth", "title": "Maximum Depth of Binary Tree", "topic": "trees",
        "difficulty": "Easy",
        "statement": "Given a binary tree as a level-order list ('N' = missing child), print its maximum depth (the number of nodes on the longest root-to-leaf path).",
        "input_format": "Single line: level-order values with 'N' for null.", "output_format": "Single integer.",
        "constraints": "1 <= number of real nodes <= 1000",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
def depth(n):
    if n is None: return 0
    return 1 + max(depth(n.l), depth(n.r))
print(depth(root))
""",
        "test_inputs": ["3 9 20 N N 15 7", "1", "1 N 2 N 3", "5 3 8 1 4 7 9", "1 2 N N 3"],
    },
    {
        "id": "tree-validate-bst", "title": "Validate Binary Search Tree", "topic": "trees",
        "difficulty": "Medium",
        "statement": "Given a binary tree as a level-order list ('N' = missing child), print 'YES' if it is a valid binary search tree (every node's value is strictly greater than all values in its left subtree and strictly less than all values in its right subtree), else 'NO'.",
        "input_format": "Single line: level-order values with 'N' for null.", "output_format": "YES or NO.",
        "constraints": "1 <= number of real nodes <= 1000",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
def valid(n, lo, hi):
    if n is None: return True
    if not (lo < n.v < hi): return False
    return valid(n.l, lo, n.v) and valid(n.r, n.v, hi)
print('YES' if valid(root, float('-inf'), float('inf')) else 'NO')
""",
        "buggy_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
def valid(n, lo, hi):
    if n is None: return True
    if not (lo <= n.v <= hi): return False
    return valid(n.l, lo, n.v) and valid(n.r, n.v, hi)
print('YES' if valid(root, float('-inf'), float('inf')) else 'NO')
""",
        "test_inputs": ["2 2", "5 3 8 1 4 7 9", "5 1 4 N N 3 6", "1", "5 4 6 N N 3 7"],
    },
    {
        "id": "tree-diameter", "title": "Diameter of Binary Tree", "topic": "trees",
        "difficulty": "Medium",
        "statement": "Given a binary tree as a level-order list ('N' = missing child), print its diameter: the number of edges on the longest path between any two nodes (the path may or may not pass through the root).",
        "input_format": "Single line: level-order values with 'N' for null.", "output_format": "Single integer.",
        "constraints": "1 <= number of real nodes <= 1000",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
best = 0
def depth(n):
    global best
    if n is None: return 0
    l = depth(n.l); r = depth(n.r)
    best = max(best, l + r)
    return 1 + max(l, r)
depth(root)
print(best)
""",
        "test_inputs": ["3 9 20 N N 15 7", "1", "1 2 N N 3", "1 2 3 4 5", "5 3 8 1 4 7 9"],
    },
    {
        "id": "tree-symmetric", "title": "Symmetric Tree", "topic": "trees",
        "difficulty": "Easy",
        "statement": "Given a binary tree as a level-order list ('N' = missing child), print 'YES' if it is a mirror of itself (symmetric around its center), else 'NO'.",
        "input_format": "Single line: level-order values with 'N' for null.", "output_format": "YES or NO.",
        "constraints": "1 <= number of real nodes <= 1000",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
def mirror(a, b):
    if a is None and b is None: return True
    if a is None or b is None: return False
    return a.v == b.v and mirror(a.l, b.r) and mirror(a.r, b.l)
print('YES' if root is None or mirror(root.l, root.r) else 'NO')
""",
        "buggy_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
def mirror(a, b):
    if a is None and b is None: return True
    if a is None or b is None: return False
    return a.v == b.v and mirror(a.l, b.l) and mirror(a.r, b.r)
print('YES' if root is None or mirror(root.l, root.r) else 'NO')
""",
        "test_inputs": ["1 2 2 3 4 4 3", "1 2 2 N 3 N 3", "1", "3 9 20 N N 15 7", "1 2 2 N N N N"],
    },
    {
        "id": "tree-balanced", "title": "Balanced Binary Tree", "topic": "trees",
        "difficulty": "Easy",
        "statement": "Given a binary tree as a level-order list ('N' = missing child), print 'YES' if it is height-balanced (for every node, the heights of its left and right subtrees differ by at most 1), else 'NO'.",
        "input_format": "Single line: level-order values with 'N' for null.", "output_format": "YES or NO.",
        "constraints": "1 <= number of real nodes <= 1000",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
ok = True
def h(n):
    global ok
    if n is None: return 0
    lh = h(n.l); rh = h(n.r)
    if abs(lh - rh) > 1: ok = False
    return 1 + max(lh, rh)
h(root)
print('YES' if ok else 'NO')
""",
        "test_inputs": ["3 9 20 N N 15 7", "1 2 N 3 N 4", "1", "5 3 8 1 4 7 9", "1 2 2 3 3 N N 4 4"],
    },
    {
        "id": "tree-path-sum", "title": "Path Sum", "topic": "trees",
        "difficulty": "Medium",
        "statement": "A binary tree is given as a level-order list ('N' = missing child) on the first line, and a target integer on the second line. Print 'YES' if there is a root-to-leaf path whose node values sum to the target, else 'NO'.",
        "input_format": "Line 1: level-order values with 'N' for null. Line 2: target integer.", "output_format": "YES or NO.",
        "constraints": "1 <= number of real nodes <= 1000",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
target = int(input())
def has(n, rem):
    if n is None: return False
    if n.l is None and n.r is None:
        return rem == n.v
    return has(n.l, rem - n.v) or has(n.r, rem - n.v)
print('YES' if has(root, target) else 'NO')
""",
        "test_inputs": ["5 4 8 11 N 13 4 7 2 N N 5 1\n22", "1 2 3\n5", "1\n1", "1\n2", "3 9 20 N N 15 7\n38"],
    },
    {
        "id": "tree-invert", "title": "Invert Binary Tree", "topic": "trees",
        "difficulty": "Easy",
        "statement": "Given a binary tree as a level-order list ('N' = missing child), invert it (swap every node's left and right children) and print the level-order traversal of the resulting tree, one line per level.",
        "input_format": "Single line: level-order values with 'N' for null.", "output_format": "One line per level of the inverted tree.",
        "constraints": "1 <= number of real nodes <= 1000",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
def invert(n):
    if n is None: return
    n.l, n.r = n.r, n.l
    invert(n.l); invert(n.r)
invert(root)
level = [root]
while level:
    print(' '.join(str(n.v) for n in level))
    nxt = []
    for n in level:
        if n.l: nxt.append(n.l)
        if n.r: nxt.append(n.r)
    level = nxt
""",
        "test_inputs": ["4 2 7 1 3 6 9", "1", "1 2 N", "3 9 20 N N 15 7", "1 2 3 4 N N 5"],
    },
    {
        "id": "tree-kth-smallest-bst", "title": "Kth Smallest Element in a BST", "topic": "trees",
        "difficulty": "Medium",
        "statement": "A valid binary search tree is given as a level-order list ('N' = missing child) on the first line, and an integer k on the second line. Print the k-th smallest value in the tree (k=1 is the smallest).",
        "input_format": "Line 1: level-order values with 'N' for null (guaranteed a valid BST). Line 2: k.", "output_format": "Single integer.",
        "constraints": "1 <= k <= number of nodes",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
k = int(input())
res = []
def inorder(n):
    if n is None or len(res) >= k: return
    inorder(n.l)
    if len(res) < k: res.append(n.v)
    inorder(n.r)
inorder(root)
print(res[k-1])
""",
        "test_inputs": ["5 3 8 1 4 7 9\n1", "5 3 8 1 4 7 9\n4", "5 3 8 1 4 7 9\n7", "1\n1", "3 1 4 N 2\n2"],
    },
    {
        "id": "tree-lca-bst", "title": "Lowest Common Ancestor in a BST", "topic": "trees",
        "difficulty": "Medium",
        "statement": "A valid binary search tree is given as a level-order list ('N' = missing child) on the first line, and two node values p and q on the second line (both guaranteed present in the tree). Print the value of their lowest common ancestor.",
        "input_format": "Line 1: level-order values with 'N' for null (guaranteed a valid BST). Line 2: p q.", "output_format": "Single integer.",
        "constraints": "p and q are distinct values present in the tree",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
p, q = map(int, input().split())
node = root
while node:
    if p < node.v and q < node.v: node = node.l
    elif p > node.v and q > node.v: node = node.r
    else: break
print(node.v)
""",
        "test_inputs": ["5 3 8 1 4 7 9\n1 4", "5 3 8 1 4 7 9\n7 9", "5 3 8 1 4 7 9\n1 9", "6 2 8 0 4 7 9\n2 4", "6 2 8 0 4 7 9\n0 9"],
    },
    {
        "id": "tree-sum-root-to-leaf", "title": "Sum Root to Leaf Numbers", "topic": "trees",
        "difficulty": "Medium",
        "statement": "A binary tree is given as a level-order list ('N' = missing child); every node's value is a single digit 0-9. Each root-to-leaf path represents a number formed by concatenating the digits along the path. Print the sum of all such numbers over every root-to-leaf path.",
        "input_format": "Single line: level-order digit values with 'N' for null.", "output_format": "Single integer.",
        "constraints": "1 <= number of real nodes <= 1000, node values are digits 0-9",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
total = 0
def dfs(n, num):
    global total
    if n is None: return
    num = num * 10 + n.v
    if n.l is None and n.r is None:
        total += num
        return
    dfs(n.l, num); dfs(n.r, num)
dfs(root, 0)
print(total)
""",
        "test_inputs": ["4 9 0 5 1", "1", "1 2 3", "0", "9 8 7"],
    },
    {
        "id": "tree-right-side-view", "title": "Binary Tree Right Side View", "topic": "trees",
        "difficulty": "Medium",
        "statement": "Given a binary tree as a level-order list ('N' = missing child), print the values visible when looking at the tree from the right side, ordered from the top level to the bottom level, space-separated on one line.",
        "input_format": "Single line: level-order values with 'N' for null.", "output_format": "Space-separated integers, one per level.",
        "constraints": "1 <= number of real nodes <= 1000",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
level = [root]
out = []
while level:
    out.append(level[-1].v)
    nxt = []
    for n in level:
        if n.l: nxt.append(n.l)
        if n.r: nxt.append(n.r)
    level = nxt
print(' '.join(map(str, out)))
""",
        "test_inputs": ["3 9 20 N N 15 7", "1", "1 N 2", "1 2 3 4", "5 3 8 1 4 7 9"],
    },
    {
        "id": "tree-min-depth", "title": "Minimum Depth of Binary Tree", "topic": "trees",
        "difficulty": "Easy",
        "statement": "Given a binary tree as a level-order list ('N' = missing child), print its minimum depth: the number of nodes on the shortest path from the root down to any leaf (a leaf has no children at all).",
        "input_format": "Single line: level-order values with 'N' for null.", "output_format": "Single integer.",
        "constraints": "1 <= number of real nodes <= 1000",
        "reference_solution":
"""from collections import deque
class N:
    def __init__(self, v):
        self.v = int(v); self.l = None; self.r = None
def build(vals):
    if not vals or vals[0] == 'N':
        return None
    root = N(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] != 'N':
            node.l = N(vals[i]); q.append(node.l)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.r = N(vals[i]); q.append(node.r)
        i += 1
    return root
vals = input().split()
root = build(vals)
from collections import deque as dq
def mindepth(n):
    if n is None: return 0
    q = dq([(n, 1)])
    while q:
        node, d = q.popleft()
        if node.l is None and node.r is None:
            return d
        if node.l: q.append((node.l, d + 1))
        if node.r: q.append((node.r, d + 1))
print(mindepth(root))
""",
        "test_inputs": ["2 N 3 N 4 N 5", "1", "3 9 20 N N 15 7", "1 2", "5 3 8 1 4 7 9"],
    },
    # ------------------------------------------------------------------ GREEDY (net-new, 2026-09)
    {
        "id": "greedy-activity-selection", "title": "Maximum Non-overlapping Activities", "topic": "greedy",
        "difficulty": "Medium",
        "statement": "Given n activities, each with a start and end time, find the maximum number of activities a single person can perform such that no two performed activities overlap (an activity ending exactly when another starts does not count as overlapping).",
        "input_format": "Line 1: n. Line 2: n start times. Line 3: n end times.", "output_format": "Single integer: max number of non-overlapping activities.",
        "constraints": "1 <= n <= 10^4",
        "reference_solution":
"""n = int(input())
starts = list(map(int, input().split()))
ends = list(map(int, input().split()))
acts = sorted(zip(starts, ends), key=lambda x: x[1])
count = 0
last_end = float('-inf')
for s, e in acts:
    if s >= last_end:
        count += 1
        last_end = e
print(count)
""",
        "test_inputs": ["4\n1 3 0 5\n2 4 6 7", "1\n0\n5", "3\n1 1 1\n2 2 2", "5\n0 2 4 6 8\n1 3 5 7 9", "3\n1 2 3\n10 3 4"],
    },
    {
        "id": "greedy-merge-intervals", "title": "Merge Overlapping Intervals", "topic": "greedy",
        "difficulty": "Medium",
        "statement": "Given n intervals, merge all overlapping intervals (two intervals overlap if one starts at or before the other ends) and print the resulting intervals in increasing order of start, one 'start end' pair per line.",
        "input_format": "Line 1: n. Next n lines: 'start end'.", "output_format": "One 'start end' pair per merged interval, one per line.",
        "constraints": "1 <= n <= 10^4",
        "reference_solution":
"""n = int(input())
ivs = [tuple(map(int, input().split())) for _ in range(n)]
ivs.sort()
merged = []
for s, e in ivs:
    if merged and s <= merged[-1][1]:
        merged[-1] = (merged[-1][0], max(merged[-1][1], e))
    else:
        merged.append((s, e))
for s, e in merged:
    print(s, e)
""",
        "test_inputs": ["4\n1 3\n2 6\n8 10\n15 18", "2\n1 4\n4 5", "1\n1 1", "3\n1 4\n0 4\n3 5", "5\n5 7\n1 3\n2 4\n6 8\n10 12"],
    },
    {
        "id": "greedy-non-overlapping-removals", "title": "Non-overlapping Intervals (Minimum Removals)", "topic": "greedy",
        "difficulty": "Medium",
        "statement": "Given n intervals, find the minimum number of intervals to remove so that the rest do not overlap (an interval ending exactly when another starts does not count as overlapping).",
        "input_format": "Line 1: n. Next n lines: 'start end'.", "output_format": "Single integer: minimum removals.",
        "constraints": "1 <= n <= 10^4",
        "reference_solution":
"""n = int(input())
ivs = [tuple(map(int, input().split())) for _ in range(n)]
ivs.sort(key=lambda x: x[1])
keep = 0
last_end = float('-inf')
for s, e in ivs:
    if s >= last_end:
        keep += 1
        last_end = e
print(n - keep)
""",
        "test_inputs": ["4\n1 2\n2 3\n3 4\n1 3", "2\n1 2\n1 2", "3\n1 100000\n11 22\n1 11", "1\n1 2", "6\n1 2\n2 3\n3 4\n4 5\n5 6\n6 7"],
    },
    {
        "id": "greedy-jump-game", "title": "Jump Game (Can Reach End)", "topic": "greedy",
        "difficulty": "Medium",
        "statement": "Given an array where each element is the maximum jump length from that position, starting at index 0, print 'YES' if you can reach the last index, else 'NO'.",
        "input_format": "Line 1: n. Line 2: n integers.", "output_format": "YES or NO.",
        "constraints": "1 <= n <= 10^5",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
reach = 0
ok = True
for i in range(n):
    if i > reach:
        ok = False
        break
    reach = max(reach, i + a[i])
print('YES' if ok else 'NO')
""",
        "buggy_solution":
"""n = int(input())
a = list(map(int, input().split()))
reach = 0
ok = True
for i in range(n):
    if i >= reach:
        ok = False
        break
    reach = max(reach, i + a[i])
print('YES' if ok else 'NO')
""",
        "test_inputs": ["5\n2 3 1 1 4", "5\n3 2 1 0 4", "1\n0", "3\n1 0 1", "4\n1 1 1 1"],
    },
    {
        "id": "greedy-jump-game-ii", "title": "Jump Game II (Minimum Jumps)", "topic": "greedy",
        "difficulty": "Medium",
        "statement": "Given an array where each element is the maximum jump length from that position, starting at index 0, print the minimum number of jumps needed to reach the last index. It is guaranteed the last index is always reachable.",
        "input_format": "Line 1: n. Line 2: n integers.", "output_format": "Single integer: minimum jumps.",
        "constraints": "1 <= n <= 10^5",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
jumps = 0
cur_end = 0
farthest = 0
for i in range(n - 1):
    farthest = max(farthest, i + a[i])
    if i == cur_end:
        jumps += 1
        cur_end = farthest
print(jumps)
""",
        "test_inputs": ["5\n2 3 1 1 4", "1\n0", "4\n1 1 1 1", "3\n2 1 1", "2\n1 1"],
    },
    {
        "id": "greedy-gas-station", "title": "Gas Station", "topic": "greedy",
        "difficulty": "Medium",
        "statement": "There are n gas stations in a circle. Starting at station i with an empty tank costs cost[i] gas to reach station i+1 and gains gas[i] gas at station i. Print the 0-indexed starting station index that allows completing the full circuit. It is guaranteed exactly one such starting index exists (sum of gas >= sum of cost).",
        "input_format": "Line 1: n. Line 2: n gas values. Line 3: n cost values.", "output_format": "Single integer: the starting station index.",
        "constraints": "1 <= n <= 10^4, sum(gas) >= sum(cost)",
        "reference_solution":
"""n = int(input())
gas = list(map(int, input().split()))
cost = list(map(int, input().split()))
tank = 0
start = 0
for i in range(n):
    tank += gas[i] - cost[i]
    if tank < 0:
        start = i + 1
        tank = 0
print(start)
""",
        "test_inputs": ["5\n1 2 3 4 5\n3 4 5 1 2", "2\n5 1\n4 2", "1\n5\n5", "4\n4 5 2 6\n3 3 5 5", "3\n3 4 4\n3 4 3"],
    },
    {
        "id": "greedy-candy-distribution", "title": "Candy Distribution", "topic": "greedy",
        "difficulty": "Hard",
        "statement": "n children stand in a line, each with a rating. Every child must get at least 1 candy, and any child with a strictly higher rating than an immediate neighbor must get strictly more candy than that neighbor. Print the minimum total number of candies needed.",
        "input_format": "Line 1: n. Line 2: n ratings.", "output_format": "Single integer: minimum total candies.",
        "constraints": "1 <= n <= 10^5",
        "reference_solution":
"""n = int(input())
r = list(map(int, input().split()))
c = [1] * n
for i in range(1, n):
    if r[i] > r[i - 1]:
        c[i] = c[i - 1] + 1
for i in range(n - 2, -1, -1):
    if r[i] > r[i + 1]:
        c[i] = max(c[i], c[i + 1] + 1)
print(sum(c))
""",
        "test_inputs": ["3\n1 0 2", "3\n1 2 2", "1\n5", "5\n1 2 3 4 5", "5\n5 4 3 2 1"],
    },
    {
        "id": "greedy-assign-cookies", "title": "Assign Cookies", "topic": "greedy",
        "difficulty": "Easy",
        "statement": "Each child i has a greed factor g[i] (the minimum cookie size that satisfies them), and each cookie j has a size s[j]. Each child can be assigned at most one cookie, and only if that cookie's size is >= the child's greed factor. Maximize and print the number of content children.",
        "input_format": "Line 1: n (children). Line 2: n greed factors. Line 3: m (cookies). Line 4: m cookie sizes.", "output_format": "Single integer: number of content children.",
        "constraints": "1 <= n, m <= 10^4",
        "reference_solution":
"""n = int(input())
g = list(map(int, input().split()))
m = int(input())
s = list(map(int, input().split()))
g.sort(); s.sort()
i = j = 0
count = 0
while i < n and j < m:
    if s[j] >= g[i]:
        count += 1; i += 1; j += 1
    else:
        j += 1
print(count)
""",
        "test_inputs": ["2\n1 2\n3\n1 2 3", "3\n1 2 3\n3\n1 1 1", "1\n5\n1\n3", "4\n1 1 1 1\n2\n1 1", "3\n3 2 1\n3\n1 2 3"],
    },
    {
        "id": "greedy-boats-save-people", "title": "Boats to Save People", "topic": "greedy",
        "difficulty": "Medium",
        "statement": "n people have given weights. Each boat carries at most 2 people at a time, as long as their combined weight does not exceed a given limit. Print the minimum number of boats needed to carry everyone.",
        "input_format": "Line 1: n. Line 2: n weights. Line 3: weight limit per boat.", "output_format": "Single integer: minimum boats.",
        "constraints": "1 <= n <= 5*10^4, every individual weight <= limit",
        "reference_solution":
"""n = int(input())
w = list(map(int, input().split()))
limit = int(input())
w.sort()
i, j = 0, n - 1
boats = 0
while i <= j:
    if w[i] + w[j] <= limit:
        i += 1
    j -= 1
    boats += 1
print(boats)
""",
        "test_inputs": ["4\n1 2 2 3\n3", "4\n3 2 2 1\n3", "1\n5\n5", "3\n2 2 2\n4", "6\n1 2 3 4 5 6\n7"],
    },
    {
        "id": "greedy-min-arrows-balloons", "title": "Minimum Arrows to Burst Balloons", "topic": "greedy",
        "difficulty": "Medium",
        "statement": "Given n balloons as intervals [start, end] along the x-axis, an arrow shot at position x bursts every balloon whose interval contains x (a balloon whose interval endpoint exactly equals x is also burst). Print the minimum number of arrows needed to burst every balloon.",
        "input_format": "Line 1: n. Next n lines: 'start end'.", "output_format": "Single integer: minimum arrows.",
        "constraints": "1 <= n <= 10^5",
        "reference_solution":
"""n = int(input())
ivs = [tuple(map(int, input().split())) for _ in range(n)]
ivs.sort(key=lambda x: x[1])
arrows = 0
end = float('-inf')
for s, e in ivs:
    if s > end:
        arrows += 1
        end = e
print(arrows)
""",
        "test_inputs": ["4\n10 16\n2 8\n1 6\n7 12", "4\n1 2\n3 4\n5 6\n7 8", "4\n1 2\n2 3\n3 4\n4 5", "1\n1 1", "3\n1 10\n2 3\n4 5"],
    },
    {
        "id": "greedy-two-city-scheduling", "title": "Two City Scheduling", "topic": "greedy",
        "difficulty": "Medium",
        "statement": "There are 2n people to fly to city A or city B; exactly n must go to each city. Sending person i to city A costs costA[i], to city B costs costB[i]. Print the minimum total cost to send everyone while sending exactly n people to each city.",
        "input_format": "Line 1: n. Line 2: 2n costs to city A. Line 3: 2n costs to city B.", "output_format": "Single integer: minimum total cost.",
        "constraints": "1 <= n <= 500",
        "reference_solution":
"""n = int(input())
costA = list(map(int, input().split()))
costB = list(map(int, input().split()))
order = sorted(range(2 * n), key=lambda i: costA[i] - costB[i])
total = 0
for idx, i in enumerate(order):
    if idx < n:
        total += costA[i]
    else:
        total += costB[i]
print(total)
""",
        "test_inputs": ["2\n10 30 400 30\n20 200 50 20", "1\n10 20\n30 40", "3\n1 2 3 4 5 6\n6 5 4 3 2 1", "1\n5 5\n5 5", "2\n100 50 50 100\n50 100 100 50"],
    },
    {
        "id": "greedy-min-platforms", "title": "Minimum Platforms Needed", "topic": "greedy",
        "difficulty": "Medium",
        "statement": "A railway station has n trains with given arrival and departure times. Print the minimum number of platforms needed so that no train ever has to wait (a platform can be reused once the train on it departs, and a departure at the same time as another arrival frees the platform in time).",
        "input_format": "Line 1: n. Line 2: n arrival times. Line 3: n departure times.", "output_format": "Single integer: minimum platforms.",
        "constraints": "1 <= n <= 10^4",
        "reference_solution":
"""n = int(input())
arr = sorted(map(int, input().split()))
dep = sorted(map(int, input().split()))
i = j = 0
cur = best = 0
while i < n:
    if arr[i] <= dep[j]:
        cur += 1; i += 1
        best = max(best, cur)
    else:
        cur -= 1; j += 1
print(best)
""",
        "test_inputs": ["6\n900 940 950 1100 1500 1800\n910 1200 1120 1130 1900 2000", "3\n100 140 150\n110 200 220", "1\n900\n1000", "4\n100 200 300 400\n150 250 350 450", "3\n100 100 100\n200 200 200"],
    },
    # ------------------------------------------------------------------ GRAPHS (net-new, 2026-09)
    {
        "id": "graph-connected-components", "title": "Number of Connected Components", "topic": "graphs",
        "difficulty": "Medium",
        "statement": "Given an undirected graph with n nodes (0-indexed) and m edges, print the number of connected components.",
        "input_format": "Line 1: n m. Next m lines: 'u v'.", "output_format": "Single integer.",
        "constraints": "1 <= n <= 10^4, 0 <= m <= 10^4",
        "reference_solution":
"""n, m = map(int, input().split())
adj = [[] for _ in range(n)]
for _ in range(m):
    u, v = map(int, input().split())
    adj[u].append(v); adj[v].append(u)
seen = [False] * n
count = 0
for i in range(n):
    if not seen[i]:
        count += 1
        stack = [i]; seen[i] = True
        while stack:
            x = stack.pop()
            for y in adj[x]:
                if not seen[y]:
                    seen[y] = True; stack.append(y)
print(count)
""",
        "test_inputs": ["5 3\n0 1\n1 2\n3 4", "4 0", "1 0", "6 5\n0 1\n0 2\n2 3\n3 4\n4 5", "5 2\n0 1\n2 3"],
    },
    {
        "id": "graph-cycle-undirected", "title": "Detect Cycle in an Undirected Graph", "topic": "graphs",
        "difficulty": "Medium",
        "statement": "Given an undirected graph with n nodes (0-indexed) and m edges, print 'YES' if it contains a cycle, else 'NO'.",
        "input_format": "Line 1: n m. Next m lines: 'u v'.", "output_format": "YES or NO.",
        "constraints": "1 <= n <= 10^4, 0 <= m <= 10^4",
        "reference_solution":
"""n, m = map(int, input().split())
parent = list(range(n))
def find(x):
    while parent[x] != x:
        x = parent[x]
    return x
cycle = False
for _ in range(m):
    u, v = map(int, input().split())
    ru, rv = find(u), find(v)
    if ru == rv:
        cycle = True
    else:
        parent[ru] = rv
print('YES' if cycle else 'NO')
""",
        "buggy_solution":
"""n, m = map(int, input().split())
parent = list(range(n))
def find(x):
    while parent[x] != x:
        x = parent[x]
    return x
cycle = False
for _ in range(m):
    u, v = map(int, input().split())
    ru, rv = find(u), find(v)
    if ru != rv:
        cycle = True
    parent[ru] = rv
print('YES' if cycle else 'NO')
""",
        "test_inputs": ["4 3\n0 1\n1 2\n2 3", "4 4\n0 1\n1 2\n2 3\n3 0", "1 0", "3 3\n0 1\n1 2\n0 2", "5 4\n0 1\n1 2\n3 4\n1 3"],
    },
    {
        "id": "graph-cycle-directed", "title": "Detect Cycle in a Directed Graph", "topic": "graphs",
        "difficulty": "Medium",
        "statement": "Given a directed graph with n nodes (0-indexed) and m directed edges, print 'YES' if it contains a cycle, else 'NO'.",
        "input_format": "Line 1: n m. Next m lines: 'u v' meaning an edge from u to v.", "output_format": "YES or NO.",
        "constraints": "1 <= n <= 10^4, 0 <= m <= 10^4",
        "reference_solution":
"""from collections import deque
n, m = map(int, input().split())
adj = [[] for _ in range(n)]
indeg = [0] * n
for _ in range(m):
    u, v = map(int, input().split())
    adj[u].append(v); indeg[v] += 1
q = deque([i for i in range(n) if indeg[i] == 0])
processed = 0
while q:
    u = q.popleft(); processed += 1
    for v in adj[u]:
        indeg[v] -= 1
        if indeg[v] == 0:
            q.append(v)
print('YES' if processed < n else 'NO')
""",
        "test_inputs": ["3 3\n0 1\n1 2\n2 0", "4 3\n0 1\n1 2\n2 3", "1 0", "2 2\n0 1\n1 0", "5 4\n0 1\n0 2\n1 3\n2 4"],
    },
    {
        "id": "graph-course-schedule", "title": "Course Schedule (Can Finish All Courses)", "topic": "graphs",
        "difficulty": "Medium",
        "statement": "There are n courses labeled 0 to n-1. Each of m prerequisite pairs 'a b' means course a requires course b to be completed first. Print 'YES' if it is possible to finish all courses, else 'NO'.",
        "input_format": "Line 1: n. Line 2: m. Next m lines: 'a b'.", "output_format": "YES or NO.",
        "constraints": "1 <= n <= 10^4, 0 <= m <= 10^4",
        "reference_solution":
"""from collections import deque
n = int(input())
m = int(input())
adj = [[] for _ in range(n)]
indeg = [0] * n
for _ in range(m):
    a, b = map(int, input().split())
    adj[b].append(a); indeg[a] += 1
q = deque([i for i in range(n) if indeg[i] == 0])
processed = 0
while q:
    u = q.popleft(); processed += 1
    for v in adj[u]:
        indeg[v] -= 1
        if indeg[v] == 0:
            q.append(v)
print('YES' if processed == n else 'NO')
""",
        "test_inputs": ["2\n1\n1 0", "2\n2\n1 0\n0 1", "1\n0", "4\n3\n1 0\n2 0\n3 1", "3\n3\n1 0\n2 1\n0 2"],
    },
    {
        "id": "graph-topo-sort-lexo", "title": "Topological Sort (Lexicographically Smallest)", "topic": "graphs",
        "difficulty": "Medium",
        "statement": "Given a directed acyclic graph with n nodes (0-indexed) and m edges 'u v' (u must come before v), print a valid topological order. If multiple valid orders exist, print the lexicographically smallest one (at each step, choose the smallest-numbered node with no remaining unprocessed prerequisite).",
        "input_format": "Line 1: n m. Next m lines: 'u v'.", "output_format": "n space-separated node ids.",
        "constraints": "1 <= n <= 10^4, the graph is guaranteed acyclic",
        "reference_solution":
"""import heapq
n, m = map(int, input().split())
adj = [[] for _ in range(n)]
indeg = [0] * n
for _ in range(m):
    u, v = map(int, input().split())
    adj[u].append(v); indeg[v] += 1
heap = [i for i in range(n) if indeg[i] == 0]
heapq.heapify(heap)
order = []
while heap:
    u = heapq.heappop(heap)
    order.append(u)
    for v in adj[u]:
        indeg[v] -= 1
        if indeg[v] == 0:
            heapq.heappush(heap, v)
print(' '.join(map(str, order)))
""",
        "test_inputs": ["4 3\n0 1\n0 2\n1 3", "3 2\n0 1\n0 2", "1 0", "5 4\n4 0\n4 1\n0 2\n1 3", "6 0"],
    },
    {
        "id": "graph-bipartite-check", "title": "Is Graph Bipartite", "topic": "graphs",
        "difficulty": "Medium",
        "statement": "Given an undirected graph with n nodes (0-indexed) and m edges, print 'YES' if its nodes can be split into two groups such that every edge connects nodes from different groups, else 'NO'.",
        "input_format": "Line 1: n m. Next m lines: 'u v'.", "output_format": "YES or NO.",
        "constraints": "1 <= n <= 10^4, 0 <= m <= 10^4",
        "reference_solution":
"""from collections import deque
n, m = map(int, input().split())
adj = [[] for _ in range(n)]
for _ in range(m):
    u, v = map(int, input().split())
    adj[u].append(v); adj[v].append(u)
color = [-1] * n
ok = True
for i in range(n):
    if color[i] == -1:
        color[i] = 0
        q = deque([i])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if color[v] == -1:
                    color[v] = 1 - color[u]
                    q.append(v)
                elif color[v] == color[u]:
                    ok = False
print('YES' if ok else 'NO')
""",
        "test_inputs": ["4 4\n0 1\n1 2\n2 3\n3 0", "3 3\n0 1\n1 2\n2 0", "1 0", "4 2\n0 1\n2 3", "5 5\n0 1\n1 2\n2 3\n3 4\n4 0"],
    },
    {
        "id": "graph-bfs-shortest-path", "title": "Shortest Path in an Unweighted Graph", "topic": "graphs",
        "difficulty": "Medium",
        "statement": "Given an undirected, unweighted graph with n nodes (0-indexed) and m edges, and a source and destination node, print the minimum number of edges on a path from source to destination, or -1 if unreachable.",
        "input_format": "Line 1: n m. Next m lines: 'u v'. Last line: 'src dst'.", "output_format": "Single integer.",
        "constraints": "1 <= n <= 10^4, 0 <= m <= 10^4",
        "reference_solution":
"""from collections import deque
n, m = map(int, input().split())
adj = [[] for _ in range(n)]
for _ in range(m):
    u, v = map(int, input().split())
    adj[u].append(v); adj[v].append(u)
src, dst = map(int, input().split())
dist = [-1] * n
dist[src] = 0
q = deque([src])
while q:
    u = q.popleft()
    for v in adj[u]:
        if dist[v] == -1:
            dist[v] = dist[u] + 1
            q.append(v)
print(dist[dst])
""",
        "test_inputs": ["5 4\n0 1\n1 2\n2 3\n3 4\n0 4", "4 2\n0 1\n2 3\n0 3", "1 0\n0 0", "6 6\n0 1\n1 2\n2 3\n0 4\n4 5\n5 3\n0 3", "3 2\n0 1\n1 2\n2 0"],
    },
    {
        "id": "graph-dijkstra", "title": "Dijkstra's Shortest Path", "topic": "graphs",
        "difficulty": "Hard",
        "statement": "Given a directed graph with n nodes (0-indexed), m weighted edges (non-negative weights), and a source node, print the shortest distance from the source to every node in order (node 0 to node n-1), using -1 for unreachable nodes.",
        "input_format": "Line 1: n m. Next m lines: 'u v w'. Last line: source.", "output_format": "n space-separated distances.",
        "constraints": "1 <= n <= 10^4, 0 <= w <= 10^4",
        "reference_solution":
"""import heapq
n, m = map(int, input().split())
adj = [[] for _ in range(n)]
for _ in range(m):
    u, v, w = map(int, input().split())
    adj[u].append((v, w))
s = int(input())
dist = [float('inf')] * n
dist[s] = 0
pq = [(0, s)]
while pq:
    d, u = heapq.heappop(pq)
    if d > dist[u]:
        continue
    for v, w in adj[u]:
        nd = d + w
        if nd < dist[v]:
            dist[v] = nd
            heapq.heappush(pq, (nd, v))
print(' '.join(str(d) if d != float('inf') else '-1' for d in dist))
""",
        "test_inputs": ["5 6\n0 1 2\n0 2 4\n1 2 1\n1 3 7\n2 4 3\n3 4 1\n0", "3 1\n0 1 5\n0", "1 0\n0", "4 4\n0 1 1\n1 2 1\n2 3 1\n0 3 10\n0", "4 3\n1 2 1\n2 3 1\n0 1 1\n2"],
    },
    {
        "id": "graph-network-delay-time", "title": "Network Delay Time", "topic": "graphs",
        "difficulty": "Medium",
        "statement": "A signal starts at node k and travels through a directed network of n nodes (labeled 1 to n) along m weighted edges 'u v w' (time w for the signal to travel from u to v). Print the minimum time for the signal to reach every node, or -1 if some node is unreachable.",
        "input_format": "Line 1: n. Line 2: m. Next m lines: 'u v w'. Last line: k.", "output_format": "Single integer.",
        "constraints": "1 <= n <= 100",
        "reference_solution":
"""import heapq
n = int(input())
m = int(input())
adj = [[] for _ in range(n + 1)]
for _ in range(m):
    u, v, w = map(int, input().split())
    adj[u].append((v, w))
k = int(input())
dist = [float('inf')] * (n + 1)
dist[k] = 0
pq = [(0, k)]
while pq:
    d, u = heapq.heappop(pq)
    if d > dist[u]:
        continue
    for v, w in adj[u]:
        nd = d + w
        if nd < dist[v]:
            dist[v] = nd
            heapq.heappush(pq, (nd, v))
mx = max(dist[1:])
print(mx if mx != float('inf') else -1)
""",
        "test_inputs": ["4\n4\n2 1 1\n2 3 1\n3 4 1\n1 4 3\n2", "2\n1\n1 2 1\n2", "1\n0\n1", "3\n2\n1 2 1\n2 3 2\n1", "4\n3\n1 2 1\n1 3 2\n1 4 1\n1"],
    },
    {
        "id": "graph-rotten-oranges", "title": "Rotten Oranges (Minimum Time to Rot All)", "topic": "graphs",
        "difficulty": "Medium",
        "statement": "A grid contains 0 (empty), 1 (fresh orange), or 2 (rotten orange). Every minute, a rotten orange rots every 4-directionally adjacent fresh orange. Print the minimum number of minutes until no fresh orange remains, or -1 if some fresh orange can never be reached.",
        "input_format": "Line 1: rows cols. Next rows lines: cols space-separated 0/1/2 values.", "output_format": "Single integer.",
        "constraints": "1 <= rows, cols <= 300",
        "reference_solution":
"""from collections import deque
r, c = map(int, input().split())
g = [list(map(int, input().split())) for _ in range(r)]
q = deque()
fresh = 0
for i in range(r):
    for j in range(c):
        if g[i][j] == 2:
            q.append((i, j, 0))
        elif g[i][j] == 1:
            fresh += 1
mins = 0
while q:
    i, j, t = q.popleft()
    mins = max(mins, t)
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ni, nj = i + di, j + dj
        if 0 <= ni < r and 0 <= nj < c and g[ni][nj] == 1:
            g[ni][nj] = 2
            fresh -= 1
            q.append((ni, nj, t + 1))
print(mins if fresh == 0 else -1)
""",
        "test_inputs": ["3 3\n2 1 1\n1 1 0\n0 1 1", "3 3\n2 1 1\n0 1 1\n1 0 1", "1 1\n0", "2 2\n2 1\n1 1", "1 4\n1 2 1 1"],
    },
    {
        "id": "graph-mst-kruskal", "title": "Minimum Spanning Tree Weight (Kruskal)", "topic": "graphs",
        "difficulty": "Hard",
        "statement": "Given a connected, undirected, weighted graph with n nodes (0-indexed) and m edges, print the total weight of its minimum spanning tree.",
        "input_format": "Line 1: n m. Next m lines: 'u v w'.", "output_format": "Single integer.",
        "constraints": "1 <= n <= 10^4, the graph is guaranteed connected",
        "reference_solution":
"""n, m = map(int, input().split())
edges = []
for _ in range(m):
    u, v, w = map(int, input().split())
    edges.append((w, u, v))
edges.sort()
parent = list(range(n))
def find(x):
    while parent[x] != x:
        x = parent[x]
    return x
total = 0
count = 0
for w, u, v in edges:
    ru, rv = find(u), find(v)
    if ru != rv:
        parent[ru] = rv
        total += w
        count += 1
        if count == n - 1:
            break
print(total)
""",
        "test_inputs": ["4 5\n0 1 10\n0 2 6\n0 3 5\n1 3 15\n2 3 4", "1 0", "2 1\n0 1 7", "3 3\n0 1 1\n1 2 2\n0 2 2", "5 6\n0 1 2\n0 3 6\n1 2 3\n1 3 8\n1 4 5\n2 4 7"],
    },
    # ------------------------------------------------------------------ STRINGS (net-new, 2026-09)
    {
        "id": "string-valid-anagram", "title": "Valid Anagram", "topic": "strings",
        "difficulty": "Easy",
        "statement": "Given two strings, print 'YES' if the second is an anagram of the first (same characters, same multiplicities, any order), else 'NO'.",
        "input_format": "Line 1: string a. Line 2: string b.", "output_format": "YES or NO.",
        "constraints": "0 <= |a|, |b| <= 10^5",
        "reference_solution":
"""a = input()
b = input()
print('YES' if sorted(a) == sorted(b) else 'NO')
""",
        "buggy_solution":
"""a = input()
b = input()
print('YES' if set(a) == set(b) else 'NO')
""",
        "test_inputs": ["aabb\nab", "anagram\nnagaram", "rat\ncar", "\n\n", "aabbcc\nabcabc"],
    },
    {
        "id": "string-compression", "title": "String Compression (Run-Length Encoding)", "topic": "strings",
        "difficulty": "Medium",
        "statement": "Given a string, compress it by replacing every maximal run of the same consecutive character with that character followed by the run's length (even if the length is 1). Print the compressed string; print an empty line if the input is empty.",
        "input_format": "Single line string (may be empty).", "output_format": "Compressed string.",
        "constraints": "0 <= |s| <= 10^5",
        "reference_solution":
"""s = input()
if not s:
    print('')
else:
    out = []
    i = 0
    n = len(s)
    while i < n:
        j = i
        while j < n and s[j] == s[i]:
            j += 1
        out.append(s[i] + str(j - i))
        i = j
    print(''.join(out))
""",
        "test_inputs": ["aaabbc", "abc", "aaaa", "\n", "aabbbba"],
    },
    {
        "id": "string-longest-common-prefix", "title": "Longest Common Prefix", "topic": "strings",
        "difficulty": "Easy",
        "statement": "Given n strings, print the longest string that is a prefix of all of them. Print an empty line if there is no common prefix.",
        "input_format": "Line 1: n. Next n lines: one string each.", "output_format": "The longest common prefix (may be empty).",
        "constraints": "1 <= n <= 200",
        "reference_solution":
"""n = int(input())
words = [input() for _ in range(n)]
pre = words[0]
for w in words[1:]:
    i = 0
    while i < len(pre) and i < len(w) and pre[i] == w[i]:
        i += 1
    pre = pre[:i]
    if not pre:
        break
print(pre)
""",
        "test_inputs": ["3\nflower\nflow\nflight", "3\ndog\nracecar\ncar", "1\nsingle", "2\nab\nab", "2\nabc\nabd"],
    },
    {
        "id": "string-isomorphic", "title": "Isomorphic Strings", "topic": "strings",
        "difficulty": "Easy",
        "statement": "Given two strings of the same length, print 'YES' if the characters of the first can be consistently replaced (one-to-one, in both directions) to obtain the second, else 'NO'.",
        "input_format": "Line 1: string s. Line 2: string t.", "output_format": "YES or NO.",
        "constraints": "0 <= |s| == |t| <= 10^5",
        "reference_solution":
"""s = input()
t = input()
if len(s) != len(t):
    print('NO')
else:
    m1, m2 = {}, {}
    ok = True
    for a, b in zip(s, t):
        if a in m1 and m1[a] != b:
            ok = False; break
        if b in m2 and m2[b] != a:
            ok = False; break
        m1[a] = b; m2[b] = a
    print('YES' if ok else 'NO')
""",
        "test_inputs": ["egg\nadd", "foo\nbar", "paper\ntitle", "ab\naa", "\n\n"],
    },
    {
        "id": "string-word-pattern", "title": "Word Pattern", "topic": "strings",
        "difficulty": "Easy",
        "statement": "Given a pattern string and a sentence of space-separated words, print 'YES' if there is a one-to-one (bijective) mapping between each pattern character and the word at that position, else 'NO'.",
        "input_format": "Line 1: pattern. Line 2: space-separated words.", "output_format": "YES or NO.",
        "constraints": "1 <= |pattern| <= 300",
        "reference_solution":
"""pattern = input()
words = input().split()
if len(pattern) != len(words):
    print('NO')
else:
    m1, m2 = {}, {}
    ok = True
    for a, b in zip(pattern, words):
        if a in m1 and m1[a] != b:
            ok = False; break
        if b in m2 and m2[b] != a:
            ok = False; break
        m1[a] = b; m2[b] = a
    print('YES' if ok else 'NO')
""",
        "test_inputs": ["abba\ndog cat cat dog", "abba\ndog cat cat fish", "aaaa\ndog cat cat dog", "abba\ndog dog dog dog", "a\ndog"],
    },
    {
        "id": "string-roman-to-integer", "title": "Roman Numeral to Integer", "topic": "strings",
        "difficulty": "Easy",
        "statement": "Given a valid Roman numeral string (characters from I, V, X, L, C, D, M), print its integer value.",
        "input_format": "Single line Roman numeral.", "output_format": "Single integer.",
        "constraints": "1 <= value <= 3999",
        "reference_solution":
"""s = input()
vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
total = 0
prev = 0
for ch in reversed(s):
    v = vals[ch]
    if v < prev:
        total -= v
    else:
        total += v
        prev = v
print(total)
""",
        "test_inputs": ["III", "LVIII", "MCMXCIV", "IV", "IX"],
    },
    {
        "id": "string-integer-to-roman", "title": "Integer to Roman Numeral", "topic": "strings",
        "difficulty": "Medium",
        "statement": "Given an integer, print its standard Roman numeral representation.",
        "input_format": "Single integer.", "output_format": "Roman numeral string.",
        "constraints": "1 <= n <= 3999",
        "reference_solution":
"""n = int(input())
vals = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'),
        (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
out = []
for v, sym in vals:
    while n >= v:
        out.append(sym)
        n -= v
print(''.join(out))
""",
        "test_inputs": ["3", "58", "1994", "4", "9"],
    },
    {
        "id": "string-count-and-say", "title": "Count and Say", "topic": "strings",
        "difficulty": "Medium",
        "statement": "The count-and-say sequence starts with '1'. Each subsequent term is generated by reading the previous term and, for every maximal run of the same digit, writing the run's length followed by that digit. Given n, print the n-th term (1-indexed).",
        "input_format": "Single integer n.", "output_format": "The n-th term of the sequence.",
        "constraints": "1 <= n <= 30",
        "reference_solution":
"""n = int(input())
s = '1'
for _ in range(n - 1):
    out = []
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out.append(str(j - i) + s[i])
        i = j
    s = ''.join(out)
print(s)
""",
        "test_inputs": ["1", "2", "3", "4", "5"],
    },
    {
        "id": "string-multiply-strings", "title": "Multiply Strings", "topic": "strings",
        "difficulty": "Medium",
        "statement": "Given two non-negative integers represented as decimal digit strings, print their product as a decimal string (no leading zeros, unless the product is 0).",
        "input_format": "Line 1: string a. Line 2: string b.", "output_format": "Product as a decimal string.",
        "constraints": "1 <= |a|, |b| <= 200, digits only",
        "reference_solution":
"""a = input()
b = input()
if a == '0' or b == '0':
    print(0)
else:
    n, m = len(a), len(b)
    res = [0] * (n + m)
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            mul = (ord(a[i]) - 48) * (ord(b[j]) - 48)
            p1, p2 = i + j, i + j + 1
            total = mul + res[p2]
            res[p2] = total % 10
            res[p1] += total // 10
    s = ''.join(map(str, res)).lstrip('0')
    print(s if s else '0')
""",
        "test_inputs": ["2\n3", "123\n456", "999\n999", "0\n123", "1\n1"],
    },
    {
        "id": "string-zigzag-conversion", "title": "Zigzag Conversion", "topic": "strings",
        "difficulty": "Medium",
        "statement": "Given a string and a number of rows, write the string in a zigzag pattern across that many rows (down each column, then diagonally up to the top row, repeating), then print the string formed by reading off each row left to right, top row first.",
        "input_format": "Line 1: string s. Line 2: number of rows.", "output_format": "The zigzag-read string.",
        "constraints": "1 <= |s| <= 1000, 1 <= rows <= 1000",
        "reference_solution":
"""s = input()
rows = int(input())
if rows == 1 or rows >= len(s):
    print(s)
else:
    buckets = [''] * rows
    r, d = 0, 1
    for ch in s:
        buckets[r] += ch
        if r == 0:
            d = 1
        elif r == rows - 1:
            d = -1
        r += d
    print(''.join(buckets))
""",
        "test_inputs": ["PAYPALISHIRING\n3", "PAYPALISHIRING\n4", "A\n1", "AB\n1", "ABCDE\n2"],
    },
    # ------------------------------------------------------------------ 2D_DP (net-new, 2026-09)
    {
        "id": "dp-longest-common-subsequence", "title": "Longest Common Subsequence", "topic": "2d_dp",
        "difficulty": "Medium",
        "statement": "Given two strings, print the length of their longest common subsequence (characters in relative order, not necessarily contiguous).",
        "input_format": "Line 1: string a. Line 2: string b.", "output_format": "Single integer.",
        "constraints": "0 <= |a|, |b| <= 1000",
        "reference_solution":
"""a = input()
b = input()
n, m = len(a), len(b)
dp = [[0] * (m + 1) for _ in range(n + 1)]
for i in range(1, n + 1):
    for j in range(1, m + 1):
        if a[i - 1] == b[j - 1]:
            dp[i][j] = dp[i - 1][j - 1] + 1
        else:
            dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
print(dp[n][m])
""",
        "test_inputs": ["abcde\nace", "abc\nabc", "abc\ndef", "\nabc", "AGGTAB\nGXTXAYB"],
    },
    {
        "id": "dp-longest-common-substring", "title": "Longest Common Substring", "topic": "2d_dp",
        "difficulty": "Medium",
        "statement": "Given two strings, print the length of their longest common substring (contiguous in both strings).",
        "input_format": "Line 1: string a. Line 2: string b.", "output_format": "Single integer.",
        "constraints": "0 <= |a|, |b| <= 1000",
        "reference_solution":
"""a = input()
b = input()
n, m = len(a), len(b)
dp = [[0] * (m + 1) for _ in range(n + 1)]
best = 0
for i in range(1, n + 1):
    for j in range(1, m + 1):
        if a[i - 1] == b[j - 1]:
            dp[i][j] = dp[i - 1][j - 1] + 1
            best = max(best, dp[i][j])
print(best)
""",
        "test_inputs": ["abcdxyz\nxyzabcd", "zxabcdezy\nyzabcdezy", "abc\nabc", "abc\ndef", "\nabc"],
    },
    {
        "id": "dp-01-knapsack", "title": "0/1 Knapsack", "topic": "2d_dp",
        "difficulty": "Medium",
        "statement": "Given n items each with a weight and a value, and a knapsack capacity, choose a subset of items (each used at most once) whose total weight does not exceed the capacity, maximizing total value. Print the maximum value.",
        "input_format": "Line 1: n. Line 2: n weights. Line 3: n values. Line 4: capacity.", "output_format": "Single integer: maximum value.",
        "constraints": "1 <= n <= 200, 0 <= capacity <= 10^4",
        "reference_solution":
"""n = int(input())
wt = list(map(int, input().split()))
val = list(map(int, input().split()))
cap = int(input())
dp = [[0] * (cap + 1) for _ in range(n + 1)]
for i in range(1, n + 1):
    for c in range(cap + 1):
        dp[i][c] = dp[i - 1][c]
        if wt[i - 1] <= c:
            dp[i][c] = max(dp[i][c], dp[i - 1][c - wt[i - 1]] + val[i - 1])
print(dp[n][cap])
""",
        "test_inputs": ["3\n10 20 30\n60 100 120\n50", "1\n5\n10\n4", "1\n5\n10\n5", "2\n1 1\n5 5\n1", "4\n1 2 3 2\n10 15 40 25\n5"],
    },
    {
        "id": "dp-minimum-path-sum", "title": "Minimum Path Sum", "topic": "2d_dp",
        "difficulty": "Medium",
        "statement": "Given a grid of non-negative integers, find a path from the top-left cell to the bottom-right cell, moving only right or down, that minimizes the sum of the values along the path. Print that minimum sum.",
        "input_format": "Line 1: rows cols. Next rows lines: cols space-separated integers.", "output_format": "Single integer.",
        "constraints": "1 <= rows, cols <= 200",
        "reference_solution":
"""rows, cols = map(int, input().split())
g = [list(map(int, input().split())) for _ in range(rows)]
dp = [[0] * cols for _ in range(rows)]
for i in range(rows):
    for j in range(cols):
        if i == 0 and j == 0:
            dp[i][j] = g[i][j]
        elif i == 0:
            dp[i][j] = dp[i][j - 1] + g[i][j]
        elif j == 0:
            dp[i][j] = dp[i - 1][j] + g[i][j]
        else:
            dp[i][j] = min(dp[i - 1][j], dp[i][j - 1]) + g[i][j]
print(dp[rows - 1][cols - 1])
""",
        "test_inputs": ["3 3\n1 3 1\n1 5 1\n4 2 1", "1 1\n5", "2 2\n1 2\n1 1", "1 4\n1 2 3 4", "4 1\n1\n2\n3\n4"],
    },
    {
        "id": "dp-longest-increasing-subsequence", "title": "Longest Increasing Subsequence", "topic": "2d_dp",
        "difficulty": "Medium",
        "statement": "Given an array of integers, print the length of the longest strictly increasing subsequence.",
        "input_format": "Line 1: n. Line 2: n integers.", "output_format": "Single integer.",
        "constraints": "0 <= n <= 2500",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split())) if n else []
dp = [1] * n
for i in range(n):
    for j in range(i):
        if a[j] < a[i]:
            dp[i] = max(dp[i], dp[j] + 1)
print(max(dp) if n else 0)
""",
        "test_inputs": ["8\n10 9 2 5 3 7 101 18", "1\n5", "5\n5 4 3 2 1", "6\n1 2 3 4 5 6", "4\n2 2 2 2"],
    },
    {
        "id": "dp-partition-equal-subset-sum", "title": "Partition Equal Subset Sum", "topic": "2d_dp",
        "difficulty": "Medium",
        "statement": "Given an array of positive integers, print 'YES' if it can be partitioned into two subsets with equal sums, else 'NO'.",
        "input_format": "Line 1: n. Line 2: n integers.", "output_format": "YES or NO.",
        "constraints": "1 <= n <= 200",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
total = sum(a)
if total % 2 != 0:
    print('NO')
else:
    target = total // 2
    dp = [False] * (target + 1)
    dp[0] = True
    for x in a:
        for c in range(target, x - 1, -1):
            if dp[c - x]:
                dp[c] = True
    print('YES' if dp[target] else 'NO')
""",
        "test_inputs": ["4\n1 5 11 5", "3\n1 2 3", "3\n1 2 5", "1\n1", "4\n1 2 3 4"],
    },
    {
        "id": "dp-word-break", "title": "Word Break", "topic": "2d_dp",
        "difficulty": "Medium",
        "statement": "Given a string and a dictionary of words, print 'YES' if the string can be segmented into a sequence of one or more dictionary words (words may be reused any number of times), else 'NO'.",
        "input_format": "Line 1: string s. Line 2: n (dictionary size). Line 3: n space-separated words (blank line if n=0).", "output_format": "YES or NO.",
        "constraints": "0 <= |s| <= 300",
        "reference_solution":
"""s = input()
n = int(input())
words = set(input().split())
m = len(s)
dp = [False] * (m + 1)
dp[0] = True
for i in range(1, m + 1):
    for j in range(i):
        if dp[j] and s[j:i] in words:
            dp[i] = True
            break
print('YES' if dp[m] else 'NO')
""",
        "test_inputs": ["leetcode\n2\nleet code", "applepenapple\n3\napple pen ok", "catsandog\n5\ncats dog sand and cat", "a\n1\nb", "\n0\n\n"],
    },
    {
        "id": "dp-interleaving-string", "title": "Interleaving String", "topic": "2d_dp",
        "difficulty": "Hard",
        "statement": "Given three strings s1, s2, s3, print 'YES' if s3 can be formed by interleaving the characters of s1 and s2 while preserving each string's own relative character order, else 'NO'.",
        "input_format": "Line 1: s1. Line 2: s2. Line 3: s3.", "output_format": "YES or NO.",
        "constraints": "0 <= |s1|, |s2| <= 200",
        "reference_solution":
"""s1 = input()
s2 = input()
s3 = input()
n, m = len(s1), len(s2)
if n + m != len(s3):
    print('NO')
else:
    dp = [[False] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = True
    for i in range(n + 1):
        for j in range(m + 1):
            if i > 0 and dp[i - 1][j] and s1[i - 1] == s3[i + j - 1]:
                dp[i][j] = True
            if j > 0 and dp[i][j - 1] and s2[j - 1] == s3[i + j - 1]:
                dp[i][j] = True
    print('YES' if dp[n][m] else 'NO')
""",
        "test_inputs": ["aabcc\ndbbca\naadbbcbcac", "aabcc\ndbbca\naadbbbaccc", "\n\n\n", "a\nb\nba", "a\nb\ncd"],
    },
    {
        "id": "dp-maximal-square", "title": "Maximal Square", "topic": "2d_dp",
        "difficulty": "Medium",
        "statement": "Given a binary matrix of 0s and 1s, find the largest square containing only 1s and print its area (side length squared).",
        "input_format": "Line 1: rows cols. Next rows lines: cols space-separated 0/1 values.", "output_format": "Single integer.",
        "constraints": "1 <= rows, cols <= 300",
        "reference_solution":
"""rows, cols = map(int, input().split())
g = [list(map(int, input().split())) for _ in range(rows)]
dp = [[0] * cols for _ in range(rows)]
best = 0
for i in range(rows):
    for j in range(cols):
        if g[i][j] == 1:
            if i == 0 or j == 0:
                dp[i][j] = 1
            else:
                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1
            best = max(best, dp[i][j])
print(best * best)
""",
        "test_inputs": ["4 5\n1 0 1 0 0\n1 0 1 1 1\n1 1 1 1 1\n1 0 0 1 0", "1 1\n0", "1 1\n1", "2 2\n1 1\n1 1", "3 3\n0 1 1\n1 1 1\n0 1 1"],
    },
    # ------------------------------------------------------------------ ADVANCED_DSA (net-new, 2026-09)
    {
        "id": "adv-kth-largest-array", "title": "Kth Largest Element in an Array", "topic": "advanced_dsa",
        "difficulty": "Medium",
        "statement": "Given an array of integers and an integer k, print the k-th largest element (k=1 is the largest).",
        "input_format": "Line 1: n. Line 2: n integers. Line 3: k.", "output_format": "Single integer.",
        "constraints": "1 <= k <= n <= 10^5",
        "reference_solution":
"""import heapq
n = int(input())
a = list(map(int, input().split()))
k = int(input())
print(heapq.nlargest(k, a)[-1])
""",
        "test_inputs": ["6\n3 2 1 5 6 4\n2", "9\n3 2 3 1 2 4 5 5 6\n4", "1\n1\n1", "5\n5 4 3 2 1\n5", "4\n7 7 7 7\n2"],
    },
    {
        "id": "adv-top-k-frequent", "title": "Top K Frequent Elements", "topic": "advanced_dsa",
        "difficulty": "Medium",
        "statement": "Given an array of integers and an integer k, print the k most frequent elements, most frequent first (break ties between equally frequent elements by smaller value first).",
        "input_format": "Line 1: n. Line 2: n integers. Line 3: k.", "output_format": "k space-separated integers.",
        "constraints": "1 <= k <= number of distinct elements <= 10^5",
        "reference_solution":
"""from collections import Counter
n = int(input())
a = list(map(int, input().split()))
k = int(input())
cnt = Counter(a)
items = sorted(cnt.items(), key=lambda x: (-x[1], x[0]))
print(' '.join(str(v) for v, c in items[:k]))
""",
        "test_inputs": ["6\n1 1 1 2 2 3\n2", "1\n1\n1", "5\n4 4 4 6 6\n1", "6\n1 2 2 3 3 3\n3", "4\n5 5 6 6\n2"],
    },
    {
        "id": "adv-redundant-connection", "title": "Redundant Connection", "topic": "advanced_dsa",
        "difficulty": "Medium",
        "statement": "A tree with n nodes (labeled 1 to n) had one extra edge added, creating exactly one cycle. Given the n edges in the order they were added, use union-find to find and print the edge that can be removed to make it a tree again (if multiple edges could be removed, print the one that appears last in the input).",
        "input_format": "Line 1: n. Next n lines: 'u v'.", "output_format": "'u v' of the redundant edge.",
        "constraints": "3 <= n <= 1000",
        "reference_solution":
"""n = int(input())
parent = list(range(n + 1))
def find(x):
    while parent[x] != x:
        x = parent[x]
    return x
ans = None
for _ in range(n):
    u, v = map(int, input().split())
    ru, rv = find(u), find(v)
    if ru == rv:
        ans = (u, v)
    else:
        parent[ru] = rv
print(ans[0], ans[1])
""",
        "test_inputs": ["3\n1 2\n1 3\n2 3", "4\n1 2\n2 3\n3 4\n1 4", "2\n1 2\n1 2", "5\n1 2\n2 3\n3 4\n4 5\n5 1", "3\n1 2\n2 3\n1 3"],
    },
    {
        "id": "adv-implement-trie", "title": "Implement a Trie (Prefix Tree)", "topic": "advanced_dsa",
        "difficulty": "Medium",
        "statement": "Implement a trie supporting three operations: 'INSERT word' (add a word), 'SEARCH word' (print 'YES' if the exact word was inserted, else 'NO'), and 'PREFIX word' (print 'YES' if any inserted word starts with this prefix, else 'NO'). Process n operations in order; INSERT produces no output.",
        "input_format": "Line 1: n. Next n lines: an operation each.", "output_format": "One line of YES/NO per SEARCH or PREFIX operation, in order.",
        "constraints": "1 <= n <= 10^4",
        "reference_solution":
"""n = int(input())
root = {}
END = '$'
for _ in range(n):
    parts = input().split()
    op, word = parts[0], parts[1]
    if op == 'INSERT':
        node = root
        for ch in word:
            node = node.setdefault(ch, {})
        node[END] = True
    elif op == 'SEARCH':
        node = root
        found = True
        for ch in word:
            if ch not in node:
                found = False; break
            node = node[ch]
        print('YES' if found and END in node else 'NO')
    elif op == 'PREFIX':
        node = root
        found = True
        for ch in word:
            if ch not in node:
                found = False; break
            node = node[ch]
        print('YES' if found else 'NO')
""",
        "test_inputs": ["5\nINSERT apple\nSEARCH apple\nSEARCH app\nPREFIX app\nINSERT app", "3\nINSERT cat\nSEARCH cat\nSEARCH ca", "4\nINSERT a\nPREFIX a\nSEARCH a\nSEARCH b", "1\nINSERT x", "6\nINSERT bat\nINSERT ball\nPREFIX ba\nSEARCH bat\nSEARCH bal\nSEARCH ball"],
    },
    {
        "id": "adv-lru-cache", "title": "LRU Cache", "topic": "advanced_dsa",
        "difficulty": "Hard",
        "statement": "Implement a Least Recently Used (LRU) cache with a fixed capacity, supporting 'PUT key value' (insert or update, evicting the least recently used entry if over capacity) and 'GET key' (print the value, or -1 if not present; a successful GET counts as a use). Process n operations in order; PUT produces no output.",
        "input_format": "Line 1: capacity. Line 2: n (number of operations). Next n lines: an operation each.", "output_format": "One line per GET operation.",
        "constraints": "1 <= capacity <= 10^4, 1 <= n <= 10^4",
        "reference_solution":
"""from collections import OrderedDict
cap = int(input())
n = int(input())
cache = OrderedDict()
for _ in range(n):
    parts = input().split()
    if parts[0] == 'PUT':
        k, v = int(parts[1]), int(parts[2])
        if k in cache:
            del cache[k]
        cache[k] = v
        if len(cache) > cap:
            cache.popitem(last=False)
    else:
        k = int(parts[1])
        if k in cache:
            print(cache[k])
            cache.move_to_end(k)
        else:
            print(-1)
""",
        "test_inputs": ["2\n9\nPUT 1 1\nPUT 2 2\nGET 1\nPUT 3 3\nGET 2\nPUT 4 4\nGET 1\nGET 3\nGET 4", "1\n4\nPUT 1 1\nGET 1\nPUT 2 2\nGET 1", "2\n2\nGET 1\nPUT 1 1", "3\n5\nPUT 1 1\nPUT 2 2\nPUT 3 3\nGET 1\nGET 2", "1\n3\nPUT 1 10\nPUT 1 20\nGET 1"],
    },
    {
        "id": "adv-min-stack", "title": "Min Stack", "topic": "advanced_dsa",
        "difficulty": "Medium",
        "statement": "Implement a stack supporting 'PUSH x', 'POP' (remove the top), 'TOP' (print the top value), and 'GETMIN' (print the current minimum value in the stack), each in O(1). Process n operations in order; PUSH and POP produce no output.",
        "input_format": "Line 1: n. Next n lines: an operation each.", "output_format": "One line per TOP or GETMIN operation.",
        "constraints": "1 <= n <= 10^4",
        "reference_solution":
"""n = int(input())
stack = []
minstack = []
for _ in range(n):
    parts = input().split()
    op = parts[0]
    if op == 'PUSH':
        v = int(parts[1])
        stack.append(v)
        if not minstack or v <= minstack[-1]:
            minstack.append(v)
        else:
            minstack.append(minstack[-1])
    elif op == 'POP':
        stack.pop(); minstack.pop()
    elif op == 'TOP':
        print(stack[-1])
    elif op == 'GETMIN':
        print(minstack[-1])
""",
        "test_inputs": ["7\nPUSH -2\nPUSH 0\nPUSH -3\nGETMIN\nPOP\nTOP\nGETMIN", "3\nPUSH 5\nTOP\nGETMIN", "5\nPUSH 1\nPUSH 2\nPUSH 1\nGETMIN\nTOP", "4\nPUSH 3\nPUSH 3\nPOP\nGETMIN", "6\nPUSH 4\nPUSH 2\nPUSH 6\nPOP\nGETMIN\nTOP"],
    },
    {
        "id": "adv-median-data-stream", "title": "Find Median from Data Stream", "topic": "advanced_dsa",
        "difficulty": "Hard",
        "statement": "Numbers arrive one at a time in a stream. After each new number is added, print the median of all numbers seen so far (for an even count, the average of the two middle values).",
        "input_format": "Line 1: n. Next n lines: one integer each.", "output_format": "One line per number added: the current median.",
        "constraints": "1 <= n <= 10^4",
        "reference_solution":
"""import heapq
n = int(input())
lo = []
hi = []
for _ in range(n):
    x = int(input())
    heapq.heappush(lo, -x)
    heapq.heappush(hi, -heapq.heappop(lo))
    if len(hi) > len(lo):
        heapq.heappush(lo, -heapq.heappop(hi))
    if len(lo) > len(hi):
        print(-lo[0])
    else:
        print((-lo[0] + hi[0]) / 2)
""",
        "test_inputs": ["4\n5\n15\n1\n3", "1\n7", "2\n1\n2", "5\n1\n2\n3\n4\n5", "3\n10\n10\n10"],
    },
    {
        "id": "adv-kth-largest-stream", "title": "Kth Largest Element in a Stream", "topic": "advanced_dsa",
        "difficulty": "Medium",
        "statement": "Numbers arrive one at a time in a stream. After each new number is added, print the k-th largest value among all numbers seen so far, or 'NA' if fewer than k numbers have arrived yet.",
        "input_format": "Line 1: n. Line 2: k. Next n lines: one integer each.", "output_format": "One line per number added.",
        "constraints": "1 <= k <= n <= 10^4",
        "reference_solution":
"""import heapq
n = int(input())
k = int(input())
heap = []
for _ in range(n):
    x = int(input())
    heapq.heappush(heap, x)
    if len(heap) > k:
        heapq.heappop(heap)
    if len(heap) < k:
        print('NA')
    else:
        print(heap[0])
""",
        "test_inputs": ["4\n3\n4\n5\n8\n2", "3\n1\n1\n2\n3", "5\n2\n10\n20\n5\n30\n1", "1\n1\n9", "3\n3\n1\n2\n3"],
    },
    {
        "id": "adv-smallest-string-swaps", "title": "Smallest String With Swaps", "topic": "advanced_dsa",
        "difficulty": "Medium",
        "statement": "Given a string and a list of index pairs, where each pair marks two positions whose characters may be swapped any number of times (swaps compose transitively through shared indices), print the lexicographically smallest string reachable via any sequence of allowed swaps.",
        "input_format": "Line 1: string s. Line 2: m (number of pairs). Next m lines: 'i j'.", "output_format": "The resulting string.",
        "constraints": "1 <= |s| <= 300",
        "reference_solution":
"""s = input()
n = len(s)
m = int(input())
parent = list(range(n))
def find(x):
    while parent[x] != x:
        x = parent[x]
    return x
for _ in range(m):
    i, j = map(int, input().split())
    ri, rj = find(i), find(j)
    if ri != rj:
        parent[ri] = rj
groups = {}
for i in range(n):
    r = find(i)
    groups.setdefault(r, []).append(i)
res = list(s)
for idxs in groups.values():
    chars = sorted(res[i] for i in idxs)
    for idx, ch in zip(sorted(idxs), chars):
        res[idx] = ch
print(''.join(res))
""",
        "test_inputs": ["dcab\n2\n0 3\n1 2", "dcab\n3\n0 3\n1 2\n0 2", "a\n0", "cba\n2\n0 1\n1 2", "abc\n0"],
    },
    # ------------------------------------------------------------------ TWO_POINTER_SLIDING_WINDOW (net-new, 2026-09)
    {
        "id": "tp-minimum-window-substring", "title": "Minimum Window Substring", "topic": "two_pointer_sliding_window",
        "difficulty": "Hard",
        "statement": "Given strings s and t, find the shortest contiguous substring of s that contains every character of t (matching t's character counts, i.e. multiplicities). Print that substring, or an empty line if no such window exists.",
        "input_format": "Line 1: string s. Line 2: string t.", "output_format": "The shortest window substring (may be empty).",
        "constraints": "1 <= |s|, |t| <= 5000",
        "reference_solution":
"""from collections import Counter
s = input()
t = input()
need = Counter(t)
missing = len(t)
left = 0
best = (float('inf'), 0, 0)
for right, ch in enumerate(s, 1):
    if need[ch] > 0:
        missing -= 1
    need[ch] -= 1
    while missing == 0:
        if right - left < best[0]:
            best = (right - left, left, right)
        need[s[left]] += 1
        if need[s[left]] > 0:
            missing += 1
        left += 1
print(s[best[1]:best[2]] if best[0] != float('inf') else '')
""",
        "test_inputs": ["ADOBECODEBANC\nABC", "a\na", "a\naa", "aa\naa", "abc\nb"],
    },
    {
        "id": "tp-sliding-window-maximum", "title": "Sliding Window Maximum", "topic": "two_pointer_sliding_window",
        "difficulty": "Hard",
        "statement": "Given an array and a window size k, print the maximum value of every contiguous window of size k as it slides from left to right, space-separated.",
        "input_format": "Line 1: n. Line 2: n integers. Line 3: k.", "output_format": "Space-separated maximums, one per window.",
        "constraints": "1 <= k <= n <= 10^5",
        "reference_solution":
"""from collections import deque
n = int(input())
a = list(map(int, input().split()))
k = int(input())
dq = deque()
out = []
for i, x in enumerate(a):
    while dq and a[dq[-1]] <= x:
        dq.pop()
    dq.append(i)
    if dq[0] <= i - k:
        dq.popleft()
    if i >= k - 1:
        out.append(a[dq[0]])
print(' '.join(map(str, out)))
""",
        "test_inputs": ["8\n1 3 -1 -3 5 3 6 7\n3", "1\n1\n1", "5\n1 2 3 4 5\n2", "4\n9 11 -4 -2\n2", "6\n7 2 4 3 5 6\n3"],
    },
    {
        "id": "tp-3sum", "title": "3Sum (Triplets Summing to Zero)", "topic": "two_pointer_sliding_window",
        "difficulty": "Medium",
        "statement": "Given n integers, find every unique triplet of values that sums to zero (no duplicate triplets, even if the same values appear at different positions). Print each triplet's three values in non-decreasing order on its own line, sorted by their first, then second, then third value; print an empty line if none exist.",
        "input_format": "Line 1: n. Line 2: n integers.", "output_format": "One line per triplet (or one empty line if none).",
        "constraints": "3 <= n <= 3000",
        "reference_solution":
"""n = int(input())
a = sorted(map(int, input().split()))
res = []
for i in range(n):
    if i > 0 and a[i] == a[i - 1]:
        continue
    l, r = i + 1, n - 1
    while l < r:
        s = a[i] + a[l] + a[r]
        if s < 0:
            l += 1
        elif s > 0:
            r -= 1
        else:
            res.append((a[i], a[l], a[r]))
            l += 1; r -= 1
            while l < r and a[l] == a[l - 1]:
                l += 1
            while l < r and a[r] == a[r + 1]:
                r -= 1
if res:
    for t in res:
        print(t[0], t[1], t[2])
else:
    print('')
""",
        "test_inputs": ["6\n-1 0 1 2 -1 -4", "3\n0 0 0", "3\n0 1 1", "4\n-2 0 1 1", "5\n3 -2 1 0 -1"],
    },
    {
        "id": "tp-3sum-closest", "title": "3Sum Closest", "topic": "two_pointer_sliding_window",
        "difficulty": "Medium",
        "statement": "Given n integers and a target integer, find the sum of three of the integers that is closest to the target (if there is a tie, either closest sum is acceptable, but the two-pointer scan below resolves ties deterministically). Print that sum.",
        "input_format": "Line 1: n. Line 2: n integers. Line 3: target.", "output_format": "Single integer.",
        "constraints": "3 <= n <= 500",
        "reference_solution":
"""n = int(input())
a = sorted(map(int, input().split()))
target = int(input())
best = a[0] + a[1] + a[2]
for i in range(n):
    l, r = i + 1, n - 1
    while l < r:
        s = a[i] + a[l] + a[r]
        if abs(s - target) < abs(best - target):
            best = s
        if s < target:
            l += 1
        elif s > target:
            r -= 1
        else:
            l += 1; r -= 1
print(best)
""",
        "test_inputs": ["4\n-1 2 1 -4\n1", "3\n0 0 0\n1", "3\n1 1 1\n0", "5\n1 1 1 0 -100\n-1", "6\n-3 -2 -1 0 0 1\n0"],
    },
    {
        "id": "tp-remove-duplicates-sorted", "title": "Remove Duplicates from Sorted Array", "topic": "two_pointer_sliding_window",
        "difficulty": "Easy",
        "statement": "Given a sorted array, remove duplicates in place so each distinct value appears once, keeping relative order. Print the resulting length, then the deduplicated values (space-separated) on the next line; print an empty second line if the array was empty.",
        "input_format": "Line 1: n. Line 2: n integers (sorted, non-decreasing).", "output_format": "Line 1: new length. Line 2: deduplicated values.",
        "constraints": "0 <= n <= 3*10^4",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
if n == 0:
    print(0)
    print('')
else:
    k = 1
    for i in range(1, n):
        if a[i] != a[k - 1]:
            a[k] = a[i]
            k += 1
    print(k)
    print(' '.join(map(str, a[:k])))
""",
        "test_inputs": ["5\n1 1 2 2 3", "8\n0 0 1 1 1 2 2 3", "1\n5", "3\n1 1 1", "0\n\n"],
    },
    {
        "id": "tp-sort-colors", "title": "Sort Colors (Dutch National Flag)", "topic": "two_pointer_sliding_window",
        "difficulty": "Medium",
        "statement": "Given an array containing only 0s, 1s, and 2s, sort it in place in a single pass using three pointers, so all 0s come first, then all 1s, then all 2s. Print the sorted array.",
        "input_format": "Line 1: n. Line 2: n values (each 0, 1, or 2).", "output_format": "n space-separated values.",
        "constraints": "1 <= n <= 300",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
low, mid, high = 0, 0, n - 1
while mid <= high:
    if a[mid] == 0:
        a[low], a[mid] = a[mid], a[low]
        low += 1; mid += 1
    elif a[mid] == 1:
        mid += 1
    else:
        a[mid], a[high] = a[high], a[mid]
        high -= 1
print(' '.join(map(str, a)))
""",
        "test_inputs": ["6\n2 0 2 1 1 0", "1\n0", "3\n2 2 2", "5\n1 0 1 2 0", "4\n0 1 2 0"],
    },
    {
        "id": "tp-subarray-product-less-than-k", "title": "Subarray Product Less Than K", "topic": "two_pointer_sliding_window",
        "difficulty": "Medium",
        "statement": "Given an array of positive integers and an integer k, count the number of contiguous subarrays whose product is strictly less than k.",
        "input_format": "Line 1: n. Line 2: n positive integers. Line 3: k.", "output_format": "Single integer.",
        "constraints": "1 <= n <= 3*10^4",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
k = int(input())
if k <= 1:
    print(0)
else:
    left = 0
    prod = 1
    count = 0
    for right in range(n):
        prod *= a[right]
        while prod >= k:
            prod //= a[left]
            left += 1
        count += right - left + 1
    print(count)
""",
        "test_inputs": ["4\n10 5 2 6\n100", "1\n5\n1", "1\n1\n2", "3\n1 1 1\n2", "5\n1 2 3 4 5\n1"],
    },
    {
        "id": "tp-longest-substring-k-distinct", "title": "Longest Substring with At Most K Distinct Characters", "topic": "two_pointer_sliding_window",
        "difficulty": "Medium",
        "statement": "Given a string and an integer k, print the length of the longest substring that contains at most k distinct characters.",
        "input_format": "Line 1: string s. Line 2: k.", "output_format": "Single integer.",
        "constraints": "0 <= |s| <= 5*10^4, 0 <= k <= 26",
        "reference_solution":
"""from collections import defaultdict
s = input()
k = int(input())
count = defaultdict(int)
left = 0
best = 0
for right, ch in enumerate(s):
    count[ch] += 1
    while len(count) > k:
        lc = s[left]
        count[lc] -= 1
        if count[lc] == 0:
            del count[lc]
        left += 1
    best = max(best, right - left + 1)
print(best)
""",
        "test_inputs": ["eceba\n2", "aa\n1", "a\n0", "aabbcc\n1", "abcabcabc\n3"],
    },
    # ------------------------------------------------------------------ ARRAYS (net-new, 2026-09, gap top-up)
    {
        "id": "arr-next-permutation", "title": "Next Permutation", "topic": "arrays",
        "difficulty": "Medium",
        "statement": "Given an array of integers, rearrange it in place into the next lexicographically greater permutation of its values. If no greater permutation exists (it is already the highest), rearrange it into the lowest possible order instead. Print the resulting array.",
        "input_format": "Line 1: n. Line 2: n integers.", "output_format": "n space-separated integers.",
        "constraints": "1 <= n <= 10^5",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
i = n - 2
while i >= 0 and a[i] >= a[i + 1]:
    i -= 1
if i >= 0:
    j = n - 1
    while a[j] <= a[i]:
        j -= 1
    a[i], a[j] = a[j], a[i]
a[i + 1:] = reversed(a[i + 1:])
print(' '.join(map(str, a)))
""",
        "test_inputs": ["3\n1 2 3", "3\n3 2 1", "3\n1 1 5", "1\n1", "4\n1 3 2 1"],
    },
    {
        "id": "arr-spiral-matrix", "title": "Spiral Matrix Traversal", "topic": "arrays",
        "difficulty": "Medium",
        "statement": "Given a matrix, print its elements visited in spiral order starting from the top-left corner, moving right, then down, then left, then up, spiraling inward.",
        "input_format": "Line 1: rows cols. Next rows lines: cols space-separated integers.", "output_format": "Space-separated integers in spiral order.",
        "constraints": "1 <= rows, cols <= 50",
        "reference_solution":
"""rows, cols = map(int, input().split())
g = [list(map(int, input().split())) for _ in range(rows)]
top, bottom, left, right = 0, rows - 1, 0, cols - 1
out = []
while top <= bottom and left <= right:
    for j in range(left, right + 1):
        out.append(g[top][j])
    top += 1
    for i in range(top, bottom + 1):
        out.append(g[i][right])
    right -= 1
    if top <= bottom:
        for j in range(right, left - 1, -1):
            out.append(g[bottom][j])
        bottom -= 1
    if left <= right:
        for i in range(bottom, top - 1, -1):
            out.append(g[i][left])
        left += 1
print(' '.join(map(str, out)))
""",
        "test_inputs": ["3 3\n1 2 3\n4 5 6\n7 8 9", "3 4\n1 2 3 4\n5 6 7 8\n9 10 11 12", "1 1\n5", "1 4\n1 2 3 4", "4 1\n1\n2\n3\n4"],
    },
    {
        "id": "arr-majority-element", "title": "Majority Element", "topic": "arrays",
        "difficulty": "Easy",
        "statement": "Given an array of n integers, print the value that appears more than n/2 times (it is guaranteed exactly one such value exists).",
        "input_format": "Line 1: n. Line 2: n integers.", "output_format": "Single integer.",
        "constraints": "1 <= n <= 5*10^4",
        "reference_solution":
"""n = int(input())
a = list(map(int, input().split()))
count = 0
candidate = None
for x in a:
    if count == 0:
        candidate = x
    count += 1 if x == candidate else -1
print(candidate)
""",
        "buggy_solution":
"""n = int(input())
a = list(map(int, input().split()))
count = 0
candidate = None
for x in a:
    if count == 0:
        candidate = x
    count += 1 if x == candidate else 0
print(candidate)
""",
        "test_inputs": ["6\n5 6 6 6 6 5", "7\n2 2 1 1 1 2 2", "3\n3 2 3", "1\n5", "6\n6 5 5 6 6 6"],
    },
]


def _run_ref(code: str, stdin: str, timeout: int = 5) -> str:
    """Execute the reference solution once. Any failure raises \u2013 that means the
    bank has a mismatched problem and we want to know at load time, not
    silently during a user run."""
    with tempfile.TemporaryDirectory(prefix="pm_bank_") as d:
        p = os.path.join(d, "main.py")
        with open(p, "w") as f:
            f.write(code)
        proc = subprocess.run(["python3", p], input=stdin, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"ref_solution exited {proc.returncode}: {proc.stderr[:200]}")
        return (proc.stdout or "").strip()


def _hydrate(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Materialize a raw entry into the shape the OA engine expects."""
    ref = raw["reference_solution"]
    tests = [
        {"input": stdin, "expected_output": _run_ref(ref, stdin)}
        for stdin in raw["test_inputs"]
    ]
    # First two are visible, rest are hidden.
    visible = tests[:2]
    hidden = tests[2:5] if len(tests) > 2 else []
    return {
        "id": raw["id"],
        "title": raw["title"],
        "difficulty": raw["difficulty"],
        "topic": raw["topic"],
        "statement": raw["statement"],
        "input_format": raw["input_format"],
        "output_format": raw["output_format"],
        "constraints": raw["constraints"],
        "visible_tests": visible,
        "hidden_tests": hidden,
        # Only include buggy_solution when present (used by Automata Fix rounds).
        **({"buggy_code": raw["buggy_solution"]} if "buggy_solution" in raw else {}),
    }


# Materialize the bank ONCE at import time so all runs share the same
# consistent problem set. Any inconsistency raises here (fail-fast).
_BANK: List[Dict[str, Any]] = [_hydrate(r) for r in _RAW]


# ---- Cross-attempt repetition tracking ------------------------------------
# Added 2026-09 (Phase 0 live-generation migration): sample_problems' own
# `exclude_ids` param only prevents duplicates WITHIN one draw (e.g. Wipro's
# easy-medium + hard split calling this twice) -- it never stopped the same
# candidate from seeing the same coding problem again on a retaken
# assessment, since nothing here tracked what a given user had already been
# served. Same collection shape and `get_seen_ids`/`mark_seen` interface as
# mcq_static_bank.py's tracker, deliberately not reinvented -- topic is
# always "coding" today (this bank has no sub-topic split), but the param is
# kept for interface consistency with every other bank's tracker.
_db = None  # set by init(db)


def init(db) -> None:
    global _db
    _db = db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_seen_ids(user_id: str, topic: str = "coding") -> set:
    if _db is None:
        return set()
    doc = await _db.problem_bank_seen.find_one({"user_id": user_id, "topic": topic})
    return set(doc.get("question_ids", [])) if doc else set()


async def mark_seen(user_id: str, question_ids: List[str], topic: str = "coding") -> None:
    if _db is None or not question_ids:
        return
    await _db.problem_bank_seen.update_one(
        {"user_id": user_id, "topic": topic},
        {"$addToSet": {"question_ids": {"$each": question_ids}}, "$set": {"updated_at": _now_iso()}},
        upsert=True,
    )


def sample_problems(
    count: int, difficulty_target: str | None = None, needs_buggy: bool = False,
    exclude_ids: set | None = None,
) -> List[Dict[str, Any]]:
    """Return ``count`` distinct problems from the bank.

    - ``difficulty_target``:
        * 'easy_medium' \u2013 60% Easy + 40% Medium (Zoho R2)
        * 'hard'        \u2013 all Hard (Zoho R3, IBM DSA)
        * None          \u2013 15/65/20 Easy/Medium/Hard
    - ``needs_buggy``: only sample problems that have a ``buggy_code`` field
      (Automata Fix requires it).
    - ``exclude_ids``: skip these problem ids \u2014 used when a company calls
      this function once per problem with different difficulty_targets
      (e.g. Wipro's easy-medium + hard split), so a Medium problem picked
      for one call can't also be drawn for another.
    """
    pool = _BANK if not needs_buggy else [p for p in _BANK if "buggy_code" in p]
    if exclude_ids:
        pool = [p for p in pool if p.get("id") not in exclude_ids]
    by_diff = {"Easy": [], "Medium": [], "Hard": []}
    for p in pool:
        by_diff[p["difficulty"]].append(p)

    def take(diff: str, n: int) -> List[Dict[str, Any]]:
        picks = by_diff[diff][:]
        random.shuffle(picks)
        return picks[:n]

    if difficulty_target == "easy_medium":
        want_e = max(1, int(round(count * 0.6)))
        want_m = count - want_e
        picks = take("Easy", want_e) + take("Medium", want_m)
    elif difficulty_target == "hard":
        picks = take("Hard", count)
        if len(picks) < count:  # not enough Hards \u2013 top up with Mediums
            picks += take("Medium", count - len(picks))
    elif difficulty_target == "medium":
        # All Medium (used by the general-purpose "Core Assessment" track).
        picks = take("Medium", count)
        if len(picks) < count:
            # Should never happen with current bank depth (10 Mediums), but
            # top up with Easy as a last resort rather than under-serving.
            picks += take("Easy", count - len(picks))
    else:
        want_e = max(0, int(round(count * 0.15)))
        want_h = max(0, int(round(count * 0.20)))
        want_m = count - want_e - want_h
        picks = take("Easy", want_e) + take("Medium", want_m) + take("Hard", want_h)
    random.shuffle(picks)
    # Ensure we always return exactly count problems if possible
    if len(picks) < count:
        remaining = [p for p in pool if p not in picks]
        random.shuffle(remaining)
        picks += remaining[: count - len(picks)]
    return picks[:count]
