from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

JsonDocument = JSON().with_variant(JSONB, "postgresql")


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class StudyPackageRow(Base):
    __tablename__ = "study_packages"

    study_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    package_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    data: Mapped[dict[str, Any]] = mapped_column(JsonDocument, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class AuditEventRow(Base):
    __tablename__ = "audit_events"
    __table_args__ = (UniqueConstraint("study_id", "idempotency_key", name="uq_audit_idempotency"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    study_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonDocument, nullable=False, default=dict)


class ExportFileRow(Base):
    __tablename__ = "export_files"
    __table_args__ = (UniqueConstraint("study_id", "artifact_id", name="uq_export_file"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    study_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    artifact_id: Mapped[str] = mapped_column(String(80), nullable=False)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    media_type: Mapped[str] = mapped_column(String(120), nullable=False)
    checksum: Mapped[str] = mapped_column(String(80), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ValidationRunRow(Base):
    __tablename__ = "validation_runs"

    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    study_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    planner_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    llm_used: Mapped[bool] = mapped_column(nullable=False)
    planner_label: Mapped[str] = mapped_column(String(120), nullable=False)
    rule_bundle_version: Mapped[str] = mapped_column(String(40), nullable=False)
    results: Mapped[list[dict[str, Any]]] = mapped_column(JsonDocument, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SectionRunRow(Base):
    __tablename__ = "section_runs"
    __table_args__ = (UniqueConstraint("study_id", "idempotency_key", name="uq_section_run_key"),)

    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    study_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    section_package_id: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    envelope: Mapped[dict[str, Any]] = mapped_column(JsonDocument, nullable=False)
    candidate: Mapped[dict[str, Any] | None] = mapped_column(JsonDocument, nullable=True)
    receipt: Mapped[dict[str, Any] | None] = mapped_column(JsonDocument, nullable=True)
    review_scaffold: Mapped[dict[str, Any] | None] = mapped_column(JsonDocument, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ContentDraftRow(Base):
    """One version of a section's drafted content. Append-only; the current
    draft is the latest non-discarded, non-proposed version."""

    __tablename__ = "content_drafts"
    __table_args__ = (
        UniqueConstraint("study_id", "section_id", "version", name="uq_content_draft_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    study_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    section_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # lifecycle: needs_review | proposed | verified | discarded
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    blocks: Mapped[list[dict[str, Any]]] = mapped_column(JsonDocument, nullable=False, default=list)
    narrative_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance: Mapped[list[dict[str, Any]]] = mapped_column(JsonDocument, nullable=False, default=list)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    feedback: Mapped[list[str]] = mapped_column(JsonDocument, nullable=False, default=list)
    data_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ChatMessageRow(Base):
    """One turn of the per-study chat thread. Append-only."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    study_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="section")  # section | study
    section_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    intent: Mapped[str] = mapped_column(String(16), nullable=False, default="ask")  # ask | revise
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
