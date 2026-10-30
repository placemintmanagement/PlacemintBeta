import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { Mic, Headphones, PhoneOff, Star, MessageCircle, ThumbsUp } from "lucide-react";
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

// Four tiles for the left "prep plan" panel, reframed (2026-10) from OA
// practice categories to interview goals -- matches the Interview row now
// being the default-highlighted phase, and reuses the same competency
// vocabulary already established in Readiness.jsx's hexagon (Communication/
// Problem Solving/Technical Depth/.../Ownership) instead of inventing new
// unrelated labels. No longer wired to the readiness hexagon's own state
// (that reads a fixed shape, see Readiness.jsx), purely a "what we're
// practising" grid now.
const TOPIC_TILES = [
  { key: "clarity", name: "Clarity", glyph: "Aa", sample: "Explain your approach clearly, out loud, as you work through it." },
  { key: "problem-solving", name: "Problem Solving", glyph: "?", sample: "Break the problem down before jumping to a solution." },
  { key: "technical-depth", name: "Technical Depth", glyph: "</>", sample: "Be ready to justify the trade-offs in your approach." },
  { key: "ownership", name: "Ownership", glyph: "123", sample: "Speak to decisions you drove, not just tasks you completed." },
];

// The illustrative "AI interview note" callout re-uses the exact feedback
// line already shown, labelled, in InsideYourReportSection.jsx's report
// card -- not a newly-invented "real" result.
const NOTE_TEXT = "You mentioned the project but not how you measured the improvement. Walk through the before and after numbers next time.";

// Persona name for the header's "who's interviewing you" pill (2026-10).
// Explicitly, unambiguously AI -- "· AI Interviewer" is part of the label
// itself, not a tooltip or fine print, same honesty bar as everywhere
// else in this app (no fabricated human recruiter name/title).
const AI_INTERVIEWER_NAME = "John";

// Placeholder name for "you" (the candidate) in the left prep-plan panel's
// demo -- same register as AI_INTERVIEWER_NAME: a stand-in for the
// interactive demo, not a claim about a real user.
const CANDIDATE_NAME = "Maya M.";
const CANDIDATE_ROLE = "Software Engineer";

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

          {/* AI interviewer persona pill (2026-10, replaces the old
              company/topic + "View plan" link) -- explicitly labelled AI,
              never a real recruiter/human name, same honesty bar as the
              rest of this app (no fabricated people/testimonials). The
              company/topic info this used to carry isn't lost: it's still
              shown via the "Preparing for" avatar switcher just to its
              left, and the two other real navigate-to-company paths
              (the nav search field, the "Crack interviews at" chip grid)
              are untouched, so dropping the link here doesn't reduce how
              a visitor can reach a real company page. */}
          <span className="gl-glass gl-pillr" data-testid={TID.heroSecondary}>
            <span style={{ fontWeight: 500 }}>{AI_INTERVIEWER_NAME}</span>
            <span style={{ opacity: 0.75, marginLeft: 6 }}>&middot; AI Interviewer</span>
          </span>
        </header>

        <aside className="gl-left gl-glass">
          <div className="gl-prof">
            <img className="gl-prof-pfp" src="/photos/hero-person-provided.jpg" alt="" aria-hidden="true" />
            <span>
              <b>{CANDIDATE_NAME}</b>
              <small>{CANDIDATE_ROLE} &middot; Your prep plan</small>
            </span>
          </div>
          <div>
            {PHASES.map((p, i) => {
              // When the demo isn't running, default-highlight the
              // Interview row instead of showing all four as flat/equal --
              // the hero photo itself (headset on, "Not recording" pill)
              // already reads as "ready for an interview", so this row
              // should match that story even before "Start practice" is
              // clicked. Once live, the real per-phase highlight (i===si)
              // takes over as before.
              const on = live ? i === si : p.key === "interview";
              return (
                <div key={p.key} className={`gl-row${on ? " on" : ""}`}>
                  {p.title}
                  <span aria-hidden="true">&#8599;</span>
                </div>
              );
            })}
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
            <h4>Interview<br />results</h4>
            {/* Shown always (not gated to the interview phase) so the
                right rail doesn't jump around as the demo state changes --
                `interviewActive` just brightens the shape while the
                interview phase (si===2) is actually live, rather than
                hiding/showing the whole card. */}
            <Readiness interviewActive={live && si === 2} />
          </div>
        </aside>

        <section className="gl-tline">
          {/* "AI Interview Notes" callout (reference: a floating card
              overlapping the timeline row). Positioned over the Interview
              card specifically (index 2 of 4) -- it only ever shows during
              that phase (si>=2), so the overlap is thematic, not
              arbitrary. Content is unchanged from before: the same
              already-labelled example feedback line reused from
              InsideYourReportSection.jsx's report card, not a new/
              fabricated quote. */}
          {live && si >= 2 && !noteDismissed && (
            <div className="gl-note">
              <b>AI interview note (example)</b>
              {NOTE_TEXT}
              <button type="button" aria-label="Dismiss note" onClick={() => setNoteDismissed(true)}>&times;</button>
            </div>
          )}
          <h3>Your four phases</h3>
          <div className="gl-segs">
            {PHASES.map((p, i) => {
              const Icon = p.icon;
              return (
                <div
                  key={p.key}
                  className={`gl-seg${live && i === si ? " on" : ""}`}
                  style={{ "--tc": `var(${PALETTE[i % PALETTE.length]})` }}
                >
                  {/* Icon swatch, not a photo thumbnail -- the reference's
                      thumbnails are specific captured interview-clip
                      moments (with timestamps) that this app has no real
                      footage to back; a fake "candidate photo" + invented
                      timestamp would be exactly the kind of fake-result
                      claim avoided everywhere else in this redesign (the
                      qualitative readiness hexagon, the icon-only feature
                      picker). Same icon per phase as PhaseStrip.jsx, for
                      consistency across the app, not a one-off choice. */}
                  <span className="gl-seg-swatch" aria-hidden="true"><Icon size={24} /></span>
                  <span>
                    <b>{p.title}</b>
                    <small>{SHORT_TAG[p.key]}</small>
                  </span>
                </div>
              );
            })}
          </div>
          {/* Purely decorative connector + icon markers (reference: a thin
              line with small icon dots below the row) -- bare icons, no
              counts/numbers next to them, same "no numbers" rule as the
              rest of this hero. */}
          <div className="gl-connector" aria-hidden="true">
            <span className="gl-connector-mark" style={{ left: "16.5%" }}><Star size={11} /></span>
            <span className="gl-connector-mark" style={{ left: "50%" }}><MessageCircle size={11} /></span>
            <span className="gl-connector-mark" style={{ left: "83.5%" }}><ThumbsUp size={11} /></span>
          </div>
        </section>
      </div>
    </div>
  );
});

export default GlassHero;
