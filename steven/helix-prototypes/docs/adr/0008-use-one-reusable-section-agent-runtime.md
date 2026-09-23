# Use one reusable Section Agent runtime

HELIX uses one versioned Section Agent runtime instantiated independently for each report section and configured by the applicable Section Package. Instances may run concurrently when the section dependency graph permits, but all use the same orchestration protocol and shared parsing, validation, drafting, and gating executors, preventing behavior from drifting across bespoke section implementations.
