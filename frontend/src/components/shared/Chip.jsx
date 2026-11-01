import React from "react";

// Pill chip (`.gl-tag`, glass.css), body font 13px, never monospace.
//   status   mint tint (duration / status)
//   neutral  blue tint
// var(--gl-text) in both.
// `!inline-flex` (Tailwind's `!` = !important) -- `.gl-tag` sets its own
// `display: inline-block` directly (glass.css), same specificity as this
// utility class, and wins the cascade tie (glass.css loads after
// Tailwind's generated output). When this Chip sits inside a flex row
// (every real usage), the loser gets CSS-blockified to plain `block`
// (an inline-level box becomes block when it's a flex item) -- not a
// flex container at all, so the icon (Tailwind preflight sets svg to
// `display: block`) renders on its own line above the text instead of
// beside it. Same bug class as Footer.jsx/LegalPage.jsx hit earlier,
// caught live via a screenshot (icon stacked above "190 min total").
export default function Chip({ tone = "neutral", icon = null, children, className = "" }) {
  return (
    <span
      className={`gl-tag ${tone} !inline-flex items-center gap-1 whitespace-nowrap ${className}`}
      style={{ color: "var(--gl-text)", fontSize: 13, padding: "4px 10px" }}
    >
      {icon}
      {children}
    </span>
  );
}
