# HELIX — nonclinical report workbench

Synthetic prototype for nonclinical evidence + report automation. Everything is
labeled `SYNTHETIC / NOT FOR SUBMISSION`; it does not certify GLP, Part 11, SEND,
eCTD, or FDA acceptance.

## Architecture map

- `backend/app/` — FastAPI service
  - `main.py` — routes + app wiring (lifespan seeds the DB)
  - `service.py` — `StudyService`: all commands (validate, disposition, approve, export) + gate derivation
  - `validation.py` — deterministic rules + optional LLM check *planner* (planner only selects checks; Python computes every result)
  - `reporting.py` — assembles report sections from the JSON template + claims
  - `section_executor.py` — deterministic per-section calculation (one `compute_*` per section); pairs each with its skill for an optional LLM render
  - `section_skills/` — 14 section skills + `meta_prompt_pathology_narrative.md` (global narrative style)
  - `schemas.py` — Pydantic models; `StudyEvidencePackage` is the aggregate root
  - `repository.py` / `models.py` — SQLAlchemy persistence (JSONB aggregate + append-only events + export bytes)
  - `data/report-template.json` — the structured 28-day template (8 sections, 37 required fields) the app actually uses
- `frontend/src/` — Next.js workbench (`HelixWorkbench`, `StudyJourney`, `EvidenceChain`, `ReportAssembly`)
- `synthetic-e2e/helix-synthetic-bundle.json` — deterministic seed study `STUDY-HLX-028`

## Commands

- Backend: `cd backend && uv run uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm run dev` (set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1`)
- Section executor demo: `cd backend && uv run python -m app.section_executor`
- Tests: `make test`
- DB: defaults to **SQLite** (`sqlite+pysqlite:///./helix.db`) with no setup. PostgreSQL is the product target; the Docker `.env` points at host `db` and is not needed for local `uv` runs.

## Conventions (important)

- **Calculation is deterministic Python; skills are presentation only.** A skill never computes a number — the executor computes it and hands pre-calculated values to the LLM render step.
- Never hallucinate values. When a data domain is absent, degrade to `[NEEDS REVIEW]` rather than inventing content.
- Every numeric claim carries **provenance** back to source record IDs.
- The LLM check planner can only select allowlisted checks; it cannot create a rule, calculate the authoritative value, change severity, or turn a failure green.
- The `.docx` files under `synthetic-e2e/data/` are illustrative sample inputs — not parsed at runtime. The runtime template is `backend/app/data/report-template.json`.

## Section id map (executor / skills vs template)

The executor + skills use the sponsor-docx numbering (`5_2_3_body_weight`, `5_3_1_organ_weights`, …). The runtime JSON template uses flat sections `S1`–`S8`; body weight is a *field* of `S5`, not its own section.

## Gotchas

- Restart uvicorn after editing `.env` (`--reload` watches Python, not `.env`).
- `HELIX_SEED_PATH` is resolved relative to the backend dir; the seed loader falls back to `<repo>/synthetic-e2e/`.
- Sex is coded `M`/`F` in this bundle; when filtering records, normalize (`M`→Male, `F`→Female) rather than matching spelled-out strings.
