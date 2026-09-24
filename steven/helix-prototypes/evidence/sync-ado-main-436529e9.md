# Sync ADO main `436529e9` into `feat/steven-workspace` (+ run-event Alembic migration)

- Branch: `cursor/sync-ado-main-436529e9`, created from `feat/steven-workspace` @ `f5776828` (#18 merged as upstream #49)
- Merged: `main` @ `436529e9c4377d32171e5ce673c3d028ce3ea6e2`. Steven-Espaillat/Helix `main` and Perk4/Helix `main` both point at this commit (checked with `gh api`).
- Commits:
  - `003359a` merge commit, with conflict resolution only
  - `d0a76a2` Alembic migration `9edd082c07ae` for the run-event tables, adoption fix, tests, and regenerated API types
  - `4b313bd` Dockerfile ships `alembic.ini` and `migrations/`
  - `cdbd2b1` Alembic `env.py` no longer disables uvicorn's loggers (found by the live acceptance run below)
- Date: 2026-09-24 (America/Chicago), macOS local run. Each tree ran in its own worktree, and Playwright runs were serialized (ports 8010/3010 were free before each run).

## What ADO main brings

- Chris's Alembic setup: `backend/alembic.ini`, `backend/migrations`, and `database.py`.
  - `create_schema` runs `create_all` on SQLite only and Alembic on every other database.
  - It can adopt ("stamp") an unversioned baseline schema.
- Upload-as-job intake with stage progress: `intake_jobs.py`, `IntakeJobRow`, and a new route.
- Steven's PR 152 P1 fixes, and Annie's PR 158, which packages the skill and contracts into the backend image.

## Conflicts and how they were resolved

| File | Conflict | Resolution |
|---|---|---|
| `backend/app/main.py` | The `fastapi` import block only. | Kept both sides in one sorted block: `BackgroundTasks` (ADO intake job route) plus `Header`/`Query` (#25 run-event SSE route). All routes from both sides are present and unchanged. |
| `backend/app/models.py` | Both sides appended tables at the end of the file. | Kept both: `RunEventRow`/`RunJourneyStateRow` (#25) and `IntakeJobRow` (ADO). |
| `backend/app/database.py` | No textual conflict, because only ADO changed it. | Semantic fix in `d0a76a2` (below). |

Nothing needed a product decision. The `before_commit` event-sync hook, the journey projection, the SSE endpoints, and the run-event tables are unchanged.

## Alembic migration `9edd082c07ae` (revises ADO head `b53f9ec18cf2`)

- **What it creates:** `run_events` (with `uq_run_event_sequence`, the unique `event_id`, and the run_id/study_id indexes) and `run_journey_states` (with the study_id index). The migration was generated with `alembic revision --autogenerate` against a database at `b53f9ec18cf2`, then tidied.
  - These are the only #25-era tables or columns that were created outside Alembic. The #25 diff against the ADO base touches only these two models.
- **Why `database.py` needed a fix:** ADO's `BASELINE_TABLES` was "every model table except `intake_jobs`". After the merge, that set would have included the run-event tables, which are not in the baseline migration. The fix:
  - Excludes the run-event tables from the baseline stamp.
  - When an unversioned database already has those tables (a `feat/steven-workspace` database that was created by `create_all`), checks that their columns match the models, and refuses to stamp if they don't.
  - The revision creates each table only if it is missing, so an adopted database keeps its rows.
- **Where `create_all` still runs:** ADO kept `create_all` for SQLite only, as the test and dev path. PostgreSQL is Alembic-only. No other side path creates the run-event tables.
- **Tests (`tests/test_database_migrations.py`, 9 passed, including PostgreSQL 18 via a throwaway `initdb` cluster):**
  - ADO's two adoption tests, with the head revision updated.
  - Head includes the run-event tables and autogenerate `compare_metadata` is empty (no drift). Runs on SQLite and PostgreSQL.
  - Downgrade to `b53f9ec18cf2`, then to `base`, then upgrade to head is clean, with no drift afterwards. Runs on SQLite and PostgreSQL.
  - A `feat/steven-workspace` `create_all` schema, containing run-event tables and a row, is adopted and upgraded, and the row is kept. Runs on SQLite and PostgreSQL.
  - A drifted `run_events` table is refused and not stamped.

## Prove: base `f5776828` vs ADO main `436529e9` vs merged branch

All commands were run from `steven/helix-prototypes`.

| Check | Base `f5776828` | ADO main `436529e9` | Branch `4b313bd` | Gate |
|---|---|---|---|---|
| Ruff `app tests scripts` | 4: `intake.py` B905, `main.py` I001, `main.py` B008, `test_intake.py` F401 | 15: the base 4, plus 10 in `approved_report_retrieval.py`/`section_executor.py` that #47 had fixed on our side, plus a second `main.py` B008 on the new intake-job route | 5: the base 4 plus ADO's second `main.py` B008 (`File()` default on the intake-job route) | 0 new from this PR; 1 inherited from ADO |
| Pytest | 84 failed / 113 passed | 84 failed / 106 passed | 84 failed / 140 passed (at `cdbd2b1`; 139 at `4b313bd`) | failing set identical to **both** baselines (diffed) |
| Journey/run-event tests | 26/26 | n/a | 26/26 (the PostgreSQL concurrency test ran and now uses the Alembic path) | pass |
| `test_database_migrations.py` | n/a | 2/2 | 10/10 (9 + the logger regression test in `cdbd2b1`) | pass |
| `test_intake_jobs.py` / `test_intake.py` | n/a / 21 | 17 / 21 | 17 / 21 | pass |
| Frontend typecheck / build | pass / pass | pass / pass | pass / pass | pass |
| `make generate` | — | — | regenerated. ADO's committed openapi/TS were missing the intake-job routes, and they are now included | committed |
| `./scripts/verify-live.sh` | 16 passed / 2 failed / 1 skipped | 8 passed / 2 failed / 1 skipped | 16 passed / 2 failed / 1 skipped | same 2 failures on all three |
| Docker build | — | — | docker is not installed on this Mac, so the image was **not built**. See the note below. | not proven |

- **verify-live:** the 2 failures are the same on all three trees. Both come from the qualification 422:
  - `workbench.spec.ts › runs the synthetic study from validation through explicit export`
  - `workbench.spec.ts › renders predecessor run identity and carry-forward counts from the workspace`
- **Qualification baseline: unchanged.**
  - Both section packages are still `qualification_status: "pending"`.
  - The 84 failing tests are the same names on base, ADO main, and the branch.
  - ADO main did not touch `run_plans.py`, the section packages, or the recorder.
- **Temporary override check (not committed; reverted with `git checkout -- skills/helix-evidence-pipeline/packages/sections`):** on the branch, pytest was 223 passed / 0 failed and verify-live was 18 passed / 1 skipped / 0 failed.

## Docker image note

docker/podman are not installed on this Mac, so the Dockerfile was not built. Instead I simulated the image's `COPY` layout and ran `upgrade_to_head` from it.

- ADO's image copied only `backend/app`, but `create_schema` resolves `alembic.ini` and `migrations/` relative to `app/`. On the compose PostgreSQL database, startup would fail with `Path doesn't exist: .../backend/migrations`. This is inherited from ADO main.
- `4b313bd` adds `COPY backend/alembic.ini` and `COPY backend/migrations`. With that change, the simulated layout upgrades to `9edd082c07ae`.
- A real `docker build` / `docker compose up` still needs to be run somewhere with docker.

## Logs

- Unit/verify-live runs (local, not committed): base `/tmp/f577-*.log`, ADO main `/tmp/ado436-*.log`, branch `/tmp/adosync-*.log`.
- Live acceptance backend logs are committed under `sync-ado-main-436529e9/logs/`.

## Live acceptance (Perk bar)

Run on the Mac on 2026-09-24, 17:25–17:40 CT, against the branch at `cdbd2b1`. Committed state only: the qualification override was applied only in the runs labelled **override**, and it was reverted each time.

**Setup**
- **PostgreSQL:** a throwaway PostgreSQL 18.4 cluster, created the same way as the tests (`initdb -U helix -A trust`, `pg_ctl` on `127.0.0.1:55441`, sockets in `/tmp/live/sock`). Each scenario got its own database.
- **Servers:** the backend ran on `:8010` (uvicorn, logs to files) and the frontend on `:3010` (`next build` into `.next-e2e`, then `next start`). I checked the ports were free before every run, and Playwright runs were serialized.
- **Files:** everything is under `evidence/sync-ado-main-436529e9/`. Screenshots are JPEG, about 50–110 KB each. Backend logs are in `logs/` and the driver scripts in `scripts/`. `scripts/zz-live-acceptance.spec.ts` sits outside `frontend/tests`, so it is not part of the suite.

**Demo default database:** the README's primary path is `docker compose up`, which is PostgreSQL. `verify-live.sh` and the `Settings` default use SQLite. Both are covered below.

| # | Item | Result |
|---|---|---|
| 1 | Upload end to end on a fresh, Alembic-migrated PostgreSQL DB | **PASS.** One caveat: the UI has no upload surface (see 1c). |
| 2 | Nine-stage journey from the UI shell on the migrated DB | **Stops at the Upload gate with a 422**, the same as base `f5776828`. With the **override**, all 9 steps pass and SSE is captured live. |
| 3 | Agent-driven stages on the migrated DB | **PASS for the deterministic paths.** The LLM planner is unavailable because no key is set. The Codex section agent was not run because it would be billed. |
| 4 | Pre-Alembic DB (PostgreSQL and SQLite) upgraded by the #19 backend | **PASS.** Nothing crashed, no data was lost, and PostgreSQL was stamped and upgraded to `9edd082c07ae`. |
| 5 | Docker | Not installed on this Mac, and not installed for this run. The image was **not built**. |

### 1. Upload end to end (`upload/`)

**a. Fresh database, then `alembic upgrade head`** (`upload/01-alembic-upgrade.txt`):
```
$ HELIX_DATABASE_URL=postgresql+psycopg://helix@127.0.0.1:55441/helix_live uv run alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade  -> bf13e5f55c15, baseline: study packages, audit events, exports, validation runs, section runs
INFO  [alembic.runtime.migration] Running upgrade bf13e5f55c15 -> ea600664952b, intake jobs
INFO  [alembic.runtime.migration] Running upgrade ea600664952b -> b53f9ec18cf2, bind intake idempotency to request
INFO  [alembic.runtime.migration] Running upgrade b53f9ec18cf2 -> 9edd082c07ae, run events and run journey states (Steven-Espaillat/Helix#25)
$ uv run alembic current   ->  9edd082c07ae (head)
$ psql -c "select version_num from alembic_version"   ->  9edd082c07ae
```
Before the upgrade the database had no tables. Afterwards it had 16, including `intake_jobs`, `run_events`, and `run_journey_states`.

**b. Real sample upload.** I used the repo's sample study, `synthetic-e2e/data/study_data/*.csv` (7 files) plus `synthetic-e2e/data/study_protocol_YZ389.docx`. They were zipped and sent to `POST /api/v1/studies/jobs` exactly as ADO's route expects. I then polled `GET /api/v1/studies/jobs/{id}` every 5 ms (`upload/02-upload-job-poll.txt`):
```
POST /studies/jobs -> 202
t=+   12.3ms status=queued    stage=received  stages_done=['received']
t=+   24.8ms status=running   stage=parsed    stages_done=['parsed','expanded','received','classified']
t=+   32.5ms status=succeeded stage=persisted stages_done=[... 'persisted' ...]
stages: received {bytes 30307, files 1} · expanded {files 8} · classified {data 7, authority 1}
        · parsed {animals 40, body_weights 200, organ_weights 240, microscopic_findings 243, clinical_observations 202, formulation 12}
        · persisted {manifest_entries 8, claims 0}   total_ms 13, slowest_stage persisted
```
The whole job took 13 ms server-side, so the poller saw `queued` → `running` (at `parsed`) → `succeeded`. The per-stage timings and counts recorded by the job cover all 5 stages.

**c. Study created from the upload** (`upload/03-study-created.txt`):
- `GET /api/v1/studies` lists `STUDY-YZ389-LIVE`.
- Its workspace shows 937 records, the 8-entry manifest, and `route: oral gavage`.
- In `psql`, `intake_jobs` has 1 row with status `succeeded`, and `study_packages` has 40 animals and 200 body weights for the study.

UI caveat: the Next.js shell is hard-wired to `STUDY-HLX-028` (`page.tsx`) and has no upload form, both on base and on ADO main. So the "UI screenshot" for this step is the job-status and studies-list API responses rendered in the browser: `upload/upload-job-status.jpg` and `upload/upload-studies-list.jpg`. I did not add an upload UI, because that would be feature work in a sync PR.

### 2. Nine-stage journey from the UI shell

`scripts/zz-live-acceptance.spec.ts` drives the demo path in the real UI. After each step it takes a screenshot and records the server's `journey` projection.

**Committed state, #19 on the migrated DB** (`branch-no-override/`):
- `01-upload-frozen-manifest` passes.
- The run stops at the next action, **Run hybrid validation**, which freezes the Pinned Run and so exits stage 1, Upload.
  - `POST /validation-runs` returns **422** with `invalid_package_qualification` for `section.5_2_3_body_weight` and `section.5_3_discussion` ("Agentic package qualification has not passed").
  - The explicit freeze, `POST /pinned-runs`, returns the same 422 (`branch-no-override/422-detail.txt`).
- The journey projection never leaves `current_stage_id: upload`, and every other stage stays `pending`.
- Screenshot: `branch-no-override/STOP-02-parse-resolve-validate.jpg`.
- This corrects the "known baseline" in the ticket: the qualification 422 blocks the freeze/validate step at the end of stage 1, **not** export. Export is never reached.

**Base `f5776828`, same steps, its own PostgreSQL DB** (created by `create_all`; `base-no-override/`):
- The run stops at the **same step, with the same 422 body** (`base-no-override/422-detail.txt`) and the same journey projection.
- So this stop is not a sync regression.

**SSE in committed state:** no Pinned Run can be created, so there are no run events to stream on either tree.

**With the override** (temporary, reverted, not committed; `override-not-committed-state/`):
- On a fresh DB migrated with `alembic upgrade head`, **all 9 steps pass**, with screenshots `00`–`09`:
  - `01` upload/manifest
  - `02` parse/resolve/validate
  - `03` extract (data validation)
  - `04` draft eligibility (Draft is `ready`; not clicked, see item 3)
  - `05` provenance/evidence chain
  - `06` gates (dispositions)
  - `07` review (four approvals)
  - `08` Final Study Approval
  - `09` export: "Package exported"
- Browser errors: none.
- The journey projection moves as expected:
  - `upload:current`
  - → stages 1–7 `complete`, `traceability:blocked`
  - → `traceability:complete`, `review-export:current`
  - → all 9 `complete`, `workflow_state: exported`
- **Live SSE** (`override-not-committed-state/sse-frames.txt`):
  - `GET .../pinned-runs/RUN-EB6114A58B3200C1/events` returned `200 text/event-stream` and delivered 116 frames.
  - E000001–E000094 were replayed when the stream opened (17:32:16 CT).
  - E000095–E000116 then arrived **live**, one poll after each UI action. Examples: `17:32:18 action_finished` (disposition), `17:32:20 gate_reached`, `17:32:21–24 action_*` (approvals, FSA), `17:32:25 stage_finished` and `export_finished`.

**Backend-log grep for errors** (`08-log-grep.txt`). Pattern: `ERROR|Traceback|OperationalError|ProgrammingError|UndefinedColumn|UndefinedTable|IntegrityError|DataError|sqlalchemy.exc|alembic.*(FAILED|Error)|" 500 `.

| Log | Errors | Notes |
|---|---|---|
| `logs/backend-pg.log` (upload + journey) | **0** | The 422s are the qualification gate and are expected. |
| `logs/backend-override.log` (override journey) | **0** | |
| `logs/backend-agents.log` | **0** | |
| `logs/backend-pre-new-pg.log` (pre-Alembic PostgreSQL) | **0** | |
| `logs/backend-pre-new-sqlite.log` (pre-Alembic SQLite) | **1** | `sqlite3.OperationalError: database is locked`. This comes from the SSE poller thread (`RunEventStore.replay` → `BEGIN IMMEDIATE`) that keeps running after the client disconnects, when a write lands at the same moment. **It reproduces identically on base `f5776828`** (`logs/lock-base.log` vs `logs/lock-branch.log`, via `scripts/sse-then-write.sh`). The engine setup and SSE code are byte-identical to base, so this is a pre-existing #25 SQLite issue, not a sync regression. The write itself succeeded with a 200. Not fixed here. |

**Code fix found by this run (`cdbd2b1`):** before it, the PostgreSQL backend log went silent right after startup. There was no `Application startup complete`, no request lines, and there would have been no 500 tracebacks (`00-logging-silenced-before-fix.txt`).
- Cause: ADO's `migrations/env.py` calls `fileConfig(alembic.ini)` with the default `disable_existing_loggers=True`, and `create_schema` runs Alembic inside the server process. That disabled `uvicorn.error` and `uvicorn.access`.
- This is inherited from ADO main, where `env.py` is identical.
- The fix passes `disable_existing_loggers=False`, and a regression test is added in `test_database_migrations.py`.
- Without that fix, the log grep above would have been a meaningless 0.

### 3. Agent-driven stages (`04-agents-override.txt`, `04-executor.txt`, `05-uploaded-study-run-gate.txt`)

**Env keys (present or absent only; values never read):**

| Key | Status |
|---|---|
| `HELIX_LLM_API_KEY` | unset |
| `HELIX_LLM_BASE_URL` | unset |
| `HELIX_LLM_MODEL` | unset |
| `OPENAI_API_KEY` | unset |
| `ANTHROPIC_API_KEY` | unset |
| `CODEX_API_KEY` | unset |
| `GEMINI_API_KEY` | unset |

- There is no `.env` in `steven/helix-prototypes`, `backend/`, or the repo root. Only `.env.example` exists.
- `~/.codex/auth.json` **exists**. The Codex SDK section agent would therefore run on this machine's Codex login and be billed.

**Results, on a migrated PostgreSQL DB (override, needed to freeze a run):**
- **LLM planner** (`planner: openai_compatible`): `503 {"detail":"HELIX_LLM_API_KEY is not configured"}`. It fails cleanly with no spend.
- **Hybrid validation, fixture planner** (deterministic): `201`.
  - It returned 13 results with `llm_used: false`, and 3 of them are blocker failures (VR-004/005/006), as seeded.
  - It froze `RUN-EB6114A58B3200C1`.
- **Data validation `validation.body_weight`** (deterministic recompute): `201`, `status: passed`.
  - Claims included `C-BW-MEAN-D1-G1-F 247.0 g`, `C-BW-SD-D1-G1-F 3.3 g`, and so on.
- **Rows written:**
  - `validation_runs` 1
  - `data_validation_runs` 2
  - `pinned_runs` 1
  - `run_events` 94, sequences 1–94 with no gaps
  - `run_journey_states` `last_sequence` 94
- **SSE replay** returned 94 frames: stage_started 6, stage_finished 7, action_started 40, action_finished 40, gate_reached 1.
- **Section executor** (`section_executor.py`, deterministic, never calls an LLM): I ran all 14 registered sections on packages read back from PostgreSQL, for both the seeded study and the **uploaded** `STUDY-YZ389-LIVE`.
  - For the uploaded study it computed, for example, `5_2_3_body_weight` with 40 provenance links ("Male G1 Day 1 mean 231.5 g (n=5)" ← `BW-M101-1..BW-M105-1`) and `5_3_1_organ_weights` with 48.
  - `4_deviations`, `5_3_2_macroscopic`, and `5_3_4_conclusion` report `data_available=False`, as designed.
  - The executor is pure: it writes no rows.
- **Section run (Codex SDK agent):** **not run.** It is not on the demo path (the demo never clicks Draft), and it would bill the Codex login. With packages `pending`, the freeze it depends on is 422 anyway.

**Uploaded studies cannot start a run on any tree** (`05-uploaded-study-run-gate.txt`):
- `validation-runs` and `pinned-runs` on an uploaded study return 422 `manifest_unauthorized` for the uploaded `A-*` entries, plus `manifest_entry_missing` for the seeded authorized entries.
- This happens identically on #19 (job upload), ADO main `436529e9` (sync upload), and base `f5776828` (sync upload).
- The run plan authorizes only the seeded manifest. This is a product gap between ADO's intake and the #25 run plans, not a sync regression. I left it alone, because closing it needs a product decision about who authorizes an uploaded manifest.

### 4. Existing pre-Alembic DB (`06-pre-alembic-postgres.txt`, `07-pre-alembic-sqlite.txt`)

For each database type I followed the same steps (`scripts/pre-alembic.sh`):
1. Start base `f5776828` on an empty DB, so its tables are created by `create_all`.
2. Write through its API: a fixture validation that freezes the run and emits run events, data validation, dispositions VR-004 and VR-006, and a sync upload of `STUDY-YZ389-PRE`. The override was applied in the base worktree only for this step, then reverted.
3. Stop base.
4. Start the #19 backend with no override against the same DB.

| Table | PostgreSQL before | PostgreSQL after | SQLite before | SQLite after |
|---|---|---|---|---|
| `alembic_version` | *absent* | **`9edd082c07ae`** | *absent* | *absent* (SQLite uses `create_all` by ADO's design) |
| `study_packages` | 2 | 3 (+1 post-upgrade upload) | 2 | 3 |
| `run_events` | 97 | 101 (+4 from the post-upgrade disposition; sequence continued at 98) | 97 | 101 |
| `run_journey_states` | 1 | 1 | 1 | 1 |
| `audit_events` | 13 | 14 | 13 | 14 |
| `pinned_runs` / `validation_runs` / `data_validation_runs` | 1 / 1 / 2 | 1 / 1 / 2 | 1 / 1 / 2 | 1 / 1 / 2 |
| `intake_jobs` | *absent* | 1 (created by the upgrade; 1 post-upgrade job) | *absent* | 1 |

**#19 startup log on the PostgreSQL DB:**
```
Running stamp_revision  -> bf13e5f55c15
Running upgrade bf13e5f55c15 -> ea600664952b, intake jobs
Running upgrade ea600664952b -> b53f9ec18cf2, bind intake idempotency to request
Running upgrade b53f9ec18cf2 -> 9edd082c07ae, run events and run journey states (Steven-Espaillat/Helix#25)
Application startup complete.
```
- After the upgrade, the old `journey.run` (`RUN-EB6114A58B3200C1`, `latest_event_id …E000097`) and its dispositions were still served.
- SSE replayed all 97 pre-existing events.
- A new disposition returned 200, and a new job upload succeeded.
- Every count change is accounted for by these post-upgrade writes, so nothing was lost.
- No manual step is needed: the adoption is automatic, so there is no README change.

### 5. Docker

docker/podman are not installed, and I did not install Docker Desktop. The image was not built; see the Docker image note above.

### Code changes in this round

- `cdbd2b1` `backend/migrations/env.py`: `fileConfig(..., disable_existing_loggers=False)`, plus the `test_running_migrations_in_process_keeps_the_server_loggers_enabled` regression test. This was needed so the synced service logs its requests and errors on PostgreSQL.
- There were no other code changes. The committed evidence and scripts are under `evidence/` only.
- After this change the suite is still clean against the pre-merge baseline: ruff has the same 5 errors; pytest is 84 failed / 140 passed with a failing set identical to base; journey + migrations + intake-jobs tests are 53/53 (26 + 10 + 17, with PostgreSQL).
