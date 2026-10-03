import { useEffect, useRef, useState } from "react";

/**
 * Drives "fade/slide in once, when scrolled into view" animations.
 * Returns [ref, revealed] -- attach ref to the observed element, gate
 * animation classes/styles on `revealed`.
 *
 * Always backed by a short fallback timer (500ms default), not just the
 * IntersectionObserver callback: an animation whose initial state is
 * invisible/offset must never depend on a single trigger path, or content
 * can end up permanently hidden (an unmet threshold on an unusual
 * viewport, a browser quirk, a race with anchor-link scrolling) -- this
 * was a real bug in PhaseStrip (2026-10): the phase cards read as
 * "missing" in a screenshot taken before the observer fired.
 */
export default function useRevealOnView({ threshold = 0.3, fallbackMs = 500 } = {}) {
  const ref = useRef(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setRevealed(true);
      return;
    }

    let fallback = null;
    const reveal = () => {
      observer.disconnect();
      if (fallback) clearTimeout(fallback);
      setRevealed(true);
    };

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) reveal();
      },
      { threshold }
    );
    observer.observe(el);
    fallback = setTimeout(reveal, fallbackMs);

    return () => {
      observer.disconnect();
      if (fallback) clearTimeout(fallback);
    };
  }, [threshold, fallbackMs]);

  return [ref, revealed];
}
