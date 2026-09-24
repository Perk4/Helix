# Sync ADO main `436529e9` into `feat/steven-workspace` (+ run-event Alembic migration)

- Branch: `cursor/sync-ado-main-436529e9`, created from `feat/steven-workspace` @ `f5776828` (#18 merged as upstream #49)
- Merged: `main` @ `436529e9c4377d32171e5ce673c3d028ce3ea6e2`. Steven-Espaillat/Helix `main` and Perk4/Helix `main` both point at this commit (checked with `gh api`).
- Commits:
  - `003359a` merge commit, with conflict resolution only
  - `d0a76a2` Alembic migration `9edd082c07ae` for the run-event tables, adoption fix, tests, and regenerated API types
  - `4b313bd` Dockerfile ships `alembic.ini` and `migrations/`
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
| Pytest | 84 failed / 113 passed | 84 failed / 106 passed | 84 failed / 139 passed | failing set identical to **both** baselines (diffed) |
| Journey/run-event tests | 26/26 | n/a | 26/26 (the PostgreSQL concurrency test ran and now uses the Alembic path) | pass |
| `test_database_migrations.py` | n/a | 2/2 | 9/9 | pass |
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

## Logs (local, not committed)

- Base: `/tmp/f577-*.log`, `/tmp/Helix-base-f577-*.log`
- ADO main: `/tmp/ado436-*.log`, `/tmp/Helix-ado-436-*.log`
- Branch: `/tmp/adosync-*.log`
