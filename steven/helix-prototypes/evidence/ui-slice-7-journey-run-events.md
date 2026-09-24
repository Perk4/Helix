# UI SLICE 7 (#25): backend-owned nine-stage journey and run events — verification evidence

- Ticket: Steven-Espaillat/Helix#25 (epic #17)
- Branch: `cursor/ui-slice-7-journey-run-events`
- Base: `feat/steven-workspace` @ `e626f5403829ce8dcd299d744abb9f9002fe7085` (upstream #48, which merged ADO main `97a94b5c`)
- Verified code commit: `420a763473f28035e77486a05804422a81c74adb`. It sits on merge `d9c9fee6` of `e626f540`, and the evidence-only commit that follows changes this file only.
- Earlier history: first verified at `19a14028` on base `cae879a2`. Then `2a639f00` (#17 ruff fix) was merged as `4923536b`.
- Date: 2026-09-24 (America/Chicago), macOS local run

## Environment

- The base was run in a separate detached worktree (`/Users/perk/src/Helix-base-e626`).
- The branch was run in a separate detached worktree at the verified commit (`/Users/perk/src/Helix-ui25-merge`).
- Playwright runs were serialized, and nothing was listening on ports 8010/3010 before each run.

## Results: base `e626f540` vs branch `420a7634`

All commands were run from `steven/helix-prototypes`.

| Check | Command | Base `e626f540` | Branch `420a7634` | Delta |
|---|---|---|---|---|
| Generation | `make generate` (first step of `make test`) | ok, but the committed `openapi.json`/`api-schema.d.ts` are stale (missing `POST /api/v1/studies`) | ok, and the regenerated files are committed (no diff after regeneration) | branch fixes the stale generated types |
| Synthetic bundle | `verify-synthetic-bundle.mjs` | verified | verified | none |
| Ruff | `uv run ruff check app tests scripts` | 4 errors: `intake.py` B905, `main.py` I001, `main.py` B008, `tests/test_intake.py` F401 | the same 4 (same codes and files) | 0 new |
| Pytest | `uv run pytest -p no:cacheprovider` | 84 failed / 87 passed | 84 failed / 105 passed | +18 new passes; failing test names identical (diffed) |
| New tests | `uv run pytest -p no:cacheprovider tests/test_journey_run_events.py` | n/a | 18 passed | all new tests pass |
| Frontend typecheck | `npm run typecheck` | pass | pass | none |
| Frontend build | `npm run build` | pass | pass | none |
| Live e2e | `./scripts/verify-live.sh` | 12 passed / 2 failed / 1 skipped | 14 passed / 2 failed / 1 skipped | +2 new passes (client spec); same 2 failures |

`make test` exits non-zero at ruff on both base and branch because of the 4 upstream errors. I ran the later steps directly.

The 2 verify-live failures are the same on base and branch. Both show "The HELIX API returned an unexpected error." from the qualification 422:
- `workbench.spec.ts › runs the synthetic study from validation through explicit export`
- `workbench.spec.ts › renders predecessor run identity and carry-forward counts from the workspace`

The skipped test is the Codex spec on both.

## Qualification baseline after e626f540

These are facts observed on `e626f540`:

1. **Packages are still `pending`.** `5_2_3_body_weight` and `5_3_discussion` both have `"qualification_status": "pending"`. No section `package.json` changed between `2a639f00` and `e626f540`.
2. **The root cause is still the same 422.** Every freeze returns `invalid_package_qualification` ("Agentic package qualification has not passed"). This was confirmed as follows:
   - The failing set on `e626f540` is byte-identical to the old baseline set (84 tests at `cae879a2`/`2a639f00`).
   - With a temporary, uncommitted override (both packages marked `passed` with the backend's `file_hash(suite)`, then restored with `git checkout`), base `e626f540` runs 171 passed / 0 failed.
3. **Counts moved only by new upstream tests.** The failed count is unchanged (84) with the same names. Passes went from 66 to 87 (+21 from the new `tests/test_intake.py`). Ruff went from 10 errors (fixed by #17) to 4 new errors introduced by the intake merge.
4. **The hash-contract mismatch is unchanged.**
   - `backend/app/run_plans.py` and `scripts/lib/hash.mjs` are untouched between `2a639f00` and `e626f540`.
   - The backend still requires `qualification_hash == file_hash(<promptfoo suite file>)` (`run_plans.py:611`).
   - `scripts/record-qualification.mjs` still writes `canonicalHash({ inputs, outcome })`, so a recorded hash still cannot match what the backend checks.
   - The recorder's changes alter the recorded value but not the scheme:
     - `outcome` now includes `tokens`.
     - A cost guard fails when tokens more than double the previous artifact.
     - The artifact path is fixed to `qualifications/helix-section-agent-qualification.json`.
     - The upstream-branch warning was removed.
   - The recorder still writes only the 5.2.3 package; `5_3_discussion` has no recorder path.
   - `promptfooconfig.yaml` gained A-2/A-3 cases (+81 lines), so its `file_hash` changed too.
   - I did not run the paid recorder.

## Additional local sanity check (temporary, uncommitted override)

This is not the gate, and nothing from it is committed. Both packages were temporarily marked `passed` and then restored with `git checkout -- skills/helix-evidence-pipeline/packages/sections`.

| Check | Base `e626f540` | Branch `d9c9fee6` | Branch `420a7634` |
|---|---|---|---|
| Pytest | 171 passed / 0 failed | 187 passed / 0 failed | 189 passed / 0 failed |
| verify-live | not run | 16 passed / 1 skipped / 0 failed | not re-run (the fix commit changes only backend SSE/failure recording, covered by pytest) |

## Merge `d9c9fee6` (e626f540 into branch): conflicts resolved

- **`backend/app/main.py`:** import blocks only.
  - Kept upstream's `re`, `File`, `Form`, `UploadFile`, `intake.IntakeRejected`/`build_package`, and `StudyPackageRepository` for the `POST /api/v1/studies` intake route.
  - Kept #25's `json`, `time`, `Header`, `Query`, and `run_events` imports for the SSE route.
  - Both routes are present unchanged.
- **`backend/app/service.py`:** auto-merged. Upstream's `derive_release_gate` changes (empty export set is not `exported`; a never-validated package is `blocked`) are compatible with the projection.
- **Regenerated `openapi.json`/`api-schema.d.ts`:** these now include both the intake route and the journey/event schemas.
- **New test:** an intake-uploaded study projects Upload as current, with no run and all later stages pending.

## Review fixes in `420a7634`

- **P1 (r4098493500):** the SSE poll cursor now starts from the validated `Last-Event-ID`, so an empty replay never re-emits retained events.
  - Regression test: reconnect at the latest cursor, with a 1 s window and 0.1 s polling. With no new events the window stays silent. When a new event is appended during the window, only that event (sequence N+1) is emitted.
- **P2 (r4098493508):** `RunConflictError` and `UnknownValidationPackageError` now append `command_failed`.
  - Test: a conflicting freeze (409) records `freeze_run`/`upload`, and an unknown DVP package (404) records `run_data_validation`/`extract`.
- Both tests fail with the fix reverted and pass with it.

## How the new tests work within the qualification gate

- Tests that need a Pinned Run use a test-local tmp copy of the governed tree under pytest `tmp_path`, with section packages marked qualified by the hash of their own suite file. Shipped package data is never modified, and these tests make no qualification claim.
- The gate test uses a tmp copy explicitly `pending` and asserts a 422 with zero run events.
- The `run_paused`/`run_resumed` events are fixture rows (#26 owns the commands).

## Logs (local, not committed)

- Base: `/tmp/e626-{maketest,ruff,pytest,tc,build,verify-live,pytest-override}.log`
- Branch at `d9c9fee6`: `/tmp/ui25m-*.log`
- Branch at `420a7634`: `/tmp/ui25f-*.log`
