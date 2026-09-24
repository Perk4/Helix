# Grill with docs for the HELIX v1 UI redesign

Source documents:

- `research/HANDOFF.md`.
- `research/helix-e2e-workbench-v1.html`.
- `CONTEXT.md`.
- `docs/architecture/helix-prototype.md`.

## Resolved questions

1. Should the redesign preserve the v0 tabs and only restyle them?

   Recommended answer. No. The reference build makes the Progress Bar the only navigation. Keeping tabs would keep traceability and report review as separate modes, which is the old behavior.

   Resolution. The phase replaces the tabs with one stage-gated Workspace Journey.

2. Should the client own progress state during production use?

   Recommended answer. No. The reference uses local state only as a demo. Production must render the backend run record, run events, gate decisions, dispositions, approvals, and export receipt.

   Resolution. Early UI tickets may use a reducer to match the reference. Later wiring tickets replace the demo runner and fixed file list with backend-owned state.

3. Should Human Gates and Agent Steps be separate domain terms?

   Recommended answer. Yes. They are the core product distinction. The agent may work between gates, but only a person passes a gate.

   Resolution. `CONTEXT.md` now defines Workspace Journey, Human Gate, Agent Step, Traceability Review, and Review and Export Gate.

4. Should Gate 2 group many claims by section in the first implementation?

   Recommended answer. No for the parity milestone. The reference source of truth shows one claim with four rules. The production contract should not prevent future grouping by claim and section.

   Resolution. The Traceability Review ticket implements the reference claim first and locks the accordion, disposition, and flow behavior. Production wiring keeps the data shape open for more claims.

5. Should Gate 3 include per-section approve and return actions?

   Recommended answer. No for this phase. The reference uses role sign-offs and a separate export action. Per-section return is adjacent workflow design.

   Resolution. The Review and Export Gate uses global role sign-offs, the active section view, provenance inspection, and explicit export.

6. Should the user be able to cancel or rewind an agent run?

   Recommended answer. No. The reference only defines pause and resume. Cancel and rewind would need backend semantics, audit rules, and stale-state handling.

   Resolution. Pause and resume are in scope. Cancel, rewind, and send back are out of scope.

7. What is the highest testing seam?

   Recommended answer. Use one Playwright journey test as the primary seam. Add reducer unit tests for the transition table and invariants because those are cheaper and catch state drift early.

   Resolution. The tickets require reducer coverage for transitions, Playwright coverage for the full journey, accessibility checks, and live wiring checks when backend events replace the demo runner.

8. Should the style migration be a broad visual refactor or incremental slices?

   Recommended answer. Incremental slices. The first slice installs tokens, fonts, shell, and removes tabs. Later slices make each stage group work.

   Resolution. Tickets are sequenced so every slice is demoable and preserves a verifiable state.

## Decisions recorded elsewhere

- `CONTEXT.md` records the UI glossary terms.
- `docs/adr/0022-adopt-stage-gated-workspace.md` records the stage-gated workspace decision.
