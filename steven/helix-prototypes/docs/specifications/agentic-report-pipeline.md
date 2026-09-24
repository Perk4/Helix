# Agentic report pipeline build specification

Status: Proposed for implementation review

This specification defines observable behavior for the HELIX agentic report pipeline. It turns the accepted architecture decisions and JSON contracts into commands, state transitions, failure rules, and tests. It does not replace the terminology in [`CONTEXT.md`](../../CONTEXT.md) or the decisions in [`docs/adr`](../adr).

## 1. Scope

### 1.1 Product outcome

HELIX must process one frozen study manifest through deterministic validation, section drafting, human review, approval, and explicit export without allowing an agent to create evidence or decide a gate.

The first implementation phase must prove this complete path:

```text
frontend action
  -> FastAPI command
  -> real Python Codex SDK invocation
  -> explicit $helix-section-agent invocation
  -> schema-valid section_draft_candidate
  -> persisted Codex thread, skill, and candidate hashes
  -> new study-wide Review Scaffold Revision
  -> receipt rendered and asserted in the frontend
```

A fixture, mocked response, direct model call, or backend-only test does not satisfy the first phase.

### 1.2 In scope

This specification covers:

- Idempotent creation and resumption of a Pinned Run.
- Package discovery, validation, version pinning, and dependency resolution.
- Deterministic validation and gate ownership.
- Codex SDK invocation of one reusable Section Agent.
- Candidate attempts, Section Draft promotion, and study-wide Review Scaffold Revisions.
- Human dispositions, Human-Directed Revisions, superseding runs, approvals, and export.
- Provenance, hashes, audit events, failures, and test evidence.

### 1.3 Explicit deferrals

The implementation must not resolve these topics by assumption:

| Deferred topic | Required behavior until a later decision |
| --- | --- |
| Embeddings | Do not create or query embeddings. |
| Upload authorization policy | Accept only artifacts that an existing authorization boundary has frozen. |
| Report-pattern selection | Use only the pinned template and applicable Section Packages. |
| Ambiguous study-type handling | Block the run and record the ambiguity. Do not infer a study type. |
| Reviewer-role configuration | Preserve the prototype's configured roles. Do not add a role model in this work. |
| Governed model selection | Use the configured Codex default. Do not hard-code a model. |
| Arbitrary sponsor-file ingestion | Keep the current seeded or authorized manifest boundary. |

The first phase also defers parallel section execution, all 22 Section Packages, final Section Draft promotion, and export changes. The example `section.5_2_3_body_weight` package has `maturity: vertical_slice` and `promotion_allowed: false`.

## 2. Actors and authority

| Actor | Owns | Must not do |
| --- | --- | --- |
| Authorized user | Freeze inputs, submit review actions, approve exact artifacts, and request export. | Mutate a Pinned Run or approve invented provenance. |
| FastAPI command boundary | Validate commands, enforce idempotency, select the active Pinned Run, and return receipts. | Derive eligibility in the browser. |
| Package Loader | Load governed packages, validate schemas, resolve dependencies, and compute hashes. | Load an unqualified complete package into a production run. |
| Run Orchestrator | Execute ready Run Plan nodes and coordinate Section Agent invocations. | Calculate or override gate status. |
| Deterministic executors | Parse sources, calculate claims, run rules, compile provenance, check templates, promote candidates, and assemble Review Scaffold Revisions. | Accept agent-authored evidence or mutable governance versions. |
| Codex Adapter | Start a read-only Codex SDK thread, invoke `$helix-section-agent`, and capture the runtime receipt. | Call a model directly or omit the explicit skill invocation. |
| Section Agent | Draft one Section Draft Candidate from one Section Execution Envelope. | Inspect unrelated raw data, calculate authoritative values, create provenance, or declare a gate result. |
| Promptfoo qualification suite | Qualify an exact skill and suite version before production use. | Satisfy a deterministic rule or study gate. |
| Study Output Evaluation | Flag study-specific agent output for review. | Promote a candidate or turn a gate green. |
| Human reviewer | Resolve allowed `review_required` results and request a new drafting cycle. | Waive a `hard_blocker` or edit an accepted artifact in place. |
| Review Scaffold Assembler | Create immutable study-wide Review Scaffold Revisions. | Export a Review Scaffold or let an agent edit scaffold history. |

