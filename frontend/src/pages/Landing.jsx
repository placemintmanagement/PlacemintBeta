import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import Header from "../components/Header";
import PipelineDiagram from "../components/PipelineDiagram";
import CompanyCard from "../components/CompanyCard";
import IDEMockup from "../components/IDEMockup";
import Footer from "../components/Footer";
import { TID } from "../testIds";
import { ArrowRight, Sparkles, ShieldCheck, Zap, MessageSquareText, FileCheck2, Code2, Star } from "lucide-react";

const AVATARS = [
  "https://images.unsplash.com/photo-1552113125-81af17f36b57?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHw0fHxpbmRpYW4lMjBzdHVkZW50JTIwcG9ydHJhaXR8ZW58MHx8fHwxNzgzOTI1NzQyfDA&ixlib=rb-4.1.0&q=85",
  "https://images.unsplash.com/photo-1667655861998-46fe4c29a4cf?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxpbmRpYW4lMjBzdHVkZW50JTIwcG9ydHJhaXR8ZW58MHx8fHwxNzgzOTI1NzQyfDA&ixlib=rb-4.1.0&q=85",
  "https://images.unsplash.com/photo-1604177091072-b7b677a077f6?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwzfHxpbmRpYW4lMjBzdHVkZW50JTIwcG9ydHJhaXR8ZW58MHx8fHwxNzgzOTI1NzQyfDA&ixlib=rb-4.1.0&q=85",
  "https://images.pexels.com/photos/15237309/pexels-photo-15237309.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
];

