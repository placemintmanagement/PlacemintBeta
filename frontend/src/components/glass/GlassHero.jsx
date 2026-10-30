import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Mic, Headphones, PhoneOff } from "lucide-react";
import { COMPANIES } from "../../data/companies";
import { PHASES } from "../PhaseStrip";
import HeroPhoto from "./HeroPhoto";
import Readiness from "./Readiness";
import { TID } from "../../testIds";

// Short status tag per phase, shown under its name in the bottom timeline
// strip -- same four phases/descriptions as PhaseStrip.jsx (real, existing
// copy), just abbreviated for the small segment chip.
const SHORT_TAG = { resume: "AI check", oa: "Sectional cutoffs", interview: "Adaptive", review: "One verdict" };
const PALETTE = ["--gl-blue", "--gl-mint", "--gl-pink", "--gl-sand", "--gl-y"];

// Four topic tiles for the left "prep plan" panel. Sample prompts are
// generic placeholder practice questions (no existing on-site equivalent
// to preserve) -- same register as the IDE section's "Two Sum" problem,
// which the task brief explicitly allows to stay as a reasonable generic
// placeholder.
const TOPIC_TILES = [
  { key: "aptitude", name: "Aptitude", glyph: "123", sample: "A train covers 240 km in 3 hours. How long will 400 km take?" },
  { key: "verbal", name: "Verbal", glyph: "Aa", sample: "Rewrite in the passive: “The team completed the project early.”" },
  { key: "reasoning", name: "Reasoning", glyph: "?", sample: "Find the next number in the series: 3, 6, 11, 18, ?" },
  { key: "coding", name: "Coding", glyph: "</>", sample: "Return the indices of the two numbers in an array that add up to a target." },
];

// The illustrative "AI interview note" callout re-uses the exact feedback
// line already shown, labelled, in InsideYourReportSection.jsx's report
// card -- not a newly-invented "real" result.
const NOTE_TEXT = "You mentioned the project but not how you measured the improvement. Walk through the before and after numbers next time.";

/**
 * Exposes `startDemo()` via ref so GlassNav's "Start practice" button (see
 * Landing.jsx, which owns the ref and wires the two together) can drive
 * the SAME interactive demo state machine as the old in-hero card's
 * button used to -- the card itself is gone (2026-10, "remove the
 * floating caption card entirely" pass: it was sitting over the photo's
 * face through several rounds of repositioning, so the simplest fix was
 * to stop putting anything there), but the recording pill / phase-row
 * highlight / segmented timeline / readiness-hexagon live state / AI note
 * callout all still work exactly as before, just started from the nav
 * instead. startDemo() also scrolls the hero into view first, since the
 * nav is sticky and can be clicked from anywhere on the page.
 */
