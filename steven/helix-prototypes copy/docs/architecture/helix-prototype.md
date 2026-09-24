# HELIX prototype architecture

## Problem

The existing artifacts define a strong interaction model and a synthetic `StudyEvidencePackage`, but they are static files. The prototype needs a real browser client, a Python service, durable PostgreSQL state, deterministic validation, optional LLM planning, append-only review history, and an explicit export gate. The design must preserve one source of truth and must not imply regulatory approval.

## Grounded system

The supplied system already has four useful parts:

- `helix-spec-sheet (1).md` defines the user, source taxonomy, authority hierarchy, and bounded-agent concept.
- `skills/helix-evidence-pipeline/references/schema.md` defines the canonical aggregate and its invariants.
- `synthetic-e2e/helix-synthetic-bundle.json` contains 1,662 study records, three claims, 14 provenance edges, three deliberate blockers, and eight report sections.
- `helix-e2e-workbench.html` defines the study journey, evidence chain, report assembly, human gate, and separate export action.

The static workbench shows `263.8 g` for the high-dose terminal mean. The generated package contains `286.2 g`. The application treats the package as authoritative and recomputes the value from its ten source records.

## Data shape

`StudyEvidencePackage` is the aggregate root.

```text
StudyEvidencePackage
  package_id
  label
  study
  manifest[]
  records{domain -> record[]}
  report_sections[]
  claims[]
  provenance_edges[]
  validation_results[]
  review_dispositions[]
  approvals[]
  gate_decisions[]
  export_artifacts[]
  events[]
```

The application stores the aggregate as PostgreSQL `JSONB`. Separate tables store append-only audit events, validation-run snapshots, and immutable exported bytes. The service locks one aggregate row for each command and increments its version. Internal validation functions accept only parsed domain models.

## Usage from the caller's view

Start the whole prototype.

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:3000`. Run hybrid validation from the study journey. Inspect the evidence chain for a claim. Resolve the three synthetic findings. Record the required review roles. Export the synthetic package with a separate action.

Call the API directly.

```bash
curl http://localhost:8000/api/v1/studies/STUDY-HLX-028/workspace
curl -X POST http://localhost:8000/api/v1/studies/STUDY-HLX-028/validation-runs \
  -H 'content-type: application/json' \
  -d '{"planner":"fixture"}'
```

The `fixture` planner proves the tool contract without claiming that an LLM ran. Provide the model credentials and choose the LLM planner in the workbench to test real structured tool planning. Deterministic tools still decide every validation result.

## Candidate A

Candidate A stores the complete package as one versioned `JSONB` aggregate. It adds event, validation-run, and immutable export-file tables. One application service owns gate derivation, dispositions, approvals, and export.

```text
Next.js client
    |
FastAPI boundary
    |
StudyService
  |-- pure validation registry
  |-- constrained check planner
  |-- report assembler
    |
StudyPackageRepository
    |
PostgreSQL JSONB + append-only event tables
```

The interface is deep. A small HTTP surface hides locking, validation, gate derivation, history, artifact generation, and idempotency. The tradeoff is weaker row-level queryability inside study records.

## Candidate B

Candidate B normalizes every manifest entry, animal, measurement, finding, claim, edge, result, disposition, approval, section, artifact, and event into separate tables. Services coordinate joins across those tables.

```text
Next.js client
    |
FastAPI routers
    |
manifest service + evidence service + report service + gate service
    |
