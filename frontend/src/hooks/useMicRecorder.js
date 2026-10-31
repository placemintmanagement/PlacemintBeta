import { useRef, useState } from "react";
import { toast } from "sonner";
import api from "../api";

// Shared MediaRecorder -> POST /oa/{attemptId}/transcribe flow. Falls back to
// `status === "unavailable"` (caller renders a typed textarea instead) if
// getUserMedia is missing, denied, or errors — there is no mic requirement
// anywhere else in this app, so this has to degrade gracefully.
//
// Moved out of OARunner.jsx (2026-08, Capgemini Round 1 Section 6 frontend
// pass) into its own module so Round1CommunicationSection.jsx (a separate
// component file, not part of OARunner.jsx) can reuse it too, without
// creating a circular import back into the page file that already imports
// Round1CommunicationSection. Behavior is unchanged from the original --
// this is a relocation, not a rewrite. Every existing call site (ReadAloudCard/
// SpeakingAnswerCard/SpeakingSection in OARunner.jsx) now imports it from
// here instead of using the local function.
export function useMicRecorder(attemptId, sectionKey, questionId, onTranscript) {
  const [status, setStatus] = useState("idle"); // idle | recording | uploading | done | unavailable | error
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  const start = async () => {
    if (!navigator.mediaDevices?.getUserMedia) { setStatus("unavailable"); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const mr = new MediaRecorder(stream);
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = async () => {
        streamRef.current?.getTracks().forEach(t => t.stop());
        setStatus("uploading");
        try {
          const blob = new Blob(chunksRef.current, { type: "audio/webm" });
          const fd = new FormData();
          fd.append("section_key", sectionKey);
          fd.append("question_id", questionId);
          fd.append("file", blob, "recording.webm");
          const { data } = await api.post(`/oa/${attemptId}/transcribe`, fd, { headers: { "Content-Type": "multipart/form-data" } });
          onTranscript(data.transcript || "");
          setStatus("done");
        } catch (err) {
          toast.error("Transcription failed. You can type your answer instead.");
          setStatus("error");
        }
      };
      mediaRecorderRef.current = mr;
      mr.start();
      setStatus("recording");
    } catch (err) {
      setStatus("unavailable");
    }
  };

  const stop = () => { mediaRecorderRef.current?.stop(); };
  const reset = () => setStatus("idle");

  return { status, start, stop, reset };
}