## 3. Stored artifacts

The `StudyEvidencePackage` is the aggregate source of truth. The backend must add these contract-backed collections before the corresponding phase ships:

- `run_plan` and Pinned Run metadata.
- `section_draft_candidates`.
- `section_drafts`.
- `review_scaffold_revisions`.
- Artifact-bound review dispositions and approvals.
- Release-candidate and export manifests.

All IDs are immutable strings. All hashes use the `sha256:` prefix followed by 64 lowercase hexadecimal characters.

### 3.1 Canonical hashing

HELIX must hash content with this process:

1. Resolve all referenced files inside the repository or frozen artifact store.
2. Encode structured records as UTF-8 JSON with sorted object keys, no insignificant whitespace, and array order preserved.
3. Hash the resulting bytes with SHA-256.
4. Store the algorithm prefix with the digest.

The backend must hash the exact stored candidate bytes. It must hash a skill from all files under the pinned skill directory in sorted repository-relative path order. Each file contributes its path, byte length, and bytes to the digest.

### 3.2 Audit event shape

Every state-changing command must append an event with:

- `event_id`.
- Event type.
- Actor.
- UTC timestamp.
- Idempotency key when the command accepts one.
- Input artifact IDs and hashes.
- Output artifact IDs and hashes.
- Rule, package, skill, suite, executor, and tool versions used by the command.
- Outcome and structured failure codes.

An event is append-only. A retry may append a new attempt event, but it must not rewrite an earlier event.

## 4. States and transitions

### 4.1 Pinned Run state sequence

The pipeline records the following successful events in order:

```text
run_requested
  -> parsed
  -> study_resolved
  -> validated
  -> template_contract_passed
  -> section_candidate_recorded
  -> provenance_compiled
  -> template_conformance_passed
  -> section_promoted
  -> review_scaffold_revised
  -> approved
  -> exported
```

A Run Plan node has one of four workflow states: `pending`, `running`, `blocked`, or `complete`. A dependency failure keeps the node `blocked`. Independent ready nodes may continue. The Run Orchestrator must not mark the entire run failed only because one section is blocked.

### 4.2 Candidate lifecycle

One drafting cycle contains at most three immutable Candidate Attempts.

| Condition | Required transition |
| --- | --- |
| Blocking deterministic or Template Contract Gate fails | Do not invoke the Section Agent. Record the affected Section Impact Set. |
| Agent returns a schema-valid candidate | Store the candidate and receipt, then run provenance compilation. |
| Provenance or Template Conformance Gate fails on attempts 1 or 2 | Store the failures and start the next attempt with the same governed inputs. |
| Attempt 3 fails | Stop automation for the section and render `[NEEDS REVIEW]`. |
| All four promotion conditions pass | Deterministic code creates a Section Draft when `promotion_allowed` is true. |
| A human requests a redraft | Start a new audited drafting cycle for that section only. |

A retry may change wording, structure, and claim placement. It must retain the manifest, Validated Claims, package, template contract, governed versions, and declared dependencies from the cycle's first attempt.

### 4.3 Promotion formula

Deterministic code may promote a candidate only when all conditions are true:

```text
no hard_blocker
AND every review_required result has a current artifact-bound disposition
AND provenance compilation passed
AND every Template Conformance Gate passed
AND the Section Package permits promotion
```

A `warning` remains visible and does not block promotion. Neither the Section Agent, the Codex SDK, nor Promptfoo may set promotion status.

### 4.4 Review Scaffold lifecycle

The Review Scaffold Assembler creates a new revision only when scaffold-visible state changes. Visible changes include a gate result, candidate, draft, blocker, disposition, approval, or stale approval.

Each revision must:

- Validate against `review-scaffold-revision.schema.json`.
- Increment `sequence` by one within the Pinned Run.
- Reference the predecessor revision except for sequence 1.
- Record the triggering event.
- Reference the exact section artifacts used for assembly.
- Set `export_eligible` to `false`.
- Use the literal `[NEEDS REVIEW]` for every `needs_review` entry.

The first vertical slice records its candidate in a new revision but leaves the body-weight entry in `needs_review`. The entry must include a blocker that says promotion is disabled for the `vertical_slice` package.

