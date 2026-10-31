import React from "react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import { useAuth } from "../auth";
import { PageShell, PageTitle, Button } from "../components/shared";

// Catch-all for paths that match no route. Signed-in users go back to the
// dashboard; everyone else goes to the landing page. No illustration: none
// in public/illustrations fits a missing page.
export default function NotFound() {
  const { user } = useAuth();
  const home = user ? "/dashboard" : "/";
  return (
    <div>
      <Header light />
      <PageShell>
        <div className="max-w-md mx-auto py-24 text-center">
          <PageTitle as="h1" style={{ fontSize: "clamp(2.25rem, 5vw, 3.5rem)" }}>Page not found.</PageTitle>
          <p className="mt-4" style={{ fontSize: 16, color: "rgba(11,42,48,0.85)", lineHeight: 1.6 }}>The link may be out of date, or the page may have moved.</p>
          <div className="mt-8 flex justify-center">
            <Button as={Link} to={home}>{user ? "Back to dashboard" : "Back to home"}</Button>
          </div>
        </div>
      </PageShell>
    </div>
  );
}
