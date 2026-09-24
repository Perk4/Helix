# Split template readiness from output conformance

HELIX evaluates the pinned template twice: pre-draft Template Contract Gates verify that required fields, locations, table shapes, labels, units, and style constraints are available and parseable before a Section Agent starts; post-draft Template Conformance Gates inspect the resulting Section Draft Candidate. This prevents drafting against a broken contract while retaining checks that are possible only after content exists.
