import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { useAuth } from "../auth";
import { TID } from "../testIds";
import { PageShell, SectionLabel, PageTitle, CardTitle, Card, Chip, Button } from "../components/shared";

// Body-size meta text (never monospace).
const META = { fontSize: 13, color: "rgba(11,42,48,0.7)" };
const BODY = { fontSize: 15, color: "rgba(11,42,48,0.85)", lineHeight: 1.6 };

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
        theme: { color: "#0F6F7A" }, // Razorpay widget config: needs a literal colour, not a CSS variable
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

  if (!pricing) return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Loading…</div></PageShell></div>;

  const isFounder = user?.plan === "founder";

  return (
    <div>
      <Header light />
      <PageShell>
        <div className="pm-in">
          <SectionLabel>pricing</SectionLabel>
          <PageTitle>Pick your run bundle.</PageTitle>
          <p className="mt-3 max-w-xl" style={BODY}>Run limits exist as a circuit breaker, not a marketing gate. Resume checker is free forever.</p>

          {/* What counts as a run */}
          <Card className="mt-6" padding="20px 24px">
            <div className="flex flex-wrap items-center gap-x-8 gap-y-4">
              <div>
                <SectionLabel className="!mb-1">what counts as 1 run</SectionLabel>
                <CardTitle style={{ fontSize: 18 }}>1 company · OA + Interview + Report</CardTitle>
              </div>
              <div className="flex flex-wrap gap-2">
                <Chip>✓ Full OA (all sections)</Chip>
                <Chip>✓ Adaptive interview</Chip>
                <Chip>✓ Final cross-phase report</Chip>
                <Chip tone="status">Resume Checker is always free</Chip>
              </div>
            </div>
          </Card>

          {isFounder && (
            <Card className="mt-6" padding="20px 24px" style={{ background: "var(--pm-success-bg)" }}>
              <div className="flex items-start gap-3">
                <span className="text-2xl" aria-hidden="true">⚡</span>
                <div>
                  <CardTitle style={{ fontSize: 18, color: "var(--pm-teal-deep)" }}>You have Founder access.</CardTitle>
                  <div style={BODY}>Payment isn't required. Every track and every run is unlocked on your account.</div>
                </div>
              </div>
            </Card>
          )}

          {!pricing.razorpay_enabled && !isFounder && (
            <Card className="mt-6" padding="16px 20px" style={{ background: "var(--pm-warning-bg)" }}>
              <div className="flex items-start gap-2" style={{ fontSize: 14, color: "var(--pm-ink)", lineHeight: 1.6 }}>
                <span aria-hidden="true">⚠️</span>
                <span>Razorpay keys are placeholders, so checkouts run in <strong>mock mode</strong> and auto-verify. Drop real <code className="font-mono">rzp_test_…</code> keys in <code className="font-mono">backend/.env</code> to enable real Razorpay.</span>
              </div>
            </Card>
          )}

          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {pricing.plans.map(p => {
              const perPeriod = p.id === "basic" || p.id === "pro" ? "/mo" : (p.id === "free" ? "" : " one-time");
              const companies = p.companies === null ? "All 14" : `${p.companies} co`;
              return (
                <Card key={p.id} data-testid={TID.pricingPlan(p.id)}
                      className="flex flex-col"
                      style={p.highlight ? { border: "1.5px solid var(--pm-teal-deep)", boxShadow: "0 20px 44px -26px rgba(15,111,122,0.55)" } : undefined}>
                  {p.tag && <Chip tone={p.highlight ? "status" : "neutral"} className="self-start mb-3">{p.tag}</Chip>}
                  <CardTitle>{p.name}</CardTitle>
                  <div className="mt-2 font-display font-semibold" style={{ fontSize: 32, color: "var(--pm-ink)", fontVariantNumeric: "tabular-nums" }}>
                    {p.price === 0 ? "₹0" : <>₹{p.price.toLocaleString("en-IN")}</>}
                    <span style={{ fontSize: 14, fontWeight: 400, color: "rgba(11,42,48,0.7)", marginLeft: 4 }}>{perPeriod}</span>
                  </div>
                  <div className="mt-1" style={META}>{companies} • {p.runs} runs</div>
                  {p.card_copy && <div className="mt-3 font-medium" style={{ fontSize: 15, color: "var(--pm-ink)" }}>{p.card_copy}</div>}
                  <ul className="mt-3 space-y-1.5" style={{ fontSize: 14, color: "rgba(11,42,48,0.85)" }}>
                    {p.features.map((f, i) => <li key={i} className="flex gap-2"><span style={{ color: "var(--pm-teal-deep)", fontWeight: 600 }} aria-hidden="true">✓</span>{f}</li>)}
                  </ul>
                  {p.contest_boost && (
                    <div className="mt-3 rounded-[12px] p-3" style={{ fontSize: 13, color: "var(--pm-ink)", background: "var(--pm-sky)" }}>
                      Contest window: 3 full runs on any company through Jul 21, 2026.
                    </div>
                  )}
                  <div className="mt-auto pt-6">
                    <Button
                      variant={p.highlight ? "primary" : "secondary"}
                      data-testid={TID.pricingSelect(p.id)}
                      onClick={() => buy(p)}
                      disabled={busy === p.id || isFounder}
                      className="w-full !py-2.5"
                      style={{ fontSize: 14 }}>
                      {isFounder ? "Already unlocked" : (busy === p.id ? "Loading…" : p.cta)}
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>

          {/* Credit packs — supplement, never replace, plan run caps. */}
          {pricing.credit_packs && pricing.credit_packs.length > 0 && (
            <div className="mt-14">
              <SectionLabel>out of runs?</SectionLabel>
              <PageTitle as="h2">Top up with credits.</PageTitle>
              <p className="mt-2 max-w-2xl" style={BODY}>
                One credit = one full 4-phase run on any company. Credits never expire, carry over between billing periods, and stack on top of your plan runs.
              </p>
              <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
                {pricing.credit_packs.map(pack => (
                  <Card key={pack.id} data-testid={`credit-pack-${pack.id}`} className="flex flex-col">
                    <CardTitle>{pack.label}</CardTitle>
                    <div className="mt-1 font-display font-semibold" style={{ fontSize: 28, color: "var(--pm-ink)", fontVariantNumeric: "tabular-nums" }}>₹{pack.price}
                      <span style={{ fontSize: 13, fontWeight: 400, color: "rgba(11,42,48,0.7)", marginLeft: 4 }}>one-time</span>
                    </div>
                    <div className="mt-1" style={META}>{pack.credits} run{pack.credits > 1 ? "s" : ""} · never expires</div>
                    <div className="mt-auto pt-4">
                      <Button
                        variant="secondary"
                        onClick={() => buyCredits(pack)}
                        disabled={busy === pack.id || isFounder}
                        data-testid={`credit-buy-${pack.id}`}
                        className="w-full !py-2.5"
                        style={{ fontSize: 14 }}>
                        {isFounder ? "N/A" : (busy === pack.id ? "Loading…" : `Buy ${pack.label}`)}
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      </PageShell>
    </div>
  );
}
