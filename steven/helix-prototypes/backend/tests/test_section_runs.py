import json
import re
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.agents.codex_section_agent import AgentResult
from app.config import Settings
from app.database import create_database_engine
from app.main import create_app
from app.models import AuditEventRow, SectionRunRow
from app.repository import StudyPackageRepository

ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "STUDY-HLX-028"
COMMAND = {
    "section_package_id": "section.5_2_3_body_weight",
    "idempotency_key": "workbench-STUDY-HLX-028-body-weight-v1",
}


class FakeSectionAgent:
    def __init__(self, mode: str = "valid"):
        self.mode = mode
        self.calls = 0

    def run(self, *, envelope_id: str, prompt: str, output_schema: dict[str, object]) -> AgentResult:
        self.calls += 1
        if self.mode == "failure":
            raise RuntimeError("SDK unavailable")
        if self.mode == "malformed":
            return AgentResult(thread_id="thread-test-001", final_response="not json")
        candidate_id = re.search(r"candidate_id (SDC-[A-Z0-9-]+)", prompt).group(1)
        run_id = re.search(r"run_id (SRUN-[A-Z0-9-]+)", prompt).group(1)
        skill_hash = re.search(r"skill_hash to (sha256:[a-f0-9]{64})", prompt).group(1)
        claim_ids = ["C-NOT-ALLOWED"] if self.mode == "unapproved" else ["C-BW-HIGH"]
        receipt = {
            "runtime": "codex_sdk",
            "thread_id": "thread-test-001",
            "skill_name": "helix-section-agent",
            "skill_hash": skill_hash,
        }
        if self.mode == "missing_receipt":
            receipt.pop("thread_id")
        candidate = {
            "schema_version": "helix.section-draft-candidate/v1",
            "status": "section_draft_candidate",
            "candidate_id": candidate_id,
            "run_id": run_id,
            "section_id": "5_2_3_body_weight",
            "section_package_id": "section.5_2_3_body_weight",
            "section_package_version": "0.1.0",
            "drafting_cycle_id": "CYCLE-BW-001",
            "attempt": 1,
            "validated_claim_ids": claim_ids,
            "content_blocks": [
                {
                    "block_id": "BW-P1",
                    "kind": "paragraph",
                    "content": "Terminal high-dose body weight was 286.2 g.",
                    "factual_spans": [
                        {"text": "286.2 g", "claim_ids": claim_ids},
                    ],
                }
            ],
            "executor_receipt_ids": ["EXEC-BW-SUMMARY-001"],
            "agent_receipt": receipt,
        }
        return AgentResult(thread_id="thread-test-001", final_response=json.dumps(candidate))


def build_client(agent: FakeSectionAgent, *, raise_server_exceptions: bool = True):
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        seed_path=ROOT / "synthetic-e2e" / "helix-synthetic-bundle.json",
        codex_repository_root=ROOT,
        auto_seed=True,
    )
    engine = create_database_engine(settings)
    client = TestClient(
        create_app(settings, engine, section_agent=agent),
        raise_server_exceptions=raise_server_exceptions,
    )
    return client, engine


def validate(client: TestClient) -> None:
    response = client.post(f"/api/v1/studies/{STUDY_ID}/validation-runs", json={"planner": "fixture"})
    assert response.status_code == 201


