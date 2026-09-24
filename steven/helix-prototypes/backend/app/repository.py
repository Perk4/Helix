from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    AuditEventRow,
    ChatMessageRow,
    ExportFileRow,
    SectionDraftRow,
    SectionRunRow,
    StudyPackageRow,
    ValidationRunRow,
)
from .schemas import StoredSectionRun, StudyEvidencePackage, ValidationRun


class StudyNotFoundError(LookupError):
    pass


class StudyPackageRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_packages(self) -> list[StudyEvidencePackage]:
        rows = self.session.scalars(select(StudyPackageRow).order_by(StudyPackageRow.study_id)).all()
        return [StudyEvidencePackage.model_validate(row.data) for row in rows]

    def get(self, study_id: str, *, for_update: bool = False) -> StudyEvidencePackage:
        statement = select(StudyPackageRow).where(StudyPackageRow.study_id == study_id)
        if for_update:
            statement = statement.with_for_update()
        row = self.session.scalar(statement)
        if row is None:
            raise StudyNotFoundError(study_id)
        return StudyEvidencePackage.model_validate(row.data)

    def save(self, package: StudyEvidencePackage) -> int:
        row = self.session.get(StudyPackageRow, package.study.study_id)
        if row is None:
            row = StudyPackageRow(
                study_id=package.study.study_id,
                package_id=package.package_id,
                label=package.label,
                data=package.model_dump(mode="json"),
            )
            self.session.add(row)
        else:
            row.data = package.model_dump(mode="json")
            row.version += 1
        self.session.flush()
        return row.version

    def append_event(
        self,
        *,
        study_id: str,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
        occurred_at: datetime | None = None,
    ) -> AuditEventRow:
        if idempotency_key is not None:
            existing = self.session.scalar(
                select(AuditEventRow).where(
                    AuditEventRow.study_id == study_id,
                    AuditEventRow.idempotency_key == idempotency_key,
                )
            )
            if existing is not None:
                return existing
        row = AuditEventRow(
            study_id=study_id,
            event_type=event_type,
            actor=actor,
            payload=payload,
            idempotency_key=idempotency_key,
            occurred_at=occurred_at,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def get_event_by_idempotency_key(self, study_id: str, key: str) -> AuditEventRow | None:
        return self.session.scalar(
            select(AuditEventRow).where(
                AuditEventRow.study_id == study_id,
                AuditEventRow.idempotency_key == key,
            )
        )

    def latest_event(self, study_id: str, event_type: str) -> AuditEventRow | None:
        return self.session.scalar(
            select(AuditEventRow)
            .where(
                AuditEventRow.study_id == study_id,
                AuditEventRow.event_type == event_type,
            )
            .order_by(AuditEventRow.occurred_at.desc(), AuditEventRow.id.desc())
            .limit(1)
        )

    def save_export_file(
        self,
        *,
        study_id: str,
        artifact_id: str,
        filename: str,
        media_type: str,
        checksum: str,
        content: bytes,
    ) -> ExportFileRow:
        existing = self.session.scalar(
            select(ExportFileRow).where(
                ExportFileRow.study_id == study_id,
                ExportFileRow.artifact_id == artifact_id,
            )
        )
        if existing is not None:
            return existing
        row = ExportFileRow(
            study_id=study_id,
            artifact_id=artifact_id,
            filename=filename,
            media_type=media_type,
            checksum=checksum,
            content=content,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def get_export_file(self, study_id: str, artifact_id: str) -> ExportFileRow | None:
        return self.session.scalar(
            select(ExportFileRow).where(
                ExportFileRow.study_id == study_id,
                ExportFileRow.artifact_id == artifact_id,
            )
        )

    def save_validation_run(self, run: ValidationRun) -> None:
        self.session.add(
            ValidationRunRow(
                run_id=run.run_id,
                study_id=run.study_id,
                planner_mode=run.planner.value,
                llm_used=run.llm_used,
                planner_label=run.planner_label,
                rule_bundle_version=run.rule_bundle_version,
                results=[result.model_dump(mode="json") for result in run.results],
                created_at=run.created_at,
            )
        )
        self.session.flush()

    def get_section_run(self, study_id: str, idempotency_key: str) -> SectionRunRow | None:
        return self.session.scalar(
            select(SectionRunRow).where(
                SectionRunRow.study_id == study_id,
                SectionRunRow.idempotency_key == idempotency_key,
            )
        )

    def add_section_run(
        self,
        *,
        run_id: str,
        study_id: str,
        section_package_id: str,
        idempotency_key: str,
        request_hash: str,
        envelope: dict[str, Any],
    ) -> SectionRunRow:
        row = SectionRunRow(
            run_id=run_id,
            study_id=study_id,
            section_package_id=section_package_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            envelope=envelope,
        )
        self.session.add(row)
        self.session.flush()
        return row

    # -- section drafts ---------------------------------------------------- #

    def next_section_draft_version(self, study_id: str, section_id: str) -> int:
        rows = self.session.scalars(
            select(SectionDraftRow).where(
                SectionDraftRow.study_id == study_id,
                SectionDraftRow.section_id == section_id,
            )
        ).all()
        return max((row.version for row in rows), default=0) + 1

    def add_section_draft(self, **fields: Any) -> SectionDraftRow:
        row = SectionDraftRow(**fields)
        self.session.add(row)
        self.session.flush()
        return row

    def current_section_draft(self, study_id: str, section_id: str) -> SectionDraftRow | None:
        """Latest applied draft: newest version that is not proposed or discarded."""
        return self.session.scalar(
            select(SectionDraftRow)
            .where(
                SectionDraftRow.study_id == study_id,
                SectionDraftRow.section_id == section_id,
                SectionDraftRow.status.in_(("needs_review", "verified")),
            )
            .order_by(SectionDraftRow.version.desc())
            .limit(1)
        )

    def get_section_draft(self, study_id: str, section_id: str, version: int) -> SectionDraftRow | None:
        return self.session.scalar(
            select(SectionDraftRow).where(
                SectionDraftRow.study_id == study_id,
                SectionDraftRow.section_id == section_id,
                SectionDraftRow.version == version,
            )
        )

    def list_section_drafts(self, study_id: str, section_id: str) -> list[SectionDraftRow]:
        return list(
            self.session.scalars(
                select(SectionDraftRow)
                .where(
                    SectionDraftRow.study_id == study_id,
                    SectionDraftRow.section_id == section_id,
                )
                .order_by(SectionDraftRow.version)
            ).all()
        )

    # -- chat -------------------------------------------------------------- #

    def add_chat_message(
        self,
        *,
        study_id: str,
        role: str,
        content: str,
        scope: str,
        section_id: str | None,
        intent: str = "ask",
    ) -> ChatMessageRow:
        row = ChatMessageRow(
            study_id=study_id,
            role=role,
            content=content,
            scope=scope,
            section_id=section_id,
            intent=intent,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list_chat_messages(self, study_id: str) -> list[ChatMessageRow]:
        return list(
            self.session.scalars(
                select(ChatMessageRow)
                .where(ChatMessageRow.study_id == study_id)
                .order_by(ChatMessageRow.id)
            ).all()
        )

    def recent_chat_messages(self, study_id: str, limit: int) -> list[ChatMessageRow]:
        rows = self.session.scalars(
            select(ChatMessageRow)
            .where(ChatMessageRow.study_id == study_id)
            .order_by(ChatMessageRow.id.desc())
            .limit(limit)
        ).all()
        return list(reversed(rows))

    def list_section_runs(self, study_id: str) -> list[StoredSectionRun]:
        rows = self.session.scalars(
            select(SectionRunRow)
            .where(SectionRunRow.study_id == study_id, SectionRunRow.receipt.is_not(None))
            .order_by(SectionRunRow.created_at, SectionRunRow.run_id)
        ).all()
        return [
            StoredSectionRun.model_validate(
                {
                    "receipt": row.receipt,
                    "candidate": row.candidate,
                    "envelope": row.envelope,
                    "review_scaffold": row.review_scaffold,
                }
            )
            for row in rows
        ]
