import React, { useId } from "react";

// Label above, input below. `.gl-field-input` (glass.css): var(--gl-card)
// bg, var(--gl-line) border, radius 14px, padding 12px 16px, focus ring in
// var(--gl-focus). Error: red border (`.err`) and helper text.
// Pass `as="textarea"` or `as="select"` for those controls; `children`
// become the select options.
export default function Field({ label, helper, error, as = "input", id, className = "", children, ...rest }) {
  const autoId = useId();
  const inputId = id || autoId;
  const helperId = `${inputId}-help`;
  const Control = as;
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={inputId} style={{ fontSize: 14, color: "var(--gl-muted)" }}>{label}</label>
      <Control
        id={inputId}
        aria-invalid={!!error}
        aria-describedby={error || helper ? helperId : undefined}
        className={`gl-field-input ${error ? "err" : ""}`}
        {...rest}
      >
        {children}
      </Control>
      {(error || helper) && (
        <div id={helperId} style={{ fontSize: 13, color: error ? "#e5484d" : "var(--gl-muted)" }}>
          {error || helper}
        </div>
      )}
    </div>
  );
}
