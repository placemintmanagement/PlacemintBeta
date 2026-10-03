# -*- coding: utf-8 -*-
"""Round 4 (AI-Assisted Coding) problem pool -- schema + content + design.

Confirmed live-evidence flow (real click-through of an actual mock
assessment tool, not guessed) this module is built against:

  1. Problem shown: statement, difficulty/topic tag, example input,
     constraints. Code editor starts EMPTY ("Code will appear here when
     requested during AI interaction...").
  2. "Start Discussion" -> AI opens with a welcome message + first question.
  3. STAGE 1 (understand the problem) -- free text, gatekept: vague answers
     ("xyz") or attempts to skip ahead ("write the full code") are rejected
     and RE-ASKED AT THE SAME STAGE, with a specific, polite re-prompt.
  4. STAGE 2 (explain approach) -- free text, also gatekept.
  5. STAGE 3 (state time/space complexity) -- its OWN explicit stage even
     if already mentioned earlier; this is checklist-driven (specific
     required elements present/absent), not a holistic read of the whole
     conversation.
  6. CONSENT GATE (buttons, not free text): "Would you like me to generate
     a preliminary [language] solution based on your strategy in the code
     editor? (Yes / No)". "No" just holds and re-prompts patiently, no
     penalty -- genuine candidate pacing control.
  7. A DELIBERATELY FLAWED solution is generated into the editor -- one
     real, specific, documented bug, inline-marked with a comment (e.g.
     "// <--- Missing required base check here!"). This is intentionally
     NOT working code.
  8. SELF-REVIEW CHECKPOINT (buttons): "Is this implementation fully
     correct and ready to run? (Yes / No)" -- the actual test: does the
     candidate blindly trust AI output or catch the flaw.
  9. If "No" (correct): "Please explain what specific logic error or
     missing condition exists" -- free text, gatekept for genuinely
     naming the real issue (not just "something's wrong").
  10. AUTO-COMPLETION once the bug is correctly explained -- no manual
      code-editing, no separate submit button. Final display shows
      "Reference Solution (Fixed)" -- the corrected code with the
      candidate's identified fix applied.

CORE INSIGHT: this round does NOT test code-writing -- the candidate
never submits runnable code themselves. It tests CRITICAL EVALUATION of
AI-generated output. No code-execution/test-running infrastructure is
needed for the live candidate experience -- this is entirely a gated,
staged LLM conversation with one built-in "trap" per problem.

UNCONFIRMED / ASSUMED (flagged, not verified against real evidence -- the
"Yes" path at the consent gate always led to a flawed solution in
testing, and clicking "Yes" at the self-review checkpoint -- i.e.
accepting the flawed code as correct -- was never observed): what
happens if a candidate blindly accepts the flawed code. This module
documents a REASONABLE DEFAULT (see STAGE_SELF_REVIEW's "on_accept_flaw"
design below: round ends, scored as a miss, reference solution is still
shown) in PART 2's design section, but this is NOT implemented as live
logic here, and should be re-verified against real evidence before a
future implementation pass treats it as confirmed.

============================================================================
PART 0 -- PROBLEM SELECTION
============================================================================
15 problems selected from problem_bank.py's ~104, EXCLUDING all 25 ids
already used by Round 3's debugging_bank.py (confirmed by reading that
module's _RAW list before picking -- see _ROUND3_EXCLUDED_IDS below, kept
as a literal, checkable record of what was excluded and why, not just an
assertion). Roughly 2 per topic across the 8 tagged topics (advanced_dsa
got only 1, since 15 doesn't divide evenly by 8):

  arrays (2): missing-number, rotate-image
  strings (2): string-isomorphic, string-integer-to-roman
  greedy (2): greedy-activity-selection, greedy-assign-cookies
  two_pointer_sliding_window (2): longest-substring-no-repeat, tp-3sum
  trees (2): tree-path-sum, tree-lca-bst
  graphs (2): graph-connected-components, graph-course-schedule
  2d_dp (2): dp-01-knapsack, dp-word-break
  advanced_dsa (1): adv-redundant-connection

Each was chosen for having a clean, ONE-SENTENCE-explainable "trap" bug
(see PART 1) -- deliberately avoiding problems needing multi-paragraph
setup to explain what's wrong, since "teachable" matters more here than
in Round 3: the candidate must articulate the bug in free text, and an
LLM grader judges whether their explanation actually names the real
issue (see bug_explanation_key_points per problem).

============================================================================
PART 1 -- BUG INJECTION + LANGUAGE DECISION (read this, it's a real decision)
============================================================================
DECISION (flagged, not silently assumed): display_language = "cpp" for
all 15, translated from problem_bank.py's existing verified Python
reference_solution. This matches the confirmed real evidence, which
showed C++ specifically (not Python) in the live tool's editor. The
Python reference remains the source of truth for correctness (it's
already fail-fast verified by problem_bank.py's own import-time check);
the C++ translations here were independently verified (see below) to
produce byte-identical stdout to the Python reference on every one of
problem_bank.py's existing test_inputs for that problem.

Unlike Round 3, NO live execution infrastructure is needed for this
round's actual candidate experience -- the candidate only ever reads and
discusses this code, never runs it. But per the task's own instruction,
every reference/flawed pair below was still ACTUALLY COMPILED AND RUN
(via services.code_runner's real g++ pipeline, the same one Round 3 and
the "coding" round use) during authoring, to guarantee:
  (a) every reference C++ translation matches the Python reference's
      output on every one of that problem's existing test_inputs, and
  (b) every flawed C++ version GENUINELY diverges (wrong output, or a
      real crash) from the correct output on at least one input -- never
      a merely cosmetic difference from the reference.
This verification was done via a standalone script during authoring, not
wired into this module's import (same fail-fast-cost lesson already
learned the hard way while building Round 3's debugging_bank.py -- see
that module's own docstring on why expensive execution-based checks must
be opt-in, not automatic at import). verify_one()/verify_all() below let
that same check be re-run on demand later; they are NOT called at import.

Bug categories used (same 6 named categories Round 3 established), with
a real effort not to let one dominate:
  off_by_one (3): missing-number, graph-connected-components,
    adv-redundant-connection
  wrong_comparison_operator (4): string-integer-to-roman,
    greedy-assign-cookies, longest-substring-no-repeat, tree-lca-bst,
    dp-01-knapsack  [5, see note below]
  incomplete_boundary_handling (2): string-isomorphic, tp-3sum
  missing_base_case (2): tree-path-sum, dp-word-break
  wrong_variable_reference (2): rotate-image, greedy-activity-selection
  state_tracking_error (1): graph-course-schedule
  (wrong_comparison_operator ended up at 5/15 despite the intent to
  balance categories -- it's genuinely the most natural fit for several
  of these problems' cleanest single-bug injection point; flagging this
  rather than forcing an artificial category label onto a bug that
  doesn't really fit it.)
"""
from __future__ import annotations
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from banks import problem_bank as _pb
from services.code_runner import run_code

