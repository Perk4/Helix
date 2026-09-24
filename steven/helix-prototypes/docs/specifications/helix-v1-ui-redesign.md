# HELIX v1 stage-gated UI redesign spec

## Problem statement

The current workbench splits the study journey, evidence chain, and report assembly into three tabs. That split makes the user choose a mode instead of following study progress. It also makes traceability review feel optional, even though the product model treats human gates as required control points.

Scientists, reviewers, and study directors need one workspace that shows where the study is, what the agent is doing, why it stopped, and what a person must do next. The redesign must keep the core HELIX governance rule visible. The agent can prepare work, but it cannot pass Human Gates.

## Solution

Replace the tabbed workbench with a single Workspace Journey controlled by a nine-stage Progress Bar. Stage 1 is upload and authorization. Stages 2 through 7 are Agent Steps. Stage 8 is Traceability Review. Stage 9 is Review and Export.

The first delivery matches the v1 reference build. It uses the clinical teal theme, IBM Plex typography, the new stage shapes, the Human Gate banner, the upload authorization view, the live Agent Step view, the traceability accordion, and the Review and Export Gate. Later delivery replaces demo-only state with backend-owned run events, real upload state, persisted dispositions, role sign-offs, and export receipts.

## User stories

1. As a study owner, I want one visible journey, so that I always know what the study needs next.
2. As a study owner, I want the Progress Bar to be the only navigation, so that I do not have to choose between disconnected tabs.
3. As a study owner, I want future stages disabled, so that I cannot jump ahead of the governed process.
4. As a study owner, I want to review completed stages, so that I can understand prior agent work without changing progress.
5. As a study owner, I want to authorize the manifest before the agent starts, so that no unapproved input enters the run.
6. As a study owner, I want the file list to show frozen status after authorization, so that I know the input boundary changed.
7. As a scientist, I want the agent actions to appear live, so that I can tell whether parsing, resolution, extraction, validation, drafting, and provenance compilation are moving.
8. As a scientist, I want Pause and Resume controls during Agent Steps, so that I can stop and continue an agent run without passing a Human Gate.
9. As a scientist, I want each Agent Step to show input, output, and control boundary, so that I can see what the agent may and may not do.
10. As a scientist, I want blocker actions to stand out in the activity list, so that failures are not hidden in completed automation.
11. As a reviewer, I want the agent to stop automatically at Traceability Review, so that I must review evidence before report review starts.
12. As a reviewer, I want validation rules in an accordion table, so that I can inspect one rule without losing the whole claim context.
13. As a reviewer, I want each rule to show the five-step traceability flow, so that I can follow the source-to-report path.
14. As a reviewer, I want blocked flow steps to be highlighted with text and icons, so that status is not communicated by color alone.
15. As a reviewer, I want the continue button disabled until a disposition exists, so that unresolved blockers cannot be skipped.
16. As a reviewer, I want the disposition to preserve the blocker as a disposition instead of a pass, so that the audit trail stays honest.
17. As a pathologist, I want the Review and Export Gate to show the active report section, so that I can review the draft in context.
18. As a pathologist, I want a provenance readout beside the draft, so that I can inspect evidence edges before sign-off.
19. As a Quality Assurance Unit reviewer, I want sign-offs to show pending and signed states, so that release readiness is clear.
20. As a study director, I want export disabled until sign-offs are complete, so that final export remains a separate deliberate action.
21. As a study director, I want the release pill to change from blocked to ready to exported, so that the final state is visible everywhere.
22. As a study director, I want the export copy to avoid FDA approval claims, so that the prototype stays within its regulatory boundary.
23. As a keyboard user, I want every control to be reachable and labeled, so that I can complete the full journey without a mouse.
24. As a screen-reader user, I want polite announcements for gate changes and export, so that progress changes are not silent.
25. As a mobile reviewer, I want the page to work at narrow widths, so that I can review status without horizontal page scroll.
26. As a dark-mode user, I want the same states to remain legible, so that review does not depend on a theme preference.
27. As a frontend maintainer, I want the stage transition model isolated in one reducer, so that future production wiring does not scatter state rules.
28. As a backend maintainer, I want the production UI to render backend-owned run state, so that the client does not derive release authority.
29. As a test owner, I want one full journey test, so that regressions in the user path fail at the highest useful seam.
30. As a product reviewer, I want screenshots of the reference states, so that visual drift is easy to compare during implementation.

