import React, { useState } from "react";
import api from "../api";
import Header from "../components/Header";
import DebuggingSection from "../components/DebuggingSection";

// Standing dev tool (not temporary) -- preview route (page itself isn't
// auth-gated, matching every other /dev/* preview) at /dev/debugging-preview
// for confirming the Debugging Assessment (Round 3) interface before it's
// wired into any real company round. These 2 problems are REAL entries from
// banks/debugging_bank.py's verified ~25-problem pool (ids "two-sum" and
// "tree-invert", picked from 2 different topics per the confirmed "2
// problems / 2 topics" session rule) -- statement, task_description, and
// all 4 languages' buggy_code are copied verbatim from that module, not
// hand-written mockups. Every one of them already passed debugging_bank.py's
// own verify_all() check (reference solutions execute correctly in all 4
// languages; buggy code passes >=1 visible test and fails >=1 hidden
// test, in all 4 languages) before being pasted here.
//
// Run/submit below hit a REAL backend endpoint (POST /api/dev/debugging/run)
// -- not a client-side simulation. That endpoint itself requires
// authentication like any other API route; opening this page in a real
// logged-in browser session works, and the Playwright E2E test authenticates
// via the same test-auth bypass used for the Round 1 click-through.
const SAMPLE_PROBLEMS = [
  {
    id: "two-sum",
    title: "Two Sum",
    difficulty: "Easy",
    topic: "arrays",
    statement:
      "Given an array `nums` and a target integer, return the 0-indexed positions of the two numbers whose sum equals the target. Each input has exactly one solution.\n\nExample: nums=[2,7,11,15], target=9 -> `0 1`.",
    input_format: "Line 1: n. Line 2: n space-separated integers. Line 3: target.",
    output_format: "Two space-separated indices (i < j).",
    constraints: "2 \u2264 n \u2264 10^4",
    visible_tests: [
      { input: "4\n2 7 11 15\n9", expected_output: "0 1" },
      { input: "3\n3 2 4\n6", expected_output: "1 2" },
    ],
    debugging_variant: {
      bug_category: "off_by_one",
      task_description:
        "This solution should return the indices of the two numbers that add up to the target, but it's returning nothing on some inputs. Find and fix the bug.",
      buggy_code: {
        python:
          "n = int(input())\na = list(map(int, input().split()))\nt = int(input())\nseen = {}\nfor i in range(1, n):\n    v = a[i]\n    if t - v in seen:\n        print(seen[t - v], i); break\n    seen[v] = i\n",
        c:
          '#include <stdio.h>\n#include <stdlib.h>\n#define SZ 200003\nlong long keys[SZ]; int vals[SZ]; int used[SZ];\nunsigned long hh(long long x){ unsigned long long ux=(unsigned long long)x; return (ux*2654435761ULL)%SZ; }\nint slot_of(long long x){ unsigned long idx=hh(x); while(used[idx] && keys[idx]!=x) idx=(idx+1)%SZ; return idx; }\nint main(void){\n    int n; scanf("%d",&n);\n    long long *a=malloc(sizeof(long long)*n);\n    for(int i=0;i<n;i++) scanf("%lld",&a[i]);\n    long long t; scanf("%lld",&t);\n    for(int i=1;i<n;i++){\n        long long need=t-a[i];\n        int s=slot_of(need);\n        if(used[s]){ printf("%d %d\\n", vals[s], i); return 0; }\n        int s2=slot_of(a[i]);\n        keys[s2]=a[i]; vals[s2]=i; used[s2]=1;\n    }\n    return 0;\n}\n',
        cpp:
          '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    int n; cin>>n;\n    vector<long long> a(n);\n    for(auto&x:a) cin>>x;\n    long long t; cin>>t;\n    unordered_map<long long,int> seen;\n    for(int i=1;i<n;i++){\n        long long need=t-a[i];\n        auto it=seen.find(need);\n        if(it!=seen.end()){ cout<<it->second<<" "<<i<<"\\n"; return 0; }\n        seen[a[i]]=i;\n    }\n    return 0;\n}\n',
        java:
          'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long[] a = new long[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n        long t = sc.nextLong();\n        Map<Long, Integer> seen = new HashMap<>();\n        for (int i = 1; i < n; i++) {\n            long need = t - a[i];\n            if (seen.containsKey(need)) { System.out.println(seen.get(need) + " " + i); return; }\n            seen.put(a[i], i);\n        }\n    }\n}\n',
      },
    },
  },
  {
    id: "tree-invert",
    title: "Invert Binary Tree",
    difficulty: "Easy",
    topic: "trees",
    statement:
      "Given a binary tree as a level-order list ('N' = missing child), invert it (swap every node's left and right children) and print the level-order traversal of the resulting tree, one line per level.",
    input_format: "Single line: level-order values with 'N' for null.",
    output_format: "One line per level of the inverted tree.",
    constraints: "1 <= number of real nodes <= 1000",
    visible_tests: [
      { input: "4 2 7 1 3 6 9", expected_output: "4\n7 2\n9 6 3 1" },
      { input: "1", expected_output: "1" },
    ],
    debugging_variant: {
      bug_category: "wrong_variable_reference",
      task_description:
        "This tree-inversion solution swaps each node's children correctly, but then recurses into the LEFT child twice instead of once into each child -- the right subtree never gets inverted below the top level. Find and fix the bug.",
      buggy_code: {
        python:
          "from collections import deque\nclass N:\n    def __init__(self, v):\n        self.v = int(v); self.l = None; self.r = None\ndef build(vals):\n    if not vals or vals[0] == 'N':\n        return None\n    root = N(vals[0]); q = deque([root]); i = 1\n    while q and i < len(vals):\n        node = q.popleft()\n        if i < len(vals) and vals[i] != 'N':\n            node.l = N(vals[i]); q.append(node.l)\n        i += 1\n        if i < len(vals) and vals[i] != 'N':\n            node.r = N(vals[i]); q.append(node.r)\n        i += 1\n    return root\nvals = input().split()\nroot = build(vals)\ndef invert(n):\n    if n is None: return\n    n.l, n.r = n.r, n.l\n    invert(n.l); invert(n.l)\ninvert(root)\nlevel = [root]\nwhile level:\n    print(' '.join(str(n.v) for n in level))\n    nxt = []\n    for n in level:\n        if n.l: nxt.append(n.l)\n        if n.r: nxt.append(n.r)\n    level = nxt\n",
        c:
          '#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\ntypedef struct Node { int v; struct Node *l,*r; } Node;\nNode* newnode(int v){ Node*n=malloc(sizeof(Node)); n->v=v; n->l=n->r=NULL; return n; }\nvoid invert(Node*n);\nint main(void){\n    char line[20000];\n    if(!fgets(line,sizeof(line),stdin)) line[0]=0;\n    line[strcspn(line,"\\r\\n")]=0;\n    char *toks[5000]; int ntok=0;\n    char *p=strtok(line," ");\n    while(p){ toks[ntok++]=p; p=strtok(NULL," "); }\n    if(ntok==0 || strcmp(toks[0],"N")==0){ return 0; }\n    Node *root=newnode(atoi(toks[0]));\n    Node *q[5000]; int qh=0,qt=0;\n    q[qt++]=root;\n    int i=1;\n    while(qh<qt && i<ntok){\n        Node *node=q[qh++];\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->l=newnode(atoi(toks[i])); q[qt++]=node->l; }\n        i++;\n        if(i<ntok && strcmp(toks[i],"N")!=0){ node->r=newnode(atoi(toks[i])); q[qt++]=node->r; }\n        i++;\n    }\n    invert(root);\n    Node *level[5000]; int lc=0;\n    level[lc++]=root;\n    while(lc>0){\n        for(int k=0;k<lc;k++) printf("%d%s", level[k]->v, k+1<lc?" ":"\\n");\n        Node *next[5000]; int nc=0;\n        for(int k=0;k<lc;k++){\n            if(level[k]->l) next[nc++]=level[k]->l;\n            if(level[k]->r) next[nc++]=level[k]->r;\n        }\n        for(int k=0;k<nc;k++) level[k]=next[k];\n        lc=nc;\n    }\n    return 0;\n}\nvoid invert(Node *n){\n    if(!n) return;\n    Node *t=n->l; n->l=n->r; n->r=t;\n    invert(n->l); invert(n->l);\n}\n',
        cpp:
          '#include <bits/stdc++.h>\nusing namespace std;\nstruct Node { int v; Node *l,*r; Node(int val):v(val),l(nullptr),r(nullptr){} };\nvoid invert(Node*n){ if(!n) return; swap(n->l, n->r); invert(n->l); invert(n->l); }\nint main(){\n    string line;\n    getline(cin, line);\n    istringstream iss(line);\n    vector<string> toks; string tok;\n    while(iss>>tok) toks.push_back(tok);\n    if(toks.empty() || toks[0]=="N") return 0;\n    Node *root=new Node(stoi(toks[0]));\n    queue<Node*> q; q.push(root);\n    size_t i=1;\n    while(!q.empty() && i<toks.size()){\n        Node *node=q.front(); q.pop();\n        if(i<toks.size() && toks[i]!="N"){ node->l=new Node(stoi(toks[i])); q.push(node->l); }\n        i++;\n        if(i<toks.size() && toks[i]!="N"){ node->r=new Node(stoi(toks[i])); q.push(node->r); }\n        i++;\n    }\n    invert(root);\n    vector<Node*> level = {root};\n    while(!level.empty()){\n        for(size_t k=0;k<level.size();k++) cout<<level[k]->v<<(k+1<level.size()?" ":"\\n");\n        vector<Node*> next;\n        for(auto n: level){\n            if(n->l) next.push_back(n->l);\n            if(n->r) next.push_back(n->r);\n        }\n        level = next;\n    }\n    return 0;\n}\n',
        java:
          'import java.io.*;\nimport java.util.*;\npublic class Main {\n    static class Node { int v; Node l, r; Node(int val){ v = val; } }\n    static void invert(Node n) { if (n == null) return; Node t = n.l; n.l = n.r; n.r = t; invert(n.l); invert(n.l); }\n    public static void main(String[] args) throws IOException {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        String line = br.readLine(); if (line == null) line = "";\n        String[] toks = line.trim().isEmpty() ? new String[0] : line.trim().split("\\\\s+");\n        if (toks.length == 0 || toks[0].equals("N")) return;\n        Node root = new Node(Integer.parseInt(toks[0]));\n        Deque<Node> q = new ArrayDeque<>();\n        q.add(root);\n        int i = 1;\n        while (!q.isEmpty() && i < toks.length) {\n            Node node = q.poll();\n            if (i < toks.length && !toks[i].equals("N")) { node.l = new Node(Integer.parseInt(toks[i])); q.add(node.l); }\n            i++;\n            if (i < toks.length && !toks[i].equals("N")) { node.r = new Node(Integer.parseInt(toks[i])); q.add(node.r); }\n            i++;\n        }\n        invert(root);\n        List<Node> level = new ArrayList<>(); level.add(root);\n        StringBuilder sb = new StringBuilder();\n        while (!level.isEmpty()) {\n            for (int k = 0; k < level.size(); k++) sb.append(level.get(k).v).append(k + 1 < level.size() ? " " : "\\n");\n            List<Node> next = new ArrayList<>();\n            for (Node n : level) {\n                if (n.l != null) next.add(n.l);\n                if (n.r != null) next.add(n.r);\n            }\n            level = next;\n        }\n        System.out.print(sb);\n    }\n}\n',
      },
    },
  },
];

