# Use a content-addressed Workflow Trace

HELIX records each deterministic executor, Skill Invocation, evaluation, Human Gate, and export action as an immutable Step Receipt linked to content-addressed Trace Artifacts. The backend derives the Workspace Journey and Workflow Trace from these records, while Rule Bundles and gate executors retain authority. This choice makes retries and provenance inspectable without treating client activity, model output, or a third mutable event list as truth.

## Considered options

- Keep progress only in the `StudyEvidencePackage` and browser state.
- Add immutable Step Receipts and Trace Artifacts in PostgreSQL.
- Move orchestration and trace state to Azure Service Bus and Durable Functions.

## Consequences

PostgreSQL remains the one persistence boundary for the demo. Existing embedded and relational event representations must converge on the trace ledger instead of gaining another independent writer. Service Bus and Durable Functions remain deferred until measured load or recovery needs justify them.