export default function Landing() {
  const [companies, setCompanies] = useState([]);
  const [plans, setPlans] = useState([]);

  useEffect(() => {
    api.get("/companies").then(r => setCompanies(r.data.companies)).catch(() => {});
    api.get("/pricing").then(r => setPlans(r.data.plans)).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen">
      <Header />

      {/* HERO */}
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
              Not one generic mock. Placemint runs the <em>real</em> Online Assessment structure of 14 top companies — sectional cutoffs, pseudocode rounds, essays, coding, adaptive interview. All in one honest, cross-phase verdict.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link to="/signup" data-testid={TID.heroCta} className="pm-btn pm-btn-primary text-base">
                Start free — 3 runs on us <ArrowRight size={16} />
              </Link>
              <a href="#companies" data-testid={TID.heroSecondary} className="pm-btn pm-btn-ghost text-base">
                Browse the 14 companies
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

      {/* Contrarian statement */}
      <section className="max-w-7xl mx-auto px-6 lg:px-10 pb-16">
        <div className="pm-card p-10 lg:p-14 relative overflow-hidden">
          <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-3">what makes this different</div>
          <div className="font-display text-3xl lg:text-5xl font-bold leading-tight max-w-4xl">
            Most placement platforms pretend every company runs the same test.<br />
            <span className="text-pm-secondary">They don't.</span> We built one engine per company — real order, real cutoffs, real pain.
          </div>
        </div>
      </section>

      {/* Pipeline */}
      <section className="max-w-7xl mx-auto px-6 lg:px-10 pb-24">
        <div className="mb-8 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-2">the flow</div>
            <h2 className="font-display font-bold text-3xl lg:text-4xl">4 phases. One story.</h2>
          </div>
          <p className="max-w-md text-pm-text2">Every attempt threads through the same pipeline, so your final report is one narrative — not four disconnected scores.</p>
        </div>
        <PipelineDiagram />
      </section>

      {/* Feature bento */}
      <section className="max-w-7xl mx-auto px-6 lg:px-10 pb-24">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 flex flex-col gap-4">
            <div className="flex items-end justify-between flex-wrap gap-3">
              <div>
                <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-2">what the OA actually looks like</div>
                <h3 className="font-display text-2xl lg:text-3xl font-bold">A real split-panel coding IDE, not a textarea.</h3>
              </div>
              <div className="text-sm text-pm-text2 max-w-xs">Same split-panel layout used by HackerRank &amp; LeetCode — problem on the left, dark editor on the right.</div>
            </div>
            <IDEMockup />
          </div>

          <div className="pm-card p-8 flex flex-col gap-4">
            <div className="w-10 h-10 rounded-lg bg-pm-primary/10 text-pm-primary-dark grid place-items-center"><Code2 /></div>
            <h4 className="font-display text-xl font-bold">LeetCode-style coding rounds</h4>
            <p className="text-pm-text2 text-sm">Split-panel IDE, dark editor on a light page. 2 visible tests. 3 hidden tests unlocked on Submit. Write in Python, JS, C, C++, Java.</p>
          </div>

          <div className="pm-card p-8 flex flex-col gap-4">
            <div className="w-10 h-10 rounded-lg bg-pm-primary/10 text-pm-primary-dark grid place-items-center"><FileCheck2 /></div>
            <h4 className="font-display text-xl font-bold">Resume checker — free forever</h4>
            <p className="text-pm-text2 text-sm">Uploads once, gets analysed against <em>this</em> company &amp; <em>this</em> role. Strengths, weaknesses, fit score, projects extracted — no credit card.</p>
          </div>

          <div className="pm-card p-8 flex flex-col gap-4">
            <div className="w-10 h-10 rounded-lg bg-pm-secondary/15 text-pm-secondary grid place-items-center"><MessageSquareText /></div>
            <h4 className="font-display text-xl font-bold">Adaptive interview</h4>
            <p className="text-pm-text2 text-sm">2 DSA + 2 project questions from your actual resume + 3 CS fundamentals. Follows up on vague answers like a real interviewer.</p>
          </div>

          <div className="pm-card p-8 flex flex-col gap-4">
            <div className="w-10 h-10 rounded-lg bg-pm-primary/10 text-pm-primary-dark grid place-items-center"><ShieldCheck /></div>
            <h4 className="font-display text-xl font-bold">Sectional cutoffs, honest verdicts</h4>
            <p className="text-pm-text2 text-sm">If Infosys wants 65% in pseudocode, you'll get eliminated at 64%. If it's blended, we tell you which section dragged you down.</p>
          </div>

          <div className="pm-card p-8 flex flex-col gap-4">
            <div className="w-10 h-10 rounded-lg bg-pm-secondary/15 text-pm-secondary grid place-items-center"><Zap /></div>
            <h4 className="font-display text-xl font-bold">One report, not four</h4>
            <p className="text-pm-text2 text-sm">The final report ties resume, OA, and interview into a single narrative — written by our premium AI tier, the one place we don't downgrade.</p>
          </div>
        </div>
      </section>

      {/* Companies grid */}
      <section id="companies" className="max-w-7xl mx-auto px-6 lg:px-10 pb-24">
        <div className="mb-8 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-2">14 supported tracks</div>
            <h2 className="font-display font-bold text-3xl lg:text-4xl">Each company runs its <em>own</em> real structure.</h2>
          </div>
          <p className="max-w-md text-pm-text2 text-sm">Time chip shows the confirmed OA duration. Dashed border + red badge = pattern we couldn't fully confirm; we use a documented fallback.</p>
        </div>
        <div data-testid={TID.companyGrid} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {companies.map(c => <CompanyCard key={c.id} company={c} />)}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-7xl mx-auto px-6 lg:px-10 pb-24">
        <div className="mb-6">
          <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-2">pricing</div>
          <h2 className="font-display font-bold text-3xl lg:text-4xl">Pay for reps, not marketing fluff.</h2>
        </div>

        {/* Explainer strip — removes any ambiguity about what "1 run" means. */}
        <div className="pm-card p-5 mb-8 flex flex-wrap items-center gap-x-8 gap-y-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-widest text-pm-primary-dark">what counts as 1 run</div>
            <div className="font-display font-bold text-lg">1 company · OA + Interview + Report</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="pm-chip">✓ Full OA (all sections)</span>
            <span className="pm-chip">✓ Adaptive interview</span>
            <span className="pm-chip">✓ Final cross-phase report</span>
            <span className="pm-chip pm-chip-primary">Resume Checker is always free</span>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {plans.map(p => (
            <div key={p.id} data-testid={TID.pricingPlan(p.id)}
                 className={`pm-card p-6 flex flex-col ${p.highlight ? "border-pm-primary shadow-[0_20px_60px_-30px_rgba(15,174,115,0.5)] scale-[1.02]" : ""}`}>
              {p.highlight && <span className="pm-chip pm-chip-primary self-start mb-3">Most picked</span>}
              <div className="font-display text-xl font-bold">{p.name}</div>
              <div className="mt-2 font-mono text-3xl font-bold">
                {p.price === 0 ? "₹0" : <>₹{p.price}</>}
                <span className="text-sm font-normal text-pm-text2 ml-1">{p.id === "basic" || p.id === "pro" ? "/mo" : (p.id === "free" ? "" : " one-time")}</span>
              </div>
              <div className="mt-1 font-mono text-xs text-pm-text2">{p.companies} co • {p.runs} runs</div>
              <ul className="mt-4 space-y-1.5 text-sm text-pm-text2">
                {p.features.map((f, i) => <li key={i} className="flex gap-2"><span className="text-pm-primary">✓</span>{f}</li>)}
              </ul>
              <Link to="/pricing" data-testid={TID.pricingSelect(p.id)} className={`mt-6 pm-btn ${p.highlight ? "pm-btn-primary" : "pm-btn-ghost"} text-sm py-2`}>{p.cta}</Link>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="max-w-4xl mx-auto px-6 lg:px-10 pb-24">
        <h2 className="font-display font-bold text-3xl lg:text-4xl mb-6">Questions people actually ask</h2>
        <div className="space-y-3">
          {FAQ.map((f, i) => (
            <details key={i} className="pm-card p-5 group open:shadow-md">
              <summary className="cursor-pointer font-display font-semibold text-lg list-none flex justify-between items-center">
                {f.q}
                <span className="text-pm-primary group-open:rotate-45 transition-transform text-xl leading-none">+</span>
              </summary>
              <div className="mt-3 text-pm-text2 leading-relaxed text-sm">{f.a}</div>
            </details>
          ))}
        </div>
      </section>

      <Footer />
    </div>
  );
}

const FAQ = [
  { q: "How is this different from any other mock-test website?", a: "Each of the 14 tracks runs its own real section order, timing, and cutoff logic. Infosys' pseudocode round has a 65% cutoff. Wipro's essay is a real elimination gate. Zoho runs a 3-round marathon — pen-paper aptitude → 5 basic programs → advanced DSA. Not a shared template." },
  { q: "Why is the resume checker free?", a: "Because it's the least AI-heavy part and it's how we earn trust. You upload once, an AI reads it against the company/role you picked, you get honest strengths/weaknesses. No credit card, ever." },
  { q: "Do I need to pay to try?", a: "No. Free tier gives you 3 full runs during our launch window. That's enough to get through 3 companies end-to-end — resume + OA + interview + final report." },
  { q: "Which languages do the coding rounds support?", a: "Python, JavaScript, C, C++, and Java all run live in the browser — same as HackerRank's model. Every submission is executed against 2 visible + 3 hidden test cases." },
  { q: "Is the AI grading actually good?", a: "For OA sections we use structured JSON outputs, so grading is deterministic — not \"vibes\" grading. The final cross-phase report uses our premium AI tier because that's the one part where the extra reasoning is worth it." },
];
