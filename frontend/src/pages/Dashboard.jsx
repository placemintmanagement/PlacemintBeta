import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { useAuth } from "../auth";
import { FileText, ArrowRight, Trophy, MailCheck } from "lucide-react";

export default function Dashboard() {
  const { user, refresh } = useAuth();
  const [data, setData] = useState(null);
  const [sendingVerify, setSendingVerify] = useState(false);

  useEffect(() => {
    api.get("/dashboard").then(r => setData(r.data));
  }, []);

  const sendVerification = async () => {
    setSendingVerify(true);
    try {
      const { data } = await api.post("/auth/email/send-verification");
      if (data.already_verified) {
        toast.success("Email already verified.");
        refresh();
      } else if (data.dev_link) {
        toast.success("Dev mode: verification link below.", { duration: 8000, description: data.dev_link });
      } else {
        toast.success("Verification email sent. Check your inbox.");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not send verification email");
    } finally { setSendingVerify(false); }
  };

  if (!user) return null;

  return (
    <div>
      <Header />
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-10 pm-in">
        {/* Verify-email banner — only for password-based unverified users */}
        {user.email_verified === false && user.auth_provider === "password" && (
          <div data-testid="verify-email-banner" className="pm-card p-4 mb-6 flex items-center gap-4 border-pm-secondary/40 bg-pm-secondary/5">
            <MailCheck className="text-pm-secondary shrink-0" />
            <div className="flex-1">
              <div className="font-display font-bold">Verify your email</div>
              <div className="text-sm text-pm-text2">Not required to use Placemint, but recommended for account recovery.</div>
            </div>
            <button data-testid="send-verify-btn" onClick={sendVerification} disabled={sendingVerify}
                    className="pm-btn pm-btn-secondary text-sm py-2 px-4 shrink-0">
              {sendingVerify ? "Sending…" : "Send link"}
            </button>
          </div>
        )}
        <div className="flex items-start justify-between flex-wrap gap-4 mb-10">
          <div>
            <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark">dashboard</div>
            <h1 className="font-display text-4xl font-bold mt-1">Hey {user.name?.split(" ")[0]}.</h1>
            <p className="text-pm-text2 mt-1">Pick a company below to start a full run. Resume check is optional but recommended.</p>
          </div>
          <div className="flex gap-3 flex-wrap">
            <div className="pm-card px-5 py-4">
              <div className="text-xs font-mono uppercase text-pm-text2">Plan</div>
              <div className="font-display text-xl font-bold capitalize">{user.plan}</div>
              {user.entitlements?.plan_expires_at && (
                <div className="text-[10px] font-mono text-pm-text2 mt-0.5">
                  expires {new Date(user.entitlements.plan_expires_at).toLocaleDateString()}
                </div>
              )}
            </div>
            <div className="pm-card px-5 py-4">
              <div className="text-xs font-mono uppercase text-pm-text2">Plan runs left</div>
              <div className="font-display text-xl font-bold">
                <span className="font-mono" data-testid="plan-runs-remaining">
                  {user.entitlements?.runs_remaining_on_plan ?? Math.max(0, (user.runs_quota ?? 0) - (user.runs_used ?? 0))}
                </span>
                <span className="text-pm-text2 text-sm ml-1">/ {user.entitlements?.run_limit ?? user.runs_quota}</span>
              </div>
            </div>
            <div className="pm-card px-5 py-4">
              <div className="text-xs font-mono uppercase text-pm-text2">Credits</div>
              <div className="font-display text-xl font-bold">
                <span className="font-mono" data-testid="credits-balance">{user.entitlements?.credits ?? user.credits ?? 0}</span>
                <span className="text-pm-text2 text-sm ml-1">never expire</span>
              </div>
              <Link to="/pricing" className="text-[10px] font-mono text-pm-primary-dark mt-0.5 inline-block">buy more →</Link>
            </div>
          </div>
        </div>

        {/* Attempts */}
        <section className="mb-14">
          <div className="flex items-end justify-between mb-4">
            <h2 className="font-display text-2xl font-bold">Recent attempts</h2>
            <Link to="/#companies" className="text-sm text-pm-primary-dark font-mono">start new →</Link>
          </div>
          {(!data || data.attempts.length === 0) ? (
            <div className="pm-card p-10 text-center">
              <Trophy className="mx-auto text-pm-primary" />
              <div className="font-display text-xl font-bold mt-3">No attempts yet.</div>
              <div className="text-pm-text2 text-sm mt-1">Pick a company from the landing page to begin your first end-to-end run.</div>
              <Link to="/" className="pm-btn pm-btn-primary mt-6 inline-flex">Browse companies <ArrowRight size={14} /></Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.attempts.map(a => (
                <Link key={a.attempt_id} to={a.status === "completed" ? `/attempt/${a.attempt_id}/review` : `/oa/${a.attempt_id}`} className="pm-card p-5 block">
                  <div className="flex items-center justify-between">
                    <div className="font-display font-bold">{a.company_name}</div>
                    <span className={`pm-chip ${a.status === "completed" ? "pm-chip-primary" : "pm-chip-coral"}`}>{a.status}</span>
                  </div>
                  <div className="mt-3 text-xs font-mono text-pm-text2">Sections: {a.sections_done}/{a.sections_total}</div>
                  <div className="mt-1 text-xs font-mono text-pm-text2">{new Date(a.created_at).toLocaleString()}</div>
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Resumes */}
        <section>
          <div className="flex items-end justify-between mb-4">
            <h2 className="font-display text-2xl font-bold">Resume checks</h2>
          </div>
          {(!data || data.resumes.length === 0) ? (
            <div className="pm-card p-6 flex items-center gap-4">
              <FileText />
              <div className="flex-1">
                <div className="font-display font-bold">No resumes uploaded yet.</div>
                <div className="text-pm-text2 text-sm">Upload one when you start a company. It's free and personalises everything.</div>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.resumes.map(r => (
                <div key={r.resume_id} className="pm-card p-5">
                  <div className="font-display font-bold">{r.role} · {r.company_id}</div>
                  <div className="text-xs font-mono text-pm-text2 mt-2">fit score</div>
                  <div className="font-mono text-3xl font-bold">{r.fit_score ?? "N/A"}</div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
