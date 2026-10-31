import React from "react";

// White card: radius 24px, 1px rgba(7,59,67,.08) border, soft teal shadow.
// header + tint: optional tinted header zone (#E8F3FB, #EAF9C4, #F2EDDF,
// #E3EEF0) rendered edge to edge above the body.
// padding: body padding, default 24px 28px. Pass "0" when the content
// sets its own inner padding (stat tiles, banners).
// interactive: hover/focus lift via index.css (.pm-dc-card), reduced-motion safe.
export default function Card({ header = null, tint = "#E8F3FB", interactive = false, padding = "24px 28px", children, className = "", style = {}, ...rest }) {
  return (
    <div
      {...rest}
      className={`${interactive ? "pm-dc-card" : ""} relative flex flex-col overflow-hidden ${className}`}
      style={{
        background: "var(--pm-white)",
        borderRadius: 24,
        border: "1px solid rgba(7,59,67,0.08)",
        boxShadow: "0 14px 28px -18px rgba(7,59,67,0.28)",
        ...style,
      }}
    >
      {header && (
        <div className="flex items-end" style={{ background: tint, minHeight: 96, padding: "22px 24px" }}>
          {header}
        </div>
      )}
      <div style={{ padding, display: "flex", flexDirection: "column", flex: 1 }}>{children}</div>
    </div>
  );
}
