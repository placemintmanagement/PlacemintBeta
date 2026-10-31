import React from "react";

/**
 * HireTric logo mark (2026-10 rebrand, from the provided brand sheet):
 * two overlapping rounded blocks forming an abstract "H". Uses its own
 * brighter hex colors, not the shared --gl-pink/--gl-mint tokens -- those
 * are deliberately soft pastels for large background fills, but read as
 * dull at logo scale (same issue the option-picker icons had), so this
 * mark gets its own more saturated variants instead.
 */
export default function GlassLogoMark({ size = 34 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 34 34" aria-hidden="true">
      <rect x="2" y="2" width="12" height="30" rx="6" fill="#f06a93" />
      <rect x="16" y="9" width="12" height="23" rx="6" fill="#2fc48d" />
      <circle cx="27" cy="6" r="4" fill="var(--gl-y)" />
    </svg>
  );
}
