import type { ParityScreen } from "../types";

// OWNER: Lane D (#23 review/approval/export/downloads + demo-unqualified flag).
//
// Human Gate 3 is reachable only after a human freeze, validation, and traceability
// dispositions, so a fresh seed (the kit's throwaway server) never shows it. "Ours" is the
// lane-D fixture route /parity/review (HELIX_PARITY_FIXTURES=1 only; display state captured
// from a real review-export workspace, demo flag off). The same selectors also work against a
// live server driven to review-export with path "/".

const masks = {
  // Server report text and identities differ from the reference copy by design (#23 renders
  // WorkspaceResponse.report, per-role controls replace "Record demo approvals", and the
  // Final Study Approval row shows the server manifest hash).
  reference: [".hx-doc", ".hx-signoff", ".hx-btn.primary"],
  ours: ['[data-testid="draft-canvas"]', '[data-testid="sign-offs"] .hx-signoff', '[data-testid="export-panel"]', '[data-testid="review-message"]'],
};

export const laneDScreens: ParityScreen[] = [
  {
    id: "review-export-light",
    title: "Human Gate 3 Review and export (#23)",
    lane: "D",
    issue: "#23",
    status: "report-only",
    colorScheme: "light",
    reference: { path: "?stage=8", selector: "#hx-panel", mask: masks.reference },
    ours: {
      path: "/parity/review",
      selector: '[data-testid="review-stage"]',
      waitFor: '[data-testid="review-stage"]',
      mask: masks.ours,
    },
    notes:
      "Report-only: server report copy and section titles differ from the reference copy, and the canvas is taller. Masked: server report canvas, per-role sign-off rows, and export controls, which #23 changes on purpose.",
  },
  {
    id: "review-export-dark",
    title: "Human Gate 3 Review and export, dark (#23)",
    lane: "D",
    issue: "#23",
    status: "report-only",
    colorScheme: "dark",
    reference: { path: "?stage=8", selector: "#hx-panel", mask: masks.reference },
    ours: {
      path: "/parity/review",
      selector: '[data-testid="review-stage"]',
      waitFor: '[data-testid="review-stage"]',
      mask: masks.ours,
    },
    notes: "Same as review-export-light, dark scheme.",
  },
];
