# SLICE 7 prove evidence

Commands were run from `steven/helix-prototypes` on `cursor/slice-7-review-scaffold-versioning-77ea`.

Base: `origin/feat/steven-workspace` at `1e44a528a906f3e1af40202367c2b59ca44cb4f5`.

## make test

```text
make test
```

Outcome: green.

- synthetic bundle verified
- ruff clean
- pytest 106 passed
- frontend typecheck and production build succeeded

## verify-review-scaffold.sh

```text
./scripts/verify-review-scaffold.sh
```

Outcome: green. Wrote `evidence/review-scaffold-receipt.json`.

- Sequences after validation through pathologist approval: `[1, 2, 3, 4, 5, 6]`
- History length: `6`
- After draft replay and evaluation replay: history length `2` (no extra revision)
- `export_eligible` on every revision: `false`
- `admit_export_document` rejected the latest revision
- Release-candidate schema rejected the latest revision
- Every `needs_review` section used placeholder `[NEEDS REVIEW]` and named at least one blocker ID

## verify-section-promotion.sh

```text
./scripts/verify-section-promotion.sh
```

Outcome: green. Slice 6 promotion path still passes after scaffold persist.

## verify-live.sh

```text
./scripts/verify-live.sh
```

Outcome: green.

- Playwright `workbench.spec.ts`: 6 passed
- `codex-section-run.spec.ts`: skipped without `HELIX_CODEX_LIVE=1`
- Journey shows `review-scaffold-history` and the triggering event ID after validation
- Report assembly has no `review-scaffold-history` (`toHaveCount(0)`)

## verify-postgres.sh

Skipped. This slice does not change storage dialect behavior.
