## Goal

Harden the redesigned parity milestone so keyboard, screen-reader, desktop, tablet, mobile, light theme, and dark theme users can complete the full journey.

## Locked

- Every interactive element is a real button, input, or label.
- Status is never shown by color alone.
- A polite live region announces agent start, gate stops, pause, resume, gate approvals, and export.
- The page has no horizontal page scroll at 390 px. The Progress Bar may scroll inside itself.
- Reduced motion slows spinners and avoids extra animation.

## Acceptance

- [ ] Axe reports no serious or critical accessibility violations for the redesigned journey.
- [ ] A keyboard-only test completes authorization, pause, resume, disposition, approvals, export, and past-stage review.
- [ ] The full journey passes in light and dark themes.
- [ ] Responsive tests cover desktop, 1100 px, and 390 px widths with no horizontal page scroll at 390 px.
- [ ] Focus-visible outlines appear for Progress Bar stages, accordion rows, gate actions, and export controls.
- [ ] Playwright screenshots capture the initial, Traceability Review, Review and Export, and exported states.

## Out of scope

Production run events, real upload APIs, server-side pause and resume, e-signature flows, and checksum verification remain out of scope.

## Refs

Spec #17; `docs/specifications/helix-v1-ui-redesign.md` · `UI-051` through `UI-058`; `research/HANDOFF.md` §§6, 7, and 10; `research/helix-e2e-workbench-v1.html` responsive styles and live region behavior.

## Process

Blocked by #23. Blocks #25, #26, #27. One vertical PR.
