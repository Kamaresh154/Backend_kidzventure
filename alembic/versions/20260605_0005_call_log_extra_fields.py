"""Add call_direction, sector, centre fields, recording_source to call_logs

Revision ID: 20260605_0005
Revises: 20260518_0004_phase4_payroll_inventory_crm
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260605_0005"
down_revision = "20260518_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("call_logs") as batch_op:
        batch_op.add_column(sa.Column("call_direction", sa.String(16), nullable=False, server_default="outbound"))
        batch_op.add_column(sa.Column("sector", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("centre_id", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("centre_name", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("recording_source", sa.String(32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("call_logs") as batch_op:
        batch_op.drop_column("call_direction")
        batch_op.drop_column("sector")
        batch_op.drop_column("centre_id")
        batch_op.drop_column("centre_name")
        batch_op.drop_column("recording_source")
