import React from "react";

// Pill chip (`.gl-tag`, glass.css), body font 13px, never monospace.
//   status   mint tint (duration / status)
//   neutral  blue tint
// var(--gl-text) in both.
export default function Chip({ tone = "neutral", icon = null, children, className = "" }) {
  return (
    <span
      className={`gl-tag ${tone} inline-flex items-center gap-1 whitespace-nowrap ${className}`}
      style={{ color: "var(--gl-text)", fontSize: 13, padding: "4px 10px" }}
    >
      {icon}
      {children}
    </span>
  );
}