## 5. Behavioral requirements

### 5.1 Freeze and start a Pinned Run

`RUN-001` Freezing an authorized manifest must emit exactly one `run_requested` event for the manifest hash and governed-version set.

`RUN-002` Replaying the same command must return or resume the same Pinned Run. It must not create a second Run Plan, validation result, or audit event.

`RUN-003` The backend must reject a request when any manifest entry is unlocked, lacks an authorization record, or has a checksum that does not match its stored bytes.

`RUN-004` The Pinned Run must store exact versions and hashes for the manifest, schema, ontology, Rule Bundles, Data Validation Packages, Section Packages, template, Section Agent skill, qualification suite, qualification result, and study-output suite.

`RUN-005` The Pinned Run must not change a governed version after `run_requested`.

`RUN-006` Study Type Resolution must use pinned protocol fields and a versioned mapping table. An unknown or ambiguous result blocks dependent nodes and creates `[NEEDS REVIEW]` without selecting a fallback type.

### 5.2 Load packages and build the Run Plan

`PKG-001` The Package Loader must load Data Validation Packages only from `skills/helix-evidence-pipeline/packages/data-validation` and Section Packages only from `skills/helix-evidence-pipeline/packages/sections`.

`PKG-002` It must validate each package against the applicable Draft 2020-12 schema before using package fields.

`PKG-003` It must reject duplicate package IDs, missing dependency IDs, duplicate node IDs, and dependency cycles before storing a Run Plan.

`PKG-004` It must include only packages that match the resolved `study_type_id`.

`PKG-005` A complete Section Package must have a passing qualification with an exact qualification ID and hash. A `vertical_slice` package may remain pending only when `promotion_allowed` is false.

`PKG-006` The stored Run Plan must validate against `run-plan.schema.json`. Its fingerprint must cover the ordered node definitions and all governed versions.

`PKG-007` Each node's `input_fingerprint` must cover the content hashes of every direct input and governed version that can affect that node.

`PKG-008` A Section Draft dependency fingerprint must cover the frozen source artifacts, Validated Claims, direct dependency artifacts, schemas, ontology, Rule Bundles, template contract, Section Package, skill, qualification, study-output suite, and deterministic executors used to create it.

### 5.3 Execute deterministic validation and gates

`GATE-001` Data Validation Packages must group rules by evidence domain and produce reusable Validated Claims once per Pinned Run.

`GATE-002` Every rule must declare exactly one enforcement class: `hard_blocker`, `review_required`, or `warning`.

`GATE-003` Template Contract Gates must pass before a Section Agent starts. They must verify required fields, locations, table shapes, labels, units, and style constraints in the pinned template.

`GATE-004` The Provenance Compiler must bind every factual span and table cell to an existing Validated Claim. Missing or invalid lineage is a non-waivable `hard_blocker`.

`GATE-005` Template Conformance Gates must check candidate completeness, table coverage, terminology, units, rounding, and approved-language constraints.

`GATE-006` A Study Output Evaluation failure must create `review_required`. A pass must not change any deterministic gate.

`GATE-007` The frontend may display backend eligibility but must not recalculate it.

### 5.4 Invoke the Section Agent

`AGENT-001` The backend must build a schema-valid `SectionExecutionEnvelope` for one section and persist its hash before invocation.

`AGENT-002` The envelope must contain only the Section Package reference, direct dependency states and hashes, required Validated Claims, relevant study context, current structured failures, executor receipts, and governed versions.

`AGENT-003` The envelope must not contain the complete Run Plan, the full Study Evidence Package, or unrelated raw study data.

`AGENT-004` The Codex Adapter must start a real Python Codex SDK thread in read-only mode with the repository root as its working directory.

`AGENT-005` The prompt must explicitly invoke `$helix-section-agent` and identify exactly one stored Section Execution Envelope.

`AGENT-006` The backend must not hard-code a model for the first vertical slice.

`AGENT-007` The adapter must accept only one JSON object. The FastAPI boundary must validate it against `section-draft-candidate.schema.json` before storage.

`AGENT-008` A Cross-Section Query may return only canonical facts, Validated Claims, or Section Drafts from dependencies declared in the Section Package. The response must record the requested artifact IDs and returned hashes.

