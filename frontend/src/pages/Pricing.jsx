import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { useAuth } from "../auth";
import { TID } from "../testIds";

export default function Pricing() {
  const [pricing, setPricing] = useState(null);
  const [busy, setBusy] = useState(null);
  const { user, refresh } = useAuth();

  useEffect(() => { api.get("/pricing").then(r => setPricing(r.data)); }, []);

  const runCheckout = async ({ orderRequest, itemName, itemId, description }) => {
    if (!user) { toast.error("Sign in to purchase"); return; }
    setBusy(itemId);
    try {
      const { data } = await api.post("/payments/order", orderRequest);
      if (data.mock) {
        await api.post("/payments/verify", { order_id: data.order.order_id });
        toast.success(`Mock purchase complete. ${itemName} unlocked.`);
        refresh();
        setBusy(null);
        return;
      }
      const options = {
        key: data.razorpay_key_id,
        amount: data.order.amount,
        currency: "INR",
        name: "Placemint",
        description,
        order_id: data.order.razorpay_order_id,
        prefill: { name: user.name, email: user.email },
        theme: { color: "#0F6F7A" },
        handler: async (resp) => {
          try {
            await api.post("/payments/verify", {
              order_id: data.order.order_id,
              razorpay_order_id: resp.razorpay_order_id,
              razorpay_payment_id: resp.razorpay_payment_id,
              razorpay_signature: resp.razorpay_signature,
            });
            toast.success(`${itemName} unlocked!`);
            refresh();
          } catch (e) {
            toast.error(e.response?.data?.detail || "Payment verify failed");
          } finally { setBusy(null); }
        },
        modal: { ondismiss: () => setBusy(null) },
      };
      // eslint-disable-next-line no-undef
      const rp = new window.Razorpay(options);
      rp.open();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not start checkout");
      setBusy(null);
    }
  };

  const buy = (plan) => {
    if (plan.price === 0) { toast.info("You're already on the free plan."); return; }
    return runCheckout({
      orderRequest: { plan_id: plan.id },
      itemName: plan.name,
      itemId: plan.id,
      description: plan.name,
    });
  };

  const buyCredits = (pack) => runCheckout({
    orderRequest: { credit_pack_id: pack.id },
    itemName: pack.label,
    itemId: pack.id,
    description: `Placemint · ${pack.label}`,
  });

  if (!pricing) return <div><Header /><div className="p-10 text-center">Loading…</div></div>;

  const isFounder = user?.plan === "founder";

  return (
    <div>
      <Header />
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-10 pm-in">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark">pricing</div>
        <h1 className="font-display text-4xl font-bold mt-1">Pick your run bundle.</h1>
        <p className="text-pm-text2 mt-2 max-w-xl">Run limits exist as a circuit breaker, not a marketing gate. Resume checker is free forever.</p>

        {/* What counts as a run */}
        <div className="pm-card p-5 mt-6 flex flex-wrap items-center gap-x-8 gap-y-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-widest text-pm-primary-dark">what counts as 1 run</div>
            <div className="font-display font-bold text-lg">1 company · OA + Interview + Report</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="pm-chip">✓ Full OA (all sections)</span>
            <span className="pm-chip">✓ Adaptive interview</span>
            <span className="pm-chip">✓ Final cross-phase report</span>
            <span className="pm-chip pm-chip-primary">Resume Checker is always free</span>
          </div>
        </div>

        {isFounder && (
          <div className="mt-6 pm-card p-5 flex items-start gap-3 border-pm-primary/40 bg-pm-primary/5">
            <span className="text-2xl">⚡</span>
            <div>
              <div className="font-display font-bold text-pm-primary-dark">You have Founder access.</div>
              <div className="text-sm text-pm-text2">Payment isn't required. Every track and every run is unlocked on your account.</div>
            </div>
          </div>
        )}

        {!pricing.razorpay_enabled && !isFounder && (
          <div className="mt-6 pm-card p-4 pm-chip-coral flex items-start gap-2 text-sm">
            ⚠️ Razorpay keys are placeholders, so checkouts run in <strong>mock mode</strong> and auto-verify. Drop real <code className="font-mono">rzp_test_…</code> keys in <code className="font-mono">backend/.env</code> to enable real Razorpay.
          </div>
        )}

        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {pricing.plans.map(p => {
            const perPeriod = p.id === "basic" || p.id === "pro" ? "/mo" : (p.id === "free" ? "" : " one-time");
            const companies = p.companies === null ? "All 14" : `${p.companies} co`;
            return (
              <div key={p.id} data-testid={TID.pricingPlan(p.id)}
                   className={`pm-card p-6 flex flex-col ${p.highlight ? "border-pm-primary shadow-[0_20px_60px_-30px_rgba(15,174,115,0.5)] scale-[1.02]" : ""}`}>
                {p.tag && <span className={`pm-chip ${p.highlight ? "pm-chip-primary" : ""} self-start mb-3`}>{p.tag}</span>}
                <div className="font-display text-xl font-bold">{p.name}</div>
                <div className="mt-2 font-mono text-3xl font-bold">
                  {p.price === 0 ? "₹0" : <>₹{p.price.toLocaleString("en-IN")}</>}
                  <span className="text-sm font-normal text-pm-text2 ml-1">{perPeriod}</span>
                </div>
                <div className="mt-1 font-mono text-xs text-pm-text2">{companies} • {p.runs} runs</div>
                {p.card_copy && <div className="mt-3 text-sm text-pm-text font-medium">{p.card_copy}</div>}
                <ul className="mt-3 space-y-1.5 text-sm text-pm-text2">
                  {p.features.map((f, i) => <li key={i} className="flex gap-2"><span className="text-pm-primary">✓</span>{f}</li>)}
                </ul>
                {p.contest_boost && (
                  <div className="mt-3 text-[11px] font-mono text-pm-primary-dark border border-pm-primary/30 bg-pm-primary/5 rounded-md p-2">
                    Contest window: 3 full runs on any company through Jul 21, 2026.
                  </div>
                )}
                <button data-testid={TID.pricingSelect(p.id)} onClick={() => buy(p)} disabled={busy === p.id || isFounder}
                        className={`mt-6 pm-btn ${p.highlight ? "pm-btn-primary" : "pm-btn-ghost"} text-sm py-2 ${isFounder ? "opacity-40 cursor-not-allowed" : ""}`}>
                  {isFounder ? "Already unlocked" : (busy === p.id ? "Loading…" : p.cta)}
                </button>
              </div>
            );
          })}
        </div>

        {/* Credit packs — supplement, never replace, plan run caps. */}
        {pricing.credit_packs && pricing.credit_packs.length > 0 && (
          <div className="mt-12">
            <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark">out of runs?</div>
            <h2 className="font-display text-2xl font-bold mt-1">Top up with credits.</h2>
            <p className="text-sm text-pm-text2 mt-1 max-w-2xl">
              One credit = one full 4-phase run on any company. Credits never expire, carry over between billing periods, and stack on top of your plan runs.
            </p>
            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
              {pricing.credit_packs.map(pack => (
                <div key={pack.id} data-testid={`credit-pack-${pack.id}`} className="pm-card p-5 flex flex-col">
                  <div className="font-display font-bold">{pack.label}</div>
                  <div className="mt-1 font-mono text-2xl font-bold">₹{pack.price}
                    <span className="text-xs font-normal text-pm-text2 ml-1">one-time</span>
                  </div>
                  <div className="mt-1 font-mono text-xs text-pm-text2">{pack.credits} run{pack.credits > 1 ? "s" : ""} · never expires</div>
                  <button
                    onClick={() => buyCredits(pack)}
                    disabled={busy === pack.id || isFounder}
                    data-testid={`credit-buy-${pack.id}`}
                    className={`mt-4 pm-btn pm-btn-ghost text-sm py-2 ${isFounder ? "opacity-40 cursor-not-allowed" : ""}`}>
                    {isFounder ? "N/A" : (busy === pack.id ? "Loading…" : `Buy ${pack.label}`)}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
