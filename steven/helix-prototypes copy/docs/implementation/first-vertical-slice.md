# Prove a frontend-triggered Codex SDK section run

This slice adds the smallest honest agent path to the existing workbench. A browser action starts a FastAPI command, FastAPI invokes the real Codex SDK, Codex loads the repo skill, and the backend stores a validated Section Draft Candidate and an execution receipt.

The slice targets the terminal body-weight component of `5_2_3_body_weight`. It does not promote the full section because the target Section Package is intentionally incomplete in this slice.

## Definition of done

The slice is complete only when a Playwright run proves this path:

```text
frontend button
  -> POST /api/v1/studies/{study_id}/section-runs
  -> FastAPI SectionRunService
  -> Python Codex SDK
  -> explicit $helix-section-agent invocation
  -> schema-validated section_draft_candidate
  -> append-only receipt and Review Scaffold Revision
  -> receipt rendered in the frontend
```

The live proof must use the Codex SDK. A fixture, mocked response, or direct model call does not meet this acceptance criterion.

## Use the Python Codex SDK

The backend already requires Python 3.12. The official Python Codex SDK requires Python 3.10 or later, so it fits the current service. Add `openai-codex` to `backend/pyproject.toml`.

The SDK controls the local Codex app server and ships with a pinned Codex runtime. Start a read-only thread for this slice. Do not hard-code a model in the first implementation. Use the configured Codex default unless the deployment adds an explicit governed model setting.

Official setup and API examples are in the [Codex SDK documentation](https://developers.openai.com/codex/codex-sdk/).

## Add the repo skill

Use [`.agents/skills/helix-section-agent/SKILL.md`](../../.agents/skills/helix-section-agent/SKILL.md). Codex discovers repo skills from `.agents/skills`. The backend prompt must invoke `$helix-section-agent` explicitly and provide the path or identifier for one `SectionExecutionEnvelope`.

The skill returns JSON that matches [`section-draft-candidate.schema.json`](../../skills/helix-evidence-pipeline/contracts/section-draft-candidate.schema.json). The FastAPI boundary validates the JSON before the repository stores it.

The official [skills documentation](https://learn.chatgpt.com/codex/build-skills) describes the skill directory, progressive loading, repository discovery, and explicit invocation.

## Add one backend command

Add these files:

```text
backend/app/agents/codex_section_agent.py
backend/app/section_runs.py
backend/tests/test_section_runs.py
```

Add this endpoint:

```http
POST /api/v1/studies/{study_id}/section-runs
Content-Type: application/json

{
  "section_package_id": "section.5_2_3_body_weight",
  "idempotency_key": "workbench-STUDY-HLX-028-body-weight-v1"
}
```

Return a receipt with enough evidence to distinguish a real SDK run from a fixture:

```json
{
  "run_id": "SRUN-...",
  "section_id": "5_2_3_body_weight",
  "status": "candidate_recorded",
  "candidate_id": "SDC-...",
  "candidate_hash": "sha256:...",
  "agent_runtime": "codex_sdk",
  "codex_thread_id": "...",
  "skill_name": "helix-section-agent",
  "skill_hash": "sha256:...",
  "review_scaffold_revision": 2
}
```

The service must complete these steps:

1. Load the Pinned Run and reject a mutable or mismatched manifest.
2. Confirm that `C-BW-HIGH` is a Validated Claim with provenance.
3. Check the body-weight Template Contract Gates.
4. Build a section-scoped execution envelope.
5. Start a read-only Codex SDK thread in the repository root.
6. Explicitly invoke `$helix-section-agent` with the envelope identifier.
7. Parse and validate the final JSON response.
8. Store the candidate, the Codex thread receipt, and a new study-wide Review Scaffold Revision atomically.

The first slice stops here. Provenance compilation and Template Conformance Gates can run, but the partial package sets `promotion_allowed` to `false` so the system cannot mistake this proof for a finished section.

## Add one frontend action

Add `runSectionAgent` to `frontend/src/lib/api.ts`. Add a **Draft body-weight component** button to `StudyJourney` after validation succeeds.

Disable the button until the backend reports that the claim and Template Contract Gates are ready. Do not derive eligibility in React.

After the command completes, render:

- `candidate_id` and `candidate_hash`.
- `agent_runtime` as `Codex SDK`.
- `skill_name` and `skill_hash`.
- `codex_thread_id`.
- The new Review Scaffold Revision number.

## Prove the browser path

Extend `frontend/tests/workbench.spec.ts` or add `frontend/tests/codex-section-run.spec.ts`. Keep the existing fixture-based test fast. Put the live proof behind `HELIX_CODEX_LIVE=1` and run it before accepting the slice.

The browser test must:

1. Open the workbench.
2. Run deterministic validation from the existing frontend button.
3. Click **Draft body-weight component**.
4. Wait for the backend command to finish.
5. Assert that the UI shows `Codex SDK` and `helix-section-agent`.
6. Assert that the candidate cites `C-BW-HIGH` and contains `286.2 g`.
7. Fetch the workspace and verify the stored Codex thread ID, skill hash, candidate hash, and Review Scaffold Revision.
8. Verify that the release gate remains blocked and the partial section is not promoted.
9. Capture a screenshot and save the API receipt under `evidence/`.

Add a script such as `scripts/verify-codex-section-run.sh` to start an isolated database, the API, and the frontend before running the live Playwright test. The script must fail when the SDK is unavailable or the agent response comes from a fixture.

## Test below the live proof

Add fast tests for failures that do not need a live agent:

- The API rejects an unknown or ineligible Section Package.
- The command is idempotent.
- The backend rejects malformed candidate JSON.
- The backend rejects a candidate with an unapproved claim ID.
- The backend rejects a missing Codex thread or skill receipt.
- The backend records no candidate when the SDK fails.
- The frontend keeps the button disabled when backend eligibility is false.

These tests protect the contract. They do not replace the live browser proof.

## Keep these items out of the first slice

- Parallel section execution.
- All 22 Section Packages.
- Embeddings.
- Report-pattern selection.
- Reviewer-role configuration.
- Final section promotion.
- Final export changes.

The first slice proves that the product can invoke one governed skill through the Codex SDK from the real frontend and preserve a verifiable receipt. Build the broader DAG only after that proof passes.
