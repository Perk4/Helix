# HELIX agentic end-to-end demo grill

The user approved autonomous answers. Each decision below records the question, recommendation, adopted answer, and evidence.

## 1. What is the product outcome?

**Question.** Is this a production regulatory platform or a deployable synthetic demonstration?

**Recommendation.** Build a deployable synthetic demonstration that proves the architecture without claiming regulatory compliance.

**Decision.** Adopt the recommendation. The demo keeps `SYNTHETIC / NOT FOR SUBMISSION` visible in the UI, receipts, and exports.

**Evidence.** Both reviewed architecture documents define HELIX as a synthetic prototype and list formal GLP, Part 11, SEND, eCTD, privacy, and security qualification as absent.

## 2. How much of the report should the demo automate?

**Question.** Must the first proof execute every report section?

**Recommendation.** Prove one body-weight section from frozen evidence through export. Keep the other report content seeded and deterministic.

**Decision.** Adopt the recommendation. One complete path is more credible than 22 partial packages.

**Evidence.** The current implementation and issue #1 already prove a real body-weight Codex run. The target pipeline deliberately starts with one vertical slice.

## 3. Must agent output enter the exported report?

**Question.** Is a stored but isolated candidate sufficient for an end-to-end demo?

**Recommendation.** No. Qualify one package version, pass every deterministic and qualitative check, require human review, promote the candidate through deterministic code, and include its exact hash in export.

**Decision.** Adopt the recommendation. Preserve earlier `vertical_slice` runs as unpromotable. A later qualified package version may set `promotion_allowed` only after the existing promotion requirements pass.

**Evidence.** The reviewed baseline states that the current candidate has no promotion or export effect. That boundary protects the prototype today but does not prove an agent contribution to final output.

## 4. Who owns workflow state?

**Question.** Should the browser, Codex SDK, or backend advance the workflow?

**Recommendation.** The backend owns Workflow Run and gate state. Codex executes eligible agent steps. The browser renders persisted state and submits commands.

**Decision.** Adopt the recommendation.

**Evidence.** ADR-0009 gives Codex coordination responsibility without gate authority. The architecture documents make FastAPI the source of truth.

## 5. What does Codex control?

**Question.** May Codex calculate values or decide deterministic checks?

**Recommendation.** No. Codex receives scoped envelopes, explicitly invokes vetted skills, and returns schema-bound candidates. Versioned Python executors calculate values and Rule Bundles decide deterministic results.

**Decision.** Adopt the recommendation.

**Evidence.** ADR-0001, ADR-0013, ADR-0015, and ADR-0021 separate model behavior from gate authority.

## 6. What counts as a skill invocation?

**Question.** Can an end user choose or upload arbitrary skills?

**Recommendation.** No. The backend maps each governed workflow step to a reviewed skill name and exact content hash. Prompts invoke the skill explicitly. The user starts a bounded workflow rather than selecting code or instructions.

**Decision.** Adopt the recommendation.

**Evidence.** OpenAI skill guidance recommends developer-integrated skills and warns against exposing an open skill repository to end users. The current section adapter explicitly invokes `$helix-section-agent`.

## 7. How should deterministic and qualitative checks interact?

**Question.** Can either check type substitute for the other?

**Recommendation.** No. Deterministic checks can block or permit transitions. Qualitative evaluations can produce `review_required` or a warning, but a pass grants no authority.

**Decision.** Adopt the recommendation. The UI labels each result by authority class.

**Evidence.** ADR-0007 and ADR-0021 require separate test and authority paths.

## 8. Which qualitative evaluation is enough for the demo?

**Question.** Does the demo need a broad evaluation framework?

**Recommendation.** Run the existing paired skill qualification suite before use and one study-output evaluation against the exact body-weight candidate. Persist both artifacts.

**Decision.** Adopt the recommendation. Broader benchmark management stays out of scope.

**Evidence.** The current Section Package names both suite versions, but the as-built architecture does not enforce or persist them.

## 9. What should the UI show as agentic activity?

**Question.** Is animated client state enough?

