import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../auth";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;
    const hash = window.location.hash || "";
    const params = new URLSearchParams(hash.replace(/^#/, ""));
    const sessionId = params.get("session_id");
    if (!sessionId) {
      navigate("/login", { replace: true });
      return;
    }
    (async () => {
      try {
        const { data } = await api.post("/auth/google/session", { session_id: sessionId });
        setUser(data.user);
        // Remove hash then navigate to dashboard
        window.history.replaceState({}, document.title, "/dashboard");
        navigate("/dashboard", { replace: true, state: { user: data.user } });
      } catch (e) {
        navigate("/login", { replace: true });
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen grid place-items-center">
      <div className="text-center">
        <div className="w-8 h-8 mx-auto border-2 border-pm-primary border-t-transparent rounded-full animate-spin"></div>
        <div className="mt-4 text-sm text-pm-text2 font-mono">Finishing sign-in…</div>
      </div>
    </div>
  );
}
