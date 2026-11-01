import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import Footer from "../components/Footer";
import CompanyCard from "../components/CompanyCard";
import { SectionLabel, PageTitle } from "../components/shared";
import { TID } from "../testIds";

export default function DepartmentCompanies() {
  const { departmentId } = useParams();
  const navigate = useNavigate();
  const [department, setDepartment] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(false);
    api.get(`/departments/${departmentId}/companies`)
      .then(r => {
        setDepartment(r.data.department);
        setCompanies(r.data.companies || []);
        setLoaded(true);
      })
      .catch(() => {
        toast.error("Department not found");
        navigate("/", { replace: true });
      });
  }, [departmentId, navigate]);

  // Companies carry a "group" label (e.g. "Group 1: IT Services & Mass
  // Recruiters"). Bucket them by that label, preserving first-seen order,
  // so a department heading naturally splits into multiple group sections
  // if a second group is ever added -- no change needed here for that.
  const groups = useMemo(() => {
    const order = [];
    const byGroup = new Map();
    for (const c of companies) {
      const label = c.group || "Other";
      if (!byGroup.has(label)) {
        byGroup.set(label, []);
        order.push(label);
      }
      byGroup.get(label).push(c);
    }
    return order.map(label => ({ label, companies: byGroup.get(label) }));
  }, [companies]);

  // Running counter across ALL groups (not reset per group) so
  // CompanyCard's header-tint cycle (index.css) reflects the cards'
  // actual visual order top-to-bottom on the page -- recomputed fresh
  // each render, never stored, so it's safe as a plain local variable.
  let cardIndex = 0;

  return (
    // `glass-landing` (pinned data-theme="light", matching Header's own
    // pin -- no page supports real dark mode yet) scopes this page's own
    // root to the glass design system; its base rule's opaque `--gl-bg`
    // background does the same job the old pm-cream override did (hides
    // the shared html/body teal gradient + grid overlay wherever this div
    // covers), without needing a one-off color here.
    <div className="glass-landing min-h-screen" data-theme="light">
      <Header light />
      <section className="max-w-7xl mx-auto px-6 lg:px-10 pt-16 pb-24">
        <div className="mb-8">
          <SectionLabel>department</SectionLabel>
          <PageTitle as="h1">
            {department ? department.name : "Loading…"}
          </PageTitle>
        </div>

        {loaded && companies.length === 0 && (
          <div className="gl-card p-8 text-center" style={{ color: "var(--gl-muted)" }}>
            No companies yet for this department. Check back soon.
          </div>
        )}

        {groups.map(g => (
          <div key={g.label} className="mb-10 last:mb-0">
            <h2
              className="font-semibold"
              style={{ color: "var(--gl-text)", fontSize: 22, marginTop: 40, marginBottom: 20 }}
            >
              {g.label}
            </h2>
            <div data-testid={TID.companyGrid} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 items-stretch">
              {g.companies.map(c => <CompanyCard key={c.id} company={c} index={cardIndex++} />)}
            </div>
          </div>
        ))}
      </section>
      <Footer />
    </div>
  );
}