15 or more normalized PostgreSQL tables
```

This shape gives the database more foreign-key enforcement and better cross-study analytics. It exposes storage joins to more services, duplicates the existing aggregate schema, and makes a throwaway prototype expensive to change.

## Synthesis decision

Candidate A is the base. It preserves the supplied aggregate, minimizes translation code, and makes each command atomic. Candidate B contributes a separate event table, stable identifiers, unique idempotency keys, and indexes on `study_id` and package version. The fully normalized evidence graph is rejected until a real query workload proves that JSONB is insufficient.

An event-sourced design was also considered. It would make audit history central, but every read would depend on a projection and migration policy. That cost does not earn its place in a pattern-testing prototype.

The environment exposes no child-agent runner, so the two shapes were compared locally rather than through a cross-model arena. The implementation keeps the seam narrow enough to replace the repository after prototype testing.

## Shape

### Backend signatures

```python
class StudyService:
    def workspace(self, study_id: StudyId) -> Workspace: ...
    def run_validation(self, study_id: StudyId, request: ValidationRequest) -> ValidationRun: ...
    def evidence(self, study_id: StudyId, claim_id: ClaimId) -> EvidenceChain: ...
    def disposition(self, study_id: StudyId, command: DispositionCommand) -> Workspace: ...
    def approve(self, study_id: StudyId, command: ApprovalCommand) -> Workspace: ...
    def export(self, study_id: StudyId, command: ExportCommand) -> ExportReceipt: ...
```

The FastAPI layer parses request bodies and maps domain errors to HTTP responses. Pure functions compute claims, validation results, structured report blocks, and gates. The repository owns SQLAlchemy and transaction details.

### Hybrid validation contract

```text
Planner input
  synthetic study summary
  report claims
  narrative blocks
  allowlisted tool descriptions

Planner output
  CheckProposal[]
    grounded_numeric_claim(claim_id)
    source_severity_match(claim_id)
    human_judgment_required(claim_id)

Tool execution
  typed proposal -> deterministic function -> ValidationResult
```

An LLM can select checks. It cannot create a rule, calculate the authoritative value, set severity, or mark a failure as passed. Unsupported tool names fail at the API boundary.

### Frontend shape

FastAPI's OpenAPI document generates TypeScript API types. `HelixWorkbench` owns only view selection, selected stage, selected claim, selected report section, and request state. The server owns study state and release decisions.

```text
app/page.tsx
  HelixWorkbench
    StudyJourney
    EvidenceChain
    ReportAssembly
    EvidenceDrawer
```

The frontend fetches one `WorkspaceResponse` and refreshes it after every command. It never derives release readiness independently.

## Tradeoffs accepted

- We accept a coarse JSONB aggregate in exchange for rapid schema changes and atomic prototype commands.
- We accept whole-package reads for one small synthetic study in exchange for a smaller repository interface.
- We accept an offline fixture planner by default in exchange for a runnable prototype without credentials. The UI names the active planner and whether an LLM ran.
- We accept sponsor-template fields rather than a claimed FDA document template. Regulations define required content and dossier placement, not one universal Word layout.

## Open questions and risks

- Which sponsor report templates and signed examples can the team legally use for pattern retrieval?
- Which application context, FDA Center, and study start date should drive the first real Data Standards Catalog decision?
- Which production identity provider and electronic-signature controls would support a formal Part 11 assessment?
- Which SEND validator and licensed controlled terminology source will replace the prototype rule bundle?
- When cross-study analytics become real, which access paths justify normalizing selected JSONB records?

## Export boundary

Explicit export generates deterministic downloadable bytes, hashes those bytes, and stores the exact immutable payloads in the database. Downloads read the stored payload rather than regenerating an already exported artifact. The synthetic report and nSDRG are valid PDF containers. The dataset archive contains domain CSV files, claim-level lineage JSON, and workflow audit JSON, and `define.xml` is well-formed XML. They test packaging, lineage, checksums, and download behavior. They are deliberately labeled as illustrative and are not SEND XPT, a conformant define.xml, or submission-ready content.

## Verification

```bash
make test
./scripts/verify-live.sh
./scripts/verify-postgres.sh
```

The static suite verifies the 1,662-record source bundle, Python rules, API workflow, strict LLM planning contract, generated TypeScript types, and production frontend build. The live suite drives Chromium from blocked validation through report correction, approvals, export, and a PDF download. The PostgreSQL suite creates a temporary PostgreSQL 16 cluster, verifies JSONB storage, runs the full release flow, checks idempotency, and compares downloaded bytes with the recorded SHA-256 checksum.
