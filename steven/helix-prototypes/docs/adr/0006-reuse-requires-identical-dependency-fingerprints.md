# Reuse requires identical dependency fingerprints

A superseding run may reuse unchanged parsing, normalized records, and embeddings through content-addressed caching. A section artifact may be carried forward only when its complete dependency fingerprint is identical and its predecessor lineage is recorded; regardless of reuse, the superseding run issues fresh validation results and gate decisions so authority never leaks across run boundaries.
