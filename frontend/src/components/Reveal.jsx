import React from "react";
import useRevealOnView from "../hooks/useRevealOnView";

/**
 * Fades and lifts its children as they scroll into view, and reverses as
 * they scroll out, in either direction.
 */
export default function Reveal({ as: Tag = "div", delay = 0, className = "", style, children, ...rest }) {
  const [ref, shown] = useRevealOnView({ threshold: 0.1 });

  return (
    <Tag
      ref={ref}
      className={className}
      style={{
        opacity: shown ? 1 : 0,
        transform: shown ? "none" : "translateY(24px)",
        transition: `opacity 600ms ease-out ${delay}ms, transform 600ms ease-out ${delay}ms`,
        ...style,
      }}
      {...rest}
    >
      {children}
    </Tag>
  );
}