`AGENT-009` The stored agent receipt must contain `runtime: codex_sdk`, the Codex thread ID, `skill_name: helix-section-agent`, and the skill hash.

### 5.5 Persist a Candidate Attempt

`CAND-001` The service must reject a candidate whose run, section, package, cycle, or attempt does not match the command context.

`CAND-002` It must reject a candidate that cites a claim outside the envelope or omits claim IDs for a factual span or table cell.

`CAND-003` It must preserve the original candidate, executor receipts, agent receipt, schema-validation result, content hash, and attempt number.

`CAND-004` It must commit the candidate, the runtime receipt, the `section_candidate_recorded` event, and the new Review Scaffold Revision in one database transaction.

`CAND-005` If the transaction fails, none of those records may become visible.

`CAND-006` The first vertical slice must not create a Section Draft because its package forbids promotion.

### 5.6 Handle human review and edits

`REVIEW-001` A disposition must bind to one validation result, one exact Section Draft hash when a draft exists, and one Review Scaffold Revision.

`REVIEW-002` A changed section artifact or declared dependency must make the prior disposition stale.

`REVIEW-003` A human edit request must create a Human-Directed Revision. It must not modify the prior candidate or Section Draft.

`REVIEW-004` The new cycle must repeat provenance compilation, Study Output Evaluation, and Template Conformance Gates for every attempt.

`REVIEW-005` An edit to one section must not rerun an unaffected section.

### 5.7 Create a superseding run

`SUPER-001` Authorized source corrections or governed-version changes must create a new manifest and Superseding Run. They must not modify the prior Pinned Run.

`SUPER-002` The new run must record the predecessor run ID and the supersession reason.

`SUPER-003` HELIX may reuse parsing and normalized records only when their content hashes match.

`SUPER-004` HELIX may carry forward a section artifact only when its complete dependency fingerprint is identical. The carried-forward artifact must reference its predecessor artifact.

`SUPER-005` The Superseding Run must issue fresh validation results, gate decisions, Review Scaffold Revisions, and approvals even when it reuses an artifact.

### 5.8 Approve and export exact artifacts

`EXPORT-001` Final Study Approval must bind to the release-candidate manifest hash and every included artifact hash.

`EXPORT-002` Any change to an included artifact must make the approval stale and block export.

`EXPORT-003` Export must require a separate user command after the release gate reaches `ready_for_export`.

`EXPORT-004` Export must package the exact approved hashes. It must not invoke an agent, recalculate a value, select latest state, or include a Review Scaffold.

`EXPORT-005` Replaying an export command must return the same artifact IDs, checksums, and bytes.

`EXPORT-006` The UI and API may report `ready for signature`, `ready for export`, or `exported`. They must not report `FDA approved`.

## 6. API commands and idempotency

### 6.1 Command summary

| Command | Endpoint | Success result |
| --- | --- | --- |
| Freeze and start or supersede a run | `POST /api/v1/studies/{study_id}/runs` | Pinned Run receipt with Run Plan hash. |
| Run deterministic validation | `POST /api/v1/studies/{study_id}/validation-runs` | Validation run and rule receipts. |
| Draft one section | `POST /api/v1/studies/{study_id}/section-runs` | Candidate and Codex SDK receipt. |
| Record a review disposition | `POST /api/v1/studies/{study_id}/validation-results/{result_id}/dispositions` | New Review Scaffold Revision. |
| Start a Human-Directed Revision | `POST /api/v1/studies/{study_id}/sections/{section_id}/revision-cycles` | New drafting-cycle receipt. |
| Record final approval | `POST /api/v1/studies/{study_id}/approvals` | Hash-bound approval receipt. |
| Export approved artifacts | `POST /api/v1/studies/{study_id}/exports` | Content-derived export receipt. |

The existing workspace and evidence queries remain read-only:

- `GET /api/v1/studies/{study_id}/workspace`.
- `GET /api/v1/studies/{study_id}/claims/{claim_id}/evidence`.

### 6.2 Shared idempotency rules

Every state-changing request must include an `idempotency_key` in the JSON body. The backend must enforce uniqueness by study ID and command type.

For the first use of a key, the backend stores the canonical request hash and command receipt in the same transaction as the command effects.

