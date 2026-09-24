"""Human Gate 1 freeze: Pinned Run first, then Data Validation (Lane A, Helix#20).

Uses the test-local qualified copy of the governed tree from
``test_journey_run_events`` (shipped package data is never modified).
"""

from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.data_validation import DataValidationService
from app.manifest_authorization import FREEZE_DATA_VALIDATION_FAILED, freeze_data_validation_key
from app.models import RunEventRow
from tests.test_journey_run_events import BASE, build_client, journey, qualified_fixture_root, statuses

FREEZE = {"actor": "Dr. Study Owner", "idempotency_key": "gate1-freeze-authorization-0001"}


def _boom(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("synthetic Data Validation outage")


def test_freeze_success_returns_run_and_data_validation(tmp_path: Path) -> None:
    client, _engine = build_client(qualified_fixture_root(tmp_path))
    with client:
        response = client.post(f"{BASE}/pinned-runs", json=FREEZE)
        assert response.status_code == 201, response.text
        run = response.json()
        workspace = client.get(f"{BASE}/workspace").json()
        assert workspace["pinned_run"]["run_id"] == run["run_id"]
        runs = [item["receipt"]["run_id"] for item in workspace["data_validation_executions"]]
        assert runs == [run["run_id"]]
        assert statuses(workspace["journey"])["upload"] == "complete"

        replay = client.post(f"{BASE}/pinned-runs", json=FREEZE)
        assert replay.status_code == 201, replay.text
        assert replay.json()["run_id"] == run["run_id"]


def test_data_validation_failure_preserves_pinned_run_with_typed_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, engine = build_client(qualified_fixture_root(tmp_path))
    with client:
        monkeypatch.setattr(DataValidationService, "execute", _boom)
        response = client.post(f"{BASE}/pinned-runs", json=FREEZE)
        assert response.status_code == 409, response.text
        detail = response.json()["detail"]
        assert detail["code"] == FREEZE_DATA_VALIDATION_FAILED
        assert detail["pinned_run_preserved"] is True
        run_id = detail["run_id"]
        assert detail["retry"]["operation"] == "run_data_validation"
        assert detail["retry"]["path"] == f"{BASE}/data-validation-packages"
        assert detail["retry"]["idempotency_key"] == freeze_data_validation_key(run_id)

        workspace = client.get(f"{BASE}/workspace").json()
        assert workspace["pinned_run"]["run_id"] == run_id
        assert workspace["data_validation_executions"] == []
        assert statuses(workspace["journey"])["upload"] == "complete"
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(RunEventRow)) > 0

        monkeypatch.undo()
        retry = client.post(
            f"{BASE}/data-validation-packages",
            json={
                "actor": FREEZE["actor"],
                "package_id": detail["retry"]["package_id"],
                "idempotency_key": detail["retry"]["idempotency_key"],
            },
        )
        assert retry.status_code == 201, retry.text
        after = client.get(f"{BASE}/workspace").json()
        assert after["pinned_run"]["run_id"] == run_id
        assert len(after["data_validation_executions"]) == 1
        assert journey(client)["run"]["run_id"] == run_id


def test_new_authorization_key_after_freeze_does_not_create_second_run(tmp_path: Path) -> None:
    client, _engine = build_client(qualified_fixture_root(tmp_path))
    with client:
        first = client.post(f"{BASE}/pinned-runs", json=FREEZE)
        assert first.status_code == 201, first.text
        second = client.post(
            f"{BASE}/pinned-runs",
            json={**FREEZE, "idempotency_key": "gate1-freeze-authorization-0002"},
        )
        assert second.status_code in {201, 409}, second.text
        workspace = client.get(f"{BASE}/workspace").json()
        assert workspace["pinned_run"]["run_id"] == first.json()["run_id"]
