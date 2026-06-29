"""Phase 4: payroll, inventory, CRM, franchise

Revision ID: 20260518_0004
Revises: 20260518_0003
Create Date: 2026-05-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260518_0004"
down_revision: Union[str, None] = "20260518_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid_type = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # ── Staff Profiles ────────────────────────────────────────────────────────
    op.create_table(
        "staff_profiles",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("center_id", uuid_type, sa.ForeignKey("centers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("designation", sa.String(128), nullable=True),
        sa.Column("department", sa.String(128), nullable=True),
        sa.Column("employee_code", sa.String(64), nullable=True),
        sa.Column("date_of_joining", sa.Date, nullable=True),
        sa.Column("basic_salary", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("bank_account", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_staff_profiles_org", "staff_profiles", ["organization_id"])

    # ── Payslips ──────────────────────────────────────────────────────────────
    op.create_table(
        "payslips",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("staff_id", uuid_type, sa.ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pay_period", sa.String(7), nullable=False),
        sa.Column("basic_salary", sa.Numeric(14, 2), nullable=False),
        sa.Column("allowances", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("deductions", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("bonus", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("gross_pay", sa.Numeric(14, 2), nullable=False),
        sa.Column("net_pay", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("breakdown", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("paid_at", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("staff_id", "pay_period", name="uq_payslip_staff_period"),
    )
    op.create_index("idx_payslips_org", "payslips", ["organization_id"])
    op.create_index("idx_payslips_staff", "payslips", ["staff_id"])

    # ── Inventory Products ────────────────────────────────────────────────────
    op.create_table(
        "inventory_products",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("unit", sa.String(32), nullable=False, server_default="pcs"),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("reorder_level", sa.Integer, nullable=False, server_default="0"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_inventory_products_org", "inventory_products", ["organization_id"])

    # ── Stock Entries ─────────────────────────────────────────────────────────
    op.create_table(
        "stock_entries",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("center_id", uuid_type, sa.ForeignKey("centers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_id", uuid_type, sa.ForeignKey("inventory_products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("entry_type", sa.String(32), nullable=False),
        sa.Column("reference_no", sa.String(128), nullable=True),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("created_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_stock_entries_product", "stock_entries", ["product_id"])

    # ── Leads ─────────────────────────────────────────────────────────────────
    op.create_table(
        "leads",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("center_id", uuid_type, sa.ForeignKey("centers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("child_name", sa.String(255), nullable=False),
        sa.Column("child_age", sa.Integer, nullable=True),
        sa.Column("parent_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),
        sa.Column("lost_reason", sa.String(255), nullable=True),
        sa.Column("assigned_to", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("follow_up_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("converted_student_id", uuid_type, sa.ForeignKey("students.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_leads_org", "leads", ["organization_id"])
    op.create_index("idx_leads_status", "leads", ["status"])

    # ── Lead Activities ───────────────────────────────────────────────────────
    op.create_table(
        "lead_activities",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id", uuid_type, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_type", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("created_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_lead_activities_lead", "lead_activities", ["lead_id"])

    # ── RBAC: new module permissions ─────────────────────────────────────────
    op.execute("""
        INSERT INTO permissions (id, code, module) VALUES
            (gen_random_uuid(), 'payroll.read', 'payroll'),
            (gen_random_uuid(), 'payroll.write', 'payroll'),
            (gen_random_uuid(), 'inventory.read', 'inventory'),
            (gen_random_uuid(), 'inventory.write', 'inventory'),
            (gen_random_uuid(), 'crm.read', 'crm'),
            (gen_random_uuid(), 'crm.write', 'crm'),
            (gen_random_uuid(), 'reports.read', 'reports'),
            (gen_random_uuid(), 'franchise.read', 'franchise')
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table("lead_activities")
    op.drop_table("leads")
    op.drop_table("stock_entries")
    op.drop_table("inventory_products")
    op.drop_table("payslips")
    op.drop_table("staff_profiles")
