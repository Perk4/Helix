## Goal

From the browser, run deterministic validation and the real governed body-weight Codex path using the production frontend and backend images with PostgreSQL, without a repository bind mount.

## Locked

- Package the exact governed packages, JSON contracts, and reviewed skill files that eligibility and Codex execution use at runtime.
- Run those assets read-only from the image. Record their content hashes in receipts.
- Keep backend eligibility and gate decisions authoritative. The browser only requests work and renders receipts.
- Keep the live Codex check opt-in. A fixture may test the adapter boundary in the fast suite but cannot satisfy this slice.
- Do not place a Codex credential in an image, generated client file, browser bundle, screenshot, or log.

## Acceptance

- [ ] `docker compose up --build` reaches backend health and loads the complete workspace from the frontend with PostgreSQL as the reported dialect.
- [ ] The backend image contains every runtime package, contract, and skill file without a host mount, and a test recomputes the same hashes recorded by the section receipt.
- [ ] The container path runs deterministic validation, then a real Python Codex SDK turn with explicit `$helix-section-agent` invocation, and the browser renders its thread, skill, envelope, and candidate identities.
- [ ] Restarting the backend preserves the run in PostgreSQL. Exact replay returns the first receipt without a second Codex turn, candidate, event, or chargeable attempt.
- [ ] A missing or changed governed asset fails readiness or eligibility with a structured error before a Codex turn starts.
- [ ] One rerunnable smoke command saves a redacted receipt, screenshot, and frontend and backend image digests.
- [ ] The static suite, API tests, production builds, Compose smoke test, and opt-in live Codex test pass from a clean checkout.

## Out of scope

The durable Workflow Trace, study-output evaluation enforcement, candidate promotion, Azure resources, and all-section automation remain out of scope.

## Refs

Spec #28. `DEMO-002` through `DEMO-004`; `AUTH-002`, `AUTH-003`, `AUTH-007`, `AUTH-008`; `PROOF-001` through `PROOF-004`, `PROOF-010`; `docs/TECHNICAL_ARCHITECTURE.md` deployment packaging gap; ADR-0001, ADR-0009, ADR-0021.

## Process

Blocked by none. Builds on completed issue #1. Blocks the Workflow Trace and Azure deployment slices. One vertical PR.
