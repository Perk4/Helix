---
name: helix-evidence-pipeline
description: Build or simulate traceable nonclinical study evidence from authorized source files through deterministic extraction, validation, report drafting, human review, and gated export. Use for HELIX corpus design, synthetic studies, retrieval schemas, provenance checks, or FDA-facing nonclinical report workflow prototypes. Do not use it to declare regulatory compliance or FDA acceptance.
---

# HELIX evidence pipeline

Keep the workflow anchored to one immutable `StudyEvidencePackage`. Never let a UI view, narrative model, or retrieval result become a second source of truth.

Read [../../docs/architecture/agentic-report-pipeline.md](../../docs/architecture/agentic-report-pipeline.md) before changing the validation-to-drafting workflow. Validate package records against [contracts](contracts/README.md).

## Start

1. Confirm that every input is authorized for the task.
2. Freeze an input manifest with artifact IDs, versions, checksums, source authority, and lock state.
3. Read [references/schema.md](references/schema.md) before creating or changing records.
4. Read [references/ontology.md](references/ontology.md) before linking evidence.
5. Use `scripts/generate-synthetic-bundle.mjs` when real study data is unavailable or inappropriate. Label every generated record `SYNTHETIC / NOT FOR SUBMISSION`.

## Run the evidence workflow

Process the package through these states and preserve each transition:

1. `run_requested`
2. `parsed`
3. `study_resolved`
4. `validated`
5. `template_contract_passed`
6. `section_candidate_recorded`
7. `provenance_compiled`
8. `template_conformance_passed`
9. `section_promoted`
10. `review_scaffold_revised`
11. `approved`
12. `exported`

Each state transition appends an event with the actor, timestamp, input IDs, output IDs, rule or tool version, and outcome. Never rewrite an earlier event.

## Extraction and validation

- Resolve `study_type_id` deterministically from pinned protocol fields and a versioned mapping table.
- Run Data Validation Packages by evidence domain, not by report section.
- Use deterministic readers and transforms to create normalized records, Validated Claims, and source-to-claim provenance.
- Reject a candidate when its source version differs from the frozen manifest, its grain cannot satisfy the report field, or its authority is below the field rule.
- Keep embedding and report-pattern selection outside the active workflow.

## Section drafting

- Validate schema, keys, controlled terminology, units, grain, source authority, aggregation, cross-domain references, and report reconciliation.
- Bind every report claim to one or more `ProvenanceEdge` records.
- Run Template Contract Gates before starting a Section Agent.
- Give each Section Agent only its Section Execution Envelope. Do not put the full Run Plan or Study Evidence Package in agent context.
- Invoke the repo `helix-section-agent` skill explicitly and accept only a schema-valid Section Draft Candidate.
- Compile provenance for every factual span and table cell, then run study-output evaluation and Template Conformance Gates.
- Promote a candidate only through deterministic shared code.
- Render unresolved, conflicting, or missing evidence as `[NEEDS REVIEW]` with a reason code. Do not fill the gap from general model knowledge.
- Keep scientific interpretation separate. A qualified reviewer owns adversity, biological relevance, and NOAEL decisions.

## Gates and export

- Use only `hard_blocker`, `review_required`, and `warning` as rule-enforcement classes.
- A section promotes only when no hard blocker exists, every review-required result has a current disposition, provenance passes, and template conformance passes.
- Stop an autonomous drafting cycle after three Candidate Attempts. A human can start a new audited cycle for one section.
- Maintain an append-only history of Review Scaffold Revisions for the full study.
- Release stays blocked while any blocking validation result is open, required peer review is incomplete, the QAU statement is absent, the study director has not approved the report, or submission metadata is incomplete.
- Export requires a separate, explicit user action after release approval. Preparation is not export.
- Name the result `ready for signature`, `ready for export`, or `exported`. Never label it `FDA approved`.
- Record the selected FDA Data Standards Catalog snapshot and applicable standard versions. Do not hard-code one SEND version as universal.

## Deliverables

Return the frozen manifest, Run Plan, normalized study records, validation results, Validated Claims, Section Draft Candidates, provenance graph, Section Drafts, Review Scaffold Revisions, review dispositions, gate decisions, and export manifest. State which parts are synthetic, incomplete, or unverified.

Throughput checkpoint: after generation, run the schema and invariants check before building a UI or drafting report text.
