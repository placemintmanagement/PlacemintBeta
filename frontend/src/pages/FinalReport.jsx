import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api";
import Header from "../components/Header";
import { TID } from "../testIds";
import { Sparkles } from "lucide-react";
import { PageShell, SectionLabel, PageTitle, CardTitle, Card, Button } from "../components/shared";

// Body-size meta text (never monospace).
const META = { fontSize: 13, color: "rgba(11,42,48,0.7)" };
const BODY = { fontSize: 16, color: "rgba(11,42,48,0.85)", lineHeight: 1.7 };

export default function FinalReport() {
  const { attemptId } = useParams();
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/report/${attemptId}`).then(r => { setDoc(r.data); setLoading(false); });
  }, [attemptId]);

  if (loading) return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Building your final report…</div></PageShell></div>;
  if (!doc) return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Report not available.</div></PageShell></div>;

  const r = doc.report || {};
  // Three-tier verdict colour: teal for clear, ink 70% for borderline, full
  // ink for eliminated. No hue beyond the palette.
  const verdictColor = r.overall_verdict === "clear" ? "var(--pm-teal-deep)" : r.overall_verdict === "borderline" ? "rgba(11,42,48,0.7)" : "var(--pm-ink)";

  return (
    <div>
      <Header light />
      <PageShell>
        <div data-testid={TID.finalReportView} className="max-w-4xl mx-auto pm-in">
          <SectionLabel>Final report · {doc.company_name}</SectionLabel>
          <div className="flex items-start justify-between flex-wrap gap-6">
            <PageTitle style={{ color: verdictColor }}>
              {r.overall_verdict === "clear" ? "You'd land this offer." : r.overall_verdict === "borderline" ? "Borderline. With focused prep, you get in." : "Not ready. Here's what to fix."}
            </PageTitle>
            <Card padding="16px 22px" style={{ borderRadius: 20 }} className="text-center">
              <div style={META}>Overall</div>
              <div className="font-display font-semibold" style={{ fontSize: 34, color: "var(--pm-ink)" }}>{r.overall_score ?? "N/A"}<span style={{ fontSize: 16, color: "rgba(11,42,48,0.7)", marginLeft: 2 }}>/100</span></div>
            </Card>
          </div>

          <Card padding="32px" className="mt-8">
            <Sparkles className="mb-3" style={{ color: "var(--pm-teal-deep)" }} aria-hidden="true" />
            <div className="whitespace-pre-wrap" style={BODY}>{r.narrative || "Report unavailable."}</div>
          </Card>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <div style={META}>Strongest dimension</div>
              <div className="font-display font-semibold mt-1" style={{ fontSize: 22, color: "var(--pm-ink)" }}>{r.strongest_dimension || "N/A"}</div>
            </Card>
            <Card>
              <div style={META}>Weakest dimension</div>
              <div className="font-display font-semibold mt-1" style={{ fontSize: 22, color: "var(--pm-ink)" }}>{r.weakest_dimension || "N/A"}</div>
            </Card>
          </div>

          {r.next_steps?.length > 0 && (
            <Card className="mt-6">
              <CardTitle style={{ marginBottom: 12 }}>Next steps</CardTitle>
              <ol className="space-y-3">
                {r.next_steps.map((s, i) => (
                  <li key={i} className="flex gap-3 items-start">
                    <div className="w-7 h-7 rounded-full grid place-items-center shrink-0 font-display font-semibold" style={{ fontSize: 14, background: "var(--pm-teal-deep)", color: "var(--pm-white)" }}>{i+1}</div>
                    <div style={{ fontSize: 15, color: "var(--pm-ink)", lineHeight: 1.6, paddingTop: 2 }}>{s}</div>
                  </li>
                ))}
              </ol>
            </Card>
          )}

          <div className="mt-10 flex gap-3 flex-wrap">
            <Button as={Link} to="/dashboard" variant="secondary">Back to dashboard</Button>
            <Button as={Link} to="/">Run another company</Button>
          </div>
        </div>
      </PageShell>
    </div>
  );
}
