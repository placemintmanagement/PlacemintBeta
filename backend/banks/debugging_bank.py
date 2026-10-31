"""Debugging Assessment (Round 3) problem pool.

Selected ~25 problems out of problem_bank.py's 104 (roughly 3 per topic
across all 8 topics), specifically chosen for being well-suited to
bug-injection and cleanly translatable across Python/C/C++/Java. This
module deliberately does NOT touch problem_bank.py -- it looks up each
selected problem's base fields (statement, topic, difficulty, and the
already-verified visible_tests/hidden_tests) by id from that module, and
layers multi-language reference solutions + bug-injected variants on top.

Test cases are reused verbatim from problem_bank.py: they're already
plain stdin -> stdout string pairs, so they're language-agnostic --  a
correct C/C++/Java translation must produce the exact same stdout for
the exact same stdin as the existing Python reference. No re-derivation
needed.

Same fail-fast philosophy as problem_bank.py: every reference solution
(all 4 languages) is actually executed against every one of its test
cases at import time via the real code_runner.run_code pipeline (the
same one used for live grading), and every buggy variant is checked to
pass at least one visible test and fail at least one hidden test, in
every language. Any inconsistency raises immediately at import, not
silently during a candidate's session.
"""
from __future__ import annotations
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from banks import problem_bank as _pb
from services.code_runner import run_code, run_tests

_PB_RAW_BY_ID: Dict[str, Dict[str, Any]] = {r["id"]: r for r in _pb._RAW}
_PB_BANK_BY_ID: Dict[str, Dict[str, Any]] = {p["id"]: p for p in _pb._BANK}

LANGUAGES = ["python", "c", "cpp", "java"]


