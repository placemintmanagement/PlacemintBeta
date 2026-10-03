import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { CheckCircle2, XCircle, Trash2, RotateCw, Sparkles, ArrowRight, Filter } from "lucide-react";
import { PageShell, SectionLabel, PageTitle, Card, Chip, Button } from "../components/shared";

// Body-size meta text (never monospace).
const META = { fontSize: 13, color: "rgba(11,42,48,0.7)" };
const BODY = { fontSize: 15, color: "rgba(11,42,48,0.85)", lineHeight: 1.6 };
const FILTER_ON = { border: "1.5px solid var(--pm-teal-deep)", background: "rgba(15,111,122,0.08)", color: "var(--pm-teal-deep)" };
const FILTER_OFF = { border: "1.5px solid var(--pm-border-control)", background: "var(--pm-white)", color: "rgba(11,42,48,0.85)" };

// Local shuffle so users don't just memorize option position.
function useShuffled(options, correctIndex, seed) {
  return useMemo(() => {
    if (!Array.isArray(options)) return { opts: [], correct: -1 };
    const paired = options.map((o, i) => ({ text: o, wasCorrect: i === correctIndex }));
    // Fisher-Yates with a stable per-card seed
    let s = seed;
    const rnd = () => {
      s = (s * 9301 + 49297) % 233280;
      return s / 233280;
    };
    for (let i = paired.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [paired[i], paired[j]] = [paired[j], paired[i]];
    }
    return {
      opts: paired.map(p => p.text),
      correct: paired.findIndex(p => p.wasCorrect),
    };
  }, [options, correctIndex, seed]);
}

