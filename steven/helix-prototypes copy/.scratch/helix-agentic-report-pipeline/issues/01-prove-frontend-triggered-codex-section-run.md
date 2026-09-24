# 01: Prove the frontend-triggered Codex SDK section run

**What to build:** From the workbench, an authorized user can run deterministic validation and click **Draft body-weight component**. That action crosses the FastAPI command boundary, invokes the real Python Codex SDK in a read-only repository-root thread, explicitly invokes `$helix-section-agent` for one persisted Section Execution Envelope, validates and atomically stores one Section Draft Candidate and its runtime receipt, creates a new study-wide Review Scaffold Revision, and renders the receipt. Reconcile the governed body-weight claim grain and section identity used by this path; do not bypass an inconsistency. This is a production-shaped tracer bullet, not a fixture-backed substitute.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] A live Playwright test runs deterministic validation, clicks **Draft body-weight component**, and proves the complete frontend → FastAPI → real Python Codex SDK → explicit `$helix-section-agent` → stored candidate → Review Scaffold Revision → rendered receipt path.
- [ ] The live candidate is schema-valid, cites `C-BW-HIGH`, and contains `286.2 g`.
- [ ] The receipt and UI identify `runtime: codex_sdk`, the Codex thread ID, `skill_name: helix-section-agent`, the skill hash, envelope hash, candidate ID and hash, and new Review Scaffold Revision sequence.
- [ ] The workspace contains the same thread, skill, envelope, candidate, and revision identities returned by the command.
- [ ] Backend eligibility controls whether the button is enabled; React does not recalculate eligibility.
- [ ] Replay with the same idempotency key and request returns the original receipt without opening another thread or creating another candidate, event, or scaffold revision; conflicting key reuse returns `409`.
- [ ] Malformed JSON, schema-invalid output, an unapproved claim, or a missing thread/skill receipt fails without storing a candidate.
- [ ] SDK or transaction failure exposes no partial candidate, receipt, event, or scaffold revision.
- [ ] The Review Scaffold body-weight entry remains `needs_review` with literal `[NEEDS REVIEW]` and a blocker stating that promotion is disabled.
- [ ] `section.5_2_3_body_weight` remains `maturity: vertical_slice` and `promotion_allowed: false`; no Section Draft is created and the release gate remains blocked.
- [ ] The live verifier saves its screenshot and API receipt under `evidence/` and fails when the SDK is unavailable or the response comes from a fixture, mock, direct model call, or backend-only test.

**Traceability:** Specification Phase 1; `AGENT-001`–`AGENT-007`, `AGENT-009`, `CAND-001`–`CAND-006`, and the first-vertical-slice boundary.
