"""Add Exotel call SID to call logs.

Revision ID: 20260610_0006
Revises: 20260605_0005
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260610_0006"
down_revision = "20260605_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("call_logs") as batch_op:
        batch_op.add_column(sa.Column("call_sid", sa.String(255), nullable=True))
        batch_op.create_index("ix_call_logs_call_sid", ["call_sid"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("call_logs") as batch_op:
        batch_op.drop_index("ix_call_logs_call_sid")
        batch_op.drop_column("call_sid")
