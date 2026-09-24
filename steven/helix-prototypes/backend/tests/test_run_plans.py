import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import Settings
from app.database import create_database_engine
from app.main import create_app
from app.models import AuditEventRow, PinnedRunRow
from app.repository import StudyPackageRepository

ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "STUDY-HLX-028"
COMMAND = {"actor": "Dr. Run Owner", "idempotency_key": "freeze-study-hlx-028-v1"}


def governed_root(tmp_path: Path) -> Path:
    root = tmp_path / "helix"
    for relative in ["skills", ".agents"]:
        shutil.copytree(ROOT / relative, root / relative)
    (root / "backend" / "app" / "agents").mkdir(parents=True)
    for filename in ["validation.py", "agents/codex_section_agent.py"]:
        source = ROOT / "backend" / "app" / filename
        target = root / "backend" / "app" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copytree(ROOT / "backend" / "app" / "data", root / "backend" / "app" / "data")
    return root


def build_client(repository_root: Path = ROOT) -> tuple[TestClient, object]:
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        seed_path=ROOT / "synthetic-e2e" / "helix-synthetic-bundle.json",
        codex_repository_root=repository_root,
        auto_seed=True,
    )
    engine = create_database_engine(settings)
    return TestClient(create_app(settings, engine)), engine


def freeze(client: TestClient, command: dict[str, str] = COMMAND):
    return client.post(f"/api/v1/studies/{STUDY_ID}/pinned-runs", json=command)


def test_freeze_persists_complete_plan_and_exact_replay() -> None:
    client, engine = build_client()
    with client:
        first = freeze(client)
        replay = freeze(client)
        replay_with_new_key = freeze(
            client,
            {**COMMAND, "idempotency_key": "freeze-study-hlx-028-v2"},
        )
        workspace = client.get(f"/api/v1/studies/{STUDY_ID}/workspace")

        assert first.status_code == 201
        assert replay.json() == first.json()
        assert replay_with_new_key.json() == first.json()
        pinned = first.json()
        assert pinned["status"] == "planned"
        assert pinned["manifest_hash"].startswith("sha256:")
        assert pinned["study_type_resolution"]["study_type_id"] == "REPEAT_DOSE_28D_RODENT"
        assert pinned["run_plan"]["fingerprint"].startswith("sha256:")
        assert workspace.json()["pinned_run"] == pinned
        kinds = {item["kind"] for item in pinned["governed_inputs"]}
        assert {
            "schema",
            "ontology",
            "ontology_schema",
            "data_validation_package",
            "section_package",
            "rule_bundle",
            "template",
            "skill",
            "suite",
            "executor",
            "tool",
        }.issubset(kinds)
        node_ids = {item["node_id"] for item in pinned["run_plan"]["nodes"]}
        assert {
            "parse.body_weights",
            "study_type.resolve",
            "validation.body_weight",
            "template_contract.section.5_2_3_body_weight",
            "section.5_2_3_body_weight",
            "provenance.section.5_2_3_body_weight",
            "review_scaffold.materialize",
        }.issubset(node_ids)
        assert len(pinned["event_history"]) == 1
        assert pinned["event_history"][0]["event"] == "run_requested"

        with client.app.state.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(PinnedRunRow)) == 2
            stored = StudyPackageRepository(session).get(STUDY_ID).pinned_run
            assert stored is not None
            assert stored.model_dump(mode="json") == pinned
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(AuditEventRow)
                    .where(AuditEventRow.event_type == "run_requested")
                )
                == 1
            )
    engine.dispose()