export default function ReviewDeck() {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("unmastered"); // "unmastered" | "all"
  const [cursor, setCursor] = useState(0);
  const [chosen, setChosen] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const [lastResult, setLastResult] = useState(null); // { correct, mastered }
  const [seed, setSeed] = useState(1);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get(filter === "unmastered" ? "/deck?unmastered=1" : "/deck");
      setCards(data.cards || []);
      setCursor(0);
      setChosen(null);
      setRevealed(false);
      setLastResult(null);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't load deck");
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [filter]);

  const card = cards[cursor];
  const shuffled = useShuffled(card?.options, card?.correct_index, seed + cursor);

  const submit = async () => {
    if (chosen === null || !card) return;
    // Translate shuffled index back to original correct_index by comparing text
    const chosenText = shuffled.opts[chosen];
    const originalIndex = (card.options || []).indexOf(chosenText);
    try {
      const { data } = await api.post(`/deck/${card.card_id}/attempt`, { chosen_index: originalIndex });
      setLastResult({ correct: data.correct, mastered: data.mastered });
      setRevealed(true);
      if (data.correct) toast.success(data.mastered ? "Mastered, nice!" : "Correct");
      else toast.error("Not quite. Check the explanation");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't record answer");
    }
  };

  const next = () => {
    setChosen(null);
    setRevealed(false);
    setLastResult(null);
    if (cursor + 1 >= cards.length) {
      // Reload with same filter to pick up any cards that unmastered
      load();
    } else {
      setCursor(c => c + 1);
    }
  };

  const remove = async () => {
    if (!card) return;
    try {
      await api.delete(`/deck/${card.card_id}`);
      toast.success("Removed from deck");
      const rest = cards.filter(c => c.card_id !== card.card_id);
      setCards(rest);
      setChosen(null);
      setRevealed(false);
      setLastResult(null);
      if (cursor >= rest.length) setCursor(Math.max(0, rest.length - 1));
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't remove");
    }
  };

  if (loading) {
    return <div><Header light /><PageShell><div className="p-10 text-center" style={BODY}>Loading your deck…</div></PageShell></div>;
  }

  return (
    <div>
      <Header light />
      <PageShell>
        <div className="max-w-3xl mx-auto pm-in">
          <SectionLabel>Review deck</SectionLabel>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <PageTitle>
                {cards.length === 0 ? "Nothing to review yet." : "Drill your misses."}
              </PageTitle>
              <p className="mt-3" style={BODY}>
                {cards.length === 0
                  ? "Finish an OA and hit 'Save to review deck' on any question you got wrong. They'll show up here."
                  : "Two correct answers in a row master a card. Mastered cards drop out of your queue."}
              </p>
            </div>
            {cards.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <Filter size={14} style={{ color: "rgba(11,42,48,0.7)" }} aria-hidden="true"/>
                <button
                  onClick={() => setFilter("unmastered")}
                  data-testid="deck-filter-unmastered"
                  aria-pressed={filter === "unmastered"}
                  className="px-3 py-1.5 rounded-full font-semibold transition-colors focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[var(--pm-teal-night)]"
                  style={{ fontSize: 14, ...(filter === "unmastered" ? FILTER_ON : FILTER_OFF) }}>Unmastered</button>
                <button
                  onClick={() => setFilter("all")}
                  data-testid="deck-filter-all"
                  aria-pressed={filter === "all"}
                  className="px-3 py-1.5 rounded-full font-semibold transition-colors focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[var(--pm-teal-night)]"
                  style={{ fontSize: 14, ...(filter === "all" ? FILTER_ON : FILTER_OFF) }}>All</button>
              </div>
            )}
          </div>

          {cards.length === 0 ? (
            <Card className="mt-10" style={{ textAlign: "center" }}>
              <div className="flex flex-col items-center">
                <Sparkles style={{ color: "var(--pm-teal-deep)" }} size={28} aria-hidden="true"/>
                <div className="mt-3 font-display font-semibold" style={{ fontSize: 22, color: "var(--pm-ink)" }}>Your review deck is empty.</div>
                <div className="mt-5">
                  <Button as={Link} to="/dashboard" className="!py-2 !px-4" style={{ fontSize: 14 }}>Back to dashboard <ArrowRight size={14} aria-hidden="true"/></Button>
                </div>
              </div>
            </Card>
          ) : (
            <>
              {/* Progress strip */}
              <div className="mt-6 flex items-center justify-between gap-4 flex-wrap" style={META}>
                <div>Card {cursor + 1} of {cards.length}</div>
                <div>{card?.company_name} · {card?.section_name}</div>
              </div>

              {/* Card */}
              <Card className="mt-3" data-testid="deck-card">
                <div className="flex items-center gap-2 flex-wrap mb-3" style={META}>
                  <Chip>{card?.difficulty || "Medium"}</Chip>
                  {card?.mastered && <Chip tone="status">mastered</Chip>}
                  {(card?.attempts || []).length > 0 && !card?.mastered && (
                    <span>{(card.attempts || []).filter(a => a.correct).length}/{(card.attempts || []).length} correct so far</span>
                  )}
                </div>
                <div className="whitespace-pre-wrap" style={{ fontSize: 17, color: "var(--pm-ink)", lineHeight: 1.5 }}>{card?.prompt}</div>

                <div className="mt-5 space-y-2">
                  {shuffled.opts.map((opt, i) => {
                    const isChosen = chosen === i;
                    const isCorrect = revealed && i === shuffled.correct;
                    const isWrongPick = revealed && isChosen && i !== shuffled.correct;
                    let style = { border: "1px solid rgba(7,59,67,0.12)", background: "var(--pm-white)" };
                    if (isChosen && !revealed) style = { border: "1.5px solid var(--pm-teal-deep)", background: "rgba(15,111,122,0.08)" };
                    if (isCorrect) style = { border: "1.5px solid var(--pm-teal-deep)", background: "var(--pm-success-bg)" };
                    if (isWrongPick) style = { border: "1.5px solid rgba(11,42,48,0.55)", background: "var(--pm-grey)" };
                    return (
                      <button
                        key={i}
                        onClick={() => !revealed && setChosen(i)}
                        disabled={revealed}
                        aria-pressed={isChosen}
                        data-testid={`deck-option-${i}`}
                        className="w-full text-left px-4 py-3 rounded-[14px] flex items-start gap-3 transition-colors hover:bg-[rgba(15,111,122,0.06)] focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[var(--pm-teal-night)]"
                        style={{ fontSize: 15, color: "var(--pm-ink)", ...style }}>
                        <span className="shrink-0 mt-0.5 font-semibold" style={{ fontSize: 13, color: "rgba(11,42,48,0.7)" }}>{String.fromCharCode(65 + i)}</span>
                        <span className="flex-1 min-w-0 whitespace-pre-wrap">{opt}</span>
                        {isCorrect && <CheckCircle2 size={16} className="shrink-0 mt-0.5" style={{ color: "var(--pm-teal-deep)" }} aria-hidden="true"/>}
                        {isWrongPick && <XCircle size={16} className="shrink-0 mt-0.5" style={{ color: "var(--pm-ink)" }} aria-hidden="true"/>}
                      </button>
                    );
                  })}
                </div>

                {revealed && card?.explanation && (
                  <div className="mt-4 pl-3" style={{ fontSize: 14, color: "rgba(11,42,48,0.85)", borderLeft: "2px solid var(--pm-teal-deep)" }}>
                    <span className="pm-eyebrow" style={{ fontSize: 11, color: "var(--pm-teal-deep)" }}>Why</span>
                    <div className="mt-0.5 whitespace-pre-wrap">{card.explanation}</div>
                  </div>
                )}

                <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
                  <Button variant="secondary" onClick={remove} data-testid="deck-remove-card" className="!py-2 !px-4" style={{ fontSize: 14 }}>
                    <Trash2 size={13} aria-hidden="true"/> Remove card
                  </Button>
                  {!revealed ? (
                    <Button onClick={submit} disabled={chosen === null} data-testid="deck-submit" className="!py-2 !px-4" style={{ fontSize: 14 }}>
                      Check answer <ArrowRight size={14} aria-hidden="true"/>
                    </Button>
                  ) : (
                    <Button onClick={next} data-testid="deck-next" className="!py-2 !px-4" style={{ fontSize: 14 }}>
                      {cursor + 1 >= cards.length ? <><RotateCw size={14} aria-hidden="true"/> Reshuffle</> : <>Next card <ArrowRight size={14} aria-hidden="true"/></>}
                    </Button>
                  )}
                </div>
              </Card>

              {lastResult && (
                <div className="mt-3" style={{ fontSize: 14, color: lastResult.correct ? "var(--pm-teal-deep)" : "var(--pm-ink)", fontWeight: 600 }}>
                  {lastResult.correct
                    ? (lastResult.mastered ? "Mastered. It'll drop out of your queue." : "Correct. One more in a row to master it.")
                    : "Wrong pick. Streak reset. Try it again next time."}
                </div>
              )}
            </>
          )}
        </div>
      </PageShell>
    </div>
  );
}
