"""run events and run journey states (Steven-Espaillat/Helix#25)

Revision ID: 9edd082c07ae
Revises: b53f9ec18cf2
Create Date: 2026-09-24 17:14:34.812994

The nine-stage journey's persisted run events and per-run journey state. Before
Alembic these tables were created by the `create_all` startup path on
feat/steven-workspace, so a database from that branch may already have them. In
that case `app.database` adopts the schema (after checking the columns match the
models) and this revision leaves the existing tables alone; otherwise it creates them.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# autogenerate renders JSON variants as JSONB(astext_type=Text()) but does not import Text.
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9edd082c07ae"
down_revision: str | Sequence[str] | None = "b53f9ec18cf2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_DOCUMENT = sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")


def _exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    """Upgrade schema."""
    if not _exists("run_events"):
        op.create_table(
            "run_events",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("event_id", sa.String(length=120), nullable=False),
            sa.Column("run_id", sa.String(length=80), nullable=False),
            sa.Column("study_id", sa.String(length=80), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=40), nullable=False),
            sa.Column("stage_id", sa.String(length=40), nullable=False),
            sa.Column("occurred_at", sa.String(length=40), nullable=False),
            sa.Column("payload", JSON_DOCUMENT, nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("event_id"),
            sa.UniqueConstraint("run_id", "sequence", name="uq_run_event_sequence"),
        )
        with op.batch_alter_table("run_events", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_run_events_run_id"), ["run_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_run_events_study_id"), ["study_id"], unique=False)

    if not _exists("run_journey_states"):
        op.create_table(
            "run_journey_states",
            sa.Column("run_id", sa.String(length=80), nullable=False),
            sa.Column("study_id", sa.String(length=80), nullable=False),
            sa.Column("last_sequence", sa.Integer(), nullable=False),
            sa.Column("oldest_retained_sequence", sa.Integer(), nullable=False),
            sa.Column("stages", JSON_DOCUMENT, nullable=False),
            sa.Column("actions", JSON_DOCUMENT, nullable=False),
            sa.PrimaryKeyConstraint("run_id"),
        )
        with op.batch_alter_table("run_journey_states", schema=None) as batch_op:
            batch_op.create_index(
                batch_op.f("ix_run_journey_states_study_id"), ["study_id"], unique=False
            )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("run_journey_states", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_run_journey_states_study_id"))
    op.drop_table("run_journey_states")
    with op.batch_alter_table("run_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_run_events_study_id"))
        batch_op.drop_index(batch_op.f("ix_run_events_run_id"))
    op.drop_table("run_events")