**Recommendation.** No. Show a live Workflow Trace built from persisted backend events and Codex turn notifications. Each row names the actor, step, status, authority, input, output, and receipt.

**Decision.** Adopt the recommendation. The UI must not use a timer to imply progress on the production path.

**Evidence.** Existing UI issues #21 and #25 already distinguish reference animation from backend-owned events.

## 10. How do backend events map to the nine-stage workspace?

**Question.** Should every executor become a top-level stage?

**Recommendation.** Keep the nine-stage Workspace Journey. Show the finer pipeline events inside the active stage.

**Decision.** Adopt the recommendation. Human Gates remain visually distinct from Agent Steps.

**Evidence.** ADR-0022 and issue #17 define the nine-stage journey. The pipeline architecture defines twelve finer state transitions.

## 11. What does pause mean?

**Question.** Can HELIX promise a lossless mid-turn pause?

**Recommendation.** No. Pause takes effect at a safe step boundary. If a Codex turn is active, HELIX requests interruption and records the attempt as interrupted. Resume starts a new immutable attempt with the same governed inputs.

**Decision.** Adopt the recommendation. UI copy must not imply that an in-memory model turn was frozen.

**Evidence.** The installed Codex Python SDK exposes turn streaming and interruption. It does not expose a mid-turn pause primitive.

## 12. What is the trace data shape?

**Question.** Is the current embedded event list enough?

**Recommendation.** Add four linked records around the existing `StudyEvidencePackage`.

The records are:

- `WorkflowRun`. One pinned execution and its current status.
- `StepReceipt`. One immutable attempt for a deterministic executor, Skill Invocation, evaluation, Human Gate, or export action.
- `TraceArtifact`. One content-addressed input, output, receipt, prompt, candidate, evaluation, or export manifest.
- `ArtifactEdge`. One typed relation between two Trace Artifacts.

**Decision.** Adopt the recommendation. Build the Workspace Journey and Workflow Trace as read models from these records. Do not add a third mutable event representation.

**Evidence.** The architecture review identifies divergence risk between embedded package events and relational audit rows.

## 13. What must a Step Receipt contain?

**Question.** Which facts make a step reproducible and auditable?

**Recommendation.** Record the run, step, attempt, actor kind, authority class, status, timestamps, idempotency key, parent receipt, exact input and output artifact IDs, skill or executor identity and hash, model and thread identity when used, and structured failure codes.

**Decision.** Adopt the recommendation. Token and latency measures are operational metadata, not gate evidence.

## 14. What must an Evaluation Artifact contain?

**Question.** Is a pass or fail string sufficient?

**Recommendation.** No. Bind the suite and rubric version, evaluator configuration, input candidate hash, structured result, reasons, raw result artifact hash, timestamp, and authority class.

**Decision.** Adopt the recommendation. A study-output pass remains advisory.

## 15. Should hidden model reasoning be stored?

**Question.** Does robust provenance require chain-of-thought capture?

**Recommendation.** No. Store governed prompts, structured inputs, tool and skill receipts, final schema-bound outputs, and public progress events. Do not request or store hidden reasoning.

**Decision.** Adopt the recommendation.

## 16. How should retries work?

**Question.** What happens after a crash, duplicate request, or failed attempt?

**Recommendation.** Commands use idempotency keys. Each attempt is immutable. Startup reconciliation finds unfinished work. Exact replay returns the prior receipt. A changed payload with the same key returns `409`.

**Decision.** Adopt the recommendation.

**Evidence.** The current section run and export paths already establish this behavior. ADR-0016 bounds candidate retries.

## 17. Which architecture shape should be used?

**Question.** Should HELIX keep the synchronous JSONB shape, add a durable PostgreSQL trace ledger, or move to Azure-native queues and functions?

**Recommendation.** Add the durable PostgreSQL trace ledger while keeping FastAPI as the orchestration boundary. Use the Codex SDK turn stream for visible progress. Defer Service Bus, Durable Functions, and multiple workers.

