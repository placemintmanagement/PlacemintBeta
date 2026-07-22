import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "./api";

const AuthCtx = createContext({ user: null, loading: true, refresh: () => {}, logout: () => {} });

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // If returning from OAuth callback, skip the /me check so AuthCallback can process first.
    if (window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem("pm_token");
    setUser(null);
  }, []);

  return <AuthCtx.Provider value={{ user, loading, refresh, logout, setUser }}>{children}</AuthCtx.Provider>;
}

export function useAuth() { return useContext(AuthCtx); }
