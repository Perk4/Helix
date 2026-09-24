## Goal

Make Stage 1 work as Human Gate 1 so a user can review the required inputs, check consent, freeze the manifest, and start the Agent Steps.

## Locked

- The agent cannot start before Gate 1 authorization.
- The authorize action is disabled until the consent checkbox is checked.
- After authorization, files show `Frozen`, the drop zone is hidden, and the primary action becomes disabled.
- This slice may use the seeded demo file list. Real upload, checksums, type checks, and missing-input handling belong to the production wiring ticket.

## Acceptance

- [ ] The Upload view shows the drop zone, file table, pre-checks, consent checkbox, and `Authorize and start agent` action from the reference.
- [ ] The authorize action is disabled until consent is checked.
- [ ] After authorization, the Progress Bar moves to Stage 2, selects Stage 2, resets the action tick, and starts the runner.
- [ ] After authorization, the manifest action reads `Manifest frozen · MANIFEST-HLX-028` and cannot be clicked again.
- [ ] The live region announces that the manifest is frozen and the agent started.
- [ ] Tests cover both the disabled and authorized paths.

## Out of scope

Real upload persistence, checksum validation, server-side manifest freeze, Agent Step activity details, traceability review, approvals, and export remain out of scope.

## Refs

Spec #17; `docs/specifications/helix-v1-ui-redesign.md` · `UI-022` through `UI-027`; `research/HANDOFF.md` §§4, 5.3, 5.4, 7, and 8; `research/helix-e2e-workbench-v1.html` Upload view and `authorize` action.

## Process

Blocked by #18, #19. Blocks #21. One vertical PR.
