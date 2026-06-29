"""Phase 2: attendance, invoices, permissions

Revision ID: 20260517_0002
Revises: 20260517_0001
Create Date: 2026-05-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260517_0002"
down_revision: Union[str, None] = "20260517_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("center_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("centers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("method", sa.String(32), server_default="manual", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_attendance_center_date", "attendance_records", ["center_id", "check_in_at"])
    op.create_index("idx_attendance_student", "attendance_records", ["student_id", "check_in_at"])

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("center_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("centers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_no", sa.String(64), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("total", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("gst_details", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "invoice_no"),
    )

    op.create_table(
        "invoice_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("qty", sa.Numeric(10, 2), server_default="1", nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
    )

    for code, module in [
        ("parents.read", "parents"),
        ("parents.write", "parents"),
        ("attendance.read", "attendance"),
        ("attendance.write", "attendance"),
        ("invoices.read", "invoices"),
        ("invoices.write", "invoices"),
    ]:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, module) VALUES (gen_random_uuid(), :code, :module) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(code=code, module=module)
        )

    op.execute(
        sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.code = 'franchise_owner' AND p.code IN (
          'parents.read','parents.write','attendance.read','attendance.write',
          'invoices.read','invoices.write'
        )
        ON CONFLICT DO NOTHING
        """)
    )
    op.execute(
        sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.code = 'branch_manager' AND p.code IN (
          'parents.read','attendance.read','attendance.write','invoices.read'
        )
        ON CONFLICT DO NOTHING
        """)
    )


def downgrade() -> None:
    op.drop_table("invoice_lines")
    op.drop_table("invoices")
    op.drop_index("idx_attendance_student", "attendance_records")
    op.drop_index("idx_attendance_center_date", "attendance_records")
    op.drop_table("attendance_records")
