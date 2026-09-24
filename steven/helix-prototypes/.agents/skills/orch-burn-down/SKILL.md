---
name: orch-burn-down
description: Runs or resumes the HELIX ticket orchestrator to burn down eligible tickets and advance pull requests to READY-FOR-MERGE. Use when burning down HELIX tickets, running or resuming the orchestrator, or advancing work to READY-FOR-MERGE. Pauses for human review and merge.
---

# Burn down HELIX tickets

1. Read the [orchestrator README](../../../../ops/orchestrator/README.md) and [example policy](../../../../ops/orchestrator/policy.example.json) before operating.
2. Require an `OWNER/REPO` value and a policy path.
3. Review `verification_commands` before running the command.
4. Run from the directory where `policy.repository_root` resolves to the intended clean Git worktree.
5. Run the command and follow its JSON disposition.

```bash
ops/orchestrator/orch run --repo OWNER/REPO --policy PATH/TO/POLICY.json [--state PATH/TO/STATE.json]
```

Append `--dry-run` to this command only when the operator asks to inspect the next action without applying it.

## Trust the runner

Let `orch run` own agent launch, exact JSON contracts, GitHub reconciliation, bounded attempts, CI polling, proof comments, policy-owned verification, whole-run locking, and READY-FOR-MERGE validation. Use [orch.py](../../../../ops/orchestrator/orch.py) as the structural source for runner behavior.

Do not invoke lower-level commands to skip the runner. Do not clear or edit state, rewrite agent output, remove labels to force progress, or bypass a dirty or wrong-head checkout.

Preserve these fail-closed rules:

- Proof is current-head, current-stack, and policy-bound.
- Findings fold by stable identity. Only current unresolved P0 or P1 findings block readiness.
- Multiple open pull requests for one issue fail closed.
- An issue or pull request query at the 1,000-item boundary fails closed.

## Handle the disposition

- `planned` means that a dry run reported the next action. Report it and stop.
- `ready_for_merge` means that every runner gate passed. Show the reported pull request to the human for review and stop. Never merge. After the human confirms the merge, rerun the same command. Do not claim the next ticket manually.
- `complete` means that no managed open issues remain. Report completion and stop.
- `blocked` means that repository state needs a person. Report the exact JSON `reason` and stop without changing state or GitHub to force progress.
- `failed` means that an action exhausted `max_attempts`. Report the exact JSON `reason`, fix only the named external cause, and rerun the same command.

Treat the [orchestrator README](../../../../ops/orchestrator/README.md) as canonical when this skill and the runner differ.
