# 04: Enforce Template Contract Gates and backend-owned eligibility

**What to build:** Before drafting, users can see whether each section is eligible and why. Deterministic Template Contract Gates prevent an ineligible section from opening a Codex thread, while sections outside its impact set remain available.

**Blocked by:** 03: Execute the body-weight Data Validation Package once per Pinned Run.

**Status:** ready-for-agent

- [ ] Required field, location, table-shape, controlled-label, unit, and style constraints are checked against the pinned template before agent invocation.
- [ ] Failure of any blocking Template Contract Gate leaves the Run Plan node blocked and starts no SDK thread.
- [ ] The backend returns eligibility and structured gate results; the frontend only renders those decisions.
- [ ] A blocked result records its Section Impact Set and renders literal `[NEEDS REVIEW]` placeholders in a new scaffold revision.
- [ ] An independent eligible section remains ready when another section is blocked.
- [ ] Correcting or superseding the relevant governed input is required for non-waivable failures; the browser cannot override them.
- [ ] API and frontend tests fail if eligibility is inferred client-side or if an SDK adapter is called before all blocking pre-draft gates pass.

**Traceability:** Specification Phase 4; `GATE-003`, `GATE-007`, and Section Impact Set behavior.
