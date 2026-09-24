## Goal

Make Stage 8 work as Human Gate 2 so a reviewer can inspect rule evidence, record a blocker disposition, and continue only after the disposition exists.

## Locked

- Only one validation rule row is open at a time.
- The Continue action is disabled until the blocked rule has a disposition.
- A blocker with a recorded disposition changes to `Disposition`. It never becomes `Pass`.
- The five-step traceability flow shows Frozen source, Normalized facts, Transform, Validated claim, and Report field.
- The implementation matches the reference claim first and keeps the data shape ready for more claims later.

## Acceptance

- [ ] The gate banner, claim header, summary chips, accordion table, and rule rows match the reference behavior.
- [ ] Each row button uses `aria-expanded` and `aria-controls`, and only one row can be open.
- [ ] Opening a rule shows the five-step traceability flow with highlighted checked, blocked, or disposition steps.
- [ ] The blocked row shows `Record disposition` only while Gate 2 is active and unresolved.
- [ ] After disposition, the badge reads `Disposition`, the note shows the disposition text, and Continue is enabled.
- [ ] Continuing moves to Stage 9, selects Review and Export, and announces Traceability Review approval.

## Out of scope

Multi-claim grouping, production disposition forms, server persistence, Review and Export internals, and export remain out of scope.

## Refs

Spec #17; `docs/specifications/helix-v1-ui-redesign.md` · `UI-035` through `UI-042`; `research/HANDOFF.md` §§4, 5.3, 5.6, 7, 8, 10, and 11; `research/helix-e2e-workbench-v1.html` Traceability view and `RULES` data.

## Process

Blocked by #21. Blocks #23, #27. One vertical PR.
