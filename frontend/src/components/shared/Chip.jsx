import React from "react";

// Pill chip, body font 13px, never monospace.
//   status   #EAF9C4 (duration / status)
//   neutral  #E8F3FB
// Ink text in both.
export default function Chip({ tone = "neutral", icon = null, children, className = "" }) {
  const bg = tone === "status" ? "var(--pm-success-bg)" : "var(--pm-sky)";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full whitespace-nowrap ${className}`}
      style={{ background: bg, color: "var(--pm-ink)", fontSize: 13, padding: "4px 10px" }}
    >
      {icon}
      {children}
    </span>
  );
}