For a replay with the same canonical request hash, the backend returns the stored receipt with `idempotent_replay: true`. It must not append an event or create an artifact.

For a replay with a different request hash, the backend returns `409 Conflict` with code `idempotency_key_reused`.

An in-progress replay returns the existing operation ID and current state. It must not start a second worker or SDK thread.

### 6.3 Section-run request and receipt

The first vertical slice uses this request:

```json
{
  "section_package_id": "section.5_2_3_body_weight",
  "idempotency_key": "workbench-STUDY-HLX-028-body-weight-v1"
}
```

The backend derives the active Pinned Run, drafting cycle, and next attempt. The success receipt contains at least:

```json
{
  "run_id": "SRUN-...",
  "section_id": "5_2_3_body_weight",
  "status": "candidate_recorded",
  "candidate_id": "SDC-...",
  "candidate_hash": "sha256:...",
  "agent_runtime": "codex_sdk",
  "codex_thread_id": "...",
  "skill_name": "helix-section-agent",
  "skill_hash": "sha256:...",
  "review_scaffold_revision": 2,
  "idempotent_replay": false
}
```

The receipt must include enough data to distinguish a live Codex SDK run from a fixture.

## 7. Failure behavior

| Failure | HTTP result | Required stored evidence |
| --- | --- | --- |
| Unknown study, package, section, claim, or artifact | `404` | Rejected command event when a study context exists. |
| Invalid command or contract body | `422` | Schema or field errors. No domain artifact. |
| State conflict, stale hash, ineligible section, or idempotency collision | `409` | Failure code, expected state or hash, and actual state or hash. |
| Package dependency is missing or cyclic | `409` | Package IDs, dependency path, and Run Plan rejection. |
| Codex SDK is unavailable or the thread cannot start | `503` | Adapter failure, SDK version, and no candidate. |
| Agent returns malformed JSON or a schema-invalid candidate | `502` | Response hash, validation errors, thread ID when available, and no candidate. |
| Candidate cites an unapproved claim | `409` | Candidate response hash, rejected claim IDs, and no candidate. |
| Provenance compilation fails | Domain result | Preserved candidate, provenance blocker, and next-attempt decision. |
| Template Conformance Gate fails | Domain result | Preserved candidate, failed gate IDs, and next-attempt decision. |
| Database transaction fails | `500` | No partial candidate, receipt, event, or Review Scaffold Revision. |

Logs and API errors must not include source-file contents, credentials, or secret environment values.

## 8. First vertical slice implementation boundary

The first phase adds these backend modules:

```text
backend/app/agents/codex_section_agent.py
backend/app/section_runs.py
backend/tests/test_section_runs.py
```

The phase also adds:

- `runSectionAgent` in `frontend/src/lib/api.ts`.
- A backend-derived eligibility field in the workspace response.
- A **Draft body-weight component** button in `StudyJourney`.
- A receipt view that shows the candidate ID and hash, Codex thread ID, skill name and hash, and Review Scaffold Revision.
- A live Playwright scenario and a `scripts/verify-codex-section-run.sh` runner.

The backend command must execute these steps in order:

1. Load the active Pinned Run and verify its immutable manifest and governed versions.
2. Load `section.5_2_3_body_weight` through the Package Loader.
3. Confirm that `C-BW-HIGH` is a Validated Claim with provenance.
4. Run the package's Template Contract Gates.
5. Build and persist a `SectionExecutionEnvelope`.
6. Start a read-only Codex SDK thread at the repository root.
7. Invoke `$helix-section-agent` with the envelope identifier.
8. Parse and validate the response.
9. Compute and persist the candidate, skill, envelope, and thread receipt hashes.
10. Create a new study-wide Review Scaffold Revision in the same transaction.

The backend may run provenance compilation and Template Conformance Gates in this phase. It must still leave the section unpromoted.

## 9. Implementation phases and acceptance criteria

Each phase is a ticket boundary. A later phase may start only when its blocker phases pass.

### Phase 1: Prove the frontend-triggered Codex SDK path

Blockers: none beyond the current repository prerequisites.

Acceptance criteria:

