import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import { useAuth } from "../auth";
import Header from "../components/Header";
import { TID } from "../testIds";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
function startGoogleLogin() {
  const redirectUrl = window.location.origin + "/dashboard";
  window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
}

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
      <Header />
      <div className="max-w-md mx-auto px-6 py-16">
        <h1 className="font-display text-4xl font-bold mb-2">Welcome back</h1>
        <p className="text-pm-text2 mb-8">Pick up right where you left off.</p>

        <button data-testid={TID.loginGoogle} onClick={startGoogleLogin} className="w-full pm-btn pm-btn-ghost mb-6 py-3">
          <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
          Continue with Google
        </button>

        <div className="flex items-center gap-3 my-4 text-xs text-pm-text2 font-mono uppercase tracking-widest">
          <div className="flex-1 h-px bg-[rgba(10,10,10,0.1)]"></div> or <div className="flex-1 h-px bg-[rgba(10,10,10,0.1)]"></div>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <input data-testid={TID.loginEmail} type="email" required placeholder="you@campus.edu" value={email} onChange={e => setEmail(e.target.value)} className="pm-input" />
          <input data-testid={TID.loginPassword} type="password" required placeholder="password" value={password} onChange={e => setPassword(e.target.value)} className="pm-input" />
          <button data-testid={TID.loginSubmit} disabled={loading} className="w-full pm-btn pm-btn-primary py-3">
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="text-sm text-pm-text2 mt-4 text-center">
          <Link to="/forgot-password" data-testid="forgot-password-link" className="text-pm-text2 hover:text-pm-primary-dark">Forgot password?</Link>
        </div>

        <div className="text-sm text-pm-text2 mt-6 text-center">
          New here? <Link to="/signup" className="text-pm-primary-dark font-semibold">Create an account</Link>
        </div>
      </div>
    </div>
  );
}
