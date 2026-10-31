import React from "react";
import { Link } from "react-router-dom";
import { COMPANIES } from "../../data/companies";
import CompanyLogo from "./CompanyLogo";

/**
 * "Crack interviews at" -- dashed-border chip grid (reference section
 * #companies). Each live company is a real <Link> to /company/:id (same
 * navigate-on-select rule as the hero's search field); the one non-live
 * entry (Microsoft SWE) renders disabled with "Rolling out next", never
 * navigates -- identical convention to ChooseCompanySection.jsx's tiles.
 */
export default function GlassCrackInterviews() {
  return (
    <section className="gl-sec gl-sec-tight-bottom" id="companies">
      <h2 className="gl-h2" style={{ textAlign: "center" }}>
        Crack <b>interviews</b> at
      </h2>
      <p className="gl-sub" style={{ margin: "0 auto 32px", textAlign: "center" }}>
        Each company runs on its own engine: real section order, real timing, real cutoffs.
      </p>
      <div className="gl-chips">
        {COMPANIES.map((c) =>
          c.live ? (
            <Link key={c.id} className="gl-chip" to={`/company/${c.id}`} title={c.name}>
              <CompanyLogo id={c.id} name={c.name} size={32} />
              <span className="sr-only">{c.name}</span>
            </Link>
          ) : (
            <div key={c.id} className="gl-chip" aria-disabled="true" title={`${c.name} — Rolling out next`}>
              <CompanyLogo id={c.id} name={c.name} size={32} />
              <span className="sr-only">{`${c.name} — Rolling out next`}</span>
            </div>
          )
        )}
      </div>
    </section>
  );
}
