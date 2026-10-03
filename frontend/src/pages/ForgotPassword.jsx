import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { PageShell, PageTitle, Card, Button } from "../components/shared";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [devLink, setDevLink] = useState(null);
  const [sent, setSent] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/password/forgot", { email });
      setSent(true);
      // Dev mode: the backend echoes back the reset link so we can test without email.
      if (data.dev_link) {
        setDevLink(data.dev_link);
        toast.success("Dev mode: reset link below. No email sent.");
      } else {
        toast.success("Reset link sent (check your inbox).");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Something went wrong");
    } finally { setLoading(false); }
  };

  return (
    <div>
      <Header light />
      <PageShell>
        <div className="max-w-md mx-auto py-16">
          <PageTitle as="h1" style={{ fontSize: "clamp(2rem, 4vw, 2.75rem)" }}>Forgot password?</PageTitle>
          <p className="mt-3 mb-8" style={{ fontSize: 16, color: "rgba(11,42,48,0.85)" }}>We'll send you a reset link. It expires in 30 minutes.</p>

          {!sent ? (
            <form onSubmit={submit} className="space-y-4">
              <input
                data-testid="forgot-email"
                type="email" required placeholder="you@campus.edu"
                aria-label="Email"
                value={email} onChange={e => setEmail(e.target.value)}
                className="pm-input"
                style={{ fontSize: 15 }}
              />
              <Button type="submit" data-testid="forgot-submit" disabled={loading} className="w-full">
                {loading ? "Sending…" : "Send reset link"}
              </Button>
            </form>
          ) : (
            <Card>
              <div className="font-display font-semibold" style={{ fontSize: 20, color: "var(--pm-ink)" }}>Check your email.</div>
              <p className="mt-1" style={{ fontSize: 15, color: "rgba(11,42,48,0.85)" }}>If <span style={{ fontWeight: 600 }}>{email}</span> is registered, a reset link was sent.</p>
              {devLink && (
                <div className="mt-4 pt-4" style={{ borderTop: "1px solid rgba(7,59,67,0.08)" }}>
                  <div className="pm-eyebrow mb-2" style={{ fontSize: 12, color: "var(--pm-ink)" }}>dev mode · test link</div>
                  <Link to={devLink} data-testid="forgot-dev-link" className="underline underline-offset-2 break-all" style={{ fontSize: 13, color: "var(--pm-teal-deep)", fontWeight: 600 }}>
                    {window.location.origin + devLink}
                  </Link>
                </div>
              )}
            </Card>
          )}

          <div className="mt-6 text-center" style={{ fontSize: 15, color: "rgba(11,42,48,0.85)" }}>
            Remembered it? <Link to="/login" className="font-semibold underline underline-offset-2" style={{ color: "var(--pm-teal-deep)" }}>Sign in</Link>
          </div>
        </div>
      </PageShell>
    </div>
  );
}
