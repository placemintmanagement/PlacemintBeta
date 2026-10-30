import React from "react";

// All 8 real FAQ entries, verbatim from components/FaqSection.jsx (teal
// design) -- the reference mockup's own 4 FAQ entries are placeholder
// copy and are not used.
const FAQ = [
  { q: "How is this different from other mock-test sites?", a: "Each company's track follows that company's own format: its section order, timing, cutoffs and gating, instead of one generic template." },
  { q: "What does a full run include?", a: "A run covers one company. It includes that company's online assessment, an interview and a final report that ties them together. The steps depend on the company's track. The resume check is separate and unlimited." },
  { q: "Is HireTric connected to the companies it simulates?", a: "No. Company names are trademarks of their respective owners. HireTric is not affiliated with or endorsed by them." },
  { q: "Which languages do the coding rounds support?", a: "In coding rounds, you can write in Python, JavaScript, C, C++ or Java. Your code is run against each problem's test cases." },
  { q: "How are my coding answers checked?", a: "Where a track has a coding round, each submission runs against visible and hidden test cases. AI feedback on your approach is guidance, not a guarantee." },
  { q: "How does the adaptive interview work?", a: "The interview asks one question at a time, with a one-line verdict after each answer. The questions are planned for the company you chose, and draw on your resume when one is attached." },
  { q: "What happens to my resume after I upload it?", a: "We store your resume text, its AI analysis and any uploaded PDF against your account, and only you can open them. If you delete your account, we wipe your profile, attempts and resume text within 7 days." },
  { q: "What does it cost?", a: "Run limits exist as a circuit breaker, not a marketing gate. Resume checker is free forever. Paid bundles: Basic is ₹399 a month, Pro is ₹799 a month, and MAX is ₹999 for a 90-day pass." },
];

export default function GlassFaq() {
  return (
    <section className="gl-sec gl-faq" id="faq" style={{ maxWidth: 820 }}>
      <h2 className="gl-h2">Questions, <b>answered.</b></h2>
      <p className="gl-sub">Short answers before you sign up.</p>
      {FAQ.map((item) => (
        <details key={item.q}>
          <summary>{item.q}</summary>
          <p>{item.a}</p>
        </details>
      ))}
    </section>
  );
}
