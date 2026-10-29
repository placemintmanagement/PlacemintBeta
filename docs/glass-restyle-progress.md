# Glass restyle — progress log

Branch: `glass-restyle` (off `design-rollout` @ 887380f / tag `teal-design-final`).
Reference: `docs/glass-restyle-reference.html` (read in full, including the `<script>` state
machine, before starting).

## Plan

Translate the reference's glassmorphic design system into real React components, landing
page only (`frontend/src/pages/Landing.jsx` + new `frontend/src/components/glass/*`). Old
teal-design landing components are left in the tree (unused) rather than deleted, so this is
reversible; `Landing.jsx` is rewritten to use the new components.

### Section → component map
- Nav → `components/glass/GlassNav.jsx`
- Hero stage → `components/glass/GlassHero.jsx` (+ `CompanyFinder.jsx`, `PersonIllustration.jsx`,
  `Readiness.jsx` for the abstract "sectional readiness" card)
- "Crack interviews at" chip grid → `components/glass/GlassCrackInterviews.jsx`
- "What you get" interactive picker → `components/glass/GlassWhatYouGet.jsx`
- "Four phases. One story." → `components/glass/GlassFourPhases.jsx`
- IDE mock → `components/glass/GlassIdeSection.jsx`
- Report section → `components/glass/GlassReportSection.jsx`
- FAQ → `components/glass/GlassFaq.jsx`
- Footer → `components/glass/GlassFooter.jsx` (landing-only; shared `components/Footer.jsx`
  used by other pages is untouched)
- Shared CSS → `components/glass/glass.css` (scoped under `.glass-landing`, never touches
  `:root` or other pages)

### Company data / routing
Real list + live/not-live status already existed, pre-vetted against `backend/companies.py`,
in `components/ChooseCompanySection.jsx`'s `COMPANIES` const (13 entries: 12 live + Microsoft
SWE not-live; the 2 generic/placeholder backend entries — `product-general`,
`core-default` — correctly excluded). Moved verbatim into `frontend/src/data/companies.js` as
the single shared source; `ChooseCompanySection.jsx` now imports it too (no behavior change,
dedup only — that component is currently feature-flagged off anyway).

Hero avatar row / chips / search all browse-preview the hero copy as you move through them;
selecting a **live** company (Enter in search, click an avatar twice / click a chip, or
"View <company>" inside the hero) navigates to `/company/:id`. Non-live (Microsoft SWE) is
always rendered disabled with a "Rolling out next" state, never navigates — matches
`ChooseCompanySection`'s existing convention.

### Honesty-rule decision (hero demo)
**Chosen: qualitative/abstract, not "Preview"-labeled percentages.** The reference's radar
chart and the report-card progress bars use a formula-generated or hardcoded numeric scale
with no disclaimer inside the hero itself. Rather than relying on a label to excuse a
numbers-shaped visual, the hero's "sectional readiness" card and the 4-phase timeline/segment
indicators carry **no numbers, no percentages, no computed "scores"** at all — only qualitative
shape/fill (a hexagon outline that fills in by topic-count, not by value) and plain state
(done / current / upcoming). This matches the hard "no numbers" rule already applied to every
icon-only mock elsewhere in this app, and means the rule holds even if a visitor screenshots
just the hero with no caption. The separate, already-existing report section
(`InsideYourReportSection.jsx` content, carried into `GlassReportSection.jsx`) keeps its
existing, ALREADY-labeled "Illustrative example" / "Illustrative layout, not real results."
treatment unchanged — that one was fine as-is per the task brief.
The interactive STATE MACHINE (idle → recording → 4 phases → stopped/report-ready, with a
"Recording 00:14"-style timer and a visible phase indicator) is kept in full — only the
numeric-looking score visuals are made non-numeric.

### Dark mode
Scoped to `.glass-landing` only (CSS vars + `@media (prefers-color-scheme: dark)` guarded by
`:not([data-theme="light"])`, + `[data-theme="dark"]` manual override), never touching `:root`
or any other page. Manual toggle added to `GlassNav`. Status: see "Done" below.

## Done
- (fill in as committed)

## Next
- (fill in)

## Issues / notes
- (fill in)
