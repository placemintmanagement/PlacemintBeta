import React from "react";
import { Link } from "react-router-dom";
import useRevealOnView from "../hooks/useRevealOnView";

/**
 * "Choose your company" (Landing.jsx, 2026-10). Cream section, between
 * What you get (white) and the closing CTA (sky) -- there is no public
 * sample round in this app, so the "Sample round" banner originally
 * planned for that slot was cancelled, not built. Structure only, taken
 * from a reference company-tile row -- no artwork, copy, logos or
 * colours copied from it. Monograms are plain initials, never a real
 * company logo.
 *
 * Company list and live/verified status pulled directly from
 * backend/companies.py (not guessed) -- only named, verified companies
 * count as "Live"; the one unverified named pattern (Microsoft SWE) is
 * "Coming soon". The two generic/placeholder entries in that file
 * ("Product Company (Generic)", "Core Assessment (Default)") aren't real
 * companies, so they're left out entirely.
 */
const TINTS = ["rgba(15,111,122,0.14)", "rgba(198,242,78,0.35)", "#E8F3FB", "#F2EDDF"];

const COMPANIES = [
  { id: "tcs-nqt", name: "TCS NQT", live: true },
  { id: "infosys", name: "Infosys", live: true },
  { id: "wipro", name: "Wipro Elite NTH", live: true },
  { id: "cognizant", name: "Cognizant GenC", live: true },
  { id: "accenture", name: "Accenture", live: true },
  { id: "ibm", name: "IBM", live: true },
  { id: "zoho", name: "Zoho", live: true },
  { id: "capgemini", name: "Capgemini", live: true },
  { id: "hcltech", name: "HCLTech", live: true },
  { id: "ltimindtree", name: "LTIMindtree", live: true },
  { id: "tech-mahindra", name: "Tech Mahindra", live: true },
  { id: "deloitte-usi", name: "Deloitte USI", live: true },
  { id: "microsoft-swe", name: "Microsoft SWE", live: false },
];

function monogram(name) {
  const words = name.split(" ").filter(Boolean);
  return ((words[0]?.[0] || "") + (words[1]?.[0] || "")).toUpperCase();
}

function Tile({ company, index }) {
  const tint = TINTS[index % TINTS.length];
  const inner = (
    <>
      <div className="w-12 h-12 rounded-full grid place-items-center font-display font-bold text-sm" style={{ background: tint, color: "#0B2A30" }}>
        {monogram(company.name)}
      </div>
      <div className="mt-3 font-display font-semibold text-sm text-center leading-snug" style={{ color: "#0B2A30" }}>
        {company.name}
      </div>
      {!company.live && (
        <span
          className="mt-2 px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wide"
          style={{ background: "rgba(11,42,48,0.08)", color: "rgba(11,42,48,0.65)" }}
        >
          Coming soon
        </span>
      )}
    </>
  );

  const baseClass = "flex flex-col items-center justify-center text-center p-5 rounded-[20px] bg-white transition-all duration-200";
  const baseStyle = {
    border: company.live ? "1px solid #F2EDDF" : "1px solid #F2EDDF",
    opacity: company.live ? 1 : 0.65,
  };

  if (!company.live) {
    return (
      <div className={baseClass} style={{ ...baseStyle, cursor: "default" }} aria-disabled="true">
        {inner}
      </div>
    );
  }

  return (
    <Link
      to={`/company/${company.id}`}
      className={`${baseClass} group`}
      style={baseStyle}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "#0F6F7A";
        e.currentTarget.style.borderWidth = "2px";
        e.currentTarget.style.boxShadow = "0 10px 28px rgba(15,111,122,0.18)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "#F2EDDF";
        e.currentTarget.style.borderWidth = "1px";
        e.currentTarget.style.boxShadow = "none";
      }}
    >
      {inner}
    </Link>
  );
}

export default function ChooseCompanySection() {
  const [rootRef, revealed] = useRevealOnView({ threshold: 0.15, fallbackMs: 500 });

  return (
    <section style={{ background: "var(--pm-cream)" }}>
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-24">
        <div className="text-center mb-12">
          <h2 className="font-display text-3xl lg:text-4xl font-bold inline-block relative" style={{ color: "#0B2A30" }}>
            Pick your company.
            <svg viewBox="0 0 220 16" width="180" height="13" className="block mx-auto mt-1" aria-hidden="true">
              <path
                d="M6 8 C 40 2, 80 13, 110 7 S 180 2, 214 9"
                fill="none"
                stroke="var(--pm-lime)"
                strokeWidth="5"
                strokeLinecap="round"
              />
            </svg>
          </h2>
          <p className="mt-3 text-base" style={{ color: "rgba(11,42,48,0.70)" }}>Each one runs on its own engine.</p>
        </div>

        <div
          ref={rootRef}
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4"
        >
          {COMPANIES.map((c, i) => (
            <div
              key={c.id}
              style={{
                opacity: revealed ? 1 : 0,
                transform: revealed ? "translateY(0)" : "translateY(14px)",
                transition: "opacity 450ms, transform 450ms",
                transitionDelay: revealed ? `${(i % 10) * 60}ms` : "0ms",
              }}
            >
              <Tile company={c} index={i} />
            </div>
          ))}
        </div>
        {/* "View all companies ->" omitted -- no dedicated all-companies
            route exists (individual companies are reached via
            /company/:id or the departments grid, not a standalone list
            page), per the instruction's own conditional. */}
      </div>
    </section>
  );
}
