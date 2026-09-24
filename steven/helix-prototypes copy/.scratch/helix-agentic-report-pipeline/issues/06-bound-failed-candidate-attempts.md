# 06: Bound failed Candidate Attempts to three

**What to build:** A section can retry failed post-draft evaluation with unchanged governed inputs. Users see each immutable attempt and, after the third failure, automation stops with an explicit review marker.

**Blocked by:** 05: Evaluate one candidate through provenance and output conformance.

**Status:** ready-for-agent

- [ ] Attempts 1 and 2 may start a new Section Agent invocation when provenance or conformance fails.
- [ ] Every attempt in a cycle retains the original manifest, Validated Claims, package, template contract, governed versions, and declared dependency hashes.
- [ ] Retry output may change only wording, structure, and claim placement; attempts with altered governed inputs are rejected.
- [ ] Every candidate and execution/evaluation receipt remains immutable and independently retrievable.
- [ ] Attempt 3 stops automated retries and creates a scaffold-visible literal `[NEEDS REVIEW]` entry.
- [ ] Replay of a completed attempt returns its stored receipt and does not consume another attempt or open another SDK thread.
- [ ] Attempt numbering and next-attempt decisions remain correct under concurrent duplicate commands.
- [ ] The frontend presents attempt history and cannot request attempt 4 within the same drafting cycle.

**Traceability:** Split from specification Phase 5; candidate lifecycle and ADR-0016 bounded retries.
