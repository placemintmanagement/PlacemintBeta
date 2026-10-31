import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { useAuth } from "../auth";
import { FileText, ArrowRight, Trophy, MailCheck } from "lucide-react";
import { PageShell, SectionLabel, PageTitle, Card, Chip, Button, EmptyState } from "../components/shared";

// Label used for small stat captions and meta lines (body font, not mono).
const META = { fontSize: 13, color: "rgba(11,42,48,0.7)" };

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
      <Header light />
      <PageShell>
        {/* Verify-email banner — only for password-based unverified users */}
        {user.email_verified === false && user.auth_provider === "password" && (
          <Card className="mb-6" padding="0" data-testid="verify-email-banner">
            <div className="flex items-center gap-4 flex-wrap w-full" style={{ padding: "16px 20px" }}>
              <MailCheck className="shrink-0" style={{ color: "var(--pm-teal-deep)" }} />
              <div className="flex-1 min-w-[200px]">
                <div className="font-display font-semibold" style={{ color: "var(--pm-ink)", fontSize: 16 }}>Verify your email</div>
                <div style={META}>Not required to use Placemint, but recommended for account recovery.</div>
              </div>
              <Button data-testid="send-verify-btn" onClick={sendVerification} disabled={sendingVerify} variant="secondary" className="!py-2 !px-4" style={{ fontSize: 14 }}>
                {sendingVerify ? "Sending…" : "Send link"}
              </Button>
            </div>
          </Card>
        )}

        <div className="flex items-start justify-between flex-wrap gap-6 mb-10">
          <div>
            <SectionLabel>dashboard</SectionLabel>
            <PageTitle>Hey {user.name?.split(" ")[0]}.</PageTitle>
            <p className="mt-2" style={{ fontSize: 16, color: "rgba(11,42,48,0.85)" }}>Pick a company below to start a full run. Resume check is optional but recommended.</p>
          </div>
          <div className="grid grid-cols-2 md:flex gap-3 w-full md:w-auto">
            <Card style={{ borderRadius: 20 }} padding="0">
              <div style={{ padding: "16px 20px" }}>
                <div style={META}>Plan</div>
                <div className="font-display font-semibold capitalize" style={{ fontSize: 22, color: "var(--pm-ink)" }}>{user.plan}</div>
                {user.entitlements?.plan_expires_at && (
                  <div style={{ ...META, fontSize: 12, marginTop: 2 }}>
                    expires {new Date(user.entitlements.plan_expires_at).toLocaleDateString()}
                  </div>
                )}
              </div>
            </Card>
            <Card style={{ borderRadius: 20 }} padding="0">
              <div style={{ padding: "16px 20px" }}>
                <div style={META}>Plan runs left</div>
                <div className="font-display font-semibold" style={{ fontSize: 22, color: "var(--pm-ink)" }}>
                  <span data-testid="plan-runs-remaining">
                    {user.entitlements?.runs_remaining_on_plan ?? Math.max(0, (user.runs_quota ?? 0) - (user.runs_used ?? 0))}
                  </span>
                  <span style={{ ...META, fontSize: 14, marginLeft: 4 }}>/ {user.entitlements?.run_limit ?? user.runs_quota}</span>
                </div>
              </div>
            </Card>
            <Card style={{ borderRadius: 20 }} padding="0" className="col-span-2 md:col-span-1">
              <div style={{ padding: "16px 20px" }}>
                <div style={META}>Credits</div>
                <div className="font-display font-semibold" style={{ fontSize: 22, color: "var(--pm-ink)" }}>
                  <span data-testid="credits-balance">{user.entitlements?.credits ?? user.credits ?? 0}</span>
                  <span style={{ ...META, fontSize: 14, marginLeft: 4 }}>never expire</span>
                </div>
                <Link to="/pricing" className="mt-1 inline-flex items-center gap-1 font-semibold" style={{ fontSize: 13, color: "var(--pm-teal-deep)" }}>
                  buy more <ArrowRight size={12} aria-hidden="true" />
                </Link>
              </div>
            </Card>
          </div>
        </div>

        {/* Attempts */}
        <section className="mb-14">
          <div className="flex items-end justify-between mb-5 gap-4">
            <PageTitle as="h2">Recent attempts</PageTitle>
            <Link to="/#companies" className="inline-flex items-center gap-1 font-semibold whitespace-nowrap" style={{ fontSize: 14, color: "var(--pm-teal-deep)" }}>
              start new <ArrowRight size={14} aria-hidden="true" />
            </Link>
          </div>
          {(!data || data.attempts.length === 0) ? (
            <Card style={{ textAlign: "center" }}>
              <div className="flex flex-col items-center">
                <Trophy style={{ color: "var(--pm-teal-deep)" }} />
                <EmptyState
                  title="No attempts yet."
                  body="Pick a company from the landing page to begin your first end-to-end run."
                  action={<Button as={Link} to="/">Browse companies <ArrowRight size={14} aria-hidden="true" /></Button>}
                />
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.attempts.map(a => (
                <Link key={a.attempt_id} to={a.status === "completed" ? `/attempt/${a.attempt_id}/review` : `/oa/${a.attempt_id}`} className="block rounded-[24px]">
                  <Card interactive>
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-display font-semibold" style={{ fontSize: 18, color: "var(--pm-ink)" }}>{a.company_name}</div>
                      <Chip tone={a.status === "completed" ? "status" : "neutral"}>{a.status}</Chip>
                    </div>
                    <div className="mt-3" style={META}>Sections: {a.sections_done}/{a.sections_total}</div>
                    <div className="mt-1" style={META}>{new Date(a.created_at).toLocaleString()}</div>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Resumes */}
        <section>
          <div className="flex items-end justify-between mb-5">
            <PageTitle as="h2">Resume checks</PageTitle>
          </div>
          {(!data || data.resumes.length === 0) ? (
            <Card>
              <div className="flex items-center gap-4 flex-wrap">
                <FileText className="shrink-0" style={{ color: "var(--pm-teal-deep)" }} />
                <div className="flex-1 min-w-[200px]">
                  <div className="font-display font-semibold" style={{ fontSize: 18, color: "var(--pm-ink)" }}>No resumes uploaded yet.</div>
                  <div style={META}>Upload one when you start a company. It's free and personalises everything.</div>
                </div>
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.resumes.map(r => (
                <Card key={r.resume_id}>
                  <div className="font-display font-semibold" style={{ fontSize: 18, color: "var(--pm-ink)" }}>{r.role} · {r.company_id}</div>
                  <div className="mt-3" style={META}>fit score</div>
                  <div className="font-display font-semibold" style={{ fontSize: 36, lineHeight: 1.1, color: "var(--pm-teal-deep)" }}>{r.fit_score ?? "N/A"}</div>
                </Card>
              ))}
            </div>
          )}
        </section>
      </PageShell>
    </div>
  );
}
