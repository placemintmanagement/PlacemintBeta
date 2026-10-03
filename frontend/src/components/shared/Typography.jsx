import React from "react";

// Small uppercase label above a heading (Poppins 600, 13px, .06em).
// Teal-deep on light surfaces; pass onDark for lime on dark ones.
export function SectionLabel({ children, onDark = false, className = "" }) {
  return (
    <div
      className={`mb-3 ${className}`}
      style={{
        fontFamily: "var(--pm-font-label)",
        fontWeight: 600,
        fontSize: 13,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        lineHeight: 1.2,
        color: onDark ? "var(--pm-lime)" : "var(--pm-teal-deep)",
      }}
    >
      {children}
    </div>
  );
}

// h1/h2 page or section title: Outfit 300, ink, -0.02em. Emphasis phrases
// go inside as <Emph>, which is Outfit 600 in teal-deep (never a highlight
// band, never lime on a light background).
export function PageTitle({ as: Tag = "h1", children, className = "", style = {} }) {
  const size = Tag === "h1" ? "clamp(2rem, 4vw, 3rem)" : "clamp(1.75rem, 3vw, 2.5rem)";
  return (
    <Tag
      className={`font-display font-light ${className}`}
      style={{ color: "var(--pm-ink)", fontSize: size, lineHeight: Tag === "h1" ? 1.08 : 1.15, letterSpacing: "-0.02em", ...style }}
    >
      {children}
    </Tag>
  );
}

export function Emph({ children }) {
  return <span style={{ fontWeight: 600, color: "var(--pm-teal-deep)" }}>{children}</span>;
}

// h3 / card titles: Outfit 600.
export function CardTitle({ children, className = "", style = {} }) {
  return (
    <div className={`font-display font-semibold ${className}`} style={{ color: "var(--pm-ink)", fontSize: 20, lineHeight: 1.2, ...style }}>
      {children}
    </div>
  );
}
