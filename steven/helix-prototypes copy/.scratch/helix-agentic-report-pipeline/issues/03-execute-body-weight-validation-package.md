# 03: Execute the body-weight Data Validation Package once per Pinned Run

**What to build:** The workbench validation action executes the governed body-weight Data Validation Package, persists reusable Validated Claims with complete provenance, and lets users inspect the deterministic evidence without recalculating values per report section.

**Blocked by:** 02: Freeze an immutable Pinned Run and materialize its Run Plan.

**Status:** ready-for-agent

- [ ] `validation.body_weight` executes its pinned deterministic executor once per Pinned Run and records the package, rule, executor, and source versions used.
- [ ] Its Validated Claims preserve declared grain, units, source hashes, transforms, rule versions, and upstream provenance.
- [ ] Recomputed body-weight results match the frozen deterministic records and expected values.
- [ ] A missing required grain or provenance edge creates a non-waivable `hard_blocker` and a visible affected-section result.
- [ ] Every rule declares exactly one enforcement class: `hard_blocker`, `review_required`, or `warning`.
- [ ] Two section consumers can reference the same stored Validated Claim without rerunning the executor.
- [ ] Replay does not create duplicate claims, validation results, executor receipts, or events.
- [ ] The frontend evidence view displays the persisted claim and lineage returned by the backend rather than deriving either in the browser.

**Traceability:** Specification Phase 3; `GATE-001`, `GATE-002`, and Data Validation Package requirements.
