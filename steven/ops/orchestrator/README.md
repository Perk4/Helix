# Run the ticket orchestrator

`orch run` works on one eligible issue at a time. It claims the issue, launches the configured agent, reviews and verifies the PR, waits for CI, and adds `READY-FOR-MERGE` after every gate passes. It never merges a PR.

## Configure the run

Copy the example policy.

```bash
cp ops/orchestrator/policy.example.json .codex/orchestrator/policy.json
```

Run `orch` from the `steven` directory when you use the example unchanged. `repository_root` resolves from the current working directory.

Set `agent_argv` to a noninteractive command that reads the prompt from standard input and writes one JSON object to standard output. The runner does not invoke a shell.

Set `verification_commands` to the exact commands that prove the repository is ready. The runner executes these commands in order. It requires a clean Git checkout at the PR head before it records test proof.

`max_attempts` bounds agent actions, GitHub mutations, and CI polls. `poll_seconds` controls the delay between observations. `timeout_seconds` applies to each agent and verification process.

## Start or resume

```bash
ops/orchestrator/orch run \
  --repo Steven-Espaillat/Helix \
  --policy .codex/orchestrator/policy.json
```

The command keeps working until it reaches a terminal disposition.

- `ready_for_merge` means that the PR passed every gate. Review and merge the PR, then run the same command again.
- `complete` means that no managed open issues remain.
- `planned` reports the next action during a dry run.
- `blocked` means that repository state needs a person. The JSON reason names the failed gate.
- `failed` means that one action exhausted `max_attempts`. Fix the cause, then run the command again.

The runner reconciles GitHub before each attempt. A restart adopts an observed claim, PR, proof comment, changed head, or ready label instead of repeating the effect.

## Inspect the next action

Use a dry run to reconcile GitHub and print the next action without invoking an agent or changing GitHub.

```bash
ops/orchestrator/orch run \
  --repo Steven-Espaillat/Helix \
  --policy .codex/orchestrator/policy.json \
  --dry-run
```

## Review the handoff

When the output contains `"disposition": "ready_for_merge"`:

1. Open the reported PR.
2. Review the code, checks, review proof, and test proof.
3. Merge the PR.
4. Run `orch run` again.

The next run waits for GitHub to close the linked issue, then selects the next dependency-ready issue.

## Limits

The GitHub issue and PR queries fail closed when either query returns 1,000 items. The current adapter cannot prove that a result at that boundary is complete. Repositories at that size need cursor-based pagination before they can use `orch run`.
