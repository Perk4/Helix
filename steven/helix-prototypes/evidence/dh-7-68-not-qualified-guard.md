# DH-7 (#68): "Not qualified" label + export fails closed for demo-frozen runs

Spec: Steven-Espaillat/Helix#64 (stories 26-29). Ticket: Steven-Espaillat/Helix#68. Base: `feat/steven-workspace` @ `d4e5015a` (fetched, SHA verified). Worktree `/Users/perk/src/Helix-dh7` (via `git worktree add`), branch `cursor/dh-7-68-not-qualified-guard`. Local only, Stevens-MacBook-Pro, 2026-09-25 CT. No Codex or OpenAI calls.

**Ports and DB.** `docs/ui-lanes-ownership.md` at `d4e5015a` assigns no 194xx range, so this ticket used: dev API 19434 / web 19435 with `/tmp/helix-dh7.db` (fresh per start); verify-live 19444/19445; parity 19454/19455; pytest `/tmp/helix-dh7-pytest.db` (head) and `/tmp/helix-dh7-base-pytest.db` (base). Every command set the flag, ports, and DB inline. `verify-live.sh` and `verify-parity.sh` always create their own `mktemp` SQLite DB; that path is not overridable.

## Guard design (credit: Design Critic proposal, Perk4/Helix#25 comment 5827577860)
- `app/qualification.py`: pure helper `demo_frozen_export_refusal(pinned_run) -> str | None` returns `DEMO_EXPORT_REFUSAL` when `demo_packages_of(pinned_run)` is non-empty. It returns a message, not an exception, because `approved_exports` already imports `qualification` (no circular import).
- `app/approved_exports.py` → `materialize_approved_artifacts()`: first statement raises `ApprovedExportError(refusal)`. `service._export_command` already maps that to `WorkflowConflictError` → **409** with a string `detail`.
- Keyed on the frozen run, not on the flag: flag on over a qualified tree skips nothing, so that run is strict and exports 200 (test below).
- Slice-11 export request/response schemas unchanged. Strict runs and flag-off behaviour unchanged. `demo_export_value` stays in place (now unreachable for export; left for a later decision).
- Docstring updated (#64 story 25): the `run_requested` event carries package ids, not the label.

## UI label
- `ReviewStageView` shows a small kit `Chip` (`hx-chip t-warn xs`, `data-testid="run-not-qualified"`, text "Not qualified") in the right slot of the Gate 3 banner, next to the hint, **only** when `demoFrozenPackages(workspace)` is non-empty. That helper (`review/reviewState.ts`) mirrors backend `demo_packages_of`: it reads `demo_unqualified_packages` from the pinned run's `run_requested` event.
- No banner, no toggle, no "Demo:" text, no `.demo-banner`. A flag-on workspace that is not yet frozen shows no label. ReportAssembly and ChatDock are untouched.
- A refused export shows the server detail through the existing export error/retry state.

Screenshots (`dh-7-68/`):
- `flag-on-demo-frozen-banner.png`, `flag-on-demo-frozen-stage.png`: live flag-on server, human freeze → validation → Gate 2 dispositions → 4 roles → FSA (`flag-on-demo-frozen-drive.json`). Label shown.
- `flag-on-demo-frozen-export-refused.png`: clicking Export → "Export refused: this run was frozen with the demo flag (packages not qualified)." Afterwards the workspace still has `release_gate=ready_for_export` and both export artifacts are `pending`.
- `flag-off-strict-banner.png` / `-stage.png` (FSA) and `flag-off-strict-exported-*.png`: flag off, qualified copy (`/tmp/helix-dh7-qualified/helix`, made by the test helper `qualified_fixture_root`). No label; export 200 with 2 artifacts (`flag-off-strict-drive.json`).

## Acceptance (#68)
| Criterion | Evidence |
|---|---|
| Demo-frozen: small "Not qualified" label; strict: none; no `.demo-banner` | `review-export.spec.ts`: "demo-frozen run: only a small 'Not qualified' status label…", "strict run: no 'Not qualified' label at any phase", flag-on-not-frozen and flag-off assertions; live screenshots above |
| Demo-frozen export → 409 with refusal detail; nothing materialized or recorded | `test_flag_on_exports_with_both_packages_pending_and_labels_ui_payload_and_report` (flipped): 409 `{"detail": DEMO_EXPORT_REFUSAL}` on first call and on replay; `release_gate` and `export_artifacts` unchanged, none `exported`, stages unchanged (the refusal is only audited as the latest run event); spec "demo-frozen run: export fails closed…"; live screenshot |
| Flipped test; strict/flag-off export tests unchanged and green | `test_flag_off_export_bytes_carry_no_demo_label` unchanged and passing; new `test_demo_frozen_export_refusal_is_keyed_on_the_frozen_run_not_the_flag` (flag on + qualified tree → 200); `test_demo_frozen_export_refusal_helper` |
| Freeze stays human-only (409 `human_freeze_required`) | `test_flag_on_never_freezes_by_itself_and_still_requires_the_human_freeze[flag-on/flag-off]`: validation and DV return 409 `human_freeze_required`, export refused, 0 pinned runs until the human `POST /pinned-runs`, flag on or off; spec "freeze stays a human action" |
| No fake hashes; packages stay pending | `test_flag_on_freeze_records_no_qualification_hash_and_keeps_packages_pending` and the flipped test check package files are byte-identical and `pending` with no `qualification_hash` |
| pytest = base + new/flipped; ruff, tsc, build clean; verify-live no worse than base | below |

## Gates
- **Backend demo-flag tests:** 14/14 passed (`dh-7-68/pytest-demo-flag.txt`).
- **Full backend pytest:** base 284 tests / 200 passed / 84 failed; head 287 / 203 / 84. The failure sets are identical (0 new, 0 fixed), all the known `invalid_package_qualification` failures on the shipped pending tree (`dh-7-68/pytest-full-failures.txt`).
- **ruff `app tests`:** 5 errors, the identical set to base (`dh-7-68/ruff-head.txt`).
- **tsc:** clean. **next build:** OK (inside every verify-live run).
- **`tests/review-export.spec.ts`:** 16/16 on dev 19435/19434 (`dh-7-68/review-export-spec.log`).
- **verify-live** (19444/19445), head vs base:

| Run | Base d4e5015a | Head |
|---|---|---|
| Flag ON, shipped tree | 76 passed, 1 failed (`workbench.spec.ts:38`), 1 skipped | 78 passed, 1 failed (same), 1 skipped |
| Flag OFF, shipped tree | 75 passed, 2 failed (`:38`, `:413`), 1 skipped | 77 passed, 2 failed (same), 1 skipped |
| Flag OFF, qualified copy | 76 passed, 1 failed (`:38`), 1 skipped | 78 passed, 1 failed (same), 1 skipped |

  - The +2 passes are the two new review-export tests. No new failures.
  - `workbench.spec.ts:38` fails **on base** in every configuration at line 73: `getByRole("status")` strict-mode violation, because the DH-3 ReportAssembly `review-banner` also has `role="status"`. That is outside DH-7 (shared spec, DH-3/DH-4 area). Note: it fails before the export step, so with the flag on, the live end-to-end export refusal is proven by the backend test, the spec, and the live drive above rather than by `:38`. Once `:38` is fixed, its flag-on variant must expect the 409 refusal.
  - `:413` (no pinned run) and the flag-off `:38` freeze 422 are the known shipped-tree base failures.
  - Logs: `dh-7-68/verify-live-{flag-on,flag-off,qualified}.log`, `dh-7-68/base-verify-live-*.log`.
- **Parity** (flag off, 19454/19455, exit 0): all 25 enforced screens PASS at 0.000 %, including the lane D Gate 3 chrome (the gate banner is unchanged for strict runs). Report-only `review-export-*` 84.4 %. `dh-7-68/parity-full-kit-summary.md`.

## Shared-file edits
None. Every edited file is lane D's in `docs/ui-lanes-ownership.md` (`app/qualification.py`, `app/approved_exports.py`, `tests/test_demo_unqualified_flag.py`, `src/components/review/**`, `tests/review-export.spec.ts`).
