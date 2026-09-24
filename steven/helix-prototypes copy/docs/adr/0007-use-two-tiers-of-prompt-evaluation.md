# Use two tiers of prompt evaluation

HELIX runs each skill's complete paired Promptfoo suite when promoting that skill version and permits pinned runs to reference only a passing qualification. During a study, HELIX runs study-specific output evaluations as advisory checks: failures create `[NEEDS REVIEW]`, but passes cannot satisfy deterministic gates or grant release authority.