_PB_BANK_BY_ID: Dict[str, Dict[str, Any]] = {p["id"]: p for p in _pb._BANK}

# Round 3's full 25-problem pool, read directly from debugging_bank.py at
# authoring time and pinned here as a literal so this exclusion is a
# checkable fact, not a claim -- if debugging_bank.py's pool ever changes,
# this won't silently drift out of sync with it (it's a deliberate, frozen
# record of what NOT to reuse, made at the moment of selection).
_ROUND3_EXCLUDED_IDS: Set[str] = {
    "two-sum", "max-subarray-sum", "arr-majority-element", "string-valid-anagram",
    "group-anagrams", "string-roman-to-integer", "buy-sell-stock", "greedy-merge-intervals",
    "greedy-gas-station", "greedy-jump-game", "valid-palindrome", "container-water",
    "tp-sort-colors", "tree-max-depth", "tree-invert", "tree-validate-bst", "num-islands",
    "graph-bfs-shortest-path", "graph-cycle-undirected", "climb-stairs", "coin-change",
    "dp-longest-common-subsequence", "adv-top-k-frequent", "adv-kth-largest-array", "adv-min-stack",
}

BUG_CATEGORIES = (
    "off_by_one", "wrong_comparison_operator", "incomplete_boundary_handling",
    "missing_base_case", "wrong_variable_reference", "state_tracking_error",
)


