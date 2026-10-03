import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "../api";
import Header from "../components/Header";
import { CheckCircle2, XCircle } from "lucide-react";
import { PageShell, PageTitle, Button } from "../components/shared";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const [status, setStatus] = useState("pending"); // pending | ok | error
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = params.get("token");
    if (!token) { setStatus("error"); setMessage("No verification token in URL"); return; }
    (async () => {
      try {
        await api.post("/auth/email/verify", { token });
        setStatus("ok");
      } catch (err) {
        setStatus("error");
        setMessage(err.response?.data?.detail || "Verification failed");
      }
    })();
  }, [params]);

  return (
    <div>
      <Header light />
      <PageShell>
        <div className="max-w-md mx-auto text-center py-16">
          {status === "pending" && (
            <>
              <div className="w-9 h-9 mx-auto rounded-full animate-spin" style={{ border: "2px solid var(--pm-teal-deep)", borderTopColor: "transparent" }}></div>
              <div className="mt-4" style={{ fontSize: 15, color: "rgba(11,42,48,0.7)" }}>Verifying your email…</div>
            </>
          )}
          {status === "ok" && (
            <>
              <CheckCircle2 className="mx-auto" size={48} style={{ color: "var(--pm-teal-deep)" }} aria-hidden="true" />
              <PageTitle as="h2" className="mt-4">Email verified.</PageTitle>
              <p className="mt-2" style={{ fontSize: 16, color: "rgba(11,42,48,0.85)" }}>You're all set. Head back to your dashboard.</p>
              <div className="mt-6 flex justify-center">
                <Button as={Link} to="/dashboard" data-testid="verify-back-dashboard">Back to dashboard</Button>
              </div>
            </>
          )}
          {status === "error" && (
            <>
              <XCircle className="mx-auto" size={48} style={{ color: "var(--pm-ink)" }} aria-hidden="true" />
              <PageTitle as="h2" className="mt-4">Couldn't verify.</PageTitle>
              <p className="mt-2" style={{ fontSize: 16, color: "rgba(11,42,48,0.85)" }}>{message}. Links expire after 30 minutes. Request a new one from your dashboard.</p>
              <div className="mt-6 flex justify-center">
                <Button as={Link} to="/dashboard" variant="secondary">Go to dashboard</Button>
              </div>
            </>
          )}
        </div>
      </PageShell>
    </div>
  );
}
