# 10: Create Superseding Runs with exact-dependency reuse

**What to build:** An authorized source correction or governed-version change creates a new Pinned Run that preserves its predecessor and carries forward only artifacts proven unaffected by identical complete dependency fingerprints.

**Blocked by:** 02: Freeze an immutable Pinned Run and materialize its Run Plan; 09: Support Human-Directed Revision cycles and scoped invalidation.

**Status:** ready-for-agent

- [ ] A correction or governed-version change creates a new run recording its predecessor and supersession reason.
- [ ] The predecessor run and all of its artifacts, decisions, and events remain byte-for-byte retrievable.
- [ ] Parsing and normalized records are reused only when their content hashes match.
- [ ] A section artifact is carried forward only when its complete dependency fingerprint is identical and its lineage references the predecessor artifact.
- [ ] A changed source or governed version reruns only the affected nodes and transitive Section Impact Set.
- [ ] The new run records fresh validation results, gate decisions, Review Scaffold Revisions, and approval state even when an artifact is reused.
- [ ] Superseding-run metadata, dependency-fingerprint, and carry-forward-lineage contracts reject incomplete hashes and unknown fields.
- [ ] The frontend distinguishes predecessor, superseding run, reused artifacts, and rerun artifacts without implying that prior approval carried forward.

**Traceability:** Specification Phase 9; `SUPER-001`–`SUPER-005` and ADR-0004 through ADR-0006.
