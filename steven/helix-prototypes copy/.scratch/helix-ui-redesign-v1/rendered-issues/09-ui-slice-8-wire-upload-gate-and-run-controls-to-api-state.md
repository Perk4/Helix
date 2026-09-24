## Goal

Replace the fixed demo file list, demo manifest freeze, local runner controls, and client-owned running state with API-backed upload, manifest authorization, pause, and resume behavior.

## Locked

- Real upload state shows progress, checksum, type check, required role, and missing-input state for each required input.
- Manifest authorization is idempotent and starts or resumes the same run on replay.
- Pause and Resume call backend run-control commands, and the UI updates only from server acknowledgement or subsequent run events.
- The agent still cannot start before Gate 1 authorization and cannot pass later Human Gates.
- Client code must remove the production use of fixed `FILES` data and timer-driven state.

## Acceptance

- [ ] Uploading or selecting required files renders per-file progress, checksum, type, role, and validation status returned by the backend.
- [ ] Missing or invalid required inputs keep authorization disabled and show an accessible explanation.
- [ ] Authorizing the manifest records the server manifest identity and starts or resumes the backend run exactly once for an idempotent replay.
- [ ] Pause and Resume call backend commands and render the acknowledged state without advancing progress locally.
- [ ] A reload after authorization shows the frozen manifest and current run state from the API.
- [ ] Tests cover duplicate authorization replay, conflicting replay rejection, pause, resume, missing input, invalid type, and checksum rendering.

## Out of scope

Traceability disposition forms, role-specific sign-off flows, artifact download verification, multi-user locking beyond the run-control contract, cancel, and rewind remain out of scope.

## Refs

Spec #17; `docs/specifications/helix-v1-ui-redesign.md` · `UI-067` through `UI-070`; `research/HANDOFF.md` §§5.4 and 8; `docs/adr/0022-adopt-stage-gated-workspace.md`; `backend/app/main.py` command patterns; `frontend/src/lib/api.ts` command wrappers.

## Process

Blocked by #25. Blocks #27. One vertical PR.
