# HELIX agentic end-to-end demo specification

## Problem Statement

HELIX has two valuable proofs that do not yet meet in one product path. The workbench can validate, review, approve, and export a seeded synthetic study. A separate path can invoke the real Python Codex SDK and record one body-weight candidate. That candidate cannot enter the reviewed report or export, and the UI cannot show a durable step-by-step account of deterministic checks, skill calls, qualitative evaluations, and artifact lineage.

The current containers also omit governed runtime assets that agent eligibility reads from disk. No Azure resources, private service boundary, managed secret path, database migration path, or deployed browser proof exists. A reviewer can inspect the design, but cannot yet use one deployed URL to prove that the design works.

## Solution

Deliver one authenticated Azure-hosted demonstration for synthetic study `STUDY-HLX-028`. A reviewer authorizes the frozen manifest, starts a backend-owned Workflow Run, watches persisted deterministic and Codex steps, inspects the exact evidence and evaluation artifacts, completes Human Gates, and exports the exact approved package.

The demo uses one qualified body-weight Section Package as the complete agent path. Codex explicitly invokes a reviewed skill against a Section Execution Envelope. Python executors retain deterministic authority. A versioned qualitative evaluation may require review but cannot turn a gate green. After provenance, template, evaluation, and human review requirements pass, deterministic code promotes the candidate and binds its hash into the approved export.

PostgreSQL stores Workflow Runs, immutable Step Receipts, content-addressed Trace Artifacts, and Artifact Edges. The UI derives its live Workflow Trace from these records. Azure Container Apps hosts separate frontend and internal backend resources. Azure Database for PostgreSQL Flexible Server stores state. Bicep, Azure Container Registry, Key Vault, Microsoft Entra authentication, and Log Analytics provide repeatable deployment, secret handling, access control, and operational evidence.

## User Stories

