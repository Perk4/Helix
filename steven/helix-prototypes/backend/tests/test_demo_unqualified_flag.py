"""HELIX_DEMO_UNQUALIFIED_PACKAGES: demo-only handling of the pending 5.2.3 / 5.3 packages.

DEMO ONLY, NOT QUALIFICATION. These tests use the shipped governed tree, where both section
packages are qualification_status "pending". Nothing here writes a status or hash into a
package file; the tests assert the files are byte-identical before and after.
"""

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from test_final_study_approval import clear_blockers, record_fsa, record_roles
from test_section_runs import FakeSectionAgent

from app import run_plans
from app.agents.codex_section_agent import AgentResult
from app.approved_exports import _payload_bytes
from app.config import Settings
from app.database import create_database_engine
from app.demo_mode import DEMO_LABEL, DEMO_UNQUALIFIED_PACKAGE_IDS
from app.main import create_app
from app.models import AuditEventRow, RunEventRow
from app.provenance_compiler import compile_provenance, demo_receipt_backings
from app.repository import StudyPackageRepository
from app.run_events import RunEventStore
from app.run_plans import canonical_hash
from app.schemas import IncludedArtifact, SectionDraftCandidate

ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "STUDY-HLX-028"
BASE = f"/api/v1/studies/{STUDY_ID}"
SECTIONS = ROOT / "skills" / "helix-evidence-pipeline" / "packages" / "sections"
PACKAGE_FILES = sorted(SECTIONS.glob("*/package.json"))
RECEIPT_ID = "EXEC-BW-SUMMARY-001"


def build_client(
    *,
    demo: bool,
    agent: object | None = None,
    root: Path = ROOT,
    database_url: str = "sqlite+pysqlite:///:memory:",
    raise_server_exceptions: bool = True,
) -> tuple[TestClient, object]:
    settings = Settings(
        database_url=database_url,
        seed_path=ROOT / "synthetic-e2e" / "helix-synthetic-bundle.json",
        codex_repository_root=root,
        auto_seed=True,
        run_event_stream_seconds=0,
        demo_unqualified_packages=demo,
    )
    engine = create_database_engine(settings)
    app = create_app(settings, engine, section_agent=agent) if agent else create_app(settings, engine)
    return TestClient(app, raise_server_exceptions=raise_server_exceptions), engine


def package_file_digests() -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in PACKAGE_FILES}


def assert_packages_pending_without_hash() -> None:
    for path in PACKAGE_FILES:
        skill = json.loads(path.read_text())["skill"]
        assert skill["qualification_status"] == "pending", path
        assert "qualification_hash" not in skill, path
        assert "qualification_id" not in skill, path


def export(client: TestClient):
    return client.post(
        f"{BASE}/exports", json={"actor": "Dr. Sam Director", "idempotency_key": "demo-export-v1"}
    )


# --- the flag -----------------------------------------------------------------------------


def test_flag_is_off_by_default_and_read_from_its_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HELIX_DEMO_UNQUALIFIED_PACKAGES", raising=False)
    assert Settings(_env_file=None).demo_unqualified_packages is False
    monkeypatch.setenv("HELIX_DEMO_UNQUALIFIED_PACKAGES", "1")
    assert Settings(_env_file=None).demo_unqualified_packages is True
    assert DEMO_UNQUALIFIED_PACKAGE_IDS == ("section.5_2_3_body_weight", "section.5_3_discussion")


# --- flag off: strict, exactly as before ------------------------------------------------


def test_flag_off_keeps_the_strict_422_for_both_pending_packages() -> None:
    before = package_file_digests()
    client, engine = build_client(demo=False)
    with client:
        frozen = client.post(
            f"{BASE}/pinned-runs", json={"actor": "Dr. Run Owner", "idempotency_key": "demo-off-v1"}
        )
        workspace = client.get(f"{BASE}/workspace").json()
    engine.dispose()
    assert frozen.status_code == 422
    assert frozen.json()["detail"] == [
        {
            "code": "invalid_package_qualification",
            "subject": package_id,
            "message": "Agentic package qualification has not passed",
        }
        for package_id in DEMO_UNQUALIFIED_PACKAGE_IDS
    ]
    assert workspace["pinned_run"] is None
    assert workspace["demo_unqualified_packages"] == []
    assert DEMO_LABEL not in json.dumps(workspace)
    assert package_file_digests() == before
    assert_packages_pending_without_hash()


