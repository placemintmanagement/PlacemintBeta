/**
 * Shared company list for the landing page (glass restyle, 2026-10).
 *
 * Pulled from backend/companies.py's COMPANIES: every real, named company
 * entry with "verified": true is `live: true`; "Microsoft SWE" is the one
 * named-but-unverified entry, so it's `live: false` ("Rolling out next").
 * The two generic/placeholder entries in that file ("Product Company
 * (Generic)" / id "product-general", "Core Assessment (Default)" / id
 * "core-default") aren't real companies and are intentionally left out.
 *
 * This exact id/name/live set already existed, independently verified
 * against the backend, in components/ChooseCompanySection.jsx -- moved
 * here verbatim as the single shared source so the new glass hero/chip
 * grid and that component both read from one place.
 */
export const COMPANIES = [
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

export function monogram(name) {
  const words = name.split(" ").filter(Boolean);
  return ((words[0]?.[0] || "") + (words[1]?.[0] || "")).toUpperCase();
}
