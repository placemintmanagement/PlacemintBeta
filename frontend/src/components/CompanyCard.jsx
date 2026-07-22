import React from "react";
import { Link } from "react-router-dom";
import { Clock, ChevronRight, TriangleAlert } from "lucide-react";
import { TID } from "../testIds";

export default function CompanyCard({ company }) {
  const unverified = !company.verified && !company.generic;
  const generic = !!company.generic;
  return (
    <div
      data-testid={TID.companyCard(company.id)}
      className={`pm-card p-6 flex flex-col gap-4 relative ${unverified ? "pm-card-unverified" : ""}`}
    >
      {unverified && (
        <div className="absolute -top-2 -right-2 pm-chip pm-chip-coral flex items-center gap-1">
          <TriangleAlert size={12} /> not confirmed
        </div>
      )}
      {generic && (
        <div className="absolute -top-2 -right-2 pm-chip pm-chip-primary flex items-center gap-1">
          <TriangleAlert size={12} /> general practice
        </div>
      )}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-display text-lg font-bold leading-tight">{company.name}</div>
          <div className="text-sm text-pm-text2 mt-1">{company.tagline}</div>
        </div>
        <span className="pm-chip pm-chip-primary whitespace-nowrap">
          <Clock size={12} /> {company.time_minutes}m
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {(company.chips || []).map((c, i) => (
          <span key={i} className="pm-chip">{c}</span>
        ))}
      </div>

      <div className="flex items-center gap-1 text-xs text-pm-text2 font-mono">
        <span>{company.sections?.length ?? 0} sections</span>
        <span>•</span>
        <span>{company.scoring_mode === "sectional" ? "sectional cutoffs" : "composite score"}</span>
      </div>

      <div className="mt-auto pt-2 flex items-center justify-between">
        <span className="text-xs text-pm-text2 font-mono uppercase tracking-wider">{company.id}</span>
        <Link
          to={`/company/${company.id}`}
          data-testid={TID.companyStartBtn(company.id)}
          className="pm-btn pm-btn-primary text-sm py-2 px-4"
        >
          Start <ChevronRight size={14} />
        </Link>
      </div>
    </div>
  );
}