# --- flag on: demo export ---------------------------------------------------------------


def test_flag_on_exports_with_both_packages_pending_and_labels_ui_payload_and_report() -> None:
    before = package_file_digests()
    client, engine = build_client(demo=True)
    with client:
        before_run = client.get(f"{BASE}/workspace").json()
        clear_blockers(client)
        record_roles(client)
        approved = record_fsa(client, key="demo-fsa-v1")
        assert approved.status_code == 200, approved.text
        exported = export(client)
        assert exported.status_code == 200, exported.text
        artifacts = {
            item["kind"]: client.get(f"{BASE}/exports/{item['artifact_id']}").content
            for item in exported.json()["artifacts"]
        }
        workspace = client.get(f"{BASE}/workspace").json()
    engine.dispose()

    # UI API payload: both sections labelled, before and after the run exists.
    for payload in (before_run, workspace):
        labels = payload["demo_unqualified_packages"]
        assert [item["section_package_id"] for item in labels] == list(DEMO_UNQUALIFIED_PACKAGE_IDS)
        assert {item["label"] for item in labels} == {DEMO_LABEL}
        assert {item["qualification_status"] for item in labels} == {"pending"}
        assert [item["prototype_section_id"] for item in labels] == ["S5", "S8"]
    assert workspace["release_gate"]["status"] == "exported"

    # The freeze event records exactly what was skipped.
    run_requested = workspace["pinned_run"]["event_history"][0]
    assert run_requested["details"]["demo_unqualified_packages"] == ",".join(DEMO_UNQUALIFIED_PACKAGE_IDS)

    # The exported report artifact itself carries the label for both sections.
    report = json.loads(artifacts["pinned_run"])
    notice = report["demo_notice"]
    assert notice["label"] == DEMO_LABEL
    assert [
        (item["section_package_id"], item["label"], item["qualification_status"])
        for item in notice["sections"]
    ] == [(package_id, DEMO_LABEL, "pending") for package_id in DEMO_UNQUALIFIED_PACKAGE_IDS]
    assert [item["title"] for item in notice["sections"]] == [
        "5.2.3 Body Weight",
        "Discussion and conclusion",
    ]
    assert "not qualification" in notice["note"].lower()
    assert report["manifest"]  # the manifest is still exported, unchanged, under the notice

    assert package_file_digests() == before
    assert_packages_pending_without_hash()


def test_flag_on_non_demo_package_still_needs_qualification(tmp_path: Path) -> None:
    """Only 5.2.3 and 5.3 are skipped. A third pending section package still blocks the run."""
    root = tmp_path / "helix"
    for relative in ["skills", ".agents"]:
        shutil.copytree(ROOT / relative, root / relative)
    for relative in [
        "backend/app/validation.py",
        "backend/app/body_weight.py",
        "backend/app/agents/codex_section_agent.py",
    ]:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, root / relative)
    shutil.copytree(ROOT / "backend" / "app" / "data", root / "backend" / "app" / "data")
    other_dir = root / "skills" / "helix-evidence-pipeline" / "packages" / "sections" / "9_9_other_section"
    other_dir.mkdir()
    other = json.loads((SECTIONS / "5_3_discussion" / "package.json").read_text())
    other.update(
        package_id="section.9_9_other_section", section_id="9_9_other_section", title="Other section"
    )
    assert other["skill"]["qualification_status"] == "pending"
    (other_dir / "package.json").write_text(json.dumps(other, indent=2))

    client, engine = build_client(demo=True, root=root)
    with client:
        frozen = client.post(
            f"{BASE}/pinned-runs", json={"actor": "Dr. Run Owner", "idempotency_key": "other-v1"}
        )
    engine.dispose()
    assert frozen.status_code == 422, frozen.text
    subjects = [
        item["subject"] for item in frozen.json()["detail"] if item["code"] == "invalid_package_qualification"
    ]
    assert subjects == ["section.9_9_other_section"]


