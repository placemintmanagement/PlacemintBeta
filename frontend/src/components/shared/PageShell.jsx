import React from "react";

// Cream page wrapper + centred container (max 1240px, 16px gutter on
// mobile, 32px from 768px up). `section` adds the 64-96px desktop /
// 40-56px mobile vertical padding; pass section={false} for a bare shell.
export default function PageShell({ children, section = true, className = "" }) {
  return (
    <div className={`min-h-screen ${className}`} style={{ background: "var(--pm-cream)", color: "var(--pm-ink)" }}>
      <div className={`mx-auto w-full max-w-[1240px] px-4 md:px-8 ${section ? "py-10 md:py-24" : ""}`}>
        {children}
      </div>
    </div>
  );
}