1. As a study owner, I want one authenticated demo URL, so that I can present HELIX without running a developer workstation.
2. As a study owner, I want the synthetic status visible throughout the journey, so that nobody mistakes the demonstration for a regulatory submission system.
3. As a scientist, I want to authorize the exact frozen manifest before automation starts, so that the run cannot consume unapproved inputs.
4. As a scientist, I want one command to start the governed run, so that I do not coordinate pipeline internals by hand.
5. As a scientist, I want the Workspace Journey to advance from backend state, so that a browser cannot skip a gate.
6. As a scientist, I want each Agent Step to show real persisted activity, so that progress is not a timer or animation.
7. As a scientist, I want to distinguish a deterministic executor from a Codex Skill Invocation, so that I know which result has gate authority.
8. As a scientist, I want to see the exact skill name, version, hash, thread, and turn receipt, so that I can prove which agent behavior ran.
9. As a scientist, I want deterministic results linked to their Rule Bundle and inputs, so that I can reproduce a pass or failure.
10. As a scientist, I want the agent to use only Validated Claims in its envelope, so that it cannot draft from unrelated source data.
11. As a scientist, I want every factual span and table cell linked to a claim, so that unsupported narrative blocks promotion.
12. As a scientist, I want template readiness checked before Codex starts, so that the model does not draft against a broken contract.
13. As a scientist, I want template conformance checked after drafting, so that the candidate preserves required fields, units, labels, and table shape.
14. As an evaluation owner, I want each skill version qualified against its paired suite, so that untested instructions cannot enter a Pinned Run.
15. As an evaluation owner, I want study-output evaluation bound to the exact candidate hash, so that a score cannot float to changed content.
16. As an evaluation owner, I want qualitative failures to create review work rather than rewrite deterministic truth, so that authority stays clear.
17. As a reviewer, I want one Workflow Trace with links to every input and output artifact, so that I can follow the run without reading logs.
18. As a reviewer, I want each trace row to show actor, authority, status, time, and failure code, so that blocked work is understandable.
19. As a reviewer, I want page reload to restore the same run and trace, so that a browser session is not the record.
20. As a reviewer, I want pause to have honest safe-boundary semantics, so that I know whether a Codex attempt was interrupted.
21. As a reviewer, I want resume to create an immutable new attempt with unchanged governed inputs, so that history remains intact.
22. As a reviewer, I want the run to stop at Traceability Review, so that an agent cannot approve its own output.
23. As a reviewer, I want to inspect deterministic, provenance, conformance, and qualitative evidence side by side, so that one green badge cannot hide a weaker check.
24. As a reviewer, I want a disposition bound to the exact reviewed artifact, so that a later change makes the decision stale.
25. As a study director, I want final approval bound to exact artifact hashes, so that export cannot select mutable latest state.
26. As a study director, I want export to remain a separate action, so that approval does not silently generate a release package.
27. As a study director, I want the exported body-weight content to match the promoted Codex candidate, so that the agent path is truly end to end.
28. As a study director, I want download checksums to match the approval and export receipts, so that I can verify exact bytes.
29. As a keyboard user, I want to complete every Human Gate without a mouse, so that the demo is operable with assistive input.
30. As a screen-reader user, I want progress, failures, and gate changes announced, so that live activity is not visual only.
31. As a mobile reviewer, I want the trace and gates to remain usable at a narrow width, so that the demo does not require a desktop monitor.
32. As a deployer, I want Bicep to create the environment from parameters, so that deployment is repeatable and reviewable.
33. As a deployer, I want only the frontend exposed publicly, so that model-spending commands are not an open API.
34. As a deployer, I want PostgreSQL and the backend reachable only on private paths, so that data and commands stay inside the environment.
35. As a deployer, I want secrets loaded from Key Vault by managed identity, so that credentials never enter an image or browser bundle.
36. As a deployer, I want immutable image digests and Container Apps revisions recorded, so that the deployed proof identifies exact code.
37. As a maintainer, I want schema migrations to run before traffic moves, so that redeployment does not depend on `create_all()` behavior.
38. As a maintainer, I want exact command replay to return the first receipt, so that retries do not duplicate work or charges.
39. As a maintainer, I want startup reconciliation for unfinished runs, so that a container restart does not strand the workflow.
40. As a test owner, I want one browser test to exercise the Azure golden path, so that the highest useful seam proves the complete system.
41. As a test owner, I want a redacted evidence bundle with receipts, hashes, screenshots, and export checksums, so that another reviewer can audit the result.
42. As a test owner, I want the same golden-path contract exercised under Docker Compose, so that cloud failures can be separated from product failures.

## Implementation Decisions

