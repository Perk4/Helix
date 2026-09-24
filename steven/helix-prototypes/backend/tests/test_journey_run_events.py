"""Nine-stage journey projection and run events (Steven-Espaillat/Helix#25).

Qualification boundary: shipped section packages are deliberately `pending`, so a real
freeze returns 422 on this base. Tests that need a Pinned Run use a *test-local* copy
of the governed tree under tmp_path whose section packages are marked qualified with a
hash of their own suite file. Shipped package data is never modified; the fixture only
exercises the journey/event contract and makes no qualification claim.
"""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import create_database_engine
from app.main import create_app
from app.models import RunEventRow
from app.run_events import RUN_EVENT_ADAPTER, RunEventStore
from app.run_plans import file_hash

ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "STUDY-HLX-028"
LABEL = "SYNTHETIC / NOT FOR SUBMISSION"
STAGE_IDS = [
    "upload",
    "parse",
    "resolve",
    "extract",
    "validate",
    "draft",
    "provenance",
    "traceability",
    "review-export",
]
FREEZE = {"actor": "Dr. Run Owner", "idempotency_key": "journey-freeze-v1"}
BASE = f"/api/v1/studies/{STUDY_ID}"


def qualified_fixture_root(tmp_path: Path, status: str = "passed") -> Path:
    """Copy the governed tree and set section-package qualification in the copy only."""
    root = tmp_path / "helix"
    for relative in ["skills", ".agents"]:
        shutil.copytree(ROOT / relative, root / relative)
    for filename in ["validation.py", "body_weight.py", "agents/codex_section_agent.py"]:
        target = root / "backend" / "app" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "backend" / "app" / filename, target)
    shutil.copytree(ROOT / "backend" / "app" / "data", root / "backend" / "app" / "data")
    sections = root / "skills" / "helix-evidence-pipeline" / "packages" / "sections"
    for path in sorted(sections.glob("*/package.json")):
        definition = json.loads(path.read_text())
        skill = definition.get("skill") or definition.get("agentic_skill")
        if skill is None:
            continue
        skill["qualification_status"] = status
        if status == "passed":
            skill["qualification_hash"] = file_hash(root / skill["promptfoo_suite"]["path"])
        else:
            skill.pop("qualification_hash", None)
        path.write_text(json.dumps(definition, indent=2))
    return root


def build_client(repository_root: Path = ROOT, **overrides: object) -> tuple[TestClient, object]:
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        seed_path=ROOT / "synthetic-e2e" / "helix-synthetic-bundle.json",
        codex_repository_root=repository_root,
        auto_seed=True,
        run_event_stream_seconds=0,
        **overrides,
    )
    engine = create_database_engine(settings)
    return TestClient(create_app(settings, engine)), engine


def journey(client: TestClient) -> dict:
    response = client.get(f"{BASE}/workspace")
    assert response.status_code == 200, response.text
    return response.json()["journey"]


def statuses(value: dict) -> dict[str, str]:
    return {stage["stage_id"]: stage["status"] for stage in value["stages"]}


def stage(value: dict, stage_id: str) -> dict:
    return next(item for item in value["stages"] if item["stage_id"] == stage_id)


def parse_frames(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line and line[0] != ":")
        if "data" in lines:
            event = json.loads(lines["data"])
            assert lines["id"] == event["event_id"]
            assert lines["event"] == event["type"]
            events.append(event)
    return events


def stream(client: TestClient, run_id: str, cursor: str | None = None):
    headers = {"Last-Event-ID": cursor} if cursor else {}
    return client.get(f"{BASE}/pinned-runs/{run_id}/events", headers=headers)


