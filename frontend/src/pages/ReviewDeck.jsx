import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../api";
import Header from "../components/Header";
import { CheckCircle2, XCircle, Trash2, RotateCw, Sparkles, ArrowRight, Filter } from "lucide-react";

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

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);

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
      if (data.correct) toast.success(data.mastered ? "Mastered — nice!" : "Correct");
      else toast.error("Not quite — check the explanation");
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
    return <div><Header /><div className="p-10 text-center text-sm text-pm-text2">Loading your deck…</div></div>;
  }

  return (
    <div>
      <Header />
      <div className="max-w-3xl mx-auto px-6 lg:px-10 py-10 pm-in">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-2">Review deck</div>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl lg:text-5xl font-bold">
              {cards.length === 0 ? "Nothing to review — yet." : "Drill your misses."}
            </h1>
            <p className="mt-2 text-sm text-pm-text2">
              {cards.length === 0
                ? "Finish an OA and hit 'Save to review deck' on any question you got wrong. They'll show up here."
                : "Two correct answers in a row master a card. Mastered cards drop out of your queue."}
            </p>
          </div>
          {cards.length > 0 && (
            <div className="flex items-center gap-2 text-xs font-mono">
              <Filter size={12} className="text-pm-text2"/>
              <button
                onClick={() => setFilter("unmastered")}
                data-testid="deck-filter-unmastered"
                className={`px-2.5 py-1 rounded-md border ${filter === "unmastered" ? "border-pm-primary bg-pm-primary/10 text-pm-primary-dark" : "border-pm-line bg-white text-pm-text2"}`}>Unmastered</button>
              <button
                onClick={() => setFilter("all")}
                data-testid="deck-filter-all"
                className={`px-2.5 py-1 rounded-md border ${filter === "all" ? "border-pm-primary bg-pm-primary/10 text-pm-primary-dark" : "border-pm-line bg-white text-pm-text2"}`}>All</button>
            </div>
          )}
        </div>

        {cards.length === 0 ? (
          <div className="mt-10 pm-card p-8 text-center">
            <Sparkles className="mx-auto text-pm-primary" size={28}/>
            <div className="mt-3 font-display text-lg font-bold">Your review deck is empty.</div>
            <Link to="/dashboard" className="pm-btn pm-btn-primary text-sm mt-5 inline-flex">Back to dashboard <ArrowRight size={14}/></Link>
          </div>
        ) : (
          <>
            {/* Progress strip */}
            <div className="mt-6 flex items-center justify-between text-xs font-mono text-pm-text2">
              <div>Card {cursor + 1} of {cards.length}</div>
              <div>{card?.company_name} · {card?.section_name}</div>
            </div>

            {/* Card */}
            <div className="mt-3 pm-card p-6" data-testid="deck-card">
              <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-pm-text2 mb-3">
                <span className="pm-chip" style={{background:"rgba(0,0,0,0.05)"}}>{card?.difficulty || "Medium"}</span>
                {card?.mastered && <span className="pm-chip pm-chip-primary">mastered</span>}
                {(card?.attempts || []).length > 0 && !card?.mastered && (
                  <span>{(card.attempts || []).filter(a => a.correct).length}/{(card.attempts || []).length} correct so far</span>
                )}
              </div>
              <div className="text-sm whitespace-pre-wrap">{card?.prompt}</div>

              <div className="mt-4 space-y-2">
                {shuffled.opts.map((opt, i) => {
                  const isChosen = chosen === i;
                  const isCorrect = revealed && i === shuffled.correct;
                  const isWrongPick = revealed && isChosen && i !== shuffled.correct;
                  let cls = "border border-pm-line bg-white hover:bg-black/[0.03]";
                  if (isChosen && !revealed) cls = "border border-pm-primary bg-pm-primary/10";
                  if (isCorrect) cls = "border border-pm-primary bg-pm-primary/10";
                  if (isWrongPick) cls = "border border-red-400 bg-red-50";
                  return (
                    <button
                      key={i}
                      onClick={() => !revealed && setChosen(i)}
                      disabled={revealed}
                      data-testid={`deck-option-${i}`}
                      className={`w-full text-left text-sm px-3 py-2.5 rounded-md flex items-start gap-2 transition-colors ${cls}`}>
                      <span className="font-mono text-[11px] text-pm-text2 shrink-0 mt-0.5">{String.fromCharCode(65 + i)}</span>
                      <span className="flex-1 min-w-0 whitespace-pre-wrap">{opt}</span>
                      {isCorrect && <CheckCircle2 size={14} className="text-pm-primary-dark shrink-0 mt-0.5"/>}
                      {isWrongPick && <XCircle size={14} className="text-red-600 shrink-0 mt-0.5"/>}
                    </button>
                  );
                })}
              </div>

              {revealed && card?.explanation && (
                <div className="mt-4 text-xs text-pm-text2 border-l-2 border-pm-primary/40 pl-3">
                  <span className="font-mono uppercase tracking-widest text-[10px] text-pm-primary-dark">Why</span>
                  <div className="mt-0.5 whitespace-pre-wrap">{card.explanation}</div>
                </div>
              )}

              <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                <button onClick={remove} data-testid="deck-remove-card" className="pm-btn pm-btn-ghost text-xs text-red-600 border-red-200 hover:bg-red-50">
                  <Trash2 size={13}/> Remove card
                </button>
                {!revealed ? (
                  <button
                    onClick={submit}
                    disabled={chosen === null}
                    data-testid="deck-submit"
                    className="pm-btn pm-btn-primary text-sm">
                    Check answer <ArrowRight size={14}/>
                  </button>
                ) : (
                  <button onClick={next} data-testid="deck-next" className="pm-btn pm-btn-primary text-sm">
                    {cursor + 1 >= cards.length ? <><RotateCw size={14}/> Reshuffle</> : <>Next card <ArrowRight size={14}/></>}
                  </button>
                )}
              </div>
            </div>

            {lastResult && (
              <div className={`mt-3 text-xs font-mono ${lastResult.correct ? "text-pm-primary-dark" : "text-red-600"}`}>
                {lastResult.correct
                  ? (lastResult.mastered ? "Mastered — it'll drop out of your queue." : "Correct. One more in a row to master it.")
                  : "Wrong pick — streak reset. Try it again next time."}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
