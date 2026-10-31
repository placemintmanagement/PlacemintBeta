import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { TID } from "../testIds";
import { Clock, ArrowRight, ChevronLeft, TriangleAlert, FileText, CheckCircle2, XCircle, Sparkles, Check, X } from "lucide-react";
import { PageShell, SectionLabel, PageTitle, CardTitle, Card, Chip, Button } from "../components/shared";

// Body-size meta text (never monospace).
const META = { fontSize: 13, color: "var(--gl-muted)" };
const BODY = { fontSize: 15, color: "var(--gl-text)", lineHeight: 1.6 };
const OUTFIT = { fontFamily: "Outfit, system-ui, sans-serif", fontWeight: 600 };

// Fit score colour by band, from existing tokens only.
function scoreColor(score) {
  if (score >= 70) return "var(--gl-accent)";
  if (score >= 50) return "var(--gl-muted)";
  return "var(--gl-text)";
}

export default function CompanyDetail() {
  const { companyId } = useParams();
  const navigate = useNavigate();
  const [company, setCompany] = useState(null);
  const [role, setRole] = useState("Software Engineer");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [resumeId, setResumeId] = useState(null);
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
    api.get(`/companies/${companyId}`).then(r => setCompany(r.data)).catch(() => toast.error("Company not found"));
  }, [companyId]);

  const uploadResume = async (e) => {
    e.preventDefault();
    if (!file) { toast.error("Choose a PDF first."); return; }
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("company_id", companyId);
      fd.append("role", role);
      fd.append("file", file);
      const { data } = await api.post("/resume/analyze", fd, { headers: { "Content-Type": "multipart/form-data" }});
      setResumeId(data.resume_id);
      setAnalysis(data.analysis);
      toast.success("Resume analysed!");
      // After a resume is on file for this company, the student lands on
      // the hub -- OA and interview as two independent next steps -- per
      // the 2026-10 company-hub rollout.
      navigate(`/company/${companyId}/hub`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Upload failed");
    } finally { setUploading(false); }
  };

  // Starting the OA (and picking a skill cluster, for the one company that
  // has cluster_options) now lives entirely on the hub -- this page's job
  // is "get a resume on file" (optional) and "go to the hub," not starting
  // anything itself. Previously this called POST /oa/start directly and
  // skipped the hub page entirely, which meant Interview was unreachable
  // from here.

  if (!company) return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Loading…</div></PageShell></div>;

  return (
    <div>
      <Header light />
      <PageShell>
        <Link to="/" className="inline-flex items-center gap-1 mb-6 hover:text-[var(--gl-text)]" style={{ fontSize: 14, color: "var(--gl-muted)" }}><ChevronLeft size={16}/> back</Link>
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div className="max-w-2xl">
            {company.generic
              ? <Chip tone="status" className="mb-3" icon={<TriangleAlert size={12}/>}>general-purpose practice · not a specific company's real OA</Chip>
              : (!company.verified && <Chip className="mb-3" icon={<TriangleAlert size={12}/>}>unverified pattern</Chip>)}
            <PageTitle>{company.name}</PageTitle>
            <p className="mt-3" style={{ fontSize: 17, color: "var(--gl-text)", lineHeight: 1.5 }}>{company.tagline}</p>
          </div>
          <div className="flex gap-3 flex-wrap">
            <Chip tone="status" icon={<Clock size={12}/>}>{company.time_minutes} min total</Chip>
            <Chip>{company.scoring_mode === "sectional" ? "sectional cutoffs" : "composite score"}</Chip>
          </div>
        </div>

        {/* Resume upload + start */}
        <section className="mt-12 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <form onSubmit={uploadResume} className="flex">
            <Card className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <FileText size={18} style={{ color: "var(--gl-accent)" }} />
                <CardTitle>Optional: upload your resume</CardTitle>
              </div>
              <p className="mb-5" style={BODY}>An AI recruiter reads your resume against this exact role. Always free.</p>
              <label htmlFor="company-resume-role" style={{ fontSize: 14, color: "var(--gl-text)" }}>Target role</label>
              <input id="company-resume-role" data-testid={TID.resumeRoleInput} value={role} onChange={e => setRole(e.target.value)} className="gl-field-input mt-1.5 mb-4" placeholder="e.g. Software Engineer (Backend)" />
              <input aria-label="Resume PDF" data-testid={TID.resumeUploadInput} type="file" accept="application/pdf" onChange={e => setFile(e.target.files?.[0] || null)} className="gl-field-input mb-4" style={{ padding: "10px 12px", fontSize: 14 }} />
              <Button data-testid={TID.resumeSubmit} type="submit" variant="secondary" disabled={uploading || !file} className="w-full">
                {uploading ? "Analysing…" : (resumeId ? "Re-analyse" : "Analyse resume")}
              </Button>
              {resumeId && <div className="mt-3" style={{ fontSize: 13, color: "var(--gl-accent)", fontWeight: 600 }}>✓ resume attached to this run</div>}
            </Card>
          </form>

          <Card style={{ background: "#0c0c0c", border: "none", boxShadow: "0 20px 40px -22px rgba(0,0,0,0.6)" }} className="!text-white">
            <div className="flex flex-col justify-between flex-1 gap-6">
              <div>
                <span className="inline-flex rounded-full" style={{ background: "rgba(255,255,255,0.12)", color: "#fff", fontSize: 13, padding: "4px 10px" }}>ready when you are</span>
                <div className="mt-4" style={{ ...OUTFIT, fontSize: 26, lineHeight: 1.2, color: "#fff" }}>
                  Start the full {company.name} run, with real section timing.
                </div>
                <div className="mt-3" style={{ fontSize: 15, color: "rgba(255,255,255,0.8)" }}>Total: {company.time_minutes} minutes · {company.sections.length} sections</div>
              </div>
              <div>
                <Button data-testid={TID.startOaBtn} variant="lime" onClick={() => navigate(`/company/${companyId}/hub`)} className="w-full">
                  Continue to OA &amp; interview <ArrowRight size={14}/>
                </Button>
                <button data-testid={TID.resumeSkip} onClick={() => navigate(`/company/${companyId}/hub`)} className="mt-3 hover:text-white underline-offset-2 hover:underline" style={{ fontSize: 14, color: "rgba(255,255,255,0.75)" }}>skip resume for this run</button>
              </div>
            </div>
          </Card>
        </section>

        {/* Resume analysis result panel — shown as soon as the AI replies. */}
        {analysis && (
          <section data-testid="resume-analysis-panel" className="mt-8 pm-in">
            <Card padding="32px">
              <div className="flex items-start justify-between flex-wrap gap-6 mb-6">
                <div>
                  <div className="flex items-center gap-2" style={{ color: "var(--gl-accent)" }}>
                    <Sparkles size={16} />
                    <SectionLabel className="!mb-0">resume analysis · {role}</SectionLabel>
                  </div>
                  <CardTitle style={{ fontSize: 26, marginTop: 4 }}>Here's what our AI recruiter read from your resume.</CardTitle>
                </div>
                <div className="text-center">
                  <div style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--gl-muted)" }}>Fit score</div>
                  <div className="leading-none mt-1" style={{ ...OUTFIT, fontSize: 56, color: scoreColor(analysis.fit_score ?? 0) }}>
                    {analysis.fit_score ?? "N/A"}
                  </div>
                  <div className="mt-1" style={META}>/ 100</div>
                </div>
              </div>

              {analysis.verdict && (
                <div className="mb-6 p-4 rounded-[16px]" style={{ background: "var(--gl-blue)", ...BODY, color: "var(--gl-text)" }}>
                  <span className="mr-2" style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--gl-muted)" }}>verdict</span>
                  {analysis.verdict}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 size={16} style={{ color: "var(--gl-accent)" }} />
                    <CardTitle style={{ fontSize: 18 }}>Strengths</CardTitle>
                  </div>
                  <ul className="space-y-2">
                    {(analysis.strengths || []).map((s, i) => (
                      <li key={i} className="flex gap-2" style={BODY}>
                        <Check size={16} className="shrink-0 mt-1" style={{ color: "var(--gl-accent)" }} aria-hidden="true" />
                        <span>{s}</span>
                      </li>
                    ))}
                    {(!analysis.strengths || analysis.strengths.length === 0) && <li style={{ ...BODY, color: "var(--gl-muted)" }}>None identified.</li>}
                  </ul>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <XCircle size={16} style={{ color: "#e5484d" }} />
                    <CardTitle style={{ fontSize: 18 }}>Weaknesses</CardTitle>
                  </div>
                  <ul className="space-y-2">
                    {(analysis.weaknesses || []).map((s, i) => (
                      <li key={i} className="flex gap-2" style={BODY}>
                        <X size={16} className="shrink-0 mt-1" style={{ color: "#e5484d" }} aria-hidden="true" />
                        <span>{s}</span>
                      </li>
                    ))}
                    {(!analysis.weaknesses || analysis.weaknesses.length === 0) && <li style={{ ...BODY, color: "var(--gl-muted)" }}>None identified.</li>}
                  </ul>
                </div>
              </div>

              {analysis.extracted_projects?.length > 0 && (
                <div className="mt-8">
                  <CardTitle style={{ fontSize: 18, marginBottom: 12 }}>Projects we pulled out</CardTitle>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {analysis.extracted_projects.map((p, i) => (
                      <Card key={i} padding="16px 18px" style={{ borderRadius: 18, boxShadow: "none" }}>
                        <div style={{ ...OUTFIT, fontSize: 16, color: "var(--gl-text)" }}>{p.name}</div>
                        <div className="mt-1" style={{ fontSize: 13, color: "var(--gl-accent)", fontWeight: 600 }}>{p.tech_stack}</div>
                        <div className="mt-2" style={{ fontSize: 14, color: "var(--gl-text)", lineHeight: 1.6 }}>{p.one_line_summary}</div>
                      </Card>
                    ))}
                  </div>
                  <div className="mt-3" style={META}>These become the "project questions" in your interview round.</div>
                </div>
              )}
            </Card>
          </section>
        )}
      </PageShell>
    </div>
  );
}
