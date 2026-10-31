import React from "react";

// Track: a faint tint of var(--gl-text) (readable but unobtrusive). Fill:
// the logo's saturated blue while in progress, var(--gl-y) once `achieved`
// (a celebratory accent, same role --pm-lime played). The value is always
// written out as text too, so meaning never depends on colour alone.
export function ProgressBar({ value = 0, label, achieved = false }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div>
      {label && <div className="mb-1.5" style={{ fontSize: 14, color: "var(--gl-text)" }}>{label} <span style={{ color: "var(--gl-muted)" }}>({Math.round(pct)}%)</span></div>}
      <div className="w-full rounded-full overflow-hidden" style={{ height: 10, background: "color-mix(in srgb, var(--gl-text) 10%, transparent)" }} role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            background: achieved ? "var(--gl-y)" : "#2dd4da",
            boxShadow: achieved ? "inset 0 0 0 2px var(--gl-text)" : "none",
          }}
        />
      </div>
    </div>
  );
}

// Inline status alert. tone: error | warning | success | info.
export function Alert({ tone = "info", title, children }) {
  const map = {
    error: { bg: "rgba(229,72,77,0.12)", fg: "#e5484d" },
    warning: { bg: "rgba(255,196,40,0.18)", fg: "var(--gl-text)" },
    success: { bg: "color-mix(in srgb, var(--gl-mint) 35%, transparent)", fg: "var(--gl-text)" },
    info: { bg: "color-mix(in srgb, var(--gl-blue) 35%, transparent)", fg: "var(--gl-text)" },
  };
  const c = map[tone] || map.info;
  return (
    <div role={tone === "error" ? "alert" : "status"} className="rounded-[14px] px-4 py-3" style={{ background: c.bg, color: c.fg, fontSize: 14 }}>
      {title && <div className="font-semibold mb-0.5" style={{ fontFamily: "Outfit, system-ui, sans-serif", fontSize: 15 }}>{title}</div>}
      {children}
    </div>
  );
}

// Centred empty state: title, body, optional action (a Button node).
export function EmptyState({ title, body, action = null }) {
  return (
    <div className="flex flex-col items-center text-center gap-3 py-12">
      <div className="font-semibold" style={{ fontFamily: "Outfit, system-ui, sans-serif", fontSize: 22, color: "var(--gl-text)" }}>{title}</div>
      {body && <div style={{ fontSize: 15, color: "var(--gl-muted)", maxWidth: 420 }}>{body}</div>}
      {action}
    </div>
  );
}
