# UI lane D: review, approvals, export, downloads (#23) + demo not-qualified flag

Base: `feat/steven-workspace` @ `be116176` (rebased, SHA verified). Parked WIP `52799982` ported onto the new CSS layout. Local run on Stevens-MacBook-Pro, 2026-09-24 CT. Lane D ports and DB per `docs/ui-lanes-ownership.md` section 6: dev 8034/3034 with `/tmp/helix-lane-d.db`, verify-live 8134/3134, parity 8234/3234. Every app, test, and parity command set these inline. No Codex or OpenAI calls.

## Demo flag `HELIX_DEMO_UNQUALIFIED_PACKAGES`
- **Home:** `backend/app/qualification.py`. It holds `skips_qualification(flag_on, package_id, skill)`, `DEMO_LABEL = "Demo: not qualified"`, and the scope, which is exactly `section.5_2_3_body_weight` and `section.5_3_discussion`.
- **Where it acts:** `run_plans.PinnedRunService._pin_declared_identities` calls it. With the flag on, only a `pending` qualification on those two packages is skipped. A `failed` status is never skipped, and any other package still blocks.
- **Freeze metadata:** freeze records the demo detail on the seed and event only when a skip actually happened. A strict run's hashes are unchanged.
- **Export labels:**
  - The pinned-run manifest bytes carry `demo_notice`, which lists both sections as "Demo: not qualified", `pending` (`ui-lane-d/flag-on-pinned-run-demo-notice.json`).
  - Section candidate and draft bytes for those packages are wrapped with the label.
  - The release candidate hashes the labeled bytes, so Final Study Approval covers the label.
  - The DV receipt is not a section-package artifact and stays byte-identical.
- **UI labels:**
  - `DemoLabel` / `DemoBanner` label S5 and S8 in the section list and canvas.
  - The banner shows on every stage, including the Upload freeze gate.
  - The downloads note also carries the label.
- **Human-only freeze** (the Chief of Staff rule): the flag never freezes by itself.
  - `test_flag_on_never_freezes_by_itself_and_still_requires_the_human_freeze` proves that with the flag on:
    - validation and data validation return 409 `human_freeze_required`
    - export is refused
    - the pinned-run count stays 0 until a human `POST /pinned-runs`
  - In the UI, `review-export.spec.ts` "demo flag on: freeze stays a human action" shows that no `/pinned-runs` POST is sent on load and freeze stays disabled without consent.
  - Live check: a fresh flag-on server reported `pinned_run: null` before the human freeze.
- **Flag off is identical to today:**
  - With the flag unset or off, the strict 422 is returned for both pending packages.
  - Unset, off, and on produce an identical run over a qualified tree.
  - Flag-off export bytes carry no label.
  - With the flag off, the workspace field is `[]` and the UI shows zero "Demo: not qualified" text.
- **No fabricated hashes:** no `qualification_hash` or `skill_hash` is written, and the packages stay `pending` and byte-identical.
- **Test results:** `backend/tests/test_demo_unqualified_flag.py`: **11 passed** (`ui-lane-d/pytest-demo-flag.txt`).

## #23 acceptance criteria
| Criterion | Evidence |
|---|---|
| Three-column page vs reference, responsive stack | `.g-review` from `helix-v1.css`. Parity `review-export-light/dark` is **report-only** at 75.6 % with masks: the server report copy and titles differ from the reference copy, and the canvas is taller (1360x1417 vs 1360x541). Screenshots are in `ui-lane-d/*-stage.png`. |
| Section list + canvas render `WorkspaceResponse.report` | spec "renders the server report…", which checks all 8 sections with server titles and statuses |
| Required fields, review markers, references, template context, no regulatory claim | Same spec: `required-fields`, `.hx-flag` markers, `regulatory-references` (non-binding context + template disclaimer), and the `regulatoryClaim` regex on the body text |
| Inspect provenance calls `getEvidence`, exact lineage | spec "inspect provenance…": `GET …/claims/C-BW-HIGH-M/evidence`, and every lineage edge is rendered |
| `recordApproval` one role at a time, renders returned workspace | spec "records one role per call…": body keys are exactly `role, reviewer, meaning` |
| Any order for pathologist/peer/QAU; director disabled until all three; server enforces | Same spec runs QAU → pathologist → peer. The real server 409 ("Pathologist, peer reviewer, and Quality Assurance Unit records are required first"), captured in the fixture, is shown by "a server-refused approval…" |
| Fixed meanings, 4–200 chars | Same spec checks each `meaning` against the #23 strings |
| Export disabled until server `ready_for_export` | spec "export is enabled only by the server ready_for_export gate…" |
| Approvals never export; only the button calls `exportPackage` | Request tracking shows zero `/exports` requests after all approvals and FSA, then exactly one `POST /exports` after the click |
| Export success: `exported_at`, replay state, checksums, downloads | Specs "export is enabled…", "downloads list every exported artifact…", and "export errors… retry… idempotent". **See the gap below on "four".** |
| Downloads use `artifactDownloadUrl`, return server bytes | Download spec checks the `href`, and the sha256 of the downloaded bytes equals the checksum. Live proof: `workbench.spec.ts:38` downloads from the real API in the qualified run. |
| Reload restores everything from `getWorkspace` | spec "reload restores…": sign-offs, receipt, checksums, 9/9, and no commands sent |
| Progress completes only after server-confirmed export | Progress is not complete after FSA. It shows "9 of 9" only after export, and stays "Awaiting you" after a failed export. |
| "Synthetic data · Not for submission" + "not FDA acceptance" | The first spec, plus the page footer and export panel copy |