export default function DevDebuggingPreview() {
  const [answers, setAnswers] = useState({});
  const [running, setRunning] = useState(false);
  const [runResults, setRunResults] = useState(null);
  const [submitted, setSubmitted] = useState(null);

  const setAnswer = (key, value) => setAnswers((prev) => ({ ...prev, [key]: value }));

  // REAL grading -- hits POST /api/dev/debugging/run (server.py), which
  // calls debugging_bank.grade_debugging_submission(), which itself reuses
  // code_runner.run_tests() -- the exact same pipeline the live "coding"
  // round's _grade_coding_section already uses. Requires the viewer to be
  // authenticated (this page itself isn't auth-gated, matching every other
  // /dev/* preview, but the API call underneath it needs a real user or the
  // Playwright E2E test-auth bypass -- see api.js's request interceptors).
  //
  // NOTE for whoever eventually wires a REAL Round 3 section: this dev
  // route's response shape intentionally includes full hidden-test
  // input/expected/got detail, because there's no live candidate attempt to
  // protect here. A real section endpoint must NOT return hidden test
  // detail this way -- follow get_oa's existing strip_answer() convention
  // instead (see server.py's get_oa docstring).
  const runOne = async (problem, current) => {
    const { data } = await api.post("/dev/debugging/run", {
      problem_id: problem.id,
      language: current.language,
      code: current.code,
    });
    return data;
  };

  const realRun = async (problem, current) => {
    setRunning(true);
    try {
      const data = await runOne(problem, current);
      const results = (data.visible.details || []).map((d) => ({
        input: d.input,
        expected: d.expected,
        got: d.got,
        passed: d.passed,
        error: d.error,
      }));
      setRunResults(results);
    } catch (err) {
      setRunResults([{ input: "", expected: "", got: "", passed: false, error: err.response?.data?.detail || err.message }]);
    } finally {
      setRunning(false);
    }
  };

  const realSubmitSession = async () => {
    const results = [];
    for (const p of SAMPLE_PROBLEMS) {
      const current = answers[p.id] || { language: "python", code: "" };
      try {
        const data = await runOne(p, current);
        results.push({ problem_id: p.id, language: current.language, passed: data.passed, score: data.score, visible: data.visible, hidden: { passed: data.hidden.passed, total: data.hidden.total } });
      } catch (err) {
        results.push({ problem_id: p.id, language: current.language, passed: false, error: err.response?.data?.detail || err.message });
      }
    }
    setSubmitted(results);
  };

  return (
    <div>
      <Header />
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-8">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-1">dev preview · not a real route</div>
        <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
          <h1 className="font-display text-3xl font-bold">Debugging Assessment: interface preview</h1>
          <button
            className="pm-btn pm-btn-primary text-sm py-2 px-4"
            onClick={realSubmitSession}
          >
            Submit session
          </button>
        </div>

        {submitted ? (
          <div className="pm-card p-6">
            <div className="font-display text-lg font-semibold mb-3">Session complete</div>
            <pre className="text-xs font-mono bg-pm-muted rounded-lg p-4 overflow-auto">
              {JSON.stringify(submitted, null, 2)}
            </pre>
            <button
              className="pm-btn pm-btn-ghost mt-4 text-sm py-2 px-4"
              onClick={() => { setSubmitted(null); setRunResults(null); }}
            >
              Restart preview
            </button>
          </div>
        ) : (
          <DebuggingSection
            problems={SAMPLE_PROBLEMS}
            answers={answers}
            setAnswer={setAnswer}
            onRun={realRun}
            running={running}
            runResults={runResults}
          />
        )}
      </div>
    </div>
  );
}
