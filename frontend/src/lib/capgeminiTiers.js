// Tier chooser catalog for company-id-based interview starts. No endpoint
// returns this list (server.py exposes a tier only once it's been chosen
// or designated, never the catalog of choices), so it's hardcoded here --
// same pattern as tierLabels.js. Durations/stage counts are paraphrased
// from the backend's own documented tier table (capgemini_interview/
// core.py's TIER_TABLE comments), not fabricated.
export const TIER_CATALOG = {
  capgemini: [
    { id: "spark", name: "Spark", blurb: "35 min text interview — one project, follow-ups, one DSA problem." },
    { id: "dave", name: "Dave", blurb: "55 min text interview — two projects, DSA with complexity, CS fundamentals, HR." },
    { id: "commit", name: "Commit", blurb: "75 min text interview — the toughest bar: two projects, DSA efficiency, CS grilling, HR." },
  ],
};
