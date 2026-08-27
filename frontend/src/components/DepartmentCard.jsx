import React from "react";
import { Link } from "react-router-dom";
import { ChevronRight, Clock } from "lucide-react";
import { TID } from "../testIds";

export default function DepartmentCard({ department }) {
  if (!department.active) {
    return (
      <div
        data-testid={TID.departmentCard(department.id)}
        className="pm-card p-6 flex flex-col gap-4 relative opacity-50 cursor-default select-none pointer-events-none"
        aria-disabled="true"
      >
        <div className="absolute -top-2 -right-2 pm-chip pm-chip-coral flex items-center gap-1">
          <Clock size={12} /> Coming Soon
        </div>
        <div>
          <div className="font-display text-lg font-bold leading-tight">{department.name}</div>
          <div className="text-sm text-pm-text2 mt-1">No tracks published yet</div>
        </div>
      </div>
    );
  }

  return (
    <Link
      to={`/departments/${department.id}`}
      data-testid={TID.departmentCard(department.id)}
      className="pm-card p-6 flex flex-col gap-4 relative"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-display text-lg font-bold leading-tight">{department.name}</div>
          <div className="text-sm text-pm-text2 mt-1">Browse supported company tracks</div>
        </div>
      </div>
      <div className="mt-auto pt-2 flex items-center justify-end">
        <span className="pm-btn pm-btn-primary text-sm py-2 px-4">
          Explore <ChevronRight size={14} />
        </span>
      </div>
    </Link>
  );
}
