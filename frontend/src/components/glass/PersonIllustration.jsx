import React from "react";

/**
 * Simple, generic, non-identifiable inline SVG figure -- same register as
 * the reference mockup's `<svg class="person">` block (plain vector
 * shapes, not a photo, not AI-generated art). Reimplemented here as a
 * small reusable component instead of inline markup so both the hero
 * stage and the IDE-section illustration frame can use it.
 */
export default function PersonIllustration({ className, small = false }) {
  return (
    <svg
      className={className}
      viewBox={small ? "0 0 400 400" : "0 0 400 520"}
      preserveAspectRatio={small ? "xMidYMax slice" : "xMidYMax meet"}
      aria-hidden="true"
    >
      {small ? (
        <>
          <circle cx="200" cy="146" r="64" fill="#e6b896" />
          <path d="M138 146c-12-84 128-108 140 0-24-38-116-38-140 0z" fill="#4b3226" />
          <path d="M100 400c0-82 44-108 100-108s100 26 100 108z" fill="#6c8fb0" />
        </>
      ) : (
        <>
          <ellipse cx="42" cy="262" rx="27" ry="66" transform="rotate(12 42 262)" fill="#e6b896" opacity=".92" />
          <ellipse cx="358" cy="262" rx="27" ry="66" transform="rotate(-12 358 262)" fill="#e6b896" opacity=".92" />
          <path d="M20 520C20 400 90 360 200 355c110 5 180 45 180 165z" fill="#9db9cf" />
          <path d="M150 360q50 60 100 0v160H150z" fill="#e9e6e1" />
          <rect x="170" y="290" width="60" height="80" rx="24" fill="#d9a888" />
          <ellipse cx="200" cy="200" rx="86" ry="104" fill="#e6b896" />
          <path d="M110 190C100 90 170 60 215 66c70 6 85 64 75 124-10-40-40-65-90-65s-80 25-90 65z" fill="#4b3226" />
          <path d="M118 215c2 85 42 101 82 101s80-16 82-101c-12 35-42 47-82 47s-70-12-82-47z" fill="#4b3226" />
          <path d="M172 268q28 18 56 0q-28 6-56 0z" fill="#f6efe8" />
          <circle cx="168" cy="198" r="6" fill="#2b1d16" />
          <circle cx="232" cy="198" r="6" fill="#2b1d16" />
          <path d="M150 178q18-10 32 0M218 178q14-10 32 0" stroke="#3a281e" strokeWidth="5" fill="none" strokeLinecap="round" />
          <path d="M104 200C96 90 304 90 296 200" stroke="#f4f4f4" strokeWidth="10" fill="none" />
          <rect x="90" y="180" width="28" height="62" rx="13" fill="#222" />
          <rect x="282" y="180" width="28" height="62" rx="13" fill="#222" />
          <path d="M110 242c8 60 50 74 82 66" stroke="#222" strokeWidth="4" fill="none" />
          <circle cx="194" cy="308" r="6" fill="#222" />
        </>
      )}
    </svg>
  );
}
