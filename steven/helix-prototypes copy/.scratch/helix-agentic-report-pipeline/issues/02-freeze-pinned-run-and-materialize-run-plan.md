# 02: Freeze an immutable Pinned Run and materialize its Run Plan

**What to build:** An authorized user can freeze a manifest, receive an immutable Pinned Run and schema-valid Run Plan fingerprint, and inspect the exact pinned governance identity in the workspace. Repeating the same request resumes the existing run; changed inputs or governed versions create a distinct run rather than mutating history.

**Blocked by:** 01: Prove the frontend-triggered Codex SDK section run.

**Status:** ready-for-agent

- [ ] A manifest entry that is unlocked, lacks authorization, or does not match its stored-byte checksum is rejected before a run is created.
- [ ] Study Type Resolution uses pinned protocol fields and a versioned mapping; an unknown or ambiguous result blocks dependent nodes and creates `[NEEDS REVIEW]` without choosing a fallback.
- [ ] Applicable package documents are validated against their Draft 2020-12 schemas before use.
- [ ] Duplicate package or node IDs, missing dependencies, and dependency cycles reject Run Plan creation with structured evidence.
- [ ] A complete package requires exact passing qualification; an unqualified `vertical_slice` package is accepted only with promotion disabled.
- [ ] The run stores exact versions and hashes for the manifest and every governed schema, ontology, package, rule bundle, template, skill, qualification, evaluation suite, executor, and tool used by the plan.
- [ ] Run Plan and node fingerprints use canonical content hashing and change when any covered governed input changes.
- [ ] Replaying the same canonical request returns the same Pinned Run, Run Plan, receipt, and event history; key reuse with a different request returns `409`.
- [ ] Once requested, a Pinned Run rejects attempts to replace any governed version.
- [ ] The workspace exposes the complete stored Run Plan, while a Section Execution Envelope contains neither the full plan nor the full Study Evidence Package.

**Traceability:** Specification Phase 2; `RUN-001`–`RUN-006` and `PKG-001`–`PKG-008`.
