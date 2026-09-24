"""Upload as a job: progress a caller can act on, and metrics worth trusting.

The synchronous endpoint is unchanged and still tested by `test_intake.py`.
What is new here is the job, and the properties that matter are:

  - progress is stage-based, because a percentage would be invented;
  - the metrics are the same numbers the caller reads, so they cannot drift
    from what actually happened;
  - a failure lands as a readable job state rather than leaving the row stuck
    on `running`, which is the failure mode that makes a job queue useless;
  - the same idempotency key does not run the intake twice.
"""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.intake_jobs import STAGES
from app.main import create_app

ROSTER = (b"study_id,animal_id,group_number,group_name,sex,dose_mgkg_day,species,strain\n"
          b"S,A1,1,Control,M,0,Rat,SD\nS,A2,1,Control,F,0,Rat,SD\n"
          b"S,A3,2,High,M,100,Rat,SD\nS,A4,2,High,F,100,Rat,SD\n")
WEIGHTS = (b"study_id,animal_id,study_day,body_weight_g\n"
           b"S,A1,1,100.5\nS,A2,1,90.5\nS,A3,28,150.5\nS,A4,28,140.5\n")
PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF\n"

FORM = {"route": "oral gavage", "protocol_version": "1.0",
        "authorized_by": "job test", "study_type_id": "REPEAT_DOSE_28D_RODENT"}
FILES = [("files", ("animal_roster.csv", ROSTER, "text/csv")),
         ("files", ("body_weights.csv", WEIGHTS, "text/csv"))]


@pytest.fixture
def client(tmp_path):
    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    settings = Settings(database_url="sqlite+pysqlite:///:memory:",
                        auto_seed=False, seed_path=tmp_path / "unused.json")
    with TestClient(create_app(settings=settings, engine=engine)) as test_client:
        yield test_client


def submit(client, *, study_id="STUDY-JOB-1", key="job-key-0001", files=None, **over):
    data = {"study_id": study_id, "idempotency_key": key, **FORM, **over}
    return client.post("/api/v1/studies/jobs", data=data, files=files or FILES)


# ── the happy path ────────────────────────────────────────────────────────────
def test_a_job_is_accepted_and_runs_to_completion(client):
    response = submit(client)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] in {"queued", "succeeded"}
    assert body["stages_total"] == len(STAGES)

    # TestClient runs background tasks before the context exits, so by the time
    # we poll the job has finished.
    job = client.get(f"/api/v1/studies/jobs/{body['job_id']}").json()
    assert job["status"] == "succeeded", job.get("error")
    assert job["stage"] == "persisted"
    assert job["stages_completed"] == len(STAGES)
    assert job["error"] is None


def test_the_study_really_exists_afterwards(client):
    job_id = submit(client).json()["job_id"]
    assert client.get(f"/api/v1/studies/jobs/{job_id}").json()["status"] == "succeeded"

    listed = [s["study_id"] for s in client.get("/api/v1/studies").json()]
    assert listed == ["STUDY-JOB-1"]
    workspace = client.get("/api/v1/studies/STUDY-JOB-1/workspace")
    assert workspace.status_code == 200
    assert workspace.json()["study"]["route"] == "oral gavage"


# ── progress is stage-based, not invented ─────────────────────────────────────
def test_every_declared_stage_is_recorded_in_order(client):
    job_id = submit(client).json()["job_id"]
    job = client.get(f"/api/v1/studies/jobs/{job_id}").json()

    assert list(job["stages"]) == list(STAGES), (
        "stages must be recorded in the declared order so a caller can show the "
        "list before the job starts")
    for stage in STAGES:
        assert "ms" in job["stages"][stage]


def test_the_stages_carry_counts_not_just_timings(client):
    """A timing with no count cannot be interpreted."""
    job_id = submit(client, files=[
        ("files", ("bundle.zip", zipped({"animal_roster.csv": ROSTER,
                                         "body_weights.csv": WEIGHTS,
                                         "protocol.pdf": PDF}), "application/zip"))
    ]).json()["job_id"]
    stages = client.get(f"/api/v1/studies/jobs/{job_id}").json()["stages"]

    assert stages["received"]["files"] == 1          # one zip arrived
    assert stages["received"]["bytes"] > 0
    assert stages["expanded"]["files"] == 3          # three came out of it
    assert stages["classified"]["data"] == 2
    assert stages["classified"]["authority"] == 1
    assert stages["parsed"]["animals"] == 4
    assert stages["persisted"]["claims"] == 0        # intake produces no claims


def test_there_is_no_fabricated_percentage(client):
    job_id = submit(client).json()["job_id"]
    job = client.get(f"/api/v1/studies/jobs/{job_id}").json()
    assert "percent" not in job and "progress" not in job
    assert job["stages_completed"] == job["stages_total"]


