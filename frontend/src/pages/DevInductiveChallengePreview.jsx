import React, { useState, useRef } from "react";
import Header from "../components/Header";
import InductiveChallengeSection from "../components/games/InductiveChallengeSection";

// Standing dev tool (not temporary) -- unauthenticated preview route at
// /dev/inductive-preview for visually confirming inductive_challenge before
// it's wired into the real OA flow. These 5 instances are real output from
// inductive_challenge.generate_instance() (seed="inductive-challenge-devpreview-seed"),
// each independently re-verified via verify_instance() before being
// hardcoded here -- not hand-drawn mockups. Not yet inserted into
// puzzle_bank. Public-safe shape only (no correctAnswer field), matching
// what strip_answer() actually sends to the client -- this type's answer
// IS hidden (unlike switch_challenge), same situation as deductive_grid's
// preview, so mockCheckAnswer below simulates plausible correct/wrong
// rather than computing a real answer client-side.
const SAMPLE_PUZZLES = [
  {
    "id": "preview-ic-1",
    "demoBefore": [
      [
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "square",
          "color": "olive"
        }
      ],
      [
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "triangle",
          "color": "brick"
        }
      ],
      [
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "cross",
          "color": "plum"
        }
      ]
    ],
    "demoAfter": [
      [
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "circle",
          "color": "navy"
        }
      ],
      [
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "square",
          "color": "olive"
        }
      ],
      [
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "triangle",
          "color": "brick"
        }
      ]
    ],
    "candidates": [
      [
        [
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "cross",
            "color": "plum"
          }
        ],
        [
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "cross",
            "color": "plum"
          }
        ],
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ]
      ],
      [
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "cross",
            "color": "plum"
          }
        ]
      ],
      [
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ],
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ],
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ]
      ],
      [
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "cross",
            "color": "plum"
          }
        ],
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ],
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ]
      ]
    ]
  },
  {
    "id": "preview-ic-2",
    "demoBefore": [
      [
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "square",
          "color": "olive"
        }
      ],
      [
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "circle",
          "color": "navy"
        }
      ],
      [
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "circle",
          "color": "navy"
        }
      ]
    ],
    "demoAfter": [
      [
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "triangle",
          "color": "brick"
        }
      ],
      [
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "cross",
          "color": "plum"
        }
      ],
      [
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "cross",
          "color": "plum"
        }
      ]
    ],
    "candidates": [
      [
        [
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "cross",
            "color": "plum"
          }
        ],
        [
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ]
      ],
      [
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "cross",
            "color": "plum"
          }
        ],
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ]
      ],
      [
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ],
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "cross",
            "color": "plum"
          }
        ],
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ]
      ],
      [
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ],
        [
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ],
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ]
      ]
    ]
  },
  {
    "id": "preview-ic-3",
    "demoBefore": [
      [
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "circle",
          "color": "navy"
        }
      ],
      [
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "circle",
          "color": "navy"
        }
      ],
      [
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "cross",
          "color": "plum"
        }
      ]
    ],
    "demoAfter": [
      [
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "triangle",
          "color": "brick"
        }
      ],
      [
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "triangle",
          "color": "brick"
        }
      ],
      [
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "circle",
          "color": "navy"
        }
      ]
    ],
    "candidates": [
      [
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ],
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ]
      ],
      [
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "cross",
            "color": "plum"
          }
        ],
        [
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ]
      ],
      [
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ],
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ]
      ],
      [
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ],
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ],
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ]
      ]
    ]
  },
  {
    "id": "preview-ic-4",
    "demoBefore": [
      [
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "circle",
          "color": "navy"
        }
      ],
      [
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "circle",
          "color": "navy"
        }
      ],
      [
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "circle",
          "color": "navy"
        }
      ]
    ],
    "demoAfter": [
      [
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "triangle",
          "color": "brick"
        }
      ],
      [
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "triangle",
          "color": "brick"
        }
      ],
      [
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "triangle",
          "color": "brick"
        }
      ]
    ],
    "candidates": [
      [
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ],
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ],
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ]
      ],
      [
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ],
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ]
      ],
      [
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ],
        [
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "cross",
            "color": "plum"
          }
        ],
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "cross",
            "color": "plum"
          }
        ]
      ],
      [
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ],
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ],
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ]
      ]
    ]
  },
  {
    "id": "preview-ic-5",
    "demoBefore": [
      [
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "triangle",
          "color": "brick"
        }
      ],
      [
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "triangle",
          "color": "brick"
        }
      ],
      [
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "square",
          "color": "olive"
        }
      ]
    ],
    "demoAfter": [
      [
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "square",
          "color": "olive"
        },
        {
          "shape": "circle",
          "color": "navy"
        }
      ],
      [
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "circle",
          "color": "navy"
        },
        {
          "shape": "circle",
          "color": "navy"
        }
      ],
      [
        {
          "shape": "cross",
          "color": "plum"
        },
        {
          "shape": "triangle",
          "color": "brick"
        },
        {
          "shape": "triangle",
          "color": "brick"
        }
      ]
    ],
    "candidates": [
      [
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "cross",
            "color": "plum"
          }
        ],
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ]
      ],
      [
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ],
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ]
      ],
      [
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "triangle",
            "color": "brick"
          }
        ],
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ],
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "cross",
            "color": "plum"
          },
          {
            "shape": "circle",
            "color": "navy"
          }
        ]
      ],
      [
        [
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "triangle",
            "color": "brick"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ],
        [
          {
            "shape": "circle",
            "color": "navy"
          },
          {
            "shape": "square",
            "color": "olive"
          },
          {
            "shape": "square",
            "color": "olive"
          }
        ]
      ]
    ]
  }
];

