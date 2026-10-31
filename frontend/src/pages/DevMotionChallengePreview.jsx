import React, { useState, useEffect } from "react";
import Header from "../components/Header";
import MotionChallengeSection from "../components/games/MotionChallengeSection";

// Standing dev tool (not temporary) -- unauthenticated-looking preview
// route at /dev/motion-challenge-preview. Like GridChallengeSection's own
// preview, this is NOT fully self-contained: motion_challenge's /move and
// /undo calls are real server round trips, so this page needs a real
// attemptId/sectionKey pointing at an actual oa_attempts + game_session
// fixture already set up server-side (see the scratchpad round-trip test
// script for how one is constructed) and a real pm_token in localStorage.
// UNLIKE grid_challenge though, the puzzle CONTENT itself is safe to
// reveal upfront (nothing hidden), so these 4 levels are real, verified
// output from motion_challenge.generate_instance() (seed="motion-challenge-step4-testdata-seed"),
// hardcoded here the same way DevGamePreview.jsx embeds real
// deductive_grid output -- not hand-drawn mockups. Query params let the
// backend fixture be swapped without editing this file:
// ?attemptId=...&sectionKey=...&token=... -- if ?token is present it's
// written into localStorage.pm_token on mount so a visitor with no prior
// session (nothing in their own browser's localStorage) still gets real,
// authenticated /move, /undo, /state round trips instead of a 401.
const SAMPLE_PUZZLES = [
  {
    "rows": 4,
    "cols": 6,
    "walls": [
      [
        1,
        1
      ],
      [
        1,
        3
      ],
      [
        3,
        3
      ]
    ],
    "hole": [
      2,
      3
    ],
    "blocks": [
      {
        "id": "b1",
        "row": 0,
        "col": 4,
        "width": 2,
        "height": 2,
        "color": "#2C6FA8"
      },
      {
        "id": "b2",
        "row": 2,
        "col": 0,
        "width": 2,
        "height": 1,
        "color": "#D4A017"
      },
      {
        "id": "b3",
        "row": 0,
        "col": 0,
        "width": 1,
        "height": 2,
        "color": "#3D8B54"
      },
      {
        "id": "b4",
        "row": 1,
        "col": 2,
        "width": 1,
        "height": 2,
        "color": "#8B4F9F"
      },
      {
        "id": "b5",
        "row": 2,
        "col": 4,
        "width": 2,
        "height": 2,
        "color": "#C1652F"
      }
    ],
    "ballStart": [
      3,
      1
    ],
    "moveBudget": 5,
    "puzzle_id": "mc-0001",
    "gameType": "motion_challenge",
    "companyTags": [
      "capgemini",
      "cognizant",
      "accenture",
      "ibm"
    ],
    "content_hash": "b6fbbf89f0ae21b09c0164b7e9cb2143583bb318aa477b2395be7405b9390a3e",
    "id": "mc-0001"
  },
  {
    "rows": 4,
    "cols": 6,
    "walls": [
      [
        0,
        3
      ],
      [
        0,
        4
      ],
      [
        2,
        1
      ]
    ],
    "hole": [
      1,
      0
    ],
    "blocks": [
      {
        "id": "b1",
        "row": 1,
        "col": 5,
        "width": 1,
        "height": 2,
        "color": "#2C6FA8"
      },
      {
        "id": "b2",
        "row": 0,
        "col": 1,
        "width": 2,
        "height": 2,
        "color": "#D4A017"
      },
      {
        "id": "b3",
        "row": 1,
        "col": 4,
        "width": 1,
        "height": 2,
        "color": "#3D8B54"
      },
      {
        "id": "b4",
        "row": 1,
        "col": 3,
        "width": 1,
        "height": 2,
        "color": "#8B4F9F"
      },
      {
        "id": "b5",
        "row": 3,
        "col": 2,
        "width": 2,
        "height": 1,
        "color": "#C1652F"
      }
    ],
    "ballStart": [
      3,
      1
    ],
    "moveBudget": 4,
    "puzzle_id": "mc-0002",
    "gameType": "motion_challenge",
    "companyTags": [
      "capgemini",
      "cognizant",
      "accenture",
      "ibm"
    ],
    "content_hash": "0e77349317f8dcbd206c59bc32255f411f1b5e66e19248757b69b63cd73f6e7f",
    "id": "mc-0002"
  },
  {
    "rows": 4,
    "cols": 6,
    "walls": [
      [
        2,
        4
      ],
      [
        2,
        5
      ],
      [
        3,
        0
      ]
    ],
    "hole": [
      1,
      5
    ],
    "blocks": [
      {
        "id": "b1",
        "row": 1,
        "col": 0,
        "width": 2,
        "height": 1,
        "color": "#2C6FA8"
      },
      {
        "id": "b2",
        "row": 3,
        "col": 1,
        "width": 2,
        "height": 1,
        "color": "#D4A017"
      },
      {
        "id": "b3",
        "row": 1,
        "col": 3,
        "width": 1,
        "height": 2,
        "color": "#3D8B54"
      },
      {
        "id": "b4",
        "row": 0,
        "col": 0,
        "width": 2,
        "height": 1,
        "color": "#8B4F9F"
      },
      {
        "id": "b5",
        "row": 3,
        "col": 4,
        "width": 2,
        "height": 1,
        "color": "#C1652F"
      }
    ],
    "ballStart": [
      2,
      2
    ],
    "moveBudget": 6,
    "puzzle_id": "mc-0003",
    "gameType": "motion_challenge",
    "companyTags": [
      "capgemini",
      "cognizant",
      "accenture",
      "ibm"
    ],
    "content_hash": "7ca1c4d617944e997ddace0e9e1b72de2332e877cf9c2ab395382dd75c6c8707",
    "id": "mc-0003"
  },
  {
    "rows": 4,
    "cols": 6,
    "walls": [
      [
        0,
        2
      ],
      [
        1,
        4
      ],
      [
        3,
        3
      ]
    ],
    "hole": [
      1,
      3
    ],
    "blocks": [
      {
        "id": "b1",
        "row": 1,
        "col": 2,
        "width": 2,
        "height": 1,
        "color": "#2C6FA8"
      },
      {
        "id": "b2",
        "row": 0,
        "col": 3,
        "width": 2,
        "height": 1,
        "color": "#D4A017"
      },
      {
        "id": "b3",
        "row": 2,
        "col": 0,
        "width": 2,
        "height": 1,
        "color": "#3D8B54"
      },
      {
        "id": "b4",
        "row": 2,
        "col": 3,
        "width": 2,
        "height": 1,
        "color": "#8B4F9F"
      },
      {
        "id": "b5",
        "row": 3,
        "col": 4,
        "width": 2,
        "height": 1,
        "color": "#C1652F"
      }
    ],
    "ballStart": [
      3,
      2
    ],
    "moveBudget": 6,
    "puzzle_id": "mc-0004",
    "gameType": "motion_challenge",
    "companyTags": [
      "capgemini",
      "cognizant",
      "accenture",
      "ibm"
    ],
    "content_hash": "9c34529c8baf33b1ae0d92f00f80a3dd4a6633bdc5f3591d3b68141822c74947",
    "id": "mc-0004"
  }
];

