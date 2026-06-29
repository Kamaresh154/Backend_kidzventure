"""Phase 3: finance ledger (accounts + entries)

Revision ID: 20260518_0003
Revises: 20260517_0002
Create Date: 2026-05-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260518_0003"
down_revision: Union[str, None] = "20260517_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Chart of accounts ────────────────────────────────────────────────────
    op.create_table(
        "ledger_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("account_type", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(8), server_default="INR", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "code", name="uq_ledger_account_org_code"),
    )
    op.create_index(
        "idx_ledger_accounts_org", "ledger_accounts", ["organization_id"]
    )

    # ── Ledger entries ────────────────────────────────────────────────────────
    op.create_table(
        "ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "center_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("centers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ledger_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("direction", sa.String(8), nullable=False),          # debit | credit
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(8), server_default="INR", nullable=False),
        sa.Column("entry_type", sa.String(32), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("reference_no", sa.String(128), nullable=True),
        sa.Column("entry_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("direction IN ('debit','credit')", name="ck_ledger_direction"),
        sa.CheckConstraint("amount > 0", name="ck_ledger_amount_positive"),
    )
    op.create_index(
        "idx_ledger_entries_org_date",
        "ledger_entries",
        ["organization_id", "entry_date"],
    )
    op.create_index("idx_ledger_entries_account", "ledger_entries", ["account_id"])
    op.create_index("idx_ledger_entries_invoice", "ledger_entries", ["invoice_id"])

    # ── RBAC: ledger permissions ──────────────────────────────────────────────
    for code, module in [
        ("ledger.read", "ledger"),
        ("ledger.write", "ledger"),
    ]:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, module) "
                "VALUES (gen_random_uuid(), :code, :module) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(code=code, module=module)
        )

    # Grant ledger.read + ledger.write to franchise_owner
    op.execute(
        sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.code = 'franchise_owner'
          AND p.code IN ('ledger.read', 'ledger.write')
        ON CONFLICT DO NOTHING
        """)
    )

    # Grant ledger.read to accountant and branch_manager
    op.execute(
        sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.code IN ('accountant', 'branch_manager')
          AND p.code = 'ledger.read'
        ON CONFLICT DO NOTHING
        """)
    )

    # Grant ledger.write to accountant
    op.execute(
        sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.code = 'accountant'
          AND p.code = 'ledger.write'
        ON CONFLICT DO NOTHING
        """)
    )


def downgrade() -> None:
    op.drop_index("idx_ledger_entries_invoice", "ledger_entries")
    op.drop_index("idx_ledger_entries_account", "ledger_entries")
    op.drop_index("idx_ledger_entries_org_date", "ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index("idx_ledger_accounts_org", "ledger_accounts")
    op.drop_table("ledger_accounts")
