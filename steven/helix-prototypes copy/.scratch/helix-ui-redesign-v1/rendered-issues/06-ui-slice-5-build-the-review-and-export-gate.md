## Goal

Make Stage 9 work as Human Gate 3 so a reviewer can inspect the draft section, record role sign-offs, and export the package through a separate explicit action.

## Locked

- Export is disabled until required sign-offs are recorded.
- Export remains a separate action after sign-off. Recording approvals does not export.
- The release pill changes only through blocked, ready for export, and package exported states.
- The prototype must never state or imply FDA approval.
- The demo approval action is allowed only in the parity milestone and must be removed during production wiring.

## Acceptance

- [ ] The Review and Export view renders the section list, active draft document, provenance readout, sign-offs card, and export card from the reference.
- [ ] Before sign-off, export is disabled and the release pill remains blocked.
- [ ] Recording demo approvals marks the sign-off rows signed and changes the release pill to ready for export.
- [ ] Export changes the journey to 9 of 9, changes the pill to package exported, updates the provenance readout, and announces completion.
- [ ] Selecting a past Agent Step after export shows completed actions and blocker flags.
- [ ] Tests cover approvals, export, release pill copy, 100 percent progress, and no FDA approval claim.

## Out of scope

Production e-signature flows, real artifact checksums, download verification, per-section approve or return, cancel, and rewind remain out of scope.

## Refs

Spec #17; `docs/specifications/helix-v1-ui-redesign.md` · `UI-043` through `UI-050`; `research/HANDOFF.md` §§4, 5.7, 7, 8, 10, and 11; `research/helix-e2e-workbench-v1.html` Review view, release pill, and export action.

## Process

Blocked by #22. Blocks #24, #27. One vertical PR.