### Gap: "four artifact checksums"
- `#23` expects a PDF/ZIP/define.xml/nSDRG packet. On this base, export follows slice 11 (`evidence/slice-11-export-approved-artifacts.md`): it materializes **exactly** the Final Study Approval hashes and never calls `generate_artifact`.
- The approved set is the pinned run, the DV receipts, and, once Codex section drafting has run, the `section_draft_candidate` and `section_draft` artifacts (`release_candidates.compile_release_candidate`).
- Without Codex, a live export has 2 artifacts (screenshots, `ui-lane-d/flag-off-export-state.txt`). The UI renders every artifact the server returns.
- Bringing back the legacy `artifacts.py` packet would change the slice-11 contract. This needs a Chief of Staff decision.

## Tests and checks
- **Frontend unit spec:** `tests/review-export.spec.ts`: 12 passed, and 36/36 with `--repeat-each=3`.
  - It uses real backend states captured by `/tmp/helix-lane-d-capture.py`: `tests/fixtures/lane-d-review.json` with `review`, approved, FSA, exported, demo, the real 409, the export receipt and replay, the evidence chain, and the artifact bytes.
  - POST mocks never forward to the backend.
- **`scripts/verify-live.sh` on 8134/3134** (next build + full e2e):
  - Qualified copy (`HELIX_CODEX_REPOSITORY_ROOT=/tmp/helix-lane-d-qualified/helix`, flag off): **52 passed, 0 failed, 1 skipped**. This includes `workbench.spec.ts:38` end to end: human freeze → validation → Gate 2 dispositions → Gate 3 per-role approvals → FSA → export → byte-verified downloads.
  - Flag on (`HELIX_DEMO_UNQUALIFIED_PACKAGES=1`, shipped pending tree): **52 passed, 0 failed, 1 skipped**. The same end-to-end flow runs with the packages still pending.
  - Shipped tree, flag off: 50 passed, 2 failed, 1 skipped. The failures are `workbench.spec.ts:38` (freeze 422 `invalid_package_qualification`) and `:407` (no pinned run). They are the same pre-existing base failures lane A documented.
  - Logs: `ui-lane-d/verify-live-*.log`.
- **Backend pytest:** 164 passed / 84 failed. The failures are the identical set as base `be11617`: 0 new, 0 fixed, all `invalid_package_qualification` (`ui-lane-d/pytest-full-failures.txt`).
- **ruff `app tests`:** the same 5 pre-existing errors as base (intake.py B905, main.py I001/B008x2, tests/test_intake.py F401). None were added.
- **`npx tsc --noEmit`:** clean. **`next build`:** OK (inside verify-live).
- **Flakes seen under machine load:** "route.fetch: Test ended" / "Response has been disposed" in lane A helpers and old workbench mocks. These are pre-existing test-teardown races and don't reproduce on rerun. The lane D spec unroutes in `afterEach`.

## Visual parity (`scripts/verify-parity.sh`, ports 8234/3234, flag off, exit 0)
- All 11 enforced screens PASS at 0.000 % (`ui-lane-d/parity-full-kit-summary.md`).
- Lane D screens use the new fixture route `/parity/review`. It returns 404 unless `HELIX_PARITY_FIXTURES=1`, uses display state only (a trimmed real review-export workspace with the demo flag off), and makes no API calls, so there is no freeze or qualification path.
- The lane D screens are report-only: 75.6 % with masks (canvas, sign-off rows, export panel). Side-by-sides: `evidence/parity/review-export-{light,dark}/`.

## Screenshots
- `ui-lane-d/flag-off-review(-stage).png` and `flag-off-exported(-stage).png`: qualified copy with the flag off, driven through the UI (per-role approvals, FSA, export).
- `ui-lane-d/flag-on-review(-stage).png` and `flag-on-exported(-stage).png`: shipped pending tree with the flag on. S5/S8 are labeled, and the banner and downloads note are shown.

## Shared-file edits (escalations)
- `HelixWorkbench.tsx`: +7 lines. They add imports, the `review-export` case block, and one `<DemoBanner>` line for the other stages.
- Backend:
  - `config.py`: the flag
  - `main.py`: passes the flag to PinnedRunService
  - `schemas.py`: `DemoPackageLabel` plus the workspace field
  - `service.py`: fills the field
  - `run_plans.freeze`: seed/event detail, written only on a skip
- `api.ts`: one import line; `recordApproval` uses `APPROVAL_POLICY`.
- `workbench.spec.ts`: the approval/export/download block and the FSA-scope test, which moved to the new selectors and opens Gate 3 from the Progress Bar.
- `src/app/parity/review/**`: new lane D fixture.
- `ReportAssembly.tsx` (D's file): the legacy disposition button is relabeled "Record Gate 2 disposition". Its `onResolve` expression is untouched for lane C.
