import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api";
import Header from "../components/Header";
import { TID } from "../testIds";
import { Sparkles } from "lucide-react";

export default function FinalReport() {
  const { attemptId } = useParams();
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/report/${attemptId}`).then(r => { setDoc(r.data); setLoading(false); });
  }, [attemptId]);

  if (loading) return <div><Header /><div className="p-10 text-center">Building your final report…</div></div>;
  if (!doc) return <div><Header /><div className="p-10 text-center">Report not available.</div></div>;

  const r = doc.report || {};
  // Three-tier verdict color, darkest = most serious -- no red/orange in
  // this palette, so "eliminated" is distinguished by being the boldest
  // ink rather than a different hue.
  const verdictClass = r.overall_verdict === "clear" ? "text-pm-primary-dark" : r.overall_verdict === "borderline" ? "text-pm-text2" : "text-pm-text";

  return (
    <div>
      <Header />
      <div data-testid={TID.finalReportView} className="max-w-4xl mx-auto px-6 py-10 pm-in">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-2">Final report · {doc.company_name}</div>
        <div className="flex items-start justify-between flex-wrap gap-4">
          <h1 className={`font-display text-4xl lg:text-5xl font-bold ${verdictClass}`}>
            {r.overall_verdict === "clear" ? "You'd land this offer." : r.overall_verdict === "borderline" ? "Borderline. With focused prep, you get in." : "Not ready. Here's what to fix."}
          </h1>
          <div className="pm-card px-5 py-3 text-center">
            <div className="text-xs font-mono uppercase text-pm-text2">Overall</div>
            <div className="font-display text-3xl font-bold font-mono">{r.overall_score ?? "N/A"}<span className="text-pm-text2 text-base">/100</span></div>
          </div>
        </div>

        <div className="mt-8 pm-card p-8 whitespace-pre-wrap leading-relaxed text-pm-text">
          <Sparkles className="text-pm-primary mb-3" />
          {r.narrative || "Report unavailable."}
        </div>

        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="pm-card p-6">
            <div className="text-xs font-mono uppercase text-pm-text2">Strongest dimension</div>
            <div className="font-display text-xl font-bold mt-1">{r.strongest_dimension || "N/A"}</div>
          </div>
          <div className="pm-card p-6">
            <div className="text-xs font-mono uppercase text-pm-text2">Weakest dimension</div>
            <div className="font-display text-xl font-bold mt-1">{r.weakest_dimension || "N/A"}</div>
          </div>
        </div>

        {r.next_steps?.length > 0 && (
          <div className="mt-6 pm-card p-6">
            <div className="font-display text-xl font-bold mb-3">Next steps</div>
            <ol className="space-y-2">
              {r.next_steps.map((s, i) => (
                <li key={i} className="flex gap-3 items-start">
                  <div className="w-6 h-6 rounded-full bg-pm-primary text-white grid place-items-center font-mono font-bold text-xs shrink-0">{i+1}</div>
                  <div className="text-sm">{s}</div>
                </li>
              ))}
            </ol>
          </div>
        )}

        <div className="mt-10 flex gap-3">
          <Link to="/dashboard" className="pm-btn pm-btn-ghost">Back to dashboard</Link>
          <Link to="/" className="pm-btn pm-btn-primary">Run another company</Link>
        </div>
      </div>
    </div>
  );
}
