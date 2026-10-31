import React from "react";

/**
 * HireTric logo mark (2026-10 rebrand, matched directly against the
 * provided reference logo image): a proper "H" -- a shorter light-blue
 * left leg with a yellow dot above it, a taller pink right leg, and a
 * light horizontal crossbar joining them. Uses its own brighter hex
 * colors, not the shared --gl-pink/--gl-mint tokens -- those are
 * deliberately soft pastels for large background fills, but read as
 * dull at logo scale (same issue the option-picker icons had), so this
 * mark gets its own more saturated variants instead.
 */
export default function GlassLogoMark({ size = 34 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 34 34" aria-hidden="true">
      <rect x="4" y="13" width="9" height="19" rx="4.5" fill="#2dd4da" />
      <rect x="21" y="3" width="9" height="29" rx="4.5" fill="#ec4899" />
      {/* Same blue as the left leg, per reference image -- not
          currentColor. An earlier version used currentColor so the
          crossbar would stay visible against both the light Header and
          dark Footer, but the reference logo has it blue in both
          contexts, so a fixed hex is correct here. */}
      <rect x="9" y="15" width="16" height="6" rx="3" fill="#2dd4da" />
      <circle cx="8.5" cy="7" r="4.5" fill="var(--gl-y)" />
    </svg>
  );
}
