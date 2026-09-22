import csv
import io
import json
import textwrap
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from .reporting import assemble_report
from .schemas import ExportArtifact, StudyEvidencePackage


@dataclass(frozen=True)
class GeneratedArtifact:
    filename: str
    media_type: str
    content: bytes


def generate_artifact(package: StudyEvidencePackage, artifact: ExportArtifact) -> GeneratedArtifact:
    if artifact.kind == "study_report_pdf":
        return GeneratedArtifact(
            filename=Path(artifact.path).name,
            media_type="application/pdf",
            content=_pdf(_report_lines(package)),
        )
    if artifact.kind == "send_dataset_package":
        return GeneratedArtifact(
            filename="send-dataset-package.zip",
            media_type="application/zip",
            content=_dataset_zip(package),
        )
    if artifact.kind == "define_xml":
        return GeneratedArtifact(
            filename=Path(artifact.path).name,
            media_type="application/xml",
            content=_define_xml(package),
        )
    if artifact.kind == "nsdrg":
        return GeneratedArtifact(
            filename=Path(artifact.path).name,
            media_type="application/pdf",
            content=_pdf(_nsdrg_lines(package)),
        )
    raise ValueError(f"Unsupported export artifact kind {artifact.kind}")


def _report_lines(package: StudyEvidencePackage) -> list[str]:
    report = assemble_report(package)
    lines = [
        "HELIX SYNTHETIC NONCLINICAL STUDY REPORT",
        "SYNTHETIC / NOT FOR SUBMISSION",
        "",
        f"Study: {package.study.study_id}",
        f"Study type: {package.study.study_type_id}; species: {package.study.species}",
        f"Protocol: {package.study.protocol_version}",
        f"Template: {report.template.template_id} version {report.template.version}",
        "",
    ]
    for section in report.sections:
        lines.extend([f"{section.section_id}  {section.title}  [{section.status}]", ""])
        for field in section.fields:
            references = ", ".join(field.regulatory_reference_ids)
            lines.extend(
                textwrap.wrap(
                    f"Required field: {field.label}; grain: {field.expected_grain}; references: {references}",
                    width=88,
                )
            )
        lines.append("")
        for block in section.blocks:
            lines.extend(textwrap.wrap(block.text, width=88) or [""])
            if block.claim_id:
                lines.append(f"Evidence: {block.claim_id}; provenance edges: {block.provenance_count or 0}")
        lines.append("")
    lines.extend(
        [
            "Regulatory references",
            *[
                f"{reference.reference_id}: {reference.citation}; {reference.url}"
                for reference in report.template.references
            ],
            "",
            "Recorded approvals",
            *[
                f"{approval.role.value}: {approval.reviewer}; {approval.meaning}; {approval.timestamp}"
                for approval in package.approvals
            ],
            "",
            "Prototype notice: this document is not a GLP final report or an FDA submission.",
        ]
    )
    return lines


def _nsdrg_lines(package: StudyEvidencePackage) -> list[str]:
    datasets = _datasets(package)
    return [
        "HELIX SYNTHETIC NONCLINICAL STUDY DATA REVIEWER'S GUIDE",
        "SYNTHETIC / NOT FOR SUBMISSION",
        "",
        f"Study: {package.study.study_id}",
        "Purpose: exercise report-to-data lineage and explicit export controls.",
        "The accompanying CSV files are illustrative transport files, not SEND XPT datasets.",
        "No claim of SEND conformance or FDA acceptance is made.",
        "",
        "Included synthetic domains",
        *[f"{name.upper()}: {len(records)} records" for name, records in datasets.items()],
        "",
        "Recorded review dispositions",
        *[
            f"{item.result_id}: {item.decision.value}; {item.reviewer}; {item.reason}"
            for item in package.review_dispositions
        ],
    ]


def _datasets(package: StudyEvidencePackage) -> dict[str, list[object]]:
    return {
        "dm": list(package.records.animals),
        "bw": list(package.records.body_weights),
        "cl": list(package.records.clinical_observations),
        "fw": list(package.records.food_consumption),
        "om": list(package.records.organ_weights),
        "mi": list(package.records.microscopic_findings),
        "pc": list(package.records.formulation),
    }


