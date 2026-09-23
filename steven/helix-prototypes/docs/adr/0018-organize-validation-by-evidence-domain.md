# Organize validation by evidence domain

HELIX organizes Data Validation Packages around canonical evidence domains rather than report sections. Each package deterministically produces reusable Validated Claims and provenance once per pinned run, while Section Packages reference the required claim and rule identifiers; this prevents sections such as body weight, summary, and conclusion from independently recalculating the same evidence.