- A fast API test proves section eligibility, idempotent replay, candidate schema rejection, claim allowlisting, missing receipt rejection, and rollback after SDK failure.
- A frontend test proves that backend eligibility controls the button.
- A live Playwright test runs deterministic validation, clicks **Draft body-weight component**, and invokes the real Python Codex SDK.
- The page renders `Codex SDK`, `helix-section-agent`, the thread ID, the skill hash, the candidate hash, and the new Review Scaffold Revision.
- The candidate cites `C-BW-HIGH` and contains `286.2 g`.
- The stored workspace contains the same hashes as the API receipt.
- The release gate remains blocked and no Section Draft exists.
- The live run saves a screenshot and API receipt under `evidence/`.
- The live verifier fails when the SDK is unavailable or a fixture supplies the response.

Test layers: unit contract tests, FastAPI integration tests, frontend component tests, and live Playwright.

### Phase 2: Persist an immutable Run Plan

Blocker: Phase 1 defines the first real agent node and receipt.

Acceptance criteria:

- Package schemas, unique IDs, existing dependencies, and acyclicity fail closed.
- Replaying manifest freeze returns the same run and Run Plan.
- A changed governed version creates a different Run Plan fingerprint and cannot mutate the prior run.
- The stored `StudyEvidencePackage` exposes the complete Run Plan, while the Section Execution Envelope does not.

Test layers: Package Loader unit tests, graph property tests, repository transaction tests, and FastAPI command tests.

### Phase 3: Execute Data Validation Packages

Blocker: Phase 2.

Acceptance criteria:

- `validation.body_weight` runs its pinned executor once per Pinned Run.
- Its output claims preserve grain, units, source hashes, transforms, and rule versions.
- Recomputed body-weight results match the deterministic fixtures.
- A missing grain or provenance edge creates a `hard_blocker`.
- Two sections can reference the same Validated Claim without recalculation.

Test layers: executor unit tests, fixture tests, schema tests, and repository integration tests.

### Phase 4: Enforce Template Contract Gates and section eligibility

Blocker: Phase 3.

Acceptance criteria:

- A missing field, table shape, label, unit, or style rule blocks invocation before any SDK thread starts.
- Eligibility comes from backend gate results.
- Independent eligible sections remain ready when another section is blocked.
- The Review Scaffold renders the Section Impact Set with literal `[NEEDS REVIEW]` placeholders.

Test layers: gate unit tests, dependency-impact tests, API tests, and frontend eligibility tests.

### Phase 5: Compile provenance and check candidate conformance

Blockers: Phases 3 and 4.

Acceptance criteria:

- Every factual span and table cell resolves to a claim that the envelope allowed.
- Unsupported content creates a non-waivable provenance blocker.
- Study Output Evaluation failure creates `review_required` without satisfying a deterministic gate.
- Template Conformance Gates return stable rule IDs and structured failures.
- Attempts 1 and 2 may retry with unchanged governed inputs.

Test layers: provenance compiler unit tests, template conformance fixtures, Promptfoo study-output tests, and service integration tests.

### Phase 6: Promote an eligible Section Draft

Blocker: Phase 5.

Acceptance criteria:

- Promotion occurs only when the five conditions in section 4.3 pass.
- The service rejects promotion requested by an agent or client.
- Warnings remain visible and do not block promotion.
- A promoted draft validates against `section-draft.schema.json` and references the exact candidate hash and gate decisions.
- The `vertical_slice` package remains unpromotable.

Test layers: promotion formula truth-table tests, schema tests, and service integration tests.

### Phase 7: Version the study-wide Review Scaffold

Blocker: Phase 6.

Acceptance criteria:

- Every scaffold-visible change creates one revision with the next sequence number.
- A replay that makes no visible change creates no revision.
- Each revision references its predecessor, triggering event, and exact section artifacts.
- `needs_review` entries contain the literal `[NEEDS REVIEW]` and at least one blocker ID.
- No export manifest accepts a Review Scaffold Revision.

Test layers: assembler unit tests, schema tests, concurrency tests, and repository integration tests.

### Phase 8: Support human redraft and edit cycles

Blocker: Phase 7.

Acceptance criteria:

- A human request creates a new cycle and preserves every earlier attempt.
- Each cycle stops after three failed attempts.
- Provenance, Study Output Evaluation, and Template Conformance Gates rerun for each new candidate.
- Unaffected sections keep their artifact hashes and do not rerun.
- A changed section or dependency makes affected dispositions and approvals stale.

