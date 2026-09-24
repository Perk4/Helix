# HELIX — nonclinical report workbench

Synthetic prototype for nonclinical evidence + report automation. Everything is
labeled `SYNTHETIC / NOT FOR SUBMISSION`; it does not certify GLP, Part 11, SEND,
eCTD, or FDA acceptance.

## Two things share this repo

1. **The workbench** — FastAPI + Next.js app over one seeded study `STUDY-HLX-028`
   (validation → dispositions → approvals → export), plus a governed **Codex SDK
   section-run** vertical slice.
2. **A standalone draft pipeline** — top-level scripts that draft report sections
   with human-in-the-loop review, using an APIM (Azure OpenAI gateway) model.

Both reuse the same deterministic `section_executor` for the numbers.

## Backend (`backend/app/`) — FastAPI service

- `main.py` — routes + wiring (lifespan seeds the DB)
- `service.py` — `StudyService`: workspace, validation, dispositions, approvals, export + release-gate derivation
- `validation.py` — deterministic rules + optional LLM check *planner* (planner only selects allowlisted checks; Python computes every result)
- `reporting.py` — assembles report sections from the JSON template + claims
- `section_executor.py` — **deterministic per-section calculation** (one `compute_*` per section, a `REGISTRY`, `run_section`/`run_all`). Loads skills from `.agents/skills/helix-section-agent/references/section_skills/`; `build_draft_messages()` pairs computed facts + skill + meta-prompt for an optional LLM render. It never calls an LLM and never invents a value.
- `section_runs.py` — `SectionRunService`: the governed Codex path for `section.5_2_3_body_weight` (eligibility → build `SectionExecutionEnvelope` carrying the executor's facts+provenance → invoke agent → strictly validate the returned `SectionDraftCandidate` → append a Review Scaffold Revision). Produces a **non-promotable** candidate (vertical slice).
- `agents/codex_section_agent.py` — `CodexSectionAgent` over the `openai_codex` SDK, read-only sandbox.
- `schemas.py` — Pydantic models; `StudyEvidencePackage` is the aggregate root. Section-run models: `SectionRunCommand/Eligibility/Receipt`, `SectionDraftCandidate`.
- `repository.py` / `models.py` — SQLAlchemy (JSONB aggregate + append-only events + export bytes + section-run rows)
- `data/report-template.json` — the runtime 28-day template (sections `S1`–`S8`, 37 required fields)

## Standalone draft pipeline (top-level, separate from `backend/app`)

- `draft_pipeline.py` — per section: **COMPUTE** (`section_executor.compute_*`) → **RETRIEVE** (`pipeline/approved_report_retrieval.py` few-shot from approved reports) → **BUILD** (`build_draft_messages`) → **RENDER** (LLM via APIM) → **REVIEW** (human approves / feedback / skip). This is the human-in-the-loop drafting flow.
- `user_review.py` — simpler HITL loop (docx few-shot + CSV figures + template).
- `pipeline/backend_api.py` — re-exports `app.*` under one name so `pipeline` code reaches the backend without import-order pain.
- Needs APIM env vars: `APIM_API_KEY`, `APIM_BASE_URL`, `APIM_MODEL` (draft_pipeline defaults to `gpt-5.5`).

## Two LLM integration paths (don't confuse them)

- **Governed Codex SDK** (`section_runs.py` + `agents/`): audited, schema-validated candidate, provenance-bound, non-promotable. Endpoint `POST /api/v1/studies/{id}/section-runs`. Requires the `openai_codex` SDK.
- **APIM** (`draft_pipeline.py` / `user_review.py`): standalone, few-shot-assisted narrative drafting with a human review loop.

## Frontend (`frontend/src/`)

Next.js workbench: `HelixWorkbench`, `StudyJourney`, `EvidenceChain`, `ReportAssembly`. Fetches one `WorkspaceResponse`; never derives release readiness itself.

## API surface

`/health` · `GET /api/v1/studies` · `.../{id}/workspace` · `POST .../validation-runs` · `POST .../section-runs` · `GET .../claims/{cid}/evidence` · `POST .../validation-results/{rid}/dispositions` · `POST .../approvals` · `POST .../exports` · `GET .../exports/{artifact_id}`

## Commands

- Backend: `cd backend && uv run uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm run dev` (set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1`)
- Section-executor demo: `cd backend && uv run python -m app.section_executor`
- Standalone draft pipeline: set APIM env vars, then `uv run python draft_pipeline.py`
- Tests: `make test`; live proofs: `scripts/verify-live.sh`, `scripts/verify-codex-section-run.sh`, `scripts/verify-postgres.sh`
- DB defaults to **SQLite** (`sqlite+pysqlite:///./helix.db`), no setup. PostgreSQL is the product target; the Docker `.env` points at host `db` and is not needed for local `uv` runs.

## Conventions (important)

- **Calculation = deterministic Python; skills = presentation only.** A skill never computes a number; the executor computes it and hands pre-calculated values to the render step. Do not ask the model for a value no layer computes (e.g. statistical significance is not fabricated).
- Never hallucinate. When a data domain is absent, degrade to `[NEEDS REVIEW]`.
- Every numeric claim/table cell carries **provenance** to source record IDs; the Codex candidate must cite only allowlisted claims and preserve exact computed values.
- The LLM check planner and section agent cannot create a rule, calculate the authoritative value, change severity, or turn a gate green.
- `.docx` files under `synthetic-e2e/data/` are illustrative inputs — not parsed at runtime.

## Section id map

Executor, skills, and section packages use sponsor-docx numbering (`5_2_3_body_weight`, `5_3_1_organ_weights`, …). The runtime JSON template uses flat `S1`–`S8`; body weight is a *field* of `S5`, not its own section. Governance for the agentic path lives in `skills/helix-evidence-pipeline/` (contracts + packages).

## Where to read more

- `docs/adr/` — 24 ADRs (the binding decisions; e.g. ADR-0013 provenance-before-drafting)
- `docs/implementation/first-vertical-slice.md` — the Codex section-run proof
- `docs/architecture/agentic-report-pipeline.md` — the full governed pipeline design

## Gotchas

- Restart uvicorn after editing `.env` (`--reload` watches Python, not `.env`).
- `HELIX_SEED_PATH` resolves relative to the backend dir; the seed loader falls back to `<repo>/synthetic-e2e/`.
- Sex is coded `M`/`F` in the bundle; normalize (`M`→Male, `F`→Female) when filtering, don't match spelled-out strings.
- Skills live under `.agents/skills/helix-section-agent/references/section_skills/` — not `backend/app/`.
