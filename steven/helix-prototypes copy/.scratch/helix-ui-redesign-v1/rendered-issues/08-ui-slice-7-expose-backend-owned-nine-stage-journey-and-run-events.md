## Goal

Replace demo-only progress authority with a backend-owned nine-stage journey contract and recorded run events that the UI can render without simulating production progress.

## Locked

- The backend is authoritative for current stage, selected allowed history, running state, gate stops, and release status.
- Production progress comes from recorded run events or a server-owned equivalent, not a client timer.
- The contract uses the v1 nine-stage model with Human Gates and Agent Steps.
- The client may render state and request controls. It must not derive release readiness or pass gates locally.
- Generated TypeScript API types must match the backend schema before frontend production wiring lands.

## Acceptance

- [ ] The workspace response or run endpoint exposes the nine v1 stages with type, short label, name, status, and selected-view eligibility.
- [ ] Run events represent stage started, action started, action finished with optional flag, stage finished, run paused, and gate reached, or an explicitly equivalent server-owned model.
- [ ] The current backend ten-stage or hybrid-owner model no longer leaks into the redesigned Progress Bar.
- [ ] Backend tests prove that agent progress stops at Human Gates and cannot pass them without gate commands.
- [ ] Type generation updates the frontend contract, and typecheck fails if the UI reads the old stage shape.
- [ ] A Playwright or API test proves that reloading the page restores progress from server state, not client memory.

## Out of scope

Real file upload, pause or resume controls, disposition forms, sign-off commands, export download verification, and visual parity polish remain out of scope.

## Refs

Spec #17; `docs/specifications/helix-v1-ui-redesign.md` · `UI-059` through `UI-066`; `research/HANDOFF.md` §§4, 5.5, 8, and 11; `backend/app/service.py` `build_stages`; `backend/app/schemas.py` `Stage`; `frontend/src/lib/types.ts`.

## Process

Blocked by #21, #24. Blocks #26, #27. One vertical PR.
