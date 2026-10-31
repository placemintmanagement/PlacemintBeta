import React from "react";

// Variants, built on `.gl-btn` (glass.css, shared with the nav/landing
// CTAs) plus the modifier classes Stage 2 added there:
//   primary      .y  -- yellow gradient fill, black text
//   secondary    .o  -- transparent, var(--gl-line) border, var(--gl-text)
//   destructive  .r  -- red fill, white text
//   lime / lime-dark  .y  -- no lime token in the glass palette; the
//                            yellow fill already reads well on the dark
//                            surfaces these variants were for (hero, etc.)
//   outline-dark .wo -- transparent, white border/text, for dark surfaces
// Disabled: 50% opacity (native `disabled` attribute handles the rest).
// Pill radius + focus ring come from `.gl-btn`/the global focus-visible
// rule, not re-declared here.
const BASE = "inline-flex items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50";

const VARIANT_CLASS = {
  primary: "y",
  secondary: "o",
  destructive: "r",
  lime: "y",
  "lime-dark": "y",
  "outline-dark": "wo",
};

// `as` renders the same styling on a router Link or an anchor; type and
// disabled only apply to the native button.
export default function Button({ as: Tag = "button", variant = "primary", type = "button", disabled = false, className = "", style = {}, children, ...rest }) {
  const mod = VARIANT_CLASS[variant] || VARIANT_CLASS.primary;
  const nativeProps = Tag === "button" ? { type, disabled } : {};
  return (
    <Tag
      {...nativeProps}
      className={`gl-btn ${mod} ${BASE} ${className}`}
      style={style}
      {...rest}
    >
      {children}
    </Tag>
  );
}