- The demonstration covers one synthetic study and one complete body-weight agent path. It does not automate every report section.
- A newly qualified body-weight package version may permit promotion. Earlier `vertical_slice` runs remain immutable and unpromotable.
- FastAPI remains the workflow and command boundary. The browser renders backend state and submits commands. Codex coordinates only eligible agent work.
- The core model consists of `WorkflowRun`, `StepReceipt`, `TraceArtifact`, and `ArtifactEdge`. The existing `StudyEvidencePackage` remains the study aggregate.
- Workflow Run status is an explicit state machine. Step attempts are immutable. An interrupted or failed attempt is never rewritten as successful.
- Every state-changing command carries an idempotency key and request hash. Exact replay returns the stored receipt. Conflicting reuse returns `409`.
- The backend returns a Workflow Run receipt before long-running execution continues. The UI reads persisted progress rather than holding an HTTP request open for the whole run.
- The Codex adapter streams public turn notifications into Step Receipts and stores the final schema-bound result. HELIX does not request or persist hidden model reasoning.
- The backend explicitly invokes allowlisted, developer-reviewed skills by name and exact content hash. End users cannot upload, browse, or select arbitrary skills.
- Deterministic Python executors and Rule Bundles own calculations and gate outcomes. Codex, qualitative evaluators, and the browser cannot set them.
- Skill Qualification binds a passing paired suite to one exact skill and suite hash before that skill can enter a Pinned Run.
- Study Output Evaluation binds its suite, rubric, evaluator configuration, reasons, and raw result hash to one exact candidate. A failure creates `review_required`. A pass grants no deterministic authority.
- The Workflow Trace is a read model derived from immutable Step Receipts and Trace Artifacts. It is not another gate or audit writer.
- The nine-stage Workspace Journey remains the top-level UI. Fine-grained pipeline steps appear inside the current Agent Step.
- Pause takes effect at a safe step boundary. An active Codex turn is interrupted and preserved as an interrupted attempt. Resume creates a new attempt with the same governed inputs.
- The final promotion path requires deterministic gate eligibility, complete provenance, template conformance, current dispositions, successful skill qualification, and package permission.
- Final approval and export bind to exact artifact hashes. Export invokes no model and performs no scientific calculation.
- Azure uses separate Container Apps for the standalone Next.js frontend and FastAPI backend. Only the frontend has public ingress.
- The frontend server proxies same-origin API calls to the internal backend. The browser does not receive an internal backend address.
- Microsoft Entra authentication protects the public demo. These identities are access controls, not compliant electronic signatures.
- Azure Database for PostgreSQL Flexible Server is the deployed state store. SQLite remains limited to isolated tests.
- Bicep creates the network, Container Apps environment, Container Registry, PostgreSQL server, Key Vault, identities, logging, and application revisions.
- Key Vault stores the Codex API key and other secrets that cannot use managed identity. The backend authenticates the Python Codex client at runtime.
- The first demo keeps bounded synthetic export bytes in PostgreSQL. Blob Storage remains a later option.
- A deployment shifts traffic only after health, workspace, migration, and golden-path checks pass. The prior Container Apps revision remains available for rollback.

## Testing Decisions

- Good tests assert external behavior and artifact identity. They do not assert private helper calls, model prose outside the schema, or a specific hidden reasoning path.
- The highest seam is one Playwright golden path against Azure. It authorizes the manifest, starts the Workflow Run, observes persisted deterministic and Codex steps, reloads, reviews artifacts, records required synthetic decisions, exports, downloads, and verifies checksums.
- The Azure proof must use the real Python Codex SDK and an explicit skill invocation. A fixture, direct model call, backend-only test, or mocked candidate does not pass.
- The same workflow contract runs against production images under Docker Compose and PostgreSQL before Azure deployment.
- API integration tests cover state transitions, idempotency conflicts, crash reconciliation, pause and resume, stale dispositions, stale approval, and forbidden client authority.
- Contract tests verify that Step Receipts, Trace Artifacts, Artifact Edges, Evaluation Artifacts, candidates, approvals, and export manifests reject unknown or inconsistent fields.
- Deterministic executor tests use fixed fixtures and exact expected calculations. Promptfoo does not replace these tests.
- Promptfoo qualification tests check instruction following, allowed claim use, executor selection, schema shape, and prohibited authority claims for one exact skill version.
- Study-output evaluation tests prove that failure creates `review_required` and pass leaves deterministic gates unchanged.
- Provenance tests walk every exported factual span and table cell back to a Validated Claim, executor receipt, and frozen source record.
- Persistence tests restart the backend during a nonterminal run and verify one converged result with no duplicate attempt or artifact.
- Browser tests verify that refresh restores progress, future stages remain disabled, authority is not shown by color alone, keyboard navigation works, live updates are announced, and narrow layouts avoid page-level horizontal scrolling.
- Deployment tests verify private backend and database ingress, Key Vault references, image digests, schema version, CORS or same-origin behavior, and secret redaction.
- The evidence bundle validator recomputes every stored hash, checks every Artifact Edge, verifies the exported body-weight text against the promoted candidate, and fails on a missing receipt.
- The normal fast suite may mock Codex at its boundary. The release proof cannot.

