import json
from functools import lru_cache
from pathlib import Path

from .schemas import (
    RESOLVED_DISPOSITIONS,
    ApprovalRole,
    AssembledSection,
    ReportAssembly,
    ReportBlock,
    ReportTemplate,
    StudyEvidencePackage,
)


@lru_cache
def load_report_template() -> ReportTemplate:
    path = Path(__file__).parent / "data" / "report-template.json"
    return ReportTemplate.model_validate(json.loads(path.read_text()))


def claim_report_text(package: StudyEvidencePackage, claim_id: str) -> str:
    claim = next((claim for claim in package.claims if claim.claim_id == claim_id), None)
    if claim is None:
        # A package can legitimately hold evidence and no claims yet - an
        # uploaded study starts that way, because computing claims is the
        # executor's job. The section renders a review marker instead of
        # raising, which would take down the whole workspace response.
        return f"[NEEDS REVIEW: no validated claim {claim_id} has been computed yet.]"
    if claim_id == "C-BW-HIGH":
        return (
            f"Terminal mean body weight in the combined high-dose group was {claim.value:.1f} {claim.unit}."
        )
    if claim_id in {"C-BW-HIGH-M", "C-BW-HIGH-F"}:
        sex = "males" if claim_id.endswith("-M") else "females"
        source_count = sum(edge.claim_id == claim_id for edge in package.provenance_edges)
        return (
            f"Terminal mean body weight in high-dose {sex} was "
            f"{claim.value:.1f} {claim.unit} (n={source_count})."
        )
    if claim_id == "C-MI-LIVER":
        severity = "Minimal" if _result_resolved(package, "VR-005") else "Moderate"
        return (
            f"{severity} hepatocellular hypertrophy was recorded in "
            f"{int(claim.value or 0)} high-dose animals."
        )
    if _result_resolved(package, "VR-006"):
        return (
            "No NOAEL was assigned in this synthetic pattern test. "
            "Qualified interpretation remains outside the prototype."
        )
    return "[NEEDS REVIEW: A qualified scientist must determine the NOAEL.]"


def assemble_report(package: StudyEvidencePackage) -> ReportAssembly:
    template = load_report_template()
    section_state = {section.section_id: section for section in package.report_sections}
    claim_edges = {
        claim.claim_id: sum(edge.claim_id == claim.claim_id for edge in package.provenance_edges)
        for claim in package.claims
    }
    blocks = _report_blocks(package, claim_edges)
    sections = [
        AssembledSection(
            section_id=section.section_id,
            title=section.title,
            status=section_state[section.section_id].status,
            required_field_count=sum(field.required for field in section.fields),
            fields=section.fields,
            blocks=blocks[section.section_id],
        )
        for section in template.sections
    ]
    return ReportAssembly(template=template, sections=sections)


def _report_blocks(
    package: StudyEvidencePackage, claim_edges: dict[str, int]
) -> dict[str, list[ReportBlock]]:
    study = package.study
    groups = ", ".join(f"{group.label} {group.dose:g} {group.dose_unit}" for group in study.dose_groups)
    return {
        "S1": [
            ReportBlock(
                block_id="S1-P1",
                kind="paragraph",
                text=(
                    f"{study.study_id} is a synthetic {study.duration_days}-day study in {study.species}. "
                    "Quality assurance and study director signatures remain controlled human records."
                ),
            )
        ],
        "S2": [
            ReportBlock(
                block_id="S2-P1",
                kind="paragraph",
                text=(
                    "The study evaluated repeat-dose oral toxicity under protocol "
                    f"version {study.protocol_version}. Protocol changes and deviations remain "
                    "linked records."
                ),
            )
        ],
        "S3": [
            ReportBlock(
                block_id="S3-P1",
                kind="paragraph",
                text=(
                    f"Forty animals received {study.route} dosing for {study.duration_days} days. "
                    f"The planned groups were {groups}."
                ),
            )
        ],
        "S4": [
            ReportBlock(
                block_id="S4-P1",
                kind="paragraph",
                text=(
                    "Formulation concentrations were taken from signed synthetic analytical records. "
                    "Each result retains its concentration and timepoint grain."
                ),
            )
        ],
        "S5": _body_weight_blocks(package, claim_edges),
        "S6": _clinical_pathology_blocks(package),
        "S7": _microscopic_blocks(package, claim_edges),
        "S8": _conclusion_blocks(package, claim_edges),
    }


