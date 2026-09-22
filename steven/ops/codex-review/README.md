# Operate the Codex pull request review

This tool reconciles one Azure DevOps Classic build definition and one advisory build validation policy. The build runs `gpt-5.6-sol` with low reasoning through server-controlled inline tasks. It does not read scripts, prompts, or configuration from the pull request.

## Prerequisites

Install Python 3.10 or later, Azure CLI, and the `azure-devops` CLI extension. Sign in to the `LLMGenAITitaniumEngineering` organization before you run the tool.

Your operator identity needs these permissions:

- View and edit build pipelines.
- Update the project-level pipeline general settings. This normally requires Project Administrators membership and an Azure CLI credential with the `vso.project_write` scope.
- View and edit branch policies.
- View repositories.

The project build service identity needs these permissions:

- Read the repository.
- Contribute to pull request status.
- Read and write pull request threads.

Use a dedicated OpenAI API key. Do not use a variable group or a key shared with another workload.

## Reconcile the automation

Run these commands from the repository root:

1. Inspect the proposed changes.

   ```sh
   ops/codex-review/codex-review plan
   ```

2. Create or update the build definition without enabling the policy.

   ```sh
   ops/codex-review/codex-review apply
   ```

   Azure rejects the initial Classic definition when `disableClassicBuildPipelineCreation` is true. The previous command failed with `The classic pipelines are disabled for this project / organization.`

   For the initial definition only, `apply` reads the project setting. If creation is disabled, it sets only `disableClassicBuildPipelineCreation` to false, verifies the value, creates the definition, restores true, and verifies the restored value. The restoration runs even when definition creation fails. A restoration failure stops `apply` before any secret or policy change.

   This project-wide setting creates a residual concurrency risk. Another operator can create a Classic pipeline during the short interval between the first update and the restoration. Run the first `apply` when no other pipeline administration is in progress.

   If creation is already enabled, `apply` does not change the setting. Updates to an existing definition never change the setting. The first `apply` exits with code 2 while `CODEX_API_KEY` is missing. It does not enable the policy.

3. Store the dedicated key from standard input.

   ```sh
   printf '%s' "$OPENAI_REVIEW_KEY" | ops/codex-review/codex-review set-key
   ```

   You can instead set `CODEX_API_KEY` in the command environment. The tool never passes the value in an argument or writes it to a file.

4. Reconcile the enabled policy.

   ```sh
   ops/codex-review/codex-review apply
   ```

5. Verify the server state.

   ```sh
   ops/codex-review/codex-review verify
   ```

`plan` and `verify` make read-only Azure calls and redact secret values. `apply` and `set-key` change Azure DevOps.

## Roll back

Disable or delete the `Codex review advisory` policy first. Then delete the `Codex PR Review` build definition. Deleting the definition also removes its dedicated secret variable. Confirm in Azure DevOps that both managed resources are absent.

## Credential risk

The Codex process must receive a reusable API key. The task removes the key from child shell environments and excludes names that contain `KEY`, `SECRET`, or `TOKEN`. It also excludes Azure environment names. These controls do not protect the key from a compromised Codex CLI package, the Codex process memory, or the hosted agent. Use a dedicated key with usage limits, monitor its use, and rotate it after suspected exposure.

## Run the offline tests

The tests use only the Python standard library and do not call Azure.

```sh
python3 -m unittest discover -s ops/codex-review -p 'test_*.py' -v
```
