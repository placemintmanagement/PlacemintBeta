import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, Clock, Laptop, Radio, Zap, Cog, Building2 } from "lucide-react";
import api from "../../api";
import { TID } from "../../testIds";

// Same icon-per-department-id map as components/DepartmentCard.jsx (teal
// design) -- real department ids from the live /departments API, not
// placeholder data.
const ICONS = { cse: Laptop, entc: Radio, electronics: Zap, mechanical: Cog, civil: Building2 };
const PALETTE = ["--gl-blue", "--gl-mint", "--gl-pink", "--gl-sand", "--gl-y"];
// Vivid icon-foreground hexes, paired by index with PALETTE's pastel
// background tints -- same reason as GlassWhatYouGet/GlassIdeSection's `ic`
// fields: the pastel tokens read as dull when used as an icon foreground.
const ICON_COLORS = ["#2563eb", "#0d9488", "#db2777", "#ca8a04", "#ea580c"];

function DeptCard({ department, i }) {
  const Icon = ICONS[department.id] || Building2;
  const tc = `var(${PALETTE[i % PALETTE.length]})`;
  const ic = ICON_COLORS[i % ICON_COLORS.length];

  if (!department.active) {
    return (
      <div data-testid={TID.departmentCard(department.id)} className="gl-dept-soon" style={{ "--tc": tc }} aria-disabled="true">
        <div className="gl-dept-soon-in">
          <div className="gl-dept-soon-top">
            <span className="gl-dept-icon" style={{ "--tc": tc, "--ic": ic }}><Icon size={20} /></span>
            <span className="gl-dept-pill"><Clock size={13} aria-hidden="true" />Coming Soon</span>
          </div>
          <b>{department.name}</b>
          <p>No tracks published yet</p>
        </div>
      </div>
    );
  }

  return (
    <Link to={`/departments/${department.id}`} data-testid={TID.departmentCard(department.id)} className="gl-dept-featured">
      <div className="gl-dept-featured-in">
        <span className="gl-dept-icon lg" style={{ "--tc": tc, "--ic": ic }}><Icon size={26} /></span>
        <b>{department.name}</b>
        <p>Browse supported company tracks</p>
        <span className="gl-btn y" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          Explore <ChevronRight size={14} aria-hidden="true" />
        </span>
      </div>
    </Link>
  );
}

/**
 * "Pick your branch, then your track." -- ported from the main app's
 * DepartmentCard.jsx/Landing.jsx (teal design) into this design system's
 * own tokens (--gl-* tile tints, gl-chip's dashed-card convention for
 * the "coming soon" cards) instead of the teal/lime palette. Fetches the
 * same live /departments API -- real backend data, not a hardcoded list.
 */
export default function GlassDepartments() {
  const [departments, setDepartments] = useState([]);

  useEffect(() => {
    api.get("/departments").then((r) => setDepartments(r.data.departments)).catch(() => {});
  }, []);

  if (!departments.length) return null;

  const active = departments.filter((d) => d.active);
  const soon = departments.filter((d) => !d.active);

  return (
    <section className="gl-sec gl-sec-wide">
      <span className="gl-bdg" style={{ marginBottom: 10 }}>{departments.length} engineering departments</span>
      <h2 className="gl-h2">
        Pick your <b>branch</b>, then your track.
      </h2>
      <p className="gl-sub" style={{ marginBottom: 36 }}>Start your prep now.</p>

      <div className="gl-dept-grid" data-testid={TID.departmentGrid}>
        <div className="gl-dept-featured-col">
          {active.map((d, i) => <DeptCard key={d.id} department={d} i={i} />)}
        </div>
        <div className="gl-dept-soon-grid">
          {soon.map((d, i) => <DeptCard key={d.id} department={d} i={i + active.length} />)}
        </div>
      </div>
    </section>
  );
}
