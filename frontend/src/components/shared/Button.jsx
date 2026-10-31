import React from "react";

// Variants (2026-10 rollout):
//   primary      teal-deep fill, white Outfit 600, hover teal-night
//   secondary    white, 1.5px teal-deep border, teal-deep text
//   destructive  error text on error bg, error border
//   lime         ink text, lime fill -- DARK surfaces only
// Disabled: ink at 35% on sky-deep. Focus ring: 3px teal-night, 2px offset
// on light surfaces; lime ring on dark (lime variant / onDark).
// Pill radius throughout. Hover/focus transitions are short and
// reduced-motion safe via the global prefers-reduced-motion rule.
const BASE = "inline-flex items-center justify-center gap-2 rounded-full font-display font-semibold text-[15px] px-6 py-3 transition-colors duration-150 focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 disabled:cursor-not-allowed";

const VARIANTS = {
  primary: {
    cls: "hover:bg-[var(--pm-teal-night)] focus-visible:outline-[var(--pm-teal-night)]",
    style: { background: "var(--pm-teal-deep)", color: "var(--pm-white)" },
  },
  secondary: {
    cls: "hover:bg-[rgba(15,111,122,0.06)] focus-visible:outline-[var(--pm-teal-night)]",
    style: { background: "var(--pm-white)", color: "var(--pm-teal-deep)", border: "1.5px solid var(--pm-teal-deep)" },
  },
  destructive: {
    cls: "hover:brightness-95 focus-visible:outline-[var(--pm-teal-night)]",
    style: { background: "var(--pm-error-text)", color: "var(--pm-white)" },
  },
  lime: {
    cls: "hover:brightness-95 focus-visible:outline-[var(--pm-lime)]",
    style: { background: "var(--pm-lime)", color: "var(--pm-ink)" },
  },
  // Dark-surface pair (hero nav). Backgrounds live in the class, not inline,
  // so the hover colour can change them (an inline background would win).
  "lime-dark": {
    cls: "bg-[#C6F24E] text-[#0B2A30] hover:bg-[#A5CC2E] focus-visible:outline-[#C6F24E]",
    style: {},
  },
  "outline-dark": {
    cls: "bg-transparent text-white border border-white/40 hover:bg-white/10 focus-visible:outline-[#C6F24E]",
    style: {},
  },
};

// `as` renders the same styling on a router Link or an anchor; type and
// disabled only apply to the native button.
export default function Button({ as: Tag = "button", variant = "primary", type = "button", disabled = false, className = "", style = {}, children, ...rest }) {
  const v = VARIANTS[variant] || VARIANTS.primary;
  const disabledStyle = disabled ? { background: "var(--pm-sky-deep)", color: "rgba(11,42,48,0.35)", border: "none" } : {};
  const nativeProps = Tag === "button" ? { type, disabled } : {};
  return (
    <Tag
      {...nativeProps}
      className={`${BASE} ${disabled ? "" : v.cls} ${className}`}
      style={{ ...v.style, ...disabledStyle, ...style }}
      {...rest}
    >
      {children}
    </Tag>
  );
}
