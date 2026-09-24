# UI SLICE 7 (#25): backend-owned nine-stage journey and run events — verification evidence

- Ticket: Steven-Espaillat/Helix#25 (epic #17)
- Branch: `cursor/ui-slice-7-journey-run-events` (git worktree `/Users/perk/src/Helix-ui25`)
- Base: `feat/steven-workspace` @ `cae879a26581627e10e4c0a0417b360cf03a7c87`
- Verified code commit: `19a140282f439b5869b64b27cebc7ff43b4681c8` (the evidence-only commit that follows changes this file only)
- Date: 2026-09-24 (America/Chicago), macOS local run

## Known-red baseline (base `cae879a2`)

The base is red on purpose. Shipped section packages `5_2_3_body_weight` and `5_3_discussion` have
`qualification_status: "pending"` (set upstream in `47c19c4`), so every pinned-run freeze returns
422 `invalid_package_qualification`. Ruff still has 10 errors in `app/approved_report_retrieval.py`
and `app/section_executor.py` because the fix (Perk4/Helix#17) isn't merged yet. This branch does not
touch those files, qualification statuses, or hashes.

## Results versus baseline

All commands run from `steven/helix-prototypes`.

| Check | Command | Base `cae879a2` | This branch | Delta |
|---|---|---|---|---|
| OpenAPI + TS generation | `make generate` (first step of `make test`) | ok | ok | regenerated `openapi.json`, `api-schema.d.ts` |
| Synthetic bundle | `node skills/.../verify-synthetic-bundle.mjs ...` | verified | verified | none |
| Ruff | `cd backend && uv run ruff check app tests scripts` | 10 errors (2 files) | 10 errors (same 2 files) | 0 new |
| Pytest | `cd backend && uv run pytest -p no:cacheprovider` | 84 failed / 66 passed | 84 failed / 81 passed | +15 passed (all new), identical 84-test failure set (diffed) |
| New backend tests | `uv run pytest -p no:cacheprovider tests/test_journey_run_events.py` | n/a | 15 passed | all new pass |
| Frontend typecheck | `cd frontend && npm run typecheck` | pass | pass | none |
| Frontend build | `cd frontend && npm run build` | pass | pass | none |
| Live e2e | `./scripts/verify-live.sh` | 12 passed / 2 failed / 1 skipped | 14 passed / 2 failed / 1 skipped | +2 passed (new client spec), same 2 failures |

`make test` exits non-zero at the ruff step on both base and branch because of the 10 known errors.
The later steps (pytest, typecheck, build) were run directly, with the results shown above.

The 2 verify-live failures are the baseline ones, and both come from the qualification 422:
- `workbench.spec.ts › runs the synthetic study from validation through explicit export`, which shows
  "The HELIX API returned an unexpected error."
- `workbench.spec.ts › renders predecessor run identity and carry-forward counts from the workspace`

The skipped test is the Codex section-run spec, which is also skipped on base.

## Additional local sanity check (temporary, uncommitted override)

This check is not part of the gate and nothing from it is committed. Both shipped section packages were
temporarily marked `passed`, with the backend's own `file_hash(promptfoo suite)`. They were then
restored with `git checkout -- skills/helix-evidence-pipeline/packages/sections`.

| Check | Result with temporary override |
|---|---|
| Pytest | 165 passed, 0 failed (150 existing + 15 new) |
| verify-live | 16 passed, 1 skipped (Codex), 0 failed |

## How the new tests work within the qualification gate

- The seeded projection (Upload current while the legacy array says Gate) needs no Pinned Run and
  uses the shipped tree.
- The qualification-gate test uses a test-local tmp copy of the governed tree with packages
  explicitly `pending`. It asserts that freeze returns 422, the projection is unchanged, and zero run
  events are written.
- The lifecycle, replay/expiry, and pause/resume tests use a test-local tmp copy of the governed tree
  (under pytest `tmp_path`) whose section packages are marked qualified with the hash of their own
  suite file. The shipped `package.json` files are never modified. These tests exercise the journey
  and event contract only and make no qualification claim.
- `run_paused`/`run_resumed` are fixture events appended in the test, because #26 owns the commands.
- The frontend client spec runs in Node with a fake fetch covering the typed 409, refresh, reconnect,
  and dedupe path.

## Logs (local, not committed)

`/tmp/ui25-maketest.log`, `/tmp/ui25-pytest.log`, `/tmp/ui25-verify-live.log`,
`/tmp/ui25-pytest-override.log`, `/tmp/ui25-verify-live-override.log`; the baseline failure list is
from `/tmp/bg-pytest0.log`.
