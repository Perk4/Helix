# Automatic Codex pull request review

Research checked on 2026-09-23 against OpenAI and GitHub documentation.

GitHub discovers the workflow at repository-root `.github/workflows/codex-review.yml`. The workflow starts at the repository root and reviews the HELIX project under `steven/helix-prototypes`.

## Configure the secret

A repository administrator must create an Actions secret named `OPENAI_API_KEY`.

1. Open the GitHub repository and select **Settings**.
2. Select **Secrets and variables**, then **Actions**.
3. On the **Secrets** tab, select **New repository secret**.
4. Enter `OPENAI_API_KEY` as the name, paste a key from [OpenAI API keys](https://platform.openai.com/api-keys), then select **Add secret**.

The workflow succeeds without the secret but skips the review and emits a notice. It passes the key only to `openai/codex-action`. The action sends the key as `Authorization: Bearer <key>`. An Azure or custom endpoint must accept that header.

## Configure optional provider variables

Standard OpenAI requires neither optional variable. To configure Azure or another Responses API provider:

1. Open the GitHub repository and select **Settings**.
2. Select **Secrets and variables**, then **Actions**.
3. On the **Variables** tab, select **New repository variable**.
4. Enter `OPENAI_RESPONSES_API_ENDPOINT` as the name and the full Responses API URL as the value, then select **Add variable**.
5. Select **New repository variable** again. Enter `OPENAI_CODEX_MODEL` as the name and the model or deployment name as the value, then select **Add variable**.

Azure requires `OPENAI_RESPONSES_API_ENDPOINT`. Include the `/v1/responses` suffix and any required query parameters. Azure may also require `OPENAI_CODEX_MODEL` with its model or deployment name.

## Review scope

The workflow runs for the `opened` and `synchronize` pull request events. These events cover a new pull request and each new head commit. Per-PR concurrency cancels an older run when another commit arrives.

The workflow reviews only same-repository pull requests from non-bot actors. It skips fork and bot pull requests before starting the secret-bearing job. It uses `pull_request`, not `pull_request_target`, because GitHub warns against checking out untrusted pull request code in a privileged workflow.

The review job has read-only repository access. Codex uses the `:read-only` permission profile and the `drop-sudo` safety strategy. A separate job has permission to read the pull request and write its issue comment. That job receives no checkout and no OpenAI key.

Before posting, the workflow compares the reviewed head SHA with the current pull request head. It discards stale output. It updates one marked comment instead of adding a comment for every push.

## Why this uses the GitHub Action

Codex cloud supports automatic review when a pull request opens. Current OpenAI documentation does not clearly promise another automatic review for every new commit. The official `openai/codex-action` supports a custom workflow with exact `opened` and `synchronize` triggers.

The workflow pins every external action to the commit behind its documented major version.

## Primary sources

- [Codex GitHub Action](https://github.com/openai/codex-action)
- [Codex GitHub Action security](https://github.com/openai/codex-action/blob/main/docs/security.md)
- [Codex cloud code review](https://developers.openai.com/codex/cloud/code-review)
- [GitHub pull request events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request)
- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
