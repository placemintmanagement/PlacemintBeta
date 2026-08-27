import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import Footer from "../components/Footer";
import CompanyCard from "../components/CompanyCard";
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

  return (
    <div className="min-h-screen">
      <Header />
      <section className="max-w-7xl mx-auto px-6 lg:px-10 pt-16 pb-24">
        <div className="mb-8">
          <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-2">department</div>
          <h1 className="font-display font-bold text-3xl lg:text-4xl">
            {department ? department.name : "Loading…"}
          </h1>
        </div>

        {loaded && companies.length === 0 && (
          <div className="pm-card p-8 text-center text-pm-text2">
            No companies yet for this department. Check back soon.
          </div>
        )}

        {groups.map(g => (
          <div key={g.label} className="mb-10 last:mb-0">
            <h2 className="font-display font-bold text-xl mb-4">{g.label}</h2>
            <div data-testid={TID.companyGrid} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {g.companies.map(c => <CompanyCard key={c.id} company={c} />)}
            </div>
          </div>
        ))}
      </section>
      <Footer />
    </div>
  );
}