# ── metrics ───────────────────────────────────────────────────────────────────
def test_metrics_describe_the_run_and_agree_with_the_stages(client):
    job_id = submit(client).json()["job_id"]
    job = client.get(f"/api/v1/studies/jobs/{job_id}").json()
    metrics = job["metrics"]

    assert metrics["uploaded_files"] == 2
    assert metrics["uploaded_bytes"] == len(ROSTER) + len(WEIGHTS)
    assert metrics["records_total"] == 8            # 4 animals + 4 weights
    assert metrics["records_by_domain"]["animals"] == 4
    assert metrics["records_by_domain"]["body_weights"] == 4

    # The metrics are derived from the stages, so they cannot disagree.
    assert metrics["stage_ms"] == {k: v["ms"] for k, v in job["stages"].items()}
    assert metrics["total_ms"] >= max(metrics["stage_ms"].values())
    assert metrics["slowest_stage"] in STAGES


def test_metrics_scale_with_the_study(client):
    """A bigger study must be visibly bigger, or the numbers are decoration."""
    small = client.get(
        f"/api/v1/studies/jobs/{submit(client).json()['job_id']}").json()["metrics"]

    many = ["study_id,animal_id,study_day,body_weight_g"]
    roster = ["study_id,animal_id,group_number,group_name,sex,dose_mgkg_day,species,strain"]
    for i in range(1, 41):
        group, sex = (1 if i <= 20 else 2), ("M" if i % 2 else "F")
        roster.append(f"S,B{i},{group},G{group},{sex},{0 if group == 1 else 100},Rat,SD")
        for day in (1, 7, 14, 21, 28):
            many.append(f"S,B{i},{day},{100 + i + day}")
    big = client.get(f"/api/v1/studies/jobs/" + submit(
        client, study_id="STUDY-JOB-BIG", key="job-key-big-01", files=[
            ("files", ("animal_roster.csv", "\n".join(roster).encode(), "text/csv")),
            ("files", ("body_weights.csv", "\n".join(many).encode(), "text/csv")),
        ]).json()["job_id"]).json()["metrics"]

    assert big["records_total"] == 40 + 200
    assert big["records_total"] > small["records_total"] * 10
    assert big["uploaded_bytes"] > small["uploaded_bytes"]


# ── failure and idempotency ───────────────────────────────────────────────────
def test_a_rejected_upload_fails_the_job_with_a_reason(client):
    """Not an exception into the void, and not stuck on `running`."""
    job_id = submit(client, key="job-key-bad01", files=[
        ("files", ("body_weights.csv", WEIGHTS, "text/csv"))     # no roster
    ]).json()["job_id"]
    job = client.get(f"/api/v1/studies/jobs/{job_id}").json()

    assert job["status"] == "failed"
    assert "animals" in job["error"]
    assert job["metrics"]["total_ms"] >= 0, "a failed job still reports its timings"
    assert client.get("/api/v1/studies").json() == [], "nothing was persisted"


def test_an_existing_study_fails_the_job_rather_than_overwriting(client):
    assert client.get(f"/api/v1/studies/jobs/{submit(client).json()['job_id']}"
                      ).json()["status"] == "succeeded"
    second = submit(client, key="job-key-0002")
    job = client.get(f"/api/v1/studies/jobs/{second.json()['job_id']}").json()
    assert job["status"] == "failed"
    assert "frozen manifest" in job["error"]


def test_the_same_key_returns_the_same_job(client):
    first = submit(client, key="job-key-same1").json()
    second = submit(client, key="job-key-same1").json()
    assert first["job_id"] == second["job_id"]
    assert len(client.get("/api/v1/studies").json()) == 1, "the intake ran once"


def test_the_same_key_for_a_different_study_is_a_conflict(client):
    submit(client, key="job-key-clash")
    clash = submit(client, study_id="STUDY-OTHER", key="job-key-clash")
    assert clash.status_code == 409
    assert "was used for" in clash.json()["detail"]


def test_a_bad_study_id_is_refused_before_any_work(client):
    response = submit(client, study_id="not-a-study")
    assert response.status_code == 422
    assert "STUDY-" in response.json()["detail"]


def test_an_unknown_job_is_404(client):
    assert client.get("/api/v1/studies/jobs/IJ-NOPE").status_code == 404


# ── the synchronous endpoint is untouched ─────────────────────────────────────
def test_the_synchronous_endpoint_still_works(client):
    response = client.post("/api/v1/studies",
                           data={"study_id": "STUDY-SYNC-1", **FORM}, files=FILES)
    assert response.status_code == 201
    assert response.json()["records"]["animals"] == 4


def zipped(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return buffer.getvalue()
