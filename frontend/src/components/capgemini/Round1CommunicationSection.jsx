import React, { useEffect, useRef, useState } from "react";
import { TID } from "../../testIds";
import { useMicRecorder } from "../../hooks/useMicRecorder";

// Capgemini Round 1: Communication Assessment -- ONE section, 6
// heterogeneous sub-parts (grammar / business_writing / situational /
// reading_comp / listening_comp / spoken_sim), sharing the section's
// single 60-minute timer (handled automatically by OARunner's existing
// per-section countdown, since this is just one section like any other).
// Items are grouped by the `part` tag server.py's generation branch sets,
// mirroring how CommMixedSection switches on `mode`.
//
// Answer keying: lettered-option parts (grammar/situational/reading_comp/
// listening_comp sub-questions) submit the selected LETTER string (e.g.
// "A") via setAnswer(id, letter) -- matches these questions' dict-shaped
// options ({A:.., B:.., ...}), not the array-shaped options the plain
// MCQSection renders elsewhere. business_writing submits the raw email
// text, same convention as EssaySection. spoken_sim (both item_types)
// submits the Whisper transcript text via the shared useMicRecorder hook
// -- same POST /oa/{attemptId}/transcribe flow Cognizant/LTIMindtree
// already use, moved to hooks/useMicRecorder.js so this file can import it
// without a circular dependency back into OARunner.jsx.
//
// All 6 parts render simultaneously in one vertical scroll (no per-part
// "next" pagination) -- matches Grammar's own existing convention of
// listing all 10 questions at once, so listening_comp's clips and
// spoken_sim's 2 items follow the same pattern rather than inventing a
// step-through flow.

