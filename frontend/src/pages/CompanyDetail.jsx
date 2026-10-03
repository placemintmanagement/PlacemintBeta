import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { useAuth } from "../auth";
import { TID } from "../testIds";
import { Clock, ArrowRight, ChevronLeft, TriangleAlert, FileText, CheckCircle2, XCircle, Sparkles, Check, X } from "lucide-react";
import { PageShell, SectionLabel, PageTitle, CardTitle, Card, Chip, Button } from "../components/shared";

// Body-size meta text (never monospace).
const META = { fontSize: 13, color: "rgba(11,42,48,0.7)" };
const BODY = { fontSize: 15, color: "rgba(11,42,48,0.85)", lineHeight: 1.6 };

// Input styling that matches shared Field (white, 1.5px control border).
const INPUT_STYLE = { border: "1.5px solid var(--pm-border-control)", borderRadius: 14, padding: "12px 16px", fontSize: 15, color: "var(--pm-ink)", background: "var(--pm-white)", width: "100%" };

// Fit score colour by band, from existing tokens only.
function scoreColor(score) {
  if (score >= 70) return "var(--pm-teal-deep)";
  if (score >= 50) return "rgba(11,42,48,0.7)";
  return "var(--pm-ink)";
}

export default function CompanyDetail() {
  const { companyId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [company, setCompany] = useState(null);
  const [role, setRole] = useState("Software Engineer");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [resumeId, setResumeId] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [cluster, setCluster] = useState(null);

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
    } catch (err) {
      toast.error(err.response?.data?.detail || "Upload failed");
    } finally { setUploading(false); }
  };

  const startOA = async () => {
    if (!user) { navigate("/login"); return; }
    if (company.cluster_options?.length && !cluster) { toast.error("Pick a skill cluster first."); return; }
    setStarting(true);
    try {
      const { data } = await api.post("/oa/start", { company_id: companyId, resume_id: resumeId, cluster });
      navigate(`/oa/${data.attempt_id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message || "Could not start OA");
    } finally { setStarting(false); }
  };

  if (!company) return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Loading…</div></PageShell></div>;

  return (
    <div>
      <Header light />
      <PageShell>
        <Link to="/" className="inline-flex items-center gap-1 mb-6 hover:text-[var(--pm-ink)]" style={{ fontSize: 14, color: "rgba(11,42,48,0.7)" }}><ChevronLeft size={16}/> back</Link>
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div className="max-w-2xl">
            {company.generic
              ? <Chip tone="status" className="mb-3" icon={<TriangleAlert size={12}/>}>general-purpose practice · not a specific company's real OA</Chip>
              : (!company.verified && <Chip className="mb-3" icon={<TriangleAlert size={12}/>}>unverified pattern</Chip>)}
            <PageTitle>{company.name}</PageTitle>
            <p className="mt-3" style={{ fontSize: 17, color: "rgba(11,42,48,0.85)", lineHeight: 1.5 }}>{company.tagline}</p>
          </div>
          <div className="flex gap-3 flex-wrap">
            <Chip tone="status" icon={<Clock size={12}/>}>{company.time_minutes} min total</Chip>
            <Chip>{company.scoring_mode === "sectional" ? "sectional cutoffs" : "composite score"}</Chip>
          </div>
        </div>

        {/* Sections list */}
        <section className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-4">
          {company.sections.map((s, i) => (
            <Card key={s.key} padding="20px 22px">
              <div className="flex items-center gap-4">
                <div className="grid place-items-center shrink-0 font-display font-semibold" style={{ width: 40, height: 40, borderRadius: 12, background: "var(--pm-sky)", color: "var(--pm-ink)", fontSize: 16 }}>{i+1}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-display font-semibold" style={{ fontSize: 18, color: "var(--pm-ink)" }}>{s.name}</div>
                  <div className="mt-1" style={META}>
                    {s.type} • {s.count} q • {s.minutes} min • cutoff {Math.round(s.cutoff*100)}%{s.negative ? " • negative marking" : ""}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </section>

        {/* Resume upload + start */}
        <section className="mt-12 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <form onSubmit={uploadResume} className="flex">
            <Card className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <FileText size={18} style={{ color: "var(--pm-teal-deep)" }} />
                <CardTitle>Optional: upload your resume</CardTitle>
              </div>
              <p className="mb-5" style={BODY}>An AI recruiter reads your resume against this exact role. Always free.</p>
              <label htmlFor="company-resume-role" style={{ fontSize: 14, color: "rgba(11,42,48,0.85)" }}>Target role</label>
              <input id="company-resume-role" data-testid={TID.resumeRoleInput} value={role} onChange={e => setRole(e.target.value)} className="mt-1.5 mb-4 outline-none focus:outline-[3px] focus:outline-offset-2 focus:outline-[var(--pm-teal-night)] focus:border-[var(--pm-teal-deep)]" style={INPUT_STYLE} placeholder="e.g. Software Engineer (Backend)" />
              <input aria-label="Resume PDF" data-testid={TID.resumeUploadInput} type="file" accept="application/pdf" onChange={e => setFile(e.target.files?.[0] || null)} className="mb-4 outline-none focus:outline-[3px] focus:outline-offset-2 focus:outline-[var(--pm-teal-night)]" style={{ ...INPUT_STYLE, padding: "10px 12px", fontSize: 14 }} />
              <Button data-testid={TID.resumeSubmit} type="submit" variant="secondary" disabled={uploading || !file} className="w-full">
                {uploading ? "Analysing…" : (resumeId ? "Re-analyse" : "Analyse resume")}
              </Button>
              {resumeId && <div className="mt-3" style={{ fontSize: 13, color: "var(--pm-teal-deep)", fontWeight: 600 }}>✓ resume attached to this run</div>}
            </Card>
          </form>

          <Card style={{ background: "var(--pm-teal-night)", border: "none", boxShadow: "0 20px 40px -22px rgba(7,59,67,0.6)" }} className="!text-[var(--pm-white)]">
            <div className="flex flex-col justify-between flex-1 gap-6">
              <div>
                <span className="inline-flex rounded-full" style={{ background: "rgba(255,255,255,0.12)", color: "var(--pm-white)", fontSize: 13, padding: "4px 10px" }}>ready when you are</span>
                <div className="font-display font-semibold mt-4" style={{ fontSize: 26, lineHeight: 1.2, color: "var(--pm-white)" }}>
                  Start the full {company.name} run, with real section timing.
                </div>
                <div className="mt-3" style={{ fontSize: 15, color: "rgba(255,255,255,0.8)" }}>Total: {company.time_minutes} minutes · {company.sections.length} sections</div>
                {company.cluster_options?.length > 0 && (
                  <div className="mt-6">
                    <SectionLabel onDark>Pick your skill cluster</SectionLabel>
                    <div className="flex gap-2 flex-wrap">
                      {company.cluster_options.map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          data-testid={TID.clusterOption(opt)}
                          aria-pressed={cluster === opt}
                          onClick={() => setCluster(opt)}
                          className="font-display font-semibold rounded-full px-4 py-2 transition-colors focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[var(--pm-lime)]"
                          style={cluster === opt
                            ? { fontSize: 15, background: "var(--pm-lime)", color: "var(--pm-ink)", border: "1.5px solid var(--pm-lime)" }
                            : { fontSize: 15, background: "transparent", color: "var(--pm-white)", border: "1.5px solid rgba(255,255,255,0.5)" }}
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div>
                <Button variant="lime" onClick={startOA} disabled={starting} className="w-full">
                  {starting ? "Starting…" : (<>Start OA <ArrowRight size={14}/></>)}
                </Button>
                <button data-testid={TID.resumeSkip} onClick={() => setResumeId(null)} className="mt-3 hover:text-[var(--pm-white)] underline-offset-2 hover:underline" style={{ fontSize: 14, color: "rgba(255,255,255,0.75)" }}>skip resume for this run</button>
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
                  <div className="flex items-center gap-2" style={{ color: "var(--pm-teal-deep)" }}>
                    <Sparkles size={16} />
                    <SectionLabel className="!mb-0">resume analysis · {role}</SectionLabel>
                  </div>
                  <CardTitle style={{ fontSize: 26, marginTop: 4 }}>Here's what our AI recruiter read from your resume.</CardTitle>
                </div>
                <div className="text-center">
                  <div className="pm-eyebrow" style={{ color: "rgba(11,42,48,0.7)" }}>Fit score</div>
                  <div className="font-display font-semibold leading-none mt-1" style={{ fontSize: 56, color: scoreColor(analysis.fit_score ?? 0) }}>
                    {analysis.fit_score ?? "N/A"}
                  </div>
                  <div className="mt-1" style={META}>/ 100</div>
                </div>
              </div>

              {analysis.verdict && (
                <div className="mb-6 p-4 rounded-[16px]" style={{ background: "var(--pm-sky)", ...BODY, color: "var(--pm-ink)" }}>
                  <span className="pm-eyebrow mr-2" style={{ fontSize: 11, color: "rgba(11,42,48,0.7)" }}>verdict</span>
                  {analysis.verdict}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 size={16} style={{ color: "var(--pm-teal-deep)" }} />
                    <CardTitle style={{ fontSize: 18 }}>Strengths</CardTitle>
                  </div>
                  <ul className="space-y-2">
                    {(analysis.strengths || []).map((s, i) => (
                      <li key={i} className="flex gap-2" style={BODY}>
                        <Check size={16} className="shrink-0 mt-1" style={{ color: "var(--pm-teal-deep)" }} aria-hidden="true" />
                        <span>{s}</span>
                      </li>
                    ))}
                    {(!analysis.strengths || analysis.strengths.length === 0) && <li style={{ ...BODY, color: "rgba(11,42,48,0.7)" }}>None identified.</li>}
                  </ul>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <XCircle size={16} style={{ color: "var(--pm-error-text)" }} />
                    <CardTitle style={{ fontSize: 18 }}>Weaknesses</CardTitle>
                  </div>
                  <ul className="space-y-2">
                    {(analysis.weaknesses || []).map((s, i) => (
                      <li key={i} className="flex gap-2" style={BODY}>
                        <X size={16} className="shrink-0 mt-1" style={{ color: "var(--pm-error-text)" }} aria-hidden="true" />
                        <span>{s}</span>
                      </li>
                    ))}
                    {(!analysis.weaknesses || analysis.weaknesses.length === 0) && <li style={{ ...BODY, color: "rgba(11,42,48,0.7)" }}>None identified.</li>}
                  </ul>
                </div>
              </div>

              {analysis.extracted_projects?.length > 0 && (
                <div className="mt-8">
                  <CardTitle style={{ fontSize: 18, marginBottom: 12 }}>Projects we pulled out</CardTitle>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {analysis.extracted_projects.map((p, i) => (
                      <Card key={i} padding="16px 18px" style={{ borderRadius: 18, boxShadow: "none" }}>
                        <div className="font-display font-semibold" style={{ fontSize: 16, color: "var(--pm-ink)" }}>{p.name}</div>
                        <div className="mt-1" style={{ fontSize: 13, color: "var(--pm-teal-deep)", fontWeight: 600 }}>{p.tech_stack}</div>
                        <div className="mt-2" style={{ fontSize: 14, color: "rgba(11,42,48,0.85)", lineHeight: 1.6 }}>{p.one_line_summary}</div>
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
