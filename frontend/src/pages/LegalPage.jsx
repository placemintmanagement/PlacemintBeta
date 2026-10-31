import React from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import { PageShell, SectionLabel, PageTitle } from "../components/shared";

/**
 * Renders a simple markdown-like static legal page. Content passed in via
 * children so each policy file stays tiny. Kept intentionally minimal — real
 * legal content should be reviewed by a lawyer before launch.
 */
export default function LegalPage({ title, updatedOn, children }) {
  return (
    <div>
      <Header light />
      <PageShell section={false}>
        <article className="max-w-3xl mx-auto px-0 py-16 pm-in">
          <SectionLabel>legal</SectionLabel>
          <PageTitle>{title}</PageTitle>
          {updatedOn && (
            <div className="mt-2" style={{ fontSize: 13, color: "var(--gl-muted)" }}>Last updated: {updatedOn}</div>
          )}
          {/* [&_a]: uses Tailwind's `!` (!important) modifier -- `.glass-landing
              a { color: inherit; text-decoration: none }` (glass.css) is the
              same specificity (one class + one type selector) as this
              arbitrary-variant utility, and wins the source-order tie since
              glass.css loads after Tailwind's generated output. Same bug
              Footer.jsx hit; !important is the simpler fix here since this
              rule targets every <a> in arbitrary markdown-like children,
              not one element's own className. */}
          <div className="mt-8 space-y-6 leading-relaxed [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:mt-8 [&_h2]:mb-2 [&_h2]:text-[var(--gl-text)] [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:mt-5 [&_h3]:mb-1 [&_h3]:text-[var(--gl-text)] [&_p]:text-[var(--gl-muted)] [&_ul]:list-disc [&_ul]:ml-6 [&_ul_li]:text-[var(--gl-muted)] [&_ul_li]:mb-1 [&_a]:!text-[var(--gl-accent)] [&_a]:!underline [&_a]:underline-offset-2" style={{ color: "var(--gl-text)" }}>
            {children}
          </div>
        </article>
      </PageShell>
      <Footer className="mt-0" />
    </div>
  );
}
