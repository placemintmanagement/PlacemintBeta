import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../auth";
import { PageShell } from "../components/shared";

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

  // Visual only: cream shell and the shared spinner colour. Logic unchanged.
  return (
    <PageShell section={false} className="grid place-items-center">
      <div className="text-center">
        <div className="w-9 h-9 mx-auto rounded-full animate-spin" style={{ border: "2px solid var(--pm-teal-deep)", borderTopColor: "transparent" }}></div>
        <div className="mt-4" style={{ fontSize: 15, color: "rgba(11,42,48,0.7)" }}>Finishing sign-in…</div>
      </div>
    </PageShell>
  );
}