function LetteredMCQCard({ id, prompt, options, selected, onSelect, qNum, qTotal, label }) {
  const letters = Object.keys(options).sort();
  return (
    <div className="pm-card p-6">
      <div className="text-xs font-mono uppercase text-pm-text2 mb-2">
        {label} {qNum} of {qTotal}
      </div>
      <div className="font-display text-lg font-semibold mb-4">{prompt}</div>
      <div className="grid grid-cols-1 gap-2">
        {letters.map((letter) => {
          const isSelected = selected === letter;
          return (
            <button
              key={letter}
              type="button"
              data-testid={TID.oaQuestionOption(id, letter)}
              onClick={() => onSelect(id, letter)}
              className={`text-left border rounded-lg p-3 flex items-start gap-3 transition ${
                isSelected ? "border-pm-primary bg-pm-primary/5" : "border-pm-border hover:bg-[rgba(0,0,0,0.02)]"
              }`}
            >
              <div className={`w-6 h-6 rounded-full grid place-items-center font-mono font-bold text-xs ${
                isSelected ? "bg-pm-primary text-white" : "bg-pm-muted"
              }`}>
                {letter}
              </div>
              <div className="flex-1 text-sm">{options[letter]}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function GrammarPart({ items, answers, setAnswer }) {
  if (!items.length) return null;
  return (
    <div className="space-y-4">
      <div className="font-display text-sm font-bold text-pm-text2 uppercase tracking-wide">
        Part 1 · Grammar &amp; Sentence Correction
      </div>
      {items.map((q, i) => (
        <LetteredMCQCard
          key={q.id}
          id={q.id}
          prompt={q.prompt}
          options={q.options}
          selected={answers[q.id]}
          onSelect={setAnswer}
          qNum={i + 1}
          qTotal={items.length}
          label="Q"
        />
      ))}
    </div>
  );
}

function BusinessWritingPart({ items, answers, setAnswer }) {
  if (!items.length) return null;
  return (
    <div className="space-y-4">
      <div className="font-display text-sm font-bold text-pm-text2 uppercase tracking-wide">
        Part 2 · Business Communication Writing
      </div>
      {items.map((q, i) => (
        <div key={q.id} className="pm-card p-6">
          <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Scenario {i + 1} of {items.length}</div>
          <div className="text-sm text-pm-text2 mb-1">
            Recipient: <span className="font-semibold text-pm-text">{q.recipient_type}</span>
            {" · "}Tone: <span className="font-semibold text-pm-text">{q.tone_expected}</span>
          </div>
          <div className="font-display text-lg font-semibold mb-4">{q.context}</div>
          <textarea
            data-testid={TID.oaEssayInput ? TID.oaEssayInput(q.id) : undefined}
            className="w-full min-h-[220px] rounded-lg border border-pm-border p-3 text-sm font-sans"
            placeholder="Write your email response…"
            value={answers[q.id] || ""}
            onChange={(e) => setAnswer(q.id, e.target.value)}
          />
        </div>
      ))}
    </div>
  );
}

function SituationalPart({ items, answers, setAnswer }) {
  if (!items.length) return null;
  return (
    <div className="space-y-4">
      <div className="font-display text-sm font-bold text-pm-text2 uppercase tracking-wide">
        Part 3 · Task Situational Awareness &amp; Response
      </div>
      {items.map((q, i) => (
        <LetteredMCQCard
          key={q.id}
          id={q.id}
          prompt={q.scenario_prompt}
          options={q.options}
          selected={answers[q.id]}
          onSelect={setAnswer}
          qNum={i + 1}
          qTotal={items.length}
          label="Q"
        />
      ))}
    </div>
  );
}

function ReadingCompPart({ items, answers, setAnswer }) {
  if (!items.length) return null;
  const totalQuestions = items.reduce((sum, p) => sum + (p.questions || []).length, 0);
  let qCounter = 0;
  return (
    <div className="space-y-4">
      <div className="font-display text-sm font-bold text-pm-text2 uppercase tracking-wide">
        Part 4 · Workplace Reading Comprehension
      </div>
      {items.map((passage) => (
        <div key={passage.id} className="pm-card p-6">
          <div className="text-xs font-mono uppercase text-pm-text2 mb-2">{passage.passage_type}</div>
          <div className="whitespace-pre-wrap text-sm font-sans mb-5 pb-5 border-b border-pm-border">
            {passage.passage_text}
          </div>
          <div className="space-y-4">
            {(passage.questions || []).map((subq) => {
              qCounter += 1;
              return (
                <LetteredMCQCard
                  key={subq.question_id}
                  id={subq.question_id}
                  prompt={subq.prompt}
                  options={subq.options}
                  selected={answers[subq.question_id]}
                  onSelect={setAnswer}
                  qNum={qCounter}
                  qTotal={totalQuestions}
                  label="Q"
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// -------- Listening audio player: SINGLE PLAY, no scrub/seek -------------
// No `controls` attribute on the underlying <audio> element -- the native
// scrub bar would let a candidate rewind/seek, defeating a listening test.
// Instead: one custom Play button, locked the INSTANT play is triggered
// (not on completion) -- disabling on play-START, not play-END, is the
// spec's own explicit preference, since locking only after the clip ends
// would let a candidate pause partway through and resume later, or replay
// via pause/seek gaming before it ever "ends".
//
// KNOWN GAP (flagged, not silently handled): `played` is local React state,
// not persisted anywhere -- checked this app's existing pattern first
// (OARunner.jsx keeps ALL answers in-memory only, via plain useState/
// setAnswers, with zero localStorage/server-side draft-save anywhere in
// this codebase) and there is genuinely nothing to hook into here without
// adding new backend/persistence machinery, which is out of scope for this
// frontend-only pass. A hard page refresh mid-section resets this lock the
// same way it already resets every other section's typed/selected answers
// today -- not a new or worse gap this component introduces, but still
// worth calling out explicitly rather than implying it's handled.
function ListeningAudioPlayer({ audioUrl }) {
  const audioRef = useRef(null);
  const [playState, setPlayState] = useState("unplayed"); // unplayed | playing | played

  const handlePlay = () => {
    if (playState !== "unplayed") return; // already locked -- no-op, not just visually disabled
    setPlayState("playing");
    audioRef.current?.play();
  };

  return (
    <div className="mb-4">
      <audio
        ref={audioRef}
        src={audioUrl}
        onEnded={() => setPlayState("played")}
        onContextMenu={(e) => e.preventDefault()}
      />
      <div className="flex items-center gap-3">
        <button
          type="button"
          data-testid={TID.oaListeningPlayBtn ? TID.oaListeningPlayBtn(audioUrl) : undefined}
          onClick={handlePlay}
          disabled={playState !== "unplayed"}
          className={`pm-btn text-sm py-2 px-4 ${
            playState === "unplayed" ? "pm-btn-primary" : "pm-btn-secondary opacity-60 cursor-not-allowed"
          }`}
        >
          {playState === "unplayed" ? "▶ Play clip" : playState === "playing" ? "Playing…" : "Already played"}
        </button>
        <div className="text-xs text-pm-text2">
          {playState === "unplayed"
            ? "You can only play this clip once — listen carefully."
            : "This clip cannot be replayed."}
        </div>
      </div>
    </div>
  );
}

function ListeningCompPart({ items, answers, setAnswer }) {
  if (!items.length) return null;
  const totalQuestions = items.reduce((sum, c) => sum + (c.questions || []).length, 0);
  let qCounter = 0;
  return (
    <div className="space-y-4">
      <div className="font-display text-sm font-bold text-pm-text2 uppercase tracking-wide">
        Part 5 · Workplace Listening Comprehension
      </div>
      {items.map((clip) => (
        <div key={clip.id} className="pm-card p-6">
          <div className="text-xs font-mono uppercase text-pm-text2 mb-2">
            {clip.clip_type === "dialogue" ? "Dialogue" : "Monologue"}
            {clip.speaker_count ? ` · ${clip.speaker_count} speaker${clip.speaker_count > 1 ? "s" : ""}` : ""}
          </div>
          <ListeningAudioPlayer audioUrl={clip.audio_url} />
          <div className="space-y-4 pt-4 border-t border-pm-border">
            {(clip.questions || []).map((subq) => {
              qCounter += 1;
              return (
                <LetteredMCQCard
                  key={subq.question_id}
                  id={subq.question_id}
                  prompt={subq.prompt}
                  options={subq.options}
                  selected={answers[subq.question_id]}
                  onSelect={setAnswer}
                  qNum={qCounter}
                  qTotal={totalQuestions}
                  label="Q"
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// -------- Spoken sim: read_aloud / respond_to_prompt (record + transcribe) -
// Mirrors OARunner's own SpeakingAnswerCard/ReadAloudCard interaction states
// (idle/recording/uploading/done, typed-mode fallback, editable transcript,
// re-record) EXACTLY -- same useMicRecorder hook, same status machine, just
// the prompt content and labels swapped for this section's two item shapes.
// Not a new recording UI: this is the established pattern, just not
// literally importable as a JSX component across files (SpeakingAnswerCard
// is a local, unexported function inside OARunner.jsx) -- only the
// underlying hook needed to move to be shared (see hooks/useMicRecorder.js).
function SpokenReadAloudCard({ attemptId, sectionKey, q, value, onChange }) {
  const [typedMode, setTypedMode] = useState(false);
  const mic = useMicRecorder(attemptId, sectionKey, q.id, onChange);

  useEffect(() => { if (mic.status === "unavailable") setTypedMode(true); }, [mic.status]);

  return (
    <div className="pm-card p-6">
      <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Read Aloud</div>
      <div className="whitespace-pre-wrap text-sm font-sans mb-5 pb-5 border-b border-pm-border">
        {q.passage_text}
      </div>
      {typedMode ? (
        <>
          <div className="text-xs text-pm-text2 mb-2">Mic unavailable — type what you would say instead.</div>
          <textarea
            data-testid={TID.oaMicFallbackInput ? TID.oaMicFallbackInput(q.id) : undefined}
            className="pm-input min-h-[120px] font-sans"
            placeholder="Type your response…"
            value={value}
            onChange={(e) => onChange(e.target.value)}
          />
        </>
      ) : mic.status === "recording" ? (
        <button data-testid={TID.oaMicStopBtn ? TID.oaMicStopBtn(q.id) : undefined} onClick={mic.stop} className="pm-btn pm-btn-secondary text-sm py-2 px-4">
          Stop
        </button>
      ) : mic.status === "uploading" ? (
        <div className="text-sm text-pm-text2">Transcribing…</div>
      ) : (
        <div className="flex items-center gap-3">
          <button data-testid={TID.oaMicRecordBtn ? TID.oaMicRecordBtn(q.id) : undefined} onClick={mic.start} className="pm-btn pm-btn-primary text-sm py-2 px-4">
            {value ? "Re-record" : "Record"}
          </button>
          <button onClick={() => setTypedMode(true)} className="text-xs text-pm-text2 underline">Type instead</button>
        </div>
      )}
      {value && !typedMode && (
        <div className="mt-3">
          <div className="text-xs text-pm-text2 mb-1">Transcript (edit if needed):</div>
          <textarea
            data-testid={TID.oaTranscriptInput ? TID.oaTranscriptInput(q.id) : undefined}
            className="pm-input min-h-[100px] font-sans"
            value={value}
            onChange={(e) => onChange(e.target.value)}
          />
        </div>
      )}
    </div>
  );
}

function SpokenRespondToPromptCard({ attemptId, sectionKey, q, value, onChange }) {
  const [typedMode, setTypedMode] = useState(false);
  const mic = useMicRecorder(attemptId, sectionKey, q.id, onChange);

  useEffect(() => { if (mic.status === "unavailable") setTypedMode(true); }, [mic.status]);

  return (
    <div className="pm-card p-6">
      <div className="text-xs font-mono uppercase text-pm-text2 mb-2">Respond to Prompt</div>
      <div className="font-display text-lg font-semibold mb-4">{q.scenario}</div>
      {typedMode ? (
        <>
          <div className="text-xs text-pm-text2 mb-2">Mic unavailable — type your response instead.</div>
          <textarea
            data-testid={TID.oaMicFallbackInput ? TID.oaMicFallbackInput(q.id) : undefined}
            className="pm-input min-h-[120px] font-sans"
            placeholder="Type your response…"
            value={value}
            onChange={(e) => onChange(e.target.value)}
          />
        </>
      ) : mic.status === "recording" ? (
        <button data-testid={TID.oaMicStopBtn ? TID.oaMicStopBtn(q.id) : undefined} onClick={mic.stop} className="pm-btn pm-btn-secondary text-sm py-2 px-4">
          Stop
        </button>
      ) : mic.status === "uploading" ? (
        <div className="text-sm text-pm-text2">Transcribing…</div>
      ) : (
        <div className="flex items-center gap-3">
          <button data-testid={TID.oaMicRecordBtn ? TID.oaMicRecordBtn(q.id) : undefined} onClick={mic.start} className="pm-btn pm-btn-primary text-sm py-2 px-4">
            {value ? "Re-record" : "Record"}
          </button>
          <button onClick={() => setTypedMode(true)} className="text-xs text-pm-text2 underline">Type instead</button>
        </div>
      )}
      {value && !typedMode && (
        <div className="mt-3">
          <div className="text-xs text-pm-text2 mb-1">Transcript (edit if needed):</div>
          <textarea
            data-testid={TID.oaTranscriptInput ? TID.oaTranscriptInput(q.id) : undefined}
            className="pm-input min-h-[100px] font-sans"
            value={value}
            onChange={(e) => onChange(e.target.value)}
          />
        </div>
      )}
    </div>
  );
}

function SpokenSimPart({ attemptId, sectionKey, items, answers, setAnswer }) {
  if (!items.length) return null;
  const readAloud = items.find((q) => q.item_type === "read_aloud");
  const respondToPrompt = items.find((q) => q.item_type === "respond_to_prompt");
  return (
    <div className="space-y-4">
      <div className="font-display text-sm font-bold text-pm-text2 uppercase tracking-wide">
        Part 6 · Spoken Communication Simulation
      </div>
      {readAloud && (
        <SpokenReadAloudCard
          attemptId={attemptId}
          sectionKey={sectionKey}
          q={readAloud}
          value={answers[readAloud.id] || ""}
          onChange={(v) => setAnswer(readAloud.id, v)}
        />
      )}
      {respondToPrompt && (
        <SpokenRespondToPromptCard
          attemptId={attemptId}
          sectionKey={sectionKey}
          q={respondToPrompt}
          value={answers[respondToPrompt.id] || ""}
          onChange={(v) => setAnswer(respondToPrompt.id, v)}
        />
      )}
    </div>
  );
}

export default function Round1CommunicationSection({ attemptId, section, answers, setAnswer }) {
  const qs = section.questions || [];
  const grammar = qs.filter((q) => q.part === "grammar");
  const businessWriting = qs.filter((q) => q.part === "business_writing");
  const situational = qs.filter((q) => q.part === "situational");
  const readingComp = qs.filter((q) => q.part === "reading_comp");
  const listeningComp = qs.filter((q) => q.part === "listening_comp");
  const spokenSim = qs.filter((q) => q.part === "spoken_sim");

  if (qs.length === 0) {
    return <div className="pm-card p-6 text-pm-text2">Question generation returned empty. Try re-starting this run.</div>;
  }

  return (
    <div className="space-y-8">
      <GrammarPart items={grammar} answers={answers} setAnswer={setAnswer} />
      <BusinessWritingPart items={businessWriting} answers={answers} setAnswer={setAnswer} />
      <SituationalPart items={situational} answers={answers} setAnswer={setAnswer} />
      <ReadingCompPart items={readingComp} answers={answers} setAnswer={setAnswer} />
      <ListeningCompPart items={listeningComp} answers={answers} setAnswer={setAnswer} />
      <SpokenSimPart attemptId={attemptId} sectionKey={section.key} items={spokenSim} answers={answers} setAnswer={setAnswer} />
    </div>
  );
}
