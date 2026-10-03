import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../api";
import { useAuth } from "../auth";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "./ui/dialog";

const YEARS = [2026, 2027, 2028, 2029, 2030];
const ROLES = [
  "Software Engineer",
  "Backend Engineer",
  "Frontend Engineer",
  "Full-Stack Engineer",
  "Data Analyst",
  "Data Scientist",
  "ML Engineer",
  "DevOps / SRE",
  "QA / Test Engineer",
  "Product Analyst",
  "Business Analyst",
  "Consultant (USI)",
];

/**
 * Shown once, right after signup or first sign-in, whenever the user's
 * profile still has an empty `college` field. Persists to /auth/profile.
 */
export default function OnboardingModal() {
  const { user, refresh } = useAuth();
  const [open, setOpen] = useState(false);
  const [college, setCollege] = useState("");
  const [targetRole, setTargetRole] = useState(ROLES[0]);
  const [graduationYear, setGraduationYear] = useState(String(YEARS[0]));
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    // Show only if the user hasn't filled these yet (first-run).
    if (!user.college || !user.graduation_year || !user.target_role) {
      setOpen(true);
      if (user.college) setCollege(user.college);
      if (user.target_role) setTargetRole(user.target_role);
      if (user.graduation_year) setGraduationYear(user.graduation_year);
    }
  }, [user]);

  if (!user) return null;

  const submit = async (e) => {
    e.preventDefault();
    if (!college.trim()) { toast.error("College is required"); return; }
    setSaving(true);
    try {
      await api.patch("/auth/profile", {
        college: college.trim(),
        target_role: targetRole,
        graduation_year: graduationYear,
      });
      toast.success("Profile saved. Let's start prepping.");
      await refresh();
      setOpen(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not save profile");
    } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent data-testid="onboarding-modal" className="sm:max-w-md bg-pm-surface" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle className="font-display text-2xl">Quick: three fields.</DialogTitle>
          <DialogDescription className="text-pm-text2">
            We tailor OA questions and interview follow-ups based on your college batch and target role. Takes 15 seconds.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={submit} className="space-y-4 pt-2">
          <div>
            <label className="text-xs font-mono uppercase text-pm-text2">College</label>
            <input
              data-testid="onboard-college"
              required autoFocus placeholder="e.g. IIT Kharagpur"
              value={college} onChange={e => setCollege(e.target.value)}
              className="pm-input mt-1"
            />
          </div>
          <div>
            <label className="text-xs font-mono uppercase text-pm-text2">Target role</label>
            <select
              data-testid="onboard-role"
              value={targetRole} onChange={e => setTargetRole(e.target.value)}
              className="pm-input mt-1"
            >
              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-mono uppercase text-pm-text2">Graduation year</label>
            <select
              data-testid="onboard-year"
              value={graduationYear} onChange={e => setGraduationYear(e.target.value)}
              className="pm-input mt-1"
            >
              {YEARS.map(y => <option key={y} value={String(y)}>{y}</option>)}
            </select>
          </div>

          <DialogFooter className="pt-2 flex-row gap-2">
            <button type="button" data-testid="onboard-skip" onClick={() => setOpen(false)} className="pm-btn pm-btn-ghost text-sm py-2 px-4 flex-1">
              Skip for now
            </button>
            <button type="submit" data-testid="onboard-save" disabled={saving} className="pm-btn pm-btn-primary text-sm py-2 px-4 flex-1">
              {saving ? "Saving…" : "Save & continue"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
