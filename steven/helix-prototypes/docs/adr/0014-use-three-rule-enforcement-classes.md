# Use three rule-enforcement classes

Every HELIX validation rule declares exactly one enforcement class: `hard_blocker` cannot be waived, `review_required` blocks until an artifact-bound human disposition resolves it, and `warning` remains visible without blocking progression. HELIX does not add nested severity levels or custom waiver categories.
