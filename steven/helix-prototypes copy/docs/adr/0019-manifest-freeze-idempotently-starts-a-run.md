# Manifest freeze idempotently starts a run

Freezing an authorized manifest emits one `run_requested` event that automatically starts the applicable Data Validation Packages after deterministic study-type resolution. The event is idempotent: replaying it resumes or returns the existing Pinned Run identified by the frozen manifest and governed-version set rather than creating duplicate processing or audit history.
