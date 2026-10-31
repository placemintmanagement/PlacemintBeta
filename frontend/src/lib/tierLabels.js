// Display names for server-computed tiers/tracks. Pure constants, no
// logic -- extracted out of OAReview.jsx (which used these same two maps
// inline) so the new company hub can reuse them without duplicating the
// strings. Values unchanged from their original definition.
export const TIER_NAMES = { spark: "Spark", dave: "Dave", commit: "Commit" };

export const TCS_TRACK_NAMES = {
  ninja: "Ninja", digital: "Digital", prime: "Prime",
  not_qualified: "Below the estimated Foundation cutoff",
};
