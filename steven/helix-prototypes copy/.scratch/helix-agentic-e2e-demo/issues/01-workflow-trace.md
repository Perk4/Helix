## Goal

When a scientist starts the governed run, show one reload-safe Workflow Trace from deterministic body-weight validation through the Codex candidate and the next Human Gate.

## Locked

- Model the path with `WorkflowRun`, immutable `StepReceipt`, content-addressed `TraceArtifact`, and typed `ArtifactEdge` records.
- Keep one canonical trace writer in the backend. Do not add a third mutable event history beside the aggregate and relational audit rows.
- Return a Workflow Run receipt before long execution continues. Persist progress before sending it to the UI.
- Use real Codex turn notifications for agent progress. Do not use a production timer or invented action text.
- Pause only at a safe step boundary. Interruption preserves the current attempt, and resume creates a new immutable attempt with unchanged governed inputs.
- Keep the nine-stage Workspace Journey as the top-level model. Fine-grained receipts live inside its Agent Steps.

## Acceptance

- [ ] Starting the run returns one Workflow Run identity and the UI renders ordered persisted rows for validation, template readiness, explicit Skill Invocation, candidate recording, and the reached Human Gate.
- [ ] Every row shows actor kind, authority class, status, attempt, timestamps, exact input and output artifact links, relevant versions and hashes, and a structured failure when present.
- [ ] Every displayed artifact link resolves through the API, and recomputing its SHA-256 digest matches the stored identity.
- [ ] Reloading the browser or restarting the backend restores the same run and trace from PostgreSQL. Exact command replay creates no duplicate step, artifact, or Codex turn.
- [ ] Public Codex turn notifications appear incrementally and the terminal Step Receipt records the thread, turn, skill, envelope, and candidate identities.
- [ ] Pausing during an active turn records an interrupted attempt. Resume creates the next attempt with the same pinned inputs and no rewritten history.
- [ ] Backend and browser tests prove that neither client state nor Codex output can advance a Human Gate or assign deterministic authority.

## Out of scope

Skill qualification policy, study-output evaluation content, candidate promotion, final approval, export changes, and Azure infrastructure remain out of scope.

## Refs

Spec #28. `AUTH-001`, `AUTH-002`, `AUTH-005`, `AUTH-006`; `TRACE-001` through `TRACE-012`; `UX-001` through `UX-008`; `PROOF-003`, `PROOF-004`, `PROOF-010`; `docs/architecture/agentic-e2e-demo.md`; ADR-0022, ADR-0023; existing issues #3, #4, #17, and #25.

## Process

Blocked by #29, #3, #4, and #25. Blocks the evaluation-artifact slice and the deployed proof. One vertical PR.
