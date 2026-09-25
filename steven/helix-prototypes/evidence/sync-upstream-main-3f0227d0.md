# Sync Steven-Espaillat/Helix `main` `3f0227d0` into `feat/steven-workspace`

- **Branch:** `sync/upstream-main-3f0227d0`, from `feat/steven-workspace` at `79eb31a9`. The merge-base is `436529e9`; upstream was 28 commits ahead and 20 behind.
- **Date:** 2026-09-24 (CT), macOS local run.
- **Lane B isolation:** `HELIX_DATABASE_URL=sqlite+pysqlite:////tmp/helix-lane-b.db` on a fresh DB. Ports were dev 8032/3032, verify-live 8132/3132 and parity 8232/3232.

## Screenshots (live, unfrozen demo workspace, no model configured)

| File | What it shows |
|---|---|
| `01-report-assembly-draft-v1.png` | A drafted section, v1 |
| `02-report-assembly-revised-v2.png` | A revision proposed as v2, then applied |
| `03-report-assembly-verified.png` | The section after verify |
| `04-chat-dock-turn.png` | ChatDock with repo icons, no emoji. The turn persists; the reply says the model is unreachable (no LLM env). |

Inspect → Gate 2 can't be reached from the live unfrozen workspace, because the Traceability stage needs a frozen run. Base behaves the same way. The Playwright spec covers it instead (below).

### Section-to-claim mapping (drafted section → Gate 2)

Steven's drafted-section blocks carry no claim IDs, so nothing is inferred from their text. The mapping reuses data the app already has:

1. Every drafted section has a `template_section` from Steven's `backend/app/section_catalog.py`. For example, `5_3_3_microscopic` maps to `S7`.
2. The server's report projection (`workspace.report.sections`, the same data #27/#28 used) lists the claim-backed statements for each template section. Each statement has a `claim_id` and its `provenance_count`.
3. `claimsByTemplateSection()` collects the distinct claims for each template section. The selected drafted section shows one `Inspect N provenance edges` button (`data-testid="inspect-claim-<ID>"`) per claim of its template section. N is that block's `provenance_count`, and clicking the button calls `onInspectClaim(claimId)`, which opens Gate 2 focused on that claim.
4. If the template section has no claims, no button renders. No claims are invented.

| Drafted sections | Template section | Claim → edges |
|---|---|---|
| 5.2.1, 5.2.2, 5.2.3 | S5 | C-BW-HIGH → 10 |
| 5.3.1, 5.3.2, 5.3.3 (liver) | S7 | C-MI-LIVER → 4 |
| Summary, 5.3.4 | S8 | C-NOAEL → 0 |
| Sections on S1–S4 | — | no button |

The navigator's "Claim traceability" list, with one Inspect per claim-backed report section, is kept, so `traceability-gate.spec.ts:417` passes unchanged. The new test at `traceability-gate.spec.ts:436` checks three things:
- 5.3.3 Microscopic Findings shows `Inspect 4 provenance edges`, and clicking it opens Gate 2 on **C-MI-LIVER** (kicker plus `aria-pressed`).
- 5.2.3 Body Weight shows `Inspect 10 provenance edges` and opens C-BW-HIGH.
- 1. Objective shows no Inspect button.

## Gates (tip vs base `79eb31a9`)

| Check | Base `79eb31a9` | Tip |
|---|---|---|
| pytest (junit) | 254 tests: 170 passed / 84 failed | 268: 184 passed / 84 failed. The failing set is identical to base, and all 14 new upstream tests pass. |
| ruff | 5 | the same 5 (B905, I001, 2× B008, F401) |
| tsc / build | pass / pass | pass / pass |
| verify-live | 59 passed / 1 skipped / 2 failed (`workbench:38`, `:408`) | 60 passed / 1 skipped / 2 failed (`workbench:38`, `:411`, the same test shifted by 3 lines). The extra pass is the new test. |
| verify-parity | 19 passed / 2 skipped | 19 passed / 2 skipped. Every enforced screen is at its committed diff. |
| Alembic | head `9edd082c07ae` | single head `c24154d7a8e9`; `upgrade head` on a fresh DB is clean |
