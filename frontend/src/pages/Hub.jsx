import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { TID } from "../testIds";
import { parseErrorDetail } from "../lib/apiError";
import { TIER_NAMES, TCS_TRACK_NAMES } from "../lib/tierLabels";
import { TIER_CATALOG } from "../lib/capgeminiTiers";
import { ChevronLeft, Clock, CheckCircle2, Lock, ArrowRight, FileText } from "lucide-react";
import { PageShell, SectionLabel, PageTitle, CardTitle, Card, Chip, Button, Alert, EmptyState } from "../components/shared";

// Body-size meta text (never monospace).
const META = { fontSize: 13, color: "rgba(11,42,48,0.7)" };
const BODY = { fontSize: 15, color: "rgba(11,42,48,0.85)", lineHeight: 1.6 };

const TIER_SOURCE_LABEL = { oa_designated: "based on OA", chosen: "chosen by you" };

// Human-facing text for each /interview/start error code this page can
// receive. `interview_already_in_progress` and a successful start are
// both handled by navigating, not shown here.
function interviewErrorCopy(detail, companyId) {
  switch (detail.code) {
    case "resume_required":
      return { title: "You'll need a resume on file first.", body: "Analyze a resume for this company, then come back to start your interview." };
    case "no_designated_tier":
      return { title: "No cleared OA tier yet.", body: "Pick a tier below to practice with instead -- it doesn't depend on the OA." };
    case "unknown_tier":
      return { title: "That tier isn't available for this company.", body: "Pick one of the tiers listed below." };
    case "interview_not_available":
      return { title: "Interviews for this company aren't available yet.", body: "Check back later." };
    case "invalid_start_body":
      return { title: "Something went wrong starting your interview.", body: "Please try again." };
    default:
      return { title: "Something went wrong starting your interview.", body: detail.message || "Please try again." };
  }
}

function tierDisplayName(tierId) {
  return TIER_NAMES[tierId] || tierId;
}

