import React from "react";

// Track sky-deep, fill teal-deep. `achieved` fills lime with a 2px
// teal-night outline. The value is always written out as text too, so
// meaning never depends on colour alone.
export function ProgressBar({ value = 0, label, achieved = false }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div>
      {label && <div className="mb-1.5" style={{ fontSize: 14, color: "rgba(11,42,48,0.85)" }}>{label} <span style={{ color: "rgba(11,42,48,0.7)" }}>({Math.round(pct)}%)</span></div>}
      <div className="w-full rounded-full overflow-hidden" style={{ height: 10, background: "var(--pm-sky-deep)" }} role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            background: achieved ? "var(--pm-lime)" : "var(--pm-teal-deep)",
            boxShadow: achieved ? "inset 0 0 0 2px var(--pm-teal-night)" : "none",
          }}
        />
      </div>
    </div>
  );
}

// Inline status alert. tone: error | warning | success | info.
export function Alert({ tone = "info", title, children }) {
  const map = {
    error: { bg: "var(--pm-error-bg)", fg: "var(--pm-error-text)" },
    warning: { bg: "var(--pm-warning-bg)", fg: "var(--pm-ink)" },
    success: { bg: "var(--pm-success-bg)", fg: "var(--pm-teal-deep)" },
    info: { bg: "var(--pm-sky)", fg: "var(--pm-ink)" },
  };
  const c = map[tone] || map.info;
  return (
    <div role={tone === "error" ? "alert" : "status"} className="rounded-[14px] px-4 py-3" style={{ background: c.bg, color: c.fg, fontSize: 14 }}>
      {title && <div className="font-display font-semibold mb-0.5" style={{ fontSize: 15 }}>{title}</div>}
      {children}
    </div>
  );
}

// Centred empty state: title, body, optional action (a Button node).
export function EmptyState({ title, body, action = null }) {
  return (
    <div className="flex flex-col items-center text-center gap-3 py-12">
      <div className="font-display font-semibold" style={{ fontSize: 22, color: "var(--pm-ink)" }}>{title}</div>
      {body && <div style={{ fontSize: 15, color: "rgba(11,42,48,0.7)", maxWidth: 420 }}>{body}</div>}
      {action}
    </div>
  );
}
