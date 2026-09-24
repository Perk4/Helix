## Goal

Show stages 2 through 7 as a live agent run with a run banner, control boundary, activity rows, blocker flags, and pause or resume controls.

## Locked

- The agent runs only between Human Gates and stops at Traceability Review.
- Each Agent Step shows its input, output, summary, and control boundary from the reference content.
- Activity rows move through queued, active, done, and blocker states without using color as the only signal.
- Pause and Resume affect only Agent Steps. They do not pass gates or change release state.
- Past Agent Steps show all actions as done when selected for review.

## Acceptance

- [ ] Stages 2 through 7 share one Agent Step view that renders the correct stage content and four actions.
- [ ] The run banner shows running, paused, and complete states with the correct current action or next gate copy.
- [ ] Pause stops the runner, and Resume continues from the current Agent Step.
- [ ] The validation stage shows blocker actions with a warning icon and `Blocker` tag.
- [ ] The agent stops at Stage 8, sets running false, selects Traceability Review, and announces the stop.
- [ ] A test covers pause, resume, blocker rendering, automatic stop at Gate 2, and review of a past Agent Step.

## Out of scope

Production run events, server-side pause and resume, Traceability Review internals, sign-offs, and export remain out of scope.

## Refs

Spec #17; `docs/specifications/helix-v1-ui-redesign.md` · `UI-028` through `UI-034`; `research/HANDOFF.md` §§4, 5.5, 7, 8, and 10; `research/helix-e2e-workbench-v1.html` `STAGES`, runner, and Agent view rendering.

## Process

Blocked by #20. Blocks #22, #25. One vertical PR.