export default function Hub() {
  const { companyId } = useParams();
  const navigate = useNavigate();

  const [company, setCompany] = useState(null);
  const [listData, setListData] = useState(null); // { interviews, companies }
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const [oaStarting, setOaStarting] = useState(false);
  const [oaInProgressId, setOaInProgressId] = useState(null);
  const [cluster, setCluster] = useState(null);

  const [intvStarting, setIntvStarting] = useState(false);
  const [intvError, setIntvError] = useState(null); // {code, message, ...}
  const [showChooser, setShowChooser] = useState(false);
  const [chosenTier, setChosenTier] = useState(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(false);
    Promise.all([
      api.get(`/companies/${companyId}`),
      api.get("/interview/list"),
    ]).then(([c, list]) => {
      if (!active) return;
      setCompany(c.data);
      setListData(list.data);
    }).catch(() => {
      if (active) setLoadError(true);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [companyId]);

  const companyInterviewInfo = (listData?.companies || []).find(c => c.company_id === companyId)
    || { company_id: companyId, interview_available: true, designated_tier: null };
  const myInterviews = (listData?.interviews || []).filter(i => i.company_id === companyId);
  const inProgressInterview = myInterviews.find(i => i.status === "in_progress");
  const tiers = TIER_CATALOG[companyId] || [];

  const startOA = async () => {
    // Skill-cluster picker (2026-10 fix: this used to live on CompanyDetail's
    // own "Start OA" button, which bypassed the hub entirely -- now that
    // the hub is the only place that actually calls POST /oa/start, the
    // picker has to live here too, for the one company (Wipro) that has
    // cluster_options. Harmless no-op for every other company.
    if (company.cluster_options?.length && !cluster) {
      toast.error("Pick a skill cluster first.");
      return;
    }
    setOaStarting(true);
    try {
      const { data } = await api.post("/oa/start", { company_id: companyId, cluster });
      navigate(`/oa/${data.attempt_id}`);
    } catch (err) {
      const detail = parseErrorDetail(err);
      if (detail.code === "oa_already_in_progress" && detail.attempt_id) {
        setOaInProgressId(detail.attempt_id);
      } else {
        toast.error(detail.message || "Could not start the OA.");
      }
    } finally {
      setOaStarting(false);
    }
  };

  const continueOA = () => {
    if (oaInProgressId) navigate(`/oa/${oaInProgressId}`);
  };

  const startInterview = async (body) => {
    setIntvStarting(true);
    setIntvError(null);
    try {
      const { data } = await api.post("/interview/start", { company_id: companyId, ...body });
      navigate(`/interview/${data.interview_id}`);
    } catch (err) {
      const detail = parseErrorDetail(err);
      if (detail.code === "interview_already_in_progress" && detail.interview_id) {
        navigate(`/interview/${detail.interview_id}`);
        return;
      }
      setIntvError(detail);
      if (detail.code === "no_designated_tier" || detail.code === "unknown_tier") setShowChooser(true);
    } finally {
      setIntvStarting(false);
    }
  };

  const continueInterview = () => {
    if (inProgressInterview) navigate(`/interview/${inProgressInterview.interview_id}`);
  };

  if (loading) {
    return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Loading your hub…</div></PageShell></div>;
  }
  if (loadError || !company) {
    return (
      <div>
        <Header light />
        <PageShell>
          <div className="p-10 text-center">
            <CardTitle style={{ fontSize: 22, marginBottom: 8 }}>Couldn't load this hub.</CardTitle>
            <Button as={Link} to={`/company/${companyId}`}>Back to company page</Button>
          </div>
        </PageShell>
      </div>
    );
  }

  const oaResultChip = (() => {
    if (companyId === "capgemini" && companyInterviewInfo.designated_tier) {
      const tier = companyInterviewInfo.designated_tier;
      return { label: "capgemini tier", title: `${tierDisplayName(tier)} tier` };
    }
    if (companyId === "tcs-nqt" && companyInterviewInfo.designated_tier) {
      const track = companyInterviewInfo.designated_tier;
      return { label: "estimated track (TCS does not publish cutoffs)", title: TCS_TRACK_NAMES[track] || track };
    }
    return null;
  })();

  return (
    <div>
      <Header light />
      <PageShell>
        <Link to={`/company/${companyId}`} className="inline-flex items-center gap-1 mb-6 hover:text-[var(--pm-ink)]" style={{ fontSize: 14, color: "rgba(11,42,48,0.7)" }}>
          <ChevronLeft size={16} /> back to {company.name}
        </Link>
        <SectionLabel>{company.name} · hub</SectionLabel>
        <PageTitle>Your OA and interview, independent of each other.</PageTitle>
        <p className="mt-3" style={BODY}>Take either one first, retake either one as many times as you like. Nothing here is forced into an order.</p>

        <section className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* OA card */}
          <Card data-testid={TID.hubOaCard} padding="28px">
            <SectionLabel>OA round</SectionLabel>
            <CardTitle style={{ fontSize: 22 }}>{company.name} online assessment</CardTitle>
            <p className="mt-2 mb-5" style={BODY}>{company.time_minutes} minutes · {company.sections?.length ?? 0} sections.</p>

            {/* Round breakdown (moved here from CompanyDetail, 2026-10 --
                belongs next to the actual "Start the OA" decision, not on
                the page before it). */}
            {company.sections?.length > 0 && (
              <div className="mb-5 space-y-2">
                {company.sections.map((s, i) => (
                  <div
                    key={s.key}
                    className="rounded-[16px] p-4 flex items-center gap-3"
                    style={{ border: "1.5px solid var(--pm-border-control)", background: "var(--pm-white)" }}
                  >
                    <div className="grid place-items-center shrink-0 font-display font-semibold" style={{ width: 32, height: 32, borderRadius: 10, background: "var(--pm-sky)", color: "var(--pm-ink)", fontSize: 14 }}>{i + 1}</div>
                    <div className="flex-1 min-w-0">
                      <div className="font-display font-semibold" style={{ fontSize: 16, color: "var(--pm-ink)" }}>{s.name}</div>
                      <div className="mt-1" style={META}>
                        {s.type} • {s.count} q • {s.minutes} min • cutoff {Math.round(s.cutoff * 100)}%{s.negative ? " • negative marking" : ""}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {oaResultChip && (
              <div data-testid={TID.hubOaResult} className="mb-5 p-4 rounded-[16px]" style={{ background: "var(--pm-sky)" }}>
                <div className="pm-eyebrow" style={{ fontSize: 11, color: "rgba(11,42,48,0.7)" }}>{oaResultChip.label}</div>
                <div className="font-display font-semibold mt-1" style={{ fontSize: 20, color: "var(--pm-ink)" }}>{oaResultChip.title}</div>
              </div>
            )}

            {oaInProgressId ? (
              <Button data-testid={TID.hubOaContinueBtn} onClick={continueOA} className="w-full">
                Continue your OA <ArrowRight size={14} aria-hidden="true" />
              </Button>
            ) : (
              <>
                {company.cluster_options?.length > 0 && (
                  <div className="mb-4">
                    <SectionLabel>Pick your skill cluster</SectionLabel>
                    <div className="flex gap-2 flex-wrap">
                      {company.cluster_options.map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          data-testid={TID.clusterOption(opt)}
                          aria-pressed={cluster === opt}
                          onClick={() => setCluster(opt)}
                          className="font-display font-semibold rounded-full px-4 py-2 transition-colors focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[var(--pm-teal-night)]"
                          style={cluster === opt
                            ? { fontSize: 15, background: "var(--pm-teal-deep)", color: "var(--pm-white)", border: "1.5px solid var(--pm-teal-deep)" }
                            : { fontSize: 15, background: "transparent", color: "var(--pm-ink)", border: "1.5px solid var(--pm-border-control)" }}
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <Button data-testid={TID.hubOaStartBtn} onClick={startOA} disabled={oaStarting} className="w-full">
                  {oaStarting ? "Starting…" : oaResultChip ? "Retake the OA" : "Start the OA"}
                </Button>
              </>
            )}
          </Card>

          {/* Interview card */}
          <Card data-testid={TID.hubInterviewCard} padding="28px">
            <SectionLabel>Interview round</SectionLabel>
            <CardTitle style={{ fontSize: 22 }}>{company.name} interview</CardTitle>

            {!companyInterviewInfo.interview_available ? (
              <div data-testid={TID.hubInterviewUnavailable} className="mt-4">
                <div className="flex items-center gap-2 mb-2" style={{ color: "rgba(11,42,48,0.6)" }}>
                  <Lock size={16} aria-hidden="true" />
                  <span style={{ fontSize: 15, fontWeight: 600 }}>Coming soon</span>
                </div>
                <p style={BODY}>Interviews for {company.name} aren't available yet.</p>
              </div>
            ) : inProgressInterview ? (
              <div className="mt-4">
                <p className="mb-4" style={BODY}>You have an interview in progress.</p>
                <Button data-testid={TID.hubInterviewContinueBtn} onClick={continueInterview} className="w-full">
                  Continue your interview <ArrowRight size={14} aria-hidden="true" />
                </Button>
              </div>
            ) : (
              <div className="mt-4">
                {companyInterviewInfo.designated_tier && !showChooser && (
                  <>
                    <p className="mb-4" style={BODY}>Your OA cleared a tier -- start the matching interview, or pick a different one to practice with.</p>
                    <Button
                      data-testid={TID.hubInterviewDesignatedBtn}
                      onClick={() => startInterview({ use_designated: true })}
                      disabled={intvStarting}
                      className="w-full"
                    >
                      Start {tierDisplayName(companyInterviewInfo.designated_tier)} interview (based on your OA)
                    </Button>
                    <button
                      data-testid={TID.hubInterviewChooseDifferent}
                      onClick={() => setShowChooser(true)}
                      className="mt-3 underline-offset-2 hover:underline"
                      style={{ fontSize: 14, color: "var(--pm-teal-deep)" }}
                    >
                      Choose a different tier
                    </button>
                  </>
                )}

                {(!companyInterviewInfo.designated_tier || showChooser) && (
                  tiers.length > 0 ? (
                    <TierChooser
                      tiers={tiers}
                      chosen={chosenTier}
                      onChoose={setChosenTier}
                      onStart={() => startInterview({ tier: chosenTier })}
                      starting={intvStarting}
                    />
                  ) : (
                    <div data-testid={TID.hubInterviewNoChooserAvailable}>
                      <p style={BODY}>Practice interviews for {company.name} aren't available from this hub yet.</p>
                      <p className="mt-2" style={META}>Complete an OA for this company, then start the interview from your OA review page.</p>
                    </div>
                  )
                )}
              </div>
            )}

            {intvError && (
              <Alert tone="error" title={interviewErrorCopy(intvError, companyId).title} className="mt-4">
                <span data-testid={TID.hubInterviewError}>{interviewErrorCopy(intvError, companyId).body}</span>
                {intvError.code === "resume_required" && (
                  <div className="mt-2">
                    <Link to={`/company/${companyId}`} className="font-semibold underline-offset-2 hover:underline" style={{ color: "var(--pm-teal-deep)" }}>
                      <FileText size={13} className="inline mr-1" aria-hidden="true" />
                      Submit a resume
                    </Link>
                  </div>
                )}
              </Alert>
            )}
          </Card>
        </section>

        {/* Past interviews */}
        <section className="mt-12">
          <PageTitle as="h2" style={{ fontSize: "clamp(1.5rem, 2.5vw, 2rem)" }}>Past interviews</PageTitle>
          {myInterviews.length === 0 ? (
            <Card className="mt-5" data-testid={TID.hubPastInterviewsEmpty}>
              <EmptyState title="No interviews yet." body="Start one above whenever you're ready." />
            </Card>
          ) : (
            <div className="mt-5 space-y-3" data-testid={TID.hubPastInterviewsList}>
              {myInterviews.map((i) => (
                <Card key={i.interview_id} padding="18px 22px" data-testid={TID.hubPastInterviewRow(i.interview_id)}>
                  <div className="flex items-center justify-between gap-4 flex-wrap">
                    <div>
                      <div className="font-display font-semibold" style={{ fontSize: 17, color: "var(--pm-ink)" }}>
                        {i.tier ? `${tierDisplayName(i.tier)} interview` : "Interview"}
                      </div>
                      <div className="mt-1 flex flex-wrap gap-3" style={META}>
                        {i.tier_source && <span>{TIER_SOURCE_LABEL[i.tier_source] || i.tier_source}</span>}
                        <span>{i.created_at ? new Date(i.created_at).toLocaleString() : ""}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Chip tone={i.status === "completed" ? "status" : "neutral"}>
                        {i.status === "completed" ? <CheckCircle2 size={12} /> : <Clock size={12} />} {i.status}
                      </Chip>
                      <Link to={`/interview/${i.interview_id}/report`} className="font-semibold underline-offset-2 hover:underline whitespace-nowrap" style={{ fontSize: 14, color: "var(--pm-teal-deep)" }}>
                        View report
                      </Link>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </section>
      </PageShell>
    </div>
  );
}

function TierChooser({ tiers, chosen, onChoose, onStart, starting }) {
  return (
    <div data-testid={TID.hubInterviewChooser}>
      <p className="mb-3" style={BODY}>This is practice -- it doesn't depend on your OA result. Pick a tier:</p>
      <div className="space-y-2">
        {tiers.map((t) => (
          <button
            key={t.id}
            type="button"
            data-testid={TID.hubInterviewTierOption(t.id)}
            aria-pressed={chosen === t.id}
            onClick={() => onChoose(t.id)}
            className="w-full text-left rounded-[16px] p-4 transition-colors focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[var(--pm-teal-night)]"
            style={chosen === t.id
              ? { border: "1.5px solid var(--pm-teal-deep)", background: "var(--pm-sky)" }
              : { border: "1.5px solid var(--pm-border-control)", background: "var(--pm-white)" }}
          >
            <div className="font-display font-semibold" style={{ fontSize: 16, color: "var(--pm-ink)" }}>{t.name}</div>
            <div className="mt-1" style={META}>{t.blurb}</div>
          </button>
        ))}
      </div>
      <Button
        data-testid={TID.hubInterviewStartChosenBtn}
        onClick={onStart}
        disabled={!chosen || starting}
        className="w-full mt-4"
      >
        {starting ? "Starting…" : "Start practice interview"}
      </Button>
    </div>
  );
}