def test_flag_on_without_the_gate_skip_5_3_would_still_block(monkeypatch: pytest.MonkeyPatch) -> None:
    """Informational (ticket item 6): receipt-backed cells help 5.2.3 only; 5.3 has no executor."""
    monkeypatch.setattr(run_plans, "DEMO_UNQUALIFIED_PACKAGE_IDS", ("section.5_2_3_body_weight",))
    client, engine = build_client(demo=True)
    with client:
        frozen = client.post(
            f"{BASE}/pinned-runs", json={"actor": "Dr. Run Owner", "idempotency_key": "no-53-v1"}
        )
    engine.dispose()
    assert frozen.status_code == 422
    assert [item["subject"] for item in frozen.json()["detail"]] == ["section.5_3_discussion"]
    definition = json.loads((SECTIONS / "5_3_discussion" / "package.json").read_text())
    assert definition.get("executors", []) == []


# --- rule 3 / provenance compiler (option 2 of 47c19c4, 5.2.3 table cells only) ---------


def _receipt(values: dict[str, dict[str, float]]) -> dict[str, object]:
    payload = {"facts": {"unit": "g", "male_means": values}, "provenance": []}
    return {"artifact_id": RECEIPT_ID, "hash": canonical_hash(payload), **payload}


def _candidate(blocks: list[dict[str, object]]) -> SectionDraftCandidate:
    return SectionDraftCandidate.model_validate(
        {
            "schema_version": "helix.section-draft-candidate/v1",
            "status": "section_draft_candidate",
            "candidate_id": "SDC-DEMO000001",
            "run_id": "SRUN-DEMO000001",
            "section_id": "5_2_3_body_weight",
            "section_package_id": "section.5_2_3_body_weight",
            "section_package_version": "0.1.0",
            "drafting_cycle_id": "CYCLE-BW-001",
            "attempt": 1,
            "validated_claim_ids": ["C-BW-HIGH"],
            "content_blocks": blocks,
            "executor_receipt_ids": [RECEIPT_ID],
            "agent_receipt": {
                "runtime": "codex_sdk",
                "thread_id": "thread-test-001",
                "skill_name": "helix-section-agent",
                "skill_hash": "sha256:" + "ab" * 32,
                "skill_references_hash": "sha256:" + "ab" * 32,
            },
        }
    )


def _table(texts: list[str], cited: str = RECEIPT_ID) -> dict[str, object]:
    cells = [{"text": text, "claim_ids": [cited]} for text in texts]
    return {
        "block_id": "BW-T1",
        "kind": "table",
        "content": {"rows": [{"cells": cells}]},
        "factual_spans": [{"text": text, "claim_ids": [cited]} for text in texts],
    }


ENVELOPE = {"executor_receipts": [_receipt({"G1": {"1": 296.5, "28": 310.0}})]}


def test_rule_3_flag_off_rejects_a_receipt_cited_table_cell() -> None:
    receipt = compile_provenance(_candidate([_table(["296.5"])]), {}, candidate_hash="sha256:" + "cd" * 32)
    assert receipt.status == "blocked"
    assert {item.code for item in receipt.blockers} == {"undeclared-claim"}
    assert receipt.bindings == []


def test_rule_3_flag_on_accepts_receipt_for_table_cells_only() -> None:
    backings = demo_receipt_backings(ENVELOPE)
    accepted = compile_provenance(
        _candidate([_table(["296.5", "310", "310.0"])]),
        {},
        candidate_hash="sha256:" + "cd" * 32,
        demo_receipts=backings,
    )
    assert accepted.status == "passed", accepted.blockers
    assert {item.claim_id for item in accepted.bindings} == {RECEIPT_ID}
    assert {item.artifact_hash for item in accepted.bindings} == {ENVELOPE["executor_receipts"][0]["hash"]}

    paragraph = {
        "block_id": "BW-P1",
        "kind": "paragraph",
        "content": "Mean was 296.5 g.",
        "factual_spans": [{"text": "Mean was 296.5 g.", "claim_ids": [RECEIPT_ID]}],
    }
    rejected = compile_provenance(
        _candidate([paragraph]), {}, candidate_hash="sha256:" + "cd" * 32, demo_receipts=backings
    )
    assert rejected.status == "blocked"
    assert {item.code for item in rejected.blockers} == {"undeclared-claim"}

    invented = compile_provenance(
        _candidate([_table(["999.9", "296.5 and 310"])]),
        {},
        candidate_hash="sha256:" + "cd" * 32,
        demo_receipts=backings,
    )
    assert [item.code for item in invented.blockers] == ["unsupported-content"] * 4