_RAW: List[Dict[str, Any]] = [
    {
        "id": "missing-number",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    long long n; cin>>n;\n"
            "    vector<long long> a(n);\n"
            "    for(auto&x:a) cin>>x;\n"
            "    long long s=0; for(auto x:a) s+=x;\n"
            "    cout << n*(n+1)/2 - s << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    long long n; cin>>n;\n"
            "    vector<long long> a(n);\n"
            "    for(auto&x:a) cin>>x;\n"
            "    long long s=0; for(auto x:a) s+=x;\n"
            "    cout << n*(n-1)/2 - s << \"\\n\";  // <--- Wrong formula: should be n*(n+1)/2 for numbers in [0,n]\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "off_by_one",
        "bug_explanation_key_points": [
            "must identify that the formula uses n*(n-1)/2 instead of n*(n+1)/2",
            "must note this is the sum of 0..n-1, not 0..n, so it's missing the value n from the expected total",
            "must connect this to producing a wrong (often negative or too-small) missing number on every input, not just edge cases",
        ],
    },
    {
        "id": "rotate-image",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<vector<long long>> m(n, vector<long long>(n));\n"
            "    for(int i=0;i<n;i++) for(int j=0;j<n;j++) cin>>m[i][j];\n"
            "    vector<vector<long long>> rot(n, vector<long long>(n));\n"
            "    for(int i=0;i<n;i++)\n"
            "        for(int j=0;j<n;j++)\n"
            "            rot[i][j] = m[n-1-j][i];\n"
            "    for(int i=0;i<n;i++){\n"
            "        for(int j=0;j<n;j++) cout<<rot[i][j]<<(j+1<n?\" \":\"\\n\");\n"
            "    }\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<vector<long long>> m(n, vector<long long>(n));\n"
            "    for(int i=0;i<n;i++) for(int j=0;j<n;j++) cin>>m[i][j];\n"
            "    vector<vector<long long>> rot(n, vector<long long>(n));\n"
            "    for(int i=0;i<n;i++)\n"
            "        for(int j=0;j<n;j++)\n"
            "            rot[i][j] = m[j][n-1-i];  // <--- Wrong index formula: this rotates COUNTER-clockwise, not clockwise\n"
            "    for(int i=0;i<n;i++){\n"
            "        for(int j=0;j<n;j++) cout<<rot[i][j]<<(j+1<n?\" \":\"\\n\");\n"
            "    }\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "wrong_variable_reference",
        "bug_explanation_key_points": [
            "must identify that the index formula m[j][n-1-i] rotates counter-clockwise",
            "must state the correct formula is m[n-1-j][i] for a clockwise rotation",
            "must note the output is a real rotation, just the wrong direction -- not garbage/random values, which is why it can look right at a glance",
        ],
    },
    {
        "id": "string-isomorphic",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    string s,t;\n"
            "    getline(cin,s); getline(cin,t);\n"
            "    if (s.size()!=t.size()){ cout<<\"NO\\n\"; return 0; }\n"
            "    unordered_map<char,char> m1,m2;\n"
            "    bool ok=true;\n"
            "    for (size_t i=0;i<s.size();i++){\n"
            "        char a=s[i], b=t[i];\n"
            "        if (m1.count(a) && m1[a]!=b){ ok=false; break; }\n"
            "        if (m2.count(b) && m2[b]!=a){ ok=false; break; }\n"
            "        m1[a]=b; m2[b]=a;\n"
            "    }\n"
            "    cout << (ok?\"YES\":\"NO\") << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    string s,t;\n"
            "    getline(cin,s); getline(cin,t);\n"
            "    if (s.size()!=t.size()){ cout<<\"NO\\n\"; return 0; }\n"
            "    unordered_map<char,char> m1,m2;\n"
            "    bool ok=true;\n"
            "    for (size_t i=0;i<s.size();i++){\n"
            "        char a=s[i], b=t[i];\n"
            "        if (m1.count(a) && m1[a]!=b){ ok=false; break; }\n"
            "        // <--- Missing reverse-mapping check here! Two different source\n"
            "        // characters can map to the SAME target character without this.\n"
            "        m1[a]=b; m2[b]=a;\n"
            "    }\n"
            "    cout << (ok?\"YES\":\"NO\") << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "incomplete_boundary_handling",
        "bug_explanation_key_points": [
            "must identify the missing check on m2 (the reverse/target-to-source mapping)",
            "must explain that isomorphism requires a ONE-TO-ONE mapping in BOTH directions, not just source-to-target",
            "must give or recognize a concrete counterexample where two different source characters map to the same target character (e.g. s=\"ab\", t=\"aa\")",
        ],
    },
    {
        "id": "string-integer-to-roman",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<pair<int,string>> vals = {\n"
            "        {1000,\"M\"},{900,\"CM\"},{500,\"D\"},{400,\"CD\"},{100,\"C\"},{90,\"XC\"},\n"
            "        {50,\"L\"},{40,\"XL\"},{10,\"X\"},{9,\"IX\"},{5,\"V\"},{4,\"IV\"},{1,\"I\"}\n"
            "    };\n"
            "    string out;\n"
            "    for (auto& pr : vals){\n"
            "        while (n>=pr.first){ out+=pr.second; n-=pr.first; }\n"
            "    }\n"
            "    cout << out << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<pair<int,string>> vals = {\n"
            "        {1000,\"M\"},{900,\"CM\"},{500,\"D\"},{400,\"CD\"},{100,\"C\"},{90,\"XC\"},\n"
            "        {50,\"L\"},{40,\"XL\"},{10,\"X\"},{9,\"IX\"},{5,\"V\"},{4,\"IV\"},{1,\"I\"}\n"
            "    };\n"
            "    string out;\n"
            "    for (auto& pr : vals){\n"
            "        while (n>pr.first){ out+=pr.second; n-=pr.first; }  // <--- Wrong comparison: should be >=, this drops exact-match units\n"
            "    }\n"
            "    cout << out << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "wrong_comparison_operator",
        "bug_explanation_key_points": [
            "must identify the comparison should be >= (greater-than-or-equal), not strictly >",
            "must explain that using strict > silently skips the case where n exactly equals a denomination (especially the final 'I'=1 tier)",
            "must connect this to producing a numeral that's short by exactly one unit's worth of value on many inputs",
        ],
    },
    {
        "id": "greedy-activity-selection",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<long long> s(n), e(n);\n"
            "    for(auto&x:s) cin>>x;\n"
            "    for(auto&x:e) cin>>x;\n"
            "    vector<pair<long long,long long>> acts(n);\n"
            "    for(int i=0;i<n;i++) acts[i]=make_pair(e[i], s[i]);\n"
            "    sort(acts.begin(), acts.end());\n"
            "    long long count=0;\n"
            "    long long last_end = LLONG_MIN;\n"
            "    for (auto& pr : acts){\n"
            "        long long end=pr.first, start=pr.second;\n"
            "        if (start >= last_end){ count++; last_end = end; }\n"
            "    }\n"
            "    cout << count << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<long long> s(n), e(n);\n"
            "    for(auto&x:s) cin>>x;\n"
            "    for(auto&x:e) cin>>x;\n"
            "    vector<pair<long long,long long>> acts(n);\n"
            "    for(int i=0;i<n;i++) acts[i]=make_pair(s[i], e[i]);  // <--- Wrong sort key: sorting by START breaks the greedy proof, must sort by END\n"
            "    sort(acts.begin(), acts.end());\n"
            "    long long count=0;\n"
            "    long long last_end = LLONG_MIN;\n"
            "    for (auto& pr : acts){\n"
            "        long long start=pr.first, end=pr.second;\n"
            "        if (start >= last_end){ count++; last_end = end; }\n"
            "    }\n"
            "    cout << count << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "wrong_variable_reference",
        "bug_explanation_key_points": [
            "must identify that activities are sorted by START time instead of END time",
            "must explain that the classic greedy proof for this problem specifically requires sorting by END time (earliest finish first)",
            "must recognize this can pick a long early-starting activity that blocks out several shorter ones, giving a suboptimal (too-small) count",
        ],
    },
    {
        "id": "greedy-assign-cookies",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<long long> g(n);\n"
            "    for(auto&x:g) cin>>x;\n"
            "    int m; cin>>m;\n"
            "    vector<long long> s(m);\n"
            "    for(auto&x:s) cin>>x;\n"
            "    sort(g.begin(),g.end());\n"
            "    sort(s.begin(),s.end());\n"
            "    int i=0,j=0,count=0;\n"
            "    while (i<n && j<m){\n"
            "        if (s[j] >= g[i]){ count++; i++; j++; }\n"
            "        else j++;\n"
            "    }\n"
            "    cout << count << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<long long> g(n);\n"
            "    for(auto&x:g) cin>>x;\n"
            "    int m; cin>>m;\n"
            "    vector<long long> s(m);\n"
            "    for(auto&x:s) cin>>x;\n"
            "    sort(g.begin(),g.end());\n"
            "    sort(s.begin(),s.end());\n"
            "    int i=0,j=0,count=0;\n"
            "    while (i<n && j<m){\n"
            "        if (s[j] > g[i]){ count++; i++; j++; }  // <--- Wrong comparison: should be >=, this rejects an exact-size match\n"
            "        else j++;\n"
            "    }\n"
            "    cout << count << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "wrong_comparison_operator",
        "bug_explanation_key_points": [
            "must identify that the comparison should be >= (a cookie exactly the child's greed factor DOES satisfy them), not strictly >",
            "must connect this to undercounting content children whenever a cookie size exactly equals a greed factor",
        ],
    },
    {
        "id": "longest-substring-no-repeat",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    string s;\n"
            "    getline(cin, s);\n"
            "    unordered_map<char,int> last;\n"
            "    int start=0, best=0;\n"
            "    for (int i=0;i<(int)s.size();i++){\n"
            "        char c=s[i];\n"
            "        if (last.count(c) && last[c] >= start) start = last[c]+1;\n"
            "        last[c]=i;\n"
            "        best = max(best, i-start+1);\n"
            "    }\n"
            "    cout << best << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    string s;\n"
            "    getline(cin, s);\n"
            "    unordered_map<char,int> last;\n"
            "    int start=0, best=0;\n"
            "    for (int i=0;i<(int)s.size();i++){\n"
            "        char c=s[i];\n"
            "        if (last.count(c) && last[c] > start) start = last[c]+1;  // <--- Wrong comparison: should be >=, misses a repeat exactly at the window's start\n"
            "        last[c]=i;\n"
            "        best = max(best, i-start+1);\n"
            "    }\n"
            "    cout << best << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "wrong_comparison_operator",
        "bug_explanation_key_points": [
            "must identify the comparison should be >= (last seen position at or after the window start), not strictly >",
            "must explain that when the repeated character's last position EQUALS the current window start, the window fails to advance past it",
            "must connect this to the algorithm reporting a window length that's too large (includes a duplicate character)",
        ],
    },
    {
        "id": "tp-3sum",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<long long> a(n);\n"
            "    for(auto&x:a) cin>>x;\n"
            "    sort(a.begin(), a.end());\n"
            "    vector<array<long long,3>> res;\n"
            "    for (int i=0;i<n;i++){\n"
            "        if (i>0 && a[i]==a[i-1]) continue;\n"
            "        int l=i+1, r=n-1;\n"
            "        while (l<r){\n"
            "            long long sum = a[i]+a[l]+a[r];\n"
            "            if (sum<0) l++;\n"
            "            else if (sum>0) r--;\n"
            "            else {\n"
            "                res.push_back({a[i],a[l],a[r]});\n"
            "                l++; r--;\n"
            "                while (l<r && a[l]==a[l-1]) l++;\n"
            "                while (l<r && a[r]==a[r+1]) r--;\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "    if (!res.empty()){\n"
            "        for (auto& t : res) cout << t[0] << \" \" << t[1] << \" \" << t[2] << \"\\n\";\n"
            "    } else {\n"
            "        cout << \"\\n\";\n"
            "    }\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<long long> a(n);\n"
            "    for(auto&x:a) cin>>x;\n"
            "    sort(a.begin(), a.end());\n"
            "    vector<array<long long,3>> res;\n"
            "    for (int i=0;i<n;i++){\n"
            "        // <--- Missing outer-loop duplicate skip here! Without it, the same\n"
            "        // triplet gets found again from the next equal value of a[i].\n"
            "        int l=i+1, r=n-1;\n"
            "        while (l<r){\n"
            "            long long sum = a[i]+a[l]+a[r];\n"
            "            if (sum<0) l++;\n"
            "            else if (sum>0) r--;\n"
            "            else {\n"
            "                res.push_back({a[i],a[l],a[r]});\n"
            "                l++; r--;\n"
            "                while (l<r && a[l]==a[l-1]) l++;\n"
            "                while (l<r && a[r]==a[r+1]) r--;\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "    if (!res.empty()){\n"
            "        for (auto& t : res) cout << t[0] << \" \" << t[1] << \" \" << t[2] << \"\\n\";\n"
            "    } else {\n"
            "        cout << \"\\n\";\n"
            "    }\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "incomplete_boundary_handling",
        "bug_explanation_key_points": [
            "must identify the missing 'if i>0 and a[i]==a[i-1]: continue' guard on the OUTER loop",
            "must distinguish this from the inner l/r dedup loops, which are still present and correct",
            "must explain this causes the SAME triplet to be emitted more than once when the outer index revisits an equal value",
        ],
    },
    {
        "id": "tree-path-sum",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "struct Node { long long v; Node *l=nullptr, *r=nullptr; Node(long long val):v(val){} };\n"
            "bool has(Node* n, long long rem){\n"
            "    if (!n) return false;\n"
            "    if (!n->l && !n->r) return rem == n->v;\n"
            "    return has(n->l, rem - n->v) || has(n->r, rem - n->v);\n"
            "}\n"
            "int main(){\n"
            "    string line;\n"
            "    getline(cin, line);\n"
            "    istringstream iss(line);\n"
            "    vector<string> toks; string tok;\n"
            "    while (iss >> tok) toks.push_back(tok);\n"
            "    long long target;\n"
            "    cin >> target;\n"
            "    if (toks.empty() || toks[0]==\"N\"){ cout << \"NO\\n\"; return 0; }\n"
            "    Node* root = new Node(stoll(toks[0]));\n"
            "    deque<Node*> q; q.push_back(root);\n"
            "    size_t i=1;\n"
            "    while (!q.empty() && i<toks.size()){\n"
            "        Node* node = q.front(); q.pop_front();\n"
            "        if (i<toks.size() && toks[i]!=\"N\"){ node->l = new Node(stoll(toks[i])); q.push_back(node->l); }\n"
            "        i++;\n"
            "        if (i<toks.size() && toks[i]!=\"N\"){ node->r = new Node(stoll(toks[i])); q.push_back(node->r); }\n"
            "        i++;\n"
            "    }\n"
            "    cout << (has(root, target) ? \"YES\" : \"NO\") << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "struct Node { long long v; Node *l=nullptr, *r=nullptr; Node(long long val):v(val){} };\n"
            "bool has(Node* n, long long rem){\n"
            "    if (!n) return false;\n"
            "    if (rem == n->v) return true;  // <--- Missing leaf check! This accepts a match at ANY node, not only a root-to-leaf path.\n"
            "    return has(n->l, rem - n->v) || has(n->r, rem - n->v);\n"
            "}\n"
            "int main(){\n"
            "    string line;\n"
            "    getline(cin, line);\n"
            "    istringstream iss(line);\n"
            "    vector<string> toks; string tok;\n"
            "    while (iss >> tok) toks.push_back(tok);\n"
            "    long long target;\n"
            "    cin >> target;\n"
            "    if (toks.empty() || toks[0]==\"N\"){ cout << \"NO\\n\"; return 0; }\n"
            "    Node* root = new Node(stoll(toks[0]));\n"
            "    deque<Node*> q; q.push_back(root);\n"
            "    size_t i=1;\n"
            "    while (!q.empty() && i<toks.size()){\n"
            "        Node* node = q.front(); q.pop_front();\n"
            "        if (i<toks.size() && toks[i]!=\"N\"){ node->l = new Node(stoll(toks[i])); q.push_back(node->l); }\n"
            "        i++;\n"
            "        if (i<toks.size() && toks[i]!=\"N\"){ node->r = new Node(stoll(toks[i])); q.push_back(node->r); }\n"
            "        i++;\n"
            "    }\n"
            "    cout << (has(root, target) ? \"YES\" : \"NO\") << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "missing_base_case",
        "bug_explanation_key_points": [
            "must identify that the equality check (rem == n->v) fires at ANY node, not only at a leaf",
            "must explain the problem specifically requires a ROOT-TO-LEAF path, so a match at an internal node must NOT count",
            "must give or recognize a concrete counterexample: a tree where the target equals the root's own value but the root has children (e.g. root=1 with children, target=1)",
        ],
    },
    {
        "id": "tree-lca-bst",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "struct Node { long long v; Node *l=nullptr, *r=nullptr; Node(long long val):v(val){} };\n"
            "int main(){\n"
            "    string line;\n"
            "    getline(cin, line);\n"
            "    istringstream iss(line);\n"
            "    vector<string> toks; string tok;\n"
            "    while (iss >> tok) toks.push_back(tok);\n"
            "    long long p,q;\n"
            "    cin >> p >> q;\n"
            "    Node* root = new Node(stoll(toks[0]));\n"
            "    deque<Node*> qu; qu.push_back(root);\n"
            "    size_t i=1;\n"
            "    while (!qu.empty() && i<toks.size()){\n"
            "        Node* node = qu.front(); qu.pop_front();\n"
            "        if (i<toks.size() && toks[i]!=\"N\"){ node->l = new Node(stoll(toks[i])); qu.push_back(node->l); }\n"
            "        i++;\n"
            "        if (i<toks.size() && toks[i]!=\"N\"){ node->r = new Node(stoll(toks[i])); qu.push_back(node->r); }\n"
            "        i++;\n"
            "    }\n"
            "    Node* node = root;\n"
            "    while (node){\n"
            "        if (p < node->v && q < node->v) node = node->l;\n"
            "        else if (p > node->v && q > node->v) node = node->r;\n"
            "        else break;\n"
            "    }\n"
            "    cout << node->v << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "struct Node { long long v; Node *l=nullptr, *r=nullptr; Node(long long val):v(val){} };\n"
            "int main(){\n"
            "    string line;\n"
            "    getline(cin, line);\n"
            "    istringstream iss(line);\n"
            "    vector<string> toks; string tok;\n"
            "    while (iss >> tok) toks.push_back(tok);\n"
            "    long long p,q;\n"
            "    cin >> p >> q;\n"
            "    Node* root = new Node(stoll(toks[0]));\n"
            "    deque<Node*> qu; qu.push_back(root);\n"
            "    size_t i=1;\n"
            "    while (!qu.empty() && i<toks.size()){\n"
            "        Node* node = qu.front(); qu.pop_front();\n"
            "        if (i<toks.size() && toks[i]!=\"N\"){ node->l = new Node(stoll(toks[i])); qu.push_back(node->l); }\n"
            "        i++;\n"
            "        if (i<toks.size() && toks[i]!=\"N\"){ node->r = new Node(stoll(toks[i])); qu.push_back(node->r); }\n"
            "        i++;\n"
            "    }\n"
            "    Node* node = root;\n"
            "    while (node){\n"
            "        if (p <= node->v && q <= node->v) node = node->l;          // <--- Wrong comparison: should be strict <, this descends\n"
            "        else if (p >= node->v && q >= node->v) node = node->r;    //      past a node whose value EQUALS p or q\n"
            "        else break;\n"
            "    }\n"
            "    cout << node->v << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "wrong_comparison_operator",
        "bug_explanation_key_points": [
            "must identify the comparisons should be strict < and > , not <= and >=",
            "must explain that once p or q EQUALS the current node's value, that node itself is the LCA and the walk must stop there",
            "must recognize this can walk right off the tree past the true LCA (node becomes null), which is a crash, not just a wrong number",
        ],
    },
    {
        "id": "graph-connected-components",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n, m; cin >> n >> m;\n"
            "    vector<vector<int>> adj(n);\n"
            "    for (int k=0;k<m;k++){\n"
            "        int u,v; cin>>u>>v;\n"
            "        adj[u].push_back(v); adj[v].push_back(u);\n"
            "    }\n"
            "    vector<bool> seen(n,false);\n"
            "    int count=0;\n"
            "    for (int i=0;i<n;i++){\n"
            "        if (!seen[i]){\n"
            "            count++;\n"
            "            vector<int> stack = {i};\n"
            "            seen[i]=true;\n"
            "            while (!stack.empty()){\n"
            "                int x = stack.back(); stack.pop_back();\n"
            "                for (int y : adj[x]){\n"
            "                    if (!seen[y]){ seen[y]=true; stack.push_back(y); }\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "    cout << count << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n, m; cin >> n >> m;\n"
            "    vector<vector<int>> adj(n);\n"
            "    for (int k=0;k<m;k++){\n"
            "        int u,v; cin>>u>>v;\n"
            "        adj[u].push_back(v); adj[v].push_back(u);\n"
            "    }\n"
            "    vector<bool> seen(n,false);\n"
            "    int count=0;\n"
            "    for (int i=1;i<n;i++){  // <--- Off-by-one: skips node 0 entirely, undercounting whenever node 0 has no edges\n"
            "        if (!seen[i]){\n"
            "            count++;\n"
            "            vector<int> stack = {i};\n"
            "            seen[i]=true;\n"
            "            while (!stack.empty()){\n"
            "                int x = stack.back(); stack.pop_back();\n"
            "                for (int y : adj[x]){\n"
            "                    if (!seen[y]){ seen[y]=true; stack.push_back(y); }\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "    cout << count << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "off_by_one",
        "bug_explanation_key_points": [
            "must identify the outer loop starts at i=1 instead of i=0, so node 0 is never checked as a potential component start",
            "must explain node 0 still gets counted correctly IF it has any edges (some other node's traversal reaches it), so the bug ONLY manifests when node 0 is isolated (no edges)",
            "must connect this to undercounting the total number of components by exactly 1 whenever node 0 is isolated",
        ],
    },
    {
        "id": "graph-course-schedule",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    int m; cin>>m;\n"
            "    vector<vector<int>> adj(n);\n"
            "    vector<int> indeg(n,0);\n"
            "    for (int k=0;k<m;k++){\n"
            "        int a,b; cin>>a>>b;\n"
            "        adj[b].push_back(a); indeg[a]++;\n"
            "    }\n"
            "    queue<int> q;\n"
            "    for (int i=0;i<n;i++) if (indeg[i]==0) q.push(i);\n"
            "    int processed=0;\n"
            "    while (!q.empty()){\n"
            "        int u=q.front(); q.pop(); processed++;\n"
            "        for (int v : adj[u]){\n"
            "            indeg[v]--;\n"
            "            if (indeg[v]==0) q.push(v);\n"
            "        }\n"
            "    }\n"
            "    cout << (processed==n ? \"YES\" : \"NO\") << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    int m; cin>>m;\n"
            "    vector<vector<int>> adj(n);\n"
            "    vector<int> indeg(n,0);\n"
            "    for (int k=0;k<m;k++){\n"
            "        int a,b; cin>>a>>b;\n"
            "        adj[b].push_back(a); indeg[a]++;\n"
            "    }\n"
            "    queue<int> q;\n"
            "    for (int i=0;i<n;i++) if (indeg[i]==0) q.push(i);\n"
            "    int processed=0;\n"
            "    while (!q.empty()){\n"
            "        int u=q.front(); q.pop(); processed++;\n"
            "        for (int v : adj[u]){\n"
            "            // <--- Missing indeg[v]-- here! A downstream course never becomes \"ready\", so its indegree never reaches 0.\n"
            "            if (indeg[v]==0) q.push(v);\n"
            "        }\n"
            "    }\n"
            "    cout << (processed==n ? \"YES\" : \"NO\") << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "state_tracking_error",
        "bug_explanation_key_points": [
            "must identify the missing 'indeg[v]--' line inside the neighbor loop",
            "must explain that without decrementing, a dependent course's indegree never drops to 0, so it never gets enqueued as ready",
            "must connect this to the algorithm reporting 'NO' (impossible) for many perfectly valid, cycle-free course orderings, since 'processed' undercounts",
        ],
    },
    {
        "id": "dp-01-knapsack",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<long long> wt(n), val(n);\n"
            "    for(auto&x:wt) cin>>x;\n"
            "    for(auto&x:val) cin>>x;\n"
            "    int cap; cin>>cap;\n"
            "    vector<vector<long long>> dp(n+1, vector<long long>(cap+1, 0));\n"
            "    for (int i=1;i<=n;i++){\n"
            "        for (int c=0;c<=cap;c++){\n"
            "            dp[i][c] = dp[i-1][c];\n"
            "            if (wt[i-1] <= c) dp[i][c] = max(dp[i][c], dp[i-1][c-wt[i-1]] + val[i-1]);\n"
            "        }\n"
            "    }\n"
            "    cout << dp[n][cap] << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin>>n;\n"
            "    vector<long long> wt(n), val(n);\n"
            "    for(auto&x:wt) cin>>x;\n"
            "    for(auto&x:val) cin>>x;\n"
            "    int cap; cin>>cap;\n"
            "    vector<vector<long long>> dp(n+1, vector<long long>(cap+1, 0));\n"
            "    for (int i=1;i<=n;i++){\n"
            "        for (int c=0;c<=cap;c++){\n"
            "            dp[i][c] = dp[i-1][c];\n"
            "            if (wt[i-1] < c) dp[i][c] = max(dp[i][c], dp[i-1][c-wt[i-1]] + val[i-1]);  // <--- Wrong comparison: should be <=, excludes an item that exactly fills the remaining capacity\n"
            "        }\n"
            "    }\n"
            "    cout << dp[n][cap] << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "wrong_comparison_operator",
        "bug_explanation_key_points": [
            "must identify the comparison should be <= (item weight at most the remaining capacity), not strictly <",
            "must connect this to systematically undervaluing knapsacks where an item's weight exactly equals the capacity (or a remaining sub-capacity)",
        ],
    },
    {
        "id": "dp-word-break",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    string s;\n"
            "    getline(cin, s);\n"
            "    int n; cin >> n;\n"
            "    unordered_set<string> words;\n"
            "    string w;\n"
            "    for (int i=0;i<n;i++){ cin >> w; words.insert(w); }\n"
            "    int m = s.size();\n"
            "    vector<bool> dp(m+1, false);\n"
            "    dp[0] = true;\n"
            "    for (int i=1;i<=m;i++){\n"
            "        for (int j=0;j<i;j++){\n"
            "            if (dp[j] && words.count(s.substr(j, i-j))){ dp[i]=true; break; }\n"
            "        }\n"
            "    }\n"
            "    cout << (dp[m] ? \"YES\" : \"NO\") << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    string s;\n"
            "    getline(cin, s);\n"
            "    int n; cin >> n;\n"
            "    unordered_set<string> words;\n"
            "    string w;\n"
            "    for (int i=0;i<n;i++){ cin >> w; words.insert(w); }\n"
            "    int m = s.size();\n"
            "    vector<bool> dp(m+1, false);\n"
            "    dp[0] = false;  // <--- Missing base case! An empty prefix trivially needs zero words, so this MUST be true.\n"
            "    for (int i=1;i<=m;i++){\n"
            "        for (int j=0;j<i;j++){\n"
            "            if (dp[j] && words.count(s.substr(j, i-j))){ dp[i]=true; break; }\n"
            "        }\n"
            "    }\n"
            "    cout << (dp[m] ? \"YES\" : \"NO\") << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "missing_base_case",
        "bug_explanation_key_points": [
            "must identify that dp[0] is set to false instead of true",
            "must explain dp[0] represents the empty prefix, which trivially requires zero words and must be true to bootstrap the recurrence",
            "must connect this to the algorithm reporting 'NO' for EVERY input, even ones with an obviously valid segmentation, since nothing can ever become true without this",
        ],
    },
    {
        "id": "adv-redundant-connection",
        "corrected_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin >> n;\n"
            "    vector<int> parent(n+1);\n"
            "    for (int i=0;i<=n;i++) parent[i]=i;\n"
            "    function<int(int)> find = [&](int x){\n"
            "        while (parent[x]!=x) x=parent[x];\n"
            "        return x;\n"
            "    };\n"
            "    int ansU=-1, ansV=-1;\n"
            "    for (int k=0;k<n;k++){\n"
            "        int u,v; cin>>u>>v;\n"
            "        int ru=find(u), rv=find(v);\n"
            "        if (ru==rv){ ansU=u; ansV=v; }\n"
            "        else parent[ru]=rv;\n"
            "    }\n"
            "    cout << ansU << \" \" << ansV << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "flawed_code": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main(){\n"
            "    int n; cin >> n;\n"
            "    vector<int> parent(n);  // <--- Off-by-one: nodes are labeled 1..n, so this array needs size n+1\n"
            "    for (int i=0;i<n;i++) parent[i]=i;\n"
            "    function<int(int)> find = [&](int x){\n"
            "        while (parent[x]!=x) x=parent[x];\n"
            "        return x;\n"
            "    };\n"
            "    int ansU=-1, ansV=-1;\n"
            "    for (int k=0;k<n;k++){\n"
            "        int u,v; cin>>u>>v;\n"
            "        int ru=find(u), rv=find(v);\n"
            "        if (ru==rv){ ansU=u; ansV=v; }\n"
            "        else parent[ru]=rv;\n"
            "    }\n"
            "    cout << ansU << \" \" << ansV << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "bug_category": "off_by_one",
        "bug_explanation_key_points": [
            "must identify that parent is sized n instead of n+1",
            "must explain nodes are labeled 1..n (1-indexed), so the highest-numbered node n needs a valid array slot at index n, which a size-n array doesn't have",
            "must connect this to a crash / out-of-bounds access on essentially every input, since node n always appears somewhere in the edge list",
        ],
    },
]

for _r in _RAW:
    if _r["id"] in _ROUND3_EXCLUDED_IDS:
        raise RuntimeError(f"ai_assisted_bank: {_r['id']!r} overlaps Round 3's debugging_bank pool -- selection error")
    if _r["id"] not in _PB_BANK_BY_ID:
        raise RuntimeError(f"ai_assisted_bank: {_r['id']!r} not found in problem_bank.py")
    if _r["bug_category"] not in BUG_CATEGORIES:
        raise RuntimeError(f"ai_assisted_bank: {_r['id']!r} has unknown bug_category {_r['bug_category']!r}")


def _hydrate(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Cheap assembly ONLY -- no execution, no compilation. Pulls base
    fields (statement/topic/difficulty/etc.) from problem_bank.py by id and
    layers the ai_assisted_variant on top. Deliberately kept free of any
    subprocess/compile cost at import time -- see verify_one()/verify_all()
    for the expensive, execution-based checks, which are opt-in only. This
    split is the same fix debugging_bank.py needed after its FIRST version
    made every server.py startup pay a ~27-minute compile-everything cost;
    doing it right from the start here rather than repeating that mistake.
    """
    pid = raw["id"]
    base = _PB_BANK_BY_ID[pid]
    return {
        "id": pid,
        "title": base["title"],
        "difficulty": base["difficulty"],
        "topic": base["topic"],
        "statement": base["statement"],
        "input_format": base["input_format"],
        "output_format": base["output_format"],
        "constraints": base["constraints"],
        "ai_assisted_variant": {
            "display_language": "cpp",
            "flawed_code": raw["flawed_code"],
            "corrected_code": raw["corrected_code"],
            "bug_category": raw["bug_category"],
            "bug_explanation_key_points": raw["bug_explanation_key_points"],
        },
    }


def verify_one(raw: Dict[str, Any]) -> None:
    """Actually compile+run the corrected and flawed C++ against this
    problem's existing problem_bank.py test_inputs (reused verbatim -- they
    are language-agnostic stdin/stdout pairs), using the Python
    reference_solution to derive expected output (same approach
    problem_bank.py's own _hydrate uses). Raises on any inconsistency.
    Callable on demand -- NOT run automatically at import (see _hydrate's
    docstring for why)."""
    import subprocess
    import tempfile
    import os

    pid = raw["id"]
    base_raw = next(r for r in _pb._RAW if r["id"] == pid)
    py_ref = base_raw["reference_solution"]
    test_inputs = base_raw["test_inputs"]

    def _run_py(stdin: str) -> str:
        with tempfile.TemporaryDirectory(prefix="ai_bank_verify_") as d:
            p = os.path.join(d, "main.py")
            with open(p, "w") as f:
                f.write(py_ref)
            proc = subprocess.run(["python3", p], input=stdin, capture_output=True, text=True, timeout=10)
            if proc.returncode != 0:
                raise RuntimeError(f"{pid}: python reference itself failed on {stdin!r}: {proc.stderr[:200]}")
            return (proc.stdout or "").strip()

    any_diff = False
    for stdin in test_inputs:
        expected = _run_py(stdin)
        ref_result = run_code("cpp", raw["corrected_code"], stdin, timeout=10)
        ref_got = (ref_result["stdout"] or "").strip()
        if ref_result["exit_code"] != 0 or ref_result["timed_out"] or ref_got != expected:
            raise RuntimeError(
                f"ai_assisted_bank: {pid!r} corrected_code MISMATCH on {stdin!r} "
                f"(expected={expected!r}, got={ref_got!r})"
            )
        flawed_result = run_code("cpp", raw["flawed_code"], stdin, timeout=10)
        flawed_got = (flawed_result["stdout"] or "").strip()
        if flawed_result["exit_code"] != 0 or flawed_result["timed_out"] or flawed_got != expected:
            any_diff = True
    if not any_diff:
        raise RuntimeError(f"ai_assisted_bank: {pid!r} flawed_code produces IDENTICAL output to the reference on every test_input -- not a real bug")


def verify_all() -> None:
    """Run verify_one() over the whole pool. Expensive (30 g++ compiles).
    Meant to be run explicitly (a standalone script, or a CI/deploy step),
    never as a side effect of importing this module."""
    for raw in _RAW:
        verify_one(raw)


# Materialize the pool at import time. Cheap -- see _hydrate's docstring.
_BANK: List[Dict[str, Any]] = [_hydrate(r) for r in _RAW]
_BANK_BY_ID: Dict[str, Dict[str, Any]] = {p["id"]: p for p in _BANK}
TOPICS: List[str] = sorted({p["topic"] for p in _BANK})


def get_problem(problem_id: str) -> Optional[Dict[str, Any]]:
    return _BANK_BY_ID.get(problem_id)


def all_problems() -> List[Dict[str, Any]]:
    return list(_BANK)


def bug_marker_line_range(flawed_code: str, context: int = 1) -> Dict[str, int]:
    """Finds the 1-indexed line containing this pool's "<--- " inline bug
    marker comment and returns a small {start, end} window around it (the
    real evidence's self-review prompt says "Review lines X through Y",
    implying a specific, meaningful range -- this derives one from the
    actual marker rather than inventing an arbitrary span or reviewing the
    whole snippet)."""
    lines = flawed_code.split("\n")
    marker_idx = next((i for i, l in enumerate(lines) if "<---" in l), None)
    if marker_idx is None:
        return {"start": 1, "end": len(lines)}
    start = max(1, marker_idx + 1 - context)
    end = min(len(lines), marker_idx + 1 + context)
    return {"start": start, "end": end}


# ---- Cross-attempt repetition tracking --------------------------------
# Same collection-shape/interface convention as debugging_bank.py's own
# get_seen_ids/mark_seen (itself modeled on problem_bank.py's tracker),
# deliberately kept in ITS OWN collection (ai_assisted_bank_seen) --
# Round 4 is a distinct ~15-item pool with its own "1 problem per session"
# draw rule, not a sub-split of either the 104-item coding bank or Round
# 3's 25-item debugging pool.
_db = None  # set by init(db)


def init(db) -> None:
    global _db
    _db = db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_seen_ids(user_id: str) -> Set[str]:
    if _db is None:
        return set()
    doc = await _db.ai_assisted_bank_seen.find_one({"user_id": user_id})
    return set(doc.get("question_ids", [])) if doc else set()


async def mark_seen(user_id: str, question_ids: List[str]) -> None:
    if _db is None or not question_ids:
        return
    await _db.ai_assisted_bank_seen.update_one(
        {"user_id": user_id},
        {"$addToSet": {"question_ids": {"$each": question_ids}}, "$set": {"updated_at": _now_iso()}},
        upsert=True,
    )


def sample_one(exclude_ids: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Draw exactly 1 problem for one Round 4 session (confirmed: 1 problem
    per session, unlike Round 3's 2). Falls back to allowing a repeat
    (same "never under-serve" philosophy as every other bank in this
    codebase) if excluding already-seen ids would leave nothing to draw."""
    pool = [p for p in _BANK if p["id"] not in (exclude_ids or set())]
    if not pool:
        pool = _BANK
    return random.choice(pool)


"""
============================================================================
PART 2 -- STAGE-GATING CONVERSATION DESIGN (schema/prompt-level only)
============================================================================
NOT implemented as live logic in this pass -- no LLM is called anywhere in
this module, no route exists for it, nothing here is wired into
companies.py. This section is a concrete, structured plan for a FUTURE
implementation pass to build against, so that pass doesn't have to invent
the stage machinery on the fly (per the explicit scope of this task).

Everything below (STAGE_ORDER, STAGE_CONFIG, CONSENT_GATE, SELF_REVIEW,
FINAL_SUMMARY_TEMPLATE) is DATA, not behavior -- a future
_generate_ai_assisted_reply()-style function would read these constants to
decide what to check for and what to say next, rather than each having its
prompt hand-authored inline in that function.
"""

# Every stage a session moves through, in order. "understand"/"approach"/
# "complexity" are free-text + LLM-gatekept; "consent" and "self_review"
# are button-driven (Yes/No), never free text; "explain_bug" is free-text +
# LLM-gatekept against that problem's bug_explanation_key_points;
# "complete" is a terminal, non-interactive display state.
STAGE_ORDER = (
    "understand",
    "approach",
    "complexity",
    "consent",
    "self_review",
    "explain_bug",
    "complete",
)

# Per free-text stage: what the LLM gate should check for before advancing,
# and the re-prompt template to use when the candidate's answer doesn't
# clear that bar. Tone matches the observed real evidence: polite,
# specific about what's missing, never harsh -- and re-prompts hold the
# candidate at the SAME stage (never silently advance on a weak answer,
# never fail the round outright for one weak attempt).
STAGE_CONFIG = {
    "understand": {
        "prompt_intro": (
            "Ask the candidate, in their own words, what the problem is asking "
            "them to do -- inputs, outputs, and any constraints that matter."
        ),
        "sufficiency_rubric": (
            "Sufficient if the answer restates the problem's actual goal using "
            "problem-specific technical terms (e.g. names the actual data "
            "structure/operation involved, not just 'find the answer'). "
            "INSUFFICIENT if it's generic/vague ('xyz', 'do the thing'), or if "
            "it tries to jump straight to a solution/code instead of "
            "demonstrating understanding of WHAT is being asked."
        ),
        "reprompt_examples": [
            "Could you elaborate a bit more using relevant technical terms or details?",
            "Please ensure your answer directly addresses the algorithmic concepts or structural conditions required.",
        ],
    },
    "approach": {
        "prompt_intro": (
            "Ask the candidate to describe, in their own words, the algorithmic "
            "strategy they'd use to solve it (not code -- the APPROACH)."
        ),
        "sufficiency_rubric": (
            "Sufficient if it names a real technique/data structure appropriate "
            "to the problem (e.g. 'two pointers', 'BFS', 'DP over prefix "
            "lengths') and roughly how it applies here. INSUFFICIENT if it's "
            "vague, restates the problem instead of a strategy, or names a "
            "technique with no indication of how/why it applies."
        ),
        "reprompt_examples": [
            "Could you elaborate a bit more using relevant technical terms or details?",
        ],
    },
    "complexity": {
        "prompt_intro": (
            "Ask the candidate to state the time and space complexity of "
            "their proposed approach -- ASKED AS ITS OWN STAGE even if they "
            "already mentioned it earlier (checklist-driven: this stage "
            "specifically requires both a time bound AND a space bound to be "
            "present in THIS answer)."
        ),
        "sufficiency_rubric": (
            "Sufficient only if both a time complexity AND a space complexity "
            "are explicitly stated (Big-O or equivalent informal phrasing is "
            "fine). INSUFFICIENT if only one is given, or neither."
        ),
        "reprompt_examples": [
            "Please ensure your answer directly addresses the algorithmic concepts or structural conditions required.",
        ],
    },
    "explain_bug": {
        "prompt_intro": (
            "Ask the candidate what specific logic error or missing condition "
            "exists in the generated code, once they've correctly flagged it "
            "as not ready to run."
        ),
        # Graded against THIS problem's own bug_explanation_key_points
        # (see _RAW above) rather than a generic rubric -- a future
        # implementation should pass ai_assisted_variant.bug_explanation_key_points
        # into the grading prompt for the drawn problem.
        "sufficiency_rubric": (
            "Sufficient only if the explanation names the ACTUAL defect (per "
            "that problem's bug_explanation_key_points) specifically -- which "
            "line/condition/comparison is wrong and why. INSUFFICIENT if it's "
            "generic ('something is wrong', 'it has a bug') without pointing "
            "at the real issue."
        ),
        "reprompt_examples": [
            "Good catch on flagging it -- but can you point to the specific line or condition that's wrong, and why?",
        ],
    },
}

# Button-driven stages -- fixed prompt text, Yes/No only, never free text.
CONSENT_GATE = {
    "prompt_template": (
        "Would you like me to generate a preliminary {language} solution "
        "based on your strategy in the code editor? (Yes / No)"
    ),
    "on_no": {
        "action": "hold_and_reprompt",
        "message": "Take your time. When you are ready, select 'Yes'.",
        "penalty": None,  # explicitly no penalty -- genuine candidate pacing control
    },
    "on_yes": {
        "action": "generate_flawed_code",
        # Pulls ai_assisted_variant.flawed_code for the language in
        # display_language (always "cpp" in this pool) and writes it into
        # the editor, verbatim, inline marker comment included.
    },
}

SELF_REVIEW = {
    "prompt_template": (
        "Review lines {start} through {end}. Is this implementation fully "
        "correct and ready to run? (Yes / No)"
    ),
    "on_no": {
        "action": "advance_to_explain_bug",
        "message": "Good catch! Please explain what specific logic error or missing condition exists.",
    },
    "on_yes": {
        # UNCONFIRMED / ASSUMED DEFAULT -- see module docstring's flagged
        # assumption. Never observed in the real evidence; this is a
        # reasonable placeholder for a future implementation to validate
        # against real behavior (or against product intent) before
        # treating it as settled.
        "action": "end_round_as_miss",
        "scored": False,  # candidate blindly accepted flawed code -> miss
        "still_shows_reference_solution": True,
        "assumption_flag": (
            "NOT OBSERVED IN REAL EVIDENCE. Round ends immediately, scored "
            "as a miss, reference solution is still displayed (same final "
            "summary as the correct path, minus credit). VERIFY before "
            "relying on this in a real implementation."
        ),
    },
}

FINAL_SUMMARY_TEMPLATE = {
    "heading": "All assessment steps complete! Displaying your comprehensive Solution and Reference Summary below...",
    "editor_label": "Reference Solution (Fixed)",
    "editor_content_source": "ai_assisted_variant.corrected_code",
    # Auto-completion trigger: fires the instant explain_bug's gate passes
    # (or immediately, per SELF_REVIEW.on_yes's assumed default) -- no
    # manual code-editing step, no separate submit button anywhere in this
    # round.
}
