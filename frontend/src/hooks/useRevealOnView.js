import { useEffect, useRef, useState } from "react";

/**
 * Scroll-driven reveal, in both directions. Returns [ref, revealed]: attach
 * ref to the observed element and gate animation styles on `revealed`.
 * `revealed` is true while the element is in view and goes false again as it
 * scrolls out, so sections animate on the way down and on the way back up.
 *
 * There is no timer fallback. A timer fires whether or not the element is on
 * screen, so the animation plays on page load instead of on scroll. The
 * observer alone decides, and content is shown straight away when reduced
 * motion is requested or IntersectionObserver is unavailable, so nothing can
 * stay hidden.
 *
 * `fallbackMs` is accepted for backwards compatibility and ignored.
 */
export default function useRevealOnView({ threshold = 0.3 } = {}) {
  const ref = useRef(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      !("IntersectionObserver" in window)
    ) {
      setRevealed(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => setRevealed(entry.isIntersecting),
      { threshold, rootMargin: "0px 0px -8% 0px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  return [ref, revealed];
}
