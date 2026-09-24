from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

StudyId = Annotated[str, Field(pattern=r"^STUDY-[A-Z0-9-]+$")]
ClaimId = Annotated[str, Field(pattern=r"^C-[A-Z0-9-]+$")]
ValidationResultId = Annotated[str, Field(pattern=r"^VR-[A-Z0-9-]+$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ManifestEntry(StrictModel):
    artifact_id: str
    kind: str
    name: str
    version: str
    authority_tier: int = Field(ge=1, le=6)
    checksum: str
    locked: bool
    authorized_by: str


class DoseGroup(StrictModel):
    group_id: str
    label: str
    dose: float
    study_id: str
    dose_unit: str
    sexes: list[Literal["M", "F"]]
    planned_n_per_sex: int = Field(gt=0)


class Study(StrictModel):
    study_id: StudyId
    study_type_id: str
    species: str
    route: str
    duration_days: int = Field(gt=0)
    study_start: str
    protocol_version: str
    dose_groups: list[DoseGroup]


class Animal(StrictModel):
    animal_id: str
    study_id: str
    group_id: str
    sex: Literal["M", "F"]
    randomization_id: str


class Measurement(StrictModel):
    record_id: str
    domain: str
    animal_id: str | None = None
    group_id: str | None = None
    timepoint: str
    test_code: str
    value: float | str
    unit: str | None
    grain: str
    source_pointer: str


class MicroscopicFinding(StrictModel):
    finding_id: str
    domain: Literal["MI"]
    animal_id: str
    tissue: str
    finding: str
    severity: str
    controlled_term: str
    source_pointer: str


class StudyRecords(StrictModel):
    animals: list[Animal]
    body_weights: list[Measurement]
    clinical_observations: list[Measurement]
    food_consumption: list[Measurement]
    organ_weights: list[Measurement]
    microscopic_findings: list[MicroscopicFinding]
    formulation: list[Measurement]


class SectionStatus(StrEnum):
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"


class ReportSection(StrictModel):
    section_id: str
    template_id: str
    title: str
    required_fields: int
    status: SectionStatus


class ClaimStatus(StrEnum):
    PENDING = "pending"
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"


class Claim(StrictModel):
    claim_id: ClaimId
    section_id: str
    field_id: str
    value: float | None
    unit: str
    grain: str
    status: ClaimStatus


class ProvenanceEdge(StrictModel):
    edge_id: str
    claim_id: str
    source_record_id: str
    transform_id: str
    source_pointer: str
    authority_tier: int = Field(ge=1, le=6)


class ValidationStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIPPED = "skipped"


class ValidationKind(StrEnum):
    DETERMINISTIC = "deterministic"
    AGENT_PLANNED = "agent_planned"


class ValidationResult(StrictModel):
    result_id: ValidationResultId
    rule_id: str
    scope_id: str
    severity: Literal["info", "warning", "blocker"]
    status: ValidationStatus
    evidence_ids: list[str]
    message: str
    rule_version: str
    kind: ValidationKind = ValidationKind.DETERMINISTIC
    tool_name: str | None = None


class DispositionDecision(StrEnum):
    OPEN = "open"
    CORRECTED = "corrected"
    EXPLAINED_IN_NSDRG = "explained_in_nsdrg"
    APPROVED_EXCEPTION = "approved_exception"
    REJECTED = "rejected"


RESOLVED_DISPOSITIONS = frozenset(
    {
        DispositionDecision.CORRECTED,
        DispositionDecision.EXPLAINED_IN_NSDRG,
        DispositionDecision.APPROVED_EXCEPTION,
    }
)


class ReviewDisposition(StrictModel):
    disposition_id: str
    result_id: str
    decision: DispositionDecision
    reason: str | None
    reviewer: str | None
    timestamp: str | None


class ApprovalRole(StrEnum):
    PATHOLOGIST = "pathologist"
    PEER_REVIEWER = "peer_reviewer"
    QAU = "qau"
    STUDY_DIRECTOR = "study_director"


class Approval(StrictModel):
    approval_id: str
    role: ApprovalRole
    reviewer: str
    meaning: str
    timestamp: str


class GateStatus(StrEnum):
    BLOCKED = "blocked"
    READY_FOR_REVIEW = "ready_for_review"
    READY_FOR_SIGNATURE = "ready_for_signature"
    READY_FOR_EXPORT = "ready_for_export"
    EXPORTED = "exported"


class GateDecision(StrictModel):
    gate_id: str
    gate_type: Literal["section", "release"]
    status: GateStatus
    blocking_result_ids: list[str]
    decided_at: str


class ExportArtifact(StrictModel):
    artifact_id: str
    kind: str
    path: str
    checksum: str | None
    status: Literal["pending", "exported"]


class WorkflowEvent(StrictModel):
    event_id: str
    event: str
    actor: str
    timestamp: str
    outcome: str
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class RetrievalIndexEntry(StrictModel):
    chunk_id: str
    study_id: StudyId
    study_type_id: str
    artifact_id: str
    artifact_version: str
    source_kind: str
    authority_tier: int = Field(ge=1, le=6)
    report_section_id: str
    grain: str
    lock_manifest_id: str


class StudyEvidencePackage(StrictModel):
    package_id: str
    label: Literal["SYNTHETIC / NOT FOR SUBMISSION"]
    workflow_state: str
    manifest: list[ManifestEntry]
    study: Study
    records: StudyRecords
    report_sections: list[ReportSection]
    claims: list[Claim]
    provenance_edges: list[ProvenanceEdge]
    validation_results: list[ValidationResult]
    review_dispositions: list[ReviewDisposition]
    approvals: list[Approval] = Field(default_factory=list)
    gate_decisions: list[GateDecision]
    export_artifacts: list[ExportArtifact]
    retrieval_index: list[RetrievalIndexEntry]
    events: list[WorkflowEvent]


class PlannerMode(StrEnum):
    FIXTURE = "fixture"
    OPENAI_COMPATIBLE = "openai_compatible"


class ValidationRequest(StrictModel):
    planner: PlannerMode = PlannerMode.FIXTURE


class ValidationRun(StrictModel):
    run_id: str
    study_id: str
    planner: PlannerMode
    llm_used: bool
    planner_label: str
    rule_bundle_version: str
    results: list[ValidationResult]
    created_at: datetime


class DispositionCommand(StrictModel):
    decision: Literal[
        DispositionDecision.CORRECTED,
        DispositionDecision.EXPLAINED_IN_NSDRG,
        DispositionDecision.APPROVED_EXCEPTION,
    ]
    reason: str = Field(min_length=8, max_length=500)
    reviewer: str = Field(min_length=2, max_length=120)


class ApprovalCommand(StrictModel):
    role: ApprovalRole
    reviewer: str = Field(min_length=2, max_length=120)
    meaning: str = Field(min_length=4, max_length=200)


class ExportCommand(StrictModel):
    actor: str = Field(min_length=2, max_length=120)
    idempotency_key: str = Field(min_length=8, max_length=120)


class RegulatoryReference(StrictModel):
    reference_id: str
    title: str
    citation: str
    url: str
    authority: Literal["regulation", "guidance", "standard", "test_guideline"]
    binding: bool


class ReportFieldTemplate(StrictModel):
    field_id: str
    label: str
    required: bool
    expected_grain: str
    human_judgment: bool
    source_expectation: str
    regulatory_reference_ids: list[str]


class ReportSectionTemplate(StrictModel):
    section_id: str
    title: str
    purpose: str
    fields: list[ReportFieldTemplate]


class ReportTemplate(StrictModel):
    template_id: str
    name: str
    version: str
    study_type_id: str
    ctd_location: str
    disclaimer: str
    references: list[RegulatoryReference]
    sections: list[ReportSectionTemplate]


class ReportBlock(StrictModel):
    block_id: str
    kind: Literal["paragraph", "claim", "review_marker"]
    text: str
    claim_id: str | None = None
    provenance_count: int = 0


class AssembledSection(StrictModel):
    section_id: str
    title: str
    status: SectionStatus
    required_field_count: int
    fields: list[ReportFieldTemplate]
    blocks: list[ReportBlock]


class ReportAssembly(StrictModel):
    template: ReportTemplate
    sections: list[AssembledSection]


class SourceRecord(StrictModel):
    record_id: str
    domain: str
    source_pointer: str
    value: float | str
    unit: str | None
    grain: str
    attributes: dict[str, str | int | float | None]


class EvidenceChain(StrictModel):
    claim: Claim
    sources: list[SourceRecord]
    transform_id: str | None
    recomputed_value: float | None
    exact_match: bool | None
    validations: list[ValidationResult]
    report_text: str


class Stage(StrictModel):
    stage_id: str
    name: str
    owner: Literal["agent", "human", "hybrid"]
    status: Literal["complete", "current", "blocked", "pending"]
    summary: str
    input_title: str
    input_detail: str
    output_title: str
    output_detail: str
    boundary: str
    checks: list[str]


class WorkspaceSummary(StrictModel):
    record_count: int
    source_count: int
    provenance_count: int
    blocker_count: int
    resolved_blocker_count: int
    section_count: int


class PlannerCapability(StrictModel):
    mode: PlannerMode
    available: bool
    label: str
    detail: str


class StudyListItem(StrictModel):
    study_id: str
    study_type_id: str
    title: str
    workflow_state: str
    release_status: GateStatus
    label: str


class SectionRunCommand(StrictModel):
    section_package_id: str = Field(min_length=1, max_length=120)
    idempotency_key: str = Field(min_length=8, max_length=160)


class SectionRunEligibility(StrictModel):
    section_package_id: str
    eligible: bool
    reasons: list[str]


class SectionDraftCandidate(StrictModel):
    schema_version: Literal["helix.section-draft-candidate/v1"]
    status: Literal["section_draft_candidate"]
    candidate_id: Annotated[str, Field(pattern=r"^SDC-[A-Z0-9-]+$")]
    run_id: str
    section_id: str
    section_package_id: str
    section_package_version: str
    drafting_cycle_id: str
    attempt: int = Field(ge=1, le=3)
    validated_claim_ids: list[str] = Field(min_length=1)
    content_blocks: list[dict[str, object]] = Field(min_length=1)
    executor_receipt_ids: list[str]
    agent_receipt: dict[str, str]


class SectionRunReceipt(StrictModel):
    run_id: str
    section_id: str
    section_package_id: str
    status: Literal["candidate_recorded"]
    candidate_id: str
    candidate_hash: str
    envelope_hash: str
    agent_runtime: Literal["codex_sdk"]
    codex_thread_id: str
    skill_name: Literal["helix-section-agent"]
    skill_hash: str
    review_scaffold_revision: int
    idempotent_replay: bool = False


class StoredSectionRun(StrictModel):
    receipt: SectionRunReceipt
    candidate: SectionDraftCandidate
    envelope: dict[str, object]
    review_scaffold: dict[str, object]


class WorkspaceResponse(StrictModel):
    label: str
    study: Study
    manifest: list[ManifestEntry]
    workflow_state: str
    stages: list[Stage]
    summary: WorkspaceSummary
    claims: list[Claim]
    validations: list[ValidationResult]
    dispositions: list[ReviewDisposition]
    approvals: list[Approval]
    release_gate: GateDecision
    export_artifacts: list[ExportArtifact]
    report: ReportAssembly
    events: list[WorkflowEvent]
    planner_capabilities: list[PlannerCapability]
    section_run_eligibility: list[SectionRunEligibility]
    section_runs: list[StoredSectionRun]


class ExportReceipt(StrictModel):
    study_id: str
    status: Literal["exported"]
    exported_at: str
    artifacts: list[ExportArtifact]
    idempotent_replay: bool


# --------------------------------------------------------------------------- #
# Section drafts (per-section generated content for the UI)
# --------------------------------------------------------------------------- #

SectionDraftStatus = Literal["needs_review", "proposed", "verified", "discarded", "empty"]


class ProseBlock(StrictModel):
    kind: Literal["prose"] = "prose"
    markdown: str


class TableBlock(StrictModel):
    kind: Literal["table"] = "table"
    title: str
    columns: list[str]
    rows: list[list[str]]


class NoteBlock(StrictModel):
    kind: Literal["note"] = "note"
    text: str


SectionBlock = Annotated[ProseBlock | TableBlock | NoteBlock, Field(discriminator="kind")]


class SectionDraft(StrictModel):
    section_id: str
    title: str
    version: int
    status: SectionDraftStatus
    data_available: bool
    blocks: list[SectionBlock]
    narrative_md: str | None = None
    note: str | None = None
    provenance_count: int = 0
    feedback: list[str] = Field(default_factory=list)
    model: str | None = None
    created_at: str


class SectionListItem(StrictModel):
    section_id: str
    title: str
    order: int
    template_section: str | None
    has_verified_claims: bool
    status: SectionDraftStatus
    version: int | None = None
    data_available: bool | None = None


class DraftRequest(StrictModel):
    feedback: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Chat (per-study thread, grounded in verified data)
# --------------------------------------------------------------------------- #

ChatScope = Literal["section", "study"]


class ChatMessage(StrictModel):
    message_id: int
    role: Literal["user", "assistant"]
    content: str
    scope: ChatScope
    section_id: str | None = None
    intent: Literal["ask", "revise"] = "ask"
    created_at: str


class ChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    scope: ChatScope = "section"
    section_id: str | None = None
