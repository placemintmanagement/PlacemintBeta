import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "../api";
import Header from "../components/Header";
import { CheckCircle2, XCircle } from "lucide-react";

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
      <Header />
      <div className="max-w-md mx-auto px-6 py-24 text-center">
        {status === "pending" && (
          <>
            <div className="w-8 h-8 mx-auto border-2 border-pm-primary border-t-transparent rounded-full animate-spin"></div>
            <div className="mt-4 text-sm text-pm-text2 font-mono">Verifying your email…</div>
          </>
        )}
        {status === "ok" && (
          <>
            <CheckCircle2 className="mx-auto text-pm-primary" size={48} />
            <h1 className="font-display text-3xl font-bold mt-4">Email verified.</h1>
            <p className="text-pm-text2 mt-2">You're all set. Head back to your dashboard.</p>
            <Link to="/dashboard" data-testid="verify-back-dashboard" className="pm-btn pm-btn-primary mt-6 inline-flex">Back to dashboard</Link>
          </>
        )}
        {status === "error" && (
          <>
            <XCircle className="mx-auto text-pm-secondary" size={48} />
            <h1 className="font-display text-3xl font-bold mt-4">Couldn't verify.</h1>
            <p className="text-pm-text2 mt-2">{message}. Links expire after 30 minutes. Request a new one from your dashboard.</p>
            <Link to="/dashboard" className="pm-btn pm-btn-ghost mt-6 inline-flex">Go to dashboard</Link>
          </>
        )}
      </div>
    </div>
  );
}
