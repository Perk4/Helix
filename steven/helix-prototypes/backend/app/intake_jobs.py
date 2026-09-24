"""Run an upload as a job, and report what it is actually doing.

`POST /api/v1/studies` does the whole intake inside the request. That is fine for
a 40-animal study and poor for a 150-animal one, where the caller waits with no
idea whether anything is happening.

This runs the same intake as a job and records progress. The progress is not a
percentage: nobody can honestly compute one, because expanding a zip, parsing
9,338 rows and writing a 2 MB JSONB document cost wildly different amounts and
the split depends on the study. What a caller gets instead is the stage that is
running, the stages already done with their timings, and counts that mean
something — bytes received, files classified, records parsed per domain.

The same numbers are the metrics. A stage that takes 200 ms on one study and
14 s on another is visible without adding separate instrumentation, because the
timings a caller reads are the timings that get stored.

SCOPE

Jobs run in the FastAPI background task pool: one process, in memory, no retry
and no recovery if the process dies mid-job. A job interrupted that way stays
`running` forever rather than lying about having finished. Moving to a real
queue means replacing `submit`, and nothing else here changes.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .intake import IntakeRejected, build_package
from .models import IntakeJobRow
from .repository import StudyNotFoundError, StudyPackageRepository

QUEUED = "queued"
RUNNING = "running"
SUCCEEDED = "succeeded"
FAILED = "failed"

# The stages a caller can expect, in order. Named so a UI can show the list
# before the job starts rather than discovering it as results arrive.
STAGES = ("received", "expanded", "classified", "parsed", "persisted")


class IntakeJobConflictError(RuntimeError):
    """The idempotency key is in use for a different request."""


@dataclass
class StageRecorder:
    """Times each stage and keeps the counts that make it interpretable."""

    stages: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    _started: float = field(default_factory=time.perf_counter)
    _last: float = field(default_factory=time.perf_counter)
    _on_done: Callable[[str, dict[str, Any], dict[str, Any]], None] | None = field(
        default=None, repr=False)

    def done(self, stage: str, **detail: Any) -> None:
        now = time.perf_counter()
        self.stages[stage] = {"ms": round((now - self._last) * 1000), **detail}
        self._last = now
        if self._on_done is not None:
            self._on_done(stage, self.stages, self.metrics)

    def finish(self) -> None:
        self.metrics["total_ms"] = round((time.perf_counter() - self._started) * 1000)
        self.metrics["stage_ms"] = {k: v["ms"] for k, v in self.stages.items()}
        slowest = max(self.stages.items(), key=lambda kv: kv[1]["ms"], default=None)
        if slowest:
            self.metrics["slowest_stage"] = slowest[0]


class IntakeJobService:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    # ── submission ────────────────────────────────────────────────────────────
    def submit(self, *, study_id: str, idempotency_key: str,
               uploads: list[tuple[str, bytes]], facts: dict[str, str]) -> IntakeJobRow:
        """Record a queued job. Replaying the same request returns the original."""
        request_hash = _request_hash(study_id, uploads, facts)
        with self.session_factory() as session:
            existing = session.scalar(
                select(IntakeJobRow).where(IntakeJobRow.idempotency_key == idempotency_key))
            if existing is not None:
                if existing.study_id != study_id:
                    raise IntakeJobConflictError(
                        f"idempotency key {idempotency_key!r} was used for "
                        f"{existing.study_id}, not {study_id}")
                if existing.request_hash != request_hash:
                    raise IntakeJobConflictError(
                        f"idempotency key {idempotency_key!r} was used for a different request")
                session.expunge(existing)
                return existing

            received = sum(len(payload) for _n, payload in uploads)
            row = IntakeJobRow(
                job_id=f"IJ-{uuid.uuid4().hex[:12].upper()}",
                study_id=study_id, idempotency_key=idempotency_key,
                request_hash=request_hash, status=QUEUED, stage="received",
                stages={"received": {"ms": 0, "files": len(uploads), "bytes": received}},
                metrics={"uploaded_bytes": received, "uploaded_files": len(uploads)})
            session.add(row)
            session.commit()
            session.refresh(row)
            session.expunge(row)
            return row

    # ── execution ─────────────────────────────────────────────────────────────
    def run(self, job_id: str, uploads: list[tuple[str, bytes]],
            facts: dict[str, str]) -> None:
        """Execute a queued job. Safe to call once; a second call is a no-op."""
        with self.session_factory() as session:
            row = session.get(IntakeJobRow, job_id)
            if row is None or row.status != QUEUED:
                return
            row.status = RUNNING
            session.commit()

        recorder = StageRecorder(
            stages=dict(row.stages), metrics=dict(row.metrics),
            _on_done=lambda stage, stages, metrics: self._persist_progress(
                job_id, stage, stages, metrics))
        try:
            package, report = self._build(recorder, row.study_id, uploads, facts)
        except IntakeRejected as exc:
            self._fail(job_id, recorder, str(exc))
            return
        except Exception as exc:                                  # noqa: BLE001
            # An unexpected failure must still land as a readable job state
            # rather than leaving the row stuck on `running`.
            self._fail(job_id, recorder, f"{type(exc).__name__}: {exc}")
            return

        try:
            with self.session_factory() as session:
                repository = StudyPackageRepository(session)
                try:
                    repository.get(row.study_id)
                except (LookupError, StudyNotFoundError):
                    repository.save(package)
                    session.commit()
                else:
                    self._fail(job_id, recorder,
                               f"{row.study_id} already exists; a frozen manifest that "
                               f"changed underneath a run would invalidate every claim "
                               f"citing it")
                    return
            recorder.done("persisted", claims=len(package.claims),
                          manifest_entries=len(package.manifest))
        except Exception as exc:                                  # noqa: BLE001
            self._fail(job_id, recorder, f"{type(exc).__name__}: {exc}")
            return

        recorder.metrics["records_total"] = sum(
            len(getattr(package.records, domain)) for domain in package.records.model_fields)
        recorder.finish()
        with self.session_factory() as session:
            row = session.get(IntakeJobRow, job_id)
            row.status, row.stage = SUCCEEDED, "persisted"
            row.stages, row.metrics = recorder.stages, recorder.metrics
            row.receipt = report.as_record()
            session.commit()

    def _build(self, recorder: StageRecorder, study_id: str,
               uploads: list[tuple[str, bytes]], facts: dict[str, str]):
        """The intake itself, with each stage timed as it completes."""
        from . import intake

        expanded: list[tuple[str, bytes]] = []
        for name, payload in uploads:
            expanded.extend(intake.expand(name, payload))
        recorder.done("expanded", files=len(expanded))

        kinds: dict[str, int] = {}
        for name, _payload in expanded:
            kind = intake.classify(name)[0]
            kinds[kind] = kinds.get(kind, 0) + 1
        recorder.done("classified", **kinds)

        package, report = build_package(study_id=study_id, uploads=uploads, **facts)
        by_domain = {domain: len(getattr(package.records, domain))
                     for domain in package.records.model_fields}
        recorder.done("parsed", **{k: v for k, v in by_domain.items() if v})
        recorder.metrics["records_by_domain"] = by_domain
        return package, report

    def _persist_progress(self, job_id: str, stage: str,
                          stages: dict[str, Any], metrics: dict[str, Any]) -> None:
        with self.session_factory() as session:
            row = session.get(IntakeJobRow, job_id)
            if row is None:
                return
            row.stage = stage
            row.stages = dict(stages)
            row.metrics = dict(metrics)
            session.commit()

    def _fail(self, job_id: str, recorder: StageRecorder, message: str) -> None:
        recorder.finish()
        with self.session_factory() as session:
            row = session.get(IntakeJobRow, job_id)
            if row is None:
                return
            row.status, row.error = FAILED, message[:500]
            row.stages, row.metrics = recorder.stages, recorder.metrics
            session.commit()

    # ── reading ───────────────────────────────────────────────────────────────
    def get(self, job_id: str) -> IntakeJobRow | None:
        with self.session_factory() as session:
            row = session.get(IntakeJobRow, job_id)
            if row is not None:
                session.expunge(row)
            return row


def _request_hash(study_id: str, uploads: list[tuple[str, bytes]],
                  facts: dict[str, str]) -> str:
    payload = {
        "study_id": study_id,
        "facts": facts,
        "uploads": [
            {"name": name, "bytes": len(content),
             "sha256": hashlib.sha256(content).hexdigest()}
            for name, content in uploads
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def as_record(row: IntakeJobRow) -> dict:
    completed = [s for s in STAGES if s in (row.stages or {})]
    return {
        "job_id": row.job_id,
        "study_id": row.study_id,
        "status": row.status,
        "stage": row.stage,
        # Stage counts, not a percentage: this one is honest and a percentage
        # would not be, because the stages cost wildly different amounts.
        "stages_completed": len(completed),
        "stages_total": len(STAGES),
        "stages": row.stages,
        "metrics": row.metrics,
        "receipt": row.receipt,
        "error": row.error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
