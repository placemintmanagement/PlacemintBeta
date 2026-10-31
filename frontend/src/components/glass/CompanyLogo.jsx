import React from "react";
import { SiTcs, SiInfosys, SiWipro, SiAccenture, SiHcl, SiZoho } from "react-icons/si";
import { monogram } from "../../data/companies";

// Only companies with a VERIFIED-correct brand icon actually present in
// the installed react-icons/simple-icons set -- checked directly against
// Object.keys(require('react-icons/si')), not assumed. Several of
// backend/companies.py's own `logo` field values (SiMicrosoft, SiIbm,
// SiCapgemini, SiCognizant) don't exist in this icon set at all (Simple
// Icons has historically dropped marks under trademark pressure), and
// "tech-mahindra" was mapped to SiTeamviewer -- an unrelated company's
// logo. Rather than carry those over or guess a close-enough substitute
// (e.g. the Mahindra Group logo for Tech Mahindra, a different company),
// anything without a confirmed-correct match falls back to the existing
// text monogram.
const ICONS = {
  "tcs-nqt": SiTcs,
  infosys: SiInfosys,
  wipro: SiWipro,
  accenture: SiAccenture,
  hcltech: SiHcl,
  zoho: SiZoho,
};

export default function CompanyLogo({ id, name, size = 20, className = "" }) {
  const Icon = ICONS[id];

  if (!Icon) {
    return <span className={`gl-cl-fallback ${className}`} style={{ width: size, height: size }}>{monogram(name)}</span>;
  }

  return <Icon className={`gl-cl ${className}`} size={size} aria-hidden="true" />;
}