const GlassHero = forwardRef(function GlassHero(_props, ref) {
  const [ci, setCi] = useState(0);
  const [ti, setTi] = useState(0);
  const [live, setLive] = useState(false);
  const [si, setSi] = useState(0);
  const [sec, setSec] = useState(0);
  const [noteDismissed, setNoteDismissed] = useState(false);
  const [stopped, setStopped] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!live) return;
    timerRef.current = setInterval(() => setSec((s) => s + 1), 1000);
    return () => clearInterval(timerRef.current);
  }, [live]);

  const company = COMPANIES[ci];
  const topic = TOPIC_TILES[ti];

  function start() {
    if (!live) {
      setLive(true);
      setStopped(false);
      setSi(0);
      setSec(0);
      setNoteDismissed(false);
    } else if (si < 3) {
      setSi((v) => v + 1);
    } else {
      stop(true);
    }
  }

  function stop(reportReady = false) {
    setLive(false);
    clearInterval(timerRef.current);
    setSi(0);
    setSec(0);
    setStopped(reportReady);
  }

  function previewCompany(i) {
    setCi(i);
    setStopped(false);
    if (live) stop(false);
  }

  useImperativeHandle(ref, () => ({
    startDemo() {
      const el = document.getElementById("top");
      if (el) {
        const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
      }
      start();
    },
  }));

  const mm = String(Math.floor(sec / 60)).padStart(2, "0");
  const ss = String(sec % 60).padStart(2, "0");

  const readinessTopic = !live
    ? topic.name
    : si === 0
    ? "Resume"
    : si === 1
    ? topic.name
    : si === 2
    ? "Interview"
    : null;

  return (
    <div className="gl-page" id="top">
      <div className={`gl-stage${live ? " gl-live" : ""}`} id="stage">
        <div className="gl-video" aria-hidden="true">
          <HeroPhoto />
        </div>

        <header className="gl-top">
          <span className="gl-glass gl-pillr">
            <i aria-hidden="true" />
            <span>{live ? `Recording ${mm}:${ss}` : "Not recording"}</span>
          </span>

          <div className="gl-today">
            <small>Preparing<br />for</small>
            <div className="gl-cos" role="group" aria-label="Switch preparing-for company">
              {COMPANIES.slice(Math.max(0, Math.min(ci - 2, COMPANIES.length - 5)), Math.max(0, Math.min(ci - 2, COMPANIES.length - 5)) + 5).map((c) => {
                const realIndex = COMPANIES.indexOf(c);
                const on = realIndex === ci;
                return (
                  <button
                    key={c.id}
                    type="button"
                    className={on ? "on" : ""}
                    style={{ "--tc": `var(${PALETTE[realIndex % PALETTE.length]})` }}
                    onClick={() => previewCompany(realIndex)}
                    aria-label={c.live ? c.name : `${c.name} (rolling out next)`}
                    aria-pressed={on}
                  >
                    {c.name[0]}
                  </button>
                );
              })}
            </div>
          </div>

          <span className="gl-glass gl-pillr" style={{ flexDirection: "column", alignItems: "flex-start", gap: 2 }}>
            {company.live ? (
              <Link to={`/company/${company.id}`} data-testid={TID.heroSecondary} style={{ fontWeight: 500 }}>
                {company.name} &middot; {topic.name}
                <span style={{ marginLeft: 8, textDecoration: "underline" }}>View plan &rarr;</span>
              </Link>
            ) : (
              <span>{company.name} &middot; Rolling out next</span>
            )}
          </span>
        </header>

        <aside className="gl-left gl-glass">
          <div className="gl-prof">
            <b>{company.name}</b>
            <small>Your prep plan</small>
          </div>
          <div>
            {PHASES.map((p, i) => (
              <div key={p.key} className={`gl-row${live && i === si ? " on" : ""}`}>
                {p.title}
                <span aria-hidden="true">&#8599;</span>
              </div>
            ))}
          </div>
          <div className="gl-tiles">
            {TOPIC_TILES.map((t, i) => (
              <button
                key={t.key}
                type="button"
                className={`gl-tile${i === ti ? " on" : ""}`}
                style={{ "--tc": `var(${PALETTE[i % PALETTE.length]})` }}
                onClick={() => setTi(i)}
              >
                <span className="g">{t.glyph}</span>
                <span>{t.name}</span>
              </button>
            ))}
          </div>
        </aside>

        <main className="gl-mid">
          {/* The floating glass caption card that used to live here (the
              "Don't practice for a test..." heading + per-phase body text
              + Start/Next/End button) is gone (2026-10) -- it sat over the
              photo's face through several rounds of repositioning, and
              the simplest fix was to stop putting anything there. The
              "Start practice" trigger moved to GlassNav (see
              GlassNav.jsx's startBtn + Landing.jsx's ref wiring); this
              control strip is what's left, floating low over the photo
              like a real video call's control bar. */}
          <div className="gl-ctl">
            <button type="button" aria-label="Microphone (decorative)" tabIndex={-1}><Mic size={20} color="#fff" /></button>
            <button type="button" aria-label="Audio (decorative)" tabIndex={-1}><Headphones size={20} color="#fff" /></button>
            <button type="button" className="end" aria-label="End session" onClick={() => stop(false)}>
              <PhoneOff size={20} color="#fff" />
            </button>
          </div>
        </main>

        <aside className="gl-right">
          <div className="gl-pip">
            <HeroPhoto small />
          </div>
          <div className="gl-glass gl-res">
            <h4>Sectional<br />readiness</h4>
            <Readiness activeTopic={readinessTopic} />
          </div>
        </aside>

        <section className="gl-tline">
          {live && si >= 2 && !noteDismissed && (
            <div className="gl-note">
              <b>AI interview note (example)</b>
              {NOTE_TEXT}
              <button type="button" aria-label="Dismiss note" onClick={() => setNoteDismissed(true)}>&times;</button>
            </div>
          )}
          <h3>Your four phases</h3>
          <div className="gl-segs">
            {PHASES.map((p, i) => (
              <div
                key={p.key}
                className={`gl-seg${live && i === si ? " on" : ""}`}
                style={{ "--tc": `var(${PALETTE[i % PALETTE.length]})` }}
              >
                <span className="gl-thumb">{i + 1}</span>
                <span>
                  <b>{p.title}</b>
                  <small>{SHORT_TAG[p.key]}</small>
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
});

export default GlassHero;
