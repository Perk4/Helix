## Goal

Replace demo Traceability Review and Review and Export actions with persisted disposition, role sign-off, export, artifact checksum, and download behavior while preserving the v1 interaction model.

## Locked

- `Record demo approvals` is removed from production wiring.
- A disposition requires reason, action, and signer data and persists to the audit trail.
- Role sign-offs come from the configured review flow and remain blocked until prerequisites pass.
- Export calls the backend export command and displays the checksums of the four finished artifacts.
- Export remains separate from approval and never claims FDA acceptance.
- The client renders backend release state and artifact data without recalculating readiness.

## Acceptance

- [ ] Gate 2 opens a disposition form for the blocked rule, persists the disposition through the API, and keeps the result labeled as `Disposition`.
- [ ] Gate 3 renders role-specific sign-off state from the backend and blocks study director approval until prerequisite roles are complete.
- [ ] Export calls the backend command, shows the four artifact checksums returned by the API, and enables downloads for exported artifacts.
- [ ] A stale or missing disposition, missing sign-off, stale approval, or backend-blocked release keeps export disabled with an accessible reason.
- [ ] The full browser workflow verifies API state after disposition, approvals, export, artifact checksums, and download availability.
- [ ] The production path contains no demo timer, fixed reference data, or demo approval shortcut.

## Out of scope

Cancel, rewind, per-section return workflows, FDA submission readiness, and multi-user gate locking beyond the implemented backend review contracts remain out of scope.

## Refs

Spec #17; `docs/specifications/helix-v1-ui-redesign.md` · `UI-071` through `UI-074`; `research/HANDOFF.md` §§5.6, 5.7, 8, 10, and 11; `backend/app/main.py` review and export endpoints; `frontend/src/components/ReportAssembly.tsx`; `frontend/tests/workbench.spec.ts`.

## Process

Blocked by #22, #23, #24, #25, #26. Blocks none. One vertical PR.
