import React from "react";
import { Link } from "react-router-dom";
import { Building2, Code2, MessageSquareText, ArrowRight } from "lucide-react";

/**
 * "Pick your starting point." Three link-cards, copy carried over verbatim
 * from the existing StartPractisingSection.jsx (teal design) -- not new
 * placeholder text. Tile coloring reuses the same --gl-* PALETTE approach
 * as the hero's topic tiles / timeline cards, so it reads as part of this
 * design system rather than a one-off.
 */
const CARDS = [
  { key: "company", icon: Building2, title: "Practice by company", desc: "Browse every company and pick the one you're prepping for.", to: "/#companies", tc: "--gl-mint" },
  { key: "oa", icon: Code2, title: "Mock Online Assessment", desc: "Real sectional structure, cutoffs and timing, not a generic quiz.", to: "/signup", tc: "--gl-pink", photo: "/photos/starting-point-oa.jpg" },
  { key: "interview", icon: MessageSquareText, title: "Adaptive Interview", desc: "Follows up on vague answers, just like a real interviewer.", to: "/signup", tc: "--gl-sand", photo: "/photos/starting-point-interview.jpg" },
];

export default function GlassStartingPoints() {
  return (
    <section className="gl-sec gl-sec-tight-top" id="starting-points">
      <h2 className="gl-h2" style={{ textAlign: "center" }}>
        Pick your <b>starting point.</b>
      </h2>
      <p className="gl-sub" style={{ margin: "0 auto 32px", textAlign: "center" }}>
        Every path runs on the real structure of the company you choose.
      </p>
      <div className="gl-sp-grid">
        {CARDS.map((c) => {
          const Icon = c.icon;
          return (
            <Link key={c.key} to={c.to} className="gl-sp-card" style={{ "--tc": `var(${c.tc})` }}>
              <span className="gl-sp-tile">
                {c.photo ? (
                  <>
                    <img src={c.photo} alt="" aria-hidden="true" />
                    <span className="gl-sp-badge"><Icon size={18} /></span>
                  </>
                ) : (
                  <Icon size={40} />
                )}
              </span>
              <b>{c.title}</b>
              <p>{c.desc}</p>
              <span className="gl-sp-go">
                Explore <ArrowRight size={14} aria-hidden="true" />
              </span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
