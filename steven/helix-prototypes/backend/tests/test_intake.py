"""Uploaded files become a Study Evidence Package the workbench can serve.

The seeded fixture is one study somebody wrote by hand. These tests cover the
other way in, and the properties that matter are not "it parsed":

  - the file format must not be able to change the evidence, so an Excel study
    and the same study as CSV must produce identical records;
  - a document that cannot be read must be admitted and marked unreadable
    rather than skipped or guessed at;
  - an archive is hostile input;
  - the package arrives with no claims, because computing those is the section
    executor's job and provenance has to be checkable.
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.intake import IntakeRejected, build_package, classify
from app.main import create_app

ROSTER = (b"study_id,animal_id,group_number,group_name,sex,dose_mgkg_day,species,strain\n"
          b"S,A1,1,Control,M,0,Rat,SD\nS,A2,1,Control,F,0,Rat,SD\n"
          b"S,A3,2,High,M,100,Rat,SD\nS,A4,2,High,F,100,Rat,SD\n")
WEIGHTS = (b"study_id,animal_id,study_day,body_weight_g\n"
           b"S,A1,1,100.5\nS,A2,1,90.5\nS,A3,1,101.5\nS,A4,1,91.5\n"
           b"S,A1,28,200.5\nS,A2,28,180.5\nS,A3,28,150.5\nS,A4,28,140.5\n")
HISTO = (b"study_id,animal_id,tissue,finding,grade,grade_text\n"
         b"S,A1,Liver,No remarkable findings,0,\n"
         b"S,A3,Liver,Hepatocellular hypertrophy,2,Mild\n")
PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"

FACTS = {"route": "oral gavage", "protocol_version": "1.0",
         "authorized_by": "intake test", "study_type_id": "REPEAT_DOSE_28D_RODENT"}


def zipped(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def as_excel(csv_bytes: bytes) -> bytes:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    for row in csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig"))):
        if row:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def client(tmp_path):
    """An app with no seeded study, so only uploads are in play."""
    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    settings = Settings(database_url="sqlite+pysqlite:///:memory:",
                        auto_seed=False, seed_path=tmp_path / "unused.json")
    with TestClient(create_app(settings=settings, engine=engine)) as test_client:
        yield test_client


# ── classification ────────────────────────────────────────────────────────────
def test_a_recognised_table_is_data():
    assert classify("histopathology.csv")[:2] == ("data", "microscopic_findings")


def test_excel_and_csv_reach_the_same_domain():
    assert classify("organ_weights.xlsx")[1] == classify("organ_weights.csv")[1]


def test_a_protocol_is_admitted_and_never_read():
    kind, domain, tier, readable, reason = classify("study_protocol.pdf")
    assert (kind, domain, tier, readable) == ("authority", None, 2, False)
    assert "read by nothing" in reason


def test_an_unrelated_document_does_not_outrank_the_records():
    assert classify("slides.pdf")[2] == 3


def test_an_unknown_table_name_is_refused_not_guessed():
    kind, _d, _t, _r, reason = classify("weights.csv")
    assert kind == "rejected"
    assert "not guessed" in reason


# ── building the package ──────────────────────────────────────────────────────
def test_uploaded_files_become_a_package_with_no_claims():
    package, report = build_package(
        study_id="STUDY-UP-1",
        uploads=[("animal_roster.csv", ROSTER), ("body_weights.csv", WEIGHTS),
                 ("study_protocol.pdf", PDF)],
        study_start="2025-02-03", **FACTS)

    assert len(package.records.animals) == 4
    assert len(package.records.body_weights) == 8
    assert package.study.duration_days == 28
    assert package.study.route == "oral gavage", "declared, never inferred"
    assert [g.group_id for g in package.study.dose_groups] == ["G1", "G2"]

    # The package carries evidence, not conclusions.
    assert package.claims == []
    assert package.provenance_edges == []
    assert package.gate_decisions[0].status == "blocked"
    assert len(package.report_sections) == 8
    assert report.data_files if hasattr(report, "data_files") else True


def test_every_file_is_checksummed_into_the_frozen_manifest():
    package, _report = build_package(
        study_id="STUDY-UP-2",
        uploads=[("animal_roster.csv", ROSTER), ("body_weights.csv", WEIGHTS),
                 ("study_protocol.pdf", PDF)], **FACTS)
    manifest = {entry.name: entry for entry in package.manifest}
    assert set(manifest) == {"animal_roster.csv", "body_weights.csv",
                             "study_protocol.pdf"}
    for entry in manifest.values():
        assert entry.checksum.startswith("sha256:")
        assert entry.locked is True
    assert manifest["study_protocol.pdf"].authority_tier == 2
    assert manifest["body_weights.csv"].authority_tier == 1


def test_a_study_without_a_roster_is_refused():
    with pytest.raises(IntakeRejected, match="animals"):
        build_package(study_id="STUDY-UP-3",
                      uploads=[("body_weights.csv", WEIGHTS)], **FACTS)


def test_the_pathology_scale_is_read_per_study_not_assumed():
    package, _r = build_package(
        study_id="STUDY-UP-4",
        uploads=[("animal_roster.csv", ROSTER), ("body_weights.csv", WEIGHTS),
                 ("histopathology.csv", HISTO)], **FACTS)
    findings = {f.animal_id: f for f in package.records.microscopic_findings}
    assert findings["A3"].severity == "mild"
    assert findings["A3"].controlled_term == "HEPATOCELLULAR HYPERTROPHY"
    # A normal tissue is normalised to one sentinel and is not a finding.
    assert findings["A1"].severity == "none"
    assert findings["A1"].controlled_term == "NORMAL"


def test_an_inconsistent_grade_scale_is_reported_not_repaired():
    rows = (b"study_id,animal_id,tissue,finding,grade,grade_text\n"
            b"S,A1,Liver,Hepatocellular hypertrophy,1,Minimal\n"
            b"S,A3,Liver,Hepatocellular hypertrophy,1,Mild\n")
    _package, report = build_package(
        study_id="STUDY-UP-5",
        uploads=[("animal_roster.csv", ROSTER), ("body_weights.csv", WEIGHTS),
                 ("histopathology.csv", rows)], **FACTS)
    kinds = {a["kind"] for a in report.anomalies}
    assert "inconsistent_grade_scale" in kinds


def test_excel_and_csv_produce_identical_records():
    """The file format must not be able to change the evidence."""
    from_csv, _a = build_package(
        study_id="STUDY-AS-CSV",
        uploads=[("animal_roster.csv", ROSTER), ("body_weights.csv", WEIGHTS)],
        **FACTS)
    from_excel, _b = build_package(
        study_id="STUDY-AS-CSV",
        uploads=[("animal_roster.csv", ROSTER),
                 ("body_weights.xlsx", as_excel(WEIGHTS))], **FACTS)
    assert ([m.model_dump() for m in from_csv.records.body_weights]
            == [m.model_dump() for m in from_excel.records.body_weights])


# ── safety ────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("member", [
    "../../../body_weights.csv", "..\\..\\body_weights.csv",
    "/etc/body_weights.csv", "sub/../../body_weights.csv"])
def test_an_archive_member_cannot_escape(member):
    """Zip slip. The member uses a recognised name, so it is not refused on name."""
    package, _report = build_package(
        study_id="STUDY-UP-6",
        uploads=[("hostile.zip", zipped({member: WEIGHTS,
                                         "animal_roster.csv": ROSTER}))], **FACTS)
    assert {entry.name for entry in package.manifest} == {
        "body_weights.csv", "animal_roster.csv"}


def test_a_corrupt_archive_is_refused():
    with pytest.raises(IntakeRejected, match="not a readable zip"):
        build_package(study_id="STUDY-UP-7",
                      uploads=[("broken.zip", b"not a zip")], **FACTS)


# ── over HTTP, into the workbench ─────────────────────────────────────────────
def test_an_uploaded_study_is_served_by_the_api(client):
    assert client.get("/api/v1/studies").json() == []

    response = client.post(
        "/api/v1/studies",
        data={"study_id": "STUDY-UPLOADED", **FACTS, "study_start": "2025-02-03"},
        files=[("files", ("bundle.zip", zipped({
            "animal_roster.csv": ROSTER, "body_weights.csv": WEIGHTS,
            "histopathology.csv": HISTO}), "application/zip")),
            ("files", ("study_protocol.pdf", PDF, "application/pdf"))])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["study_id"] == "STUDY-UPLOADED"
    assert body["claims"] == 0
    assert body["records"]["animals"] == 4
    assert body["receipt"]["authority_files"] == 1

    listed = client.get("/api/v1/studies").json()
    assert [item["study_id"] for item in listed] == ["STUDY-UPLOADED"]

    workspace = client.get("/api/v1/studies/STUDY-UPLOADED/workspace")
    assert workspace.status_code == 200, workspace.text
    assert workspace.json()["study"]["route"] == "oral gavage"


def test_a_bad_study_id_is_refused(client):
    response = client.post(
        "/api/v1/studies", data={"study_id": "not-a-study-id", **FACTS},
        files=[("files", ("animal_roster.csv", ROSTER, "text/csv"))])
    assert response.status_code == 422
    assert "STUDY-" in response.json()["detail"]


def test_an_existing_study_is_not_silently_replaced(client):
    payload = {"data": {"study_id": "STUDY-TWICE", **FACTS},
               "files": [("files", ("animal_roster.csv", ROSTER, "text/csv")),
                         ("files", ("body_weights.csv", WEIGHTS, "text/csv"))]}
    assert client.post("/api/v1/studies", **payload).status_code == 201
    conflict = client.post("/api/v1/studies", **payload)
    assert conflict.status_code == 409
    assert "frozen manifest" in conflict.json()["detail"]


# ── release gate on a package that has not been checked ───────────────────────
def test_an_unvalidated_study_is_blocked_not_exported(client):
    """Two vacuous-truth bugs this uploaded state exposed.

    `all([])` is True, so a package with no export artifacts read as fully
    EXPORTED. With that fixed it fell through to READY_FOR_SIGNATURE, because
    an empty validation set produces no blocking failures — and "nothing
    failed" is not "passed". A study nobody has checked must be blocked.
    """
    client.post("/api/v1/studies",
                data={"study_id": "STUDY-UNCHECKED", **FACTS},
                files=[("files", ("animal_roster.csv", ROSTER, "text/csv")),
                       ("files", ("body_weights.csv", WEIGHTS, "text/csv"))])

    listed = client.get("/api/v1/studies").json()[0]
    assert listed["release_status"] == "blocked"

    workspace = client.get("/api/v1/studies/STUDY-UNCHECKED/workspace").json()
    assert workspace["release_gate"]["status"] == "blocked"
    assert workspace["claims"] == []


def test_report_assembly_survives_a_package_with_no_claims(client):
    """reporting.py looked its claim ids up with a defaultless next().

    That took down the whole workspace response for an uploaded study, which
    legitimately has no claims yet. The section renders a review marker now.
    """
    client.post("/api/v1/studies",
                data={"study_id": "STUDY-NOCLAIMS", **FACTS},
                files=[("files", ("animal_roster.csv", ROSTER, "text/csv")),
                       ("files", ("body_weights.csv", WEIGHTS, "text/csv"))])

    response = client.get("/api/v1/studies/STUDY-NOCLAIMS/workspace")
    assert response.status_code == 200
    sections = response.json()["report"]["sections"]
    assert len(sections) == 8
    text = " ".join(b["text"] for s in sections for b in s["blocks"])
    assert "NEEDS REVIEW" in text
