import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.body_weight import compute_body_weight_summary, load_frozen_fixture, recompute_matches_fixture
from app.config import Settings
from app.database import create_database_engine
from app.main import create_app
from app.models import AuditEventRow, DataValidationRunRow
from app.repository import StudyPackageRepository
from app.seed import load_seed_package

ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "STUDY-HLX-028"
COMMAND = {
    "actor": "HELIX data validation service",
    "idempotency_key": "dvp-study-hlx-028-body-weight-v1",
    "package_id": "validation.body_weight",
}
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "body-weight-summary.json"


def build_client() -> tuple[TestClient, object]:
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        seed_path=ROOT / "synthetic-e2e" / "helix-synthetic-bundle.json",
        auto_seed=True,
        codex_repository_root=ROOT,
    )
    engine = create_database_engine(settings)
    return TestClient(create_app(settings, engine)), engine


def execute(client: TestClient, command: dict[str, str] = COMMAND):
    return client.post(f"/api/v1/studies/{STUDY_ID}/data-validation-packages", json=command)


def test_recomputed_body_weight_matches_frozen_fixture() -> None:
    package = load_seed_package(ROOT / "synthetic-e2e" / "helix-synthetic-bundle.json")
    fixture = load_frozen_fixture()
    computation = compute_body_weight_summary(package)
    matched, evidence = recompute_matches_fixture(computation, fixture)

    assert fixture == json.loads(FIXTURE_PATH.read_text())
    assert matched
    assert evidence == []
    terminal = next(claim for claim in computation.claims if claim.claim_id == "C-BW-HIGH")
    assert terminal.value == 286.2
    assert terminal.unit == "g"
    assert terminal.grain == "dose_group"
    assert terminal.transform_id == "mean-v1"
    assert len(terminal.source_hashes) == 10


def test_one_validation_action_records_pinned_identity_and_exact_replay() -> None:
    client, engine = build_client()
    with client:
        first = execute(client)
        replay = execute(client)
        extra_key = execute(client, {**COMMAND, "idempotency_key": "dvp-study-hlx-028-body-weight-v2"})
        workspace = client.get(f"/api/v1/studies/{STUDY_ID}/workspace").json()
        evidence = client.get(f"/api/v1/studies/{STUDY_ID}/claims/C-BW-HIGH/evidence").json()

        assert first.status_code == 201
        body = first.json()
        replay_body = replay.json()
        assert replay_body["receipt"]["idempotent_replay"] is True
        assert extra_key.json()["receipt"]["idempotent_replay"] is True
        assert replay_body["receipt"]["receipt_id"] == body["receipt"]["receipt_id"]
        assert extra_key.json()["claims"] == body["claims"]
        assert extra_key.json()["results"] == body["results"]
        receipt = body["receipt"]
        assert receipt["package_id"] == "validation.body_weight"
        assert receipt["package_hash"].startswith("sha256:")
        assert receipt["executor_id"] == "body-weight-summary"
        assert receipt["executor_hash"].startswith("sha256:")
        assert receipt["source_artifact_id"] == "A-BW"
        assert receipt["source_hash"].startswith("sha256:")
        assert "validation.body_weight" in receipt["governed_versions"]
        assert receipt["rule_ids"] == [
            "body-weight-required-grain",
            "body-weight-summary-recompute",
            "body-weight-cell-provenance",
        ]
        assert {result["enforcement_class"] for result in body["results"]} == {"hard_blocker"}
        assert {result["status"] for result in body["results"]} == {"pass"}
        assert all(result["waivable"] is False for result in body["results"])
        terminal = next(claim for claim in body["claims"] if claim["claim_id"] == "C-BW-HIGH")
        assert terminal["grain"] == "dose_group"
        assert terminal["unit"] == "g"
        assert terminal["source_hashes"]
        assert terminal["transform_id"] == "mean-v1"
        assert terminal["transform_version"] == "1.0.0"
        assert terminal["rule_versions"]["body-weight-cell-provenance"] == "1.0.0"
        assert len(body["section_references"]) == 2
        assert {item["section_package_id"] for item in body["section_references"]} == {
            "section.5_2_3_body_weight",
            "section.5_3_discussion",
        }
        assert {item["claim_id"] for item in body["section_references"]} == {"C-BW-HIGH"}
        assert workspace["data_validation_executions"][0]["receipt"]["receipt_id"] == receipt["receipt_id"]
        assert evidence["claim"]["value"] == 286.2
        assert evidence["exact_match"] is True
        assert evidence["source_hashes"]
        assert evidence["lineage"]
        assert evidence["rule_versions"]["body-weight-summary-recompute"] == "1.0.0"

        with client.app.state.session_factory() as session:
            executions = session.scalars(select(DataValidationRunRow)).all()
            assert {row.execution["receipt"]["receipt_id"] for row in executions} == {receipt["receipt_id"]}
            stored = StudyPackageRepository(session).get(STUDY_ID)
            assert len(stored.data_validation_executions) == 1
            assert len(stored.data_validation_executions[0].claims) == len(body["claims"])
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(AuditEventRow)
                    .where(AuditEventRow.event_type == "data_validation_completed")
                )
                == 1
            )
            claim_ids = [claim.claim_id for claim in stored.claims if claim.claim_id == "C-BW-HIGH"]
            assert claim_ids == ["C-BW-HIGH"]
    engine.dispose()