Test layers: lifecycle state tests, retry-limit tests, audit-history tests, and API integration tests.

### Phase 9: Create superseding runs and reuse exact dependencies

Blocker: Phase 2. Phase 8 must pass before carried-forward approvals are evaluated.

Acceptance criteria:

- A correction creates a new run with predecessor and reason fields.
- The prior run remains byte-for-byte retrievable.
- Reuse occurs only for matching content hashes.
- Section carry-forward occurs only for an identical complete dependency fingerprint.
- The new run records fresh validations, gates, scaffold revisions, and approval state.

Test layers: fingerprint unit tests, mutation tests, repository history tests, and supersession API tests.

### Phase 10: Bind approval and export to exact hashes

Blockers: Phases 6 through 9.

Acceptance criteria:

- Final Study Approval names the release-candidate manifest hash and all included artifact hashes.
- Any included hash change blocks export and marks the approval stale.
- Export requires an explicit command and contains no Review Scaffold.
- Idempotent replay returns the same checksums and exact bytes.
- Export does not start an agent or run a calculation.

Test layers: approval formula tests, export byte-equality tests, API integration tests, PostgreSQL verification, and live browser export tests.

## 10. Traceability

| Requirement group | Accepted decisions | Primary contracts or source |
| --- | --- | --- |
| `RUN-*` | [ADR-0002](../adr/0002-study-runs-cannot-mutate-governance-versions.md), [ADR-0019](../adr/0019-manifest-freeze-idempotently-starts-a-run.md) | [`run-plan.schema.json`](../../skills/helix-evidence-pipeline/contracts/run-plan.schema.json), [`schema.md`](../../skills/helix-evidence-pipeline/references/schema.md) |
| `PKG-*` | [ADR-0006](../adr/0006-reuse-requires-identical-dependency-fingerprints.md), [ADR-0007](../adr/0007-use-two-tiers-of-prompt-evaluation.md), [ADR-0008](../adr/0008-use-one-reusable-section-agent-runtime.md), [ADR-0018](../adr/0018-organize-validation-by-evidence-domain.md), [ADR-0020](../adr/0020-keep-the-run-plan-out-of-agent-context.md) | [`data-validation-package.schema.json`](../../skills/helix-evidence-pipeline/contracts/data-validation-package.schema.json), [`section-package.schema.json`](../../skills/helix-evidence-pipeline/contracts/section-package.schema.json), [`run-plan.schema.json`](../../skills/helix-evidence-pipeline/contracts/run-plan.schema.json) |
| `GATE-*` | [ADR-0001](../adr/0001-rule-bundles-own-gate-authority.md), [ADR-0007](../adr/0007-use-two-tiers-of-prompt-evaluation.md), [ADR-0010](../adr/0010-split-template-readiness-from-output-conformance.md), [ADR-0013](../adr/0013-provenance-precedes-and-constrains-drafting.md), [ADR-0014](../adr/0014-use-three-rule-enforcement-classes.md), [ADR-0015](../adr/0015-derive-section-promotion-from-four-conditions.md), [ADR-0018](../adr/0018-organize-validation-by-evidence-domain.md), [ADR-0021](../adr/0021-test-ai-behavior-and-deterministic-code-separately.md) | Both package schemas and [`section-draft.schema.json`](../../skills/helix-evidence-pipeline/contracts/section-draft.schema.json) |
| `AGENT-*` | [ADR-0008](../adr/0008-use-one-reusable-section-agent-runtime.md), [ADR-0009](../adr/0009-codex-sdk-coordinates-section-agents.md), [ADR-0013](../adr/0013-provenance-precedes-and-constrains-drafting.md), [ADR-0020](../adr/0020-keep-the-run-plan-out-of-agent-context.md) | [`section-execution-envelope.schema.json`](../../skills/helix-evidence-pipeline/contracts/section-execution-envelope.schema.json), [`section-draft-candidate.schema.json`](../../skills/helix-evidence-pipeline/contracts/section-draft-candidate.schema.json), [Section Agent skill](../../.agents/skills/helix-section-agent/SKILL.md) |
| `CAND-*` | [ADR-0003](../adr/0003-separate-review-scaffolds-from-section-drafts.md), [ADR-0011](../adr/0011-version-the-study-review-scaffold.md), [ADR-0016](../adr/0016-bound-section-candidate-retries.md) | [`section-draft-candidate.schema.json`](../../skills/helix-evidence-pipeline/contracts/section-draft-candidate.schema.json), [`review-scaffold-revision.schema.json`](../../skills/helix-evidence-pipeline/contracts/review-scaffold-revision.schema.json) |
| `REVIEW-*` | [ADR-0012](../adr/0012-bind-reviews-and-approvals-to-artifact-hashes.md), [ADR-0016](../adr/0016-bound-section-candidate-retries.md), [ADR-0017](../adr/0017-human-edits-create-new-gated-candidates.md) | [`section-draft.schema.json`](../../skills/helix-evidence-pipeline/contracts/section-draft.schema.json), [`review-scaffold-revision.schema.json`](../../skills/helix-evidence-pipeline/contracts/review-scaffold-revision.schema.json), [`schema.md`](../../skills/helix-evidence-pipeline/references/schema.md) |
| `SUPER-*` | [ADR-0004](../adr/0004-section-dependencies-limit-invalidation.md), [ADR-0005](../adr/0005-corrections-create-superseding-runs.md), [ADR-0006](../adr/0006-reuse-requires-identical-dependency-fingerprints.md) | [`run-plan.schema.json`](../../skills/helix-evidence-pipeline/contracts/run-plan.schema.json), [`schema.md`](../../skills/helix-evidence-pipeline/references/schema.md) |
| `EXPORT-*` | [ADR-0003](../adr/0003-separate-review-scaffolds-from-section-drafts.md), [ADR-0012](../adr/0012-bind-reviews-and-approvals-to-artifact-hashes.md), [ADR-0017](../adr/0017-human-edits-create-new-gated-candidates.md) | [`schema.md`](../../skills/helix-evidence-pipeline/references/schema.md), current `ExportCommand` and `ExportReceipt` models |
| First vertical slice | [ADR-0003](../adr/0003-separate-review-scaffolds-from-section-drafts.md), [ADR-0009](../adr/0009-codex-sdk-coordinates-section-agents.md), [ADR-0011](../adr/0011-version-the-study-review-scaffold.md), [ADR-0013](../adr/0013-provenance-precedes-and-constrains-drafting.md), [ADR-0020](../adr/0020-keep-the-run-plan-out-of-agent-context.md) | [First vertical slice](../implementation/first-vertical-slice.md), [example Section Package](../../skills/helix-evidence-pipeline/packages/sections/5_2_3_body_weight/package.json), [Section Agent skill](../../.agents/skills/helix-section-agent/SKILL.md) |