def _dataset_zip(package: StudyEvidencePackage) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_STORED) as archive:
        manifest = {
            "label": package.label,
            "study_id": package.study.study_id,
            "format": "illustrative CSV; not SEND XPT",
            "datasets": {name.upper(): len(records) for name, records in _datasets(package).items()},
            "support_files": ["lineage.json", "workflow-audit.json"],
        }
        _zip_write(
            archive,
            "README.json",
            json.dumps(manifest, indent=2, sort_keys=True).encode(),
        )
        lineage = {
            "label": package.label,
            "claims": [claim.model_dump(mode="json") for claim in package.claims],
            "provenance_edges": [edge.model_dump(mode="json") for edge in package.provenance_edges],
        }
        workflow_audit = {
            "label": package.label,
            "validation_results": [result.model_dump(mode="json") for result in package.validation_results],
            "review_dispositions": [
                disposition.model_dump(mode="json") for disposition in package.review_dispositions
            ],
            "approvals": [approval.model_dump(mode="json") for approval in package.approvals],
            "events": [event.model_dump(mode="json") for event in package.events],
        }
        _zip_write(
            archive,
            "lineage.json",
            json.dumps(lineage, indent=2, sort_keys=True).encode(),
        )
        _zip_write(
            archive,
            "workflow-audit.json",
            json.dumps(workflow_audit, indent=2, sort_keys=True).encode(),
        )
        for name, records in _datasets(package).items():
            _zip_write(archive, f"{name}.csv", _csv_bytes(records, package.label))
    return output.getvalue()


def _csv_bytes(records: list[object], label: str) -> bytes:
    if not records:
        return b""
    rows = [{"_helix_label": label, **record.model_dump(mode="json")} for record in records]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: "" if value is None else value for key, value in row.items()} for row in rows)
    return output.getvalue().encode()


def _zip_write(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    item.compress_type = zipfile.ZIP_STORED
    item.external_attr = 0o644 << 16
    archive.writestr(item, content)


def _define_xml(package: StudyEvidencePackage) -> bytes:
    datasets = "".join(
        f'<Dataset name="{escape(name.upper())}" records="{len(records)}" />'
        for name, records in _datasets(package).items()
    )
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Define DocumentType="SYNTHETIC_NOT_FOR_SUBMISSION" '
        f'StudyId="{escape(package.study.study_id)}">'
        "<Notice>Illustrative metadata only. This is not a conformant define.xml.</Notice>"
        f"<Datasets>{datasets}</Datasets>"
        "</Define>"
    )
    return content.encode()


def _pdf(lines: list[str]) -> bytes:
    wrapped_lines = [
        wrapped
        for line in lines
        for wrapped in (textwrap.wrap(line, width=96, break_on_hyphens=False) or [""])
    ]
    pages = [wrapped_lines[index : index + 46] for index in range(0, len(wrapped_lines), 46)] or [[]]
    object_count = 3 + len(pages) * 2
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            f"<< /Type /Pages /Count {len(pages)} /Kids "
            f"[{' '.join(f'{4 + index * 2} 0 R' for index in range(len(pages)))}] >>"
        ).encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, page_lines in enumerate(pages):
        page_id = 4 + index * 2
        content_id = page_id + 1
        stream = _pdf_stream(page_lines)
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode()
        objects[content_id] = f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id in range(1, object_count + 1):
        offsets.append(len(document))
        document.extend(f"{object_id} 0 obj\n".encode())
        document.extend(objects[object_id])
        document.extend(b"\nendobj\n")
    xref_offset = len(document)
    document.extend(f"xref\n0 {object_count + 1}\n".encode())
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode())
    document.extend(
        f"trailer\n<< /Size {object_count + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(document)


def _pdf_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 9 Tf", "48 752 Td", "13 TL"]
    for line in lines:
        safe = line.encode("latin-1", errors="replace").decode("latin-1")
        safe = safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({safe}) Tj")
        commands.append("T*")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1")
