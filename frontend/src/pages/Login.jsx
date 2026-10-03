import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import { useAuth } from "../auth";
import Header from "../components/Header";
import { PageShell, PageTitle, Button } from "../components/shared";
import { TID } from "../testIds";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
function startGoogleLogin() {
  const redirectUrl = window.location.origin + "/dashboard";
  window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
}

const INPUT_CLASS = "w-full bg-[var(--pm-white)] outline-none focus:outline-[3px] focus:outline-offset-2 focus:outline-[var(--pm-teal-night)] focus:border-[var(--pm-teal-deep)]";
const INPUT_STYLE = { border: "1.5px solid var(--pm-border-control)", borderRadius: 14, padding: "12px 16px", fontSize: 15, color: "var(--pm-ink)" };

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { setUser } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      if (data.token) localStorage.setItem("pm_token", data.token);
      setUser(data.user);
      toast.success("Welcome back!");
      navigate("/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Header light />
      <PageShell>
        <div className="mx-auto w-full max-w-[440px] bg-[var(--pm-white)]" style={{ borderRadius: 24, border: "1px solid rgba(7,59,67,0.08)", boxShadow: "0 14px 28px -18px rgba(7,59,67,0.28)", padding: 32 }}>
          <PageTitle>Welcome back</PageTitle>
          <p className="mt-2 mb-7" style={{ color: "rgba(11,42,48,0.7)", fontSize: 15 }}>Pick up right where you left off.</p>

          <button
            data-testid={TID.loginGoogle}
            onClick={startGoogleLogin}
            className="w-full inline-flex items-center justify-center gap-2 rounded-full font-display font-semibold text-[15px] px-6 py-3 mb-6 transition-colors hover:bg-[rgba(15,111,122,0.06)] focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[var(--pm-teal-night)]"
            style={{ background: "var(--pm-white)", color: "var(--pm-teal-deep)", border: "1.5px solid var(--pm-teal-deep)" }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.530-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Continue with Google
          </button>

          <div className="flex items-center gap-3 my-4" style={{ fontSize: 13, color: "rgba(11,42,48,0.6)" }}>
            <div className="flex-1 h-px" style={{ background: "rgba(7,59,67,0.08)" }}></div> or <div className="flex-1 h-px" style={{ background: "rgba(7,59,67,0.08)" }}></div>
          </div>

          <form onSubmit={submit} className="space-y-4">
            <input aria-label="Email" data-testid={TID.loginEmail} type="email" required placeholder="you@campus.edu" value={email} onChange={e => setEmail(e.target.value)} className={INPUT_CLASS} style={INPUT_STYLE} />
            <input aria-label="Password" data-testid={TID.loginPassword} type="password" required placeholder="password" value={password} onChange={e => setPassword(e.target.value)} className={INPUT_CLASS} style={INPUT_STYLE} />
            <Button type="submit" data-testid={TID.loginSubmit} disabled={loading} className="w-full">
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <div className="mt-4 text-center" style={{ fontSize: 14 }}>
            <Link to="/forgot-password" data-testid="forgot-password-link" className="hover:underline" style={{ color: "rgba(11,42,48,0.7)" }}>Forgot password?</Link>
          </div>

          <div className="mt-6 text-center" style={{ fontSize: 14, color: "rgba(11,42,48,0.7)" }}>
            New here? <Link to="/signup" className="font-semibold hover:underline" style={{ color: "var(--pm-teal-deep)" }}>Create an account</Link>
          </div>
        </div>
      </PageShell>
    </div>
  );
}
