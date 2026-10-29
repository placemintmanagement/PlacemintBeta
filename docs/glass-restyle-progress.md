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

Where browsing ends and navigation begins (judgment call, as the task invited): the hero's own
avatar row ("preparing for" switcher) is pure browse-preview — clicking an avatar restyles the
hero's caption/profile/readiness without navigating, same register as the reference. The
top-right "current selection" pill is the hero's real navigate affordance: it renders as an
actual `<Link to="/company/:id">…View plan →` for a live company (live-updated as you browse the
avatars), or plain disabled text ("Rolling out next") for Microsoft SWE. The nav's company
search (`CompanyFinder.jsx`, the reference's one shared search field) commits immediately on
Enter/click, same as the "Crack interviews at" chip grid (plain `<Link>` per live company,
disabled div for Microsoft SWE) — both of those are explicit "pick a company" UI, so they
navigate straight away rather than preview-then-commit. A visitor can always reach a real
`/company/:id` page through at least three of these paths.

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
- `cb4a94d` — progress log + plan.
- `169c6b5` — full landing rebuild: nav, hero state machine, crack-interviews chips, what-you-get
  picker, four phases, IDE mock, report section, FAQ, footer, `data/companies.js`,
  `glass.css`. `yarn build` clean, all 67 existing tests still pass.
- Fixed a bug caught via Playwright screenshot review: `&nearr;` (the phase-row arrow glyph)
  didn't decode in JSX and rendered as literal text, unlike `&rarr;`/`&middot;`/`&times;`
  elsewhere, which did — replaced with the numeric reference `&#8599;` (always decodes,
  no dependency on the parser's named-entity table). Verified via Playwright text extraction
  post-fix.
- Verified with Playwright: no horizontal overflow at 390px
  (`document.documentElement.scrollWidth === clientWidth === 390`); dark mode toggle flips
  `.glass-landing[data-theme]` without touching `/login`'s background (confirms the scoping
  holds); `/login` and `/company/:id` render in the untouched original teal design, confirming
  the logged-in/auth app is unaffected.

## Next
- Nothing blocking; the build is feature-complete against the task's section list. If there's
  time left: consider porting the reference's exact `i1`–`i6` decorative SVG background tiles
  into the "What you get" preview card (currently a generated `color-mix` gradient instead —
  same visual register, less literal) and double-checking color contrast (AA) on the glass
  panels' white-on-translucent text at every opacity used, which wasn't separately audited
  beyond eyeballing the screenshots.

## Issues / notes
- The hero's left "prep plan" panel's 4 phase rows and the bottom "Your four phases" segmented
  strip currently derive their copy from `components/PhaseStrip.jsx`'s exported `PHASES`
  (already-real site copy) rather than re-declaring it — if that file's copy changes, the hero
  picks it up automatically (intentional, not a loose end).
- `docs/glass-restyle-reference.html` is left untracked (matches how it was found in the
  worktree) — it's the design reference asset, not shipped product code.
- Old teal-design landing components (`HeroV2.jsx`, `FaqSection.jsx`, `WhatYouGetSection.jsx`,
  `IDEMockup.jsx`, `InsideYourReportSection.jsx`, `ClosingCTASection.jsx`,
  `StartPractisingSection.jsx`, `DifferentiatorCards.jsx`, `DepartmentCard.jsx`,
  `CrackInterviewsSection.jsx`) are no longer imported anywhere but were intentionally left in
  the tree, not deleted, so the change stays reversible and reviewable as a diff against
  `Landing.jsx` rather than a destructive rewrite. `ChooseCompanySection.jsx` is also now
  unused (it was already feature-flagged off before this task) but still compiles and its own
  tests/usages (none) are unaffected.
