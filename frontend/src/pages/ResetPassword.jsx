import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";

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
      <Header />
      <div className="max-w-md mx-auto px-6 py-16">
        <h1 className="font-display text-4xl font-bold mb-2">Set a new password</h1>
        <p className="text-pm-text2 mb-8">Choose something you'll actually remember.</p>

        <form onSubmit={submit} className="space-y-4">
          {!params.get("token") && (
            <input
              data-testid="reset-token"
              required placeholder="paste reset token"
              value={token} onChange={e => setToken(e.target.value)}
              className="pm-input font-mono text-xs"
            />
          )}
          <input
            data-testid="reset-password"
            type="password" required minLength={6} placeholder="new password (min 6 chars)"
            value={password} onChange={e => setPassword(e.target.value)}
            className="pm-input"
          />
          <input
            data-testid="reset-confirm"
            type="password" required placeholder="confirm new password"
            value={confirm} onChange={e => setConfirm(e.target.value)}
            className="pm-input"
          />
          <button data-testid="reset-submit" disabled={loading} className="w-full pm-btn pm-btn-primary py-3">
            {loading ? "Resetting…" : "Reset password"}
          </button>
        </form>

        <div className="text-sm text-pm-text2 mt-6 text-center">
          <Link to="/login" className="text-pm-primary-dark font-semibold">Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}
