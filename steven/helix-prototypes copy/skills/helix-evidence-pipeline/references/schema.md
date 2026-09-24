# HELIX evidence schema

This reference defines the stable records shared by ingest, retrieval, validation, drafting, review, and export.

## Study evidence package

```json
{
  "package_id": "PKG-HLX-028",
  "label": "SYNTHETIC / NOT FOR SUBMISSION",
  "workflow_state": "validated",
  "run_plan": {},
  "manifest": [],
  "study": {},
  "records": {},
  "report_sections": [],
  "claims": [],
  "provenance_edges": [],
  "validation_results": [],
  "section_draft_candidates": [],
  "section_drafts": [],
  "review_scaffold_revisions": [],
  "review_dispositions": [],
  "gate_decisions": [],
  "export_artifacts": [],
  "events": []
}
```

Treat IDs as immutable strings. Store display text separately from IDs. Store units beside values. Store the grain on every measurement and every report field.

## Core records

| Record | Required fields | Invariant |
| --- | --- | --- |
| `ManifestEntry` | `artifact_id`, `kind`, `name`, `version`, `checksum`, `authority_tier`, `locked`, `authorized_by` | A later stage may reference only a frozen entry. |
| `RunPlan` | `run_plan_id`, `run_id`, `version`, `fingerprint`, `governed_versions`, `nodes` | The backend validates every dependency and rejects a cycle before storage. |
| `Study` | `study_id`, `study_type_id`, `species`, `route`, `duration_days`, `study_start`, `protocol_version` | `study_type_id` resolves before extraction. |
| `DoseGroup` | `group_id`, `study_id`, `dose`, `dose_unit`, `sexes`, `planned_n_per_sex` | Dose and cohort plan come from the protocol. |
| `Animal` | `animal_id`, `study_id`, `group_id`, `sex`, `randomization_id` | One animal belongs to one frozen group. |
| `Measurement` | `record_id`, `domain`, `animal_id` or `group_id`, `timepoint`, `test_code`, `value`, `unit`, `grain`, `source_pointer` | Keys match the domain grain. |
| `Finding` | `finding_id`, `domain`, `animal_id`, `tissue`, `finding`, `severity`, `controlled_term`, `source_pointer` | Submitted terms map to a versioned terminology set. |
| `ReportSection` | `section_id`, `template_id`, `title`, `required_fields`, `status` | Status derives from its fields and claims. |
| `Claim` | `claim_id`, `section_id`, `field_id`, `value`, `unit`, `grain`, `status` | A numeric claim has at least one provenance edge. |
| `ProvenanceEdge` | `edge_id`, `claim_id`, `source_record_id`, `transform_id`, `source_pointer`, `authority_tier` | The edge identifies the exact record and deterministic transform. |
| `ValidationResult` | `result_id`, `rule_id`, `scope_id`, `severity`, `status`, `evidence_ids`, `message`, `rule_version` | Blocking failures prevent release. |
| `SectionDraftCandidate` | `candidate_id`, `run_id`, `section_id`, `section_package_id`, `drafting_cycle_id`, `attempt`, `validated_claim_ids`, `content_blocks`, `agent_receipt` | A Section Agent creates candidates but cannot promote them. |
| `SectionDraft` | `draft_id`, `candidate_id`, `content_hash`, `promoted_at`, `gate_decision_ids` | Shared code creates a draft only after deterministic promotion conditions pass. |
| `ReviewScaffoldRevision` | `revision_id`, `sequence`, `content_hash`, `triggering_event_id`, `predecessor_id`, `section_artifact_ids` | Revisions are append-only and cannot enter final export. |
| `ReviewDisposition` | `disposition_id`, `result_id`, `decision`, `reason`, `reviewer`, `timestamp` | Decisions are append-only. |
| `GateDecision` | `gate_id`, `gate_type`, `status`, `blocking_result_ids`, `decided_at` | A gate derives from recorded results and approvals. |
| `ExportArtifact` | `artifact_id`, `kind`, `path`, `checksum`, `status` | Artifacts become final only after explicit export. |

## Grain values

- `study`
- `dose_group`
- `dose_group_x_sex`
- `animal`
- `animal_x_day`
- `animal_x_tissue`
- `group_x_week`
- `concentration_x_timepoint`
- `endpoint_x_group_comparison`

## Status values

- Workflow: `pending`, `running`, `blocked`, `complete`.
- Claim: `pending`, `validated`, `needs_review`, `approved`.
- Validation: `pass`, `warn`, `fail`.
- Enforcement: `hard_blocker`, `review_required`, `warning`.
- Candidate: `section_draft_candidate`.
- Disposition: `open`, `corrected`, `explained_in_nsdrg`, `approved_exception`, `rejected`.
- Gate: `blocked`, `ready_for_review`, `ready_for_signature`, `ready_for_export`, `exported`.

## Boundary checks

Validate external files when parsing them into these records. Internal functions should accept only normalized records. Do not repeat CSV, DOCX, PDF, or vendor-format checks inside report logic.
