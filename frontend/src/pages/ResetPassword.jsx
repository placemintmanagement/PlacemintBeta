import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { PageShell, PageTitle, Button } from "../components/shared";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const t = params.get("token");
    if (t) setToken(t);
  }, [params]);

  const submit = async (e) => {
    e.preventDefault();
    if (password !== confirm) { toast.error("Passwords don't match"); return; }
    if (password.length < 6) { toast.error("Password must be at least 6 characters"); return; }
    setLoading(true);
    try {
      await api.post("/auth/password/reset", { token, new_password: password });
      toast.success("Password reset. Sign in with your new password.");
      navigate("/login");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Reset failed. Link may be expired");
    } finally { setLoading(false); }
  };

  return (
    <div>
      <Header light />
      <PageShell>
        <div className="max-w-md mx-auto py-16">
          <PageTitle as="h1" style={{ fontSize: "clamp(2rem, 4vw, 2.75rem)" }}>Set a new password</PageTitle>
          <p className="mt-3 mb-8" style={{ fontSize: 16, color: "rgba(11,42,48,0.85)" }}>Choose something you'll actually remember.</p>

          <form onSubmit={submit} className="space-y-4">
            {!params.get("token") && (
              <input
                data-testid="reset-token"
                required placeholder="paste reset token"
                aria-label="Reset token"
                value={token} onChange={e => setToken(e.target.value)}
                className="pm-input"
                style={{ fontSize: 13 }}
              />
            )}
            <input
              data-testid="reset-password"
              type="password" required minLength={6} placeholder="new password (min 6 chars)"
              aria-label="New password"
              value={password} onChange={e => setPassword(e.target.value)}
              className="pm-input"
              style={{ fontSize: 15 }}
            />
            <input
              data-testid="reset-confirm"
              type="password" required placeholder="confirm new password"
              aria-label="Confirm new password"
              value={confirm} onChange={e => setConfirm(e.target.value)}
              className="pm-input"
              style={{ fontSize: 15 }}
            />
            <Button type="submit" data-testid="reset-submit" disabled={loading} className="w-full">
              {loading ? "Resetting…" : "Reset password"}
            </Button>
          </form>

          <div className="mt-6 text-center" style={{ fontSize: 15, color: "rgba(11,42,48,0.85)" }}>
            <Link to="/login" className="font-semibold underline underline-offset-2" style={{ color: "var(--pm-teal-deep)" }}>Back to sign in</Link>
          </div>
        </div>
      </PageShell>
    </div>
  );
}