def test_seeded_study_projects_upload_current_while_legacy_array_says_gate() -> None:
    client, engine = build_client()
    with client:
        workspace = client.get(f"{BASE}/workspace").json()
    projection = workspace["journey"]
    legacy_current = next(item for item in workspace["stages"] if item["status"] == "current")
    assert legacy_current["stage_id"] == "gate"
    assert workspace["pinned_run"] is None
    assert projection["label"] == LABEL
    assert projection["run"] is None
    assert projection["current_stage_id"] == "upload"
    assert [item["stage_id"] for item in projection["stages"]] == STAGE_IDS
    assert statuses(projection) == {sid: ("current" if sid == "upload" else "pending") for sid in STAGE_IDS}
    gate_numbers = [item["gate_number"] for item in projection["stages"]]
    assert gate_numbers == [1, None, None, None, None, None, None, 2, 3]
    assert [item["kind"] for item in projection["stages"]] == [
        "human_gate",
        *["agent_step"] * 6,
        "human_gate",
        "human_gate",
    ]
    assert [item["selectable"] for item in projection["stages"]] == [True] + [False] * 8
    upload = stage(projection, "upload")
    freeze_action = upload["actions"][-1]
    assert freeze_action["action_id"] == "manifest:freeze"
    assert freeze_action["status"] == "pending"
    assert freeze_action["command"] == f"POST {BASE}/pinned-runs"
    for item in projection["stages"]:
        assert item["short_label"] and item["name"] and item["summary"] and item["control_boundary"]
        assert item["input"]["title"] and item["output"]["title"]
    engine.dispose()


def test_qualification_gate_keeps_upload_current_and_writes_no_run_events(tmp_path: Path) -> None:
    client, engine = build_client(qualified_fixture_root(tmp_path, status="pending"))
    with client:
        before = journey(client)
        rejected = client.post(f"{BASE}/pinned-runs", json=FREEZE)
        after = journey(client)
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(RunEventRow)) == 0
    assert rejected.status_code == 422
    assert "invalid_package_qualification" in {item["code"] for item in rejected.json()["detail"]}
    assert after == before
    engine.dispose()


