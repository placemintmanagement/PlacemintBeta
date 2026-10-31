import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../api";
import { useAuth } from "../auth";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "./ui/dialog";
import { Field, Button } from "./shared";

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
      <DialogContent data-testid="onboarding-modal" className="sm:max-w-md" style={{ background: "var(--pm-white)", borderRadius: 24, border: "1px solid rgba(7,59,67,0.08)", boxShadow: "0 14px 28px -18px rgba(7,59,67,0.28)", padding: 28 }} onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle className="font-display font-light" style={{ fontSize: 28, lineHeight: 1.15, letterSpacing: "-0.02em", color: "var(--pm-ink)" }}>Quick: three fields.</DialogTitle>
          <DialogDescription style={{ fontSize: 15, color: "rgba(11,42,48,0.85)" }}>
            We tailor OA questions and interview follow-ups based on your college batch and target role. Takes 15 seconds.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={submit} className="space-y-4 pt-2">
          <Field
            label="College"
            data-testid="onboard-college"
            required autoFocus placeholder="e.g. IIT Kharagpur"
            value={college} onChange={e => setCollege(e.target.value)}
          />
          <Field
            as="select"
            label="Target role"
            data-testid="onboard-role"
            value={targetRole} onChange={e => setTargetRole(e.target.value)}
          >
            {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
          </Field>
          <Field
            as="select"
            label="Graduation year"
            data-testid="onboard-year"
            value={graduationYear} onChange={e => setGraduationYear(e.target.value)}
          >
            {YEARS.map(y => <option key={y} value={String(y)}>{y}</option>)}
          </Field>

          <DialogFooter className="pt-2 flex-row gap-2">
            <Button variant="secondary" data-testid="onboard-skip" onClick={() => setOpen(false)} className="flex-1 !px-4 !py-2" style={{ fontSize: 14 }}>
              Skip for now
            </Button>
            <Button type="submit" data-testid="onboard-save" disabled={saving} className="flex-1 !px-4 !py-2" style={{ fontSize: 14 }}>
              {saving ? "Saving…" : "Save & continue"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