## Out of Scope

- Real sponsor data or arbitrary file ingestion.
- Malware scanning, source quarantine, and generalized mapping proposals.
- Automation of every report section.
- Multi-study scheduling and high-volume concurrency.
- User-provided skills or an open skill catalog.
- Azure OpenAI compatibility for the Codex SDK.
- Multi-tenant access control and study-specific authorization.
- Electronic signatures or a 21 CFR Part 11 claim.
- GLP, SEND, eCTD, FDA, privacy, security, or scientific-validity certification.
- Submission-grade PDF, XML, XPT, or nSDRG generation.
- Multi-region recovery, zone-redundant high availability, and formal service-level objectives.
- Blob Storage, Service Bus, Durable Functions, Kubernetes, or a separate workflow engine before measured need.
- Storage of hidden model reasoning.

## Further Notes

The accepted release predicate is strict. One authenticated user must complete the deployed path and verify that every displayed receipt and exported byte resolves to the exact approved hashes in PostgreSQL. Local-only execution, fake progress, SQLite, an isolated Codex candidate, or an unverified screenshot is insufficient.

The implementation uses these requirement identifiers.

### Demo outcome

- `DEMO-001`. One authenticated Azure URL exposes the synthetic demonstration.
- `DEMO-002`. The run starts only from the authorized frozen manifest.
- `DEMO-003`. The golden path executes deterministic body-weight validation.
- `DEMO-004`. The golden path uses the real Python Codex SDK and explicit section skill invocation.
- `DEMO-005`. The exact candidate receives provenance, template, and study-output evaluation.
- `DEMO-006`. The run stops at required Human Gates.
- `DEMO-007`. Deterministic code promotes the exact qualified and reviewed candidate.
- `DEMO-008`. Export contains the exact approved agent-produced body-weight content.
- `DEMO-009`. Every view and artifact remains labeled `SYNTHETIC / NOT FOR SUBMISSION`.
- `DEMO-010`. No mocked agent, fake timer, or SQLite database may satisfy the release proof.

### Authority

- `AUTH-001`. The backend owns workflow, gate, approval, and export state.
- `AUTH-002`. Codex coordinates eligible agent steps but cannot set a gate result.
- `AUTH-003`. Versioned deterministic executors and Rule Bundles own calculations and automated gate results.
- `AUTH-004`. Qualitative evaluation is advisory and cannot satisfy a deterministic rule.
- `AUTH-005`. The browser renders authority and never derives it.
- `AUTH-006`. A person passes each Human Gate through an explicit artifact-bound command.
- `AUTH-007`. Every Skill Invocation uses an allowlisted skill name and exact hash.
- `AUTH-008`. End users cannot upload or select arbitrary skills.
- `AUTH-009`. Microsoft Entra controls demo access without representing an electronic signature.

### Trace and provenance

- `TRACE-001`. Every execution has one immutable Workflow Run identity.
- `TRACE-002`. Every workflow-step attempt has one immutable Step Receipt.
- `TRACE-003`. Every input and output is a content-addressed Trace Artifact.
- `TRACE-004`. Typed Artifact Edges connect sources, claims, candidates, evaluations, approvals, and exports.
- `TRACE-005`. Step Receipts record actor, authority, status, versions, hashes, timestamps, and structured failures.
- `TRACE-006`. Completed and interrupted attempts are append-only.
- `TRACE-007`. Exact command replay returns the prior receipt and creates no duplicate work.
- `TRACE-008`. Startup reconciliation converges unfinished work after a crash.
- `TRACE-009`. Public Codex turn notifications become persisted progress events.
- `TRACE-010`. HELIX stores governed prompts and structured outputs but no hidden model reasoning.
- `TRACE-011`. The trace ledger becomes the canonical source for workflow trace projection instead of adding another mutable event writer.
- `TRACE-012`. Every link shown in the UI resolves to a stored artifact and reproducible hash.

