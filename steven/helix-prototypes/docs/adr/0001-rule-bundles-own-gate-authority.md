# Rule bundles own gate authority

HELIX uses versioned executable rule bundles as the sole automated authority for section and release gate decisions. Codex skill files and Promptfoo evaluations specify and test expected behavior, but their results cannot independently turn a gate green; this preserves deterministic, reproducible, and auditable release decisions while still allowing prompt-driven extraction and drafting to evolve.