def test_rule_3_flag_on_ignores_a_receipt_whose_hash_does_not_match_its_payload() -> None:
    tampered = {"executor_receipts": [{**ENVELOPE["executor_receipts"][0], "hash": "sha256:" + "00" * 32}]}
    assert demo_receipt_backings(tampered) == {}


class ReceiptTableAgent(FakeSectionAgent):
    """Conforming candidate plus a table whose value cells cite the executor receipt."""

    def __init__(self, cited_in: str = "table") -> None:
        super().__init__("conforming")
        self.cited_in = cited_in

    def run(self, *, envelope_id: str, prompt: str, output_schema: dict[str, object]) -> AgentResult:
        result = super().run(envelope_id=envelope_id, prompt=prompt, output_schema=output_schema)
        candidate = json.loads(result.final_response)
        envelope = json.loads(prompt.split(" Envelope: ", 1)[1])
        facts = envelope["executor_receipts"][0]["facts"]
        group = sorted(facts["male_means"])[0]
        values = [f"{value:.1f}" for value in list(facts["male_means"][group].values())[:3]]
        block = _table(values)
        if self.cited_in == "paragraph":
            block = {
                "block_id": "BW-P2",
                "kind": "paragraph",
                "content": values[0],
                "factual_spans": [{"text": values[0], "claim_ids": [RECEIPT_ID]}],
            }
        block["block_id"] = "BW-T2" if self.cited_in == "table" else "BW-P2"
        candidate["content_blocks"].append(block)
        self.demo_prompt = "DEMO MODE, NOT QUALIFIED" in prompt
        return AgentResult(thread_id=result.thread_id, final_response=json.dumps(candidate))


def _draft(client: TestClient, key: str):
    return client.post(
        f"{BASE}/section-runs",
        json={"section_package_id": "section.5_2_3_body_weight", "idempotency_key": key},
    )


def test_rule_3_end_to_end_receipt_cells_need_the_flag(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'helix.db'}"
    # Freeze and validate in demo mode, so a run exists at all on this base.
    agent = ReceiptTableAgent()
    client, engine = build_client(demo=True, agent=agent, database_url=database_url)
    with client:
        assert client.post(f"{BASE}/validation-runs", json={"planner": "fixture"}).status_code == 201
        drafted = _draft(client, "demo-receipt-cells-v1")
        assert drafted.status_code == 201, drafted.text
        assert agent.demo_prompt is True
        evaluation = client.post(
            f"{BASE}/section-runs/{drafted.json()['run_id']}/evaluations",
            json={"idempotency_key": "demo-receipt-eval-v1"},
        )
        assert evaluation.status_code in {200, 201}, evaluation.text
        provenance = evaluation.json()["provenance_receipt"]
    engine.dispose()
    assert provenance["status"] == "passed", provenance["blockers"]
    assert RECEIPT_ID in {item["claim_id"] for item in provenance["bindings"]}
    assert all(
        item["location"].startswith("table:")
        for item in provenance["bindings"]
        if item["claim_id"] == RECEIPT_ID
    )

    # Same database, flag off: the identical receipt-cited table is rejected by rule 3.
    strict_agent = ReceiptTableAgent()
    client, engine = build_client(demo=False, agent=strict_agent, database_url=database_url)
    with client:
        rejected = _draft(client, "strict-receipt-cells-v1")
    engine.dispose()
    assert strict_agent.demo_prompt is False
    assert rejected.status_code == 422
    assert "unapproved claim" in rejected.json()["detail"]


def test_rule_3_flag_on_still_rejects_a_receipt_cited_paragraph() -> None:
    client, engine = build_client(demo=True, agent=ReceiptTableAgent(cited_in="paragraph"))
    with client:
        assert client.post(f"{BASE}/validation-runs", json={"planner": "fixture"}).status_code == 201
        rejected = _draft(client, "demo-receipt-paragraph-v1")
    engine.dispose()
    assert rejected.status_code == 422
    assert "unapproved claim" in rejected.json()["detail"]


