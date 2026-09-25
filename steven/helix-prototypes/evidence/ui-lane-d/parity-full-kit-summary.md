# Visual parity summary

Viewport 1440x900 @1x. Default max diff ratio 1.00%, pixelmatch threshold 0.02.

| Screen | Lane | Status | Theme | Diff ratio | Max | Result | Size (ours vs ref) | Note |
|---|---|---|---|---|---|---|---|---|
| shell-header-light | step0 | enforced | light | 0.000% | 0.10% | PASS | 1440x60 vs 1440x60 |  |
| shell-header-dark | step0 | enforced | dark | 0.000% | 0.10% | PASS | 1440x60 vs 1440x60 |  |
| component-stage-rail-s0-light | step0 | enforced | light | 0.000% | 1.00% | PASS | 1360x144 vs 1360x144 |  |
| component-stage-rail-s7-light | step0 | enforced | light | 0.000% | 1.00% | PASS | 1360x144 vs 1360x144 |  |
| component-stage-rail-s0-dark | step0 | enforced | dark | 0.000% | 1.00% | PASS | 1360x144 vs 1360x144 |  |
| component-gate-banner-light | step0 | enforced | light | 0.000% | 1.00% | PASS | 1360x70 vs 1360x70 |  |
| component-file-table-light | step0 | enforced | light | 0.000% | 1.00% | PASS | 930x442 vs 930x442 |  |
| component-auth-card-light | step0 | enforced | light | 0.000% | 1.00% | PASS | 360x450 vs 360x450 |  |
| component-upload-composition-light | step0 | enforced | light | 0.000% | 1.00% | PASS | 1440x900 vs 1440x900 |  |
| shell-viewport-light | step0 | report-only | light | 30.317% | 1.00% | reported | 1440x900 vs 1440x900 |  |
| journey-progress-light | A | enforced | light | 0.000% | 1.00% | PASS | 1360x144 vs 1360x144 |  |
| upload-gate-light | A | report-only | light | 39.190% | 1.00% | reported | 1360x1094 vs 1360x880 | size mismatch (padded area counts as diff) |
| agent-step-light | B | pending | light | - | 1.00% | skipped |  | skipped: owned by lane B (#21) |
| traceability-gate-light | C | pending | light | - | 1.00% | skipped |  | skipped: owned by lane C (#22) |
| review-header-light | D | enforced | light | 0.000% | 0.10% | PASS | 1440x60 vs 1440x60 |  |
| review-rail-s8-light | D | enforced | light | 0.000% | 1.00% | PASS | 1360x144 vs 1360x144 |  |
| review-gate-banner-light | D | enforced | light | 0.000% | 1.00% | PASS | 1360x70 vs 1360x70 |  |
| review-export-control-light | D | enforced | light | 0.000% | 1.00% | PASS | 270x45 vs 270x45 |  |
| review-header-dark | D | enforced | dark | 0.000% | 0.10% | PASS | 1440x60 vs 1440x60 |  |
| review-rail-s8-dark | D | enforced | dark | 0.000% | 1.00% | PASS | 1360x144 vs 1360x144 |  |
| review-gate-banner-dark | D | enforced | dark | 0.000% | 1.00% | PASS | 1360x70 vs 1360x70 |  |
| review-export-control-dark | D | enforced | dark | 0.000% | 1.00% | PASS | 270x45 vs 270x45 |  |
| review-export-light | D | report-only | light | 83.669% | 1.00% | reported | 1360x1417 vs 1360x541 | size mismatch (padded area counts as diff) |
| review-export-dark | D | report-only | dark | 83.674% | 1.00% | reported | 1360x1417 vs 1360x541 | size mismatch (padded area counts as diff) |
| design-tokens-light | step0 | enforced | light | 0.000% | 0.00% | PASS | 28 tokens |  |
| design-tokens-dark | step0 | enforced | dark | 0.000% | 0.00% | PASS | 28 tokens |  |
