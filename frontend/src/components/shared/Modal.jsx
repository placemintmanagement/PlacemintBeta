import React, { useEffect } from "react";

// `.gl-modal-overlay`/`.gl-modal-panel` (glass.css): var(--gl-card) panel,
// radius 24px, neutral dark overlay. Closes on Escape and overlay click.
// Focus is moved into the panel on open.
export default function Modal({ open, onClose, title, children, footer = null }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") onClose?.(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="gl-modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose?.(); }}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className="gl-modal-panel"
      >
        {title && <div className="font-semibold mb-3" style={{ fontFamily: "Outfit, system-ui, sans-serif", fontSize: 22, color: "var(--gl-text)" }}>{title}</div>}
        <div style={{ color: "var(--gl-text)", fontSize: 15 }}>{children}</div>
        {footer && <div className="mt-6 flex flex-wrap gap-3 justify-end">{footer}</div>}
      </div>
    </div>
  );
}
