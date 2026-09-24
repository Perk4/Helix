# Study runs cannot mutate governance versions

Every HELIX study run is pinned to exact schema, ontology, rule-bundle, drafting-skill, and Promptfoo-suite versions. Unrecognized input creates a quarantined mapping proposal marked `[NEEDS REVIEW]`; an authorized person must approve a new governed version and rerun the study, preventing a run from changing the rules by which its own evidence and release readiness are judged.
