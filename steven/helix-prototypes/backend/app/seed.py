import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .config import Settings
from .repository import StudyPackageRepository
from .schemas import StudyEvidencePackage


def resolve_seed_path(configured_path: Path) -> Path:
    if configured_path.is_absolute():
        return configured_path
    candidates = [
        Path.cwd() / configured_path,
        Path(__file__).resolve().parents[2] / "synthetic-e2e" / configured_path.name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_seed_package(path: Path) -> StudyEvidencePackage:
    raw = json.loads(path.read_text())
    return StudyEvidencePackage.model_validate(raw)


def seed_database(session: Session, settings: Settings) -> StudyEvidencePackage:
    repository = StudyPackageRepository(session)
    seed = load_seed_package(resolve_seed_path(settings.seed_path))
    try:
        existing = repository.get(seed.study.study_id)
    except LookupError:
        repository.save(seed)
        for event in seed.events:
            repository.append_event(
                study_id=seed.study.study_id,
                event_type=event.event,
                actor=event.actor,
                payload={"outcome": event.outcome, **event.details},
                idempotency_key=f"seed:{event.event_id}",
                occurred_at=datetime.fromisoformat(event.timestamp.replace("Z", "+00:00")),
            )
        session.commit()
        return seed
    return existing
