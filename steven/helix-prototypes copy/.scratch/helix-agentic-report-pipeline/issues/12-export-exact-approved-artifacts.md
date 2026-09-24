# 12: Export the exact approved artifact set

**What to build:** After approval, a separate frontend action exports exactly the approved release candidate. Export selects no newer state, invokes no agent, performs no calculation, and never includes the Review Scaffold.

**Blocked by:** 11: Bind Final Study Approval to an exact release candidate.

**Status:** ready-for-agent

- [ ] Export requires a separate explicit command after the backend reports `ready_for_export`.
- [ ] The export contains exactly the artifact hashes named by the current Final Study Approval.
- [ ] Export rejects a stale approval, changed artifact, unapproved artifact, or attempt to include a Review Scaffold Revision.
- [ ] Export starts no agent, runs no deterministic calculation, and does not select a `latest` artifact at execution time.
- [ ] Replaying the same command returns identical artifact IDs, checksums, and bytes without appending another export event.
- [ ] PostgreSQL and byte-equality tests prove stored bytes match all receipt and approval checksums.
- [ ] A live browser test performs the explicit export and verifies the downloaded artifacts against the receipt.
- [ ] The API and frontend report `exported` and never report `FDA approved`.

**Traceability:** Second half of specification Phase 10; `EXPORT-003`–`EXPORT-006`.
