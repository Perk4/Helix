"""add content drafts and chat

Revision ID: c24154d7a8e9
Revises: 9edd082c07ae
Create Date: 2026-09-24 17:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = "c24154d7a8e9"
down_revision: str | Sequence[str] | None = "9edd082c07ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonDocument = sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "content_drafts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("study_id", sa.String(length=80), nullable=False),
        sa.Column("section_id", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("blocks", JsonDocument, nullable=False),
        sa.Column("narrative_md", sa.Text(), nullable=True),
        sa.Column("provenance", JsonDocument, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=80), nullable=True),
        sa.Column("feedback", JsonDocument, nullable=False),
        sa.Column("data_available", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("study_id", "section_id", "version", name="uq_content_draft_version"),
    )
    op.create_index(op.f("ix_content_drafts_study_id"), "content_drafts", ["study_id"])
    op.create_index(op.f("ix_content_drafts_section_id"), "content_drafts", ["section_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("study_id", sa.String(length=80), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("section_id", sa.String(length=80), nullable=True),
        sa.Column("intent", sa.String(length=16), nullable=False),
        sa.Column("draft_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_messages_study_id"), "chat_messages", ["study_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_chat_messages_study_id"), table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index(op.f("ix_content_drafts_section_id"), table_name="content_drafts")
    op.drop_index(op.f("ix_content_drafts_study_id"), table_name="content_drafts")
    op.drop_table("content_drafts")
