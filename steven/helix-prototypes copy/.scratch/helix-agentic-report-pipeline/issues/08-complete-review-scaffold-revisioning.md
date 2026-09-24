# 08: Complete study-wide Review Scaffold revisioning

**What to build:** Users can inspect immutable, ordered Review Scaffold history reflecting the current candidates, drafts, blockers, dispositions, approvals, and stale decisions across the entire study.

**Blocked by:** 07: Promote only deterministically eligible Section Drafts.

**Status:** ready-for-agent

- [ ] Every scaffold-visible gate, candidate, draft, blocker, disposition, approval, or stale-approval change creates exactly one next revision.
- [ ] A command replay or other no-op creates no Review Scaffold Revision.
- [ ] Each revision validates against its contract and references its predecessor, triggering event, and exact section artifacts.
- [ ] Sequence numbers are monotonic and unique under concurrent state changes.
- [ ] Every `needs_review` entry contains literal `[NEEDS REVIEW]` and at least one blocker ID.
- [ ] Every revision has `export_eligible: false`.
- [ ] Export and release-candidate contracts reject Review Scaffold Revisions as exportable content.
- [ ] The frontend presents revision history and exact triggering changes without treating the scaffold as a draft report.

**Traceability:** Specification Phase 7; `CAND-004`, Review Scaffold lifecycle, and ADR-0011.
