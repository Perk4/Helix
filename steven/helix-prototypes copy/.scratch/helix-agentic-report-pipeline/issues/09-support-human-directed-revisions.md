# 09: Support Human-Directed Revision cycles and scoped invalidation

**What to build:** A reviewer can request a new drafting cycle for one section without editing prior artifacts or rerunning unaffected sections. Changed section or dependency hashes visibly stale affected human decisions.

**Blocked by:** 08: Complete study-wide Review Scaffold revisioning.

**Status:** ready-for-agent

- [ ] A human revision command creates a new audited drafting cycle and preserves every earlier Candidate Attempt and Section Draft.
- [ ] A cycle has its own three-attempt limit and cannot mutate or extend a prior cycle.
- [ ] Provenance compilation, Study Output Evaluation, and Template Conformance run for every candidate in the new cycle.
- [ ] Unaffected sections retain their artifact hashes and do not rerun.
- [ ] Changing a section artifact or declared dependency marks affected dispositions and approvals stale.
- [ ] The Section Impact Set identifies direct and transitive dependents without invalidating unrelated sections.
- [ ] Human-Directed Revision command and drafting-cycle JSON Schemas match their Pydantic models and reject unknown properties.
- [ ] The frontend lets a reviewer request and inspect the new cycle but provides no in-place edit of accepted artifacts.

**Traceability:** Specification Phase 8; `REVIEW-002`–`REVIEW-005`, ADR-0016, and ADR-0017.