def _body_weight_blocks(package: StudyEvidencePackage, claim_edges: dict[str, int]) -> list[ReportBlock]:
    sex_claims = [claim_id for claim_id in ("C-BW-HIGH-M", "C-BW-HIGH-F") if claim_id in claim_edges]
    if len(sex_claims) == 2 and _result_resolved(package, "VR-004"):
        return [
            ReportBlock(
                block_id="S5-P1",
                kind="paragraph",
                text="Body weight records were summarized by sex with the mean-by-sex-v1 transform.",
            ),
            *[
                ReportBlock(
                    block_id=f"S5-{claim_id}",
                    kind="claim",
                    text=claim_report_text(package, claim_id),
                    claim_id=claim_id,
                    provenance_count=claim_edges.get(claim_id, 0),
                )
                for claim_id in sex_claims
            ],
        ]
    return [
        ReportBlock(
            block_id="S5-P1",
            kind="paragraph",
            text="Body weight records were summarized with the versioned mean-v1 transform.",
        ),
        ReportBlock(
            block_id="S5-C1",
            kind="claim",
            text=claim_report_text(package, "C-BW-HIGH"),
            claim_id="C-BW-HIGH",
            provenance_count=claim_edges.get("C-BW-HIGH", 0),
        ),
        ReportBlock(
            block_id="S5-R1",
            kind="review_marker",
            text=(
                "[NEEDS REVIEW: The sponsor table requires dose group by sex. "
                "This draft combines ten animals.]"
            ),
            claim_id="C-BW-HIGH",
            provenance_count=claim_edges.get("C-BW-HIGH", 0),
        ),
    ]


def _clinical_pathology_blocks(package: StudyEvidencePackage) -> list[ReportBlock]:
    reviewed = any(approval.role == ApprovalRole.STUDY_DIRECTOR for approval in package.approvals)
    if reviewed:
        return [
            ReportBlock(
                block_id="S6-P1",
                kind="paragraph",
                text=(
                    "Clinical pathology source domains are not present in this synthetic bundle. "
                    "The omission is disclosed and no values were inferred from model knowledge."
                ),
            )
        ]
    return [
        ReportBlock(
            block_id="S6-R1",
            kind="review_marker",
            text=(
                "[NEEDS REVIEW: Clinical pathology source domains are not present in this "
                "synthetic bundle. The section remains visible rather than filled from model knowledge.]"
            ),
        )
    ]


def _microscopic_blocks(package: StudyEvidencePackage, claim_edges: dict[str, int]) -> list[ReportBlock]:
    blocks = [
        ReportBlock(
            block_id="S7-C1",
            kind="claim",
            text=claim_report_text(package, "C-MI-LIVER"),
            claim_id="C-MI-LIVER",
            provenance_count=claim_edges.get("C-MI-LIVER", 0),
        )
    ]
    if not _result_resolved(package, "VR-005"):
        blocks.append(
            ReportBlock(
                block_id="S7-R1",
                kind="review_marker",
                text=(
                    "[NEEDS REVIEW: The pattern draft says moderate. The four locked MI records say minimal.]"
                ),
                claim_id="C-MI-LIVER",
                provenance_count=claim_edges.get("C-MI-LIVER", 0),
            )
        )
    return blocks


def _conclusion_blocks(package: StudyEvidencePackage, claim_edges: dict[str, int]) -> list[ReportBlock]:
    resolved = _result_resolved(package, "VR-006")
    return [
        ReportBlock(
            block_id="S8-R1",
            kind="paragraph" if resolved else "review_marker",
            text=claim_report_text(package, "C-NOAEL"),
            claim_id="C-NOAEL",
            provenance_count=claim_edges.get("C-NOAEL", 0),
        )
    ]


def _result_resolved(package: StudyEvidencePackage, result_id: str) -> bool:
    dispositions = [
        disposition for disposition in package.review_dispositions if disposition.result_id == result_id
    ]
    return bool(dispositions and dispositions[-1].decision in RESOLVED_DISPOSITIONS)