def test_every_projected_status_from_intake_to_export_with_gate_stops(tmp_path: Path) -> None:
    client, engine = build_client(qualified_fixture_root(tmp_path))
    seen: set[str] = set()
    with client:
        intake = journey(client)
        seen.update(statuses(intake).values())

        frozen = client.post(f"{BASE}/pinned-runs", json=FREEZE)
        assert frozen.status_code == 201, frozen.text
        run_id = frozen.json()["run_id"]
        after_freeze = journey(client)
        seen.update(statuses(after_freeze).values())
        assert after_freeze["run"]["run_id"] == run_id
        assert after_freeze["run"]["events_url"] == f"{BASE}/pinned-runs/{run_id}/events"
        assert statuses(after_freeze) == {
            "upload": "complete",
            "parse": "complete",
            "resolve": "complete",
            "extract": "complete",
            "validate": "current",
            "draft": "pending",
            "provenance": "pending",
            "traceability": "pending",
            "review-export": "pending",
        }

        validation = client.post(f"{BASE}/validation-runs", json={"planner": "fixture"})
        assert validation.status_code == 201, validation.text
        at_gate = journey(client)
        seen.update(statuses(at_gate).values())
        # Agent-owned steps stop at the Traceability gate; Review and export is not exposed.
        assert at_gate["current_stage_id"] == "traceability"
        assert statuses(at_gate)["provenance"] == "complete"
        assert statuses(at_gate)["traceability"] == "blocked"
        assert statuses(at_gate)["review-export"] == "pending"
        assert stage(at_gate, "review-export")["selectable"] is False
        validate_outcomes = {item["outcome"] for item in stage(at_gate, "validate")["actions"]}
        assert {"passed", "blocker"} <= validate_outcomes

        # A second agent run never passes the human gate.
        rerun = client.post(f"{BASE}/validation-runs", json={"planner": "fixture"})
        assert rerun.status_code == 201
        assert statuses(journey(client))["traceability"] == "blocked"

        premature = client.post(
            f"{BASE}/approvals",
            json={"role": "pathologist", "reviewer": "Dr. Ada Path", "meaning": "Scientific review"},
        )
        assert premature.status_code == 409

        blockers = [
            item["action_id"].removeprefix("disposition:")
            for item in stage(journey(client), "traceability")["actions"]
            if item["outcome"] == "blocker"
        ]
        assert blockers
        for result_id in blockers:
            response = client.post(
                f"{BASE}/validation-results/{result_id}/dispositions",
                json={
                    "decision": "approved_exception" if result_id == "VR-006" else "corrected",
                    "reason": f"Synthetic disposition for {result_id}.",
                    "reviewer": "Dr. Ada Path",
                },
            )
            assert response.status_code == 200, response.text
            assert response.json()["journey"]["run"]["latest_event_id"] is not None
        after_dispositions = journey(client)
        seen.update(statuses(after_dispositions).values())
        trace = stage(after_dispositions, "traceability")
        assert trace["status"] == "complete"
        # Dispositions remain distinguishable from passes.
        assert {item["outcome"] for item in trace["actions"]} == {"dispositioned"}
        assert all(item["status"] == "done" for item in trace["actions"])
        assert statuses(after_dispositions)["review-export"] == "current"
        assert stage(after_dispositions, "review-export")["selectable"] is True

        roles = [
            ("pathologist", "Dr. Ada Path", "Scientific review complete"),
            ("peer_reviewer", "Dr. Priya Peer", "Independent pathology review complete"),
            ("qau", "Morgan QA", "Quality assurance statement recorded"),
            ("study_director", "Dr. Sam Director", "Final report approval"),
        ]
        for role, reviewer, meaning in roles:
            approved = client.post(
                f"{BASE}/approvals", json={"role": role, "reviewer": reviewer, "meaning": meaning}
            )
            assert approved.status_code == 200, approved.text
        signed = client.post(
            f"{BASE}/final-study-approvals",
            json={"reviewer": "Dr. Sam Director", "idempotency_key": "journey-fsa-v1"},
        )
        assert signed.status_code == 200, signed.text
        ready = journey(client)
        final = stage(ready, "review-export")
        # Approvals make the final gate ready; they never export.
        assert final["status"] == "current"
        assert final["gate_status"] == "ready_for_export"
        assert {item["action_id"]: item["status"] for item in final["actions"]}["export"] == "pending"
        commands = {item["action_id"]: item["command"] for item in final["actions"]}
        assert commands["approval:pathologist"] == f"POST {BASE}/approvals"
        assert commands["final-study-approval"] == f"POST {BASE}/final-study-approvals"
        assert commands["export"] == f"POST {BASE}/exports"
        events_before_export = parse_frames(stream(client, run_id).text)
        assert "export_finished" not in {item["type"] for item in events_before_export}

        exported = client.post(
            f"{BASE}/exports", json={"actor": "Dr. Sam Director", "idempotency_key": "journey-export-v1"}
        )
        assert exported.status_code == 200, exported.text
        done = journey(client)
        seen.update(statuses(done).values())
        assert done["current_stage_id"] is None
        assert set(statuses(done).values()) == {"complete"}
        replay_export = client.post(
            f"{BASE}/exports", json={"actor": "Dr. Sam Director", "idempotency_key": "journey-export-v1"}
        )
        assert replay_export.status_code == 200

        # Reload restores the same projection without client memory.
        assert journey(client) == done

        events = parse_frames(stream(client, run_id).text)
    engine.dispose()

    assert {"complete", "current", "blocked", "pending"} <= seen
    assert [item["sequence"] for item in events] == list(range(1, len(events) + 1))
    assert len({item["event_id"] for item in events}) == len(events)
    assert all(item["label"] == LABEL and item["run_id"] == run_id for item in events)
    types = [item["type"] for item in events]
    gates = [(item["stage_id"], item["gate_number"]) for item in events if item["type"] == "gate_reached"]
    assert gates == [("traceability", 2), ("review-export", 3)]
    assert types.count("export_finished") == 1
    assert types[-2:] == ["stage_finished", "export_finished"]
    export_event = events[-1]
    assert export_event["artifact_count"] > 0
    finished = [item["stage_id"] for item in events if item["type"] == "stage_finished"]
    assert finished == STAGE_IDS
    started = [item["stage_id"] for item in events if item["type"] == "stage_started"]
    assert started == ["parse", "resolve", "extract", "validate", "draft", "provenance"]
    failed = [item for item in events if item["type"] == "command_failed"]
    assert [(item["command"], item["stage_id"]) for item in failed] == [("record_approval", "review-export")]
    flagged = [item for item in events if item["type"] == "action_finished" and item["flag"] == "blocker"]
    assert flagged
    dispositioned = [
        item for item in events if item["type"] == "action_finished" and item["outcome"] == "dispositioned"
    ]
    assert dispositioned and all(item["flag"] is None for item in dispositioned)
    # The traceability gate is reached before any disposition completes it.
    first_gate = types.index("gate_reached")
    assert first_gate < events.index(dispositioned[0])
    # Approvals never produce stage completion; only the export does.
    review_finish = next(
        index
        for index, item in enumerate(events)
        if item["type"] == "stage_finished" and item["stage_id"] == "review-export"
    )
    export_action = next(
        index
        for index, item in enumerate(events)
        if item["type"] == "action_finished" and item["action_id"] == "export"
    )
    assert export_action < review_finish


