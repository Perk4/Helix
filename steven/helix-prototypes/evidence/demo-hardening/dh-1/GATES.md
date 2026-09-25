# DH-1 gate evidence (Steven-Espaillat/Helix#65)

Local-only on Perk's Mac, ports API 8031 / web 3031, dist `.next-dh1`. No Codex calls: every spec that could reach `section-runs` stubs or guards it.

- `npx tsc --noEmit`: clean.
- Hermetic Playwright (`dh1-auto-run`, `upload-gate`, `agent-steps`, `journey-progress`): all pass, also with `--repeat-each=2`.
- `verify-live.sh` against a temporary qualified copy of the repo (`HELIX_CODEX_REPOSITORY_ROOT`): 84 passed, 1 skipped, three consecutive runs (`verify-live-qualified.log`).
- `verify-live.sh` on shipped packages: fails only `workbench.spec.ts` live export and the predecessor-run test, the same two tests that fail on base `d4e5015a` because package qualification is pending (`verify-live-shipped.log`).
- Backend pytest: 84 failures, identical count to base (qualification pending); the new `test_open_event_stream_does_not_hold_the_sqlite_write_lock` passes, and fails without the `main.py` fix.
- `ruff check app tests scripts` (the standard scope): 5 findings, identical to base; none added. (The earlier "34" was the whole backend directory, also identical to base.)

Screenshots in this folder come from `tests/dh1-auto-run.spec.ts`.

## Follow-up (Tester P2s on #32)

- A failed workspace reload after the freeze is retried once. If it still fails, Upload shows "the workspace did not reload" with a Reload button, never "Manifest frozen", and the auto-start waits until a reloaded workspace shows the run past Upload.
- The Gate 2 stop message is shown as the workbench notice after the view moves to Traceability.
- Gates at this tip: hermetic DH-1, upload-gate, agent-steps and journey-progress specs 80/80 with `--repeat-each=2`; qualified `verify-live.sh` 86 passed, three runs in a row (`verify-live-qualified.log`); shipped `verify-live.sh` fails only the two base-red tests (`verify-live-shipped.log`); pytest 84 failures and ruff 5, both identical to base; `tsc --noEmit` clean.
- New screenshot: `freeze-reload-needed.png`.
