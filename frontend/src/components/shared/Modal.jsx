import React, { useEffect } from "react";

// White panel, radius 24px, overlay rgba(7,59,67,.5). Closes on Escape and
// overlay click. Focus is moved into the panel on open.
export default function Modal({ open, onClose, title, children, footer = null }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") onClose?.(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(7,59,67,0.5)" }} onMouseDown={(e) => { if (e.target === e.currentTarget) onClose?.(); }}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className="w-full max-w-[520px] bg-[var(--pm-white)]"
        style={{ borderRadius: 24, border: "1px solid rgba(7,59,67,0.08)", boxShadow: "0 14px 28px -18px rgba(7,59,67,0.28)", padding: 28 }}
      >
        {title && <div className="font-display font-semibold mb-3" style={{ fontSize: 22, color: "var(--pm-ink)" }}>{title}</div>}
        <div style={{ color: "rgba(11,42,48,0.85)", fontSize: 15 }}>{children}</div>
        {footer && <div className="mt-6 flex flex-wrap gap-3 justify-end">{footer}</div>}
      </div>
    </div>
  );
}
