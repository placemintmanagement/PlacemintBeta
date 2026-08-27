import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/auth";
import OnboardingModal from "@/components/OnboardingModal";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import CompanyDetail from "@/pages/CompanyDetail";
import DepartmentCompanies from "@/pages/DepartmentCompanies";
import OARunner from "@/pages/OARunner";
import OAReview from "@/pages/OAReview";
import ReviewDeck from "@/pages/ReviewDeck";
import Interview from "@/pages/Interview";
import FinalReport from "@/pages/FinalReport";
import Pricing from "@/pages/Pricing";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import VerifyEmail from "@/pages/VerifyEmail";
import { PrivacyPolicy, TermsOfService, RefundPolicy, CookiePolicy, About } from "@/pages/Legal";
import DevChartPreview from "@/pages/DevChartPreview";
import DevGamePreview from "@/pages/DevGamePreview";
import DevSwitchChallengePreview from "@/pages/DevSwitchChallengePreview";
import DevGridChallengePreview from "@/pages/DevGridChallengePreview";
import DevInductiveChallengePreview from "@/pages/DevInductiveChallengePreview";
import DevMotionChallengePreview from "@/pages/DevMotionChallengePreview";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen grid place-items-center text-sm text-pm-text2">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

// Detect OAuth callback in URL hash before rendering normal routes.
function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
      <Route path="/pricing" element={<Pricing />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/legal/privacy" element={<PrivacyPolicy />} />
      <Route path="/legal/terms" element={<TermsOfService />} />
      <Route path="/legal/refund" element={<RefundPolicy />} />
      <Route path="/legal/cookies" element={<CookiePolicy />} />
      <Route path="/legal/about" element={<About />} />
      <Route path="/company/:companyId" element={<CompanyDetail />} />
      <Route path="/departments/:departmentId" element={<DepartmentCompanies />} />
      <Route path="/oa/:attemptId" element={<Protected><OARunner /></Protected>} />
      <Route path="/attempt/:attemptId/review" element={<Protected><OAReview /></Protected>} />
      <Route path="/deck" element={<Protected><ReviewDeck /></Protected>} />
      <Route path="/interview/:interviewId" element={<Protected><Interview /></Protected>} />
      <Route path="/attempt/:attemptId/report" element={<Protected><FinalReport /></Protected>} />
      {/* Standing dev tool — DI chart question visual check, not gated behind auth */}
      <Route path="/dev/chart-preview" element={<DevChartPreview />} />
      {/* Standing dev tool — gamified-round component visual check, not gated behind auth */}
      <Route path="/dev/game-preview" element={<DevGamePreview />} />
      <Route path="/dev/switch-preview" element={<DevSwitchChallengePreview />} />
      <Route path="/dev/grid-challenge-preview" element={<DevGridChallengePreview />} />
      <Route path="/dev/inductive-preview" element={<DevInductiveChallengePreview />} />
      <Route path="/dev/motion-challenge-preview" element={<DevMotionChallengePreview />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRouter />
        <OnboardingModal />
        <Toaster position="top-right" richColors closeButton />
      </BrowserRouter>
    </AuthProvider>
  );
}
