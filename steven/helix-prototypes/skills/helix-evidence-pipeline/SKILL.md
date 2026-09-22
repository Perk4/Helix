---
name: helix-evidence-pipeline
description: Build or simulate traceable nonclinical study evidence from authorized source files through deterministic extraction, validation, report drafting, human review, and gated export. Use for HELIX corpus design, synthetic studies, retrieval schemas, provenance checks, or FDA-facing nonclinical report workflow prototypes. Do not use it to declare regulatory compliance or FDA acceptance.
---

# HELIX evidence pipeline

Keep the workflow anchored to one immutable `StudyEvidencePackage`. Never let a UI view, narrative model, or retrieval result become a second source of truth.

## Start

1. Confirm that every input is authorized for the task.
2. Freeze an input manifest with artifact IDs, versions, checksums, source authority, and lock state.
3. Read [references/schema.md](references/schema.md) before creating or changing records.
4. Read [references/ontology.md](references/ontology.md) before indexing, retrieving, or linking evidence.
5. Use `scripts/generate-synthetic-bundle.mjs` when real study data is unavailable or inappropriate. Label every generated record `SYNTHETIC / NOT FOR SUBMISSION`.

## Run the evidence workflow

Process the package through these states in order:

1. `authorized_upload`
2. `parsed`
3. `study_resolved`
4. `extracted`
5. `validated`
6. `drafted`
7. `provenance_compiled`
8. `gated`
9. `approved`
10. `exported`

Each state transition appends an event with the actor, timestamp, input IDs, output IDs, rule or tool version, and outcome. Never rewrite an earlier event.

## Retrieval and extraction

- Retrieve patterns and candidate evidence by `study_type`, `report_section`, `endpoint`, `source_authority`, and `grain`.
- Use approved prior reports to retrieve structure and phrasing patterns. Do not reuse their study values.
- Use retrieval to locate evidence. Use deterministic readers to extract values from the selected source records.
- Reject a candidate when its source version differs from the frozen manifest, its grain cannot satisfy the report field, or its authority is below the field rule.
- Return a ranked evidence set with rejection reasons. Do not return an unqualified best match.

## Validation and drafting

- Validate schema, keys, controlled terminology, units, grain, source authority, aggregation, cross-domain references, and report reconciliation.
- Bind every report claim to one or more `ProvenanceEdge` records.
- Draft narrative only around claims with `pass` validation results.
- Render unresolved, conflicting, or missing evidence as `[NEEDS REVIEW]` with a reason code. Do not fill the gap from general model knowledge.
- Keep scientific interpretation separate. A qualified reviewer owns adversity, biological relevance, and NOAEL decisions.

## Gates and export

- A section passes only when every required field is either validated or dispositioned for review, and every numeric claim has provenance.
- Release stays blocked while any blocking validation result is open, required peer review is incomplete, the QAU statement is absent, the study director has not approved the report, or submission metadata is incomplete.
- Export requires a separate, explicit user action after release approval. Preparation is not export.
- Name the result `ready for signature`, `ready for export`, or `exported`. Never label it `FDA approved`.
- Record the selected FDA Data Standards Catalog snapshot and applicable standard versions. Do not hard-code one SEND version as universal.

## Deliverables

Return the frozen manifest, normalized study records, retrieval index, validation results, report sections, provenance graph, review dispositions, gate decisions, and export manifest. State which parts are synthetic, incomplete, or unverified.

Throughput checkpoint: after generation, run the schema and invariants check before building a UI or drafting report text.
