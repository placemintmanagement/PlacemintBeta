import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { useAuth } from "../auth";
import { TID } from "../testIds";
import { Clock, ArrowRight, ChevronLeft, TriangleAlert, FileText, CheckCircle2, XCircle, Sparkles } from "lucide-react";

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

  if (!company) return <div><Header /><div className="p-10 text-center text-pm-text2">Loading…</div></div>;

  return (
    <div>
      <Header />
      <div className="max-w-6xl mx-auto px-6 lg:px-10 py-10 pm-in">
        <Link to="/" className="inline-flex items-center gap-1 text-sm text-pm-text2 mb-6 hover:text-pm-text"><ChevronLeft size={16}/> back</Link>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            {company.generic
              ? <span className="pm-chip pm-chip-primary mb-3"><TriangleAlert size={12}/> general-purpose practice · not a specific company's real OA</span>
              : (!company.verified && <span className="pm-chip pm-chip-coral mb-3"><TriangleAlert size={12}/> unverified pattern</span>)}
            <h1 className="font-display text-4xl lg:text-5xl font-bold">{company.name}</h1>
            <p className="text-pm-text2 mt-2 max-w-2xl">{company.tagline}</p>
          </div>
          <div className="flex gap-3">
            <span className="pm-chip pm-chip-primary"><Clock size={12}/> {company.time_minutes} min total</span>
            <span className="pm-chip">{company.scoring_mode === "sectional" ? "sectional cutoffs" : "composite score"}</span>
          </div>
        </div>

        {/* Sections list */}
        <section className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-4">
          {company.sections.map((s, i) => (
            <div key={s.key} className="pm-card p-5 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-pm-muted grid place-items-center font-mono font-bold">{i+1}</div>
              <div className="flex-1">
                <div className="font-display font-bold">{s.name}</div>
                <div className="text-xs font-mono text-pm-text2 mt-1">
                  {s.type} • {s.count} q • {s.minutes} min • cutoff {Math.round(s.cutoff*100)}%{s.negative ? " • negative marking" : ""}
                </div>
              </div>
            </div>
          ))}
        </section>

        {/* Resume upload + start */}
        <section className="mt-12 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <form onSubmit={uploadResume} className="pm-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <FileText size={18} className="text-pm-primary" />
              <div className="font-display text-lg font-bold">Optional: upload your resume</div>
            </div>
            <p className="text-sm text-pm-text2 mb-4">An AI recruiter reads your resume against this exact role. Free — always.</p>
            <label className="text-xs font-mono uppercase text-pm-text2">Target role</label>
            <input data-testid={TID.resumeRoleInput} value={role} onChange={e => setRole(e.target.value)} className="pm-input mt-1 mb-3" placeholder="e.g. Software Engineer (Backend)" />
            <input data-testid={TID.resumeUploadInput} type="file" accept="application/pdf" onChange={e => setFile(e.target.files?.[0] || null)} className="pm-input mb-3" />
            <button data-testid={TID.resumeSubmit} type="submit" disabled={uploading || !file} className="pm-btn pm-btn-secondary text-sm py-2 w-full">
              {uploading ? "Analysing…" : (resumeId ? "Re-analyse" : "Analyse resume")}
            </button>
            {resumeId && <div className="mt-3 text-xs font-mono text-pm-primary-dark">✓ resume attached to this run</div>}
          </form>

          <div className="pm-card p-6 bg-[#0A0A0A] text-white flex flex-col justify-between hover:!transform-none">
            <div>
              <div className="pm-chip" style={{ background: "rgba(255,255,255,0.08)", color: "#fff" }}>ready when you are</div>
              <div className="font-display text-2xl font-bold mt-4 leading-tight">
                Start the full {company.name} run — with real section timing.
              </div>
              <div className="text-sm text-white/70 mt-3">Total: <span className="font-mono">{company.time_minutes} minutes</span> · {company.sections.length} sections</div>
              {company.cluster_options?.length > 0 && (
                <div className="mt-5">
                  <div className="text-xs font-mono uppercase text-white/60 mb-2">Pick your skill cluster</div>
                  <div className="flex gap-2">
                    {company.cluster_options.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        data-testid={TID.clusterOption(opt)}
                        onClick={() => setCluster(opt)}
                        className={`px-4 py-2 rounded-lg text-sm font-mono border transition-colors ${
                          cluster === opt
                            ? "bg-white text-black border-white"
                            : "bg-transparent text-white/70 border-white/30 hover:border-white/60"
                        }`}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <button data-testid={TID.startOaBtn} onClick={startOA} disabled={starting} className="pm-btn pm-btn-primary mt-6 w-full">
              {starting ? "Starting…" : (<>Start OA <ArrowRight size={14}/></>)}
            </button>
            <button data-testid={TID.resumeSkip} onClick={() => setResumeId(null)} className="text-xs text-white/50 mt-2 hover:text-white">skip resume for this run</button>
          </div>
        </section>

        {/* Resume analysis result panel — shown as soon as the AI replies. */}
        {analysis && (
          <section data-testid="resume-analysis-panel" className="mt-8 pm-card p-8 pm-in">
            <div className="flex items-start justify-between flex-wrap gap-4 mb-6">
              <div>
                <div className="flex items-center gap-2 text-pm-primary-dark">
                  <Sparkles size={16} />
                  <span className="font-mono text-xs uppercase tracking-widest">resume analysis · {role}</span>
                </div>
                <div className="font-display text-2xl font-bold mt-1">Here's what our AI recruiter read from your resume.</div>
              </div>
              <div className="text-center">
                <div className="text-xs font-mono uppercase text-pm-text2">Fit score</div>
                <div className="font-display font-bold font-mono text-5xl leading-none mt-1"
                     style={{ color: (analysis.fit_score ?? 0) >= 70 ? "#0FAE73" : (analysis.fit_score ?? 0) >= 50 ? "#FF6F4D" : "#DC2626" }}>
                  {analysis.fit_score ?? "—"}
                </div>
                <div className="text-[10px] font-mono text-pm-text2 mt-1">/ 100</div>
              </div>
            </div>

            {analysis.verdict && (
              <div className="mb-6 p-4 rounded-lg bg-pm-muted text-pm-text leading-relaxed">
                <span className="font-mono text-[10px] uppercase tracking-widest text-pm-text2 mr-2">verdict</span>
                {analysis.verdict}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <CheckCircle2 size={16} className="text-pm-primary" />
                  <div className="font-display font-bold">Strengths</div>
                </div>
                <ul className="space-y-2">
                  {(analysis.strengths || []).map((s, i) => (
                    <li key={i} className="text-sm flex gap-2">
                      <span className="text-pm-primary shrink-0">✓</span>
                      <span>{s}</span>
                    </li>
                  ))}
                  {(!analysis.strengths || analysis.strengths.length === 0) && <li className="text-sm text-pm-text2">None identified.</li>}
                </ul>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <XCircle size={16} className="text-pm-secondary" />
                  <div className="font-display font-bold">Weaknesses</div>
                </div>
                <ul className="space-y-2">
                  {(analysis.weaknesses || []).map((s, i) => (
                    <li key={i} className="text-sm flex gap-2">
                      <span className="text-pm-secondary shrink-0">✕</span>
                      <span>{s}</span>
                    </li>
                  ))}
                  {(!analysis.weaknesses || analysis.weaknesses.length === 0) && <li className="text-sm text-pm-text2">None identified.</li>}
                </ul>
              </div>
            </div>

            {analysis.extracted_projects?.length > 0 && (
              <div className="mt-8">
                <div className="font-display font-bold mb-3">Projects we pulled out</div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {analysis.extracted_projects.map((p, i) => (
                    <div key={i} className="p-4 border border-pm-border rounded-lg bg-white">
                      <div className="font-display font-semibold">{p.name}</div>
                      <div className="text-xs font-mono text-pm-primary-dark mt-1">{p.tech_stack}</div>
                      <div className="text-sm text-pm-text2 mt-2 leading-relaxed">{p.one_line_summary}</div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 text-xs text-pm-text2 font-mono">These become the "project questions" in your interview round.</div>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