def test_last_event_id_replays_only_missed_events_and_expired_cursor_is_typed(tmp_path: Path) -> None:
    client, engine = build_client(qualified_fixture_root(tmp_path), run_event_retention=5)
    with client:
        run_id = client.post(f"{BASE}/pinned-runs", json=FREEZE).json()["run_id"]
        current = journey(client)["run"]
        latest_id = current["latest_event_id"]
        latest_sequence = current["latest_sequence"]
        assert latest_sequence > 5

        retained = parse_frames(stream(client, run_id).text)
        assert [item["sequence"] for item in retained] == list(
            range(latest_sequence - 4, latest_sequence + 1)
        )
        cursor = retained[1]["event_id"]
        missed = parse_frames(stream(client, run_id, cursor).text)
        assert [item["event_id"] for item in missed] == [item["event_id"] for item in retained[2:]]
        by_query = client.get(f"{BASE}/pinned-runs/{run_id}/events", params={"last_event_id": cursor})
        assert parse_frames(by_query.text) == missed
        assert parse_frames(stream(client, run_id, latest_id).text) == []

        expired = stream(client, run_id, f"{run_id}.E000001")
        assert expired.status_code == 409
        body = expired.json()
        assert body == {
            "label": LABEL,
            "code": "event_cursor_expired",
            "detail": body["detail"],
            "run_id": run_id,
            "run_version": current["run_version"],
            "latest_event_id": latest_id,
        }
        foreign = stream(client, run_id, "RUN-OTHER.E000001")
        assert foreign.status_code == 400
        assert foreign.json()["code"] == "invalid_event_cursor"
        unknown = stream(client, "RUN-UNKNOWN")
        assert unknown.status_code == 404
        assert stream(client, run_id).headers["content-type"].startswith("text/event-stream")
    engine.dispose()


def test_pause_and_resume_fixtures_serialize_replay_and_project(tmp_path: Path) -> None:
    """#26 owns pause/resume commands; these are test-local fixture events."""
    client, engine = build_client(qualified_fixture_root(tmp_path))
    with client:
        run_id = client.post(f"{BASE}/pinned-runs", json=FREEZE).json()["run_id"]
        cursor = journey(client)["run"]["latest_event_id"]
        with Session(engine) as session:
            RunEventStore(session).append(
                run_id=run_id,
                study_id=STUDY_ID,
                label=LABEL,
                event_type="run_paused",
                stage_id="validate",
                payload={"reason": "fixture pause"},
            )
            session.commit()
        paused = journey(client)
        assert stage(paused, "validate")["status"] == "paused"
        assert paused["latest_event"]["type"] == "run_paused"
        replayed = parse_frames(stream(client, run_id, cursor).text)
        assert [item["type"] for item in replayed] == ["run_paused"]
        assert replayed[0]["reason"] == "fixture pause"

        with Session(engine) as session:
            RunEventStore(session).append(
                run_id=run_id,
                study_id=STUDY_ID,
                label=LABEL,
                event_type="run_resumed",
                stage_id="validate",
            )
            session.commit()
        resumed = journey(client)
        assert stage(resumed, "validate")["status"] == "current"
        assert [item["type"] for item in parse_frames(stream(client, run_id, cursor).text)] == [
            "run_paused",
            "run_resumed",
        ]
    engine.dispose()


