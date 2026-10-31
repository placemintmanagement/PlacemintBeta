import React from "react";

// `.gl-card` (glass.css): radius 24px, var(--gl-line) border, soft shadow.
// header + tint: optional tinted header zone rendered edge to edge above
// the body. padding: body padding, default 24px 28px. Pass "0" when the
// content sets its own inner padding (stat tiles, banners).
// interactive: hover/focus lift via `.gl-card-interactive` (glass.css),
// reduced-motion safe.
export default function Card({ header = null, tint = "var(--gl-sand)", interactive = false, padding = "24px 28px", children, className = "", style = {}, ...rest }) {
  return (
    <div
      {...rest}
      className={`gl-card ${interactive ? "gl-card-interactive" : ""} relative flex flex-col overflow-hidden ${className}`}
      style={style}
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
