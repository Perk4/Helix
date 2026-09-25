import type { ParityScreen } from "../types";

// OWNER: Lane C (#22 Traceability Review gate).
//
// Stays "pending": the seeded synthetic backend the kit starts sits at Upload and cannot
// reach Gate 2 without a qualified freeze and a Codex section run, so `/` never renders
// the Traceability view in a default run. Lane C captures it with
// HELIX_PARITY_INCLUDE_PENDING=1 HELIX_PARITY_ONLY=traceability-gate-light against its own
// servers, whose API journey is projected to Gate 2 over the live dispositions (see the
// PR evidence). Enforcing needs a step-0 Gate 2 fixture or seed (escalated in the PR).

export const laneCScreens: ParityScreen[] = [
  {
    id: "traceability-gate-light",
    title: "Human Gate 2 Traceability Review (#22)",
    lane: "C",
    issue: "#22",
    status: "pending",
    colorScheme: "light",
    reference: { path: "?stage=7", selector: "#hx-panel" },
    ours: {
      path: "/",
      selector: '[data-testid="traceability-gate"]',
      waitFor: '[data-testid="trace-flow"]',
    },
    notes:
      "Banner, claim header, chips, accordion and five-step flow match the reference structure. Row content is server data (2 rules for C-BW-HIGH: VR-003 pass, VR-004 blocked) instead of the reference's 4 static rules, and the flow shows real record pointers, so the rule rows and flow text differ by design.",
  },
];
