# SLICE 3 prove evidence

## make test

```text
cd steven/helix-prototypes && make test
```

Outcome: green.

- synthetic bundle verified
- ruff clean
- pytest 61 passed
- frontend typecheck and production build succeeded

## verify-template-contract-gates.sh

```text
cd steven/helix-prototypes && ./scripts/verify-template-contract-gates.sh
```

Outcome: green. Wrote `evidence/template-contract-gates.json`.

- After hybrid validation, body-weight and discussion packages are both `eligible: true`
- Body-weight gate results cover fields, locations, table_shapes, labels, units, and style_constraints
- Every Template Contract Gate result is `hard_blocker` and `waivable: false`
- Independent discussion package is not in the body-weight Section Impact Set
- `POST .../validation-results/TCR-BW-FIELDS/dispositions` returns 409 with a non-waivable detail
- A template fix on the same Pinned Run is rejected; a named superseding freeze is required
- Review Scaffold Revision sequence 1 records empty `section_impact_sets` when both packaged sections are eligible

## verify-live.sh

Not required to prove Template Contract Gates; Playwright workbench coverage is in `frontend/tests/workbench.spec.ts` and runs under `verify-live` when that environment is available. This slice's backend-owned eligibility, gate results, impact sets, and non-waivable TCR dispositions are proven by `make test` and `verify-template-contract-gates.sh`.
