# 05: Evaluate one candidate through provenance and output conformance

**What to build:** After a Section Agent returns a candidate, the user can inspect deterministic provenance compilation, advisory Study Output Evaluation, and Template Conformance results for that exact immutable attempt.

**Blocked by:** 03: Execute the body-weight Data Validation Package once per Pinned Run; 04: Enforce Template Contract Gates and backend-owned eligibility.

**Status:** ready-for-agent

- [ ] Every factual span and every table cell resolves to an existing Validated Claim allowed by the candidate's Section Execution Envelope.
- [ ] Unsupported content or invalid lineage creates a non-waivable provenance blocker without modifying or discarding the original candidate.
- [ ] Template Conformance checks cover completeness, table coverage, terminology, units, rounding, and approved-language constraints and return stable rule IDs.
- [ ] A Study Output Evaluation failure creates `review_required`; a pass does not satisfy or alter any deterministic gate.
- [ ] A Cross-Section Query can return only canonical facts, Validated Claims, or Section Drafts from declared dependencies and records requested artifact IDs and returned hashes.
- [ ] The candidate, provenance receipt, study-output result, conformance results, and next-attempt decision are persisted with exact hashes.
- [ ] New JSON Schemas and Pydantic models for provenance and study-output receipts reject the same invalid examples and reject unknown properties.
- [ ] The frontend displays the three evaluation classes separately and never describes Promptfoo as deterministic validation or gate authority.

**Traceability:** Specification Phase 5; `GATE-004`–`GATE-006`, `AGENT-008`, and provenance constraints.
