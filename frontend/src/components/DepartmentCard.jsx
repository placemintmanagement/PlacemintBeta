import React from "react";
import { Link } from "react-router-dom";
import { ChevronRight, Clock, Cpu, Radio, Zap, Cog, Building2 } from "lucide-react";
import { TID } from "../testIds";

// Icon per department id. Unknown ids fall back to Building2.
const ICONS = { cse: Cpu, entc: Radio, electronics: Zap, mechanical: Cog, civil: Building2 };

/**
 * Live department (active): the featured card -- white, teal icon
 * tile, lime Explore button, and the student-cs illustration anchored to
 * the bottom edge. Coming-soon department: a dashed, non-interactive card.
 */
export default function DepartmentCard({ department }) {
  const Icon = ICONS[department.id] || Building2;

  if (!department.active) {
    return (
      <div
        data-testid={TID.departmentCard(department.id)}
        className="flex flex-col gap-4 p-6 rounded-[24px] cursor-default select-none pointer-events-none"
        style={{
          background: "rgba(255,255,255,0.6)",
          border: "1px dashed rgba(7,59,67,0.25)",
          boxShadow: "none",
        }}
        aria-disabled="true"
      >
        <div className="flex items-center justify-between gap-3">
          <div className="w-10 h-10 rounded-[12px] grid place-items-center shrink-0" style={{ background: "#F2EDDF" }}>
            <Icon size={20} style={{ color: "rgba(15,111,122,0.7)" }} aria-hidden="true" />
          </div>
          <span
            className="inline-flex items-center gap-1 rounded-full whitespace-nowrap"
            style={{ background: "#F2EDDF", color: "#0B2A30", fontSize: 12, fontWeight: 600, padding: "4px 10px" }}
          >
            <Clock size={14} style={{ color: "#0F6F7A" }} aria-hidden="true" />
            Coming Soon
          </span>
        </div>
        <div>
          <div className="font-display font-semibold" style={{ fontSize: 20, lineHeight: 1.25, color: "rgba(11,42,48,0.85)" }}>{department.name}</div>
          <div className="mt-1" style={{ fontSize: 14, color: "rgba(11,42,48,0.7)" }}>No tracks published yet</div>
        </div>
      </div>
    );
  }

  return (
    <Link
      to={`/departments/${department.id}`}
      data-testid={TID.departmentCard(department.id)}
      className="group pm-dept-featured relative flex flex-col h-full overflow-hidden rounded-[24px] focus:outline-none"
      style={{
        background: "#FFFFFF",
        border: "1px solid rgba(7,59,67,0.14)",
        paddingTop: 32,
        paddingLeft: 32,
        paddingRight: 32,
        paddingBottom: 0,
      }}
    >
      <div className="w-12 h-12 rounded-[14px] grid place-items-center shrink-0" style={{ background: "var(--pm-teal-deep)", color: "#FFFFFF" }}>
        <Icon size={24} aria-hidden="true" />
      </div>
      <div className="mt-6">
        <div className="font-display font-semibold" style={{ fontSize: 28, lineHeight: 1.2, color: "#0B2A30" }}>{department.name}</div>
        <div className="mt-2" style={{ fontSize: 16, lineHeight: 1.5, color: "rgba(11,42,48,0.75)" }}>Browse supported company tracks</div>
      </div>
      <div className="mt-6">
        {/* The Link is the focusable element; the ring shows on this pill. */}
        <span
          className="inline-flex items-center gap-1.5 rounded-full font-display font-semibold group-focus-visible:outline group-focus-visible:outline-[3px] group-focus-visible:outline-offset-2 group-focus-visible:outline-[var(--pm-teal-night)]"
          style={{ minHeight: 44, padding: "10px 20px", background: "var(--pm-lime)", color: "#0B2A30", fontSize: 15 }}
        >
          Explore <ChevronRight size={14} aria-hidden="true" />
        </span>
      </div>
      <img
        src="/illustrations/student-cs.svg"
        alt=""
        width={1510}
        height={942}
        loading="lazy"
        className="mt-auto mx-auto block h-auto object-contain"
        style={{ width: "min(70%, 280px)", maxHeight: 200 }}
      />
    </Link>
  );
}
