# HELIX ontology and retrieval rules

## Entity graph

```text
Study ─has_protocol→ Protocol
Study ─uses_template→ ReportTemplate
Study ─classified_as→ StudyType
StudyType ─selects→ PatternSet
Study ─has_group→ DoseGroup
DoseGroup ─contains→ Animal
Animal ─has_measurement→ Measurement
Animal ─has_finding→ Finding
SourceArtifact ─contains→ Measurement | Finding | ProtocolFact
ReportTemplate ─contains→ ReportSection
ReportSection ─requires→ ReportField
ReportField ─materializes_as→ Claim
Claim ─supported_by→ SourceRecord
Claim ─produced_by→ DeterministicTransform
Claim ─checked_by→ ValidationResult
ValidationResult ─uses→ ValidationRule
ValidationResult ─resolved_by→ ReviewDisposition
ReportSection ─controlled_by→ SectionGate
Study ─controlled_by→ ReleaseGate
ReleaseGate ─permits→ ExportArtifact
```

## Retrieval index

Index these fields for each chunk or record:

```text
record_id
study_id
study_type_id
artifact_id
artifact_version
source_kind
authority_tier
domain
endpoint
report_section_id
field_id
grain
sex
dose_group
timepoint
tissue
controlled_term_version
lock_manifest_id
```

## Retrieval policy

Filter before semantic ranking:

1. Match `lock_manifest_id` and `study_id`.
2. Match the resolved `study_type_id` and requested report section.
3. Require an allowed source kind and sufficient authority tier.
4. Require compatible grain and units.
5. Rank remaining records for section and endpoint relevance.

Return accepted candidates and rejected candidates with reason codes such as `wrong_manifest`, `wrong_study`, `grain_mismatch`, `authority_too_low`, `unit_mismatch`, or `unsupported_source_kind`.

Pattern retrieval and value retrieval are different operations. Prior approved reports may supply section order, preferred phrasing, and field expectations. They may not supply values for the current study.

## Validation rule registry

Each report field points to a rule with:

```text
field_id
expected_grain
minimum_authority_tier
allowed_source_kinds
allowed_units
controlled_terminology
aggregation_method
blocking
rule_version
```

Keep rule versions in provenance and validation output. A rerun with a newer rule bundle must not silently rewrite a historical decision.