_RAW: List[Dict[str, Any]] = [
    {
        "id": 'two-sum',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\n#define SZ 200003\nlong long keys[SZ]; int vals[SZ]; int used[SZ];\nunsigned long hh(long long x){ unsigned long long ux=(unsigned long long)x; return (ux*2654435761ULL)%SZ; }\nint slot_of(long long x){ unsigned long idx=hh(x); while(used[idx] && keys[idx]!=x) idx=(idx+1)%SZ; return idx; }\nint main(void){\n    int n; scanf("%d",&n);\n    long long *a=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&a[i]);\n    long long t; scanf("%lld",&t);\n    for(int i=0;i<n;i++){\n        long long need=t-a[i];\n        int s=slot_of(need);\n        if(used[s]){ printf("%d %d\\n", vals[s], i); return 0; }\n        int s2=slot_of(a[i]);\n        keys[s2]=a[i]; vals[s2]=i; used[s2]=1;\n    }\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> a(n);\n    for(auto&x:a) cin>>x;\n    long long t; cin>>t;\n    unordered_map<long long,int> seen;\n    for(int i=0;i<n;i++){\n        long long need=t-a[i];\n        auto it=seen.find(need);\n        if(it!=seen.end()){ cout<<it->second<<" "<<i<<"\\n"; return 0; }\n        seen[a[i]]=i;\n    }\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] a = new long[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n        long t = sc.nextLong();\n        Map<Long, Integer> seen = new HashMap<>();\n        for (int i = 0; i < n; i++) {\n            long need = t - a[i];\n            if (seen.containsKey(need)) { System.out.println(seen.get(need) + " " + i); return; }\n            seen.put(a[i], i);\n        }\n    }\n}\n',
        },
        "buggy": {
            'python': 'n = int(input())\na = list(map(int, input().split()))\nt = int(input())\nseen = {}\nfor i in range(1, n):\n    v = a[i]\n    if t - v in seen:\n        print(seen[t - v], i); break\n    seen[v] = i\n',
            'c': '#include <stdio.h>\n#include <stdlib.h>\n#define SZ 200003\nlong long keys[SZ]; int vals[SZ]; int used[SZ];\nunsigned long hh(long long x){ unsigned long long ux=(unsigned long long)x; return (ux*2654435761ULL)%SZ; }\nint slot_of(long long x){ unsigned long idx=hh(x); while(used[idx] && keys[idx]!=x) idx=(idx+1)%SZ; return idx; }\nint main(void){\n    int n; scanf("%d",&n);\n    long long *a=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&a[i]);\n    long long t; scanf("%lld",&t);\n    for(int i=1;i<n;i++){\n        long long need=t-a[i];\n        int s=slot_of(need);\n        if(used[s]){ printf("%d %d\\n", vals[s], i); return 0; }\n        int s2=slot_of(a[i]);\n        keys[s2]=a[i]; vals[s2]=i; used[s2]=1;\n    }\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> a(n);\n    for(auto&x:a) cin>>x;\n    long long t; cin>>t;\n    unordered_map<long long,int> seen;\n    for(int i=1;i<n;i++){\n        long long need=t-a[i];\n        auto it=seen.find(need);\n        if(it!=seen.end()){ cout<<it->second<<" "<<i<<"\\n"; return 0; }\n        seen[a[i]]=i;\n    }\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] a = new long[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n        long t = sc.nextLong();\n        Map<Long, Integer> seen = new HashMap<>();\n        for (int i = 1; i < n; i++) {\n            long need = t - a[i];\n            if (seen.containsKey(need)) { System.out.println(seen.get(need) + " " + i); return; }\n            seen.put(a[i], i);\n        }\n    }\n}\n',
        },
        "bug_category": 'off_by_one',
        "task_description": "This solution should return the indices of the two numbers that add up to the target, but it's returning nothing on some inputs. Find and fix the bug.",
    },
    {
        "id": 'max-subarray-sum',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *a=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&a[i]);\n    long long best=a[0], cur=a[0];\n    for(int i=1;i<n;i++){\n        long long x=a[i];\n        cur = (x > cur+x) ? x : cur+x;\n        if (cur>best) best=cur;\n    }\n    printf("%lld\\n", best);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> a(n);\n    for(auto&x:a) cin>>x;\n    long long best=a[0], cur=a[0];\n    for(int i=1;i<n;i++){\n        long long x=a[i];\n        cur = max(x, cur+x);\n        best = max(best, cur);\n    }\n    cout<<best<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] a = new long[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n        long best = a[0], cur = a[0];\n        for (int i = 1; i < n; i++) {\n            long x = a[i];\n            cur = Math.max(x, cur + x);\n            best = Math.max(best, cur);\n        }\n        System.out.println(best);\n    }\n}\n',
        },
        "buggy": {
            'python': 'n = int(input())\na = list(map(int, input().split()))\nbest = 0\ncur = 0\nfor x in a:\n    cur = max(x, cur + x)\n    best = max(best, cur)\nprint(best)\n',
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *a=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&a[i]);\n    long long best=0, cur=0;\n    for(int i=0;i<n;i++){\n        long long x=a[i];\n        cur = (x > cur+x) ? x : cur+x;\n        if (cur>best) best=cur;\n    }\n    printf("%lld\\n", best);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> a(n);\n    for(auto&x:a) cin>>x;\n    long long best=0, cur=0;\n    for(int i=0;i<n;i++){\n        long long x=a[i];\n        cur = max(x, cur+x);\n        best = max(best, cur);\n    }\n    cout<<best<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] a = new long[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n        long best = 0, cur = 0;\n        for (int i = 0; i < n; i++) {\n            long x = a[i];\n            cur = Math.max(x, cur + x);\n            best = Math.max(best, cur);\n        }\n        System.out.println(best);\n    }\n}\n',
        },
        "bug_category": 'incomplete_boundary_handling',
        "task_description": "This Kadane's-algorithm solution assumes the best subarray sum can never be negative, so it initializes its running best to 0 instead of the first element. It gives correct answers whenever the true answer is positive, but breaks for all-negative arrays. Find and fix the bug.",
    },
    {
        "id": 'arr-majority-element',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *a=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&a[i]);\n    long long count=0, candidate=0;\n    for(int i=0;i<n;i++){\n        if(count==0) candidate=a[i];\n        count += (a[i]==candidate) ? 1 : -1;\n    }\n    printf("%lld\\n", candidate);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> a(n);\n    for(auto&x:a) cin>>x;\n    long long count=0, candidate=0;\n    for(int i=0;i<n;i++){\n        if(count==0) candidate=a[i];\n        count += (a[i]==candidate) ? 1 : -1;\n    }\n    cout<<candidate<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] a = new long[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n        long count = 0, candidate = 0;\n        for (int i = 0; i < n; i++) {\n            if (count == 0) candidate = a[i];\n            count += (a[i] == candidate) ? 1 : -1;\n        }\n        System.out.println(candidate);\n    }\n}\n',
        },
        "buggy": {
            'python': 'n = int(input())\na = list(map(int, input().split()))\ncount = 0\ncandidate = a[0]\nfor x in a:\n    count += 1 if x == candidate else -1\n    if count == 0:\n        candidate = x\nprint(candidate)\n',
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *a=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&a[i]);\n    long long count=0, candidate=a[0];\n    for(int i=0;i<n;i++){\n        count += (a[i]==candidate) ? 1 : -1;\n        if(count==0) candidate=a[i];\n    }\n    printf("%lld\\n", candidate);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> a(n);\n    for(auto&x:a) cin>>x;\n    long long count=0, candidate=a[0];\n    for(int i=0;i<n;i++){\n        count += (a[i]==candidate) ? 1 : -1;\n        if(count==0) candidate=a[i];\n    }\n    cout<<candidate<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] a = new long[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n        long count = 0, candidate = a[0];\n        for (int i = 0; i < n; i++) {\n            count += (a[i] == candidate) ? 1 : -1;\n            if (count == 0) candidate = a[i];\n        }\n        System.out.println(candidate);\n    }\n}\n',
        },
        "bug_category": 'state_tracking_error',
        "task_description": 'This Boyer-Moore voting solution presets the candidate to the first element and checks the reset condition AFTER updating the count instead of before, which can trigger a premature candidate reset. Find and fix the bug.',
    },
    {
        "id": 'string-valid-anagram',
        "ref": {
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\nint cmpchar(const void*a,const void*b){ return (*(unsigned char*)a)-(*(unsigned char*)b); }\nint main(void){\n    char a[100005], b[100005];\n    if(!fgets(a,sizeof(a),stdin)) a[0]=0;\n    if(!fgets(b,sizeof(b),stdin)) b[0]=0;\n    a[strcspn(a,"\\r\\n")]=0;\n    b[strcspn(b,"\\r\\n")]=0;\n    int la=strlen(a), lb=strlen(b);\n    if(la!=lb){ printf("NO\\n"); return 0; }\n    qsort(a,la,1,cmpchar); qsort(b,lb,1,cmpchar);\n    printf("%s\\n", strcmp(a,b)==0 ? "YES":"NO");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    string a, b;\n    getline(cin, a);\n    getline(cin, b);\n    sort(a.begin(), a.end());\n    sort(b.begin(), b.end());\n    cout << (a == b ? "YES" : "NO") << "\\n";\n    return 0;\n}\n',
            'java': 'import java.io.*;\nimport java.util.*;\npublic class Main {\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String a = br.readLine(); if (a == null) a = "";\n        String b = br.readLine(); if (b == null) b = "";\n        char[] ca = a.toCharArray(), cb = b.toCharArray();\n        Arrays.sort(ca); Arrays.sort(cb);\n        System.out.println(Arrays.equals(ca, cb) ? "YES" : "NO");\n    }\n}\n',
        },
        "buggy": {
            'python': "a = input()\nb = input()\nif not a or not b:\n    print('NO')\nelse:\n    print('YES' if sorted(a) == sorted(b) else 'NO')\n",
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\nint cmpchar(const void*a,const void*b){ return (*(unsigned char*)a)-(*(unsigned char*)b); }\nint main(void){\n    char a[100005], b[100005];\n    if(!fgets(a,sizeof(a),stdin)) a[0]=0;\n    if(!fgets(b,sizeof(b),stdin)) b[0]=0;\n    a[strcspn(a,"\\r\\n")]=0;\n    b[strcspn(b,"\\r\\n")]=0;\n    int la=strlen(a), lb=strlen(b);\n    if(la==0 || lb==0){ printf("NO\\n"); return 0; }\n    if(la!=lb){ printf("NO\\n"); return 0; }\n    qsort(a,la,1,cmpchar); qsort(b,lb,1,cmpchar);\n    printf("%s\\n", strcmp(a,b)==0 ? "YES":"NO");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    string a, b;\n    getline(cin, a);\n    getline(cin, b);\n    if (a.empty() || b.empty()) { cout << "NO\\n"; return 0; }\n    sort(a.begin(), a.end());\n    sort(b.begin(), b.end());\n    cout << (a == b ? "YES" : "NO") << "\\n";\n    return 0;\n}\n',
            'java': 'import java.io.*;\nimport java.util.*;\npublic class Main {\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String a = br.readLine(); if (a == null) a = "";\n        String b = br.readLine(); if (b == null) b = "";\n        if (a.isEmpty() || b.isEmpty()) { System.out.println("NO"); return; }\n        char[] ca = a.toCharArray(), cb = b.toCharArray();\n        Arrays.sort(ca); Arrays.sort(cb);\n        System.out.println(Arrays.equals(ca, cb) ? "YES" : "NO");\n    }\n}\n',
        },
        "bug_category": 'missing_edge_case',
        "task_description": 'This anagram check special-cases empty input but gets it backwards: it prints NO whenever either string is empty, even though two empty strings ARE anagrams of each other (both being the empty multiset). Find and fix the bug.',
    },
    {
        "id": 'group-anagrams',
        "ref": {
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\nint cmpchar(const void*a,const void*b){ return (*(unsigned char*)a)-(*(unsigned char*)b); }\nint main(void){\n    int n; scanf("%d",&n);\n    char (*words)[105] = malloc(sizeof(char[105]) * (n>0?n:1));\n    for(int i=0;i<n;i++) scanf("%s", words[i]);\n    char (*sortedw)[105] = malloc(sizeof(char[105]) * (n>0?n:1));\n    for(int i=0;i<n;i++){\n        strcpy(sortedw[i], words[i]);\n        qsort(sortedw[i], strlen(sortedw[i]), 1, cmpchar);\n    }\n    int *used = calloc(n>0?n:1, sizeof(int));\n    int groups=0;\n    for(int i=0;i<n;i++){\n        if(used[i]) continue;\n        groups++;\n        used[i]=1;\n        for(int j=i+1;j<n;j++){\n            if(!used[j] && strcmp(sortedw[i],sortedw[j])==0) used[j]=1;\n        }\n    }\n    printf("%d\\n", groups);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<string> words(n);\n    for(auto&w:words) cin>>w;\n    vector<string> sortedw(n);\n    for(int i=0;i<n;i++){ sortedw[i]=words[i]; sort(sortedw[i].begin(), sortedw[i].end()); }\n    vector<int> used(n,0);\n    int groups=0;\n    for(int i=0;i<n;i++){\n        if(used[i]) continue;\n        groups++; used[i]=1;\n        for(int j=i+1;j<n;j++){\n            if(!used[j] && sortedw[i]==sortedw[j]) used[j]=1;\n        }\n    }\n    cout<<groups<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        String[] words = new String[n];\n        for (int i = 0; i < n; i++) words[i] = sc.next();\n        String[] sortedw = new String[n];\n        for (int i = 0; i < n; i++) {\n            char[] c = words[i].toCharArray();\n            Arrays.sort(c);\n            sortedw[i] = new String(c);\n        }\n        boolean[] used = new boolean[n];\n        int groups = 0;\n        for (int i = 0; i < n; i++) {\n            if (used[i]) continue;\n            groups++; used[i] = true;\n            for (int j = i + 1; j < n; j++) {\n                if (!used[j] && sortedw[i].equals(sortedw[j])) used[j] = true;\n            }\n        }\n        System.out.println(groups);\n    }\n}\n',
        },
        "buggy": {
            'python': 'n = int(input())\nwords = input().split()\ngroups = []\nused = [False] * len(words)\nfor i in range(len(words)):\n    if used[i]:\n        continue\n    groups.append(words[i])\n    for j in range(i + 1, len(words)):\n        if sorted(words[i]) == sorted(words[j]):\n            pass\nprint(len(groups))\n',
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\nint cmpchar(const void*a,const void*b){ return (*(unsigned char*)a)-(*(unsigned char*)b); }\nint main(void){\n    int n; scanf("%d",&n);\n    char (*words)[105] = malloc(sizeof(char[105]) * (n>0?n:1));\n    for(int i=0;i<n;i++) scanf("%s", words[i]);\n    char (*sortedw)[105] = malloc(sizeof(char[105]) * (n>0?n:1));\n    for(int i=0;i<n;i++){\n        strcpy(sortedw[i], words[i]);\n        qsort(sortedw[i], strlen(sortedw[i]), 1, cmpchar);\n    }\n    int *used = calloc(n>0?n:1, sizeof(int));\n    int groups=0;\n    for(int i=0;i<n;i++){\n        if(used[i]) continue;\n        groups++;\n        used[i]=1;\n        for(int j=i+1;j<n;j++){\n            if(!used[j] && strcmp(sortedw[i],sortedw[j])==0) { /* BUG: forgot used[j]=1 */ }\n        }\n    }\n    printf("%d\\n", groups);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<string> words(n);\n    for(auto&w:words) cin>>w;\n    vector<string> sortedw(n);\n    for(int i=0;i<n;i++){ sortedw[i]=words[i]; sort(sortedw[i].begin(), sortedw[i].end()); }\n    vector<int> used(n,0);\n    int groups=0;\n    for(int i=0;i<n;i++){\n        if(used[i]) continue;\n        groups++; used[i]=1;\n        for(int j=i+1;j<n;j++){\n            if(!used[j] && sortedw[i]==sortedw[j]) { /* BUG: forgot used[j]=1 */ }\n        }\n    }\n    cout<<groups<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        String[] words = new String[n];\n        for (int i = 0; i < n; i++) words[i] = sc.next();\n        String[] sortedw = new String[n];\n        for (int i = 0; i < n; i++) {\n            char[] c = words[i].toCharArray();\n            Arrays.sort(c);\n            sortedw[i] = new String(c);\n        }\n        boolean[] used = new boolean[n];\n        int groups = 0;\n        for (int i = 0; i < n; i++) {\n            if (used[i]) continue;\n            groups++; used[i] = true;\n            for (int j = i + 1; j < n; j++) {\n                if (!used[j] && sortedw[i].equals(sortedw[j])) { /* BUG: forgot used[j]=true */ }\n            }\n        }\n        System.out.println(groups);\n    }\n}\n',
        },
        "bug_category": 'state_tracking_error',
        "task_description": "This solution is supposed to count distinct anagram groups, but it forgets to mark a matched word as 'used' once it's grouped with an earlier word -- so that word gets re-counted as the start of its own group later. Find and fix the bug.",
    },
    {
        "id": 'string-roman-to-integer',
        "ref": {
            'c': '#include <stdio.h>\n#include <string.h>\nint val(char c){\n    switch(c){case \'I\':return 1;case \'V\':return 5;case \'X\':return 10;case \'L\':return 50;case \'C\':return 100;case \'D\':return 500;case \'M\':return 1000;}\n    return 0;\n}\nint main(void){\n    char s[20];\n    scanf("%s", s);\n    int n=strlen(s);\n    long long total=0, prev=0;\n    for(int i=n-1;i>=0;i--){\n        long long v=val(s[i]);\n        if(v<prev) total-=v; else { total+=v; prev=v; }\n    }\n    printf("%lld\\n", total);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nlong long val(char c){\n    switch(c){case \'I\':return 1;case \'V\':return 5;case \'X\':return 10;case \'L\':return 50;case \'C\':return 100;case \'D\':return 500;case \'M\':return 1000;}\n    return 0;\n}\nint main(){\n    string s; cin>>s;\n    long long total=0, prev=0;\n    for(int i=(int)s.size()-1;i>=0;i--){\n        long long v=val(s[i]);\n        if(v<prev) total-=v; else { total+=v; prev=v; }\n    }\n    cout<<total<<"\\n";\n    return 0;\n}\n',
            'java': "import java.util.*;\npublic class Main {\n    static long val(char c){\n        switch(c){case 'I':return 1;case 'V':return 5;case 'X':return 10;case 'L':return 50;case 'C':return 100;case 'D':return 500;case 'M':return 1000;}\n        return 0;\n    }\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        String s = sc.next();\n        long total = 0, prev = 0;\n        for (int i = s.length() - 1; i >= 0; i--) {\n            long v = val(s.charAt(i));\n            if (v < prev) total -= v; else { total += v; prev = v; }\n        }\n        System.out.println(total);\n    }\n}\n",
        },
        "buggy": {
            'python': "s = input()\nvals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}\ntotal = 0\ni = 0\nwhile i < len(s):\n    if i + 1 < len(s) and vals[s[i]] < vals[s[i + 1]]:\n        total += vals[s[i + 1]] - vals[s[i]]\n        i += 1\n    else:\n        total += vals[s[i]]\n        i += 1\nprint(total)\n",
            'c': '#include <stdio.h>\n#include <string.h>\nint val(char c){\n    switch(c){case \'I\':return 1;case \'V\':return 5;case \'X\':return 10;case \'L\':return 50;case \'C\':return 100;case \'D\':return 500;case \'M\':return 1000;}\n    return 0;\n}\nint main(void){\n    char s[20];\n    scanf("%s", s);\n    int n=strlen(s);\n    long long total=0;\n    int i=0;\n    while(i<n){\n        if(i+1<n && val(s[i])<val(s[i+1])){\n            total += val(s[i+1]) - val(s[i]);\n            i += 1;\n        } else {\n            total += val(s[i]);\n            i += 1;\n        }\n    }\n    printf("%lld\\n", total);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nlong long val(char c){\n    switch(c){case \'I\':return 1;case \'V\':return 5;case \'X\':return 10;case \'L\':return 50;case \'C\':return 100;case \'D\':return 500;case \'M\':return 1000;}\n    return 0;\n}\nint main(){\n    string s; cin>>s;\n    int n=(int)s.size();\n    long long total=0;\n    int i=0;\n    while(i<n){\n        if(i+1<n && val(s[i])<val(s[i+1])){\n            total += val(s[i+1]) - val(s[i]);\n            i += 1;\n        } else {\n            total += val(s[i]);\n            i += 1;\n        }\n    }\n    cout<<total<<"\\n";\n    return 0;\n}\n',
            'java': "import java.util.*;\npublic class Main {\n    static long val(char c){\n        switch(c){case 'I':return 1;case 'V':return 5;case 'X':return 10;case 'L':return 50;case 'C':return 100;case 'D':return 500;case 'M':return 1000;}\n        return 0;\n    }\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        String s = sc.next();\n        int n = s.length();\n        long total = 0;\n        int i = 0;\n        while (i < n) {\n            if (i + 1 < n && val(s.charAt(i)) < val(s.charAt(i + 1))) {\n                total += val(s.charAt(i + 1)) - val(s.charAt(i));\n                i += 1;\n            } else {\n                total += val(s.charAt(i));\n                i += 1;\n            }\n        }\n        System.out.println(total);\n    }\n}\n",
        },
        "bug_category": 'off_by_one',
        "task_description": 'This forward-scanning Roman numeral parser handles the subtractive case (like IV or IX) but only advances the index by 1 after consuming both characters, instead of 2 -- so the second character gets reprocessed. Find and fix the bug.',
    },
    {
        "id": 'buy-sell-stock',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *a=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&a[i]);\n    long long best=0, lo=a[0];\n    for(int i=0;i<n;i++){\n        if(a[i]<lo) lo=a[i];\n        long long profit=a[i]-lo;\n        if(profit>best) best=profit;\n    }\n    printf("%lld\\n", best);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> a(n);\n    for(auto&x:a) cin>>x;\n    long long best=0, lo=a[0];\n    for(int i=0;i<n;i++){\n        lo=min(lo,a[i]);\n        best=max(best, a[i]-lo);\n    }\n    cout<<best<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] a = new long[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n        long best = 0, lo = a[0];\n        for (int i = 0; i < n; i++) {\n            lo = Math.min(lo, a[i]);\n            best = Math.max(best, a[i] - lo);\n        }\n        System.out.println(best);\n    }\n}\n',
        },
        "buggy": {
            'python': 'n = int(input())\na = list(map(int, input().split()))\nbest = 0\nlo = a[0]\nfor x in a:\n    lo = min(lo, x)\n    best = max(best, lo - x)\nprint(best)\n',
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *a=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&a[i]);\n    long long best=0, lo=a[0];\n    for(int i=0;i<n;i++){\n        if(a[i]<lo) lo=a[i];\n        long long profit=lo-a[i];\n        if(profit>best) best=profit;\n    }\n    printf("%lld\\n", best);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> a(n);\n    for(auto&x:a) cin>>x;\n    long long best=0, lo=a[0];\n    for(int i=0;i<n;i++){\n        lo=min(lo,a[i]);\n        best=max(best, lo-a[i]);\n    }\n    cout<<best<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] a = new long[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n        long best = 0, lo = a[0];\n        for (int i = 0; i < n; i++) {\n            lo = Math.min(lo, a[i]);\n            best = Math.max(best, lo - a[i]);\n        }\n        System.out.println(best);\n    }\n}\n',
        },
        "bug_category": 'wrong_variable_reference',
        "task_description": "This solution should track (today's price) minus (lowest price seen so far), but the subtraction is backwards -- it computes (lowest price so far) minus (today's price). Find and fix the bug.",
    },
    {
        "id": 'greedy-merge-intervals',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\ntypedef struct { long long s,e; } Iv;\nint cmp_start(const void*a,const void*b){ Iv*x=(Iv*)a,*y=(Iv*)b; return (x->s>y->s)-(x->s<y->s); }\nint main(void){\n    int n; scanf("%d",&n);\n    Iv *iv=malloc(sizeof(Iv)*n);\n    for(int i=0;i<n;i++) scanf("%lld %lld",&iv[i].s,&iv[i].e);\n    qsort(iv,n,sizeof(Iv),cmp_start);\n    Iv *merged=malloc(sizeof(Iv)*n);\n    int m=0;\n    for(int i=0;i<n;i++){\n        if(m>0 && iv[i].s<=merged[m-1].e){\n            if(iv[i].e>merged[m-1].e) merged[m-1].e=iv[i].e;\n        } else {\n            merged[m].s=iv[i].s; merged[m].e=iv[i].e; m++;\n        }\n    }\n    for(int i=0;i<m;i++) printf("%lld %lld\\n", merged[i].s, merged[i].e);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<pair<long long,long long>> iv(n);\n    for(auto&p:iv) cin>>p.first>>p.second;\n    sort(iv.begin(), iv.end());\n    vector<pair<long long,long long>> merged;\n    for(auto&p:iv){\n        if(!merged.empty() && p.first<=merged.back().second){\n            merged.back().second = max(merged.back().second, p.second);\n        } else {\n            merged.push_back(p);\n        }\n    }\n    for(auto&p:merged) cout<<p.first<<" "<<p.second<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[][] iv = new long[n][2];\n        for (int i = 0; i < n; i++) { iv[i][0] = sc.nextLong(); iv[i][1] = sc.nextLong(); }\n        Arrays.sort(iv, (a, b) -> Long.compare(a[0], b[0]));\n        List<long[]> merged = new ArrayList<>();\n        for (long[] p : iv) {\n            if (!merged.isEmpty() && p[0] <= merged.get(merged.size() - 1)[1]) {\n                long[] last = merged.get(merged.size() - 1);\n                last[1] = Math.max(last[1], p[1]);\n            } else {\n                merged.add(new long[]{p[0], p[1]});\n            }\n        }\n        StringBuilder sb = new StringBuilder();\n        for (long[] p : merged) sb.append(p[0]).append(" ").append(p[1]).append("\\n");\n        System.out.print(sb);\n    }\n}\n',
        },
        "buggy": {
            'python': 'n = int(input())\nivs = [tuple(map(int, input().split())) for _ in range(n)]\nivs.sort(key=lambda p: p[1])\nmerged = []\nfor s, e in ivs:\n    if merged and s <= merged[-1][1]:\n        merged[-1] = (merged[-1][0], max(merged[-1][1], e))\n    else:\n        merged.append((s, e))\nmerged.sort()\nfor s, e in merged:\n    print(s, e)\n',
            'c': '#include <stdio.h>\n#include <stdlib.h>\ntypedef struct { long long s,e; int idx; } Iv;\nint cmp_end(const void*a,const void*b){\n    Iv*x=(Iv*)a,*y=(Iv*)b;\n    if(x->e!=y->e) return (x->e>y->e)-(x->e<y->e);\n    return x->idx-y->idx;\n}\nint cmp_start(const void*a,const void*b){ Iv*x=(Iv*)a,*y=(Iv*)b; return (x->s>y->s)-(x->s<y->s); }\nint main(void){\n    int n; scanf("%d",&n);\n    Iv *iv=malloc(sizeof(Iv)*n);\n    for(int i=0;i<n;i++){ scanf("%lld %lld",&iv[i].s,&iv[i].e); iv[i].idx=i; }\n    qsort(iv,n,sizeof(Iv),cmp_end);\n    Iv *merged=malloc(sizeof(Iv)*n);\n    int m=0;\n    for(int i=0;i<n;i++){\n        if(m>0 && iv[i].s<=merged[m-1].e){\n            if(iv[i].e>merged[m-1].e) merged[m-1].e=iv[i].e;\n        } else {\n            merged[m].s=iv[i].s; merged[m].e=iv[i].e; m++;\n        }\n    }\n    qsort(merged,m,sizeof(Iv),cmp_start);\n    for(int i=0;i<m;i++) printf("%lld %lld\\n", merged[i].s, merged[i].e);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<pair<long long,long long>> iv(n);\n    for(auto&p:iv) cin>>p.first>>p.second;\n    stable_sort(iv.begin(), iv.end(), [](auto&a, auto&b){ return a.second < b.second; });\n    vector<pair<long long,long long>> merged;\n    for(auto&p:iv){\n        if(!merged.empty() && p.first<=merged.back().second){\n            merged.back().second = max(merged.back().second, p.second);\n        } else {\n            merged.push_back(p);\n        }\n    }\n    sort(merged.begin(), merged.end());\n    for(auto&p:merged) cout<<p.first<<" "<<p.second<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[][] iv = new long[n][2];\n        for (int i = 0; i < n; i++) { iv[i][0] = sc.nextLong(); iv[i][1] = sc.nextLong(); }\n        Arrays.sort(iv, (a, b) -> Long.compare(a[1], b[1]));\n        List<long[]> merged = new ArrayList<>();\n        for (long[] p : iv) {\n            if (!merged.isEmpty() && p[0] <= merged.get(merged.size() - 1)[1]) {\n                long[] last = merged.get(merged.size() - 1);\n                last[1] = Math.max(last[1], p[1]);\n            } else {\n                merged.add(new long[]{p[0], p[1]});\n            }\n        }\n        merged.sort((a, b) -> Long.compare(a[0], b[0]));\n        StringBuilder sb = new StringBuilder();\n        for (long[] p : merged) sb.append(p[0]).append(" ").append(p[1]).append("\\n");\n        System.out.print(sb);\n    }\n}\n',
        },
        "bug_category": 'wrong_variable_reference',
        "task_description": 'This interval-merging solution sorts the intervals by END instead of by START before scanning for overlaps (the final output is re-sorted by start, so it looks right at a glance). Find and fix the bug.',
    },
    {
        "id": 'greedy-gas-station',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *gas=malloc(sizeof(long long)*n), *cost=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&gas[i]);\n    for(int i=0;i<n;i++) scanf("%lld",&cost[i]);\n    long long tank=0; int start=0;\n    for(int i=0;i<n;i++){\n        tank += gas[i]-cost[i];\n        if(tank<0){ start=i+1; tank=0; }\n    }\n    printf("%d\\n", start);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> gas(n), cost(n);\n    for(auto&x:gas) cin>>x;\n    for(auto&x:cost) cin>>x;\n    long long tank=0; int start=0;\n    for(int i=0;i<n;i++){\n        tank += gas[i]-cost[i];\n        if(tank<0){ start=i+1; tank=0; }\n    }\n    cout<<start<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] gas = new long[n], cost = new long[n];\n        for (int i = 0; i < n; i++) gas[i] = sc.nextLong();\n        for (int i = 0; i < n; i++) cost[i] = sc.nextLong();\n        long tank = 0; int start = 0;\n        for (int i = 0; i < n; i++) {\n            tank += gas[i] - cost[i];\n            if (tank < 0) { start = i + 1; tank = 0; }\n        }\n        System.out.println(start);\n    }\n}\n',
        },
        "buggy": {
            'python': 'n = int(input())\ngas = list(map(int, input().split()))\ncost = list(map(int, input().split()))\ntank = 0\nstart = 0\nfor i in range(n):\n    tank += gas[i] - cost[i]\n    if tank <= 0:\n        start = i + 1\n        tank = 0\nprint(start)\n',
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *gas=malloc(sizeof(long long)*n), *cost=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&gas[i]);\n    for(int i=0;i<n;i++) scanf("%lld",&cost[i]);\n    long long tank=0; int start=0;\n    for(int i=0;i<n;i++){\n        tank += gas[i]-cost[i];\n        if(tank<=0){ start=i+1; tank=0; }\n    }\n    printf("%d\\n", start);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> gas(n), cost(n);\n    for(auto&x:gas) cin>>x;\n    for(auto&x:cost) cin>>x;\n    long long tank=0; int start=0;\n    for(int i=0;i<n;i++){\n        tank += gas[i]-cost[i];\n        if(tank<=0){ start=i+1; tank=0; }\n    }\n    cout<<start<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] gas = new long[n], cost = new long[n];\n        for (int i = 0; i < n; i++) gas[i] = sc.nextLong();\n        for (int i = 0; i < n; i++) cost[i] = sc.nextLong();\n        long tank = 0; int start = 0;\n        for (int i = 0; i < n; i++) {\n            tank += gas[i] - cost[i];\n            if (tank <= 0) { start = i + 1; tank = 0; }\n        }\n        System.out.println(start);\n    }\n}\n',
        },
        "bug_category": 'wrong_comparison_operator',
        "task_description": 'This solution resets the starting station whenever the tank drops to zero or below, but it should only reset when the tank goes strictly negative -- exactly-zero is still a valid running total. Find and fix the bug.',
    },
    {
        "id": 'greedy-jump-game',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *a=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&a[i]);\n    long long reach=0; int ok=1;\n    for(int i=0;i<n;i++){\n        if(i>reach){ ok=0; break; }\n        long long r=i+a[i];\n        if(r>reach) reach=r;\n    }\n    printf("%s\\n", ok?"YES":"NO");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> a(n);\n    for(auto&x:a) cin>>x;\n    long long reach=0; bool ok=true;\n    for(int i=0;i<n;i++){\n        if(i>reach){ ok=false; break; }\n        reach=max(reach, (long long)i+a[i]);\n    }\n    cout<<(ok?"YES":"NO")<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] a = new long[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n        long reach = 0; boolean ok = true;\n        for (int i = 0; i < n; i++) {\n            if (i > reach) { ok = false; break; }\n            reach = Math.max(reach, i + a[i]);\n        }\n        System.out.println(ok ? "YES" : "NO");\n    }\n}\n',
        },
        "buggy": {
            'python': "n = int(input())\na = list(map(int, input().split()))\nreach = 0\nok = True\nfor i in range(n):\n    if i >= reach:\n        ok = False\n        break\n    reach = max(reach, i + a[i])\nprint('YES' if ok else 'NO')\n",
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *a=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&a[i]);\n    long long reach=0; int ok=1;\n    for(int i=0;i<n;i++){\n        if(i>=reach){ ok=0; break; }\n        long long r=i+a[i];\n        if(r>reach) reach=r;\n    }\n    printf("%s\\n", ok?"YES":"NO");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> a(n);\n    for(auto&x:a) cin>>x;\n    long long reach=0; bool ok=true;\n    for(int i=0;i<n;i++){\n        if(i>=reach){ ok=false; break; }\n        reach=max(reach, (long long)i+a[i]);\n    }\n    cout<<(ok?"YES":"NO")<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] a = new long[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n        long reach = 0; boolean ok = true;\n        for (int i = 0; i < n; i++) {\n            if (i >= reach) { ok = false; break; }\n            reach = Math.max(reach, i + a[i]);\n        }\n        System.out.println(ok ? "YES" : "NO");\n    }\n}\n',
        },
        "bug_category": 'wrong_comparison_operator',
        "task_description": 'This solution declares failure as soon as the current index reaches the furthest known reach, but landing exactly ON the reach boundary is fine -- only going PAST it is a failure. Find and fix the bug.',
    },
    {
        "id": 'valid-palindrome',
        "ref": {
            'c': '#include <stdio.h>\n#include <string.h>\n#include <ctype.h>\nint main(void){\n    char line[100005];\n    if(!fgets(line,sizeof(line),stdin)) line[0]=0;\n    line[strcspn(line,"\\r\\n")]=0;\n    int n=strlen(line);\n    char buf[100005]; int m=0;\n    for(int i=0;i<n;i++){\n        if(isalnum((unsigned char)line[i])) buf[m++]=tolower((unsigned char)line[i]);\n    }\n    int l=0,r=m-1,ok=1;\n    while(l<r){ if(buf[l]!=buf[r]){ok=0;break;} l++; r--; }\n    printf("%s\\n", ok?"YES":"NO");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    string line;\n    getline(cin, line);\n    string buf;\n    for(char c: line) if(isalnum((unsigned char)c)) buf += (char)tolower((unsigned char)c);\n    int l=0, r=(int)buf.size()-1; bool ok=true;\n    while(l<r){ if(buf[l]!=buf[r]){ok=false;break;} l++; r--; }\n    cout<<(ok?"YES":"NO")<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.io.*;\npublic class Main {\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String line = br.readLine(); if (line == null) line = "";\n        StringBuilder buf = new StringBuilder();\n        for (char c : line.toCharArray()) if (Character.isLetterOrDigit(c)) buf.append(Character.toLowerCase(c));\n        int l = 0, r = buf.length() - 1; boolean ok = true;\n        while (l < r) { if (buf.charAt(l) != buf.charAt(r)) { ok = false; break; } l++; r--; }\n        System.out.println(ok ? "YES" : "NO");\n    }\n}\n',
        },
        "buggy": {
            'python': "s = ''.join(c.lower() for c in input() if c.isalnum())\nl, r = 0, len(s) - 2\nok = True\nwhile l < r:\n    if s[l] != s[r]:\n        ok = False\n        break\n    l += 1; r -= 1\nprint('YES' if ok else 'NO')\n",
            'c': '#include <stdio.h>\n#include <string.h>\n#include <ctype.h>\nint main(void){\n    char line[100005];\n    if(!fgets(line,sizeof(line),stdin)) line[0]=0;\n    line[strcspn(line,"\\r\\n")]=0;\n    int n=strlen(line);\n    char buf[100005]; int m=0;\n    for(int i=0;i<n;i++){\n        if(isalnum((unsigned char)line[i])) buf[m++]=tolower((unsigned char)line[i]);\n    }\n    int l=0,r=m-2,ok=1;\n    while(l<r){ if(buf[l]!=buf[r]){ok=0;break;} l++; r--; }\n    printf("%s\\n", ok?"YES":"NO");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    string line;\n    getline(cin, line);\n    string buf;\n    for(char c: line) if(isalnum((unsigned char)c)) buf += (char)tolower((unsigned char)c);\n    int l=0, r=(int)buf.size()-2; bool ok=true;\n    while(l<r){ if(buf[l]!=buf[r]){ok=false;break;} l++; r--; }\n    cout<<(ok?"YES":"NO")<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.io.*;\npublic class Main {\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String line = br.readLine(); if (line == null) line = "";\n        StringBuilder buf = new StringBuilder();\n        for (char c : line.toCharArray()) if (Character.isLetterOrDigit(c)) buf.append(Character.toLowerCase(c));\n        int l = 0, r = buf.length() - 2; boolean ok = true;\n        while (l < r) { if (buf.charAt(l) != buf.charAt(r)) { ok = false; break; } l++; r--; }\n        System.out.println(ok ? "YES" : "NO");\n    }\n}\n',
        },
        "bug_category": 'off_by_one',
        "task_description": "This palindrome check's right pointer starts one position too far left (at length-2 instead of length-1), so the very last character is never actually compared. Find and fix the bug.",
    },
    {
        "id": 'container-water',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *h=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&h[i]);\n    int l=0,r=n-1; long long best=0;\n    while(l<r){\n        long long area=(h[l]<h[r]?h[l]:h[r])*(r-l);\n        if(area>best) best=area;\n        if(h[l]<h[r]) l++; else r--;\n    }\n    printf("%lld\\n", best);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> h(n);\n    for(auto&x:h) cin>>x;\n    int l=0,r=n-1; long long best=0;\n    while(l<r){\n        best = max(best, min(h[l],h[r]) * (long long)(r-l));\n        if(h[l]<h[r]) l++; else r--;\n    }\n    cout<<best<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] h = new long[n];\n        for (int i = 0; i < n; i++) h[i] = sc.nextLong();\n        int l = 0, r = n - 1; long best = 0;\n        while (l < r) {\n            best = Math.max(best, Math.min(h[l], h[r]) * (long)(r - l));\n            if (h[l] < h[r]) l++; else r--;\n        }\n        System.out.println(best);\n    }\n}\n',
        },
        "buggy": {
            'python': 'n = int(input())\nh = list(map(int, input().split()))\nl, r = 0, n - 1\nbest = 0\nwhile l < r:\n    best = max(best, min(h[l], h[r]) * (r - l))\n    if h[l] < h[r]:\n        r -= 1\n    else:\n        l += 1\nprint(best)\n',
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *h=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&h[i]);\n    int l=0,r=n-1; long long best=0;\n    while(l<r){\n        long long area=(h[l]<h[r]?h[l]:h[r])*(r-l);\n        if(area>best) best=area;\n        if(h[l]<h[r]) r--; else l++;\n    }\n    printf("%lld\\n", best);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> h(n);\n    for(auto&x:h) cin>>x;\n    int l=0,r=n-1; long long best=0;\n    while(l<r){\n        best = max(best, min(h[l],h[r]) * (long long)(r-l));\n        if(h[l]<h[r]) r--; else l++;\n    }\n    cout<<best<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] h = new long[n];\n        for (int i = 0; i < n; i++) h[i] = sc.nextLong();\n        int l = 0, r = n - 1; long best = 0;\n        while (l < r) {\n            best = Math.max(best, Math.min(h[l], h[r]) * (long)(r - l));\n            if (h[l] < h[r]) r--; else l++;\n        }\n        System.out.println(best);\n    }\n}\n',
        },
        "bug_category": 'wrong_comparison_operator',
        "task_description": "This two-pointer solution moves the wrong pointer -- it should always shrink the SHORTER wall's side (since that's the only side that could improve the area), but it moves the opposite pointer instead. Find and fix the bug.",
    },
    {
        "id": 'tp-sort-colors',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    int *a=malloc(sizeof(int)*n);\n    for(int i=0;i<n;i++) scanf("%d",&a[i]);\n    int low=0,mid=0,high=n-1;\n    while(mid<=high){\n        if(a[mid]==0){ int t=a[low];a[low]=a[mid];a[mid]=t; low++;mid++; }\n        else if(a[mid]==1){ mid++; }\n        else { int t=a[mid];a[mid]=a[high];a[high]=t; high--; }\n    }\n    for(int i=0;i<n;i++) printf("%d%s", a[i], i+1<n?" ":"\\n");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<int> a(n);\n    for(auto&x:a) cin>>x;\n    int low=0,mid=0,high=n-1;\n    while(mid<=high){\n        if(a[mid]==0){ swap(a[low],a[mid]); low++;mid++; }\n        else if(a[mid]==1){ mid++; }\n        else { swap(a[mid],a[high]); high--; }\n    }\n    for(int i=0;i<n;i++) cout<<a[i]<<(i+1<n?" ":"\\n");\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        int[] a = new int[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextInt();\n        int low = 0, mid = 0, high = n - 1;\n        while (mid <= high) {\n            if (a[mid] == 0) { int t=a[low];a[low]=a[mid];a[mid]=t; low++; mid++; }\n            else if (a[mid] == 1) { mid++; }\n            else { int t=a[mid];a[mid]=a[high];a[high]=t; high--; }\n        }\n        StringBuilder sb = new StringBuilder();\n        for (int i = 0; i < n; i++) sb.append(a[i]).append(i + 1 < n ? " " : "\\n");\n        System.out.print(sb);\n    }\n}\n',
        },
        "buggy": {
            'python': "n = int(input())\na = list(map(int, input().split()))\nlow, mid, high = 0, 0, n - 1\nwhile mid <= high:\n    if a[mid] == 0:\n        a[low], a[mid] = a[mid], a[low]\n        low += 1; mid += 1\n    elif a[mid] == 1:\n        mid += 1\n    else:\n        a[mid], a[high] = a[high], a[mid]\n        high -= 1; mid += 1\nprint(' '.join(map(str, a)))\n",
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    int *a=malloc(sizeof(int)*n);\n    for(int i=0;i<n;i++) scanf("%d",&a[i]);\n    int low=0,mid=0,high=n-1;\n    while(mid<=high){\n        if(a[mid]==0){ int t=a[low];a[low]=a[mid];a[mid]=t; low++;mid++; }\n        else if(a[mid]==1){ mid++; }\n        else { int t=a[mid];a[mid]=a[high];a[high]=t; high--; mid++; }\n    }\n    for(int i=0;i<n;i++) printf("%d%s", a[i], i+1<n?" ":"\\n");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<int> a(n);\n    for(auto&x:a) cin>>x;\n    int low=0,mid=0,high=n-1;\n    while(mid<=high){\n        if(a[mid]==0){ swap(a[low],a[mid]); low++;mid++; }\n        else if(a[mid]==1){ mid++; }\n        else { swap(a[mid],a[high]); high--; mid++; }\n    }\n    for(int i=0;i<n;i++) cout<<a[i]<<(i+1<n?" ":"\\n");\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        int[] a = new int[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextInt();\n        int low = 0, mid = 0, high = n - 1;\n        while (mid <= high) {\n            if (a[mid] == 0) { int t=a[low];a[low]=a[mid];a[mid]=t; low++; mid++; }\n            else if (a[mid] == 1) { mid++; }\n            else { int t=a[mid];a[mid]=a[high];a[high]=t; high--; mid++; }\n        }\n        StringBuilder sb = new StringBuilder();\n        for (int i = 0; i < n; i++) sb.append(a[i]).append(i + 1 < n ? " " : "\\n");\n        System.out.print(sb);\n    }\n}\n',
        },
        "bug_category": 'state_tracking_error',
        "task_description": "This Dutch-flag partitioning solution advances `mid` after swapping a 2 to the high end, but the freshly-swapped-in value at `mid` hasn't been examined yet -- advancing past it can leave it unclassified. Find and fix the bug.",
    },
    {
        "id": 'tree-max-depth',
        "ref": {
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\ntypedef struct Node { int v; struct Node *l,*r; } Node;\nNode* newnode(int v){ Node*n=malloc(sizeof(Node)); n->v=v; n->l=n->r=NULL; return n; }\nint depth(Node*n);\nint main(void){\n    char line[20000];\n    if(!fgets(line,sizeof(line),stdin)) line[0]=0;\n    line[strcspn(line,"\\r\\n")]=0;\n    char *toks[5000]; int ntok=0;\n    char *p=strtok(line," ");\n    while(p){ toks[ntok++]=p; p=strtok(NULL," "); }\n    if(ntok==0 || strcmp(toks[0],"N")==0){ printf("0\\n"); return 0; }\n    Node *root=newnode(atoi(toks[0]));\n    Node *q[5000]; int qh=0,qt=0;\n    q[qt++]=root;\n    int i=1;\n    while(qh<qt && i<ntok){\n        Node *node=q[qh++];\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->l=newnode(atoi(toks[i])); q[qt++]=node->l; }\n        i++;\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->r=newnode(atoi(toks[i])); q[qt++]=node->r; }\n        i++;\n    }\n    printf("%d\\n", depth(root));\n    return 0;\n}\nint depth(Node *n){\n    if(!n) return 0;\n    int dl=depth(n->l), dr=depth(n->r);\n    return 1+(dl>dr?dl:dr);\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nstruct Node { int v; Node *l,*r; Node(int val):v(val),l(nullptr),r(nullptr){} };\nint depth(Node*n){ if(!n) return 0; return 1+max(depth(n->l), depth(n->r)); }\nint main(){\n    string line;\n    getline(cin, line);\n    istringstream iss(line);\n    vector<string> toks; string tok;\n    while(iss>>tok) toks.push_back(tok);\n    if(toks.empty() || toks[0]=="N"){ cout<<0<<"\\n"; return 0; }\n    Node *root=new Node(stoi(toks[0]));\n    queue<Node*> q; q.push(root);\n    size_t i=1;\n    while(!q.empty() && i<toks.size()){\n        Node *node=q.front(); q.pop();\n        if(i<toks.size() && toks[i]!="N"){ node->l=new Node(stoi(toks[i])); q.push(node->l); }\n        i++;\n        if(i<toks.size() && toks[i]!="N"){ node->r=new Node(stoi(toks[i])); q.push(node->r); }\n        i++;\n    }\n    cout<<depth(root)<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.io.*;\nimport java.util.*;\npublic class Main {\n    static class Node { int v; Node l, r; Node(int val){ v = val; } }\n    static int depth(Node n) { if (n == null) return 0; return 1 + Math.max(depth(n.l), depth(n.r)); }\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String line = br.readLine(); if (line == null) line = "";\n        String[] toks = line.trim().isEmpty() ? new String[0] : line.trim().split("\\\\s+");\n        if (toks.length == 0 || toks[0].equals("N")) { System.out.println(0); return; }\n        Node root = new Node(Integer.parseInt(toks[0]));\n        Deque<Node> q = new ArrayDeque<>();\n        q.add(root);\n        int i = 1;\n        while (!q.isEmpty() && i < toks.length) {\n            Node node = q.poll();\n            if (i < toks.length && !toks[i].equals("N")) { node.l = new Node(Integer.parseInt(toks[i])); q.add(node.l); }\n            i++;\n            if (i < toks.length && !toks[i].equals("N")) { node.r = new Node(Integer.parseInt(toks[i])); q.add(node.r); }\n            i++;\n        }\n        System.out.println(depth(root));\n    }\n}\n',
        },
        "buggy": {
            'python': "from collections import deque\nclass N:\n    def __init__(self, v):\n        self.v = int(v); self.l = None; self.r = None\ndef build(vals):\n    if not vals or vals[0] == 'N':\n        return None\n    root = N(vals[0]); q = deque([root]); i = 1\n    while q and i < len(vals):\n        node = q.popleft()\n        if i < len(vals) and vals[i] != 'N':\n            node.l = N(vals[i]); q.append(node.l)\n        i += 1\n        if i < len(vals) and vals[i] != 'N':\n            node.r = N(vals[i]); q.append(node.r)\n        i += 1\n    return root\nvals = input().split()\nroot = build(vals)\ndef depth(n):\n    if n is None: return 0\n    return max(1 + depth(n.l), depth(n.r))\nprint(depth(root))\n",
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\ntypedef struct Node { int v; struct Node *l,*r; } Node;\nNode* newnode(int v){ Node*n=malloc(sizeof(Node)); n->v=v; n->l=n->r=NULL; return n; }\nint depth(Node*n);\nint main(void){\n    char line[20000];\n    if(!fgets(line,sizeof(line),stdin)) line[0]=0;\n    line[strcspn(line,"\\r\\n")]=0;\n    char *toks[5000]; int ntok=0;\n    char *p=strtok(line," ");\n    while(p){ toks[ntok++]=p; p=strtok(NULL," "); }\n    if(ntok==0 || strcmp(toks[0],"N")==0){ printf("0\\n"); return 0; }\n    Node *root=newnode(atoi(toks[0]));\n    Node *q[5000]; int qh=0,qt=0;\n    q[qt++]=root;\n    int i=1;\n    while(qh<qt && i<ntok){\n        Node *node=q[qh++];\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->l=newnode(atoi(toks[i])); q[qt++]=node->l; }\n        i++;\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->r=newnode(atoi(toks[i])); q[qt++]=node->r; }\n        i++;\n    }\n    printf("%d\\n", depth(root));\n    return 0;\n}\nint depth(Node *n){\n    if(!n) return 0;\n    int dl=1+depth(n->l), dr=depth(n->r);\n    return dl>dr?dl:dr;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nstruct Node { int v; Node *l,*r; Node(int val):v(val),l(nullptr),r(nullptr){} };\nint depth(Node*n){ if(!n) return 0; return max(1+depth(n->l), depth(n->r)); }\nint main(){\n    string line;\n    getline(cin, line);\n    istringstream iss(line);\n    vector<string> toks; string tok;\n    while(iss>>tok) toks.push_back(tok);\n    if(toks.empty() || toks[0]=="N"){ cout<<0<<"\\n"; return 0; }\n    Node *root=new Node(stoi(toks[0]));\n    queue<Node*> q; q.push(root);\n    size_t i=1;\n    while(!q.empty() && i<toks.size()){\n        Node *node=q.front(); q.pop();\n        if(i<toks.size() && toks[i]!="N"){ node->l=new Node(stoi(toks[i])); q.push(node->l); }\n        i++;\n        if(i<toks.size() && toks[i]!="N"){ node->r=new Node(stoi(toks[i])); q.push(node->r); }\n        i++;\n    }\n    cout<<depth(root)<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.io.*;\nimport java.util.*;\npublic class Main {\n    static class Node { int v; Node l, r; Node(int val){ v = val; } }\n    static int depth(Node n) { if (n == null) return 0; return Math.max(1 + depth(n.l), depth(n.r)); }\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String line = br.readLine(); if (line == null) line = "";\n        String[] toks = line.trim().isEmpty() ? new String[0] : line.trim().split("\\\\s+");\n        if (toks.length == 0 || toks[0].equals("N")) { System.out.println(0); return; }\n        Node root = new Node(Integer.parseInt(toks[0]));\n        Deque<Node> q = new ArrayDeque<>();\n        q.add(root);\n        int i = 1;\n        while (!q.isEmpty() && i < toks.length) {\n            Node node = q.poll();\n            if (i < toks.length && !toks[i].equals("N")) { node.l = new Node(Integer.parseInt(toks[i])); q.add(node.l); }\n            i++;\n            if (i < toks.length && !toks[i].equals("N")) { node.r = new Node(Integer.parseInt(toks[i])); q.add(node.r); }\n            i++;\n        }\n        System.out.println(depth(root));\n    }\n}\n',
        },
        "bug_category": 'missing_edge_case',
        "task_description": "This max-depth solution only adds 1 to the left subtree's depth before comparing, but not to the right subtree's -- so whenever the right side is actually the deeper branch, its depth gets undercounted by one level. Find and fix the bug.",
    },
    {
        "id": 'tree-invert',
        "ref": {
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\ntypedef struct Node { int v; struct Node *l,*r; } Node;\nNode* newnode(int v){ Node*n=malloc(sizeof(Node)); n->v=v; n->l=n->r=NULL; return n; }\nvoid invert(Node*n);\nint main(void){\n    char line[20000];\n    if(!fgets(line,sizeof(line),stdin)) line[0]=0;\n    line[strcspn(line,"\\r\\n")]=0;\n    char *toks[5000]; int ntok=0;\n    char *p=strtok(line," ");\n    while(p){ toks[ntok++]=p; p=strtok(NULL," "); }\n    if(ntok==0 || strcmp(toks[0],"N")==0){ return 0; }\n    Node *root=newnode(atoi(toks[0]));\n    Node *q[5000]; int qh=0,qt=0;\n    q[qt++]=root;\n    int i=1;\n    while(qh<qt && i<ntok){\n        Node *node=q[qh++];\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->l=newnode(atoi(toks[i])); q[qt++]=node->l; }\n        i++;\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->r=newnode(atoi(toks[i])); q[qt++]=node->r; }\n        i++;\n    }\n    invert(root);\n    Node *level[5000]; int lc=0;\n    level[lc++]=root;\n    while(lc>0){\n        for(int k=0;k<lc;k++) printf("%d%s", level[k]->v, k+1<lc?" ":"\\n");\n        Node *next[5000]; int nc=0;\n        for(int k=0;k<lc;k++){\n            if(level[k]->l) next[nc++]=level[k]->l;\n            if(level[k]->r) next[nc++]=level[k]->r;\n        }\n        for(int k=0;k<nc;k++) level[k]=next[k];\n        lc=nc;\n    }\n    return 0;\n}\nvoid invert(Node *n){\n    if(!n) return;\n    Node *t=n->l; n->l=n->r; n->r=t;\n    invert(n->l); invert(n->r);\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nstruct Node { int v; Node *l,*r; Node(int val):v(val),l(nullptr),r(nullptr){} };\nvoid invert(Node*n){ if(!n) return; swap(n->l, n->r); invert(n->l); invert(n->r); }\nint main(){\n    string line;\n    getline(cin, line);\n    istringstream iss(line);\n    vector<string> toks; string tok;\n    while(iss>>tok) toks.push_back(tok);\n    if(toks.empty() || toks[0]=="N") return 0;\n    Node *root=new Node(stoi(toks[0]));\n    queue<Node*> q; q.push(root);\n    size_t i=1;\n    while(!q.empty() && i<toks.size()){\n        Node *node=q.front(); q.pop();\n        if(i<toks.size() && toks[i]!="N"){ node->l=new Node(stoi(toks[i])); q.push(node->l); }\n        i++;\n        if(i<toks.size() && toks[i]!="N"){ node->r=new Node(stoi(toks[i])); q.push(node->r); }\n        i++;\n    }\n    invert(root);\n    vector<Node*> level = {root};\n    while(!level.empty()){\n        for(size_t k=0;k<level.size();k++) cout<<level[k]->v<<(k+1<level.size()?" ":"\\n");\n        vector<Node*> next;\n        for(auto n: level){\n            if(n->l) next.push_back(n->l);\n            if(n->r) next.push_back(n->r);\n        }\n        level = next;\n    }\n    return 0;\n}\n',
            'java': 'import java.io.*;\nimport java.util.*;\npublic class Main {\n    static class Node { int v; Node l, r; Node(int val){ v = val; } }\n    static void invert(Node n) { if (n == null) return; Node t = n.l; n.l = n.r; n.r = t; invert(n.l); invert(n.r); }\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String line = br.readLine(); if (line == null) line = "";\n        String[] toks = line.trim().isEmpty() ? new String[0] : line.trim().split("\\\\s+");\n        if (toks.length == 0 || toks[0].equals("N")) return;\n        Node root = new Node(Integer.parseInt(toks[0]));\n        Deque<Node> q = new ArrayDeque<>();\n        q.add(root);\n        int i = 1;\n        while (!q.isEmpty() && i < toks.length) {\n            Node node = q.poll();\n            if (i < toks.length && !toks[i].equals("N")) { node.l = new Node(Integer.parseInt(toks[i])); q.add(node.l); }\n            i++;\n            if (i < toks.length && !toks[i].equals("N")) { node.r = new Node(Integer.parseInt(toks[i])); q.add(node.r); }\n            i++;\n        }\n        invert(root);\n        List<Node> level = new ArrayList<>(); level.add(root);\n        StringBuilder sb = new StringBuilder();\n        while (!level.isEmpty()) {\n            for (int k = 0; k < level.size(); k++) sb.append(level.get(k).v).append(k + 1 < level.size() ? " " : "\\n");\n            List<Node> next = new ArrayList<>();\n            for (Node n : level) {\n                if (n.l != null) next.add(n.l);\n                if (n.r != null) next.add(n.r);\n            }\n            level = next;\n        }\n        System.out.print(sb);\n    }\n}\n',
        },
        "buggy": {
            'python': "from collections import deque\nclass N:\n    def __init__(self, v):\n        self.v = int(v); self.l = None; self.r = None\ndef build(vals):\n    if not vals or vals[0] == 'N':\n        return None\n    root = N(vals[0]); q = deque([root]); i = 1\n    while q and i < len(vals):\n        node = q.popleft()\n        if i < len(vals) and vals[i] != 'N':\n            node.l = N(vals[i]); q.append(node.l)\n        i += 1\n        if i < len(vals) and vals[i] != 'N':\n            node.r = N(vals[i]); q.append(node.r)\n        i += 1\n    return root\nvals = input().split()\nroot = build(vals)\ndef invert(n):\n    if n is None: return\n    n.l, n.r = n.r, n.l\n    invert(n.l); invert(n.l)\ninvert(root)\nlevel = [root]\nwhile level:\n    print(' '.join(str(n.v) for n in level))\n    nxt = []\n    for n in level:\n        if n.l: nxt.append(n.l)\n        if n.r: nxt.append(n.r)\n    level = nxt\n",
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\ntypedef struct Node { int v; struct Node *l,*r; } Node;\nNode* newnode(int v){ Node*n=malloc(sizeof(Node)); n->v=v; n->l=n->r=NULL; return n; }\nvoid invert(Node*n);\nint main(void){\n    char line[20000];\n    if(!fgets(line,sizeof(line),stdin)) line[0]=0;\n    line[strcspn(line,"\\r\\n")]=0;\n    char *toks[5000]; int ntok=0;\n    char *p=strtok(line," ");\n    while(p){ toks[ntok++]=p; p=strtok(NULL," "); }\n    if(ntok==0 || strcmp(toks[0],"N")==0){ return 0; }\n    Node *root=newnode(atoi(toks[0]));\n    Node *q[5000]; int qh=0,qt=0;\n    q[qt++]=root;\n    int i=1;\n    while(qh<qt && i<ntok){\n        Node *node=q[qh++];\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->l=newnode(atoi(toks[i])); q[qt++]=node->l; }\n        i++;\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->r=newnode(atoi(toks[i])); q[qt++]=node->r; }\n        i++;\n    }\n    invert(root);\n    Node *level[5000]; int lc=0;\n    level[lc++]=root;\n    while(lc>0){\n        for(int k=0;k<lc;k++) printf("%d%s", level[k]->v, k+1<lc?" ":"\\n");\n        Node *next[5000]; int nc=0;\n        for(int k=0;k<lc;k++){\n            if(level[k]->l) next[nc++]=level[k]->l;\n            if(level[k]->r) next[nc++]=level[k]->r;\n        }\n        for(int k=0;k<nc;k++) level[k]=next[k];\n        lc=nc;\n    }\n    return 0;\n}\nvoid invert(Node *n){\n    if(!n) return;\n    Node *t=n->l; n->l=n->r; n->r=t;\n    invert(n->l); invert(n->l);\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nstruct Node { int v; Node *l,*r; Node(int val):v(val),l(nullptr),r(nullptr){} };\nvoid invert(Node*n){ if(!n) return; swap(n->l, n->r); invert(n->l); invert(n->l); }\nint main(){\n    string line;\n    getline(cin, line);\n    istringstream iss(line);\n    vector<string> toks; string tok;\n    while(iss>>tok) toks.push_back(tok);\n    if(toks.empty() || toks[0]=="N") return 0;\n    Node *root=new Node(stoi(toks[0]));\n    queue<Node*> q; q.push(root);\n    size_t i=1;\n    while(!q.empty() && i<toks.size()){\n        Node *node=q.front(); q.pop();\n        if(i<toks.size() && toks[i]!="N"){ node->l=new Node(stoi(toks[i])); q.push(node->l); }\n        i++;\n        if(i<toks.size() && toks[i]!="N"){ node->r=new Node(stoi(toks[i])); q.push(node->r); }\n        i++;\n    }\n    invert(root);\n    vector<Node*> level = {root};\n    while(!level.empty()){\n        for(size_t k=0;k<level.size();k++) cout<<level[k]->v<<(k+1<level.size()?" ":"\\n");\n        vector<Node*> next;\n        for(auto n: level){\n            if(n->l) next.push_back(n->l);\n            if(n->r) next.push_back(n->r);\n        }\n        level = next;\n    }\n    return 0;\n}\n',
            'java': 'import java.io.*;\nimport java.util.*;\npublic class Main {\n    static class Node { int v; Node l, r; Node(int val){ v = val; } }\n    static void invert(Node n) { if (n == null) return; Node t = n.l; n.l = n.r; n.r = t; invert(n.l); invert(n.l); }\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String line = br.readLine(); if (line == null) line = "";\n        String[] toks = line.trim().isEmpty() ? new String[0] : line.trim().split("\\\\s+");\n        if (toks.length == 0 || toks[0].equals("N")) return;\n        Node root = new Node(Integer.parseInt(toks[0]));\n        Deque<Node> q = new ArrayDeque<>();\n        q.add(root);\n        int i = 1;\n        while (!q.isEmpty() && i < toks.length) {\n            Node node = q.poll();\n            if (i < toks.length && !toks[i].equals("N")) { node.l = new Node(Integer.parseInt(toks[i])); q.add(node.l); }\n            i++;\n            if (i < toks.length && !toks[i].equals("N")) { node.r = new Node(Integer.parseInt(toks[i])); q.add(node.r); }\n            i++;\n        }\n        invert(root);\n        List<Node> level = new ArrayList<>(); level.add(root);\n        StringBuilder sb = new StringBuilder();\n        while (!level.isEmpty()) {\n            for (int k = 0; k < level.size(); k++) sb.append(level.get(k).v).append(k + 1 < level.size() ? " " : "\\n");\n            List<Node> next = new ArrayList<>();\n            for (Node n : level) {\n                if (n.l != null) next.add(n.l);\n                if (n.r != null) next.add(n.r);\n            }\n            level = next;\n        }\n        System.out.print(sb);\n    }\n}\n',
        },
        "bug_category": 'wrong_variable_reference',
        "task_description": "This tree-inversion solution swaps each node's children correctly, but then recurses into the LEFT child twice instead of once into each child -- the right subtree never gets inverted below the top level. Find and fix the bug.",
    },
    {
        "id": 'tree-validate-bst',
        "ref": {
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\n#include <limits.h>\ntypedef struct Node { long long v; struct Node *l,*r; } Node;\nNode* newnode(long long v){ Node*n=malloc(sizeof(Node)); n->v=v; n->l=n->r=NULL; return n; }\nint valid(Node*n, long long lo, long long hi);\nint main(void){\n    char line[20000];\n    if(!fgets(line,sizeof(line),stdin)) line[0]=0;\n    line[strcspn(line,"\\r\\n")]=0;\n    char *toks[5000]; int ntok=0;\n    char *p=strtok(line," ");\n    while(p){ toks[ntok++]=p; p=strtok(NULL," "); }\n    if(ntok==0 || strcmp(toks[0],"N")==0){ printf("YES\\n"); return 0; }\n    Node *root=newnode(atoll(toks[0]));\n    Node *q[5000]; int qh=0,qt=0;\n    q[qt++]=root;\n    int i=1;\n    while(qh<qt && i<ntok){\n        Node *node=q[qh++];\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->l=newnode(atoll(toks[i])); q[qt++]=node->l; }\n        i++;\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->r=newnode(atoll(toks[i])); q[qt++]=node->r; }\n        i++;\n    }\n    printf("%s\\n", valid(root, LLONG_MIN, LLONG_MAX) ? "YES":"NO");\n    return 0;\n}\nint valid(Node*n, long long lo, long long hi){\n    if(!n) return 1;\n    if(!(lo<n->v && n->v<hi)) return 0;\n    return valid(n->l, lo, n->v) && valid(n->r, n->v, hi);\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nstruct Node { long long v; Node *l,*r; Node(long long val):v(val),l(nullptr),r(nullptr){} };\nbool valid(Node*n, long long lo, long long hi){\n    if(!n) return true;\n    if(!(lo<n->v && n->v<hi)) return false;\n    return valid(n->l, lo, n->v) && valid(n->r, n->v, hi);\n}\nint main(){\n    string line;\n    getline(cin, line);\n    istringstream iss(line);\n    vector<string> toks; string tok;\n    while(iss>>tok) toks.push_back(tok);\n    if(toks.empty() || toks[0]=="N"){ cout<<"YES\\n"; return 0; }\n    Node *root=new Node(stoll(toks[0]));\n    queue<Node*> q; q.push(root);\n    size_t i=1;\n    while(!q.empty() && i<toks.size()){\n        Node *node=q.front(); q.pop();\n        if(i<toks.size() && toks[i]!="N"){ node->l=new Node(stoll(toks[i])); q.push(node->l); }\n        i++;\n        if(i<toks.size() && toks[i]!="N"){ node->r=new Node(stoll(toks[i])); q.push(node->r); }\n        i++;\n    }\n    cout<<(valid(root, LLONG_MIN, LLONG_MAX) ? "YES":"NO")<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.io.*;\nimport java.util.*;\npublic class Main {\n    static class Node { long v; Node l, r; Node(long val){ v = val; } }\n    static boolean valid(Node n, long lo, long hi) {\n        if (n == null) return true;\n        if (!(lo < n.v && n.v < hi)) return false;\n        return valid(n.l, lo, n.v) && valid(n.r, n.v, hi);\n    }\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String line = br.readLine(); if (line == null) line = "";\n        String[] toks = line.trim().isEmpty() ? new String[0] : line.trim().split("\\\\s+");\n        if (toks.length == 0 || toks[0].equals("N")) { System.out.println("YES"); return; }\n        Node root = new Node(Long.parseLong(toks[0]));\n        Deque<Node> q = new ArrayDeque<>();\n        q.add(root);\n        int i = 1;\n        while (!q.isEmpty() && i < toks.length) {\n            Node node = q.poll();\n            if (i < toks.length && !toks[i].equals("N")) { node.l = new Node(Long.parseLong(toks[i])); q.add(node.l); }\n            i++;\n            if (i < toks.length && !toks[i].equals("N")) { node.r = new Node(Long.parseLong(toks[i])); q.add(node.r); }\n            i++;\n        }\n        System.out.println(valid(root, Long.MIN_VALUE, Long.MAX_VALUE) ? "YES" : "NO");\n    }\n}\n',
        },
        "buggy": {
            'python': "from collections import deque\nclass N:\n    def __init__(self, v):\n        self.v = int(v); self.l = None; self.r = None\ndef build(vals):\n    if not vals or vals[0] == 'N':\n        return None\n    root = N(vals[0]); q = deque([root]); i = 1\n    while q and i < len(vals):\n        node = q.popleft()\n        if i < len(vals) and vals[i] != 'N':\n            node.l = N(vals[i]); q.append(node.l)\n        i += 1\n        if i < len(vals) and vals[i] != 'N':\n            node.r = N(vals[i]); q.append(node.r)\n        i += 1\n    return root\nvals = input().split()\nroot = build(vals)\ndef valid(n, lo, hi):\n    if n is None: return True\n    if not (lo < n.v < hi): return False\n    return valid(n.l, float('-inf'), n.v) and valid(n.r, n.v, float('inf'))\nprint('YES' if valid(root, float('-inf'), float('inf')) else 'NO')\n",
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\n#include <limits.h>\ntypedef struct Node { long long v; struct Node *l,*r; } Node;\nNode* newnode(long long v){ Node*n=malloc(sizeof(Node)); n->v=v; n->l=n->r=NULL; return n; }\nint valid(Node*n, long long lo, long long hi);\nint main(void){\n    char line[20000];\n    if(!fgets(line,sizeof(line),stdin)) line[0]=0;\n    line[strcspn(line,"\\r\\n")]=0;\n    char *toks[5000]; int ntok=0;\n    char *p=strtok(line," ");\n    while(p){ toks[ntok++]=p; p=strtok(NULL," "); }\n    if(ntok==0 || strcmp(toks[0],"N")==0){ printf("YES\\n"); return 0; }\n    Node *root=newnode(atoll(toks[0]));\n    Node *q[5000]; int qh=0,qt=0;\n    q[qt++]=root;\n    int i=1;\n    while(qh<qt && i<ntok){\n        Node *node=q[qh++];\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->l=newnode(atoll(toks[i])); q[qt++]=node->l; }\n        i++;\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->r=newnode(atoll(toks[i])); q[qt++]=node->r; }\n        i++;\n    }\n    printf("%s\\n", valid(root, LLONG_MIN, LLONG_MAX) ? "YES":"NO");\n    return 0;\n}\nint valid(Node*n, long long lo, long long hi){\n    if(!n) return 1;\n    if(!(lo<n->v && n->v<hi)) return 0;\n    return valid(n->l, LLONG_MIN, n->v) && valid(n->r, n->v, LLONG_MAX);\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nstruct Node { long long v; Node *l,*r; Node(long long val):v(val),l(nullptr),r(nullptr){} };\nbool valid(Node*n, long long lo, long long hi){\n    if(!n) return true;\n    if(!(lo<n->v && n->v<hi)) return false;\n    return valid(n->l, LLONG_MIN, n->v) && valid(n->r, n->v, LLONG_MAX);\n}\nint main(){\n    string line;\n    getline(cin, line);\n    istringstream iss(line);\n    vector<string> toks; string tok;\n    while(iss>>tok) toks.push_back(tok);\n    if(toks.empty() || toks[0]=="N"){ cout<<"YES\\n"; return 0; }\n    Node *root=new Node(stoll(toks[0]));\n    queue<Node*> q; q.push(root);\n    size_t i=1;\n    while(!q.empty() && i<toks.size()){\n        Node *node=q.front(); q.pop();\n        if(i<toks.size() && toks[i]!="N"){ node->l=new Node(stoll(toks[i])); q.push(node->l); }\n        i++;\n        if(i<toks.size() && toks[i]!="N"){ node->r=new Node(stoll(toks[i])); q.push(node->r); }\n        i++;\n    }\n    cout<<(valid(root, LLONG_MIN, LLONG_MAX) ? "YES":"NO")<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.io.*;\nimport java.util.*;\npublic class Main {\n    static class Node { long v; Node l, r; Node(long val){ v = val; } }\n    static boolean valid(Node n, long lo, long hi) {\n        if (n == null) return true;\n        if (!(lo < n.v && n.v < hi)) return false;\n        return valid(n.l, Long.MIN_VALUE, n.v) && valid(n.r, n.v, Long.MAX_VALUE);\n    }\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String line = br.readLine(); if (line == null) line = "";\n        String[] toks = line.trim().isEmpty() ? new String[0] : line.trim().split("\\\\s+");\n        if (toks.length == 0 || toks[0].equals("N")) { System.out.println("YES"); return; }\n        Node root = new Node(Long.parseLong(toks[0]));\n        Deque<Node> q = new ArrayDeque<>();\n        q.add(root);\n        int i = 1;\n        while (!q.isEmpty() && i < toks.length) {\n            Node node = q.poll();\n            if (i < toks.length && !toks[i].equals("N")) { node.l = new Node(Long.parseLong(toks[i])); q.add(node.l); }\n            i++;\n            if (i < toks.length && !toks[i].equals("N")) { node.r = new Node(Long.parseLong(toks[i])); q.add(node.r); }\n            i++;\n        }\n        System.out.println(valid(root, Long.MIN_VALUE, Long.MAX_VALUE) ? "YES" : "NO");\n    }\n}\n',
        },
        "bug_category": 'incomplete_boundary_handling',
        "task_description": 'This BST validator resets the allowed value range to (-infinity, +infinity) on every recursive call instead of narrowing it from the range it was passed -- so it only checks each node against its immediate parent, losing constraints from higher ancestors. Find and fix the bug.',
    },
    {
        "id": 'num-islands',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint r, c; int **g;\nvoid dfs(int i, int j){\n    if (i < 0 || j < 0 || i >= r || j >= c || g[i][j] != 1) return;\n    g[i][j] = 2;\n    dfs(i + 1, j); dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1);\n}\nint main(void){\n    scanf("%d %d", &r, &c);\n    g = malloc(sizeof(int*) * r);\n    for (int i = 0; i < r; i++) { g[i] = malloc(sizeof(int) * c); for (int j = 0; j < c; j++) scanf("%d", &g[i][j]); }\n    int cnt = 0;\n    for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) if (g[i][j] == 1) { cnt++; dfs(i, j); }\n    printf("%d\\n", cnt);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint r, c;\nvector<vector<int>> g;\nvoid dfs(int i, int j){\n    if (i < 0 || j < 0 || i >= r || j >= c || g[i][j] != 1) return;\n    g[i][j] = 2;\n    dfs(i + 1, j); dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1);\n}\nint main(){\n    cin >> r >> c;\n    g.assign(r, vector<int>(c));\n    for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) cin >> g[i][j];\n    int cnt = 0;\n    for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) if (g[i][j] == 1) { cnt++; dfs(i, j); }\n    cout << cnt << "\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    static int r, c;\n    static int[][] g;\n    static void dfs(int i, int j) {\n        if (i < 0 || j < 0 || i >= r || j >= c || g[i][j] != 1) return;\n        g[i][j] = 2;\n        dfs(i + 1, j); dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1);\n    }\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        r = sc.nextInt(); c = sc.nextInt();\n        g = new int[r][c];\n        for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) g[i][j] = sc.nextInt();\n        int cnt = 0;\n        for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) if (g[i][j] == 1) { cnt++; dfs(i, j); }\n        System.out.println(cnt);\n    }\n}\n',
        },
        "buggy": {
            'python': 'import sys\nsys.setrecursionlimit(200000)\nr, c = map(int, input().split())\ng = [list(map(int, input().split())) for _ in range(r)]\ndef dfs(i, j):\n    if i < 0 or j < 0 or i >= r or j >= c or g[i][j] != 1: return\n    g[i][j] = 2\n    dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1)\ncnt = 0\nfor i in range(r):\n    for j in range(c):\n        if g[i][j] == 1:\n            cnt += 1; dfs(i, j)\nprint(cnt)\n',
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint r, c; int **g;\nvoid dfs(int i, int j){\n    if (i < 0 || j < 0 || i >= r || j >= c || g[i][j] != 1) return;\n    g[i][j] = 2;\n    dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1);\n}\nint main(void){\n    scanf("%d %d", &r, &c);\n    g = malloc(sizeof(int*) * r);\n    for (int i = 0; i < r; i++) { g[i] = malloc(sizeof(int) * c); for (int j = 0; j < c; j++) scanf("%d", &g[i][j]); }\n    int cnt = 0;\n    for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) if (g[i][j] == 1) { cnt++; dfs(i, j); }\n    printf("%d\\n", cnt);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint r, c;\nvector<vector<int>> g;\nvoid dfs(int i, int j){\n    if (i < 0 || j < 0 || i >= r || j >= c || g[i][j] != 1) return;\n    g[i][j] = 2;\n    dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1);\n}\nint main(){\n    cin >> r >> c;\n    g.assign(r, vector<int>(c));\n    for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) cin >> g[i][j];\n    int cnt = 0;\n    for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) if (g[i][j] == 1) { cnt++; dfs(i, j); }\n    cout << cnt << "\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    static int r, c;\n    static int[][] g;\n    static void dfs(int i, int j) {\n        if (i < 0 || j < 0 || i >= r || j >= c || g[i][j] != 1) return;\n        g[i][j] = 2;\n        dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1);\n    }\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        r = sc.nextInt(); c = sc.nextInt();\n        g = new int[r][c];\n        for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) g[i][j] = sc.nextInt();\n        int cnt = 0;\n        for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) if (g[i][j] == 1) { cnt++; dfs(i, j); }\n        System.out.println(cnt);\n    }\n}\n',
        },
        "bug_category": 'missing_edge_case',
        "task_description": "This flood-fill island counter's DFS only explores up, left, and right from each cell -- it never recurses downward, so islands that are only connected via a cell below can be split into multiple counted islands. Find and fix the bug.",
    },
    {
        "id": 'graph-bfs-shortest-path',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n, m; scanf("%d %d", &n, &m);\n    int *head = malloc(sizeof(int) * n); for (int i = 0; i < n; i++) head[i] = -1;\n    int *to = malloc(sizeof(int) * 2 * (m > 0 ? m : 1)), *nxt = malloc(sizeof(int) * 2 * (m > 0 ? m : 1));\n    int ec = 0;\n    for (int e = 0; e < m; e++) {\n        int u, v; scanf("%d %d", &u, &v);\n        to[ec] = v; nxt[ec] = head[u]; head[u] = ec++;\n        to[ec] = u; nxt[ec] = head[v]; head[v] = ec++;\n    }\n    int src, dst; scanf("%d %d", &src, &dst);\n    int *dist = malloc(sizeof(int) * n);\n    for (int i = 0; i < n; i++) dist[i] = -1;\n    int *q = malloc(sizeof(int) * (n > 0 ? n : 1)); int qh = 0, qt = 0;\n    dist[src] = 0; q[qt++] = src;\n    while (qh < qt) {\n        int u = q[qh++];\n        for (int e = head[u]; e != -1; e = nxt[e]) {\n            int v = to[e];\n            if (dist[v] == -1) { dist[v] = dist[u] + 1; q[qt++] = v; }\n        }\n    }\n    printf("%d\\n", dist[dst]);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n, m; cin >> n >> m;\n    vector<vector<int>> adj(n);\n    for (int e = 0; e < m; e++) {\n        int u, v; cin >> u >> v;\n        adj[u].push_back(v); adj[v].push_back(u);\n    }\n    int src, dst; cin >> src >> dst;\n    vector<int> dist(n, -1);\n    queue<int> q;\n    dist[src] = 0; q.push(src);\n    while (!q.empty()) {\n        int u = q.front(); q.pop();\n        for (int v : adj[u]) if (dist[v] == -1) { dist[v] = dist[u] + 1; q.push(v); }\n    }\n    cout << dist[dst] << "\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt(), m = sc.nextInt();\n        List<List<Integer>> adj = new ArrayList<>();\n        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());\n        for (int e = 0; e < m; e++) {\n            int u = sc.nextInt(), v = sc.nextInt();\n            adj.get(u).add(v); adj.get(v).add(u);\n        }\n        int src = sc.nextInt(), dst = sc.nextInt();\n        int[] dist = new int[n];\n        Arrays.fill(dist, -1);\n        Deque<Integer> q = new ArrayDeque<>();\n        dist[src] = 0; q.add(src);\n        while (!q.isEmpty()) {\n            int u = q.poll();\n            for (int v : adj.get(u)) if (dist[v] == -1) { dist[v] = dist[u] + 1; q.add(v); }\n        }\n        System.out.println(dist[dst]);\n    }\n}\n',
        },
        "buggy": {
            'python': 'from collections import deque\nn, m = map(int, input().split())\nadj = [[] for _ in range(n)]\nfor _ in range(m):\n    u, v = map(int, input().split())\n    adj[u].append(v); adj[v].append(u)\nsrc, dst = map(int, input().split())\ndist = [-1] * n\ndist[src] = 0\nq = deque([src])\nwhile q:\n    u = q.popleft()\n    for v in adj[u]:\n        if dist[v] == -1:\n            dist[v] = dist[u]\n            q.append(v)\nprint(dist[dst])\n',
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n, m; scanf("%d %d", &n, &m);\n    int *head = malloc(sizeof(int) * n); for (int i = 0; i < n; i++) head[i] = -1;\n    int *to = malloc(sizeof(int) * 2 * (m > 0 ? m : 1)), *nxt = malloc(sizeof(int) * 2 * (m > 0 ? m : 1));\n    int ec = 0;\n    for (int e = 0; e < m; e++) {\n        int u, v; scanf("%d %d", &u, &v);\n        to[ec] = v; nxt[ec] = head[u]; head[u] = ec++;\n        to[ec] = u; nxt[ec] = head[v]; head[v] = ec++;\n    }\n    int src, dst; scanf("%d %d", &src, &dst);\n    int *dist = malloc(sizeof(int) * n);\n    for (int i = 0; i < n; i++) dist[i] = -1;\n    int *q = malloc(sizeof(int) * (n > 0 ? n : 1)); int qh = 0, qt = 0;\n    dist[src] = 0; q[qt++] = src;\n    while (qh < qt) {\n        int u = q[qh++];\n        for (int e = head[u]; e != -1; e = nxt[e]) {\n            int v = to[e];\n            if (dist[v] == -1) { dist[v] = dist[u]; q[qt++] = v; }\n        }\n    }\n    printf("%d\\n", dist[dst]);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n, m; cin >> n >> m;\n    vector<vector<int>> adj(n);\n    for (int e = 0; e < m; e++) {\n        int u, v; cin >> u >> v;\n        adj[u].push_back(v); adj[v].push_back(u);\n    }\n    int src, dst; cin >> src >> dst;\n    vector<int> dist(n, -1);\n    queue<int> q;\n    dist[src] = 0; q.push(src);\n    while (!q.empty()) {\n        int u = q.front(); q.pop();\n        for (int v : adj[u]) if (dist[v] == -1) { dist[v] = dist[u]; q.push(v); }\n    }\n    cout << dist[dst] << "\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt(), m = sc.nextInt();\n        List<List<Integer>> adj = new ArrayList<>();\n        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());\n        for (int e = 0; e < m; e++) {\n            int u = sc.nextInt(), v = sc.nextInt();\n            adj.get(u).add(v); adj.get(v).add(u);\n        }\n        int src = sc.nextInt(), dst = sc.nextInt();\n        int[] dist = new int[n];\n        Arrays.fill(dist, -1);\n        Deque<Integer> q = new ArrayDeque<>();\n        dist[src] = 0; q.add(src);\n        while (!q.isEmpty()) {\n            int u = q.poll();\n            for (int v : adj.get(u)) if (dist[v] == -1) { dist[v] = dist[u]; q.add(v); }\n        }\n        System.out.println(dist[dst]);\n    }\n}\n',
        },
        "bug_category": 'state_tracking_error',
        "task_description": "This BFS shortest-path solution assigns each newly-discovered node the SAME distance as the node it came from, instead of one more than it -- so every reachable node ends up reported at distance equal to the source's own distance. Find and fix the bug.",
    },
    {
        "id": 'graph-cycle-undirected',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint parent[10005];\nint find(int x){ while(parent[x]!=x) x=parent[x]; return x; }\nint main(void){\n    int n,m; scanf("%d %d",&n,&m);\n    for(int i=0;i<n;i++) parent[i]=i;\n    int cycle=0;\n    for(int e=0;e<m;e++){\n        int u,v; scanf("%d %d",&u,&v);\n        int ru=find(u), rv=find(v);\n        if(ru==rv) cycle=1;\n        else parent[ru]=rv;\n    }\n    printf("%s\\n", cycle?"YES":"NO");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nvector<int> parent;\nint find(int x){ while(parent[x]!=x) x=parent[x]; return x; }\nint main(){\n    int n,m; cin>>n>>m;\n    parent.resize(n);\n    for(int i=0;i<n;i++) parent[i]=i;\n    bool cycle=false;\n    for(int e=0;e<m;e++){\n        int u,v; cin>>u>>v;\n        int ru=find(u), rv=find(v);\n        if(ru==rv) cycle=true;\n        else parent[ru]=rv;\n    }\n    cout<<(cycle?"YES":"NO")<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    static int[] parent;\n    static int find(int x){ while(parent[x]!=x) x=parent[x]; return x; }\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt(), m = sc.nextInt();\n        parent = new int[n];\n        for (int i = 0; i < n; i++) parent[i] = i;\n        boolean cycle = false;\n        for (int e = 0; e < m; e++) {\n            int u = sc.nextInt(), v = sc.nextInt();\n            int ru = find(u), rv = find(v);\n            if (ru == rv) cycle = true;\n            else parent[ru] = rv;\n        }\n        System.out.println(cycle ? "YES" : "NO");\n    }\n}\n',
        },
        "buggy": {
            'python': "n, m = map(int, input().split())\nparent = list(range(n))\ndef find(x):\n    while parent[x] != x:\n        x = parent[x]\n    return x\ncycle = False\nfor _ in range(m):\n    u, v = map(int, input().split())\n    ru, rv = find(u), find(v)\n    if ru != rv:\n        cycle = True\n    parent[ru] = rv\nprint('YES' if cycle else 'NO')\n",
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint parent[10005];\nint find(int x){ while(parent[x]!=x) x=parent[x]; return x; }\nint main(void){\n    int n,m; scanf("%d %d",&n,&m);\n    for(int i=0;i<n;i++) parent[i]=i;\n    int cycle=0;\n    for(int e=0;e<m;e++){\n        int u,v; scanf("%d %d",&u,&v);\n        int ru=find(u), rv=find(v);\n        if(ru!=rv) cycle=1;\n        parent[ru]=rv;\n    }\n    printf("%s\\n", cycle?"YES":"NO");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nvector<int> parent;\nint find(int x){ while(parent[x]!=x) x=parent[x]; return x; }\nint main(){\n    int n,m; cin>>n>>m;\n    parent.resize(n);\n    for(int i=0;i<n;i++) parent[i]=i;\n    bool cycle=false;\n    for(int e=0;e<m;e++){\n        int u,v; cin>>u>>v;\n        int ru=find(u), rv=find(v);\n        if(ru!=rv) cycle=true;\n        parent[ru]=rv;\n    }\n    cout<<(cycle?"YES":"NO")<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    static int[] parent;\n    static int find(int x){ while(parent[x]!=x) x=parent[x]; return x; }\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt(), m = sc.nextInt();\n        parent = new int[n];\n        for (int i = 0; i < n; i++) parent[i] = i;\n        boolean cycle = false;\n        for (int e = 0; e < m; e++) {\n            int u = sc.nextInt(), v = sc.nextInt();\n            int ru = find(u), rv = find(v);\n            if (ru != rv) cycle = true;\n            parent[ru] = rv;\n        }\n        System.out.println(cycle ? "YES" : "NO");\n    }\n}\n',
        },
        "bug_category": 'wrong_comparison_operator',
        "task_description": "This union-find cycle detector has the condition backwards -- it flags a cycle whenever two endpoints are in DIFFERENT sets (a normal union, not a cycle) instead of when they're already in the SAME set. Find and fix the bug.",
    },
    {
        "id": 'climb-stairs',
        "ref": {
            'c': '#include <stdio.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long a=1,b=1;\n    for(int i=0;i<n;i++){ long long t=a+b; a=b; b=t; }\n    printf("%lld\\n", a);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    long long a=1,b=1;\n    for(int i=0;i<n;i++){ long long t=a+b; a=b; b=t; }\n    cout<<a<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long a = 1, b = 1;\n        for (int i = 0; i < n; i++) { long t = a + b; a = b; b = t; }\n        System.out.println(a);\n    }\n}\n',
        },
        "buggy": {
            'python': 'n = int(input())\na, b = 1, 1\nfor _ in range(n):\n    a, b = b, (a + b) & 0xFFFF\nprint(a)\n',
            'c': '#include <stdio.h>\nint main(void){\n    int n; scanf("%d",&n);\n    unsigned short a=1,b=1;\n    for(int i=0;i<n;i++){ unsigned short t=(unsigned short)(a+b); a=b; b=t; }\n    printf("%u\\n", a);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    unsigned short a=1,b=1;\n    for(int i=0;i<n;i++){ unsigned short t=(unsigned short)(a+b); a=b; b=t; }\n    cout<<a<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        short a = 1, b = 1;\n        for (int i = 0; i < n; i++) { short t = (short) (a + b); a = b; b = t; }\n        System.out.println(a);\n    }\n}\n',
        },
        "bug_category": 'incomplete_boundary_handling',
        "task_description": "This solution stores the running Fibonacci-like counts in a 16-bit integer. It's correct for small staircases, but silently wraps around (overflows) once the true count exceeds 65535, giving a wrong answer for larger n. Find and fix the bug.",
    },
    {
        "id": 'coin-change',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    int *coins=malloc(sizeof(int)*n);\n    for(int i=0;i<n;i++) scanf("%d",&coins[i]);\n    int amount; scanf("%d",&amount);\n    int INF=amount+1;\n    int *dp=malloc(sizeof(int)*(amount+1));\n    dp[0]=0;\n    for(int i=1;i<=amount;i++) dp[i]=INF;\n    for(int i=1;i<=amount;i++){\n        for(int k=0;k<n;k++){\n            int c=coins[k];\n            if(c<=i && dp[i-c]+1<dp[i]) dp[i]=dp[i-c]+1;\n        }\n    }\n    printf("%d\\n", dp[amount]<=amount?dp[amount]:-1);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<int> coins(n);\n    for(auto&x:coins) cin>>x;\n    int amount; cin>>amount;\n    int INF=amount+1;\n    vector<int> dp(amount+1, INF);\n    dp[0]=0;\n    for(int i=1;i<=amount;i++)\n        for(int c: coins)\n            if(c<=i) dp[i]=min(dp[i], dp[i-c]+1);\n    cout<<(dp[amount]<=amount ? dp[amount] : -1)<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        int[] coins = new int[n];\n        for (int i = 0; i < n; i++) coins[i] = sc.nextInt();\n        int amount = sc.nextInt();\n        int INF = amount + 1;\n        int[] dp = new int[amount + 1];\n        Arrays.fill(dp, INF);\n        dp[0] = 0;\n        for (int i = 1; i <= amount; i++)\n            for (int c : coins)\n                if (c <= i) dp[i] = Math.min(dp[i], dp[i - c] + 1);\n        System.out.println(dp[amount] <= amount ? dp[amount] : -1);\n    }\n}\n',
        },
        "buggy": {
            'python': 'n = int(input())\ncoins = list(map(int, input().split()))\namount = int(input())\nINF = amount + 1\ndp = [0] + [INF] * amount\nfor i in range(1, amount + 1):\n    for c in coins:\n        if c < i:\n            dp[i] = min(dp[i], dp[i - c] + 1)\nprint(dp[amount] if dp[amount] <= amount else -1)\n',
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint main(void){\n    int n; scanf("%d",&n);\n    int *coins=malloc(sizeof(int)*n);\n    for(int i=0;i<n;i++) scanf("%d",&coins[i]);\n    int amount; scanf("%d",&amount);\n    int INF=amount+1;\n    int *dp=malloc(sizeof(int)*(amount+1));\n    dp[0]=0;\n    for(int i=1;i<=amount;i++) dp[i]=INF;\n    for(int i=1;i<=amount;i++){\n        for(int k=0;k<n;k++){\n            int c=coins[k];\n            if(c<i && dp[i-c]+1<dp[i]) dp[i]=dp[i-c]+1;\n        }\n    }\n    printf("%d\\n", dp[amount]<=amount?dp[amount]:-1);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<int> coins(n);\n    for(auto&x:coins) cin>>x;\n    int amount; cin>>amount;\n    int INF=amount+1;\n    vector<int> dp(amount+1, INF);\n    dp[0]=0;\n    for(int i=1;i<=amount;i++)\n        for(int c: coins)\n            if(c<i) dp[i]=min(dp[i], dp[i-c]+1);\n    cout<<(dp[amount]<=amount ? dp[amount] : -1)<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        int[] coins = new int[n];\n        for (int i = 0; i < n; i++) coins[i] = sc.nextInt();\n        int amount = sc.nextInt();\n        int INF = amount + 1;\n        int[] dp = new int[amount + 1];\n        Arrays.fill(dp, INF);\n        dp[0] = 0;\n        for (int i = 1; i <= amount; i++)\n            for (int c : coins)\n                if (c < i) dp[i] = Math.min(dp[i], dp[i - c] + 1);\n        System.out.println(dp[amount] <= amount ? dp[amount] : -1);\n    }\n}\n',
        },
        "bug_category": 'wrong_comparison_operator',
        "task_description": "This coin-change DP only considers a coin usable when its value is strictly less than the current amount, excluding the case where the coin's value exactly equals the amount. Find and fix the bug.",
    },
    {
        "id": 'dp-longest-common-subsequence',
        "ref": {
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\nint main(void){\n    char a[1005], b[1005];\n    if(!fgets(a,sizeof(a),stdin)) a[0]=0;\n    if(!fgets(b,sizeof(b),stdin)) b[0]=0;\n    a[strcspn(a,"\\r\\n")]=0;\n    b[strcspn(b,"\\r\\n")]=0;\n    int n=strlen(a), m=strlen(b);\n    int **dp=malloc(sizeof(int*)*(n+1));\n    for(int i=0;i<=n;i++){ dp[i]=malloc(sizeof(int)*(m+1)); }\n    for(int j=0;j<=m;j++) dp[0][j]=0;\n    for(int i=1;i<=n;i++){\n        dp[i][0]=0;\n        for(int j=1;j<=m;j++){\n            if(a[i-1]==b[j-1]) dp[i][j]=dp[i-1][j-1]+1;\n            else dp[i][j] = dp[i-1][j]>dp[i][j-1]?dp[i-1][j]:dp[i][j-1];\n        }\n    }\n    printf("%d\\n", dp[n][m]);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    string a, b;\n    getline(cin, a);\n    getline(cin, b);\n    int n=(int)a.size(), m=(int)b.size();\n    vector<vector<int>> dp(n+1, vector<int>(m+1, 0));\n    for(int i=1;i<=n;i++)\n        for(int j=1;j<=m;j++)\n            dp[i][j] = (a[i-1]==b[j-1]) ? dp[i-1][j-1]+1 : max(dp[i-1][j], dp[i][j-1]);\n    cout<<dp[n][m]<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.io.*;\npublic class Main {\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String a = br.readLine(); if (a == null) a = "";\n        String b = br.readLine(); if (b == null) b = "";\n        int n = a.length(), m = b.length();\n        int[][] dp = new int[n + 1][m + 1];\n        for (int i = 1; i <= n; i++)\n            for (int j = 1; j <= m; j++)\n                dp[i][j] = (a.charAt(i - 1) == b.charAt(j - 1)) ? dp[i - 1][j - 1] + 1 : Math.max(dp[i - 1][j], dp[i][j - 1]);\n        System.out.println(dp[n][m]);\n    }\n}\n',
        },
        "buggy": {
            'python': 'a = input()\nb = input()\nn, m = len(a), len(b)\ndp = [[0] * (m + 1) for _ in range(n + 1)]\nfor i in range(1, n + 1):\n    for j in range(1, m + 1):\n        if a[i - 1] == b[j - 1]:\n            dp[i][j] = dp[i - 1][j - 1] + 1\n        else:\n            dp[i][j] = dp[i - 1][j]\nprint(dp[n][m])\n',
            'c': '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\nint main(void){\n    char a[1005], b[1005];\n    if(!fgets(a,sizeof(a),stdin)) a[0]=0;\n    if(!fgets(b,sizeof(b),stdin)) b[0]=0;\n    a[strcspn(a,"\\r\\n")]=0;\n    b[strcspn(b,"\\r\\n")]=0;\n    int n=strlen(a), m=strlen(b);\n    int **dp=malloc(sizeof(int*)*(n+1));\n    for(int i=0;i<=n;i++){ dp[i]=malloc(sizeof(int)*(m+1)); }\n    for(int j=0;j<=m;j++) dp[0][j]=0;\n    for(int i=1;i<=n;i++){\n        dp[i][0]=0;\n        for(int j=1;j<=m;j++){\n            if(a[i-1]==b[j-1]) dp[i][j]=dp[i-1][j-1]+1;\n            else dp[i][j] = dp[i-1][j];\n        }\n    }\n    printf("%d\\n", dp[n][m]);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    string a, b;\n    getline(cin, a);\n    getline(cin, b);\n    int n=(int)a.size(), m=(int)b.size();\n    vector<vector<int>> dp(n+1, vector<int>(m+1, 0));\n    for(int i=1;i<=n;i++)\n        for(int j=1;j<=m;j++)\n            dp[i][j] = (a[i-1]==b[j-1]) ? dp[i-1][j-1]+1 : dp[i-1][j];\n    cout<<dp[n][m]<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.io.*;\npublic class Main {\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String a = br.readLine(); if (a == null) a = "";\n        String b = br.readLine(); if (b == null) b = "";\n        int n = a.length(), m = b.length();\n        int[][] dp = new int[n + 1][m + 1];\n        for (int i = 1; i <= n; i++)\n            for (int j = 1; j <= m; j++)\n                dp[i][j] = (a.charAt(i - 1) == b.charAt(j - 1)) ? dp[i - 1][j - 1] + 1 : dp[i - 1][j];\n        System.out.println(dp[n][m]);\n    }\n}\n',
        },
        "bug_category": 'wrong_variable_reference',
        "task_description": 'In the no-match case, this LCS solution only carries forward dp[i-1][j] and forgets to also consider dp[i][j-1] -- so it misses common subsequences that require skipping a character from the second string. Find and fix the bug.',
    },
    {
        "id": 'adv-top-k-frequent',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\nint cmp_int(const void*a,const void*b){ return (*(int*)a)-(*(int*)b); }\ntypedef struct { int val, cnt; } VC;\nint cmp_final(const void*a,const void*b){\n    VC*x=(VC*)a,*y=(VC*)b;\n    if(x->cnt!=y->cnt) return y->cnt-x->cnt;\n    return x->val-y->val;\n}\nint main(void){\n    int n; scanf("%d",&n);\n    int *a=malloc(sizeof(int)*n);\n    for(int i=0;i<n;i++) scanf("%d",&a[i]);\n    int k; scanf("%d",&k);\n    int *sortedv=malloc(sizeof(int)*n);\n    memcpy(sortedv,a,sizeof(int)*n);\n    qsort(sortedv,n,sizeof(int),cmp_int);\n    VC *vc=malloc(sizeof(VC)*n);\n    int m=0, i=0;\n    while(i<n){\n        int j=i;\n        while(j<n && sortedv[j]==sortedv[i]) j++;\n        vc[m].val=sortedv[i]; vc[m].cnt=j-i; m++;\n        i=j;\n    }\n    qsort(vc,m,sizeof(VC),cmp_final);\n    for(int t=0;t<k;t++) printf("%d%s", vc[t].val, t+1<k?" ":"\\n");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<int> a(n);\n    for(auto&x:a) cin>>x;\n    int k; cin>>k;\n    map<int,int> cnt;\n    for(int x: a) cnt[x]++;\n    vector<pair<int,int>> items(cnt.begin(), cnt.end());\n    sort(items.begin(), items.end(), [](auto&p, auto&q){\n        if(p.second!=q.second) return p.second>q.second;\n        return p.first<q.first;\n    });\n    for(int t=0;t<k;t++) cout<<items[t].first<<(t+1<k?" ":"\\n");\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        int[] a = new int[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextInt();\n        int k = sc.nextInt();\n        Map<Integer, Integer> cnt = new TreeMap<>();\n        for (int x : a) cnt.merge(x, 1, Integer::sum);\n        List<Map.Entry<Integer, Integer>> items = new ArrayList<>(cnt.entrySet());\n        items.sort((p, q) -> p.getValue().equals(q.getValue()) ? p.getKey() - q.getKey() : q.getValue() - p.getValue());\n        StringBuilder sb = new StringBuilder();\n        for (int t = 0; t < k; t++) sb.append(items.get(t).getKey()).append(t + 1 < k ? " " : "\\n");\n        System.out.print(sb);\n    }\n}\n',
        },
        "buggy": {
            'python': "from collections import Counter\nn = int(input())\na = list(map(int, input().split()))\nk = int(input())\ncnt = Counter(a)\nitems = sorted(cnt.items(), key=lambda x: (-x[1], -x[0]))\nprint(' '.join(str(v) for v, c in items[:k]))\n",
            'c': '#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\nint cmp_int(const void*a,const void*b){ return (*(int*)a)-(*(int*)b); }\ntypedef struct { int val, cnt; } VC;\nint cmp_final(const void*a,const void*b){\n    VC*x=(VC*)a,*y=(VC*)b;\n    if(x->cnt!=y->cnt) return y->cnt-x->cnt;\n    return y->val-x->val;\n}\nint main(void){\n    int n; scanf("%d",&n);\n    int *a=malloc(sizeof(int)*n);\n    for(int i=0;i<n;i++) scanf("%d",&a[i]);\n    int k; scanf("%d",&k);\n    int *sortedv=malloc(sizeof(int)*n);\n    memcpy(sortedv,a,sizeof(int)*n);\n    qsort(sortedv,n,sizeof(int),cmp_int);\n    VC *vc=malloc(sizeof(VC)*n);\n    int m=0, i=0;\n    while(i<n){\n        int j=i;\n        while(j<n && sortedv[j]==sortedv[i]) j++;\n        vc[m].val=sortedv[i]; vc[m].cnt=j-i; m++;\n        i=j;\n    }\n    qsort(vc,m,sizeof(VC),cmp_final);\n    for(int t=0;t<k;t++) printf("%d%s", vc[t].val, t+1<k?" ":"\\n");\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<int> a(n);\n    for(auto&x:a) cin>>x;\n    int k; cin>>k;\n    map<int,int> cnt;\n    for(int x: a) cnt[x]++;\n    vector<pair<int,int>> items(cnt.begin(), cnt.end());\n    sort(items.begin(), items.end(), [](auto&p, auto&q){\n        if(p.second!=q.second) return p.second>q.second;\n        return p.first>q.first;\n    });\n    for(int t=0;t<k;t++) cout<<items[t].first<<(t+1<k?" ":"\\n");\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        int[] a = new int[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextInt();\n        int k = sc.nextInt();\n        Map<Integer, Integer> cnt = new TreeMap<>();\n        for (int x : a) cnt.merge(x, 1, Integer::sum);\n        List<Map.Entry<Integer, Integer>> items = new ArrayList<>(cnt.entrySet());\n        items.sort((p, q) -> p.getValue().equals(q.getValue()) ? q.getKey() - p.getKey() : q.getValue() - p.getValue());\n        StringBuilder sb = new StringBuilder();\n        for (int t = 0; t < k; t++) sb.append(items.get(t).getKey()).append(t + 1 < k ? " " : "\\n");\n        System.out.print(sb);\n    }\n}\n',
        },
        "bug_category": 'wrong_comparison_operator',
        "task_description": 'When two values are tied on frequency, this solution should break the tie by picking the SMALLER value first, but the tie-break comparison is reversed, so it picks the larger value first. Find and fix the bug.',
    },
    {
        "id": 'adv-kth-largest-array',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint cmp_desc(const void*a,const void*b){ return (*(int*)b)-(*(int*)a); }\nint main(void){\n    int n; scanf("%d",&n);\n    int *a=malloc(sizeof(int)*n);\n    for(int i=0;i<n;i++) scanf("%d",&a[i]);\n    int k; scanf("%d",&k);\n    qsort(a,n,sizeof(int),cmp_desc);\n    printf("%d\\n", a[k-1]);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<int> a(n);\n    for(auto&x:a) cin>>x;\n    int k; cin>>k;\n    sort(a.rbegin(), a.rend());\n    cout<<a[k-1]<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        Integer[] a = new Integer[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextInt();\n        int k = sc.nextInt();\n        Arrays.sort(a, Collections.reverseOrder());\n        System.out.println(a[k - 1]);\n    }\n}\n',
        },
        "buggy": {
            'python': 'n = int(input())\na = list(map(int, input().split()))\nk = int(input())\nuniq_sorted = sorted(set(a), reverse=True)\nprint(uniq_sorted[k - 1])\n',
            'c': '#include <stdio.h>\n#include <stdlib.h>\nint cmp_desc(const void*a,const void*b){ return (*(int*)b)-(*(int*)a); }\nint main(void){\n    int n; scanf("%d",&n);\n    int *a=malloc(sizeof(int)*n);\n    for(int i=0;i<n;i++) scanf("%d",&a[i]);\n    int k; scanf("%d",&k);\n    qsort(a,n,sizeof(int),cmp_desc);\n    int *uniq=malloc(sizeof(int)*n);\n    int m=0;\n    for(int i=0;i<n;i++){\n        if(m==0 || uniq[m-1]!=a[i]) uniq[m++]=a[i];\n    }\n    printf("%d\\n", uniq[k-1]);\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<int> a(n);\n    for(auto&x:a) cin>>x;\n    int k; cin>>k;\n    sort(a.rbegin(), a.rend());\n    a.erase(unique(a.begin(), a.end()), a.end());\n    cout<<a.at(k-1)<<"\\n";\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        int[] a = new int[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextInt();\n        int k = sc.nextInt();\n        TreeSet<Integer> uniq = new TreeSet<>(Collections.reverseOrder());\n        for (int x : a) uniq.add(x);\n        List<Integer> list = new ArrayList<>(uniq);\n        System.out.println(list.get(k - 1));\n    }\n}\n',
        },
        "bug_category": 'missing_edge_case',
        "task_description": 'This k-th-largest solution deduplicates the array before indexing by position k-1 -- it works fine when all values are distinct, but undercounts (or goes out of bounds) whenever the array contains duplicate values, since those should still count separately toward the k-th position. Find and fix the bug.',
    },
    {
        "id": 'adv-min-stack',
        "ref": {
            'c': '#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *st=malloc(sizeof(long long)*(n>0?n:1));\n    long long *mn=malloc(sizeof(long long)*(n>0?n:1));\n    int sp=0, mp=0;\n    char op[10];\n    for(int q=0;q<n;q++){\n        scanf("%s", op);\n        if(strcmp(op,"PUSH")==0){\n            long long v; scanf("%lld",&v);\n            st[sp++]=v;\n            long long mv = (mp==0 || v<=mn[mp-1]) ? v : mn[mp-1];\n            mn[mp++]=mv;\n        } else if(strcmp(op,"POP")==0){\n            sp--; mp--;\n        } else if(strcmp(op,"TOP")==0){\n            printf("%lld\\n", st[sp-1]);\n        } else if(strcmp(op,"GETMIN")==0){\n            printf("%lld\\n", mn[mp-1]);\n        }\n    }\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> st, mn;\n    for(int q=0;q<n;q++){\n        string op; cin>>op;\n        if(op=="PUSH"){\n            long long v; cin>>v;\n            st.push_back(v);\n            long long mv = (mn.empty() || v<=mn.back()) ? v : mn.back();\n            mn.push_back(mv);\n        } else if(op=="POP"){\n            st.pop_back(); mn.pop_back();\n        } else if(op=="TOP"){\n            cout<<st.back()<<"\\n";\n        } else if(op=="GETMIN"){\n            cout<<mn.back()<<"\\n";\n        }\n    }\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        Deque<Long> st = new ArrayDeque<>();\n        Deque<Long> mn = new ArrayDeque<>();\n        StringBuilder sb = new StringBuilder();\n        for (int q = 0; q < n; q++) {\n            String op = sc.next();\n            if (op.equals("PUSH")) {\n                long v = sc.nextLong();\n                st.push(v);\n                long mv = (mn.isEmpty() || v <= mn.peek()) ? v : mn.peek();\n                mn.push(mv);\n            } else if (op.equals("POP")) {\n                st.pop(); mn.pop();\n            } else if (op.equals("TOP")) {\n                sb.append(st.peek()).append("\\n");\n            } else if (op.equals("GETMIN")) {\n                sb.append(mn.peek()).append("\\n");\n            }\n        }\n        System.out.print(sb);\n    }\n}\n',
        },
        "buggy": {
            'python': "n = int(input())\nstack = []\nminstack = []\nfor _ in range(n):\n    parts = input().split()\n    op = parts[0]\n    if op == 'PUSH':\n        v = int(parts[1])\n        stack.append(v)\n        if not minstack or v <= minstack[-1]:\n            minstack.append(v)\n        else:\n            minstack.append(minstack[-1])\n    elif op == 'POP':\n        minstack.pop()\n    elif op == 'TOP':\n        print(stack[-1])\n    elif op == 'GETMIN':\n        print(minstack[-1])\n",
            'c': '#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\nint main(void){\n    int n; scanf("%d",&n);\n    long long *st=malloc(sizeof(long long)*(n>0?n:1));\n    long long *mn=malloc(sizeof(long long)*(n>0?n:1));\n    int sp=0, mp=0;\n    char op[10];\n    for(int q=0;q<n;q++){\n        scanf("%s", op);\n        if(strcmp(op,"PUSH")==0){\n            long long v; scanf("%lld",&v);\n            st[sp++]=v;\n            long long mv = (mp==0 || v<=mn[mp-1]) ? v : mn[mp-1];\n            mn[mp++]=mv;\n        } else if(strcmp(op,"POP")==0){\n            mp--;\n        } else if(strcmp(op,"TOP")==0){\n            printf("%lld\\n", st[sp-1]);\n        } else if(strcmp(op,"GETMIN")==0){\n            printf("%lld\\n", mn[mp-1]);\n        }\n    }\n    return 0;\n}\n',
            'cpp': '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> st, mn;\n    for(int q=0;q<n;q++){\n        string op; cin>>op;\n        if(op=="PUSH"){\n            long long v; cin>>v;\n            st.push_back(v);\n            long long mv = (mn.empty() || v<=mn.back()) ? v : mn.back();\n            mn.push_back(mv);\n        } else if(op=="POP"){\n            mn.pop_back();\n        } else if(op=="TOP"){\n            cout<<st.back()<<"\\n";\n        } else if(op=="GETMIN"){\n            cout<<mn.back()<<"\\n";\n        }\n    }\n    return 0;\n}\n',
            'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        Deque<Long> st = new ArrayDeque<>();\n        Deque<Long> mn = new ArrayDeque<>();\n        StringBuilder sb = new StringBuilder();\n        for (int q = 0; q < n; q++) {\n            String op = sc.next();\n            if (op.equals("PUSH")) {\n                long v = sc.nextLong();\n                st.push(v);\n                long mv = (mn.isEmpty() || v <= mn.peek()) ? v : mn.peek();\n                mn.push(mv);\n            } else if (op.equals("POP")) {\n                mn.pop();\n            } else if (op.equals("TOP")) {\n                sb.append(st.peek()).append("\\n");\n            } else if (op.equals("GETMIN")) {\n                sb.append(mn.peek()).append("\\n");\n            }\n        }\n        System.out.print(sb);\n    }\n}\n',
        },
        "bug_category": 'state_tracking_error',
        "task_description": "This min-stack's POP operation only removes the top of the min-tracking stack -- it forgets to also remove the top of the main value stack, so the two stacks drift out of sync and later TOP calls return stale values. Find and fix the bug.",
    },
]


