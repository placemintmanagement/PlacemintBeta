import React, { useId } from "react";

// Label above, input below. White, 1.5px rgba(7,59,67,.2), radius 14px,
// padding 12px 16px. Focus: teal-deep border + 3px teal-night outline,
// 2px offset. Error: error border and helper text.
// Pass `as="textarea"` or `as="select"` for those controls; `children`
// become the select options.
export default function Field({ label, helper, error, as = "input", id, className = "", children, ...rest }) {
  const autoId = useId();
  const inputId = id || autoId;
  const helperId = `${inputId}-help`;
  const Control = as;
  const borderColor = error ? "var(--pm-error-text)" : "rgba(7,59,67,0.2)";
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={inputId} style={{ fontSize: 14, color: "rgba(11,42,48,0.85)" }}>{label}</label>
      <Control
        id={inputId}
        aria-invalid={!!error}
        aria-describedby={error || helper ? helperId : undefined}
        className="w-full bg-[var(--pm-white)] outline-none focus:outline-[3px] focus:outline-offset-2 focus:outline-[var(--pm-teal-night)] focus:border-[var(--pm-teal-deep)]"
        style={{
          border: `1.5px solid ${borderColor}`,
          borderRadius: 14,
          padding: "12px 16px",
          fontSize: 15,
          color: "var(--pm-ink)",
        }}
        {...rest}
      >
        {children}
      </Control>
      {(error || helper) && (
        <div id={helperId} style={{ fontSize: 13, color: error ? "var(--pm-error-text)" : "rgba(11,42,48,0.7)" }}>
          {error || helper}
        </div>
      )}
    </div>
  );
}
