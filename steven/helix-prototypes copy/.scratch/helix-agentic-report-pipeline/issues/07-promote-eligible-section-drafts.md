# 07: Promote only deterministically eligible Section Drafts

**What to build:** A promotion-capable section becomes a Section Draft only when deterministic code proves every promotion condition. Users can inspect the exact candidate, dispositions, and gate decisions from which the draft was created.

**Blocked by:** 06: Bound failed Candidate Attempts to three.

**Status:** ready-for-agent

- [ ] Promotion occurs only when there is no `hard_blocker`, every `review_required` result has a current artifact-bound disposition, provenance passed, all Template Conformance Gates passed, and the Section Package permits promotion.
- [ ] Truth-table tests cover every individual false condition and combinations of false conditions.
- [ ] Agent-, Codex-, Promptfoo-, or client-authored promotion status is ignored or rejected.
- [ ] Warnings remain visible and do not block promotion.
- [ ] A promoted draft validates against the Section Draft contract and references the exact candidate hash and gate decisions.
- [ ] A disposition binds to the exact validation result, candidate or draft hash, and Review Scaffold Revision required by its state.
- [ ] The frontend renders the promoted draft and its governing evidence without recalculating eligibility.
- [ ] The `section.5_2_3_body_weight` vertical-slice package remains unpromotable in every service and API path.

**Traceability:** Specification Phase 6; promotion formula, `REVIEW-001`, and ADR-0015.
