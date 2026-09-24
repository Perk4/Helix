from pathlib import Path

from sqlalchemy import func, select

from app.config import Settings
from app.database import create_database_engine, create_schema, create_session_factory
from app.models import AuditEventRow, StudyPackageRow
from app.reporting import load_report_template
from app.seed import seed_database

ROOT = Path(__file__).resolve().parents[2]


def test_seed_is_valid_and_idempotent() -> None:
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        seed_path=ROOT / "synthetic-e2e" / "helix-synthetic-bundle.json",
    )
    engine = create_database_engine(settings)
    create_schema(engine)
    factory = create_session_factory(engine)

    with factory() as session:
        first = seed_database(session, settings)
        second = seed_database(session, settings)
        package_count = session.scalar(select(func.count()).select_from(StudyPackageRow))
        event_count = session.scalar(select(func.count()).select_from(AuditEventRow))

    assert first == second
    assert package_count == 1
    assert event_count == 8
    assert first.label == "SYNTHETIC / NOT FOR SUBMISSION"
    assert sum(len(records) for records in first.records.model_dump().values()) == 1662
    assert len(first.provenance_edges) == 14
    assert len(first.retrieval_index) == 80
    assert {entry.artifact_id for entry in first.retrieval_index}.issubset(
        {entry.artifact_id for entry in first.manifest}
    )
    assert {entry.report_section_id for entry in first.retrieval_index}.issubset(
        {section.section_id for section in first.report_sections}
    )


def test_required_report_fields_have_resolvable_regulatory_references() -> None:
    template = load_report_template()
    reference_ids = {reference.reference_id for reference in template.references}
    required_fields = [field for section in template.sections for field in section.fields if field.required]

    assert len(template.sections) == 8
    assert len(required_fields) == 37
    assert all(field.regulatory_reference_ids for field in required_fields)
    assert all(set(field.regulatory_reference_ids).issubset(reference_ids) for field in required_fields)
    assert all(reference.url.startswith("https://") for reference in template.references)
