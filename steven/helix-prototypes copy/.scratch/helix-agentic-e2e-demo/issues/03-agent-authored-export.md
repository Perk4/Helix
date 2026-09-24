## Goal

After traceability review and synthetic approvals, export a report whose body-weight section is the exact qualified Codex-authored Section Draft that the reviewer inspected.

## Locked

- Preserve every run pinned to the current `vertical_slice` package as unpromotable. Promotion permission may appear only in a new, separately qualified package version.
- Shared deterministic code owns promotion. Codex, Promptfoo, the browser, and a reviewer cannot set promotion status directly.
- Promotion requires no hard blocker, current dispositions for every review-required result, passing provenance and template conformance, passing skill qualification, and package permission.
- Bind review decisions and Final Study Approval to exact candidate, Section Draft, scaffold, dependency, and release-candidate hashes.
- Export selects only the approved hashes. It invokes no model, performs no scientific calculation, and never packages a Review Scaffold Revision.

## Acceptance

- [ ] A newly qualified body-weight package version produces one promoted Section Draft that references the exact candidate, provenance, conformance, evaluation, disposition, and dependency hashes.
- [ ] The prior `vertical_slice` package and every run pinned to it remain unpromotable and byte-for-byte retrievable.
- [ ] Review and Export shows the promoted body-weight content with its Workflow Trace and provenance before any synthetic sign-off can bind to it.
- [ ] Final Study Approval names the exact release-candidate manifest and promoted Section Draft hash, and any covered change makes the approval stale.
- [ ] Export contains the exact approved body-weight text and excludes every candidate, scaffold, stale artifact, and unapproved replacement.
- [ ] Downloaded artifact bytes match the approval, export receipt, and displayed SHA-256 values.
- [ ] Tests prove that an agent-authored promotion flag, qualitative pass, stale disposition, changed hash, replay, or export-time agent call cannot bypass the path.

## Out of scope

Automation of the other report sections, real electronic signatures, submission-grade publishing, source corrections, superseding runs beyond existing contracts, and regulator acceptance remain out of scope.

## Refs

Spec #28. `DEMO-005` through `DEMO-009`; `AUTH-001` through `AUTH-006`; `TRACE-004`, `TRACE-006`, `TRACE-012`; `UX-004` through `UX-006`; `PROOF-007`, `PROOF-010`; `docs/architecture/agentic-e2e-demo.md`; ADR-0012, ADR-0013, ADR-0015, ADR-0017, ADR-0023; existing issues #7, #8, #11, #12, and #27.

## Process

Blocked by #12, #27, and #31. Blocks the deployed golden-path proof. One vertical PR.