def test_two_sections_reuse_the_stored_claim_without_rerunning() -> None:
    client, engine = build_client()
    with client:
        first = execute(client).json()
        replay = execute(client).json()
        references = first["section_references"]
        assert len(references) == 2
        assert references[0]["claim_id"] == references[1]["claim_id"] == "C-BW-HIGH"
        assert references[0]["executor_receipt_id"] == references[1]["executor_receipt_id"]
        assert replay["receipt"]["receipt_id"] == first["receipt"]["receipt_id"]
        assert [item["section_id"] for item in references] == ["S5", "S8"]
    engine.dispose()


def test_missing_grain_creates_non_waivable_hard_blocker() -> None:
    client, engine = build_client()
    with client:
        with client.app.state.session_factory() as session:
            repository = StudyPackageRepository(session)
            package = repository.get(STUDY_ID)
            records = package.records.model_copy(
                update={
                    "body_weights": [
                        item.model_copy(update={"grain": ""}) for item in package.records.body_weights
                    ]
                }
            )
            repository.save(package.model_copy(update={"records": records}))
            session.commit()

        response = execute(client)
        assert response.status_code == 201
        body = response.json()
        grain = next(
            result for result in body["results"] if result["rule_id"] == "body-weight-required-grain"
        )
        assert grain["status"] == "fail"
        assert grain["enforcement_class"] == "hard_blocker"
        assert grain["waivable"] is False
        assert body["receipt"]["status"] == "blocked"
        assert body["claims"] == []
        waiver = client.post(
            f"/api/v1/studies/{STUDY_ID}/validation-results/VR-BW-GRAIN/dispositions",
            json={
                "decision": "approved_exception",
                "reason": "A missing grain must not be waivable in this slice.",
                "reviewer": "Dr. Ada Path",
            },
        )
        assert waiver.status_code == 409
        assert waiver.json()["detail"] == "hard_blocker results cannot be waived"
        workspace = client.get(f"/api/v1/studies/{STUDY_ID}/workspace").json()
        assert "VR-BW-GRAIN" in workspace["release_gate"]["blocking_result_ids"]
        assert any(result["result_id"] == "VR-BW-GRAIN" for result in workspace["validations"])
    engine.dispose()


def test_missing_provenance_edge_creates_non_waivable_hard_blocker() -> None:
    client, engine = build_client()
    with client:
        with client.app.state.session_factory() as session:
            repository = StudyPackageRepository(session)
            package = repository.get(STUDY_ID)
            records = package.records.model_copy(
                update={
                    "body_weights": [
                        item.model_copy(update={"source_pointer": ""})
                        for item in package.records.body_weights
                    ]
                }
            )
            repository.save(package.model_copy(update={"records": records}))
            session.commit()

        response = execute(client)
        assert response.status_code == 201
        body = response.json()
        provenance = next(
            result for result in body["results"] if result["rule_id"] == "body-weight-cell-provenance"
        )
        assert provenance["status"] == "fail"
        assert provenance["enforcement_class"] == "hard_blocker"
        assert provenance["waivable"] is False
        waiver = client.post(
            f"/api/v1/studies/{STUDY_ID}/validation-results/VR-BW-PROVENANCE/dispositions",
            json={
                "decision": "explained_in_nsdrg",
                "reason": "A missing provenance edge must not be waivable.",
                "reviewer": "Dr. Ada Path",
            },
        )
        assert waiver.status_code == 409
        workspace = client.get(f"/api/v1/studies/{STUDY_ID}/workspace").json()
        assert "VR-BW-PROVENANCE" in workspace["release_gate"]["blocking_result_ids"]
    engine.dispose()


def test_unknown_package_is_not_executed() -> None:
    client, engine = build_client()
    with client:
        response = execute(client, {**COMMAND, "package_id": "validation.unknown"})
        assert response.status_code == 404
    engine.dispose()