## 11. Required contract updates by phase

The current JSON Schemas cover Run Plans, packages, envelopes, candidates, drafts, and Review Scaffold Revisions. The FastAPI aggregate does not yet expose those records. Implementation must add the fields without weakening `extra="forbid"` validation.

The following missing contracts require a schema before their phase can ship:

| Phase | Required contract |
| --- | --- |
| 1 | Section-run command and receipt, stored agent execution receipt, and backend eligibility response. |
| 2 | Pinned Run metadata and manifest-freeze command. |
| 5 | Provenance compilation receipt and Study Output Evaluation result. |
| 8 | Human-Directed Revision command and drafting-cycle record. |
| 9 | Superseding Run metadata, dependency fingerprint, and carried-forward artifact lineage. |
| 10 | Release-candidate manifest and hash-bound Final Study Approval. |

Each new contract must use Draft 2020-12 JSON Schema, reject unknown properties, and include a versioned `$id`. A phase is not complete until its Pydantic model and JSON Schema reject the same invalid examples.

## 12. Verification commands

Run these checks after each contract change:

```bash
jq empty skills/helix-evidence-pipeline/contracts/*.json \
  skills/helix-evidence-pipeline/packages/*/*/package.json
```

Run the repository checks after each implementation phase:

```bash
make test
```

Phase 1 also requires the live verifier:

```bash
HELIX_CODEX_LIVE=1 ./scripts/verify-codex-section-run.sh
```

These commands do not replace the phase-specific acceptance evidence. A phase is complete only when its required live or PostgreSQL proof passes.
