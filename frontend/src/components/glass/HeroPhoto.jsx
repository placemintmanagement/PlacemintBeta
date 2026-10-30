import React, { useState } from "react";
import PersonIllustration from "./PersonIllustration";

// Real, product-owner-provided photo (2026-10, replaces the earlier
// AI-generated ones -- those are deleted from public/photos/, nothing
// still references them) -- a person wearing a headset, smiling, bookshelf
// background. Still decorative (alt=""), but it's a genuine photo, not
// AI-generated, so the "AI-generated" framing used for the earlier photos
// doesn't apply to this one specifically.
//
// Re-encoded from the original 8192x5464 / ~22MB JPEG down to 2400x1601 /
// ~250KB (resized to 2400px on the long edge, JPEG quality 82) -- the
// original was far too large to ship as a web asset. Aspect ratio 1.5:1
// (2400/1601), used for BOTH the hero's big "video window" (.gl-video,
// ~1.76:1 measured live) and its small picture-in-picture thumbnail
// (.gl-pip, 150x100 = exactly 1.5:1 -- an essentially perfect match,
// needs no cropping at all there). For .gl-video, cover-fit is width-
// constrained (container is relatively wider than the photo): checked
// against the actual photo (a 5%-gridline overlay, not a guess) -- her
// headphones start at ~15% of the photo's height and the crop only trims
// ~7.5% off the top/bottom at default centre position, so the default
// centre object-position already clears her head/headphones with real
// margin; no object-position override needed, unlike the very first
// (portrait, 0.75:1) photo this hero used.
const SRC = "/photos/hero-person-provided.jpg";

// Second real, product-owner-provided photo (2026-10): the AI interviewer
// persona ("Arun"), shown only in the small picture-in-picture slot --
// the big .gl-video background stays the candidate's photo. 1565x1005
// (~1.56:1), a close match for .gl-pip's 150x100 (1.5:1) frame, so no
// cropping math was needed here the way the hero photo required.
const PIP_SRC = "/photos/interviewer-person-provided.jpg";

/**
 * Renders the hero photo, filling its parent container (parent supplies
 * the frame: size, border-radius, overflow:hidden). Falls back to the
 * generic inline SVG figure (PersonIllustration) if the photo fails to
 * load for any reason, instead of showing a broken image -- same
 * robustness convention as the rest of this project's photo-slot work.
 * `small` renders the AI interviewer's own photo (the pip), not a cropped
 * copy of the big candidate photo.
 */
export default function HeroPhoto({ small = false }) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return <PersonIllustration small={small} />;
  }

  return (
    <img
      src={small ? PIP_SRC : SRC}
      alt=""
      aria-hidden="true"
      style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
      onError={() => setFailed(true)}
    />
  );
}