const SAMPLE_CONFIG = {
  timerPerPuzzle: 30,
  instructions: {
    title: "Inductive Challenge",
    rule: "Two grids follow a hidden rule. Find it, then pick the 2 of 4 candidate grids that follow the same rule.",
    scoringNote: "+3 for a correct answer, -1 for an incorrect or incomplete answer, or a time out.",
    timerNote: "You have 30 seconds per level.",
  },
};

export default function DevInductiveChallengePreview() {
  const [completedAnswers, setCompletedAnswers] = useState(null);
  const [runKey, setRunKey] = useState(0);
  const scoreRef = useRef(0);

  // Dev-only mock -- the real onCheckAnswer hits POST /oa/{attemptId}/section/check,
  // which knows the puzzle's real correctAnswer server-side. This preview has
  // no attemptId/backend session, and SAMPLE_PUZZLES intentionally carries no
  // correctAnswer (matches the real strip_answer() shape), so there's nothing
  // genuine to check against -- this just SIMULATES a plausible correct/wrong
  // split so the running-score bar can be previewed visually. Not real grading.
  const mockCheckAnswer = async (_puzzleId, result) => {
    const isCorrect = !result.timedOut && Array.isArray(result.selected) && Math.random() > 0.4;
    scoreRef.current += isCorrect ? 3 : -1;
    return { correct: isCorrect, pointsAwarded: isCorrect ? 3 : -1, runningScore: scoreRef.current };
  };

  return (
    <div>
      <Header />
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="font-mono text-xs uppercase tracking-widest text-pm-primary-dark mb-1">dev preview · not a real route</div>
        <h1 className="font-display text-2xl font-bold mb-6">Inductive Challenge — full flow preview</h1>

        {completedAnswers ? (
          <div className="pm-card p-6">
            <div className="font-display text-lg font-semibold mb-3">Session complete</div>
            <pre className="text-xs font-mono bg-pm-muted rounded-lg p-4 overflow-auto">
              {JSON.stringify(completedAnswers, null, 2)}
            </pre>
            <button
              className="pm-btn pm-btn-ghost mt-4 text-sm py-2 px-4"
              onClick={() => { setCompletedAnswers(null); setRunKey((k) => k + 1); scoreRef.current = 0; }}
            >
              Restart preview
            </button>
          </div>
        ) : (
          <InductiveChallengeSection
            key={runKey}
            puzzles={SAMPLE_PUZZLES}
            config={SAMPLE_CONFIG}
            onComplete={setCompletedAnswers}
            onCheckAnswer={mockCheckAnswer}
          />
        )}
      </div>
    </div>
  );
}
