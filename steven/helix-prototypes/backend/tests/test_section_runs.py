import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.agents.codex_section_agent import AgentResult, CodexSectionAgent
from app.config import Settings
from app.database import create_database_engine
from app.main import create_app
from app.models import AuditEventRow, SectionRunRow
from app.repository import StudyPackageRepository
from app.section_runs import SectionRunService

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
        span_claim_ids = ["C-NOT-ALLOWED"] if self.mode == "nested_unapproved" else claim_ids
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
                        {"text": "286.2 g", "claim_ids": span_claim_ids},
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
        body_weight_section = next(
            section
            for section in stored["review_scaffold"]["sections"]
            if section["section_id"] == "5_2_3_body_weight"
        )
        assert body_weight_section["render_state"] == "needs_review"
        assert body_weight_section["placeholder"] == "[NEEDS REVIEW]"
        assert body_weight_section["blocker_result_ids"] == [f"PENDING-{receipt['candidate_id']}"]
        assert workspace["release_gate"]["status"] == "blocked"
        assert all(
            item["candidate"]["status"] == "section_draft_candidate" for item in workspace["section_runs"]
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
        ("nested_unapproved", 422),
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


def test_eligibility_rejects_a_claim_that_does_not_match_the_package_grain(tmp_path: Path) -> None:
    agent = FakeSectionAgent()
    client, engine = build_client(agent)
    package_definition = json.loads(
        (ROOT / "skills/helix-evidence-pipeline/packages/sections/5_2_3_body_weight/package.json").read_text()
    )
    package_definition["required_claims"][0]["grain"] = "dose_group_x_sex"
    package_path = tmp_path / "package.json"
    package_path.write_text(json.dumps(package_definition))

    with client:
        validate(client)
        with client.app.state.session_factory() as session:
            service = SectionRunService(session, agent, ROOT)
            service.package_path = package_path
            eligibility = service.eligibility(StudyPackageRepository(session).get(STUDY_ID))

    assert eligibility.eligible is False
    assert "C-BW-HIGH does not match the Section Package grain" in eligibility.reasons
    engine.dispose()


def test_template_contract_gates_inspect_the_pinned_template(tmp_path: Path) -> None:
    template = json.loads((ROOT / "backend/app/data/report-template.json").read_text())
    section = next(item for item in template["sections"] if item["section_id"] == "S5")
    field = next(item for item in section["fields"] if item["field_id"] == "body-weight")
    field["expected_grain"] = "dose_group"
    template_path = tmp_path / "report-template.json"
    template_path.write_text(json.dumps(template))
    package_definition = json.loads(
        (ROOT / "skills/helix-evidence-pipeline/packages/sections/5_2_3_body_weight/package.json").read_text()
    )
    service = object.__new__(SectionRunService)
    service.template_path = template_path

    failures = service._template_contract_gate_failures(package_definition)

    assert failures == ["Template Contract Gate body-weight-table-shape failed"]


def test_codex_agent_passes_the_candidate_schema_to_the_sdk() -> None:
    calls = []

    class FakeThread:
        id = "thread-schema-001"

        def run(self, prompt, **kwargs):
            calls.append((prompt, kwargs))
            return SimpleNamespace(final_response="{}")

    class FakeCodex:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def thread_start(self, **kwargs):
            return FakeThread()

    schema = {"type": "object", "additionalProperties": False}
    module = SimpleNamespace(
        Codex=FakeCodex,
        Sandbox=SimpleNamespace(read_only="read-only"),
    )
    with patch.dict(sys.modules, {"openai_codex": module}):
        result = CodexSectionAgent(ROOT).run(
            envelope_id="ENV-1",
            prompt="thread={{CODEX_THREAD_ID}}",
            output_schema=schema,
        )

    assert result.thread_id == "thread-schema-001"
    assert calls == [
        (
            "thread=thread-schema-001",
            {"cwd": str(ROOT), "sandbox": "read-only", "output_schema": schema},
        )
    ]
