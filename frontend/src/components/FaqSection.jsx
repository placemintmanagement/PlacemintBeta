import React, { useId, useState } from "react";

/**
 * "Questions people actually ask" -- the landing FAQ accordion.
 *
 * Behaviour: every item starts closed, and each item opens and closes
 * independently (several can be open at once). The question is a button with
 * aria-expanded and aria-controls; the answer is a region labelled by its
 * question. Enter and Space work because the question is a native button.
 * Open/close is a grid-template-rows 0fr -> 1fr transition, switched off
 * under prefers-reduced-motion in index.css (.pm-faq-*).
 */
const FAQ = [
  { q: "How is this different from other mock-test sites?", a: "Each company has its own structure, including section order, timing and cutoffs. Infosys' pseudocode section has a 65% cutoff, and Zoho runs three rounds: pen-and-paper aptitude, five basic programs, then advanced DSA." },
  { q: "What does a full run include?", a: "A run covers one company and includes the online assessment, an adaptive interview, and a final report that ties them together. The resume check is separate and unlimited." },
  { q: "Is Placemint connected to the companies it simulates?", a: "No. Company names are trademarks of their respective owners. Placemint is not affiliated with or endorsed by them." },
  { q: "Which languages do the coding rounds support?", a: "The coding rounds support Python, JavaScript, C, C++ and Java. Your code is run against each problem's test cases." },
  { q: "How are my coding answers checked?", a: "Each submission runs against two visible test cases and up to three hidden ones. AI feedback on your approach is guidance, not a guarantee." },
  { q: "How does the adaptive interview work?", a: "The interview asks one question at a time, built from your resume projects. It follows up when an answer is vague or incorrect." },
  { q: "What happens to my resume after I upload it?", a: "We store your resume text, its AI analysis and any uploaded PDF against your account, and only you can open them. If you delete your account, we wipe your profile, attempts and resume text within 7 days." },
  { q: "What does it cost?", a: "Run limits exist as a circuit breaker, not a marketing gate. Resume checker is free forever. Paid bundles: Basic is ₹399 a month, Pro is ₹799 a month, and MAX is ₹999 for a 90-day pass." },
];


function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" className="pm-faq-icon">
      <line x1="7" y1="1" x2="7" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="1" y1="7" x2="13" y2="7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function FaqItem({ item, index, open, onToggle }) {
  const id = useId();
  const qId = `${id}-q`;
  const aId = `${id}-a`;
  return (
    <div className="pm-faq-item bg-white" data-open={open} style={{ borderRadius: 20 }}>
      <h3 className="m-0">
        <button
          type="button"
          id={qId}
          aria-expanded={open}
          aria-controls={aId}
          onClick={() => onToggle(index)}
          className="pm-faq-q w-full flex items-center justify-between gap-4 text-left cursor-pointer bg-transparent border-0"
          style={{ minHeight: 64, padding: "20px 24px", borderRadius: 20, color: "#0B2A30" }}
        >
          <span className="pm-faq-q-text font-display font-semibold">{item.q}</span>
          <span className="pm-faq-tile shrink-0 grid place-items-center" style={{ width: 32, height: 32, borderRadius: 9999 }}>
            <PlusIcon />
          </span>
        </button>
      </h3>
      <div id={aId} role="region" aria-labelledby={qId} className="pm-faq-panel" data-open={open}>
        <div>
          <p style={{ padding: "0 24px 24px", fontSize: 16, lineHeight: 1.65, color: "rgba(11,42,48,0.75)", maxWidth: "62ch" }}>
            {item.a}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function FaqSection() {
  const [openItems, setOpenItems] = useState(() => FAQ.map(() => false));
  const toggle = (i) => setOpenItems((prev) => prev.map((v, j) => (j === i ? !v : v)));

  return (
    // White wrapper: the gap above the sky section is white (same as the
    // departments section above it), so the rounded top corners curve into
    // white instead of showing the dark page background.
    <div className="bg-white pt-8 lg:pt-0">
    <section
      id="faq"
      className="relative"
      style={{
        background: "var(--pm-sky)",
        borderTopLeftRadius: 56,
        borderTopRightRadius: 56,
        zIndex: 23,
      }}
    >
      <div className="max-w-[1200px] mx-auto px-6 lg:px-10 py-14 lg:py-24">
        <div className="lg:grid lg:grid-cols-[4fr_8fr] lg:gap-14 lg:items-start">
          <div className="lg:sticky lg:top-24 lg:self-start">
            <div
              className="uppercase"
              style={{ fontFamily: "var(--pm-font-label)", fontWeight: 600, fontSize: 13, letterSpacing: "0.06em", color: "var(--pm-teal-deep)" }}
            >
              FAQ
            </div>
            <h2
              className="font-display text-[#0B2A30] mt-3"
              style={{ fontWeight: 300, fontSize: "clamp(32px, 3.6vw, 44px)", lineHeight: 1.15, letterSpacing: "-0.02em" }}
            >
              Questions people{" "}
              <span style={{ fontWeight: 600, color: "var(--pm-teal-deep)" }}>actually ask</span>
            </h2>
            <p className="mt-3" style={{ fontSize: 17, lineHeight: 1.6, color: "rgba(11,42,48,0.75)" }}>
              Straight answers about how Placemint works.
            </p>


            <img
              src="/illustrations/student-lost.svg"
              alt=""
              aria-hidden="true"
              width={857}
              height={1244}
              loading="lazy"
              className="hidden lg:block mt-8 h-auto"
              style={{ maxWidth: 320 }}
            />
          </div>

          <div className="mt-10 lg:mt-0 flex flex-col gap-3">
            {FAQ.map((item, i) => (
              <FaqItem key={i} item={item} index={i} open={openItems[i]} onToggle={toggle} />
            ))}
          </div>
        </div>
      </div>
    </section>
    </div>
  );
}
