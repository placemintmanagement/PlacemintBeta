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
- **Hero person element: full rework, standing SVG → framed photo window.** Original request
  was narrower (swap the SVG `PersonIllustration` for a photo in the two existing slots), but
  went through many rounds based on direct product-owner review of live screenshots:
  1. First pass: an AI-generated PORTRAIT photo (1792x2400, 0.75:1) dropped into a `.gl-video`
     "video window" card sized to the `.gl-mid` grid column. Composition read as 3 roughly-equal
     columns side by side, not the dominant-photo-with-floating-panels look the reference
     ("Int." interview UI) implied.
  2. Redesigned `.gl-stage` to a single-column layout: `.gl-video` became a full-bleed
     `position:absolute;inset:0` background layer (same role the radial-gradient background/the
     mockup's own standing silhouette used to play), `.gl-left`/`.gl-right` pulled out of grid
     flow into narrow (232–252px) `position:absolute` floating glass panels near the edges.
     This is the composition that stuck for the rest of the session.
  3. The portrait photo's 0.75:1 aspect against the stage's ~1.76:1 forced a brutal ~58% height
     crop, making `object-position` extremely sensitive (tuned 3 times chasing head/chin
     clearance) — concluded a portrait photo fundamentally can't frame well in a landscape
     window. Replaced with an AI-generated LANDSCAPE photo (`hero-person-wide.png`,
     2752x1536, 1.79:1) — near-exact match to the stage's aspect, crop became trivial.
  4. Hit two real structural bugs along the way, both caught live (not assumed) and fixed:
     - `.gl-stage`'s `grid-template-rows: auto 1fr auto` left the middle `1fr` track empty once
       everything in it went `position:absolute`; `.gl-tline` (still grid-flow at the time)
       auto-placed into that now-empty row instead of the bottom row, floating mid-page.
       Fixed by pulling `.gl-tline` out of grid flow too (`position:absolute`, bottom-anchored
       at the stage's own 22px padding, same as the other panels).
     - The mobile (`<=980px`) breakpoint resets `.gl-mid`/`.gl-tline` back to `position:static`
       for stacking, but the base rules set `position`/`z-index` with `!important` (needed to
       escape `.gl-stage > *`'s generic reset and to out-rank `.gl-tline`'s z-index) — a
       non-`!important` override inside a media query cannot beat an `!important` base rule
       regardless of source order, so the card/strip stayed absolutely positioned and floated
       over the stacked mobile content. Fixed by adding `!important` to the mobile overrides too.
     - Separately, once `.gl-tline` was back in grid flow at mobile, its non-shrinking
       `.gl-seg` children (`flex: 1 0 170px` × 4) gave the single `1fr` column a ~708px
       min-content floor, overflowing the 390px viewport (clipped invisibly by
       `.glass-landing`'s own `overflow-x: clip`, silently hiding "Sign up"). Fixed with the
       standard CSS Grid fix: `min-width: 0` on `.gl-stage`'s direct children (overrides the
       grid default `min-width: auto`, which is "don't shrink below your content's min-content
       size").
  5. **The floating `.gl-cap` caption card was removed entirely** (not repositioned again) —
     after several rounds of chin/collar-line measurement it kept landing on some part of her
     face. "Start practice" moved to `GlassNav.jsx` (new button, before Log in/Dashboard,
     `.gl-btn k` black solid — Sign up already owns the yellow accent). `GlassHero.jsx` now
     exposes `startDemo()` via `forwardRef`/`useImperativeHandle` (`Landing.jsx` owns the ref
     and wires nav→hero); it scrolls the hero into view, then runs the same `start()` logic the
     old card's button called — so the recording pill, phase-row highlight, segmented timeline,
     readiness-hexagon live state and the AI note callout are all still fully functional, just
     triggered from the nav. Hid the new nav button below 980px (same breakpoint that already
     hides `.gl-links`/`.gl-finder`) — a third nav action button overflowed the 390px nav,
     clipping "Sign up" off-screen; caught live via a `scrollWidth` check on the nav, not
     assumed. **Deliberately kept `.gl-ctl`** (mic/headphones/end-call icons): since the demo
     is still fully triggerable (from the nav) and endable (the red button still calls
     `stop()`), the floating control-bar-over-video-feed reads as a normal, legitimate "video
     call controls" pattern rather than dead UI — this was an explicit judgment call, not an
     oversight.
  6. Product owner then provided their OWN real photo (`hero-person-provided.jpg`, originally
     8192x5464 / ~22MB) to replace the AI-generated one, for both the big `.gl-video` and the
     small `.gl-pip` thumbnail (checked `.gl-pip`'s actual CSS aspect — 150x100 = 1.5:1,
     landscape, not portrait/square — so it gets the same photo, not the old AI portrait).
     Downscaled to 2400px on the long edge / JPEG quality 82 (~250KB) before wiring it in — no
     existing raster-photo convention in this codebase's `public/` to match (everything else is
     SVG), so picked JPEG since the source already was one. Measured crop against the stage via
     a 5%-gridline overlay on the actual file (not guessed): headphones start at ~15% down: the
     default-centre crop (~7.5% trimmed off top/bottom, width-constrained... *checked live and
     corrected* — it's actually width-constrained the OTHER way: container wider than photo, so
     this crop is trimming off height) needed a small `object-position: 50% 33%` nudge to clear
     the top pill row (caught live: default centre had the pill row sitting right at her
     hairline).
  7. Final fix: product owner felt the face read as too magnified/zoomed-in even after the crop
     fix — root cause is that `object-fit: cover` on a container noticeably wider than the photo
     necessarily blows up an already-fairly-tight headshot. There's no crop that shows literally
     more of the source image without gaps (cover already picks the minimum necessary crop), so
     pulled the whole photo back via `transform: scale(0.68)` on the `.gl-video img` instead —
     renders as a smaller, clearly "pulled back" inset video window with the stage's own
     gradient background showing as a frame around it (first tried 0.82, confirmed via computed
     styles it WAS applying but read as too subtle once the side margins landed under the
     floating `.gl-left`/`.gl-right` panels; 0.68 is unmistakable).
  8. Old AI-generated photos (`hero-person.png`, `hero-person-wide.png`) deleted from
     `public/photos/` — fully unreferenced once `HeroPhoto.jsx` switched to the provided photo.
  9. Final verification (clean, isolated `yarn build` + `yarn test`, Playwright at
     1440/1024/390px + nav + mid-interaction): `yarn build` compiles clean. `yarn test`: one
     flaky suite (`SparkInterview.test.jsx`, unrelated to anything touched this session) showed
     timeout-based failures when run alongside the other 10 suites under heavy system load from
     this long session's accumulated background processes — re-ran it in total isolation and all
     8 tests passed cleanly in 1-2s each (vs. the 5s timeout), confirming it's resource
     contention, not a real regression; the full suite's failure COUNT varied across repeated
     runs (12 → 8 → 2 failures) which is itself the signature of a load-sensitive flake rather
     than a deterministic break. No horizontal overflow at 390px (`scrollWidth === clientWidth
     === 390`, including the nav with the new button hidden below 980px).

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
- `GlassHero.jsx` is now a `forwardRef` component (exposes `startDemo()`); `Landing.jsx` owns
  the ref and passes `onStartPractice` down to `GlassNav.jsx` — this is the only cross-component
  wiring in the whole glass restyle, everything else is self-contained per component.
