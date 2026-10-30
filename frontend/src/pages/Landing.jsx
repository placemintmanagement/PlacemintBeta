import React, { useEffect, useRef, useState } from "react";
import "../components/glass/glass.css";
import Reveal from "../components/Reveal";
import GlassNav from "../components/glass/GlassNav";
import GlassHero from "../components/glass/GlassHero";
import GlassCrackInterviews from "../components/glass/GlassCrackInterviews";
import GlassStartingPoints from "../components/glass/GlassStartingPoints";
import GlassDepartments from "../components/glass/GlassDepartments";
import GlassWhatYouGet from "../components/glass/GlassWhatYouGet";
import GlassFourPhases from "../components/glass/GlassFourPhases";
import GlassIdeSection from "../components/glass/GlassIdeSection";
import GlassReportSection from "../components/glass/GlassReportSection";
import GlassFaq from "../components/glass/GlassFaq";
import GlassFooter from "../components/glass/GlassFooter";

const THEME_KEY = "pm-glass-theme";

/**
 * Landing page -- glass restyle (2026-10), reimplementing
 * docs/glass-restyle-reference.html's design system as real React
 * components (see docs/glass-restyle-progress.md for the full section ->
 * component map and the honesty-rule decision for the hero demo).
 *
 * Everything here is scoped under the `.glass-landing` wrapper (glass.css)
 * so none of it leaks into any other page -- the logged-in app keeps its
 * existing teal design untouched. `theme` is a manual light/dark override
 * on top of the system `prefers-color-scheme`, remembered per-browser.
 */
export default function Landing() {
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem(THEME_KEY) || "system";
    } catch {
      return "system";
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      // ignore (private mode / storage disabled)
    }
  }, [theme]);

  function toggleTheme() {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }

  // GlassNav's "Start practice" button (replaces the hero's own removed
  // caption-card button, 2026-10) drives GlassHero's demo state machine
  // through this ref -- see GlassHero.jsx's startDemo() for what it does
  // (scrolls the hero into view, then starts/advances the demo).
  const heroRef = useRef(null);

  return (
    <div className="glass-landing" data-theme={theme === "system" ? undefined : theme}>
      <GlassNav
        theme={theme}
        onToggleTheme={toggleTheme}
        onStartPractice={() => heroRef.current?.startDemo()}
      />
      <GlassHero ref={heroRef} />
      {/* Hero stays as-is (above the fold, visible on load) -- everything
          below fades/lifts in on scroll via the same Reveal used
          throughout the main app's own Landing.jsx. */}
      <Reveal><GlassCrackInterviews /></Reveal>
      <Reveal><GlassStartingPoints /></Reveal>
      <Reveal><GlassWhatYouGet /></Reveal>
      <Reveal><GlassFourPhases /></Reveal>
      <Reveal><GlassIdeSection /></Reveal>
      <Reveal><GlassReportSection /></Reveal>
      <Reveal><GlassDepartments /></Reveal>
      <Reveal><GlassFaq /></Reveal>
      <Reveal><GlassFooter /></Reveal>
    </div>
  );
}