**Decision.** Adopt the recommendation. It survives reloads and retries without adding a new cloud control plane.

## 18. Which Azure runtime should host the demo?

**Question.** Should the demo use Static Web Apps and App Service, Container Apps, or AKS?

**Recommendation.** Use separate Azure Container Apps for the Next.js frontend and FastAPI backend. Use Azure Database for PostgreSQL Flexible Server, Azure Container Registry, Key Vault, and Log Analytics.

**Decision.** Adopt the recommendation. Use Bicep for infrastructure as code.

**Evidence.** Both applications already have production container images. Container Apps supports internal ingress, revisions, managed secrets, and container scaling. AKS adds unnecessary operations. Static hosting does not match the standalone Next.js server.

## 19. Which network boundary is acceptable?

**Question.** May the browser call a public backend that can spend model tokens?

**Recommendation.** No. Expose only the frontend. The frontend server proxies same-origin API requests to an internal backend Container App. Protect the public frontend with Microsoft Entra authentication for the demo audience.

**Decision.** Adopt the recommendation. Keep the backend and PostgreSQL on private network paths.

## 20. How should secrets reach Codex?

**Question.** May a Codex credential be baked into an image or exposed to the browser?

**Recommendation.** No. Store the credential in Key Vault. Give the backend managed identity access to that secret. Authenticate the Python Codex client with the API key at runtime.

**Decision.** Adopt the recommendation. Logs and evidence bundles must redact secret values.

**Evidence.** The installed `openai-codex` package supports `login_api_key`. Key Vault is designed for API keys and managed access.

## 21. What database is authoritative in Azure?

**Question.** Is SQLite acceptable for the deployed proof?

**Recommendation.** No. Use PostgreSQL Flexible Server. Run schema migrations before serving traffic and prove persistence across backend revisions.

**Decision.** Adopt the recommendation. SQLite remains an isolated test dependency.

## 22. Where should export bytes live?

**Question.** Does the demo need Blob Storage now?

**Recommendation.** No. Keep exact export bytes in PostgreSQL for this bounded synthetic demo. Define Blob Storage as a later seam when artifact size or retention requires it.

**Decision.** Adopt the recommendation. This avoids a second artifact authority.

## 23. What deployment safety is required?

**Question.** Can the demo deploy an untested revision directly?

**Recommendation.** No. Build immutable images, deploy a new Container Apps revision, run health and workspace smoke checks, run the golden path, then shift traffic. Retain the previous revision for rollback.

**Decision.** Adopt the recommendation.

## 24. What proof artifact closes the work?

**Question.** What must a reviewer inspect to believe the architecture works?

**Recommendation.** Publish one redacted evidence bundle from Azure. Include deployment identifiers and image digests, the Workflow Run and every Step Receipt, input and output artifact hashes, deterministic results, qualitative evaluation artifacts, Codex thread and skill hashes, browser screenshots, the export manifest, downloaded checksums, and the verification command output.

**Decision.** Adopt the recommendation. The proof fails if any edge or hash does not resolve.

## 25. What is explicitly out of scope?

**Question.** Which adjacent capabilities should the demo refuse to imply?

**Recommendation.** Exclude arbitrary sponsor uploads, real study data, multi-tenant authorization, electronic signatures, SEND or eCTD validation, all-section automation, multi-region disaster recovery, high availability, Azure OpenAI compatibility, and regulatory claims.

**Decision.** Adopt the recommendation.

## 26. What is the release predicate?

**Question.** When can the architecture demo be called complete?

**Recommendation.** One authenticated user opens the Azure URL, authorizes the synthetic manifest, starts a backend-owned Workflow Run, watches real persisted deterministic and Codex skill steps, reviews the linked evaluation and provenance artifacts, records the required synthetic disposition and approvals, exports the package, downloads the artifact, and verifies that the exported body-weight content and every displayed receipt resolve to the exact approved hashes in PostgreSQL.

**Decision.** Adopt the recommendation. A local-only run, mocked Codex response, fake progress timer, SQLite database, or unverified screenshot does not pass.