def test_flag_on_section_artifacts_of_demo_packages_are_labelled_in_the_export() -> None:
    """A demo-package section candidate is exported wrapped in the label, and its approved hash covers it.

    A drafted-but-unpromoted section blocks Final Study Approval on this base, so this checks
    the live release candidate against the exact bytes export would write for it.
    """
    client, engine = build_client(demo=True, agent=FakeSectionAgent("conforming"))
    with client:
        clear_blockers(client)
        assert _draft(client, "demo-export-draft-v1").status_code == 201
        workspace = client.get(f"{BASE}/workspace").json()
        factory = client.app.state.session_factory
        with factory() as session:
            repository = StudyPackageRepository(session)
            package = repository.get(STUDY_ID)
            runs = repository.list_section_runs(STUDY_ID)
            drafts = repository.list_section_drafts(STUDY_ID)
    engine.dispose()
    included = {item["kind"]: item for item in workspace["release_candidate"]["included_artifacts"]}
    for kind in ("pinned_run", "section_draft_candidate"):
        item = IncludedArtifact.model_validate(included[kind])
        content = _payload_bytes(package, item, section_runs=runs, section_drafts=drafts)
        assert f"sha256:{hashlib.sha256(content).hexdigest()}" == item.content_hash
        body = json.loads(content)
        if kind == "pinned_run":
            assert body["demo_notice"]["label"] == DEMO_LABEL
        else:
            assert body["demo_label"] == DEMO_LABEL
            assert body["section_package_id"] == "section.5_2_3_body_weight"
            assert body["content"]["candidate_id"] == item.artifact_id


# --- verify-claim-coverage.mjs ----------------------------------------------------------


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize(
    ("env", "args", "exit_code", "expected"),
    [
        ({}, [], 1, "FAIL 5_2_3_body_weight"),
        (
            {"HELIX_DEMO_UNQUALIFIED_PACKAGES": "1"},
            [],
            0,
            f"40 cell(s) backed by executor receipt {RECEIPT_ID} [{DEMO_LABEL}]",
        ),
        ({}, ["--demo-unqualified-packages"], 0, f"[{DEMO_LABEL}]"),
    ],
    ids=["off", "on-env", "on-cli"],
)
def test_claim_coverage_counts_receipt_cells_only_in_demo_mode(
    env: dict[str, str], args: list[str], exit_code: int, expected: str
) -> None:
    import os

    base_env = {key: value for key, value in os.environ.items() if key != "HELIX_DEMO_UNQUALIFIED_PACKAGES"}
    result = subprocess.run(
        ["node", str(ROOT / "scripts" / "verify-claim-coverage.mjs"), *args],
        env={**base_env, **env},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == exit_code, result.stdout + result.stderr
    assert expected in result.stdout + result.stderr


# --- run-event feed: a sync failure inside a command ------------------------------------


def test_run_event_sync_failure_rolls_back_the_command_and_returns_a_typed_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = build_client(demo=True, raise_server_exceptions=False)
    with client:
        validation = client.post(f"{BASE}/validation-runs", json={"planner": "fixture"})
        assert validation.status_code == 201
        before = client.get(f"{BASE}/workspace").json()
        factory = client.app.state.session_factory
        with factory() as session:
            audit_before = session.scalar(select(func.count()).select_from(AuditEventRow))
            events_before = session.scalar(select(func.count()).select_from(RunEventRow))

        def broken_sync(self: RunEventStore, journey: object) -> list[dict[str, object]]:
            raise OperationalError("INSERT INTO run_events", {}, Exception("disk I/O error"))

        monkeypatch.setattr(RunEventStore, "sync", broken_sync)
        failed = client.post(
            f"{BASE}/validation-results/VR-004/dispositions",
            json={
                "decision": "corrected",
                "reason": "Synthetic disposition for VR-004.",
                "reviewer": "Dr. Ada Path",
            },
        )
        monkeypatch.undo()
        after = client.get(f"{BASE}/workspace").json()
        with factory() as session:
            audit_after = session.scalar(select(func.count()).select_from(AuditEventRow))
            events_after = session.scalar(select(func.count()).select_from(RunEventRow))
    engine.dispose()

    assert failed.status_code == 503, failed.text
    assert failed.json()["detail"]["code"] == "run_event_sync_failed"
    assert "nothing was saved" in failed.json()["detail"]["message"]
    # No partial write: the disposition, its audit event, and its run events are all absent.
    assert after["dispositions"] == before["dispositions"]
    assert after["release_gate"] == before["release_gate"]
    assert audit_after == audit_before
    assert events_after == events_before
    assert re.fullmatch(r".*VR-004.*", json.dumps(before["release_gate"]["blocking_result_ids"]))
