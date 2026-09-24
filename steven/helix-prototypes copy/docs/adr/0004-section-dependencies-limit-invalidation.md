# Section dependencies limit invalidation

HELIX does not halt all section processing when one section is blocked. It computes a section impact set from an explicit dependency graph, represents directly affected and transitively dependent sections as blockers and `[NEEDS REVIEW]` placeholders in the study-wide Review Scaffold, and allows independent sections to produce Section Draft Candidates; however, any required source-data change outside the frozen manifest remains a study release blocker until a governed replacement run resolves it.
