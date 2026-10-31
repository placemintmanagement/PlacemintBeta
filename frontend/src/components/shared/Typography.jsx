import React from "react";

// Small uppercase label above a heading (Poppins 600, 13px, .06em).
// var(--gl-accent) on light surfaces; pass onDark for var(--gl-y) on dark
// section panels (e.g. .gl-dk/.gl-rep), which stays legible regardless of
// the global light/dark theme those live inside.
export function SectionLabel({ children, onDark = false, className = "" }) {
  return (
    <div
      className={`mb-3 ${className}`}
      style={{
        fontFamily: "Poppins, system-ui, sans-serif",
        fontWeight: 600,
        fontSize: 13,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        lineHeight: 1.2,
        color: onDark ? "var(--gl-y)" : "var(--gl-accent)",
      }}
    >
      {children}
    </div>
  );
}

// h1/h2 page or section title: Outfit 300, near-black/white, -0.02em.
// Emphasis phrases go inside as <Emph>, which is Outfit 600 in
// var(--gl-accent) (never a highlight band).
export function PageTitle({ as: Tag = "h1", children, className = "", style = {} }) {
  const size = Tag === "h1" ? "clamp(2rem, 4vw, 3rem)" : "clamp(1.75rem, 3vw, 2.5rem)";
  return (
    <Tag
      className={className}
      style={{ fontFamily: "Outfit, system-ui, sans-serif", fontWeight: 300, color: "var(--gl-text)", fontSize: size, lineHeight: Tag === "h1" ? 1.08 : 1.15, letterSpacing: "-0.02em", ...style }}
    >
      {children}
    </Tag>
  );
}

export function Emph({ children }) {
  return <span style={{ fontWeight: 600, color: "var(--gl-accent)" }}>{children}</span>;
}

// h3 / card titles: Outfit 600.
export function CardTitle({ children, className = "", style = {} }) {
  return (
    <div className={className} style={{ fontFamily: "Outfit, system-ui, sans-serif", fontWeight: 600, color: "var(--gl-text)", fontSize: 20, lineHeight: 1.2, ...style }}>
      {children}
    </div>
  );
}
