## Goal

Give the one-page workspace a tested nine-stage reducer and Progress Bar that selects reached stages without letting the user or agent skip Human Gates.

## Locked

- Encode the handoff transition table and invariants in one reducer or equivalent state boundary.
- The Progress Bar is the only navigation for the redesigned workspace.
- Clicking a reached stage changes only the selected view. It never changes progress.
- Future stages are disabled, and the agent never passes a Human Gate.
- Gate nodes are rounded squares with a person icon. Agent nodes are circles with stage numbers or running state.

## Acceptance

- [ ] Reducer tests cover every transition row from `authorize` through `export`.
- [ ] Reducer tests cover all six governance invariants from the handoff.
- [ ] Progress Bar tests cover `current` values from 0 through 9, including done, current, selected, paused, awaiting, and pending states.
- [ ] Future stages cannot be clicked, and clicking a past stage changes only the selected stage.
- [ ] The current stage uses `aria-current="step"`, and each stage button has an accessible label that includes its status.
- [ ] The track is green through completed progress and neutral after the current stage.

## Out of scope

Stage view content, file upload behavior, live agent actions, traceability accordion, approvals, export, and backend production events remain out of scope.

## Refs

Spec #17; `docs/specifications/helix-v1-ui-redesign.md` · `UI-001` through `UI-013`, `UI-014` through `UI-021`; `research/HANDOFF.md` §§3, 4, 5.2, and 7; `research/helix-e2e-workbench-v1.html` `State`, `Transitions`, and stepper rendering.

## Process

Blocked by #18. Blocks #20, #21, #22, #23. One vertical PR.
