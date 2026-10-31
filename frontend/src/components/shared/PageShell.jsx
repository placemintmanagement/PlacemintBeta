import React from "react";

// Glass-scoped page wrapper + centred container (max 1240px, 16px gutter on
// mobile, 32px from 768px up). `section` adds the 64-96px desktop / 40-56px
// mobile vertical padding; pass section={false} for a bare shell.
// `glass-landing` applied here, once, scopes every descendant shared/*
// primitive to the glass design system -- same "apply the scope class at
// the subtree root" pattern Header.jsx/Footer.jsx use on their own root.
export default function PageShell({ children, section = true, className = "" }) {
  return (
    <div className={`glass-landing min-h-screen ${className}`}>
      <div className={`mx-auto w-full max-w-[1240px] px-4 md:px-8 ${section ? "py-10 md:py-24" : ""}`}>
        {children}
      </div>
    </div>
  );
}
