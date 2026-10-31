import React from "react";
import { Link } from "react-router-dom";
import { Clock, ChevronRight, TriangleAlert } from "lucide-react";
import { TID } from "../testIds";

// gl-text / gl-accent as RGB triplets so every text colour on this card can
// be expressed as rgba(INK, alpha) -- lets the "not yet available" card
// variant apply its own 70%-of-normal-alpha rule (spec) with one
// multiplier instead of a second hardcoded colour per element. Glass
// restyle (2026-11): INK matches --gl-text's own near-black (#0b0b0b);
// ACCENT matches --gl-accent (#be185d), the glass system's one vivid
// emphasis colour, standing in for the old TEAL_DEEP accent role.
const INK = "11,11,11";
const ACCENT = "190,24,93";

// Cycles through the four glass header tints in card order (spec item 3) --
// index is this card's position across the WHOLE page (DepartmentCompanies
// passes a running counter spanning all groups, not reset per group).
const HEADER_TINTS = ["var(--gl-blue)", "var(--gl-mint)", "var(--gl-sand)", "var(--gl-pink)"];

// The data source's `tagline` is one string with "→" between section
// names (confirmed against the live API response) -- spec item 1 wants
// it split at RENDER time, never edited at the source, and also handles
// "->" and "&rarr;" in case either ever shows up. Already-array taglines
// are used as-is.
function splitFlow(tagline) {
  if (Array.isArray(tagline)) return tagline.map((s) => String(s).trim()).filter(Boolean);
  if (!tagline) return [];
  return String(tagline)
    .split(/→|->|&rarr;/)
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Company-selection cards (DepartmentCompanies.jsx, 2026-10 redesign --
 * removes the arrow-joined flow string in favour of a numbered step
 * list, moves the duration chip out of a new tinted header, and
 * replaces the old grey pill "chips" with a plain dotted notes list).
 * Glass restyle (2026-11): uses the shared `.gl-card`/`.gl-card-
 * interactive`/`.gl-btn` primitives (glass.css) for the card shell,
 * hover lift, and Start button; the step connector line keeps its own
 * small scoped classes (`.gl-dc-step`/`-connected`, glass.css) since
 * that layout trick isn't shared with anything else yet.
 */
export default function CompanyCard({ company, index = 0 }) {
  const unverified = !company.verified && !company.generic;
  const generic = !!company.generic;
  // "Not yet available" cards use every text colour below at 70% of its
  // normal alpha (spec, item 6) -- one multiplier instead of a parallel
  // set of hardcoded rgba values.
  const dim = unverified ? 0.7 : 1;
  const headerTint = HEADER_TINTS[index % HEADER_TINTS.length];

  const steps = splitFlow(company.tagline);
  const notes = company.chips || [];

  const nameEl = (
    <div className="font-semibold leading-[1.15]" style={{ fontFamily: "Outfit, system-ui, sans-serif", fontSize: 22, color: `rgba(${INK},${dim})` }}>
      {company.name}
    </div>
  );

  return (
    <div
      data-testid={TID.companyCard(company.id)}
      className={`relative flex flex-col h-full overflow-hidden gl-card-interactive ${unverified ? "" : "gl-card"}`}
      style={{
        background: unverified ? "transparent" : undefined,
        borderRadius: 24,
        border: unverified ? "1.5px dashed var(--gl-line)" : undefined,
      }}
    >
      {unverified && (
        <div
          className="absolute top-2 right-2 inline-flex items-center gap-1 rounded-full z-10"
          style={{ background: "var(--gl-sand)", color: "var(--gl-text)", fontSize: 12, padding: "4px 10px" }}
        >
          <TriangleAlert size={12} /> not confirmed
        </div>
      )}
      {generic && (
        <div
          className="absolute top-2 right-2 inline-flex items-center gap-1 rounded-full z-10"
          style={{ background: "var(--gl-blue)", color: "var(--gl-text)", fontSize: 12, padding: "4px 10px" }}
        >
          <TriangleAlert size={12} /> general practice
        </div>
      )}

      {/* Tinted header -- spec item 3. Not-yet-available cards get no
          header at all (item 6); the name renders as the first thing in
          the body instead. */}
      {!unverified && (
        <div className="flex items-end" style={{ background: headerTint, minHeight: 96, padding: "22px 24px" }}>
          {nameEl}
        </div>
      )}

      <div className="flex flex-col flex-1" style={{ padding: unverified ? "24px 24px 24px" : "20px 24px 24px", gap: 18 }}>
        {unverified && nameEl}

        {/* a) Meta row */}
        <div className="flex items-center flex-wrap gap-x-2 gap-y-1">
          <span className="inline-flex items-center gap-1 rounded-full shrink-0" style={{ background: "var(--gl-mint)", padding: "4px 10px" }}>
            <Clock size={12} style={{ color: `rgba(${ACCENT},${dim})` }} />
            <span style={{ fontSize: 13, color: `rgba(${INK},${dim})` }}>{company.time_minutes}m</span>
          </span>
          {/* .60 (spec) measured 4.18:1 on white -- fails AA for this
              13px text, the same recurring pattern hit and fixed the
              same way several times earlier this session. .70 clears
              it: 5.7:1+. Same fix applied to the "section order"/
              "details" labels and the footer slug below. */}
          <span style={{ fontSize: 13, color: `rgba(${INK},${0.7 * dim})` }}>
            {company.sections?.length ?? 0} sections • {company.scoring_mode === "sectional" ? "sectional cutoffs" : "composite score"}
          </span>
        </div>

        {/* b) Section order -- numbered steps parsed from the tagline
            string at render time, never from edited data. */}
        {steps.length > 0 && (
          <div>
            <div
              className="mb-2.5"
              style={{
                fontFamily: "Poppins, system-ui, sans-serif",
                fontWeight: 600,
                fontSize: 11,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: `rgba(${INK},${0.7 * dim})`,
              }}
            >
              Section order
            </div>
            <div className="flex flex-col" style={{ gap: 10 }}>
              {steps.map((step, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className={`gl-dc-step shrink-0 ${steps.length > 1 && i > 0 ? "gl-dc-step-connected" : ""}`}>
                    <div
                      className="flex items-center justify-center rounded-full"
                      style={{ width: 22, height: 22, background: "var(--gl-blue)" }}
                    >
                      <span style={{ fontFamily: "Poppins, system-ui, sans-serif", fontWeight: 600, fontSize: 11, color: `rgba(${ACCENT},${dim})` }}>
                        {i + 1}
                      </span>
                    </div>
                  </div>
                  <span style={{ fontSize: 14, color: `rgba(${INK},${0.85 * dim})` }}>{step}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* c) Notes -- plain dotted list, replaces the old grey pills. */}
        {notes.length > 0 && (
          <div>
            <div
              className="mb-2"
              style={{
                fontFamily: "Poppins, system-ui, sans-serif",
                fontWeight: 600,
                fontSize: 11,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: `rgba(${INK},${0.7 * dim})`,
              }}
            >
              Details
            </div>
            <div className="flex flex-col" style={{ gap: 8 }}>
              {notes.map((note, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span
                    className="shrink-0 rounded-full"
                    style={{ width: 6, height: 6, marginTop: 7, background: `rgba(${ACCENT},${dim})` }}
                  />
                  <span style={{ fontSize: 13.5, color: `rgba(${INK},${0.8 * dim})` }}>{note}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer -- divider + slug + Start */}
        <div
          className="mt-auto flex items-center justify-between"
          style={{ borderTop: "1px solid var(--gl-line)", paddingTop: 18 }}
        >
          <span
            style={{
              fontFamily: "Poppins, system-ui, sans-serif",
              fontWeight: 600,
              textTransform: "uppercase",
              fontSize: 12,
              letterSpacing: "0.06em",
              color: `rgba(${INK},${0.7 * dim})`,
            }}
          >
            {company.id}
          </span>
          <Link
            to={`/company/${company.id}`}
            data-testid={TID.companyStartBtn(company.id)}
            className="gl-btn y font-semibold inline-flex items-center gap-1 text-sm"
            style={{ fontFamily: "Outfit, system-ui, sans-serif", padding: "0.5rem 1rem" }}
          >
            Start <ChevronRight size={14} />
          </Link>
        </div>
      </div>
    </div>
  );
}
