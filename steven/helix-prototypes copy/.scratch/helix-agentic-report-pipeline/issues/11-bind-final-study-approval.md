# 11: Bind Final Study Approval to an exact release candidate

**What to build:** Authorized reviewers approve one immutable release-candidate manifest, and the workspace shows the precise artifact hashes covered by the approval and whether that approval remains current.

**Blocked by:** 07: Promote only deterministically eligible Section Drafts; 08: Complete study-wide Review Scaffold revisioning; 09: Support Human-Directed Revision cycles and scoped invalidation; 10: Create Superseding Runs with exact-dependency reuse.

**Status:** ready-for-agent

- [ ] A release-candidate manifest validates against its contract and names every included artifact and content hash.
- [ ] Final Study Approval binds to the release-candidate manifest hash and every included artifact hash.
- [ ] Approval cannot be recorded while required sections, gates, dispositions, or reviewer-role prerequisites remain unresolved.
- [ ] Any included artifact change immediately marks the approval stale and blocks export.
- [ ] A Superseding Run starts with fresh approval state and cannot inherit predecessor approval.
- [ ] Approval replay with the same request is a no-op; conflicting idempotency-key reuse returns `409`.
- [ ] Release-candidate and Final Study Approval JSON Schemas match their Pydantic models and reject unknown properties.
- [ ] The frontend shows exact approval scope and uses only `ready for signature` or `ready for export`, never `FDA approved`.

**Traceability:** First half of specification Phase 10; `EXPORT-001`, `EXPORT-002`, and artifact-bound approval decisions.
