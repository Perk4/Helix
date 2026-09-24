## Goal

From the authenticated Azure URL, complete the synthetic HELIX journey and publish one redacted evidence bundle that proves every displayed step, evaluation, approval, and exported byte.

## Locked

- Use the real deployed frontend, internal backend, PostgreSQL Flexible Server, and Python Codex SDK. A local service, SQLite database, mocked candidate, direct model call, or fake progress event cannot satisfy this slice.
- Start from the frozen synthetic manifest and keep `SYNTHETIC / NOT FOR SUBMISSION` visible in the UI and generated artifacts.
- Exercise Human Gates through the browser. Do not seed passed gates, promotion, approval, or export state directly in the database.
- Validate evidence with a deterministic rerunnable command. A screenshot or agent summary is not proof.
- Redact credentials, cookies, bearer tokens, personal identifiers, and private network details from every retained artifact.
- Pin the evidence bundle to Azure resource identifiers, Container Apps revisions, image digests, database schema version, governed asset hashes, and one Workflow Run.

## Acceptance

- [ ] Playwright signs in as an authorized demo user, authorizes the manifest, starts the Workflow Run, observes real persisted deterministic and Codex steps, reloads, and reaches Traceability Review without losing state.
- [ ] The trace contains resolvable Step Receipts and Trace Artifacts for deterministic validation, template readiness, explicit Skill Invocation, candidate recording, provenance, Skill Qualification, Study Output Evaluation, template conformance, Human Gates, promotion, approval, and export.
- [ ] The browser records the required synthetic disposition and role approvals, then exports and downloads a report whose body-weight content matches the exact promoted candidate and approved hashes.
- [ ] Accessibility and responsive checks cover keyboard-only completion, focus, live announcements, non-color status cues, and a 390 CSS pixel viewport without page-level horizontal scrolling.
- [ ] Failure probes prove that stale approval, conflicting idempotency reuse, missing qualification, unsupported candidate content, and direct backend access cannot pass.
- [ ] The evidence bundle contains redacted receipts, evaluation artifacts, browser screenshots, deployment and image identities, the export manifest, downloaded checksums, and verification output for one run.
- [ ] A deterministic validator recomputes every SHA-256 value, walks every Artifact Edge from frozen source to exported body-weight content, rejects missing or orphaned evidence, and exits successfully in CI.

## Out of scope

Real study data, all-section automation, load certification, formal penetration testing, disaster recovery, electronic signatures, SEND or eCTD validation, and any regulatory or production-readiness claim remain out of scope.

## Refs

Spec #28. `DEMO-001` through `DEMO-010`; `AUTH-001` through `AUTH-009`; `TRACE-001` through `TRACE-012`; `EVAL-001` through `EVAL-008`; `UX-001` through `UX-010`; `AZURE-001` through `AZURE-012`; `PROOF-001` through `PROOF-010`; `docs/architecture/agentic-e2e-demo.md`; ADR-0023, ADR-0024; existing issues #24 and #27.

## Process

Blocked by #24, #32, and #33. Blocks none. One vertical PR and one retained Azure proof run.
