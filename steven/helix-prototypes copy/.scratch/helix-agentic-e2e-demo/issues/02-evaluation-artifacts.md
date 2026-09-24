## Goal

At Traceability Review, let a reviewer inspect the exact Skill Qualification and Study Output Evaluation artifacts beside the deterministic and provenance evidence for the body-weight candidate.

## Locked

- A promotable Pinned Run may reference only a passing qualification bound to the exact skill directory hash and paired suite hash.
- Bind each Study Output Evaluation to one immutable candidate hash, suite, rubric, evaluator configuration, reasons, and raw result artifact hash.
- A qualitative failure creates `review_required`. A qualitative pass cannot satisfy a deterministic rule, provenance check, template gate, promotion condition, or release gate.
- Keep Promptfoo behavior tests separate from deterministic executor fixture tests.
- Label deterministic, qualification, qualitative, and human evidence by authority class in both the API and UI.

## Acceptance

- [ ] A passing qualification produces a content-addressed Evaluation Artifact linked to the exact skill and suite artifacts before that skill version becomes eligible.
- [ ] A missing, stale, or failing qualification blocks the Codex step before a thread starts and appears as a structured trace failure.
- [ ] The exact candidate from the real Codex turn receives one Study Output Evaluation whose artifact records suite, rubric, evaluator, result, reasons, timestamp, and raw result hash.
- [ ] A failing study-output fixture creates `review_required`, while a passing fixture leaves every deterministic gate value unchanged.
- [ ] Traceability Review shows deterministic results, provenance, template conformance, Skill Qualification, and Study Output Evaluation without collapsing them into one pass indicator.
- [ ] Every evaluation link resolves to stored input and output hashes, and changing the candidate, skill, suite, or rubric makes the prior evaluation inapplicable.
- [ ] Promptfoo, deterministic executor, API, and browser tests pass and prove the authority separation.

## Out of scope

Candidate promotion, approval, export, broad benchmark management, evaluator model comparison, and all-section qualification remain out of scope.

## Refs

Spec #28. `DEMO-005`; `AUTH-003`, `AUTH-004`; `EVAL-001` through `EVAL-008`; `UX-004` through `UX-006`; `PROOF-005`, `PROOF-010`; `docs/architecture/agentic-e2e-demo.md`; ADR-0001, ADR-0007, ADR-0021, ADR-0023; existing issues #5 and #22.

## Process

Blocked by #5 and #30. Blocks the agent-authored export slice and the deployed proof. One vertical PR.
