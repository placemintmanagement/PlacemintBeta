// Landing-page Pricing section + its nav/footer links are hidden for now
// (2026-10). The /pricing route and the Pricing page itself are untouched
// and still fully live -- flip this back to true to bring the section and
// its links back everywhere at once.
export const SHOW_PRICING = false;

// Landing-page "Choose your company" tile grid (components/
// ChooseCompanySection.jsx) is hidden for now (2026-10), replaced in the
// page by "Inside your report" (components/InsideYourReportSection.jsx).
// The component itself is untouched -- flip this back to true to bring
// the grid back. It has no id/anchor and nothing else in the app links
// to it, so there was nothing else to un-link.
export const SHOW_COMPANY_GRID = false;