## Implementation decisions

- The redesign uses a Workspace Journey instead of v0 tabs.
- The Progress Bar owns navigation. Clicking a reached stage changes only the selected view. It does not change progress.
- The journey has nine stages. Upload, Traceability Review, and Review and Export are Human Gates. Parse, Resolve, Extract, Validate, Draft, and Provenance are Agent Steps.
- The initial UI parity work may use a reducer and timer to match the reference build. Production wiring must replace the timer with backend run events and server acknowledgements.
- The reducer must encode the transition table and invariants from the handoff.
- Gate 1 starts the agent only after authorization. The demo can render the seeded file list, but production wiring must use real upload status, checksums, type checks, and missing-input state.
- Gate 2 implements the reference claim first. The data shape should allow later grouping by claim and section without changing the interaction contract.
- A validation blocker cannot become a pass. The UI must show a disposition state when a reviewer records a disposition.
- Gate 3 keeps role sign-offs and export as separate actions. It does not add per-section approve, return, cancel, or rewind controls in this phase.
- The clinical teal theme uses CSS custom properties and `light-dark()` tokens. Components must not hard-code reference colors outside tokens.
- IBM Plex Sans is the UI font. IBM Plex Mono is for identifiers and pointers. Georgia is only for draft report body text.
- Inline stroke SVG icons replace emoji.
- Production wiring must keep the backend authoritative for stage progress, release status, dispositions, approvals, export readiness, and artifact checksums.

## Testing decisions

- The highest seam is a Playwright journey test that starts at upload, authorizes the manifest, pauses and resumes the agent, stops at Traceability Review, records a disposition, records approvals, exports, and reviews a past Agent Step.
- Reducer unit tests must cover each transition row and each invariant from the handoff.
- Progress Bar tests must cover every `current` value from 0 through 9, gate and agent node shapes, disabled future stages, selected-stage review, and `aria-current`.
- Accessibility checks must include axe serious and critical violations, keyboard-only completion, live-region announcements, focus-visible outlines, and non-color status cues.
- Responsive checks must cover desktop, 1100 px, and 390 px widths. The page must avoid horizontal page scroll at 390 px, with only the Progress Bar scrolling within itself.
- Production wiring tests must prove that run events, pause and resume, upload freeze, dispositions, approvals, export, and artifact checksums come from API state rather than client simulation.
- Existing workbench tests remain useful prior art because they drive the full validation-to-export flow and assert backend release state.

## Out of scope

- Real regulatory submission readiness.
- FDA approval claims.
- Canceling an agent run.
- Sending a run back to an earlier stage.
- Per-section approve or return workflows.
- Multi-user locking at gates beyond the backend contracts already available or explicitly added in production wiring.
- Redesigning the scientific validation rules, report template content, or Section Agent runtime.
- Expanding Gate 2 beyond the reference claim before the parity milestone.

## Further notes

The reference build is the source of truth for layout, copy, states, and behavior. If the handoff and reference build disagree, the reference build wins.

Requirement IDs used by tickets:

- `UI-001` through `UI-006`. Stage-gated information architecture.
- `UI-007` through `UI-013`. Reducer state, transitions, and invariants.
- `UI-014` through `UI-021`. Design tokens, typography, shell, and Progress Bar.
- `UI-022` through `UI-027`. Upload and authorization gate.
- `UI-028` through `UI-034`. Agent Step activity, pause, resume, and control boundaries.
- `UI-035` through `UI-042`. Traceability Review and disposition behavior.
- `UI-043` through `UI-050`. Review and Export Gate.
- `UI-051` through `UI-058`. Accessibility, responsive, and full-journey testing.
- `UI-059` through `UI-066`. Production run events and controls.
- `UI-067` through `UI-074`. Production upload, sign-off, export, and checksum wiring.

Source documents:

- `research/HANDOFF.md`.
- `research/helix-e2e-workbench-v1.html`.
- `.scratch/helix-ui-redesign-v1/grill-with-docs.md`.
- `docs/adr/0022-adopt-stage-gated-workspace.md`.
