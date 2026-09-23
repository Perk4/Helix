# HELIX nonclinical report workbench

HELIX is a synthetic end-to-end prototype for testing nonclinical evidence and report automation patterns. A scientist can follow the study journey, inspect claim-level evidence, run hybrid checks, review report fields, resolve synthetic blockers, record approvals, and perform a separate export action.

The seeded package, interface, and generated artifacts say `SYNTHETIC / NOT FOR SUBMISSION`. The prototype does not certify GLP, Part 11, SEND, eCTD, scientific validity, or FDA acceptance.

## Start the complete stack

Docker Compose starts PostgreSQL 16, FastAPI, and Next.js.

```bash
cp .env.example .env
docker compose up --build
```

Open these URLs:

- Workbench at `http://localhost:3000`.
- API documentation at `http://localhost:8000/docs`.
- Health check at `http://localhost:8000/health`.

PostgreSQL stores one versioned `StudyEvidencePackage` as `JSONB`. Separate tables store workflow events, validation runs, and the exact bytes frozen at export.

The demo starts from the supplied synthetic bundle after its authorization and lock boundary. The workbench exposes the ten-entry frozen manifest, but this prototype does not ingest arbitrary sponsor files.

## Exercise the workflow

1. Open **Study journey** and run hybrid validation.
2. Open **Evidence chain**. Inspect the high-dose terminal body-weight claim and its ten source records.
3. Open **Report assembly**. Review the 37 required template fields and their regulatory references.
4. Record the three synthetic review dispositions.
5. Record pathologist review, peer review, the Quality Assurance Unit statement, and study director approval. These are synthetic workflow records, not authenticated electronic signatures.
6. Export the synthetic package. HELIX assigns content-derived checksums and enables downloads for the report PDF, dataset archive, `define.xml`, and nSDRG PDF.

Export remains disabled until the service derives a `ready_for_export` gate. The client never computes release readiness. The dataset archive contains illustrative CSV files plus machine-readable lineage and workflow audit JSON, not SEND XPT datasets. The generated `define.xml` and nSDRG exercise packaging and lineage only. They do not claim SEND conformance.

Reset the demo to its seeded blocked state by removing the development volume.

```bash
docker compose down -v
```

## Run without containers

Install Node.js 22, Python 3.12 or newer, `uv`, and PostgreSQL 16. Start PostgreSQL and create a database. Then run the API.

```bash
cd backend
uv sync --all-groups
HELIX_DATABASE_URL='postgresql+psycopg://helix:password@localhost:5432/helix' \
  uv run uvicorn app.main:app --reload
```

Run the client in another terminal.

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL='http://127.0.0.1:8000/api/v1' npm run dev
```

The API supports SQLite for isolated automated tests. PostgreSQL is the product storage target.

## Choose the check planner

The default `fixture` planner exercises the same structured tool contract without claiming that an LLM ran. It selects three allowlisted checks. Python executes each check and owns the result.

To test an OpenAI-compatible model, set these values in `.env`:

```dotenv
HELIX_LLM_BASE_URL=https://api.openai.com/v1
HELIX_LLM_MODEL=gpt-5-mini
HELIX_LLM_API_KEY=replace-me
```

The model can propose only these tools:

- `grounded_numeric_claim`.
- `source_severity_match`.
- `human_judgment_required`.

Choose **LLM planner** in the Study journey after setting the credentials. The model cannot create a rule, perform the authoritative calculation, change severity, or turn a failed rule green.

## Verify the prototype

Run the static, unit, API, and production-build checks.

```bash
make test
```

Install Playwright Chromium once, then run the full browser workflow against a fresh isolated database.

```bash
cd frontend && npx playwright install chromium && cd ..
./scripts/verify-live.sh
```

Run the complete release and artifact-download flow against a temporary PostgreSQL 16 cluster.

```bash
./scripts/verify-postgres.sh
```

Set `POSTGRES_BIN` if PostgreSQL is installed outside `/opt/homebrew/opt/postgresql@16/bin`.

Regenerate the OpenAPI document and TypeScript client types after an API schema change.

```bash
make generate
```

## Read the design and regulatory basis

- [`docs/architecture/helix-prototype.md`](docs/architecture/helix-prototype.md) explains the aggregate, API, validation boundary, and alternatives.
- [`docs/architecture/agentic-report-pipeline.md`](docs/architecture/agentic-report-pipeline.md) defines the governed validation-to-drafting process and gate order.
- [`docs/specifications/agentic-report-pipeline.md`](docs/specifications/agentic-report-pipeline.md) defines the buildable commands, state transitions, failures, acceptance criteria, and source traceability for that process.
- [`docs/implementation/first-vertical-slice.md`](docs/implementation/first-vertical-slice.md) defines the frontend-triggered Codex SDK proof.
- [`docs/research/fda-nonclinical-reporting.md`](docs/research/fda-nonclinical-reporting.md) maps 21 CFR Part 58, OECD TG 407, FDA study-data guidance, the Data Standards Catalog, and ICH M4S to product controls.
- [`backend/app/data/report-template.json`](backend/app/data/report-template.json) is the structured 28-day report template.
- [`synthetic-e2e/helix-synthetic-bundle.json`](synthetic-e2e/helix-synthetic-bundle.json) is the deterministic seed package.

The template is a sponsor working structure. FDA defines required report content and submission organization, not one universal Word template.
