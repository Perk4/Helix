"""bind intake idempotency to request

Revision ID: b53f9ec18cf2
Revises: ea600664952b
Create Date: 2026-09-24 16:11:49.411649

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b53f9ec18cf2'
down_revision: str | Sequence[str] | None = 'ea600664952b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store the canonical request bound to each idempotency key."""
    with op.batch_alter_table("intake_jobs") as batch_op:
        batch_op.add_column(sa.Column("request_hash", sa.String(length=80), nullable=True))
    op.execute("UPDATE intake_jobs SET request_hash = 'legacy:unknown' WHERE request_hash IS NULL")
    with op.batch_alter_table("intake_jobs") as batch_op:
        batch_op.alter_column("request_hash", existing_type=sa.String(length=80), nullable=False)


def downgrade() -> None:
    """Remove request fingerprints."""
    with op.batch_alter_table("intake_jobs") as batch_op:
        batch_op.drop_column("request_hash")