def test_conflicting_idempotency_key_returns_409() -> None:
    client, engine = build_client()
    with client:
        assert freeze(client).status_code == 201
        conflict = freeze(client, {**COMMAND, "actor": "Another Owner"})
        assert conflict.status_code == 409

        with client.app.state.session_factory() as session:
            repository = StudyPackageRepository(session)
            package = repository.get(STUDY_ID)
            manifest = [item.model_copy() for item in package.manifest]
            manifest[0] = manifest[0].model_copy(update={"checksum": "sha256:" + "0" * 64})
            repository.save(package.model_copy(update={"manifest": manifest}))
            session.commit()
        changed_manifest = freeze(client)
        assert changed_manifest.status_code == 409
    engine.dispose()


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("unlocked", "manifest_unlocked"),
        ("unauthorized", "manifest_unauthorized"),
        ("checksum", "manifest_checksum_mismatch"),
    ],
)
def test_manifest_failures_reject_before_run_creation(mutation: str, code: str) -> None:
    client, engine = build_client()
    with client:
        with client.app.state.session_factory() as session:
            repository = StudyPackageRepository(session)
            package = repository.get(STUDY_ID)
            manifest = [item.model_copy() for item in package.manifest]
            if mutation == "unlocked":
                manifest[0] = manifest[0].model_copy(update={"locked": False})
            elif mutation == "unauthorized":
                manifest[0] = manifest[0].model_copy(update={"authorized_by": ""})
            else:
                manifest[0] = manifest[0].model_copy(update={"checksum": "sha256:" + "0" * 64})
            repository.save(package.model_copy(update={"manifest": manifest}))
            session.commit()

        response = freeze(client)
        assert response.status_code == 422
        assert code in {item["code"] for item in response.json()["detail"]}
        with client.app.state.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(PinnedRunRow)) == 0
    engine.dispose()


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("duplicate", "duplicate_node_id"),
        ("missing", "missing_dependency"),
        ("cycle", "dependency_cycle"),
        ("schema", "invalid_package_schema"),
        ("qualification", "invalid_package_qualification"),
    ],
)
def test_invalid_packages_return_structured_evidence(tmp_path: Path, mutation: str, code: str) -> None:
    root = governed_root(tmp_path)
    validation_path = (
        root
        / "skills"
        / "helix-evidence-pipeline"
        / "packages"
        / "data-validation"
        / "body-weight"
        / "package.json"
    )
    section_path = (
        root
        / "skills"
        / "helix-evidence-pipeline"
        / "packages"
        / "sections"
        / "5_2_3_body_weight"
        / "package.json"
    )
    validation = json.loads(validation_path.read_text())
    section = json.loads(section_path.read_text())
    if mutation == "duplicate":
        duplicate = validation_path.parent.parent / "duplicate" / "package.json"
        duplicate.parent.mkdir()
        duplicate.write_text(json.dumps(validation))
    elif mutation == "missing":
        validation["depends_on"].append("parse.missing")
        validation_path.write_text(json.dumps(validation))
    elif mutation == "cycle":
        validation["depends_on"].append(section["package_id"])
        validation_path.write_text(json.dumps(validation))
    elif mutation == "schema":
        validation.pop("rules")
        validation_path.write_text(json.dumps(validation))
    else:
        section["skill"]["qualification_status"] = "failed"
        section_path.write_text(json.dumps(section))

    client, engine = build_client(root)
    with client:
        response = freeze(client)
        assert response.status_code == 422
        assert code in {item["code"] for item in response.json()["detail"]}
    engine.dispose()


@pytest.mark.parametrize(
    ("mapping_mode", "code"), [("unknown", "unknown_study_type"), ("ambiguous", "ambiguous_study_type")]
)
def test_unresolved_study_type_blocks_dependents_without_fallback(
    tmp_path: Path, mapping_mode: str, code: str
) -> None:
    root = governed_root(tmp_path)
    mapping_path = root / "backend" / "app" / "data" / "study-type-mapping.json"
    mapping = json.loads(mapping_path.read_text())
    if mapping_mode == "unknown":
        mapping["mappings"] = []
    else:
        duplicate = {**mapping["mappings"][0], "study_type_id": "ANOTHER_MATCH"}
        mapping["mappings"].append(duplicate)
    mapping_path.write_text(json.dumps(mapping))

    client, engine = build_client(root)
    with client:
        response = freeze(client)
        assert response.status_code == 201
        pinned = response.json()
        assert pinned["status"] == "needs_review"
        assert pinned["study_type_resolution"]["study_type_id"] is None
        evidence = pinned["study_type_resolution"]["evidence"][0]
        assert evidence["code"] == code
        assert "[NEEDS REVIEW]" in evidence["message"]
        resolution = next(
            node for node in pinned["run_plan"]["nodes"] if node["node_id"] == "study_type.resolve"
        )
        validation = next(
            node for node in pinned["run_plan"]["nodes"] if node["node_id"] == "validation.body_weight"
        )
        assert resolution["status"] == "blocked"
        assert validation["status"] == "blocked"
    engine.dispose()


def test_governed_input_change_changes_plan_and_node_fingerprints(tmp_path: Path) -> None:
    baseline_client, baseline_engine = build_client()
    with baseline_client:
        baseline = freeze(baseline_client).json()
    baseline_engine.dispose()

    root = governed_root(tmp_path)
    skill = root / ".agents" / "skills" / "helix-section-agent" / "SKILL.md"
    skill.write_text(skill.read_text() + "\nGoverned fingerprint test.\n")
    changed_client, changed_engine = build_client(root)
    with changed_client:
        changed = freeze(changed_client).json()
    changed_engine.dispose()

    assert changed["run_plan"]["fingerprint"] != baseline["run_plan"]["fingerprint"]
    baseline_nodes = {item["node_id"]: item["input_fingerprint"] for item in baseline["run_plan"]["nodes"]}
    changed_nodes = {item["node_id"]: item["input_fingerprint"] for item in changed["run_plan"]["nodes"]}
    assert changed_nodes.keys() == baseline_nodes.keys()
    assert all(changed_nodes[node_id] != baseline_nodes[node_id] for node_id in baseline_nodes)