def test_section_run_records_candidate_receipt_scaffold_and_exact_replay() -> None:
    agent = FakeSectionAgent()
    client, engine = build_client(agent)
    with client:
        before = client.get(f"/api/v1/studies/{STUDY_ID}/workspace").json()
        assert before["section_run_eligibility"][0]["eligible"] is False
        validate(client)
        eligible = client.get(f"/api/v1/studies/{STUDY_ID}/workspace").json()
        assert eligible["section_run_eligibility"][0] == {
            "section_package_id": "section.5_2_3_body_weight",
            "eligible": True,
            "reasons": [],
        }

        first = client.post(f"/api/v1/studies/{STUDY_ID}/section-runs", json=COMMAND)
        replay = client.post(f"/api/v1/studies/{STUDY_ID}/section-runs", json=COMMAND)
        workspace = client.get(f"/api/v1/studies/{STUDY_ID}/workspace").json()

        assert first.status_code == 201
        assert replay.status_code == 201
        assert replay.json() == first.json()
        assert agent.calls == 1
        receipt = first.json()
        assert receipt["agent_runtime"] == "codex_sdk"
        assert receipt["codex_thread_id"] == "thread-test-001"
        assert receipt["candidate_hash"].startswith("sha256:")
        assert receipt["envelope_hash"].startswith("sha256:")
        assert receipt["skill_hash"].startswith("sha256:")
        assert receipt["review_scaffold_revision"] == 2
        assert len(workspace["section_runs"]) == 1
        stored = workspace["section_runs"][0]
        assert stored["receipt"] == receipt
        assert stored["candidate"]["validated_claim_ids"] == ["C-BW-HIGH"]
        assert "286.2 g" in json.dumps(stored["candidate"])
        assert stored["review_scaffold"]["export_eligible"] is False
        assert workspace["release_gate"]["status"] == "blocked"
        assert all(
            item["candidate"]["status"] == "section_draft_candidate"
            for item in workspace["section_runs"]
        )

        conflict = client.post(
            f"/api/v1/studies/{STUDY_ID}/section-runs",
            json={**COMMAND, "section_package_id": "section.other"},
        )
        assert conflict.status_code == 409

        with client.app.state.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(SectionRunRow)) == 1
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(AuditEventRow)
                    .where(AuditEventRow.event_type == "section_candidate_recorded")
                )
                == 1
            )
    engine.dispose()


def test_unknown_and_ineligible_section_packages_are_rejected_without_starting_codex() -> None:
    agent = FakeSectionAgent()
    client, engine = build_client(agent)
    with client:
        ineligible = client.post(f"/api/v1/studies/{STUDY_ID}/section-runs", json=COMMAND)
        unknown = client.post(
            f"/api/v1/studies/{STUDY_ID}/section-runs",
            json={"section_package_id": "section.other", "idempotency_key": "unknown-package-key"},
        )
        assert ineligible.status_code == 409
        assert unknown.status_code == 404
        assert agent.calls == 0
    engine.dispose()


def test_same_key_with_different_study_command_conflicts() -> None:
    agent = FakeSectionAgent()
    client, engine = build_client(agent)
    with client:
        validate(client)
        assert client.post(f"/api/v1/studies/{STUDY_ID}/section-runs", json=COMMAND).status_code == 201
        response = client.post(
            f"/api/v1/studies/{STUDY_ID}/section-runs",
            json={**COMMAND, "section_package_id": "section.other"},
        )
        assert response.status_code == 409
    engine.dispose()


def test_candidate_and_sdk_failures_leave_no_partial_state() -> None:
    for mode, expected_status in [
        ("malformed", 422),
        ("unapproved", 422),
        ("missing_receipt", 422),
        ("failure", 503),
    ]:
        agent = FakeSectionAgent(mode)
        client, engine = build_client(agent)
        with client:
            validate(client)
            response = client.post(f"/api/v1/studies/{STUDY_ID}/section-runs", json=COMMAND)
            assert response.status_code == expected_status
            with client.app.state.session_factory() as session:
                assert session.scalar(select(func.count()).select_from(SectionRunRow)) == 0
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(AuditEventRow)
                        .where(AuditEventRow.event_type == "section_candidate_recorded")
                    )
                    == 0
                )
        engine.dispose()


def test_transaction_failure_rolls_back_candidate_event_and_revision() -> None:
    agent = FakeSectionAgent()
    client, engine = build_client(agent, raise_server_exceptions=False)
    with client:
        validate(client)
        original_save = StudyPackageRepository.save

        def fail_on_candidate(self, package):
            if any(event.event == "section_candidate_recorded" for event in package.events):
                raise RuntimeError("forced transaction failure")
            return original_save(self, package)

        with patch.object(StudyPackageRepository, "save", fail_on_candidate):
            response = client.post(f"/api/v1/studies/{STUDY_ID}/section-runs", json=COMMAND)
        assert response.status_code == 500
        with client.app.state.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(SectionRunRow)) == 0
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(AuditEventRow)
                    .where(AuditEventRow.event_type == "section_candidate_recorded")
                )
                == 0
            )
    engine.dispose()
