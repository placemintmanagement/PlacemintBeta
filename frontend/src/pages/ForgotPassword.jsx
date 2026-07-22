import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";

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
        toast.success("Dev mode: reset link below — no email sent.");
      } else {
        toast.success("Reset link sent (check your inbox).");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Something went wrong");
    } finally { setLoading(false); }
  };

  return (
    <div>
      <Header />
      <div className="max-w-md mx-auto px-6 py-16">
        <h1 className="font-display text-4xl font-bold mb-2">Forgot password?</h1>
        <p className="text-pm-text2 mb-8">We'll send you a reset link. It expires in 30 minutes.</p>

        {!sent ? (
          <form onSubmit={submit} className="space-y-4">
            <input
              data-testid="forgot-email"
              type="email" required placeholder="you@campus.edu"
              value={email} onChange={e => setEmail(e.target.value)}
              className="pm-input"
            />
            <button data-testid="forgot-submit" disabled={loading} className="w-full pm-btn pm-btn-primary py-3">
              {loading ? "Sending…" : "Send reset link"}
            </button>
          </form>
        ) : (
          <div className="pm-card p-6">
            <div className="font-display text-lg font-bold">Check your email.</div>
            <p className="text-sm text-pm-text2 mt-1">If <span className="font-mono">{email}</span> is registered, a reset link was sent.</p>
            {devLink && (
              <div className="mt-4 border-t pt-4">
                <div className="text-xs font-mono uppercase text-pm-secondary mb-2">dev mode · test link</div>
                <Link to={devLink} data-testid="forgot-dev-link" className="text-pm-primary-dark underline break-all text-xs font-mono">
                  {window.location.origin + devLink}
                </Link>
              </div>
            )}
          </div>
        )}

        <div className="text-sm text-pm-text2 mt-6 text-center">
          Remembered it? <Link to="/login" className="text-pm-primary-dark font-semibold">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