@pytest.mark.parametrize(
    ("event_type", "extra"),
    [
        ("stage_started", {}),
        ("stage_finished", {}),
        ("action_started", {"action_id": "a", "action_label": "A"}),
        ("action_finished", {"action_id": "a", "action_label": "A", "outcome": "blocker", "flag": "blocker"}),
        ("run_paused", {"reason": None}),
        ("run_resumed", {}),
        ("gate_reached", {"gate_number": 2}),
        ("command_failed", {"command": "export", "detail": "not ready"}),
        ("export_finished", {"artifact_count": 3}),
    ],
)
def test_every_run_event_type_round_trips(event_type: str, extra: dict) -> None:
    event = {
        "label": LABEL,
        "event_id": "RUN-ABC.E000001",
        "run_id": "RUN-ABC",
        "study_id": STUDY_ID,
        "sequence": 1,
        "stage_id": "traceability",
        "occurred_at": "2026-09-24T12:00:00Z",
        "type": event_type,
        **extra,
    }
    parsed = RUN_EVENT_ADAPTER.validate_python(event)
    dumped = RUN_EVENT_ADAPTER.dump_python(parsed, mode="json")
    assert RUN_EVENT_ADAPTER.validate_json(json.dumps(dumped)) == parsed
    assert dumped["type"] == event_type


def test_workspace_docs_separate_audit_history_from_live_stream() -> None:
    client, engine = build_client()
    with client:
        schema = client.get("/openapi.json").json()
    events_doc = schema["components"]["schemas"]["WorkspaceResponse"]["properties"]["events"]["description"]
    assert "audit history" in events_doc and "not the live" in events_doc
    route = schema["paths"]["/api/v1/studies/{study_id}/pinned-runs/{run_id}/events"]["get"]
    assert "audit" in route["description"]
    assert "409" in route["responses"]
    text = json.dumps(schema).lower()
    for claim in ["fda approved", "fda approval", "submission-ready", "submission ready", "compliant"]:
        assert claim not in text
    engine.dispose()


def test_uploaded_study_projects_upload_current_with_no_run() -> None:
    """An intake-uploaded study (no claims, never validated) starts at Upload, not later."""
    roster = (
        b"study_id,animal_id,group_number,group_name,sex,dose_mgkg_day,species,strain\n"
        b"S,A1,1,Control,M,0,Rat,SD\nS,A2,2,High,F,100,Rat,SD\n"
    )
    weights = b"study_id,animal_id,study_day,body_weight_g\nS,A1,1,100.5\nS,A2,1,90.5\n"
    client, engine = build_client()
    with client:
        created = client.post(
            "/api/v1/studies",
            data={
                "study_id": "STUDY-JOURNEY-UP",
                "route": "oral gavage",
                "protocol_version": "1.0",
                "authorized_by": "journey test",
            },
            files=[
                ("files", ("animal_roster.csv", roster, "text/csv")),
                ("files", ("body_weights.csv", weights, "text/csv")),
            ],
        )
        assert created.status_code == 201, created.text
        workspace = client.get("/api/v1/studies/STUDY-JOURNEY-UP/workspace").json()
    projection = workspace["journey"]
    assert workspace["release_gate"]["status"] == "blocked"
    assert projection["label"] == LABEL
    assert projection["run"] is None
    assert projection["current_stage_id"] == "upload"
    assert statuses(projection) == {sid: ("current" if sid == "upload" else "pending") for sid in STAGE_IDS}
    freeze_action = stage(projection, "upload")["actions"][-1]
    assert freeze_action["command"] == "POST /api/v1/studies/STUDY-JOURNEY-UP/pinned-runs"
    engine.dispose()
