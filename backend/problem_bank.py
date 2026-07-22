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
from typing import Any, Dict, List

_RAW: List[Dict[str, Any]] = [
    # ------------------------------------------------------------------ EASY
    {
        "id": "two-sum", "title": "Two Sum", "difficulty": "Easy",
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
        "id": "reverse-string", "title": "Reverse String", "difficulty": "Easy",
        "statement": "Read a string and print it reversed. No leading/trailing whitespace in output.",
        "input_format": "Single line string.", "output_format": "Reversed string.",
        "constraints": "1 \u2264 |s| \u2264 10^5",
        "reference_solution": "print(input()[::-1])\n",
        "buggy_solution": "print(input()[::-2])\n",
        "test_inputs": ["hello", "a", "racecar", "Placemint", "12345"],
    },
    {
        "id": "fizzbuzz", "title": "Fizz Buzz", "difficulty": "Easy",
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
        "id": "valid-palindrome", "title": "Valid Palindrome", "difficulty": "Easy",
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
        "id": "max-subarray-sum", "title": "Maximum Subarray Sum (Kadane)", "difficulty": "Easy",
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
        "id": "group-anagrams", "title": "Group Anagrams (count)", "difficulty": "Medium",
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
        "id": "longest-substring-no-repeat", "title": "Longest Substring Without Repeating Characters", "difficulty": "Medium",
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
        "id": "coin-change", "title": "Coin Change (Min Coins)", "difficulty": "Medium",
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
        "id": "product-except-self", "title": "Product of Array Except Self", "difficulty": "Medium",
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
        "id": "rotate-image", "title": "Rotate Matrix 90\u00b0 Clockwise", "difficulty": "Medium",
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
        "id": "num-islands", "title": "Number of Islands", "difficulty": "Medium",
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
        "id": "edit-distance", "title": "Edit Distance (Levenshtein)", "difficulty": "Hard",
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
        "id": "trap-rain", "title": "Trapping Rain Water", "difficulty": "Hard",
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
        "id": "word-ladder-length", "title": "Word Ladder Length", "difficulty": "Hard",
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
        "id": "contains-duplicate", "title": "Contains Duplicate", "difficulty": "Easy",
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
        "id": "missing-number", "title": "Missing Number", "difficulty": "Easy",
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
        "id": "buy-sell-stock", "title": "Best Time to Buy and Sell Stock", "difficulty": "Easy",
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
        "id": "climb-stairs", "title": "Climbing Stairs", "difficulty": "Easy",
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
        "id": "merge-sorted", "title": "Merge Two Sorted Arrays", "difficulty": "Easy",
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
        "id": "search-rotated", "title": "Search in Rotated Sorted Array", "difficulty": "Medium",
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
        "id": "container-water", "title": "Container With Most Water", "difficulty": "Medium",
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
        "id": "longest-palindromic", "title": "Longest Palindromic Substring Length", "difficulty": "Medium",
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
        "id": "combination-sum-count", "title": "Combination Sum (Count)", "difficulty": "Medium",
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
        "id": "median-two-sorted", "title": "Median of Two Sorted Arrays", "difficulty": "Hard",
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
        "id": "largest-rect-hist", "title": "Largest Rectangle in Histogram", "difficulty": "Hard",
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
        "id": "longest-valid-paren", "title": "Longest Valid Parentheses", "difficulty": "Hard",
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
        "id": "n-queens-count", "title": "N-Queens (Count Solutions)", "difficulty": "Hard",
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
        "id": "merge-k-sorted", "title": "Merge K Sorted Arrays", "difficulty": "Hard",
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
        "id": "sudoku-valid", "title": "Validate a 9x9 Sudoku Board", "difficulty": "Hard",
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
