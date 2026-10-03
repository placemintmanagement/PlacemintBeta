import React from "react";
import { TID } from "../testIds";
import { Sparkles, Star } from "lucide-react";

/**
 * The original Landing.jsx hero, extracted verbatim (2026-10) when HeroV2
 * became the default on "/". Kept in the repo, unused, as a rollback
 * reference -- not imported anywhere.
 */
const AVATARS = [
  "https://images.unsplash.com/photo-1552113125-81af17f36b57?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHw0fHxpbmRpYW4lMjBzdHVkZW50JTIwcG9ydHJhaXR8ZW58MHx8fHwxNzgzOTI1NzQyfDA&ixlib=rb-4.1.0&q=85",
  "https://images.unsplash.com/photo-1667655861998-46fe4c29a4cf?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxpbmRpYW4lMjBzdHVkZW50JTIwcG9ydHJhaXR8ZW58MHx8fHwxNzgzOTI1NzQyfDA&ixlib=rb-4.1.0&q=85",
  "https://images.unsplash.com/photo-1604177091072-b7b677a077f6?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwzfHxpbmRpYW4lMjBzdHVkZW50JTIwcG9ydHJhaXR8ZW58MHx8fHwxNzgzOTI1NzQyfDA&ixlib=rb-4.1.0&q=85",
  "https://images.pexels.com/photos/15237309/pexels-photo-15237309.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
];

export default function HeroClassic() {
  return (
    <section className="relative overflow-hidden pm-grain">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 pt-16 pb-24 lg:pt-24 lg:pb-32">
        <div className="max-w-4xl">
          <div className="inline-flex items-center gap-2 pm-chip pm-chip-primary mb-6">
            <Sparkles size={12} /> Made for Indian engineering freshers
          </div>
          <h1 className="font-display font-extrabold leading-[1.02] text-[44px] sm:text-6xl lg:text-7xl tracking-tighter">
            Placement prep, <br />
            <span className="bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(90deg, #0FAE73, #0A0A0A 50%, #FF6F4D)" }}>
              the way companies actually test you.
            </span>
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-pm-text2 leading-relaxed">
            Not one generic mock. Placemint runs the <em>real</em> Online Assessment structure of 14 top companies, from sectional cutoffs and pseudocode rounds to essays, coding, and the adaptive interview. All in one honest, cross-phase verdict.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <a href="#companies" data-testid={TID.heroSecondary} className="pm-btn pm-btn-primary text-base">
              Browse all companies
            </a>
          </div>

          {/* Social proof */}
          <div className="mt-10 flex items-center gap-4">
            <div className="flex -space-x-3">
              {AVATARS.map((src, i) => (
                <img key={i} src={src} alt="" className="w-10 h-10 rounded-full object-cover border-2 border-[#FAF8F3]" loading="lazy" />
              ))}
            </div>
            <div>
              <div className="flex items-center gap-1 text-pm-secondary">
                {[0,1,2,3,4].map(i => <Star key={i} size={14} fill="currentColor" />)}
                <span className="font-mono text-sm text-pm-text ml-2">4.9 / 5</span>
              </div>
              <div className="text-sm text-pm-text2">from 2,000+ campus students last placement cycle</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
