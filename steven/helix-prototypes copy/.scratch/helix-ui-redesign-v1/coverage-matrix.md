# HELIX v1 UI redesign ticket coverage matrix

## Source requirements

| Source requirement | Covered by |
|---|---|
| One page replaces three v0 tabs. | UI SLICE 0, UI SLICE 1 |
| Progress Bar is the only navigation. | UI SLICE 1 |
| Nine stages with three Human Gates and six Agent Steps. | UI SLICE 1, UI SLICE 7 |
| Gate 1 uploads and authorizes inputs. | UI SLICE 2, UI SLICE 8 |
| Agent Steps run by themselves between gates. | UI SLICE 3, UI SLICE 7 |
| Pause and Resume are available during Agent Steps. | UI SLICE 3, UI SLICE 8 |
| Agent stops at each Human Gate. | UI SLICE 1, UI SLICE 3, UI SLICE 4, UI SLICE 5, UI SLICE 7 |
| Gate 2 uses a rule accordion with a five-step traceability flow. | UI SLICE 4, UI SLICE 9 |
| Blocked validation result becomes Disposition, not Pass. | UI SLICE 4, UI SLICE 9 |
| Gate 3 uses role sign-offs and explicit export. | UI SLICE 5, UI SLICE 9 |
| Export stays separate from approval. | UI SLICE 5, UI SLICE 9 |
| Clinical teal theme, IBM Plex fonts, `light-dark()` tokens, SVG icons. | UI SLICE 0, UI SLICE 6 |
| Accessibility requirements from the handoff. | UI SLICE 1, UI SLICE 2, UI SLICE 3, UI SLICE 4, UI SLICE 5, UI SLICE 6 |
| Demo runner must become production run events. | UI SLICE 7, UI SLICE 8 |
| Fixed file list must become production upload state. | UI SLICE 8 |
| Demo disposition must become a persisted disposition form. | UI SLICE 9 |
| Demo approvals must be removed. | UI SLICE 9 |
| Export must call the API and show checksums. | UI SLICE 9 |
| Full e2e script from the handoff. | UI SLICE 6, UI SLICE 9 |

## ADR and glossary coverage

| Domain decision or term | Covered by |
|---|---|
| `Workspace Journey`. | UI SLICE 0, UI SLICE 1, UI SLICE 7 |
| `Human Gate`. | UI SLICE 1, UI SLICE 2, UI SLICE 4, UI SLICE 5, UI SLICE 7 |
| `Agent Step`. | UI SLICE 1, UI SLICE 3, UI SLICE 7, UI SLICE 8 |
| `Traceability Review`. | UI SLICE 4, UI SLICE 9 |
| `Review and Export Gate`. | UI SLICE 5, UI SLICE 9 |
| ADR-0022 stage-gated workspace over tabs. | UI SLICE 0, UI SLICE 1 |
| Backend remains authoritative for production state. | UI SLICE 7, UI SLICE 8, UI SLICE 9 |

## Dependency edges

| Ticket | Blocked by | Blocks |
|---|---|---|
| UI SLICE 0 | None | UI SLICE 1, UI SLICE 2 |
| UI SLICE 1 | UI SLICE 0 | UI SLICE 2, UI SLICE 3, UI SLICE 4, UI SLICE 5 |
| UI SLICE 2 | UI SLICE 0, UI SLICE 1 | UI SLICE 3 |
| UI SLICE 3 | UI SLICE 2 | UI SLICE 4, UI SLICE 7 |
| UI SLICE 4 | UI SLICE 3 | UI SLICE 5, UI SLICE 9 |
| UI SLICE 5 | UI SLICE 4 | UI SLICE 6, UI SLICE 9 |
| UI SLICE 6 | UI SLICE 5 | UI SLICE 7, UI SLICE 8, UI SLICE 9 |
| UI SLICE 7 | UI SLICE 3, UI SLICE 6 | UI SLICE 8, UI SLICE 9 |
| UI SLICE 8 | UI SLICE 7 | UI SLICE 9 |
| UI SLICE 9 | UI SLICE 4, UI SLICE 5, UI SLICE 6, UI SLICE 7, UI SLICE 8 | None |

## Verification obligations

| Verification | Covered by |
|---|---|
| Reducer transition and invariant tests. | UI SLICE 1 |
| Progress Bar state tests for `current` 0 through 9. | UI SLICE 1 |
| Upload authorization tests. | UI SLICE 2, UI SLICE 8 |
| Pause, resume, blocker, and gate-stop tests. | UI SLICE 3, UI SLICE 8 |
| Accordion and disposition tests. | UI SLICE 4, UI SLICE 9 |
| Approval and export tests. | UI SLICE 5, UI SLICE 9 |
| Axe accessibility, keyboard-only, responsive, and theme tests. | UI SLICE 6 |
| API-owned journey and reload persistence tests. | UI SLICE 7 |
| Full browser workflow with API state and downloads. | UI SLICE 9 |
