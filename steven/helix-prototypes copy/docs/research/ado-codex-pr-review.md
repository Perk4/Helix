# Azure DevOps PR review with OpenAI Codex CLI

Research checked 2026-09-22. Sources are limited to official OpenAI and Microsoft documentation.

## Recommendation

Yes. Run Codex in a dedicated **PR-validation build**, not in the deployment stage. For Azure Repos, attach an automatic Build validation policy to each protected target branch; Azure Repos implements PR validation through branch policies rather than YAML `pr:` triggers, and validates the PR merge commit. Start as an optional/advisory review and make it required only after measuring reliability and adding deterministic output validation. [Azure Repos pipeline triggers](https://learn.microsoft.com/en-us/azure/devops/pipelines/repos/azure-repos-git?view=azure-devops#pr-triggers) [Build validation policy](https://learn.microsoft.com/en-us/azure/devops/repos/git/branch-policies?view=azure-devops#set-build-validation)

A deployment pipeline is the wrong primary trigger: review belongs before merge; deployment runs later, may have broader environment credentials, and ordinarily lacks the branch-policy-only `System.PullRequest.*` context. `Build.Reason` is `PullRequest`, and PR IDs/source/target values are initialized for branch-policy PR builds. [Predefined variables](https://learn.microsoft.com/en-us/azure/devops/pipelines/build/variables?view=azure-devops)

## Identifier mapping for the named target

An ADO Git REST URL has separate `{organization}/{project}/.../{repositoryId}` fields. The actual remotes and read-only ADO repository lookup establish this mapping:

- organization: `LLMGenAITitaniumEngineering`
- project: `LLMGenAITitaniumEngineering`
- repository: `Titanium_Engineer-04_Team_3`
- repository ID: `be68a2ca-fba3-4202-989e-e8f00003e11e`
- reviewed path within that repository: `steven/helix-prototypes/`
- URL: `https://dev.azure.com/LLMGenAITitaniumEngineering/LLMGenAITitaniumEngineering/_git/Titanium_Engineer-04_Team_3`

`titanium-engineer-labs` is a separate repository in the same organization and project, with repository ID `c7bd1728-7d2e-4f78-86dc-18014204599d`. A branch policy is repository-specific, so reviewing both repositories requires separate policy scopes (and preferably separate definitions or explicitly parameterized trusted orchestration). Microsoft’s REST route and pipeline variables distinguish organization, project, repository ID, and PR ID. [Create PR thread REST API](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-request-threads/create?view=azure-devops-rest-7.1) [Predefined variables](https://learn.microsoft.com/en-us/azure/devops/pipelines/build/variables?view=azure-devops)

## Codex command and review context

OpenAI provides two noninteractive choices:

- `codex review --base <ref>` is the dedicated noninteractive code-review command; exactly one of `--base`, `--commit`, `--uncommitted`, or a custom prompt may be used.
- `codex exec` is the general CI/script interface. It defaults to a read-only sandbox and supports `--ephemeral`, `--json`, `--output-last-message`, and `--output-schema`. Prefer `exec` when a publisher needs schema-constrained findings; prefer `review --base` for the simplest human-readable review. [CLI command reference](https://developers.openai.com/codex/cli/reference) [Non-interactive mode](https://developers.openai.com/codex/non-interactive-mode)

ADO checks out `refs/pull/<id>/merge` for a branch-policy build; `Build.SourceVersion` is the merge commit. Use `fetchDepth: 0` because shallow checkout can omit comparison history, and leave `persistCredentials: false` (its default) so Git credentials are removed after checkout. For that synthetic merge, first verify `HEAD` has two parents, then review `HEAD^1..HEAD`: the first parent is the target side and the merge result contains the PR changes. Alternatively, use the documented source/target variables plus ADO PR metadata and commit-diff APIs. Never review `HEAD~1..HEAD` without first establishing that this is a PR merge commit. [Azure Repos checkout and PR behavior](https://learn.microsoft.com/en-us/azure/devops/pipelines/repos/azure-repos-git?view=azure-devops) [Checkout schema](https://learn.microsoft.com/en-us/azure/devops/pipelines/yaml-schema/steps-checkout?view=azure-pipelines)

## Secure practical YAML shape

This is an illustrative reviewer pipeline, not a file to copy blindly. It assumes the YAML/job comes from a protected, centrally maintained `extends` template, pinned to a reviewed ref and enforced with resource checks. Microsoft recommends `extends` templates to define the outer structure and prevent malicious steps; OpenAI warns not to expose an API key at job scope where repository build scripts or compromised tasks can read it. Do not run package lifecycle scripts, tests, or any PR-controlled executable in the secret-bearing job. [Secure pipeline templates](https://learn.microsoft.com/en-us/azure/devops/pipelines/security/templates?view=azure-devops) [OpenAI CI key guidance](https://developers.openai.com/codex/non-interactive-mode)

```yaml
# Configure this pipeline as an automatic Build validation branch policy.
trigger: none
pr: none # Azure Repos ignores YAML PR triggers; policy queues the run.

pool:
  vmImage: ubuntu-latest

variables:
  codexVersion: '<PINNED_VERSION>' # update deliberately

steps:
- checkout: self
  clean: true
  fetchDepth: 0
  fetchTags: false
  persistCredentials: false

# Installation has no OpenAI or ADO publishing credential.
- bash: |
    set -euo pipefail
    npm install --global --ignore-scripts --no-audit --no-fund "@openai/codex@${CODEX_VERSION}"
    codex --version
  displayName: Install pinned Codex CLI
  env:
    CODEX_VERSION: $(codexVersion)

- bash: |
    set -euo pipefail
    test "$BUILD_REASON" = PullRequest
    test -n "$SYSTEM_PULLREQUEST_PULLREQUESTID"
    test "$(git rev-list --parents -n 1 HEAD | wc -w | tr -d ' ')" = 3
    base="$(git rev-parse HEAD^1)"

    # Generic exec is used here because it exposes explicit CI safety/output flags.
    codex --ask-for-approval never exec \
      --sandbox read-only \
      --ephemeral \
      --ignore-user-config \
      --ignore-rules \
      -c 'web_search="disabled"' \
      --output-last-message "$REPORT" \
      "Review only the pull-request changes shown by git diff $base HEAD. Report prioritized, actionable findings with file and line references; do not modify files." \
      > "$CODEX_LOG" 2>&1
  displayName: Review PR merge with Codex
  workingDirectory: $(Build.SourcesDirectory)
  env:
    # Scope the key to this one process step, never the job.
    CODEX_API_KEY: $(CodexApiKey)
    CODEX_HOME: $(Agent.TempDirectory)/codex-home
    REPORT: $(Agent.TempDirectory)/codex-review.md
    CODEX_LOG: $(Agent.TempDirectory)/codex-run.log

- bash: |
    set -euo pipefail
    # Validate, sanitize, and cap output before publishing in production.
    test -s "$REPORT"
    echo "##vso[task.uploadsummary]$REPORT"
  displayName: Add review to build summary
  env:
    REPORT: $(Agent.TempDirectory)/codex-review.md
```

The official package is `@openai/codex`; pin an exact reviewed release rather than silently taking latest. [OpenAI Codex repository quickstart](https://github.com/openai/codex#installing-and-running-codex-cli)

For stable downstream parsing, use a checked-in/trusted JSON Schema and this invocation instead of `codex review`:

```bash
codex --ask-for-approval never exec --ephemeral --sandbox read-only \
  --ignore-user-config --ignore-rules -c 'web_search="disabled"' \
  --output-schema "$TRUSTED_SCHEMA" \
  --output-last-message "$REPORT_JSON" \
  "Review only the pull-request changes shown by git diff HEAD^1 HEAD. Return findings matching the supplied schema."
```

`codex exec` writes progress to stderr and its final message to stdout/file. The example redirects both streams so model- or repository-controlled text cannot be interpreted as ADO `##vso[...]` logging commands; only the fixed publisher emits one. Structured output still needs deterministic validation of severity, paths, and changed-line bounds before it can fail a build or create inline comments. [Non-interactive mode](https://developers.openai.com/codex/non-interactive-mode) [ADO logging commands](https://learn.microsoft.com/en-us/azure/devops/pipelines/scripts/logging-commands?view=azure-devops)

## Authentication and secret boundary

- OpenAI recommends API-key authentication for programmatic CI/CD. Set `CODEX_API_KEY` only on the Codex invocation. Cached login may be plaintext in `~/.codex/auth.json`; do not pre-login a shared runner. Use `--ephemeral` and a temporary `CODEX_HOME`. [Codex authentication](https://developers.openai.com/codex/auth) [Non-interactive mode](https://developers.openai.com/codex/non-interactive-mode)
- Store the key in an authorized ADO secret variable, protected variable group, or Azure Key Vault. Secret variables are not automatically mapped into script environments. Never echo them or pass them as command-line arguments; masking is not foolproof. [ADO secret variables](https://learn.microsoft.com/en-us/azure/devops/pipelines/process/set-secret-variables?view=azure-devops) [Pipeline secret guidance](https://learn.microsoft.com/en-us/azure/devops/pipelines/security/secrets?view=azure-devops)
- A read-only Codex sandbox with approvals disabled is the appropriate unattended review profile. Keep web search, MCP servers, repository hooks, tests, and network-capable PR code out of this job. Read-only prevents workspace edits; it is not a substitute for controlling which process receives the key. [Agent approvals and security](https://developers.openai.com/codex/agent-approvals-security)
- OpenAI’s official GitHub Action adds an API proxy to reduce key exposure, but it is a GitHub Action, not an ADO task. In ADO, invoke the CLI directly and compensate with a trusted template, step-scoped key, disposable hosted agent, and no untrusted executable code. [Codex GitHub Action](https://developers.openai.com/codex/github-action)

## Publishing results and permissions

The summary command above needs no PR-write credential and places Markdown on the pipeline run’s Extensions tab. [ADO logging command `UploadSummary`](https://learn.microsoft.com/en-us/azure/devops/pipelines/scripts/logging-commands?view=azure-devops#uploadsummary-add-some-markdown-content-to-the-build-summary)

For visible PR feedback, use a **separate deterministic publisher step** that receives only `System.AccessToken`, not the OpenAI key. POST a summary thread to:

```text
$(System.CollectionUri)$(System.TeamProjectId)/_apis/git/repositories/
$(Build.Repository.ID)/pullRequests/$(System.PullRequest.PullRequestId)/threads?api-version=7.1
```

A thread without `threadContext` is a PR-level summary. Inline comments require `threadContext` file/right-side positions and, for iteration-aware PRs, `changeTrackingId` plus iteration context. Sanitize/cap model output, use a stable marker so retries update instead of duplicate, and recheck the PR’s current source/target commits immediately before posting. [Create PR thread](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-request-threads/create?view=azure-devops-rest-7.1)

`System.AccessToken` is a per-job token whose effective rights derive from authorization scope and the Build Service identity. Explicitly map it only into the publisher step. Use project-scoped authorization, enable “Protect access to repositories in YAML pipelines,” and grant the project Build Service identity only repository **Read** plus **Contribute to pull requests**. Do not grant source-code Contribute, force-push, bypass, policy-edit, or collection-wide access. [Job access tokens](https://learn.microsoft.com/en-us/azure/devops/pipelines/process/access-tokens?view=azure-devops) [Secure repository access](https://learn.microsoft.com/en-us/azure/devops/pipelines/security/secure-access-to-repos?view=azure-devops) [Repository permissions](https://learn.microsoft.com/en-us/azure/devops/repos/git/set-git-repository-permissions?view=azure-devops)

The thread REST endpoint accepts OAuth scopes `vso.threads_full` or `vso.code_write` when using an external OAuth/PAT credential; those selectable scopes do not replace the Build Service permission model for `System.AccessToken`. A PR status is another option (`vso.code_status` for an external token) and can become a required branch-policy status check, but Build validation already supplies the natural pass/fail gate. [Create PR thread](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-request-threads/create?view=azure-devops-rest-7.1) [Create PR status](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-request-statuses/create?view=azure-devops-rest-7.1) [Status-check policy](https://learn.microsoft.com/en-us/azure/devops/repos/git/branch-policies?view=azure-devops#require-status-checks)

## Rollout checklist

1. Confirm the actual ADO organization/project/repository URL and target branches.
2. Put the fixed reviewer orchestration in a protected, pinned, enforced template; authorize its secret source only for this pipeline.
3. Configure automatic, initially optional Build validation on protected target branches.
4. Use a Microsoft-hosted disposable agent, full Git history, no persisted checkout credential, pinned Codex CLI, read-only/no-approval execution, and a step-scoped API key.
5. Publish a sanitized build summary first. Add PR threads later with the narrowly permissioned Build Service identity and a stale-run/idempotency check.
6. Keep human review mandatory; do not deploy solely because a probabilistic review returned no findings.