def _run_lang(language: str, code: str, stdin: str, timeout: int = 15) -> tuple:
    """Execute ``code`` once via the real (production) code_runner pipeline.
    Returns (ok, stdout_stripped). ``ok`` is False on any error/timeout/nonzero exit."""
    res = run_code(language, code, stdin, timeout=timeout)
    ok = (not res["error"]) and res["exit_code"] == 0 and not res["timed_out"]
    return ok, (res["stdout"] or "").strip()


def _hydrate(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Materialize one selected problem: pull its base fields from
    problem_bank.py and attach the multi-language reference_solution and
    debugging_variant. Deliberately CHEAP -- no code execution here.

    Earlier revision of this module actually executed every reference/buggy
    solution, every language, against every test case INSIDE this function,
    at import time (matching problem_bank.py's own fail-fast philosophy).
    That's fine for problem_bank.py, where every check is a fast native
    Python run -- it's actually correct here: an import-time hang. This
    module's checks involve compiling C/C++/Java 175 times over (25
    problems x ~7 solutions each), which measured ~27 minutes end to end.
    problem_bank.py gets imported by server.py at process startup; this
    module now does too (see server.py's dev-only debugging-run route) --
    an import that takes 27 minutes would make every server start (dev,
    test, prod) hang past any reasonable timeout, including the Playwright
    E2E suite's 90s webServer startup window. Execution verification still
    happens, just not on every import -- see verify_all() below, which is
    exactly the logic this function used to run inline, now callable
    on demand (already run to completion once, successfully, for all 25
    problems/languages, before this split -- see the session's own
    verification transcript)."""
    pid = raw["id"]
    base = _PB_BANK_BY_ID[pid]
    py_ref = _PB_RAW_BY_ID[pid]["reference_solution"]
    visible = base["visible_tests"] or []
    hidden = base["hidden_tests"] or []

    reference_solution = {"python": py_ref, "c": raw["ref"]["c"], "cpp": raw["ref"]["cpp"], "java": raw["ref"]["java"]}

    return {
        "id": pid,
        "title": base["title"],
        "difficulty": base["difficulty"],
        "topic": base["topic"],
        "statement": base["statement"],
        "input_format": base["input_format"],
        "output_format": base["output_format"],
        "constraints": base["constraints"],
        "visible_tests": visible,
        "hidden_tests": hidden,
        "reference_solution": reference_solution,
        "debugging_variant": {
            "buggy_code": raw["buggy"],
            "bug_category": raw["bug_category"],
            "task_description": raw["task_description"],
        },
    }


def verify_one(raw: Dict[str, Any], hydrated: Dict[str, Any]) -> None:
    """The expensive check _hydrate() used to run inline: ACTUALLY EXECUTE
    every reference/buggy solution, every language, against every test case,
    via the real code_runner pipeline. Raises on any inconsistency. Callable
    on demand (see verify_all()) -- NOT run automatically at import."""
    pid = raw["id"]
    tests = hydrated["visible_tests"] + hydrated["hidden_tests"]
    visible, hidden = hydrated["visible_tests"], hydrated["hidden_tests"]

    for lang, code in hydrated["reference_solution"].items():
        for t in tests:
            ok, got = _run_lang(lang, code, t["input"])
            want = t["expected_output"].strip()
            if not ok or got != want:
                raise RuntimeError(
                    f"debugging_bank: {pid!r} {lang} REFERENCE failed on input={t['input']!r} "
                    f"(ok={ok}, got={got!r}, want={want!r})"
                )

    for lang, code in raw["buggy"].items():
        any_visible_pass = False
        for t in visible:
            ok, got = _run_lang(lang, code, t["input"])
            if ok and got == t["expected_output"].strip():
                any_visible_pass = True
        if not any_visible_pass:
            raise RuntimeError(f"debugging_bank: {pid!r} {lang} BUGGY code fails ALL visible tests")

        any_hidden_fail = False
        for t in hidden:
            ok, got = _run_lang(lang, code, t["input"])
            if not (ok and got == t["expected_output"].strip()):
                any_hidden_fail = True
        if not any_hidden_fail:
            raise RuntimeError(f"debugging_bank: {pid!r} {lang} BUGGY code passes ALL hidden tests (no differentiation)")


def verify_all() -> None:
    """Run verify_one() over the whole pool. Expensive (~25-30 minutes --
    175 solutions, many requiring a fresh gcc/g++/javac compile). Meant to
    be run explicitly (a standalone script, or a CI/deploy step), never as
    a side effect of importing this module."""
    for raw in _RAW:
        verify_one(raw, _DEBUG_BANK_BY_ID[raw["id"]])


# Materialize the whole pool at import time. Cheap (no execution -- see
# _hydrate's docstring for why that changed). Correctness is guaranteed by
# verify_all() having been run to completion at least once against this
# exact content, not by this import itself.
_DEBUG_BANK: List[Dict[str, Any]] = [_hydrate(r) for r in _RAW]
_DEBUG_BANK_BY_ID: Dict[str, Dict[str, Any]] = {p["id"]: p for p in _DEBUG_BANK}
TOPICS: List[str] = sorted({p["topic"] for p in _DEBUG_BANK})


# ---- Cross-attempt repetition tracking --------------------------------
# Same collection-shape/interface convention as problem_bank.py's own
# get_seen_ids/mark_seen (itself modeled on mcq_static_bank.py's tracker),
# deliberately kept in ITS OWN collection (debugging_bank_seen) rather than
# reusing problem_bank's problem_bank_seen -- this is a separate ~25-item
# pool with its own topic-pairing draw rule, not a sub-split of the
# 104-item coding-round bank.
_db = None  # set by init(db)


def init(db) -> None:
    global _db
    _db = db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_seen_ids(user_id: str) -> Set[str]:
    if _db is None:
        return set()
    doc = await _db.debugging_bank_seen.find_one({"user_id": user_id})
    return set(doc.get("question_ids", [])) if doc else set()


async def mark_seen(user_id: str, question_ids: List[str]) -> None:
    if _db is None or not question_ids:
        return
    await _db.debugging_bank_seen.update_one(
        {"user_id": user_id},
        {"$addToSet": {"question_ids": {"$each": question_ids}}, "$set": {"updated_at": _now_iso()}},
        upsert=True,
    )


def sample_debug_session(exclude_ids: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """Draw exactly 1 problem for one debugging-round session, from the
    same 25-problem pool.

    CORRECTED (2026-09, R3/R4-config-correction pass): this used to draw
    2 problems forced to come from 2 DIFFERENT topics -- reversed per
    explicit instruction confirming the pattern is 1 problem per session;
    the topic-diversity draw rule no longer applies with only 1 problem
    to pick. Still returns a LIST (of length 1), not a bare dict -- every
    call site (server.py's "debugging" generation branch, which stores
    this directly into a section's `questions` array, and the strip
    whitelist / grading code that iterate over `questions`) already
    treats a debugging session as a list of problems, so keeping the
    list shape here means none of that call-site code needed to change.

    Falls back to allowing a repeat (problem_bank.py's same "never
    under-serve" philosophy) only in the degenerate case where
    exclude_ids has excluded literally every problem in the pool.
    """
    pool = [p for p in _DEBUG_BANK if p["id"] not in (exclude_ids or set())]
    if not pool:
        pool = _DEBUG_BANK[:]
    return [random.choice(pool)]


def get_problem(problem_id: str) -> Optional[Dict[str, Any]]:
    return _DEBUG_BANK_BY_ID.get(problem_id)


def grade_debugging_submission(problem: Dict[str, Any], code: str, language: str) -> Dict[str, Any]:
    """Grade a candidate's (edited) submission for one debugging problem by
    reusing code_runner.run_tests -- the exact same execution pipeline the
    existing 'coding' round's _grade_coding_section already uses in
    server.py.

    SCORE FORMULA (fixed 2026-10, R3-scoring-fix pass): previously a flat
    (visible_passed + hidden_passed) / total fraction, weighting visible
    and hidden tests equally. That let an unfixed buggy submission score
    >= the section's 0.5 cutoff whenever its injected bug only manifested
    on a narrow edge case one of the ~5 total tests happened to probe --
    confirmed for 16 of this bank's 25 problems by running this exact
    function against every problem's own unmodified buggy code. Hidden
    tests are the trustworthy signal for a debugging problem (visible
    tests are example-only, inspectable by the candidate before
    submitting) -- verify_one() below ALREADY enforces, at bank-build
    time, that every buggy variant in every language fails at least one
    hidden test, and every reference solution passes every visible+hidden
    test, in every language. So: if any hidden test still fails, score is
    explicitly capped below any reasonable pass cutoff (scaled by hidden-
    test fraction, not flattened to 0, so it stays informative -- closer
    to a real fix scores higher, just never high enough to cross 0.5).
    Only once every hidden test passes does this fall back to today's
    original combined fraction -- a correct reference solution's score is
    computed by that EXACT SAME branch as before this fix, byte for byte.
    `passed` (strict: every visible+hidden test, unchanged) was already
    correct and didn't need to change -- server.py's _grade_debugging_
    section never read it, only `score`, which is what this fixes.
    """
    visible = problem.get("visible_tests", []) or []
    hidden = problem.get("hidden_tests", []) or []
    vpass, vdetails = run_tests(language, code, visible)
    hpass, hdetails = run_tests(language, code, hidden)
    total = len(visible) + len(hidden)
    passed = vpass + hpass
    hidden_total = len(hidden)
    if hidden_total and hpass < hidden_total:
        hidden_fraction = hpass / hidden_total
        score = round(hidden_fraction * 0.49, 3)
    else:
        score = round(passed / total, 3) if total else 0.0
    return {
        "problem_id": problem["id"],
        "language": language,
        "visible": {"passed": vpass, "total": len(visible), "details": vdetails},
        "hidden": {"passed": hpass, "total": len(hidden), "details": hdetails},
        "score": score,
        "passed": passed == total,
    }
