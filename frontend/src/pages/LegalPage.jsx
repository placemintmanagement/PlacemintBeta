import React from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";

/**
 * Renders a simple markdown-like static legal page. Content passed in via
 * children so each policy file stays tiny. Kept intentionally minimal — real
 * legal content should be reviewed by a lawyer before launch.
 */
export default function LegalPage({ title, updatedOn, children }) {
  return (
    <div>
      <Header />
      <article className="max-w-3xl mx-auto px-6 lg:px-10 py-16 pm-in">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-2">legal</div>
        <h1 className="font-display text-4xl lg:text-5xl font-bold">{title}</h1>
        {updatedOn && (
          <div className="text-xs font-mono text-pm-text2 mt-2">Last updated: {updatedOn}</div>
        )}
        <div className="mt-8 space-y-6 text-pm-text leading-relaxed [&_h2]:font-display [&_h2]:text-2xl [&_h2]:font-bold [&_h2]:mt-8 [&_h2]:mb-2 [&_h3]:font-display [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:mt-5 [&_h3]:mb-1 [&_p]:text-pm-text2 [&_ul]:list-disc [&_ul]:ml-6 [&_ul_li]:text-pm-text2 [&_ul_li]:mb-1">
          {children}
        </div>
      </article>
      <Footer />
    </div>
  );
}
