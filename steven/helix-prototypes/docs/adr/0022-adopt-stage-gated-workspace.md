# Adopt the stage-gated HELIX workspace

The v1 UI uses one progress-controlled Workspace Journey instead of the v0 tabs for study journey, evidence chain, and report assembly. This makes Human Gates the visible control points, keeps Agent Steps subordinate to recorded workflow progress, and prevents the user from treating traceability review as an optional side view.

## Considered options

- Keep the three v0 tabs and restyle them.
- Replace the tabs with one nine-stage Workspace Journey.

## Consequences

Frontend work must move view selection, release state, traceability review, sign-offs, and export into one stage model. The backend journey contract must eventually expose the same nine-stage model so the client does not simulate production progress.