### Evaluation

- `EVAL-001`. Skill Qualification binds an exact skill hash to an exact paired suite and result.
- `EVAL-002`. An unqualified skill version cannot enter a promotable Pinned Run.
- `EVAL-003`. Study Output Evaluation binds to one exact candidate hash.
- `EVAL-004`. An Evaluation Artifact records suite, rubric, evaluator, result, reasons, and raw result hash.
- `EVAL-005`. A study-output failure creates `review_required`.
- `EVAL-006`. A study-output pass leaves deterministic gates unchanged.
- `EVAL-007`. Deterministic executor behavior uses ordinary fixture and integration tests.
- `EVAL-008`. Promptfoo tests agent behavior separately from deterministic calculations.

### User experience

- `UX-001`. The nine-stage Workspace Journey remains the top-level navigation.
- `UX-002`. Fine-grained Step Receipts appear inside the active Agent Step.
- `UX-003`. Production progress comes only from persisted backend events.
- `UX-004`. Every result displays its actor and authority class.
- `UX-005`. Each step exposes its input, output, and control boundary.
- `UX-006`. Blocked, failed, interrupted, awaiting human review, and complete states use text and icons.
- `UX-007`. Reload restores the same run, selected reachable stage, and trace.
- `UX-008`. Pause and resume follow safe-boundary and immutable-attempt semantics.
- `UX-009`. Keyboard access, focus, live announcements, and non-color cues cover the golden path.
- `UX-010`. The journey and trace remain usable at 390 CSS pixels without page-level horizontal scrolling.

### Azure deployment

- `AZURE-001`. Bicep defines every deployed Azure resource and parameter.
- `AZURE-002`. Azure Container Registry stores immutable frontend and backend image digests.
- `AZURE-003`. Separate Azure Container Apps host the frontend and backend.
- `AZURE-004`. Only the authenticated frontend has public ingress.
- `AZURE-005`. The frontend server proxies same-origin requests to the internal backend.
- `AZURE-006`. Microsoft Entra restricts access to the configured demo audience.
- `AZURE-007`. Azure Database for PostgreSQL Flexible Server stores deployed state.
- `AZURE-008`. The backend and PostgreSQL use private network paths.
- `AZURE-009`. Versioned schema migrations run before a revision receives traffic.
- `AZURE-010`. Key Vault and managed identity deliver secrets without image or browser exposure.
- `AZURE-011`. Log Analytics receives redacted application and deployment logs.
- `AZURE-012`. Health, workspace, and golden-path checks gate traffic shift and preserve rollback.

### Verification

- `PROOF-001`. Docker Compose production images pass a workspace and golden-path smoke test.
- `PROOF-002`. The backend image contains exact governed packages, contracts, and skills without a host mount.
- `PROOF-003`. PostgreSQL state and receipts survive backend restart.
- `PROOF-004`. The proof records a real Codex thread, turn, skill hash, envelope hash, and candidate hash.
- `PROOF-005`. The proof records qualification and study-output Evaluation Artifacts.
- `PROOF-006`. Playwright completes the full path against the Azure URL.
- `PROOF-007`. Downloaded bytes and body-weight content match approval and export hashes.
- `PROOF-008`. A redacted evidence bundle records deployment, browser, run, evaluation, and export proof.
- `PROOF-009`. A deterministic validator resolves every receipt, Artifact Edge, and SHA-256 digest in the evidence bundle.
- `PROOF-010`. Failure, replay, restart, reload, stale decision, and forbidden-authority tests pass.

Existing issues remain authoritative for their current slices. Issues #3 through #12 own deterministic packages, candidate evaluation, retries, promotion, scaffold history, approval, and export. Issues #17 through #27 own the stage-gated workspace and production UI wiring. The demo tickets add only the missing integration, deployment, and proof work.