const SAMPLE_CONFIG = {
  poolSeconds: 240,
  instructions: {
    title: "Motion Challenge",
    rule: "Move the colored blocks out of the way to clear a path, then get the red ball into the black hole.",
    scoringNote: "+4 for solving a level within its move budget, -1 if the budget runs out (or time runs out) before you solve it.",
    timerNote: "You have 4 minutes total across all levels -- moves used counts up toward each level's budget.",
  },
};

export default function DevMotionChallengePreview() {
  const [completed, setCompleted] = useState(false);
  const params = new URLSearchParams(window.location.search);
  const attemptId = params.get("attemptId") || "oa-mcshow-0001";
  const sectionKey = params.get("sectionKey") || "motiontest";
  const tokenParam = params.get("token");

  useEffect(() => {
    if (tokenParam) {
      localStorage.setItem("pm_token", tokenParam);
    }
  }, [tokenParam]);

  if (!tokenParam && !localStorage.getItem("pm_token")) {
    return (
      <div>
        <Header />
        <div className="max-w-3xl mx-auto px-6 py-10">
          <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-1">dev preview · not a real route</div>
          <h1 className="font-display text-2xl font-bold mb-2">Motion Challenge: live preview</h1>
          <div className="pm-card p-6 text-sm text-pm-text2">
            No auth token found. This page makes real, authenticated <code>/move</code>/<code>/undo</code>/<code>/state</code> calls against a real backend
            fixture, so it needs a <code>pm_token</code> belonging to the fixture's owning user. Ask whoever set up the fixture for a link with
            <code>&amp;token=...</code> appended, or log in normally as that user first.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header />
      <div className="max-w-3xl mx-auto px-6 py-10">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-1">dev preview · not a real route</div>
        <h1 className="font-display text-2xl font-bold mb-2">Motion Challenge: live preview</h1>
        <p className="text-sm text-pm-text2 mb-6">
          Uses a real backend fixture (attemptId=<code>{attemptId}</code>, sectionKey=<code>{sectionKey}</code>) for real /move and /undo round trips -- swap via <code>?attemptId=...&amp;sectionKey=...</code>
        </p>

        {completed ? (
          <div className="pm-card p-6">
            <div className="font-display text-lg font-semibold mb-3">Section complete</div>
            <div className="text-sm text-pm-text2">onComplete() fired -- in the real app, OARunner takes over from here.</div>
          </div>
        ) : (
          <MotionChallengeSection
            puzzles={SAMPLE_PUZZLES}
            attemptId={attemptId}
            sectionKey={sectionKey}
            config={SAMPLE_CONFIG}
            onComplete={() => setCompleted(true)}
          />
        )}
      </div>
    </div>
  );
}
