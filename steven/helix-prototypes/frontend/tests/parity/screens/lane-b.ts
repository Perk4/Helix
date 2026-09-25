import type { ParityScreen } from "../types";

// OWNER: Lane B (#21 Agent Steps + governed drafting).
//
// Our side needs a server state past Human gate 1: the journey projection must report an
// Agent Step as current, and the page opens the current stage. The self-started
// verify-parity.sh backend is freshly seeded (Upload current), so these screens stay
// `pending` there. Run them against a lane server whose Pinned Run is frozen:
//   HELIX_PARITY_BASE_URL=http://127.0.0.1:3032 HELIX_PARITY_INCLUDE_PENDING=1 \
//   HELIX_PARITY_ONLY=agent-run-banner-light,agent-stage-card-light,agent-activity-card-light,agent-step-light \
//   ./scripts/verify-parity.sh
// After a freeze the server reports Validate (stage 5) current, which is the reference
// `?stage=4`. Note: a local freeze is refused with `invalid_package_qualification` until
// the agentic packages are qualified (or Lane D's demo-unqualified flag lands), so today
// even a lane server cannot reach this state. A step-0 `/parity?fixture=agent` fixture
// would let these run in CI (escalated: src/app/parity/** is shared).
//
// Deliberate, documented differences (masked):
// - Pause/Resume are disabled until #26 (the button is masked on both sides).
// - Activity rows come from the server projection, not the reference's 4 fixed actions.
// - Our stage card adds governed commands, the polite live region, and receipt evidence
//   below the control boundary; only the reference-shaped top of the card is compared.
// - The banner says "Agent waiting" (no auto-run exists) where the reference says
//   "Agent paused"; "Agent paused" is shown only when the server reports a paused run.

const REF = "?stage=4";
const WAIT = '[data-testid="agent-stage-view"][data-stage="validate"]';

export const laneBScreens: ParityScreen[] = [
  {
    id: "agent-run-banner-light",
    title: "Agent Step run banner, Validate current (#21)",
    lane: "B",
    issue: "#21",
    status: "pending",
    colorScheme: "light",
    reference: { path: REF, selector: "#hx-panel .hx-banner", mask: [".hx-banner-right .hx-btn"] },
    ours: {
      path: "/",
      selector: '[data-testid="agent-run-banner"]',
      waitFor: WAIT,
      mask: ['[data-testid="agent-pause"]'],
      replaceText: [{ selector: '[data-testid="agent-run-banner"] .hx-kicker', text: "Agent paused · Stage 5 of 9" }],
    },
    notes:
      "replaceText maps our honest 'Agent waiting' kicker onto the reference 'Agent paused' copy so the diff measures layout and tokens only; the copy difference is deliberate (no auto-run until #25/#26).",
  },
  {
    id: "agent-stage-card-light",
    title: "Agent Step stage card (summary, Input -> Output, control boundary) (#21)",
    lane: "B",
    issue: "#21",
    status: "pending",
    colorScheme: "light",
    reference: { path: REF, selector: "#hx-panel .g-agent > section:first-child" },
    ours: {
      path: "/",
      selector: '[data-testid="agent-stage-card"]',
      waitFor: WAIT,
      css: '[data-testid="agent-stage-card"] > :nth-child(n+5) { display: none !important; }',
      replaceText: [{ selector: '[data-testid="agent-stage-chip"]', text: "Paused" }],
    },
    notes:
      "Our card continues below the control boundary with governed commands, the live region, and receipt evidence (not in the reference); css hides those children so the reference-shaped top is compared. The chip text maps 'Current' onto the reference 'Paused'.",
  },
  {
    id: "agent-activity-card-light",
    title: "Agent activity card header and row chrome (#21)",
    lane: "B",
    issue: "#21",
    status: "pending",
    colorScheme: "light",
    reference: { path: REF, selector: "#hx-panel .g-agent > section:last-child", mask: ["ol"] },
    ours: {
      path: "/",
      selector: '[data-testid="agent-activity-card"]',
      waitFor: WAIT,
      mask: ['[data-testid="agent-activity"]', '[data-testid="agent-activity-count"]'],
    },
    notes: "Rows and the count come from the server projection (not the reference's fixed 4 actions); they are masked.",
  },
  {
    id: "agent-step-light",
    title: "Agent Step view, whole panel, Validate current (#21)",
    lane: "B",
    issue: "#21",
    status: "pending",
    colorScheme: "light",
    reference: { path: REF, selector: "#hx-panel", mask: [".hx-banner-right .hx-btn", "ol"] },
    ours: {
      path: "/",
      selector: '[data-testid="agent-stage-view"]',
      waitFor: WAIT,
      mask: ['[data-testid="agent-pause"]', '[data-testid="agent-activity"]'],
    },
    notes: "Whole-panel report only: our stage card is taller (commands and evidence), so the size difference is expected.",
  },
];
